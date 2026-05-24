"""
Chapter 3 — The Paperwork corridor.
Theme: fluorescent government office. Bureaucracy weaponized.
"""
from __future__ import annotations
import math
import random
import pygame

from delivery.corridor.elements import (
    Platform, MovingPlatform, CollapsingPlatform, Ladder,
    OneWayWall, NPCEncounter, Collectible, Secret, Checkpoint,
    BossRoomTrigger,
    CORRIDOR_W, CORRIDOR_H, FLOOR_Y, CEIL_Y, PLAYER_H,
)
from delivery.corridor.base import Room, Corridor

_PAL_R1 = {
    "bg":            (12, 12, 8),
    "grid":          (24, 24, 14),
    "ceiling_fill":  (22, 22, 14),
    "ceiling_line":  (160, 200, 80),
    "floor_fill":    (18, 18, 10),
    "floor_line":    (140, 180, 60),
    "platform":      (80, 90, 60),
    "platform_hi":   (140, 160, 90),
    "brick":         (120, 100, 40),
    "brick_hi":      (255, 230, 120),
    "light":         (255, 240, 140),
}
_PAL_R2 = {
    "bg":            (8, 8, 6),
    "grid":          (20, 20, 12),
    "ceiling_fill":  (18, 18, 10),
    "ceiling_line":  (120, 160, 60),
    "floor_fill":    (14, 14, 8),
    "floor_line":    (100, 140, 50),
    "platform":      (100, 80, 40),
    "platform_hi":   (160, 130, 60),
    "collapsing":    (180, 100, 0),
    "ladder":        (120, 100, 50),
    "light":         (140, 180, 70),
}
_PAL_R3 = {
    "bg":            (10, 8, 4),
    "grid":          (24, 20, 10),
    "ceiling_fill":  (20, 16, 8),
    "ceiling_line":  (220, 160, 40),
    "floor_fill":    (16, 12, 6),
    "floor_line":    (200, 140, 30),
    "platform":      (120, 80, 20),
    "platform_hi":   (220, 160, 50),
    "light":         (220, 180, 60),
}


def _bg_r1(surf, camera_x, t, pal):
    """Open-plan government office — empty desks, fluorescents."""
    bg_off = camera_x * 0.5
    f = pygame.font.SysFont("monospace", 8)
    # Desk rows
    for wx in range(200, 3000, 280):
        sx = int(wx - bg_off)
        if -180 < sx < CORRIDOR_W + 20:
            # Desk
            pygame.draw.rect(surf, (22, 22, 14), (sx, FLOOR_Y - 28, 100, 20))
            pygame.draw.rect(surf, (40, 40, 22), (sx, FLOOR_Y - 28, 100, 20), 1)
            # Monitor
            pygame.draw.rect(surf, (8, 12, 6), (sx + 4, FLOOR_Y - 50, 28, 20))
            pygame.draw.rect(surf, (80, 120, 40), (sx + 4, FLOOR_Y - 50, 28, 20), 1)
            # Scrolling debt data on monitor
            scroll = int((t * 12 + wx * 0.04) % 40)
            for li, ln in enumerate(["DEBT", "QUOTA", "CLONE", "STATUS"]):
                ly = FLOOR_Y - 48 + li * 8 - scroll
                if FLOOR_Y - 50 < ly < FLOOR_Y - 32:
                    surf.set_clip(pygame.Rect(sx + 5, FLOOR_Y - 49, 26, 18))
                    surf.blit(f.render(ln, True, (80, 120, 40)), (sx + 5, ly))
                    surf.set_clip(None)
    # Cubicle dividers (overlapping with OneWayWalls)
    for wx2 in range(300, 3000, 350):
        sx2 = int(wx2 - bg_off)
        if -10 < sx2 < CORRIDOR_W + 10:
            pygame.draw.line(surf, (30, 30, 18),
                             (sx2, CEIL_Y + 10), (sx2, FLOOR_Y), 2)
    # Fluorescent buzz effect
    flk = 1.0 - 0.04 * abs(math.sin(t * 47.0))
    fl_col = (int(120 * flk), int(160 * flk), int(60 * flk))
    for lx in range(0, CORRIDOR_W, 120):
        pygame.draw.rect(surf, fl_col, (lx, CEIL_Y + 2, 100, 4))


def _bg_r2(surf, camera_x, t, pal):
    """File Room 4 — impossibly tall shelves of paperwork."""
    bg_off = camera_x * 0.4
    # Towering shelves (wider and taller as you go further)
    for wx in range(0, 3500, 160):
        sx = int(wx - bg_off) % (CORRIDOR_W + 100) - 50
        scale = min(2.0, 1.0 + wx / 3000)
        sh = int((FLOOR_Y - CEIL_Y) * scale)
        pygame.draw.line(surf, (40, 32, 16),
                         (sx, FLOOR_Y), (sx, FLOOR_Y - sh), 2)
        # Shelf boards
        for yi in range(CEIL_Y, FLOOR_Y, 22):
            pygame.draw.line(surf, (32, 26, 12),
                             (sx, yi), (sx + 140, yi), 1)
            # Files/folders
            for fi in range(3):
                fc = [(80, 60, 20), (60, 80, 30), (70, 50, 40)][fi % 3]
                pygame.draw.rect(surf, fc,
                                 (sx + 5 + fi * 42, yi + 2, 35, 18))


def _bg_r3(surf, camera_x, t, pal):
    """Executive processing office — mahogany, Employee of Quarter plaques."""
    # Mahogany floor
    pygame.draw.rect(surf, (28, 14, 6), (0, FLOOR_Y - 6, CORRIDOR_W, 6))
    for lx in range(0, CORRIDOR_W, 40):
        pygame.draw.line(surf, (38, 20, 8), (lx, FLOOR_Y - 6), (lx + 20, FLOOR_Y), 1)
    # Plaques on wall
    f_sm = pygame.font.SysFont("monospace", 8)
    for i, (wx, text) in enumerate([
        (60,  "EMPLOYEE Q1"),
        (180, "TOP IMPOUND"),
        (300, "MOST FORMS"),
        (360, "BEST UNIFORM"),
    ]):
        col = (180, 140, 40)
        pygame.draw.rect(surf, (30, 20, 6), (wx, CEIL_Y + 10, 80, 28))
        pygame.draw.rect(surf, col, (wx, CEIL_Y + 10, 80, 28), 2)
        s = f_sm.render(text, True, col)
        surf.blit(s, (wx + 4, CEIL_Y + 14))
        s2 = f_sm.render(f"NOVA SOMA  Q{i+1}", True, (100, 80, 20))
        surf.blit(s2, (wx + 4, CEIL_Y + 24))
    # Secretary silhouette
    for sx3, sy3 in [(CORRIDOR_W - 50, FLOOR_Y - 1)]:
        pygame.draw.rect(surf, (14, 10, 5), (sx3 - 5, sy3 - 22, 10, 14))
        pygame.draw.circle(surf, (14, 10, 5), (sx3, sy3 - 28), 6)
    # Big mahogany desk
    pygame.draw.rect(surf, (22, 10, 4),
                     (CORRIDOR_W - 140, FLOOR_Y - 36, 120, 28))
    pygame.draw.rect(surf, (60, 30, 10),
                     (CORRIDOR_W - 140, FLOOR_Y - 36, 120, 28), 2)


# NPC responses
_MARGARET_RESPONSES = [
    {
        "keywords": ["27", "27-b", "form 27", "form"],
        "credits":  0,
        "lore":     "Margaret stamps it. Through.",
        "outcome":  "pass",
    },
    {
        "keywords": [],  # fallback after delay
        "credits":  0,
        "lore":     "Margaret sighs. 5-second delay.",
        "outcome":  "penalty",
    },
]
_HOWARD_RESPONSES = [
    # Any non-empty input works
    {
        "keywords": [],
        "credits":  0,
        "lore":     "Howard doesn't read it. Through.",
        "outcome":  "pass",
    },
]
_BRENDA_RESPONSES = [
    {
        "keywords": ["void", "null", "expired", "invalid", "revoke"],
        "credits":  600,
        "lore":     "Brenda blinks. Fast-track stamp. +600 cr.",
        "outcome":  "reward",
    },
    {
        "keywords": [],
        "credits":  0,
        "lore":     "Standard 5-second delay.",
        "outcome":  "penalty",
    },
]
_DISPATCHER_RESPONSES = [
    {
        "keywords": ["delivery", "paperwork", "forms", "done", "complete", "here"],
        "credits":  800,
        "lore":     "Dispatcher receives the forms. Visibly uncomfortable.",
        "outcome":  "reward",
    },
    {
        "keywords": [],
        "credits":  400,
        "lore":     "",
        "outcome":  "pass",
    },
]


def build() -> Corridor:
    # ── Room 1: INTAKE FLOOR ─────────────────────────────────────────────
    r1_elms = [
        # OneWayWalls forcing zigzag through cubicles
        OneWayWall(220, CEIL_Y + 20, FLOOR_Y, blocks_right=True),
        OneWayWall(420, CEIL_Y + 20, FLOOR_Y, blocks_right=False),
        OneWayWall(620, CEIL_Y + 20, FLOOR_Y, blocks_right=True),
        # 3 mandatory clerks
        NPCEncounter(
            300, "MARGARET",
            "Form 27-B. Required. Section 9. Don't make this difficult.",
            _MARGARET_RESPONSES,
        ),
        NPCEncounter(
            500, "HOWARD",
            "Purpose of visit? Enter anything. I'll file it. I don't actually read these.",
            _HOWARD_RESPONSES,
        ),
        NPCEncounter(
            700, "BRENDA",
            "Argue that Union Bylaw 12-F is invalid. Use the correct legal term.",
            _BRENDA_RESPONSES,
        ),
        # 5 collectible chips across desk row
        Collectible(250, FLOOR_Y - 20, 200),
        Collectible(380, FLOOR_Y - 20, 200),
        Collectible(480, FLOOR_Y - 20, 200),
        Collectible(650, FLOOR_Y - 20, 200),
        Collectible(780, FLOOR_Y - 20, 200),
        Checkpoint(900),
    ]
    room1 = Room(
        length     = 1050,
        palette    = _PAL_R1,
        elements   = r1_elms,
        bg_draw_fn = _bg_r1,
        bax_enter_line = "Office. Real office. With fluorescents. They want forms. Just give 'em forms. Don't make it weird.",
        star3_t    = 30.0,
        star2_t    = 50.0,
    )

    # ── Room 2: FILE ROOM 4 ──────────────────────────────────────────────
    r2_elms = [
        # CollapsingPlatform stacks of paper files
        CollapsingPlatform(200, FLOOR_Y - 55),
        CollapsingPlatform(310, FLOOR_Y - 90),
        CollapsingPlatform(420, FLOOR_Y - 130),
        CollapsingPlatform(530, FLOOR_Y - 165),
        CollapsingPlatform(640, FLOOR_Y - 200),
        # Moving platform (filing cart)
        MovingPlatform(380, FLOOR_Y - 70, left=320, right=460, speed=80),
        MovingPlatform(680, FLOOR_Y - 140, left=610, right=760, speed=90),
        # Ladder for low path
        Ladder(280, CEIL_Y, FLOOR_Y - 10, path_tag="low"),
        Ladder(800, CEIL_Y, FLOOR_Y - 10, path_tag="low"),
        # Secrets
        Secret(
            360, FLOOR_Y - 110, value=1500,
            lore="Form NS-19B: opt-out from clone debt. Status: REJECTED. Reason: applicant currently deceased.",
        ),
        Secret(
            700, FLOOR_Y - 240, value=600,
            lore="Discarded petty-cash envelope. Nova Soma's loss is your gain.",
        ),
        # High path platforms
        Platform(200, CEIL_Y + 40, 80, path_tag="high"),
        Platform(340, CEIL_Y + 40, 80, path_tag="high"),
        Platform(480, CEIL_Y + 40, 80, path_tag="high"),
        Platform(620, CEIL_Y + 40, 80, path_tag="high"),
        Platform(760, CEIL_Y + 40, 80, path_tag="high"),
    ]
    room2 = Room(
        length     = 1100,
        palette    = _PAL_R2,
        elements   = r2_elms,
        bg_draw_fn = _bg_r2,
        branch_x   = 180.0,
        converge_x = 860.0,
        bax_enter_line = "Up we go. There are receipts up there from before the Republic. The Republic. Climb.",
        star3_t    = 32.0,
        star2_t    = 55.0,
    )

    # ── Room 3: EXECUTIVE PROCESSING (boss) ──────────────────────────────
    r3_elms = [
        BossRoomTrigger(
            150,
            bax_line="That's the Dispatcher. In his actual office. We've never been in an actual office before. Be respectful or whatever.",
        ),
        NPCEncounter(
            330,
            "UNION DISPATCHER",
            "You're — you're physically here? In my office? With the forms? Fine. Sign the ledger.",
            _DISPATCHER_RESPONSES,
        ),
    ]
    room3 = Room(
        length     = 500,
        palette    = _PAL_R3,
        elements   = r3_elms,
        bg_draw_fn = _bg_r3,
        bax_enter_line = "Corner office. He's not expecting us. He's going to pretend he is.",
        star3_t    = 60.0,
        star2_t    = 90.0,
    )

    return Corridor(
        chapter          = 3,
        rooms            = [room1, room2, room3],
        cargo_silhouette = "forms",
    )
