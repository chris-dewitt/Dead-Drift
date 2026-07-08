"""
Chapter 4 — Schrödinger Hotel corridor.
Theme: luxury orbital hotel, quantum doors, the cargo is contagious to reality.
"""
from __future__ import annotations
import math
import random
import pygame

from core.text import get_font
from delivery.corridor.elements import (
    Platform, MovingPlatform, Hazard, MovingHazard, Ladder,
    NPCEncounter, Collectible, Secret, Checkpoint, StealthZone,
    BossRoomTrigger, QuantumDoor,
    BossRoomActor, boss_actor_quantum_observation,
    LoreRoom, NPCShortcut,
    CORRIDOR_W, CORRIDOR_H, FLOOR_Y, CEIL_Y, PLAYER_H,
)
from delivery.corridor.base import Room, Corridor

_PAL_R1 = {
    "tile_style":  "chrome",   # I.4.1 chapter tile vocabulary
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
    # Epic 10.4 — gold-marble luxury hotel lighting
    "light_tint":    (220, 180, 110),
    "light_alpha":   20,
    "deep_struct":   (40,  20,  60),
    "panel_num":     (200, 150,  60),
    "crack":         (80,  60,  20),
    "branding":      (150, 110,  60),
    "scrub":         (60,  40,  20),
    "floor_grid":    (90,  70,  40),
    "floor_wear":    (70,  56,  30),
    "drip":          (255, 200,  90),
}
_PAL_R2 = {
    "tile_style":  "chrome",   # I.4.1 chapter tile vocabulary
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
    "tile_style":  "chrome",   # I.4.1 chapter tile vocabulary
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
    """Service corridor — chandeliers, gold trim, velvet wallpaper, room-service cart, staff silhouette, stain."""
    bg_off = camera_x * 0.5
    bg_off_slow = camera_x * 0.3

    WALL_TOP = CEIL_Y
    WALL_BOT = FLOOR_Y
    WALL_H = WALL_BOT - WALL_TOP  # 80

    # --- Deep midnight-purple base fill ---
    pygame.draw.rect(surf, (10, 6, 16), (0, WALL_TOP, CORRIDOR_W, WALL_H))

    # --- Velvet wallpaper: subtle diamond tiling in dark purple ---
    diamond_w = 22
    diamond_h = 14
    for gx in range(-diamond_w, CORRIDOR_W + diamond_w, diamond_w):
        gx_off = int(gx - bg_off_slow * 0.08)
        for gy in range(WALL_TOP + 2, WALL_BOT - 4, diamond_h):
            # alternating rows offset by half
            row = (gy - WALL_TOP) // diamond_h
            x_off = (diamond_w // 2) if row % 2 == 1 else 0
            cx_d = gx_off + x_off
            if -diamond_w < cx_d < CORRIDOR_W + diamond_w:
                pts = [
                    (cx_d, gy - diamond_h // 2),
                    (cx_d + diamond_w // 2, gy),
                    (cx_d, gy + diamond_h // 2),
                    (cx_d - diamond_w // 2, gy),
                ]
                pygame.draw.polygon(surf, (22, 10, 32), pts, 1)

    # --- Thick GOLD border trim along top and bottom of wall zone (4px) ---
    pygame.draw.line(surf, (180, 140, 40), (0, WALL_TOP + 3), (CORRIDOR_W, WALL_TOP + 3), 4)
    pygame.draw.line(surf, (120, 90, 24), (0, WALL_TOP + 7), (CORRIDOR_W, WALL_TOP + 7), 1)
    pygame.draw.line(surf, (180, 140, 40), (0, WALL_BOT - 4), (CORRIDOR_W, WALL_BOT - 4), 4)
    pygame.draw.line(surf, (120, 90, 24), (0, WALL_BOT - 8), (CORRIDOR_W, WALL_BOT - 8), 1)

    # --- Chandelier shapes along ceiling ---
    for wx_ch in range(120, CORRIDOR_W + 1400, 220):
        sx_ch = int(wx_ch - bg_off)
        if -60 < sx_ch < CORRIDOR_W + 60:
            # Vertical drop rod from ceiling
            pygame.draw.line(surf, (140, 110, 30), (sx_ch, WALL_TOP + 4), (sx_ch, WALL_TOP + 18), 2)
            # Main horizontal arm
            pygame.draw.line(surf, (160, 125, 35), (sx_ch - 22, WALL_TOP + 18), (sx_ch + 22, WALL_TOP + 18), 2)
            # Two side drop arms
            for arm_dx in (-22, -11, 0, 11, 22):
                arm_len = 6 + int(4 * abs(math.sin(abs(arm_dx) * 0.15)))
                pygame.draw.line(surf, (140, 110, 28),
                                 (sx_ch + arm_dx, WALL_TOP + 18),
                                 (sx_ch + arm_dx, WALL_TOP + 18 + arm_len), 1)
                # Small gem circle at tip
                gem_y = WALL_TOP + 18 + arm_len + 2
                gem_col_base = int(180 + 60 * abs(math.sin(t * 1.2 + arm_dx * 0.3 + wx_ch * 0.01)))
                pygame.draw.circle(surf, (int(gem_col_base * 0.9), int(gem_col_base * 0.7), 20),
                                   (sx_ch + arm_dx, gem_y), 2)
                pygame.draw.circle(surf, (gem_col_base, int(gem_col_base * 0.85), 40),
                                   (sx_ch + arm_dx, gem_y), 2, 1)
            # Central body (octagonal lantern-like shape)
            pygame.draw.rect(surf, (60, 45, 10), (sx_ch - 5, WALL_TOP + 15, 10, 8))
            pygame.draw.rect(surf, (180, 140, 36), (sx_ch - 5, WALL_TOP + 15, 10, 8), 1)
            # Warm ambient glow beneath chandelier
            glow_surf = pygame.Surface((50, 16), pygame.SRCALPHA)
            glow_a = int(30 + 12 * abs(math.sin(t * 0.6 + wx_ch * 0.01)))
            glow_surf.fill((220, 170, 60, glow_a))
            surf.blit(glow_surf, (sx_ch - 25, WALL_TOP + 24))

    # --- Hotel staff silhouette facing away ---
    staff_wx = 580
    staff_sx = int(staff_wx - bg_off * 0.6)
    if -20 < staff_sx < CORRIDOR_W + 20:
        sy_base = WALL_BOT - 1
        # Uniform body (dark jacket, facing away — wider shoulders than hips)
        body_pts = [
            (staff_sx - 8, sy_base),
            (staff_sx + 8, sy_base),
            (staff_sx + 10, sy_base - 20),
            (staff_sx - 10, sy_base - 20),
        ]
        pygame.draw.polygon(surf, (12, 8, 20), body_pts)
        # Head
        pygame.draw.circle(surf, (12, 8, 20), (staff_sx, sy_base - 26), 6)
        # White collar band
        pygame.draw.line(surf, (180, 175, 170), (staff_sx - 5, sy_base - 20),
                         (staff_sx + 5, sy_base - 20), 2)
        # Epaulette hints on shoulders
        pygame.draw.rect(surf, (140, 110, 28), (staff_sx - 12, sy_base - 22, 5, 3))
        pygame.draw.rect(surf, (140, 110, 28), (staff_sx + 7, sy_base - 22, 5, 3))

    # --- Room service cart ---
    cart_wx = 350
    cart_sx = int(cart_wx - bg_off * 0.7)
    if -50 < cart_sx < CORRIDOR_W + 50:
        cy = WALL_BOT - 1
        # Cart body (3 shelves)
        pygame.draw.rect(surf, (30, 18, 42), (cart_sx - 18, cy - 48, 36, 40))
        pygame.draw.rect(surf, (80, 60, 100), (cart_sx - 18, cy - 48, 36, 40), 1)
        # Shelf dividers
        for shelf_y in (cy - 32, cy - 18):
            pygame.draw.line(surf, (60, 44, 78), (cart_sx - 16, shelf_y), (cart_sx + 16, shelf_y), 1)
        # Dish circles on top shelf
        for dish_x in (cart_sx - 10, cart_sx, cart_sx + 10):
            pygame.draw.circle(surf, (200, 195, 185), (dish_x, cy - 42), 4)
            pygame.draw.circle(surf, (240, 235, 225), (dish_x, cy - 42), 4, 1)
            # Dome/cloche
            pygame.draw.arc(surf, (170, 165, 155),
                            pygame.Rect(dish_x - 4, cy - 46, 8, 6), 0, math.pi, 1)
        # Wheels
        for wx_w in (cart_sx - 12, cart_sx + 12):
            pygame.draw.circle(surf, (20, 14, 30), (wx_w, cy - 4), 4)
            pygame.draw.circle(surf, (70, 50, 90), (wx_w, cy - 4), 4, 1)
        # Handle bar
        pygame.draw.line(surf, (90, 65, 110), (cart_sx + 18, cy - 44), (cart_sx + 18, cy - 10), 2)

    # --- STAIN on carpet near floor (horror note — dark red smear) ---
    stain_wx = 480
    stain_sx = int(stain_wx - bg_off * 0.4)
    if -40 < stain_sx < CORRIDOR_W + 40:
        # Irregular smear using SRCALPHA ellipse-ish overlay
        stain_surf = pygame.Surface((34, 8), pygame.SRCALPHA)
        stain_surf.fill((0, 0, 0, 0))
        pygame.draw.ellipse(stain_surf, (90, 6, 6, 160), (0, 2, 34, 5))
        pygame.draw.ellipse(stain_surf, (70, 4, 4, 120), (5, 0, 20, 8))
        surf.blit(stain_surf, (stain_sx - 17, WALL_BOT - 9))


def _bg_r2(surf, camera_x, t, pal):
    """Guest floor 47 — identical doors, long hallway."""
    bg_off = camera_x * 0.5
    f = get_font(8)
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
        name       = "STAFF ENTRANCE",
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
        # G.6 — Lore wall: guest complaint log, room 1408
        LoreRoom(
            640,
            "Guest complaint, room 1408: 'The corridor changes at night. Something is in the wall.' Management response: 'Thank you for your stay. Your deposit has been processed.'",
            chapter=4, npc_voice="MX. DELL", path_tag=None,
        ),
        # G.7 — Staff elevator: skip guest floor for 400cr
        NPCShortcut(
            160, "MX. DELL",
            flavor="Staff elevator. Dell's pass. Don't ask how I got it.",
            skip_x=900, cost=400, path_tag=None,
        ),
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
        name       = "GUEST FLOOR 47",
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
        # Epic 14.1 — Quantum Observation Deck: a box on a pedestal,
        # lid superposition-flickering, spectator silhouettes, periodic
        # observation glitch frame.
        BossRoomActor(360, boss_actor_quantum_observation),
    ]
    room3 = Room(
        length     = 450,
        palette    = _PAL_R3,
        elements   = r3_elms,
        bg_draw_fn = _bg_r3,
        bax_enter_line = "Penthouse. Fireplace. In space. Sure.",
        star3_t    = 60.0,
        star2_t    = 90.0,
        name       = "PENTHOUSE SUITE",
    )

    # Delivery v2 I.3b — three new rooms of hotel back-of-house between
    # the staff entrance and the penthouse.
    from delivery.corridor.rooms_v2 import (lift_shaft, conveyor_gallery,
                                            spring_yard)
    service = lift_shaft(
        _PAL_R1, "SERVICE ELEVATORS",
        bax_enter_line="Service lifts. Guests never see this side. Neither should we.")
    luggage = conveyor_gallery(
        _PAL_R2, "LUGGAGE HANDLING",
        bax_enter_line="Luggage belts. Try not to end up in a suite you can't afford.")
    laundry = spring_yard(
        _PAL_R2, "LAUNDRY CHUTES",
        secret_lore="A guest ledger page in a pillowcase: room 4707, "
                    "paid in full, name redacted by hand. Twice.",
        bax_enter_line="Laundry room. Everything bounces. EVERYTHING.")

    return Corridor(
        chapter          = 4,
        rooms            = [room1, service, room2, luggage, laundry, room3],
        cargo_silhouette = "vip",
    )
