import os
import sys
import random
import pygame

# =========================
# PyInstaller 대응: assets 경로 처리
# =========================
def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)

# =========================
# 기본 설정
# =========================
pygame.init()
try:
    pygame.mixer.init()
    SOUND_OK = True
except:
    SOUND_OK = False

W, H = 1280, 720
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("조선 왕 강화하기")
clock = pygame.time.Clock()

FONT_NAME = "malgungothic"
FONT_S = pygame.font.SysFont(FONT_NAME, 18)
FONT_M = pygame.font.SysFont(FONT_NAME, 26, bold=True)
FONT_L = pygame.font.SysFont(FONT_NAME, 44, bold=True)
FONT_T = pygame.font.SysFont(FONT_NAME, 56, bold=True)
FONT_POP = pygame.font.SysFont(FONT_NAME, 64, bold=True)

WHITE = (255, 255, 255)
BLACK = (10, 10, 10)
GRAY = (170, 170, 170)
PANEL = (240, 240, 240)
RED = (220, 0, 0)
BTN_DISABLED = (205, 205, 205)

# =========================
# 조선 왕 데이터
# =========================
KINGS = [
    "태조","정종","태종","세종","문종","단종","세조","예종","성종","연산군",
    "중종","인종","명종","선조","광해군","인조","효종","현종","숙종","경종",
    "영조","정조","순조","헌종","철종","고종","순종"
]

# =========================
# 밸런스(원하면 여기만 조절)
# =========================
START_MONEY = 500_000
BASE_COST = 500

# 판매가: (강화비용 * SELL_MULT) + (레벨 * SELL_LV_BONUS)
SELL_MULT = 0.90
SELL_LV_BONUS = 1000

# =========================
# 상태
# =========================
king_i = 0
plus_level = 0
money = START_MONEY

face_mark = None
face_mark_timer = 0.0

popup_text = ""
popup_timer = 0.0

game_state = "play"   # "play" or "ending"
ending_lines = []

def set_popup(text: str, seconds: float = 1.2):
    global popup_text, popup_timer
    popup_text = text
    popup_timer = seconds

def set_face_x(seconds: float = 1.1):
    global face_mark, face_mark_timer
    face_mark = "X"
    face_mark_timer = seconds

def cost_now():
    return int(BASE_COST * (1.18 ** plus_level))

# =========================
# 확률 규칙(정수 %로 안정화)
# =========================
def success_rate(lv: int) -> int:
    if lv <= 2:
        return 100
    return max(10, 100 - (lv - 2) * 5)

def down_rate(lv: int) -> int:
    # +5부터 하락 시작, 최대 15%
    if lv < 5:
        return 0
    # 기존 너 코드 느낌 유지: (lv-4)*3% 를 15% 상한
    return min(15, int((lv - 4) * 3))

def break_rate(lv: int) -> int:
    # +10부터 파괴 시작, 최대 5%
    if lv < 10:
        return 0
    # 기존 너 코드 느낌 유지: +10=1%, +11=2% ... 최대 5%
    return min(5, int(lv - 9))

def sell_price(lv: int) -> int:
    return int(cost_now() * SELL_MULT + lv * SELL_LV_BONUS)

# =========================
# assets 로드
# =========================
ASSET_DIR = resource_path("assets")
KING_DIR = os.path.join(ASSET_DIR, "kings")
SOUND_DIR = os.path.join(ASSET_DIR, "sounds")

FACE_SIZE = (260, 320)

def load_face(path):
    img = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(img, FACE_SIZE)

def face_placeholder(name):
    s = pygame.Surface(FACE_SIZE)
    s.fill((225, 225, 225))
    pygame.draw.rect(s, BLACK, s.get_rect(), 2, border_radius=16)
    s.blit(FONT_M.render("초상화 없음", True, BLACK), (65, 140))
    s.blit(FONT_M.render(name, True, BLACK), (65, 175))
    return s

FACES = {}
for i, name in enumerate(KINGS, start=1):
    p = os.path.join(KING_DIR, f"{i}.png")
    if os.path.exists(p):
        try:
            FACES[i] = load_face(p)
        except:
            FACES[i] = face_placeholder(name)
    else:
        FACES[i] = face_placeholder(name)

# =========================
# 효과음
# =========================
snd_down = snd_break = None
if SOUND_OK:
    try:
        snd_down = pygame.mixer.Sound(os.path.join(SOUND_DIR, "down.wav"))
        snd_down.set_volume(0.4)
    except:
        pass
    try:
        snd_break = pygame.mixer.Sound(os.path.join(SOUND_DIR, "break.wav"))
        snd_break.set_volume(0.4)
    except:
        pass

def play(s):
    if SOUND_OK and s:
        try:
            s.play()
        except:
            pass

# =========================
# UI 위치
# =========================
LEFT_X = 100
FACE_RECT = pygame.Rect(LEFT_X, 190, *FACE_SIZE)

BTN_UP   = pygame.Rect(LEFT_X, 605, 260, 70)
BTN_SELL = pygame.Rect(LEFT_X + 290, 605, 260, 70)

RIGHT_X = 720
RIGHT_W = W - RIGHT_X - 60

def draw_btn(rect, text, enabled=True):
    bg = GRAY if enabled else BTN_DISABLED
    pygame.draw.rect(screen, bg, rect, border_radius=16)
    pygame.draw.rect(screen, BLACK, rect, 2, border_radius=16)
    tcol = BLACK if enabled else (120, 120, 120)
    t = FONT_M.render(text, True, tcol)
    screen.blit(t, (rect.centerx - t.get_width()//2, rect.y + 22))

def reset_item():
    global king_i, plus_level
    king_i = 0
    plus_level = 0

def reset_game():
    global money, game_state, popup_text, popup_timer, face_mark, face_mark_timer
    reset_item()
    money = START_MONEY
    game_state = "play"
    popup_text = ""
    popup_timer = 0.0
    face_mark = None
    face_mark_timer = 0.0

def start_ending():
    global game_state, ending_lines
    game_state = "ending"
    ending_lines = [
        "🎉 조선 왕 강화 엔딩!",
        f"최종 왕: {KINGS[king_i]}",
        f"최종 강화: +{plus_level}",
        f"보유 금액: {money}원",
        "",
        "ENTER : 다시 시작",
        "ESC   : 종료"
    ]

def do_upgrade():
    global money, plus_level, king_i

    c = cost_now()
    if money < c:
        set_popup("돈 부족!", 1.2)
        return
    money -= c

    s = success_rate(plus_level)
    d = down_rate(plus_level)
    b = break_rate(plus_level)

    # 성공
    if random.randint(1, 100) <= s:
        plus_level += 1
        if king_i < len(KINGS) - 1:
            king_i += 1

        set_popup("성공!", 1.1)

        # 엔딩 조건: 순종 도달 + 최종 강화(+27) 달성
        if king_i == len(KINGS) - 1 and plus_level >= len(KINGS):
            start_ending()
        return

    # 실패
    r = random.randint(1, 100)

    if b > 0 and r <= b:
        reset_item()
        play(snd_break)
        set_popup("파괴!", 1.4)
        set_face_x(1.2)
        return

    if d > 0 and r <= b + d:
        if plus_level > 0:
            plus_level -= 1
        if king_i > 0:
            king_i -= 1
        play(snd_down)
        set_popup("하락!", 1.3)
        set_face_x(1.2)
        return

    set_popup("실패(유지)", 1.2)

def do_sell():
    global money

    # 0강 판매 불가
    if plus_level == 0:
        set_popup("0강은 판매 불가!", 1.2)
        return

    price = sell_price(plus_level)
    money += price
    reset_item()
    set_popup("판매!", 1.1)

# =========================
# 메인 루프
# =========================
running = True
while running:
    dt = clock.tick(60) / 1000.0

    if popup_timer > 0:
        popup_timer = max(0.0, popup_timer - dt)
    if face_mark_timer > 0:
        face_mark_timer = max(0.0, face_mark_timer - dt)
        if face_mark_timer == 0:
            face_mark = None

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

        # 엔딩 화면 입력
        if game_state == "ending":
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN:
                    reset_game()
                elif e.key == pygame.K_ESCAPE:
                    running = False
            continue

        # 플레이 입력
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if FACE_RECT.collidepoint(e.pos) or BTN_UP.collidepoint(e.pos):
                do_upgrade()
            elif BTN_SELL.collidepoint(e.pos):
                do_sell()

    # -------------------------
    # Draw
    # -------------------------
    screen.fill(WHITE)

    title = FONT_T.render("조선 왕 강화하기", True, (200, 0, 0))
    screen.blit(title, (W//2 - title.get_width()//2, 35))

    screen.blit(FONT_M.render(f"강화비용: {cost_now()}원", True, BLACK), (LEFT_X, 100))
    sell_text = "판매가격: (0강 판매 불가)" if plus_level == 0 else f"판매가격: {sell_price(plus_level)}원"
    screen.blit(FONT_M.render(sell_text, True, BLACK), (LEFT_X, 135))

    pygame.draw.rect(screen, (250, 250, 250), FACE_RECT.inflate(18, 18), border_radius=20)
    pygame.draw.rect(screen, BLACK, FACE_RECT.inflate(18, 18), 2, border_radius=20)
    screen.blit(FACES[king_i + 1], FACE_RECT.topleft)

    if face_mark == "X":
        x1, y1 = FACE_RECT.left + 20, FACE_RECT.top + 25
        x2, y2 = FACE_RECT.right - 20, FACE_RECT.bottom - 25
        pygame.draw.line(screen, RED, (x1, y1), (x2, y2), 12)
        pygame.draw.line(screen, RED, (x1, y2), (x2, y1), 12)

    main = FONT_L.render(f"+{plus_level}  {KINGS[king_i]}", True, BLACK)
    screen.blit(main, (LEFT_X, 500))

    s = success_rate(plus_level)
    screen.blit(FONT_M.render(f"성공률 {s}%", True, BLACK), (LEFT_X, 550))

    draw_btn(BTN_UP, "강화하기", enabled=True)
    draw_btn(BTN_SELL, "판매하기", enabled=(plus_level > 0))

    money_surf = FONT_M.render(f"돈: {money}원", True, BLACK)
    screen.blit(money_surf, (LEFT_X, 690))

    right = pygame.Rect(RIGHT_X, 130, RIGHT_W, 540)
    pygame.draw.rect(screen, PANEL, right, border_radius=18)
    pygame.draw.rect(screen, BLACK, right, 2, border_radius=18)

    d = down_rate(plus_level)
    b = break_rate(plus_level)
    screen.blit(FONT_M.render(f"하락 {d}%", True, BLACK), (RIGHT_X + 30, 155))
    bsurf = FONT_M.render(f"파괴 {b}%", True, BLACK)
    screen.blit(bsurf, (RIGHT_X + RIGHT_W - 30 - bsurf.get_width(), 155))

    if popup_timer > 0 and popup_text:
        box = pygame.Rect(RIGHT_X + 40, 270, RIGHT_W - 80, 170)
        pygame.draw.rect(screen, WHITE, box, border_radius=18)
        pygame.draw.rect(screen, BLACK, box, 2, border_radius=18)

        t = FONT_POP.render(popup_text, True, RED)
        screen.blit(t, (box.centerx - t.get_width()//2, box.centery - t.get_height()//2))

    if game_state == "ending":
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        box = pygame.Rect(W//2 - 360, H//2 - 200, 720, 400)
        pygame.draw.rect(screen, WHITE, box, border_radius=24)
        pygame.draw.rect(screen, BLACK, box, 3, border_radius=24)

        y = box.y + 40
        for i, line in enumerate(ending_lines):
            font = FONT_L if i == 0 else FONT_M
            surf = font.render(line, True, BLACK)
            screen.blit(surf, (box.centerx - surf.get_width()//2, y))
            y += 55

    pygame.display.flip()

pygame.quit()
