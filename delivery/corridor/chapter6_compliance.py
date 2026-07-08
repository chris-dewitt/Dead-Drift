"""
Chapter 6 — Compliance.

Theme: Nova Soma Station. Glass, chrome, fluorescent, polite, terrifying.

Story beats wired in:
  Room 1: ELEVATOR — glass descent past 47 floors. Bax goes silent. You see.
  Room 2: SERVER ROOM — plug in the drive. 90-second upload while alarms scream.
  Room 3: ESCAPE   — chase corridor back to the ship. The building IS the boss.
"""
from __future__ import annotations
import math
import random
import pygame

from core.text import get_font
from delivery.corridor.elements import (
    Platform, Hazard, MovingHazard, Ladder, NPCEncounter, Collectible,
    Secret, Checkpoint, BossRoomTrigger, LoreRoom, NPCShortcut,
    SecurityBeam, SteamVent,
    CORRIDOR_W, CORRIDOR_H, FLOOR_Y, CEIL_Y, PLAYER_H,
)
from delivery.corridor.base import Room, Corridor


# Palette — clinical white/chrome with cold cyan accents. The opposite of ch5.
_PAL_R1 = {  # Elevator
    "bg":            (16, 20, 26),
    "grid":          (40, 50, 60),
    "ceiling_fill":  (28, 36, 44),
    "ceiling_line":  (180, 220, 240),
    "floor_fill":    (24, 30, 38),
    "floor_line":    (140, 180, 210),
    "platform":      (100, 130, 150),
    "platform_hi":   (220, 240, 255),
    "light":         (220, 240, 255),
    "light_tint":    (200, 230, 255),
    "light_alpha":   24,
    "deep_struct":   (40,  60,  80),
    "panel_num":     (180, 210, 230),
    "crack":         (40,  50,  60),
    "branding":      (160, 200, 220),
    "glass":         (90, 130, 170),
}
_PAL_R2 = {  # Server room
    "bg":            (6,  8, 14),
    "grid":          (14, 18, 28),
    "ceiling_fill":  (10, 14, 22),
    "ceiling_line":  (255, 200,  60),
    "floor_fill":    (8,  10, 18),
    "floor_line":    (220, 160,  40),
    "platform":      (50,  60,  90),
    "platform_hi":   (255, 200,  80),
    "light":         (255, 200,  60),
    "tower":         (16,  22,  36),
}
_PAL_R3 = {  # Escape — red emergency lighting
    "bg":            (20,  4,  4),
    "grid":          (50, 14, 14),
    "ceiling_fill":  (40, 10, 10),
    "ceiling_line":  (255, 50, 50),
    "floor_fill":    (30,  8,  8),
    "floor_line":    (220, 60, 60),
    "platform":      (140, 40, 40),
    "platform_hi":   (255, 90, 90),
    "light":         (255, 60, 60),
}


# ---------------------------------------------------------------------------
def _bg_r1(surf, camera_x, t, pal):
    """ELEVATOR — glass walls, you can see the floors going by."""
    surf.fill(pal["bg"])

    # Ceiling / floor are the elevator's interior frame
    pygame.draw.line(surf, pal["ceiling_line"], (0, CEIL_Y), (CORRIDOR_W, CEIL_Y), 2)
    pygame.draw.line(surf, pal["floor_line"], (0, FLOOR_Y), (CORRIDOR_W, FLOOR_Y), 2)

    # Floor numbers descending — synced to camera_x as the elevator descends
    f12 = get_font(12, bold=True)
    f8  = get_font(8)
    floor_now = 47 - int(camera_x / 120)
    floor_label = f"FLOOR  {max(0, floor_now):02d}"
    fl_s = f12.render(floor_label, True, (200, 230, 255))
    surf.blit(fl_s, (CORRIDOR_W - fl_s.get_width() - 24, CEIL_Y + 10))

    # Vignettes through the glass — different scenes at different camera positions
    scenes = [
        (200,   "BULLPEN — COLLECTIONS DESK 47"),
        (700,   "BULLPEN — COLLECTIONS DESK 38"),
        (1200,  "CLONE TANK BAY — FLOOR 31"),
        (1700,  "EXECUTIVE DINING — FLOOR 22"),
        (2100,  "SERVER FLOOR — RESTRICTED"),
        (2600,  "LOBBY — GROUND LEVEL"),
    ]
    for sx, label in scenes:
        rx = sx - int(camera_x)
        if -200 < rx < CORRIDOR_W + 200:
            # Glass panel
            glass = pygame.Rect(rx, CEIL_Y + 30, 220, FLOOR_Y - CEIL_Y - 60)
            gs = pygame.Surface(glass.size, pygame.SRCALPHA)
            gs.fill((90, 130, 170, 40))
            surf.blit(gs, glass.topleft)
            pygame.draw.rect(surf, pal["glass"], glass, 1)
            # Faint silhouettes of people at desks
            for fx in range(6):
                for fy in range(3):
                    px = glass.x + 16 + fx * 32
                    py = glass.y + 20 + fy * 38
                    pygame.draw.rect(surf, (50, 80, 110), (px, py, 12, 18))
                    pygame.draw.circle(surf, (70, 110, 140), (px + 6, py - 4), 4)
            # Label
            lbl = f8.render(label, True, (160, 200, 230))
            surf.blit(lbl, (glass.x + 4, glass.bottom + 4))


def _bg_r2(surf, camera_x, t, pal):
    """SERVER ROOM — black towers, amber blinking lights, COLD."""
    surf.fill(pal["bg"])
    pygame.draw.line(surf, pal["ceiling_line"], (0, CEIL_Y), (CORRIDOR_W, CEIL_Y), 2)
    pygame.draw.line(surf, pal["floor_line"], (0, FLOOR_Y), (CORRIDOR_W, FLOOR_Y), 2)

    # Rows of server towers
    off = int(camera_x * 0.4)
    for col in range(16):
        cx = 60 + col * 110 - off
        if -80 < cx < CORRIDOR_W + 80:
            tower = pygame.Rect(cx, CEIL_Y + 30, 70, FLOOR_Y - CEIL_Y - 80)
            pygame.draw.rect(surf, pal["tower"], tower)
            pygame.draw.rect(surf, (60, 70, 100), tower, 1)
            # Blinking amber LEDs
            blink = (math.sin(t * 4.0 + col * 0.7) > 0)
            color = (255, 200, 60) if blink else (90, 70, 20)
            for row in range(4):
                ly = tower.y + 20 + row * 30
                pygame.draw.rect(surf, color, (tower.x + 6, ly, 3, 3))
                pygame.draw.rect(surf, color, (tower.right - 9, ly, 3, 3))


def _bg_r3(surf, camera_x, t, pal):
    """ESCAPE — red alert. Strobing emergency lights. The building hunts you."""
    # Strobe between dark and red-tinted
    flash = (math.sin(t * 7.0) > 0)
    base  = (30, 6, 6) if flash else pal["bg"]
    surf.fill(base)
    pygame.draw.line(surf, pal["ceiling_line"], (0, CEIL_Y), (CORRIDOR_W, CEIL_Y), 2)
    pygame.draw.line(surf, pal["floor_line"], (0, FLOOR_Y), (CORRIDOR_W, FLOOR_Y), 2)
    # Rotating strobe lights on the ceiling
    for bx in range(160, CORRIDOR_W, 300):
        rx = bx - int(camera_x * 0.3)
        if -40 < rx < CORRIDOR_W + 40:
            pulse = 0.4 + 0.6 * abs(math.sin(t * 6.0 + bx * 0.01))
            pygame.draw.circle(surf, (int(255 * pulse), 40, 40),
                               (rx, CEIL_Y + 18), 5)


# ---------------------------------------------------------------------------
# Bowen — boss-room encounter at the server room. Polite to the end.
_BOWEN_RESPONSES = [
    {"keywords": ["okay", "fine", "sure", "yes", "comply", "wait"],
     "credits": 0, "lore": "Bowen smiles. Security arrives. Everything ends here.",
     "outcome": "penalty"},
    {"keywords": ["no", "never", "won't", "make me", "no way"],
     "credits": 0, "lore": "Bowen's smile holds, but he steps aside. 'I had to ask.'",
     "outcome": "release"},
    {"keywords": ["clone tanks", "the names", "i saw them", "your workers"],
     "credits": 600, "lore": "Bowen's face cracks for a half-second. He waves you through.",
     "outcome": "release"},
    {"keywords": ["your family", "the photo", "lanyard", "your kids"],
     "credits": 800, "lore": "Bowen freezes. 'Just— go. Forty seconds. Go.'",
     "outcome": "release"},
    {"penalty_default": True,
     "credits": 0, "lore": "Security arrives while Bowen apologises.",
     "outcome": "penalty"},
]


# ---------------------------------------------------------------------------
def build() -> Corridor:
    """Build chapter 6 — Nova Soma Station."""

    # ── Room 1: THE ELEVATOR ──────────────────────────────────────────────
    # Long horizontal traversal representing a 47-floor descent. Bax goes
    # quiet. The player just walks, watches the floors pass.
    r1_len = 2800
    r1_elms = [
        Platform(120, FLOOR_Y - 8, 220, path_tag=None),
        # G.6 — the moments through the glass become lore drops
        LoreRoom(
            320,
            "Floor 47. Open bullpen. Hundreds of collectors at terminals. "
            "Each screen shows a name and a number. None of them look up.",
            chapter=6, npc_voice="THROUGH THE GLASS", path_tag=None,
        ),
        LoreRoom(
            900,
            "Floor 31. Clone tank bay. Rows of them. Labels with names. "
            "You read three before you have to look away.",
            chapter=6, npc_voice="THROUGH THE GLASS", path_tag=None,
        ),
        LoreRoom(
            1500,
            "Floor 22. A single corner office. A man eating lunch alone, "
            "staring at nothing. A family photo on his desk. You think it's Bowen.",
            chapter=6, npc_voice="THROUGH THE GLASS", path_tag=None,
        ),
        LoreRoom(
            2050,
            "Floor 12. The server room slides past. Black towers, amber lights. "
            "The whole ledger. Right there.",
            chapter=6, npc_voice="THROUGH THE GLASS", path_tag=None,
        ),
        Secret(2400, FLOOR_Y - 60, value=500,
               lore="Stuck to the inside of the elevator: a sticky note. 'YOU CAN STILL TURN BACK.' "
                    "Old. Yellowed. Someone — long before you — almost did.",
               path_tag=None),
        Checkpoint(2680),
    ]
    room1 = Room(
        length      = r1_len,
        palette     = _PAL_R1,
        elements    = r1_elms,
        bg_draw_fn  = _bg_r1,
        bax_enter_line = "...I'll be quiet. Just look. Forty-seven floors. Look at all of it.",
        star3_t     = 30.0,
        star2_t     = 50.0,
        name        = "THE ELEVATOR  //  47 → 0",
    )

    # ── Room 2: SERVER ROOM ───────────────────────────────────────────────
    # The boss-room of the chapter. Bowen meets you here. You plug in
    # the drive — handled by the boss-room actor — and then chase begins.
    r2_len = 700
    r2_elms = [
        NPCEncounter(
            300,
            "BOWEN — ASST. DIR. COMPLIANCE",
            "Hello, courier. I'm afraid we've detected an irregularity. "
            "Could you please remain where you are?",
            _BOWEN_RESPONSES,
        ),
        BossRoomTrigger(
            120,
            bax_line="There he is. The smiley one. Don't agree to anything. "
                     "Plug in the damn drive. I'll keep an eye on the door.",
        ),
        LoreRoom(
            520,
            "The drive slot is small, unremarkable. You plug it in. "
            "The screen turns white. UPLOAD: 0% / 90s. Bax whispers: 'Hold the line.'",
            chapter=6, npc_voice="THE TERMINAL", path_tag=None,
        ),
    ]
    room2 = Room(
        length     = r2_len,
        palette    = _PAL_R2,
        elements   = r2_elms,
        bg_draw_fn = _bg_r2,
        bax_enter_line = "Server room. Black towers. Whole ledger's in here. Don't blink.",
        star3_t    = 60.0,
        star2_t    = 90.0,
        name       = "SERVER ROOM  //  FLOOR 12",
    )

    # ── Room 3: THE ESCAPE ────────────────────────────────────────────────
    # Forced-momentum chase. Heavy hazards, security beams, fast scrolling
    # palette. The building is now hostile.
    r3_len = 1600
    r3_elms = [
        Platform(120, FLOOR_Y - 8, 180, path_tag=None),
        # Security beams sweep the corridor — running through them is a hit
        SecurityBeam(380, CEIL_Y + 12, length=240, phase=0.0, path_tag=None),
        SecurityBeam(640, CEIL_Y + 12, length=240, phase=math.pi, path_tag=None),
        # Steam vents from sprinkler failure
        SteamVent(520, FLOOR_Y, phase_offset=0.4),
        SteamVent(780, FLOOR_Y, phase_offset=1.7),
        # A few mid-air hazards
        MovingHazard(900,  CEIL_Y + 40, 28, 28, left=850, right=1010, speed=140, path_tag=None),
        MovingHazard(1150, CEIL_Y + 40, 28, 28, left=1080, right=1240, speed=160, path_tag=None),
        Collectible(420, FLOOR_Y - 30, 200),
        Collectible(680, FLOOR_Y - 30, 200),
        Collectible(960, FLOOR_Y - 30, 200),
        Collectible(1240, FLOOR_Y - 30, 200),
        # Override-codes secret: opens a "shortcut door" (renders as a free credit drop here)
        Secret(1050, CEIL_Y + 80, value=600,
               lore="Override card 4-A. Door unlocks. Bax: 'Through here! Move move move!'",
               path_tag=None),
        Checkpoint(1400),
        # The blast door is the final beat — narratively the corridor's end
        LoreRoom(
            1500,
            "The blast door is closing. 40% open. 30%. 20%. "
            "You don't slow down. You don't look back. Bax is screaming RUN.",
            chapter=6, npc_voice="BAX", path_tag=None,
        ),
    ]
    room3 = Room(
        length     = r3_len,
        palette    = _PAL_R3,
        elements   = r3_elms,
        bg_draw_fn = _bg_r3,
        bax_enter_line = "RUN. They know. They know. RUN.",
        star3_t    = 28.0,
        star2_t    = 45.0,
        name       = "ESCAPE  //  BLAST DOOR CLOSING",
    )

    # Delivery v2 I.3b — parity pass + the campaign's one chase room.
    # Nova Soma's ledger floor: polite, fluorescent, closing in.
    from delivery.corridor.rooms_v2 import (conveyor_gallery, crate_warren,
                                            lift_shaft, chase_sweep)
    processing = conveyor_gallery(
        _PAL_R1, "PROCESSING FLOOR",
        bax_enter_line="Processing floor. The belts move paper. And evidence. And us.")
    lockup = crate_warren(
        _PAL_R2, "EVIDENCE LOCKUP",
        secret_lore="Evidence tag, case closed: one harmonica, "
                    "confiscated. Owner: 'G. Pruitt.' Gary, you dark horse.",
        bax_enter_line="Evidence lockup. Everything they took. In boxes. Labelled.")
    atrium = lift_shaft(
        _PAL_R2, "ATRIUM LIFTS",
        bax_enter_line="Atrium lifts. Glass everywhere. Wave at compliance, they log it.")
    sweep = chase_sweep(
        _PAL_R3, "COMPLIANCE SWEEP", speed=150.0,
        bax_enter_line="SWEEP PROTOCOL. The building is HERDING us. GO GO GO.")

    return Corridor(
        chapter          = 6,
        rooms            = [room1, processing, room2, lockup, atrium, sweep, room3],
        cargo_silhouette = "drive",
    )
