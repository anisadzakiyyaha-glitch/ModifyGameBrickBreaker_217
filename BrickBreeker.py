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


