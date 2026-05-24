"""
Chapter 1 — Acoustic Archive corridor.
Theme: smuggler's tunnel under a record shop / unlicensed broadcast hideout.
"""
from __future__ import annotations
import math
import random
import pygame

from delivery.corridor.elements import (
    Platform, MovingPlatform, Hazard, MovingHazard, Ladder,
    NPCEncounter, Collectible, Secret, Checkpoint, BossRoomTrigger,
    CORRIDOR_W, CORRIDOR_H, FLOOR_Y, CEIL_Y, PLAYER_H,
)
from delivery.corridor.base import Room, Corridor, STAR_3_TIME, STAR_2_TIME

# Palette — warm oranges/reds/dark brutalist
_PAL_R1 = {
    "bg":            (12,  6,  14),
    "grid":          (40, 20,  50),
    "ceiling_fill":  (30, 12,  40),
    "ceiling_line":  (255, 80,  200),
    "floor_fill":    (22, 10,  28),
    "floor_line":    (255, 120,  60),
    "platform":      (120, 50, 10),
    "platform_hi":   (200, 90, 20),
    "brick":         (160, 60,  20),
    "brick_hi":      (255, 180,  70),
    "light":         (255, 140,  80),
}
_PAL_R2 = {
    "bg":            (8,  4,  8),
    "grid":          (22, 10, 18),
    "ceiling_fill":  (20,  8, 16),
    "ceiling_line":  (200, 80, 180),
    "floor_fill":    (16,  6, 14),
    "floor_line":    (180, 60, 160),
    "platform":      (100, 30, 80),
    "platform_hi":   (180, 70, 160),
    "ladder":        (160, 80, 30),
    "light":         (180, 60, 160),
}
_PAL_R3 = {
    "bg":            (12,  6,  4),
    "grid":          (28, 14, 10),
    "ceiling_fill":  (24, 12,  8),
    "ceiling_line":  (255, 140, 0),
    "floor_fill":    (20,  10,  6),
    "floor_line":    (220, 120, 0),
    "platform":      (160, 80, 20),
    "platform_hi":   (255, 160, 40),
    "light":         (255, 140, 0),
}


def _bg_r1(surf, camera_x, t, pal):
    """Loading dock — crane hooks, vinyl records, neon signs, speaker cones, propaganda."""
    bg_off = camera_x * 0.45
    f8 = pygame.font.SysFont("monospace", 8)

    # ── Deep purple brick wall texture ───────────────────────────────────
    brick_off = int(camera_x * 0.15) % 40
    for brow in range(2):
        by = CEIL_Y + 2 + brow * 40
        row_off = (brow * 20 - brick_off) % 40
        for bx in range(-row_off, CORRIDOR_W + 40, 40):
            pygame.draw.rect(surf, (28, 12, 36), (bx, by, 38, 18))
            pygame.draw.rect(surf, (50, 22, 62), (bx, by, 38, 18), 1)

    # ── Overhead crane rail ──────────────────────────────────────────────
    pygame.draw.line(surf, (100, 55, 15), (0, CEIL_Y + 6), (CORRIDOR_W, CEIL_Y + 6), 5)
    pygame.draw.line(surf, (180, 100, 30), (0, CEIL_Y + 7), (CORRIDOR_W, CEIL_Y + 7), 1)

    # ── Crane hooks (keep) ───────────────────────────────────────────────
    for wx in range(200, 3200, 320):
        sx = int(wx - bg_off) % (CORRIDOR_W + 120) - 60
        hy = CEIL_Y + 6 + int(18 * abs(math.sin(t * 0.28 + wx * 0.0013)))
        pygame.draw.line(surf, (120, 65, 18), (sx, CEIL_Y + 6), (sx, hy), 2)
        pygame.draw.line(surf, (180, 90, 25), (sx - 8, hy), (sx + 8, hy), 3)
        pygame.draw.line(surf, (180, 90, 25), (sx - 8, hy), (sx - 2, hy + 11), 2)
        pygame.draw.line(surf, (180, 90, 25), (sx + 8, hy), (sx + 2, hy + 11), 2)
        # Hook tip highlight
        pygame.draw.circle(surf, (255, 160, 40), (sx, hy + 11), 2)

    # ── Vinyl records on wall ────────────────────────────────────────────
    record_data = [
        (280,  (220, 60, 255), 28),
        (650,  (255, 130, 20), 32),
        (1100, (255, 40,  140), 26),
        (1550, (255, 200, 0),  30),
        (1950, (180, 80,  255), 28),
    ]
    for wx, col, r in record_data:
        sx = int(wx - bg_off * 0.55)
        if -70 < sx < CORRIDOR_W + 70:
            cy = CEIL_Y + 32
            # Vinyl body
            pygame.draw.circle(surf, (14, 6, 18), (sx, cy), r)
            pygame.draw.circle(surf, col, (sx, cy), r, 3)
            # Groove rings
            for gr in [int(r * 0.72), int(r * 0.52), int(r * 0.30)]:
                dim = tuple(max(0, c // 4) for c in col)
                pygame.draw.circle(surf, dim, (sx, cy), gr, 1)
            # Center label (bright filled)
            lab_r = max(4, r // 5)
            pygame.draw.circle(surf, col, (sx, cy), lab_r)
            pygame.draw.circle(surf, (255, 255, 255), (sx, cy), max(1, lab_r - 2))
            # Outer glow (SRCALPHA)
            glow_s = pygame.Surface((r * 2 + 10, r * 2 + 10), pygame.SRCALPHA)
            ga = int(18 + 10 * math.sin(t * 1.5 + wx * 0.004))
            pygame.draw.circle(glow_s, (*col, ga), (r + 5, r + 5), r + 4)
            surf.blit(glow_s, (sx - r - 5, cy - r - 5))

    # ── Speaker cones on wall ────────────────────────────────────────────
    for wx in range(500, 3200, 680):
        sx = int(wx - bg_off * 0.5) % (CORRIDOR_W + 140) - 70
        cy2 = FLOOR_Y - 42
        # Mounting plate
        pygame.draw.rect(surf, (40, 18, 10), (sx - 24, cy2 - 24, 48, 48))
        pygame.draw.rect(surf, (120, 60, 15), (sx - 24, cy2 - 24, 48, 48), 1)
        # Speaker cone (filled dark + rim)
        pygame.draw.circle(surf, (30, 14, 6), (sx, cy2), 20)
        pygame.draw.circle(surf, (200, 100, 20), (sx, cy2), 20, 2)
        pygame.draw.circle(surf, (160, 80, 15), (sx, cy2), 14, 1)
        # Radiating spokes
        for spoke_a in range(0, 360, 45):
            rad = math.radians(spoke_a)
            pygame.draw.line(surf, (120, 60, 12),
                             (sx, cy2),
                             (sx + int(17 * math.cos(rad)), cy2 + int(17 * math.sin(rad))), 1)
        pygame.draw.circle(surf, (255, 140, 20), (sx, cy2), 5)
        pygame.draw.circle(surf, (255, 220, 80), (sx, cy2), 2)
        # Pulsing LED indicator
        led_bright = int(180 + 60 * math.sin(t * 3.5 + wx * 0.007))
        pygame.draw.circle(surf, (led_bright, 20, 20), (sx + 22, cy2 - 22), 3)

    # ── NEON signs with glow box ─────────────────────────────────────────
    sign_data = [
        (200,  "NOISE IS ILLEGAL",  (255, 30,  120)),
        (900,  "DEAD FREQUENCIES",  (255, 160, 0)),
        (1500, "LOCAL 404",         (200, 50,  220)),
        (2100, "FREE THE ARCHIVE",  (0,   220, 200)),
    ]
    for wx, text, col in sign_data:
        sx = int(wx - bg_off * 0.55)
        if -170 < sx < CORRIDOR_W + 30:
            tw = len(text) * 7
            flicker = math.sin(t * 7.3 + wx * 0.011)
            glow_a = int(50 + 40 * abs(math.sin(t * 2.1 + wx * 0.003)))
            if flicker > 0.92:
                glow_a = max(0, glow_a - 40)  # occasional flicker dim
            # Wide glow halo
            halo = pygame.Surface((tw + 28, 26), pygame.SRCALPHA)
            halo.fill((*col, glow_a // 2))
            surf.blit(halo, (sx - 14, CEIL_Y + 52))
            # Bright inner glow
            gw = pygame.Surface((tw + 14, 18), pygame.SRCALPHA)
            gw.fill((*col, glow_a))
            surf.blit(gw, (sx - 7, CEIL_Y + 56))
            # Border rect
            pygame.draw.rect(surf, col, (sx - 7, CEIL_Y + 56, tw + 14, 18), 2)
            # Sign text
            s = f8.render(text, True, (255, 255, 255))
            surf.blit(s, (sx, CEIL_Y + 60))

    # ── Propaganda posters (vivid, colored, large) ───────────────────────
    poster_data = [
        (320,  "DEBT IS IDENTITY",    (140, 18, 6),   (255, 70,  20)),
        (780,  "REPORT COURIERS",     (18, 55, 8),    (60,  220, 30)),
        (1320, "STAY COMPLIANT",      (8,  22, 90),   (30,  100, 255)),
        (1820, "LOCAL 404 PROTECTS",  (70, 8,  55),   (240, 30,  200)),
    ]
    for wx, text, bg_col, fg_col in poster_data:
        sx = int(wx - bg_off)
        if -140 < sx < CORRIDOR_W + 30:
            # Poster body (taller, wider)
            pygame.draw.rect(surf, bg_col, (sx, FLOOR_Y - 46, 116, 34))
            pygame.draw.rect(surf, fg_col, (sx, FLOOR_Y - 46, 116, 34), 2)
            # Header bar
            pygame.draw.rect(surf, fg_col, (sx, FLOOR_Y - 46, 116, 9))
            # Text
            ts = f8.render(text, True, fg_col)
            surf.blit(ts, (sx + 4, FLOOR_Y - 34))
            # Star mark in header
            pygame.draw.circle(surf, bg_col, (sx + 6, FLOOR_Y - 41), 3)


def _bg_r2(surf, camera_x, t, pal):
    """Employee corridor — vivid band posters, surveillance cam, graffiti, waveform."""
    bg_off = camera_x * 0.5
    f8 = pygame.font.SysFont("monospace", 8)
    f7 = pygame.font.SysFont("monospace", 7)
    bands = ["THE NULL SETS", "VOID UNION", "LOCAL STATIC", "ARCHIVE RATS",
             "BARGE CHASERS", "CLONEWAVE", "NOISE OF 404", "FEEDBACK LOOP"]
    poster_cols = [(220, 60, 200), (60, 220, 160), (220, 150, 0), (0, 200, 230),
                   (255, 60, 80), (80, 255, 120), (255, 200, 0), (200, 80, 255)]

    # ── Dark corridor paneling ────────────────────────────────────────────
    panel_off = int(camera_x * 0.12) % 80
    for px in range(-panel_off, CORRIDOR_W + 80, 80):
        pygame.draw.line(surf, (35, 15, 30), (px, CEIL_Y + 2), (px, FLOOR_Y - 2), 1)
    pygame.draw.line(surf, (55, 25, 50), (0, CEIL_Y + 14), (CORRIDOR_W, CEIL_Y + 14), 1)
    pygame.draw.line(surf, (55, 25, 50), (0, FLOOR_Y - 14), (CORRIDOR_W, FLOOR_Y - 14), 1)

    # ── Neon band posters with vivid glow rects ───────────────────────────
    for i, wx in enumerate(range(120, 2800, 310)):
        sx = int(wx - bg_off)
        if -120 < sx < CORRIDOR_W + 30:
            col = poster_cols[i % len(poster_cols)]
            pw, ph = 100, 34
            # Wide outer glow
            outer = pygame.Surface((pw + 20, ph + 20), pygame.SRCALPHA)
            outer.fill((*col, 22))
            surf.blit(outer, (sx - 10, FLOOR_Y - ph - 14))
            # Inner glow
            inner = pygame.Surface((pw + 8, ph + 8), pygame.SRCALPHA)
            inner.fill((*col, 45))
            surf.blit(inner, (sx - 4, FLOOR_Y - ph - 8))
            # Poster body
            pygame.draw.rect(surf, tuple(max(0, c // 5) for c in col), (sx, FLOOR_Y - ph - 4, pw, ph))
            pygame.draw.rect(surf, col, (sx, FLOOR_Y - ph - 4, pw, ph), 2)
            # Top accent stripe
            pygame.draw.rect(surf, col, (sx, FLOOR_Y - ph - 4, pw, 8))
            # Band name (in body)
            s = f8.render(bands[i % len(bands)], True, col)
            surf.blit(s, (sx + 4, FLOOR_Y - ph + 6))
            # Sub-line
            sub = f7.render("LIVE  ONE NIGHT ONLY", True, tuple(max(0, c // 2) for c in col))
            surf.blit(sub, (sx + 4, FLOOR_Y - ph + 17))

    # ── Surveillance cameras on wall brackets ────────────────────────────
    for wx in range(420, 2800, 750):
        sx = int(wx - bg_off * 0.42)
        if -50 < sx < CORRIDOR_W + 50:
            # Bracket: ceiling mount arm
            pygame.draw.line(surf, (70, 45, 70), (sx, CEIL_Y + 2), (sx, CEIL_Y + 16), 4)
            pygame.draw.line(surf, (70, 45, 70), (sx, CEIL_Y + 16), (sx + 14, CEIL_Y + 22), 3)
            # Camera body
            pygame.draw.rect(surf, (36, 26, 42), (sx + 12, CEIL_Y + 18, 22, 12))
            pygame.draw.rect(surf, (110, 80, 120), (sx + 12, CEIL_Y + 18, 22, 12), 1)
            # Lens assembly
            pygame.draw.circle(surf, (6, 4, 14), (sx + 24, CEIL_Y + 24), 5)
            pygame.draw.circle(surf, (100, 70, 120), (sx + 24, CEIL_Y + 24), 5, 1)
            pygame.draw.circle(surf, (60, 40, 80), (sx + 24, CEIL_Y + 24), 2)
            # Red LED blink (faster, more paranoid)
            led_phase = math.sin(t * 3.0 + wx * 0.013)
            if led_phase > 0.1:
                led_bright = int(200 + 55 * led_phase)
                pygame.draw.circle(surf, (led_bright, 20, 20), (sx + 14, CEIL_Y + 20), 2)
                # Small glow around LED
                led_glow = pygame.Surface((8, 8), pygame.SRCALPHA)
                pygame.draw.circle(led_glow, (255, 0, 0, 40), (4, 4), 4)
                surf.blit(led_glow, (sx + 10, CEIL_Y + 16))

    # ── Graffiti text (spray-style, double-drawn for fuzz) ────────────────
    graffiti = [
        (230,  "LOCAL 404 OUT",      (140, 40,  100)),
        (650,  "FREE THE ARCHIVE",   (80,  140, 40)),
        (1080, "NO DEBT NO CHAINS",  (120, 90,  30)),
        (1540, "UNION LIES",         (100, 30,  80)),
        (1980, "LOCAL 404 OUT",      (110, 35,  90)),
    ]
    for wx, text, col in graffiti:
        sx = int(wx - bg_off * 0.58)
        if -160 < sx < CORRIDOR_W + 30:
            s = f8.render(text, True, col)
            # Triple-draw slight offsets for spray effect
            surf.blit(s, (sx - 1, FLOOR_Y - 54))
            surf.blit(s, (sx + 1, FLOOR_Y - 52))
            surf.blit(s, (sx,     FLOOR_Y - 53))
            # Optional underline scratch
            pygame.draw.line(surf, tuple(max(0, c - 40) for c in col),
                             (sx, FLOOR_Y - 51), (sx + len(text) * 7, FLOOR_Y - 51), 1)

    # ── Sound waveform on wall mid-height (dual wave) ─────────────────────
    mid_y = (CEIL_Y + FLOOR_Y) // 2
    wave_off = camera_x * 0.35
    pts1, pts2 = [], []
    for px in range(0, CORRIDOR_W + 4, 3):
        wx2 = px + wave_off
        wy1 = mid_y + int(10 * math.sin(wx2 * 0.055 + t * 2.8))
        wy2 = mid_y + int(6  * math.sin(wx2 * 0.09  - t * 3.5 + 1.1))
        pts1.append((px, wy1))
        pts2.append((px, wy2))
    if len(pts1) >= 2:
        pygame.draw.lines(surf, (120, 40, 90), False, pts1, 1)
    if len(pts2) >= 2:
        pygame.draw.lines(surf, (80, 25, 60), False, pts2, 1)


def _bg_r3(surf, camera_x, t, pal):
    """Underground club — EQ bars, detailed crowd, DJ booth, spinning vinyl, warm light pools."""
    # ── Dramatic warm light cones from ceiling (spotlights) ───────────────
    spot_cols = [(255, 120, 0), (255, 60, 120), (255, 200, 0), (200, 80, 255)]
    for si, lx in enumerate(range(0, CORRIDOR_W, 95)):
        a = int(18 + 14 * math.sin(t * 0.65 + lx * 0.055 + si))
        lp = pygame.Surface((95, FLOOR_Y - CEIL_Y), pygame.SRCALPHA)
        sc = spot_cols[si % len(spot_cols)]
        lp.fill((*sc, a))
        surf.blit(lp, (lx, CEIL_Y))
        # Spotlight cone: bright top strip
        cone = pygame.Surface((12, FLOOR_Y - CEIL_Y), pygame.SRCALPHA)
        cone.fill((*sc, min(255, a * 3)))
        surf.blit(cone, (lx + 42, CEIL_Y))

    # ── DJ booth silhouette (left side, detailed) ─────────────────────────
    bx, by = 22, FLOOR_Y - 42
    # Booth body
    pygame.draw.rect(surf, (22, 10, 5), (bx, by, 94, 34))
    pygame.draw.rect(surf, (160, 70, 12), (bx, by, 94, 34), 2)
    # Booth face panel details
    pygame.draw.rect(surf, (40, 18, 6), (bx + 4, by + 6, 86, 20))
    for knob_x in range(bx + 10, bx + 88, 14):
        pygame.draw.circle(surf, (120, 60, 10), (knob_x, by + 16), 4)
        pygame.draw.circle(surf, (220, 110, 20), (knob_x, by + 16), 4, 1)
    # Two turntables on top
    for ti, tx in enumerate([bx + 22, bx + 68]):
        pygame.draw.circle(surf, (14, 6, 2), (tx, by - 8), 14)
        pygame.draw.circle(surf, (200, 100, 20), (tx, by - 8), 14, 2)
        for gr2 in [10, 6]:
            pygame.draw.circle(surf, (60, 30, 6), (tx, by - 8), gr2, 1)
        spin_a = t * (2.1 + ti * 0.25)
        if ti == 1:
            spin_a = -spin_a * 0.9
        pygame.draw.line(surf, (255, 176, 0),
                         (tx, by - 8),
                         (tx + int(11 * math.cos(spin_a)), by - 8 + int(11 * math.sin(spin_a))), 2)
        pygame.draw.circle(surf, (255, 200, 60), (tx, by - 8), 3)

    # ── Equalizer bars from floor (8 bars, pulses with sin) ───────────────
    eq_start_x = 170
    for i in range(8):
        bar_x = eq_start_x + i * 52
        phase = t * 3.0 + i * 0.82
        bar_h = int(6 + 44 * abs(math.sin(phase)))
        intensity = int(80 + 160 * abs(math.sin(phase)))
        # Color shifts red->orange->yellow with height
        heat = bar_h / 50.0
        col_eq = (min(255, intensity), min(255, int(intensity * heat * 0.6)), 0)
        # Bar body
        pygame.draw.rect(surf, col_eq, (bar_x - 11, FLOOR_Y - bar_h, 20, bar_h))
        # Glow overlay
        glow_s = pygame.Surface((26, bar_h + 6), pygame.SRCALPHA)
        glow_s.fill((*col_eq, 38))
        surf.blit(glow_s, (bar_x - 13, FLOOR_Y - bar_h - 3))
        # Peak indicator line
        if bar_h > 30:
            pygame.draw.rect(surf, (255, 255, 200), (bar_x - 11, FLOOR_Y - bar_h - 2, 20, 2))

    # ── Crowd silhouettes (head + torso + arms + bob, more people) ────────
    crowd_xs = [560, 598, 630, 662, 696, 726, 580, 648, 678]
    for i, cx in enumerate(crowd_xs):
        rng = random.Random(i * 23 + 7)
        bob = int(4 * math.sin(t * (1.4 + rng.random() * 0.6) + i * 1.1))
        dark = rng.randint(14, 32)
        col_c = (dark, dark // 2, dark // 4)
        ny = FLOOR_Y - 1
        # Legs
        pygame.draw.line(surf, col_c, (cx - 3, ny), (cx - 4, ny - 10 + bob), 2)
        pygame.draw.line(surf, col_c, (cx + 3, ny), (cx + 4, ny - 10 + bob), 2)
        # Torso
        pygame.draw.rect(surf, col_c, (cx - 5, ny - 22 + bob, 10, 13))
        # Head
        pygame.draw.circle(surf, col_c, (cx, ny - 30 + bob), 7)
        # Left arm
        arm_sw = math.sin(t * 1.7 + i * 1.2) * 0.5
        pygame.draw.line(surf, col_c,
                         (cx - 5, ny - 18 + bob),
                         (cx - 12 + int(3 * math.sin(arm_sw)), ny - 12 + bob + int(5 * math.cos(arm_sw))), 2)
        # Right arm — raised rave pose
        raise_ph = math.sin(t * 1.3 + i * 0.85)
        arm_rise = int(8 * (0.5 + 0.5 * raise_ph))
        pygame.draw.line(surf, col_c,
                         (cx + 5, ny - 18 + bob),
                         (cx + 13, ny - 26 + bob - arm_rise), 2)

    # ── Spinning vinyl art on wall (right side) ───────────────────────────
    vx, vy = CORRIDOR_W - 55, CEIL_Y + 34
    spin = t * 1.6
    # Outer glow
    vg = pygame.Surface((72, 72), pygame.SRCALPHA)
    ga_v = int(30 + 15 * math.sin(t * 0.9))
    pygame.draw.circle(vg, (255, 140, 0, ga_v), (36, 36), 34)
    surf.blit(vg, (vx - 36, vy - 36))
    pygame.draw.circle(surf, (18, 8, 4), (vx, vy), 28)
    pygame.draw.circle(surf, (220, 110, 20), (vx, vy), 28, 3)
    for gr in [22, 15, 9]:
        pygame.draw.circle(surf, (70, 35, 8), (vx, vy), gr, 1)
    # Rotating radius line (tonearm position indicator)
    pygame.draw.line(surf, (255, 200, 0),
                     (vx, vy),
                     (vx + int(24 * math.cos(spin)), vy + int(24 * math.sin(spin))), 2)
    pygame.draw.circle(surf, (255, 220, 80), (vx, vy), 5)
    pygame.draw.circle(surf, (255, 255, 200), (vx, vy), 2)


# NPC responses
_KENJI_RESPONSES = [
    {
        "keywords": ["hello", "hi", "hey", "yo", "sup", "greet", "what"],
        "credits":  400,
        "lore":     "MARROW says hi. Says you owe him a favor still.",
        "outcome":  "reward",
    },
    {
        "keywords": [],  # fallback
        "credits":  0,
        "lore":     "",
        "outcome":  "pass",
    },
]

_GARY_RESPONSES = [
    {
        "keywords": ["forget", "know", "happen", "delivery", "done", "here"],
        "credits":  0,
        "lore":     "Gary nods. Off-duty Gary. He won't tell anyone.",
        "outcome":  "reward",
    },
    {
        "keywords": [],
        "credits":  0,
        "lore":     "",
        "outcome":  "pass",
    },
]


def build() -> Corridor:
    # ── Room 1: DOCK ACCESS — SUB-LEVEL 3 ──────────────────────────────
    r1_len  = 1000
    r1_elms = [
        # Hazard floor section (exposed cable)
        Hazard(350, FLOOR_Y - 10, 80, 10, "LIVE CABLE"),
        Hazard(600, FLOOR_Y - 10, 80, 10, "LIVE CABLE"),
        # Platforms over hazards
        Platform(350, FLOOR_Y - 60, 80),
        Platform(600, FLOOR_Y - 55, 80),
        Platform(800, FLOOR_Y - 50, 80),
        # Moving platform over wider gap
        MovingPlatform(500, FLOOR_Y - 80, left=440, right=560, speed=50),
        # Collectibles — 4 on path
        Collectible(260, FLOOR_Y - 20, 200),
        Collectible(450, FLOOR_Y - 95, 200),
        Collectible(620, FLOOR_Y - 70, 200),
        Collectible(800, FLOOR_Y - 65, 200),
        # 1 collectible on higher detour platform
        Platform(700, FLOOR_Y - 110, 60, path_tag=None),
        Collectible(700, FLOOR_Y - 130, 300),
        # Checkpoint
        Checkpoint(920),
    ]
    room1 = Room(
        length      = r1_len,
        palette     = _PAL_R1,
        elements    = r1_elms,
        bg_draw_fn  = _bg_r1,
        bax_enter_line = "Right. We're in the tunnels. Music industry's gone underground. Literally. Don't get crushed by anything.",
        star3_t     = 20.0,
        star2_t     = 35.0,
    )

    # ── Room 2: EMPLOYEE CORRIDOR (branching) ──────────────────────────
    r2_len  = 1200
    r2_elms = [
        # Branch trigger point at x=200
        # HIGH PATH (catwalk): y around CEIL_Y + 60
        Platform(260,  CEIL_Y + 60, 140, path_tag="high"),
        Platform(460,  CEIL_Y + 60, 140, path_tag="high"),
        Platform(680,  CEIL_Y + 60, 140, path_tag="high"),
        Platform(880,  CEIL_Y + 60, 120, path_tag="high"),
        # Moving hazards on high path (swinging cargo hooks)
        MovingHazard(350, CEIL_Y + 30, 20, 40, left=300, right=420, speed=70, path_tag="high"),
        MovingHazard(580, CEIL_Y + 30, 20, 40, left=520, right=660, speed=80, path_tag="high"),
        # Secret on high path
        Secret(930, CEIL_Y + 45, value=0,
               lore="Notes on Gary — he played sax at the depot. Stopped after his wife died. Doesn't talk about it.",
               path_tag="high"),
        # LOW PATH (crawlspace): ground level, 2 collapsing platforms
        Hazard(200, FLOOR_Y - 8, 40, 8, path_tag="low"),  # small gap indicator
        Platform(240, FLOOR_Y - 50, 70, path_tag="low"),
        Platform(380, FLOOR_Y - 55, 70, path_tag="low"),  # collapsing equivalents
        # 3 Collectibles on low path
        Collectible(280, FLOOR_Y - 65, 200, path_tag="low"),
        Collectible(420, FLOOR_Y - 20, 200, path_tag="low"),
        Collectible(600, FLOOR_Y - 20, 200, path_tag="low"),
        # NPC KENJI on low path
        NPCEncounter(
            550,
            "KENJI THE DJ",
            "Broadcasting illegal music from here. You carrying something good?",
            _KENJI_RESPONSES,
            path_tag="low",
        ),
        # Ladder up to Room 3 convergence point
        Ladder(1100, CEIL_Y + 60, FLOOR_Y - 10),
    ]
    room2 = Room(
        length     = r2_len,
        palette    = _PAL_R2,
        elements   = r2_elms,
        bg_draw_fn = _bg_r2,
        branch_x   = 200.0,
        converge_x = 1050.0,
        bax_enter_line = "Two paths. High is the catwalk. Low is the crawlspace. Your call.",
        star3_t    = 22.0,
        star2_t    = 40.0,
    )

    # ── Room 3: THE BACK ROOM (boss) ────────────────────────────────────
    r3_len  = 500
    r3_elms = [
        # Gary behind counter
        NPCEncounter(
            320,
            "GARY (OFF-DUTY)",
            "You'll forget this happened, courier. Delivery received.",
            _GARY_RESPONSES,
        ),
        BossRoomTrigger(
            180,
            bax_line="There's Gary. Off-duty Gary. He's gonna pretend he doesn't know us. Play along.",
        ),
    ]
    room3 = Room(
        length     = r3_len,
        palette    = _PAL_R3,
        elements   = r3_elms,
        bg_draw_fn = _bg_r3,
        bax_enter_line = "Back room. It's warm in here. I can hear music through the walls.",
        star3_t    = 60.0,   # boss room — time doesn't matter
        star2_t    = 90.0,
    )

    return Corridor(
        chapter          = 1,
        rooms            = [room1, room2, room3],
        cargo_silhouette = "archive",
    )
