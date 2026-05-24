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
    """Industrial loading bay — cranes, cracked concrete."""
    bg_off = camera_x * 0.45
    # Overhead crane rail
    pygame.draw.line(surf, (60, 30, 10), (0, CEIL_Y + 8), (CORRIDOR_W, CEIL_Y + 8), 3)
    # Crane hooks at intervals
    for wx in range(200, 3200, 300):
        sx = int(wx - bg_off) % (CORRIDOR_W + 100) - 50
        hy = CEIL_Y + 8 + int(20 * abs(math.sin(t * 0.3 + wx * 0.001)))
        pygame.draw.line(surf, (80, 40, 10), (sx, CEIL_Y + 8), (sx, hy), 2)
        pygame.draw.line(surf, (100, 50, 20),
                         (sx - 6, hy), (sx + 6, hy), 2)
        pygame.draw.line(surf, (100, 50, 20),
                         (sx - 6, hy), (sx - 2, hy + 8), 2)
        pygame.draw.line(surf, (100, 50, 20),
                         (sx + 6, hy), (sx + 2, hy + 8), 2)
    # Propaganda posters
    f = pygame.font.SysFont("monospace", 8)
    for wx, text in [(300, "DEBT IS IDENTITY"), (800, "LOCAL 404 PROTECTS"),
                     (1300, "REPORT COURIERS"), (1900, "STAY COMPLIANT")]:
        sx = int(wx - bg_off)
        if -110 < sx < CORRIDOR_W + 10:
            pygame.draw.rect(surf, (30, 12, 8), (sx, FLOOR_Y - 30, 100, 20))
            pygame.draw.rect(surf, (120, 50, 10), (sx, FLOOR_Y - 30, 100, 20), 1)
            s = f.render(text, True, (120, 50, 10))
            surf.blit(s, (sx + 2, FLOOR_Y - 27))
    # Floor crack lines
    for wx2 in range(150, 3200, 220):
        sx2 = int(wx2 - bg_off) % (CORRIDOR_W + 80) - 40
        pygame.draw.line(surf, (40, 18, 12),
                         (sx2, FLOOR_Y - 2),
                         (sx2 + random.Random(wx2).randint(10, 30), FLOOR_Y), 1)


def _bg_r2(surf, camera_x, t, pal):
    """Employee corridor — illegal band posters, mid-shift colour."""
    bg_off = camera_x * 0.5
    f = pygame.font.SysFont("monospace", 8)
    bands = ["THE NULL SETS", "VOID UNION", "LOCAL STATIC", "ARCHIVE RATS",
             "BARGE CHASERS", "CLONEWAVE", "NOISE OF 404", "FEEDBACK LOOP"]
    rng = random.Random(42)
    for i, wx in enumerate(range(200, 2800, 340)):
        sx = int(wx - bg_off)
        if -120 < sx < CORRIDOR_W + 20:
            col = [(200, 60, 180), (60, 200, 160), (200, 140, 0),
                   (0, 160, 200)][i % 4]
            pygame.draw.rect(surf, tuple(c // 4 for c in col),
                             (sx, FLOOR_Y - 34, 90, 22))
            pygame.draw.rect(surf, col, (sx, FLOOR_Y - 34, 90, 22), 1)
            s = f.render(bands[i % len(bands)], True, col)
            surf.blit(s, (sx + 2, FLOOR_Y - 30))


def _bg_r3(surf, camera_x, t, pal):
    """Back room — underground club, record sleeves, crowd silhouettes."""
    bg_off = camera_x * 0.4
    # Warm ambient light pools
    for lx2 in range(0, CORRIDOR_W, 80):
        a = int(18 + 10 * math.sin(t * 0.8 + lx2 * 0.05))
        lp = pygame.Surface((80, FLOOR_Y - CEIL_Y), pygame.SRCALPHA)
        lp.fill((60, 30, 0, a))
        surf.blit(lp, (lx2, CEIL_Y))
    # Record sleeves on wall
    f = pygame.font.SysFont("monospace", 7)
    sleeve_data = [(80, "STATIC ECHOES", (200, 80, 20)),
                   (180, "ARCHIVE VOL. 3", (0, 160, 120)),
                   (280, "NOISE FLOOR", (180, 0, 100)),
                   (360, "GARYS MIXTAPE", (200, 160, 0))]
    for sx3, title, col in sleeve_data:
        pygame.draw.rect(surf, tuple(c // 5 for c in col),
                         (sx3, CEIL_Y + 10, 56, 56))
        pygame.draw.rect(surf, col, (sx3, CEIL_Y + 10, 56, 56), 1)
        pygame.draw.circle(surf, (10, 8, 6), (sx3 + 28, CEIL_Y + 38), 20)
        pygame.draw.circle(surf, col, (sx3 + 28, CEIL_Y + 38), 20, 1)
        pygame.draw.circle(surf, col, (sx3 + 28, CEIL_Y + 38), 4)
        s = f.render(title, True, col)
        surf.blit(s, (sx3 + 2, CEIL_Y + 68))
    # Crowd silhouettes
    for i, npc_wx in enumerate([100, 200, 290, 370]):
        ny = FLOOR_Y - 1
        bob = int(3 * math.sin(t * 1.4 + i * 1.1))
        col2 = (20, 10, 8)
        pygame.draw.rect(surf, col2, (npc_wx - 5, ny - 24 + bob, 10, 16))
        pygame.draw.circle(surf, col2, (npc_wx, ny - 30 + bob), 7)


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
