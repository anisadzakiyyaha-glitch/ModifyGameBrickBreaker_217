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