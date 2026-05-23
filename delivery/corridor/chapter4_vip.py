"""
Chapter 4 — Schrödinger Hotel corridor.
Theme: luxury orbital hotel, quantum doors, the cargo is contagious to reality.
"""
from __future__ import annotations
import math
import random
import pygame

from delivery.corridor.elements import (
    Platform, MovingPlatform, Hazard, MovingHazard, Ladder,
    NPCEncounter, Collectible, Secret, Checkpoint, StealthZone,
    BossRoomTrigger, QuantumDoor,
    CORRIDOR_W, CORRIDOR_H, FLOOR_Y, CEIL_Y, PLAYER_H,
)
from delivery.corridor.base import Room, Corridor

_PAL_R1 = {
    "bg":            (6, 4, 8),
    "grid":          (16, 10, 20),
    "ceiling_fill":  (12, 8, 18),
    "ceiling_line":  (140, 80, 200),
    "floor_fill":    (10, 6, 16),
    "floor_line":    (100, 60, 160),
    "platform":      (60, 30, 100),
    "platform_hi":   (120, 70, 200),
    "brick":         (180, 140, 40),
    "brick_hi":      (255, 220, 100),
    "light":         (255, 200, 80),
}
_PAL_R2 = {
    "bg":            (8, 6, 10),
    "grid":          (20, 14, 24),
    "ceiling_fill":  (14, 10, 18),
    "ceiling_line":  (200, 160, 80),
    "floor_fill":    (12, 8, 16),
    "floor_line":    (180, 140, 60),
    "platform":      (80, 60, 30),
    "platform_hi":   (160, 130, 60),
    "light":         (200, 160, 60),
}
_PAL_R3 = {
    "bg":            (10, 6, 12),
    "grid":          (24, 14, 28),
    "ceiling_fill":  (16, 10, 20),
    "ceiling_line":  (255, 200, 80),
    "floor_fill":    (14, 8, 18),
    "floor_line":    (220, 170, 60),
    "platform":      (100, 70, 20),
    "platform_hi":   (220, 180, 60),
    "light":         (255, 210, 80),
}


def _bg_r1(surf, camera_x, t, pal):
    """Service corridor — industrial pipes but with carpet."""
    bg_off = camera_x * 0.5
    # Carpet (mid-floor band)
    pygame.draw.rect(surf, (30, 10, 40),
                     (0, FLOOR_Y - 8, CORRIDOR_W, 8))
    # Carpet pattern
    for cx in range(0, CORRIDOR_W, 16):
        pul = int(40 + 15 * abs(math.sin(t * 0.3 + cx * 0.1)))
        pygame.draw.rect(surf, (pul, 0, int(pul * 0.6)),
                         (cx, FLOOR_Y - 8, 8, 8))
    # Overhead pipes
    for py_c in (CEIL_Y + 4, CEIL_Y + 10, CEIL_Y + 16):
        pygame.draw.line(surf, (40, 20, 60), (0, py_c), (CORRIDOR_W, py_c), 2)
    for cx2 in range(0, CORRIDOR_W, 70):
        pygame.draw.rect(surf, (50, 25, 70), (cx2, CEIL_Y, 10, 22))
    # Laundry carts (cover objects)
    for wx in range(300, 2500, 500):
        sx = int(wx - bg_off) % (CORRIDOR_W + 100) - 50
        if -30 < sx < CORRIDOR_W + 30:
            pygame.draw.rect(surf, (20, 12, 30), (sx - 20, FLOOR_Y - 44, 40, 36))
            pygame.draw.rect(surf, (60, 30, 80), (sx - 20, FLOOR_Y - 44, 40, 36), 1)
            # Wheels
            pygame.draw.circle(surf, (30, 20, 40), (sx - 14, FLOOR_Y - 6), 4)
            pygame.draw.circle(surf, (30, 20, 40), (sx + 14, FLOOR_Y - 6), 4)
            pygame.draw.circle(surf, (60, 40, 80), (sx - 14, FLOOR_Y - 6), 4, 1)
            pygame.draw.circle(surf, (60, 40, 80), (sx + 14, FLOOR_Y - 6), 4, 1)


def _bg_r2(surf, camera_x, t, pal):
    """Guest floor 47 — identical doors, long hallway."""
    bg_off = camera_x * 0.5
    f = pygame.font.SysFont("monospace", 8)
    # Doors along both walls
    for wx in range(80, 3000, 160):
        sx = int(wx - bg_off)
        if -50 < sx < CORRIDOR_W + 50:
            door_col = (60, 50, 20)
            pygame.draw.rect(surf, door_col, (sx - 16, CEIL_Y + 4, 32, FLOOR_Y - CEIL_Y - 8))
            pygame.draw.rect(surf, (140, 110, 40),
                             (sx - 16, CEIL_Y + 4, 32, FLOOR_Y - CEIL_Y - 8), 1)
            # Room number
            room_n = str(1400 + wx // 10)
            s = f.render(room_n, True, (100, 80, 30))
            surf.blit(s, (sx - s.get_width() // 2, CEIL_Y + 6))
            # Door knob
            pygame.draw.circle(surf, (180, 140, 40),
                               (sx + 12, (CEIL_Y + FLOOR_Y) // 2), 4)
    # Floor carpet
    pygame.draw.rect(surf, (20, 14, 6), (0, FLOOR_Y - 6, CORRIDOR_W, 6))
    for cx in range(0, CORRIDOR_W, 20):
        pul2 = int(30 + 10 * abs(math.sin(t * 0.2 + cx * 0.08)))
        pygame.draw.rect(surf, (pul2, int(pul2 * 0.7), 0),
                         (cx, FLOOR_Y - 6, 10, 6))


def _bg_r3(surf, camera_x, t, pal):
    """Penthouse suite — wall-sized window, plush furniture, fireplace."""
    # Planet view through window
    win_x, win_y = 20, CEIL_Y + 8
    win_w, win_h = 180, FLOOR_Y - CEIL_Y - 16
    pygame.draw.rect(surf, (4, 8, 20), (win_x, win_y, win_w, win_h))
    pygame.draw.rect(surf, (60, 100, 180), (win_x, win_y, win_w, win_h), 2)
    # Planet
    pul = 0.6 + 0.4 * math.sin(t * 0.1)
    pygame.draw.circle(surf, (int(40 * pul), int(80 * pul), int(30 * pul)),
                       (win_x + win_w // 2, win_y + win_h - 30), 60)
    # Cloud bands
    for band_y in (win_y + win_h - 55, win_y + win_h - 40):
        pygame.draw.line(surf, (int(60 * pul), int(120 * pul), int(50 * pul)),
                         (win_x + 10, band_y), (win_x + win_w - 10, band_y), 3)
    # Fireplace
    fx, fy = CORRIDOR_W - 80, FLOOR_Y - 10
    pygame.draw.rect(surf, (20, 10, 4), (fx - 24, fy - 40, 48, 40))
    pygame.draw.rect(surf, (80, 50, 20), (fx - 24, fy - 40, 48, 40), 2)
    # Flames
    for fi in range(5):
        fa = t * 4.0 + fi * 1.2
        fh2 = int(14 + 8 * abs(math.sin(fa)))
        fc = (255, int(80 + 60 * abs(math.sin(fa))), 0)
        pygame.draw.line(surf, fc,
                         (fx - 12 + fi * 6, fy - 4),
                         (fx - 10 + fi * 5, fy - 4 - fh2), 2)
    # Plush armchair
    pygame.draw.rect(surf, (60, 20, 40), (CORRIDOR_W // 2 - 20, FLOOR_Y - 30, 40, 22))
    pygame.draw.rect(surf, (100, 40, 60), (CORRIDOR_W // 2 - 20, FLOOR_Y - 30, 40, 22), 1)
    # Morwenna (insurance adjuster) behind coffee table
    mx, my = CORRIDOR_W - 40, FLOOR_Y - 1
    pygame.draw.rect(surf, (14, 8, 18), (mx - 5, my - 26, 10, 18))
    pygame.draw.circle(surf, (14, 8, 18), (mx, my - 32), 7)


# NPC responses
_DELL_RESPONSES = [
    {
        "keywords": ["yes", "alive", "living", "fine", "okay", "active"],
        "credits":  200,
        "lore":     "Mx. Dell nods. Gives directions. Concierge tip received.",
        "outcome":  "reward",
    },
    {
        "keywords": ["no", "dead", "deceased", "gone", "not"],
        "credits":  0,
        "lore":     "Mx. Dell's expression flickers. They walk away.",
        "outcome":  "pass",
    },
    {
        "keywords": ["both", "maybe", "either", "neither", "paradox", "unknown", "uncertain"],
        "credits":  500,
        "lore":     "You broke the concierge. Philosophical compliment: +500 cr.",
        "outcome":  "paradox",
    },
    {
        "keywords": [],
        "credits":  0,
        "lore":     "",
        "outcome":  "pass",
    },
]
_MORWENNA_RESPONSES = [
    {
        "keywords": ["alive", "yes", "living", "fine", "surviv"],
        "credits":  1000,
        "lore":     "VIP: ALIVE. Full payout. Morwenna signs the receipt.",
        "outcome":  "reward",
    },
    {
        "keywords": ["dead", "no", "deceased", "not"],
        "credits":  400,
        "lore":     "VIP: DECEASED. Partial payout. Morwenna notes the outcome.",
        "outcome":  "pass",
    },
    {
        "keywords": ["open", "check", "look", "box", "observe"],
        "credits":  600,
        "lore":     "Morwenna opens it herself. Observation event. State collapses now.",
        "outcome":  "reward",
    },
    {
        "keywords": [],
        "credits":  500,
        "lore":     "VIP: UNOBSERVED. Morwenna opens the box.",
        "outcome":  "pass",
    },
]


def build() -> Corridor:
    # ── Room 1: STAFF ENTRANCE — DO NOT BE SEEN ─────────────────────────
    r1_patrols = [
        {
            "ox": 200, "oy": FLOOR_Y - CEIL_Y - 20,
            "angle_min": -120, "angle_max": -60,
            "speed": 25, "cone_deg": 50, "range": 160,
        },
        {
            "ox": 600, "oy": FLOOR_Y - CEIL_Y - 20,
            "angle_min": -140, "angle_max": -40,
            "speed": 20, "cone_deg": 45, "range": 140,
        },
    ]
    r1_elms = [
        # Cover platforms (laundry carts / room service trays)
        Platform(180, FLOOR_Y - 52, 50),
        Platform(360, FLOOR_Y - 52, 50),
        Platform(540, FLOOR_Y - 52, 50),
        Platform(720, FLOOR_Y - 52, 50),
        # Full stealth zone
        StealthZone(80, CEIL_Y, CORRIDOR_W + 400, FLOOR_Y - CEIL_Y, r1_patrols),
        # Secrets
        Secret(
            240, FLOOR_Y - 70, value=0,
            lore="Guest in room 1408 has been here for forty-three years and never opened the curtains. Doesn't tip.",
        ),
        Secret(480, FLOOR_Y - 70, value=800,
               lore="Guest left this for housekeeping. They were very generous."),
        Checkpoint(880),   # elevator
    ]
    room1 = Room(
        length     = 980,
        palette    = _PAL_R1,
        elements   = r1_elms,
        bg_draw_fn = _bg_r1,
        bax_enter_line = "Hotel. Luxury one. Don't touch anything. They charge for breathing.",
        star3_t    = 25.0,
        star2_t    = 45.0,
    )

    # ── Room 2: GUEST FLOOR 47 (quantum doors) ───────────────────────────
    r2_elms = [
        # Quantum doors — 5 total, 2 real (outcome varies)
        QuantumDoor(200, outcome="nothing"),
        QuantumDoor(300, outcome="secret"),
        QuantumDoor(440, outcome="nothing"),
        QuantumDoor(560, outcome="shortcut"),
        QuantumDoor(700, outcome="nothing"),
        # Hazard strip — vacuum-cleaner robots
        MovingHazard(350, FLOOR_Y - 16, 20, 16, left=180, right=540, speed=88),
        MovingHazard(600, FLOOR_Y - 16, 20, 16, left=480, right=780, speed=72),
        # NPC Mx. Dell
        NPCEncounter(
            560,
            "MX. DELL",
            "Pardon me — is the package... live?",
            _DELL_RESPONSES,
        ),
        # Collectibles
        Collectible(260, FLOOR_Y - 30, 300),
        Collectible(480, FLOOR_Y - 30, 300),
        Collectible(750, FLOOR_Y - 30, 300),
    ]
    room2 = Room(
        length     = 900,
        palette    = _PAL_R2,
        elements   = r2_elms,
        bg_draw_fn = _bg_r2,
        bax_enter_line = "Pick a door, mate. Or don't. They're not all real anyway. I don't know which are which. I don't think I'm supposed to know.",
        star3_t    = 22.0,
        star2_t    = 40.0,
    )

    # ── Room 3: PENTHOUSE SUITE (boss) ───────────────────────────────────
    r3_elms = [
        BossRoomTrigger(
            120,
            bax_line="Penthouse. Morwenna's waiting. Don't make her open the box. ...Actually, do. I want to see.",
        ),
        NPCEncounter(
            280,
            "MORWENNA (INSURANCE)",
            "Is the passenger alive or deceased? The claim is already filed either way.",
            _MORWENNA_RESPONSES,
        ),
    ]
    room3 = Room(
        length     = 450,
        palette    = _PAL_R3,
        elements   = r3_elms,
        bg_draw_fn = _bg_r3,
        bax_enter_line = "Penthouse. Fireplace. In space. Sure.",
        star3_t    = 60.0,
        star2_t    = 90.0,
    )

    return Corridor(
        chapter          = 4,
        rooms            = [room1, room2, room3],
        cargo_silhouette = "vip",
    )
