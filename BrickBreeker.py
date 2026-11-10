import math
import os
import random
from array import array
from collections import deque

import pygame

# ---------------------------------------------------------------
# BRICK BREAKER - EDISI MODIFIKASI
# Dasar: game Brick Breaker (pygame) dari GeeksforGeeks
# ---------------------------------------------------------------

try:
    pygame.mixer.init(22050, -16, 1, 512, allowedchanges=0)
except Exception:
    pass
pygame.init()

WIDTH, HEIGHT = 800, 600
FPS = 60
HUD_H = 44
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.txt")

# warna
BG_TOP = (10, 8, 30)
BG_BOTTOM = (38, 12, 70)
WHITE = (255, 255, 255)
CYAN = (80, 225, 255)
PINK = (255, 110, 200)
GREEN = (80, 235, 140)
ORANGE = (255, 160, 60)
RED = (255, 90, 110)
YELLOW = (255, 215, 80)
PURPLE = (190, 120, 255)
STEEL = (140, 150, 175)
HP_COLORS = {1: GREEN, 2: YELLOW, 3: RED}

# jenis power-up: huruf -> (warna, tulisan popup)
POWER_INFO = {
    "W": (CYAN, "PAPAN LEBAR"),
    "M": (PINK, "MULTI BOLA"),
    "S": (GREEN, "BOLA LAMBAT"),
    "F": (ORANGE, "BOLA API"),
    "N": (RED, "+1 NYAWA"),
}

# pola balok tiap level: angka = nyawa balok, B = balok bonus (pasti jatuhin power-up),
# S = balok baja (nggak bisa hancur), titik = kosong
LAYOUTS = [
    ["222222222222",
     "111111111111",
     "11B11111B111",
     "111111111111"],

    ["....1111....",
     "...122221...",
     "..12333321..",
     ".1233BB3321.",
     "112333333211"],

    ["S1212121212S",
     "1.3.1.B.1.3.",
     "212121212121",
     ".3.3.3.3.3.3",
     "S2S2S2S2S2S2"],

    ["333333333333",
     "3..........3",
     "3.22222222.3",
     "3.2.B11B.2.3",
     "3.22222222.3",
     "3..........3"],

    ["33S33333S333",
     "222222222222",
     "1S11B11B11S1",
     "111111111111"],
]

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Brick Breaker - Edisi Modifikasi")
clock = pygame.time.Clock()

FONT_S = pygame.font.Font(None, 22)
FONT_M = pygame.font.Font(None, 32)
FONT_L = pygame.font.Font(None, 72)


# ---------------------------------------------------------------
# fungsi bantu
# ---------------------------------------------------------------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def mix(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def text(surf, msg, font, color, center, shadow=True):
    if shadow:
        sh = font.render(msg, True, (0, 0, 0))
        surf.blit(sh, sh.get_rect(center=(center[0] + 2, center[1] + 2)))
    img = font.render(msg, True, color)
    surf.blit(img, img.get_rect(center=center))


_glow_cache = {}


def glow(radius, color):
    key = (radius, color)
    if key not in _glow_cache:
        s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for i in range(radius, 0, -2):
            a = int(120 * (1 - i / radius) ** 2)
            pygame.draw.circle(s, (*color, a), (radius, radius), i)
        _glow_cache[key] = s
    return _glow_cache[key]


def draw_heart(surf, cx, cy, size, color):
    r = size // 2
    pygame.draw.circle(surf, color, (cx - r, cy - r // 2), r)
    pygame.draw.circle(surf, color, (cx + r, cy - r // 2), r)
    pygame.draw.polygon(surf, color, [(cx - 2 * r, cy - r // 4), (cx + 2 * r, cy - r // 4), (cx, cy + 2 * r)])


def load_high():
    try:
        with open(SAVE_FILE) as f:
            return int(f.read().strip())
    except Exception:
        return 0


def save_high(value):
    try:
        with open(SAVE_FILE, "w") as f:
            f.write(str(value))
    except Exception:
        pass


# ---------------------------------------------------------------
# suara (dibuat sendiri pakai gelombang sinus, jadi nggak butuh file audio)
# ---------------------------------------------------------------
def make_tone(freq, ms, vol=0.3, end_freq=None):
    sr = 22050
    n = int(sr * ms / 1000)
    end_freq = end_freq or freq
    buf = array("h")
    phase = 0.0
    for i in range(n):
        f = freq + (end_freq - freq) * i / n
        phase += 2 * math.pi * f / sr
        buf.append(int(math.sin(phase) * (1 - i / n) * vol * 32767))
    return pygame.mixer.Sound(buffer=buf.tobytes())


sounds = {}
if pygame.mixer.get_init():
    try:
        sounds = {
            "wall": make_tone(300, 60),
            "paddle": make_tone(420, 80),
            "hit": make_tone(520, 70),
            "break": make_tone(700, 120, end_freq=300),
            "steel": make_tone(200, 60, vol=0.4),
            "power": make_tone(500, 250, end_freq=1000),
            "lose": make_tone(400, 500, vol=0.4, end_freq=80),
            "clear": make_tone(500, 600, end_freq=1200),
        }
    except Exception:
        sounds = {}


def play(name):
    s = sounds.get(name)
    if s:
        s.play()


# ---------------------------------------------------------------
# objek-objek game
# ---------------------------------------------------------------
class Paddle:
    def __init__(self):
        self.base_w = 110
        self.w = self.base_w
        self.h = 14
        self.x = WIDTH / 2 - self.w / 2
        self.y = HEIGHT - 44
        self.speed = 9

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), int(self.w), self.h)

    def move(self, direction):
        self.x = clamp(self.x + direction * self.speed, 0, WIDTH - self.w)

    def set_center(self, cx):
        self.x = clamp(cx - self.w / 2, 0, WIDTH - self.w)

    def set_width(self, w):
        center = self.x + self.w / 2
        self.w = w
        self.set_center(center)

    def draw(self, surf):
        r = self.rect
        surf.blit(glow(60, CYAN), (r.centerx - 60, r.centery - 60))
        pygame.draw.rect(surf, CYAN, r, border_radius=7)
        pygame.draw.rect(surf, (200, 245, 255), (r.x + 6, r.y + 2, r.w - 12, 4), border_radius=3)


class Ball:
    def __init__(self, x, y, stuck=True):
        self.x, self.y = x, y
        self.vx, self.vy = 0.0, -1.0
        self.r = 8
        self.stuck = stuck
        self.trail = deque(maxlen=12)

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.r), int(self.y - self.r), self.r * 2, self.r * 2)

    def set_speed(self, speed):
        mag = math.hypot(self.vx, self.vy) or 1
        self.vx, self.vy = self.vx / mag * speed, self.vy / mag * speed

    def rotate(self, degrees):
        a = math.radians(degrees)
        self.vx, self.vy = (self.vx * math.cos(a) - self.vy * math.sin(a),
                            self.vx * math.sin(a) + self.vy * math.cos(a))


class Brick:
    def __init__(self, x, y, w, h, kind, hp):
        self.rect = pygame.Rect(x, y, w, h)
        self.kind = kind          # normal, bonus, steel
        self.hp = hp
        self.max_hp = hp
        self.flash = 0

    @property
    def color(self):
        if self.kind == "steel":
            return STEEL
        if self.kind == "bonus":
            return PURPLE
        return HP_COLORS[max(1, self.hp)]

    def draw(self, surf, tick):
        col = self.color
        if self.kind == "bonus":
            col = mix(PURPLE, WHITE, (math.sin(tick * 0.12) + 1) * 0.2)
        if self.flash > 0:
            col = mix(col, WHITE, self.flash / 6)
        r = self.rect
        pygame.draw.rect(surf, col, r, border_radius=4)
        pygame.draw.rect(surf, mix(col, WHITE, 0.45), (r.x + 3, r.y + 2, r.w - 6, 5), border_radius=3)
        pygame.draw.rect(surf, mix(col, (0, 0, 0), 0.45), r, 2, border_radius=4)
        if self.kind == "steel":
            for px in (r.x + 6, r.right - 7):
                pygame.draw.circle(surf, (90, 95, 115), (px, r.centery), 2)
        elif self.kind == "bonus":
            text(surf, "?", FONT_S, WHITE, r.center, shadow=False)


class PowerUp:
    def __init__(self, x, y, kind):
        self.x, self.y = x, y
        self.kind = kind

    @property
    def rect(self):
        return pygame.Rect(int(self.x - 17), int(self.y - 10), 34, 20)

    def draw(self, surf):
        color = POWER_INFO[self.kind][0]
        r = self.rect
        surf.blit(glow(26, color), (r.centerx - 26, r.centery - 26))
        pygame.draw.rect(surf, color, r, border_radius=10)
        pygame.draw.rect(surf, WHITE, r, 2, border_radius=10)
        text(surf, self.kind, FONT_S, (20, 20, 40), r.center, shadow=False)


# ---------------------------------------------------------------
# pengatur game
# ---------------------------------------------------------------
class Game:
    def __init__(self):
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.bg = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            pygame.draw.line(self.bg, mix(BG_TOP, BG_BOTTOM, y / HEIGHT), (0, y), (WIDTH, y))
        self.stars = [[random.uniform(0, WIDTH), random.uniform(0, HEIGHT),
                       random.uniform(0.2, 1.2), random.randint(1, 2)] for _ in range(70)]
        self.high = load_high()
        self.tick = 0
        self.state = "menu"
        self.reset()

    # ---------- pengaturan awal ----------
    def reset(self):
        self.score = 0
        self.lives = 3
        self.level = 1
        self.combo = 1
        self.shake = 0
        self.clear_timer = 0
        self.paddle = Paddle()
        self.particles = []
        self.popups = []
        self.start_level()

    def start_level(self):
        self.bricks = self.build_level(self.level)
        self.powerups = []
        self.effects = {"W": 0, "S": 0, "F": 0}
        self.paddle.set_width(self.paddle.base_w)
        self.new_ball()

    def new_ball(self):
        self.balls = [Ball(self.paddle.x + self.paddle.w / 2, self.paddle.y - 9)]

    def build_level(self, level):
        rows = LAYOUTS[(level - 1) % len(LAYOUTS)]
        extra_hp = (level - 1) // len(LAYOUTS)
        bw, bh, gap = 56, 22, 4
        sx = (WIDTH - (12 * bw + 11 * gap)) // 2
        sy = HUD_H + 50
        bricks = []
        for r, line in enumerate(rows):
            for c, ch in enumerate(line):
                if ch == ".":
                    continue
                x = sx + c * (bw + gap)
                y = sy + r * (bh + gap)
                if ch == "S":
                    bricks.append(Brick(x, y, bw, bh, "steel", 99))
                elif ch == "B":
                    bricks.append(Brick(x, y, bw, bh, "bonus", 1))
                else:
                    bricks.append(Brick(x, y, bw, bh, "normal", min(3, int(ch) + extra_hp)))
        return bricks

    def base_speed(self):
        return min(5.5 + 0.45 * (self.level - 1), 9.5)

    # ---------- efek visual ----------
    def burst(self, x, y, color, n=14, power=4):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(1, power)
            life = random.randint(20, 40)
            self.particles.append([x, y, math.cos(a) * s, math.sin(a) * s, life, life, color, random.randint(2, 4)])

    def popup(self, msg, x, y, color):
        self.popups.append([msg, x, y, 60, color])

    # ---------- aksi ----------
    def launch(self):
        for b in self.balls:
            if b.stuck:
                b.stuck = False
                b.vx = random.uniform(-0.5, 0.5)
                b.vy = -1
                b.set_speed(self.base_speed())

    def apply_power(self, kind):
        play("power")
        self.popup(POWER_INFO[kind][1], self.paddle.x + self.paddle.w / 2, self.paddle.y - 20, POWER_INFO[kind][0])
        if kind == "W":
            self.effects["W"] = 600
            self.paddle.set_width(self.paddle.base_w * 1.6)
        elif kind == "S":
            self.effects["S"] = 480
        elif kind == "F":
            self.effects["F"] = 360
        elif kind == "N":
            self.lives = min(5, self.lives + 1)
        elif kind == "M":
            moving = [b for b in self.balls if not b.stuck]
            if moving:
                src = moving[0]
                for deg in (-25, 25):
                    nb = Ball(src.x, src.y, stuck=False)
                    nb.vx, nb.vy = src.vx, src.vy
                    nb.rotate(deg)
                    self.balls.append(nb)

    def destroy_brick(self, brick):
        self.score += 10 * brick.max_hp * self.combo
        self.combo = min(self.combo + 1, 8)
        self.burst(brick.rect.centerx, brick.rect.centery, brick.color)
        self.shake = max(self.shake, 4)
        play("break")
        if brick.kind == "bonus" or random.random() < 0.12:
            kind = random.choices(list(POWER_INFO), weights=[3, 3, 3, 2, 1])[0]
            self.powerups.append(PowerUp(brick.rect.centerx, brick.rect.centery, kind))

    def lose_life(self):
        self.lives -= 1
        self.combo = 1
        self.shake = 20
        play("lose")
        self.effects = {"W": 0, "S": 0, "F": 0}
        self.paddle.set_width(self.paddle.base_w)
        if self.lives <= 0:
            self.state = "gameover"
            if self.score > self.high:
                self.high = self.score
                save_high(self.high)
        else:
            self.new_ball()

    # ---------- update ----------
    def update_ball(self, ball):
        p = self.paddle
        if ball.stuck:
            ball.x = p.x + p.w / 2
            ball.y = p.y - ball.r - 1
            return

        speed = self.base_speed() * (0.7 if self.effects["S"] > 0 else 1)
        ball.set_speed(speed)
        # jaga supaya bola nggak terlalu datar
        if abs(ball.vy) < speed * 0.3:
            ball.vy = math.copysign(speed * 0.3, ball.vy or -1)
            ball.set_speed(speed)

        ball.trail.append((ball.x, ball.y))
        ball.x += ball.vx
        ball.y += ball.vy

        # dinding
        if ball.x <= ball.r:
            ball.x, ball.vx = ball.r, abs(ball.vx)
            play("wall")
        elif ball.x >= WIDTH - ball.r:
            ball.x, ball.vx = WIDTH - ball.r, -abs(ball.vx)
            play("wall")
        if ball.y <= HUD_H + ball.r:
            ball.y, ball.vy = HUD_H + ball.r, abs(ball.vy)
            play("wall")

        # papan: sudut pantulan tergantung bagian papan yang kena
        pr = p.rect
        if ball.vy > 0 and ball.rect.colliderect(pr) and ball.y < pr.bottom:
            off = clamp((ball.x - pr.centerx) / (pr.w / 2), -1, 1)
            ang = off * math.radians(60) + math.radians(random.uniform(-4, 4))
            sp = math.hypot(ball.vx, ball.vy)
            ball.vx, ball.vy = sp * math.sin(ang), -sp * math.cos(ang)
            ball.y = pr.top - ball.r - 1
            self.combo = 1
            self.burst(ball.x, pr.top, CYAN, n=5, power=2)
            play("paddle")

        self.hit_bricks(ball)

    def hit_bricks(self, ball):
        fire = self.effects["F"] > 0
        br = ball.rect
        for brick in self.bricks:
            if brick.hp <= 0 or not br.colliderect(brick.rect):
                continue
            if fire and brick.kind != "steel":
                brick.hp = 0
                self.destroy_brick(brick)
                continue

            # pantul: tentukan dari sisi mana bola menabrak
            ox = min(br.right - brick.rect.left, brick.rect.right - br.left)
            oy = min(br.bottom - brick.rect.top, brick.rect.bottom - br.top)
            if ox < oy:
                ball.vx = -abs(ball.vx) if ball.x < brick.rect.centerx else abs(ball.vx)
                ball.x += -ox if ball.x < brick.rect.centerx else ox
            else:
                ball.vy = -abs(ball.vy) if ball.y < brick.rect.centery else abs(ball.vy)
                ball.y += -oy if ball.y < brick.rect.centery else oy

            if brick.kind == "steel":
                brick.flash = 6
                play("steel")
            else:
                brick.hp -= 1
                brick.flash = 6
                if brick.hp <= 0:
                    self.destroy_brick(brick)
                else:
                    self.score += 5
                    play("hit")
            break
        self.bricks = [b for b in self.bricks if b.hp > 0]

    def update_playing(self):
        keys = pygame.key.get_pressed()
        direction = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        if direction:
            self.paddle.move(direction)

        for k in self.effects:
            if self.effects[k] > 0:
                self.effects[k] -= 1
                if k == "W" and self.effects[k] == 0:
                    self.paddle.set_width(self.paddle.base_w)

        for ball in self.balls:
            self.update_ball(ball)
        self.balls = [b for b in self.balls if b.y < HEIGHT + 20]
        if not self.balls:
            self.lose_life()
            return

        for pu in self.powerups:
            pu.y += 3
        caught = [pu for pu in self.powerups if pu.rect.colliderect(self.paddle.rect)]
        for pu in caught:
            self.apply_power(pu.kind)
        self.powerups = [pu for pu in self.powerups if pu not in caught and pu.y < HEIGHT + 20]

        if not any(b.kind != "steel" for b in self.bricks):
            self.state = "levelclear"
            self.clear_timer = 120
            self.score += 100 * self.level
            play("clear")

    def update(self):
        self.tick += 1
        for s in self.stars:
            s[1] += s[2]
            if s[1] > HEIGHT:
                s[0], s[1] = random.uniform(0, WIDTH), 0

        for b in self.bricks:
            if b.flash > 0:
                b.flash -= 1
        for pt in self.particles:
            pt[0] += pt[2]
            pt[1] += pt[3]
            pt[3] += 0.12
            pt[4] -= 1
        self.particles = [pt for pt in self.particles if pt[4] > 0]
        for po in self.popups:
            po[2] -= 0.8
            po[3] -= 1
        self.popups = [po for po in self.popups if po[3] > 0]
        if self.shake > 0:
            self.shake -= 1

        if self.state == "playing":
            self.update_playing()
        elif self.state == "levelclear":
            self.clear_timer -= 1
            if self.clear_timer <= 0:
                self.level += 1
                self.start_level()
                self.state = "playing"

   