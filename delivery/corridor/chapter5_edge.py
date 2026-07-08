"""
Chapter 5 — The Edge.

Theme: the Remnants' off-grid station, deep in the outer belt.
Warm. Human. Cramped. The first place in Dead Drift that feels like home.

Story beats wired in:
  Room 1: ENTRY — a "Names Wall" of debt victims. Bax goes quiet.
  Room 2: WORKSHOP — Chen's whiteboard with the original ledger design.
  Room 3: CHEN — Chen hands you the drive. Fitz offers a shortcut out.
"""
from __future__ import annotations
import math
import random
import pygame

from core.text import get_font
from delivery.corridor.elements import (
    Platform, Ladder, NPCEncounter, Collectible, Secret, Checkpoint,
    BossRoomTrigger, LoreRoom, NPCShortcut,
    CORRIDOR_W, CORRIDOR_H, FLOOR_Y, CEIL_Y, PLAYER_H,
)
from delivery.corridor.base import Room, Corridor


# Palette — warm amber/red, hand-built feel. The opposite of corporate.
_PAL_R1 = {
    "tile_style":  "girder",   # I.4.1 chapter tile vocabulary
    "bg":            (10,  8,  6),
    "grid":          (28, 22, 16),
    "ceiling_fill":  (24, 18, 12),
    "ceiling_line":  (220, 150, 90),
    "floor_fill":    (16, 12,  8),
    "floor_line":    (180, 120, 70),
    "platform":      (90,  60, 30),
    "platform_hi":   (200, 140, 70),
    "light":         (255, 180, 90),
    "light_tint":    (220, 160, 90),
    "light_alpha":   22,
    "deep_struct":   (40,  28, 16),
    "panel_num":     (200, 140,  70),
    "crack":         (60,  35, 18),
    "branding":      (90,  60,  30),
}
_PAL_R2 = {
    "tile_style":  "girder",   # I.4.1 chapter tile vocabulary
    "bg":            (8,  10, 12),
    "grid":          (18, 24, 28),
    "ceiling_fill":  (14, 18, 22),
    "ceiling_line":  (100, 160, 200),
    "floor_fill":    (10, 14, 16),
    "floor_line":    (80, 130, 170),
    "platform":      (40,  70, 90),
    "platform_hi":   (90, 160, 220),
    "light":         (140, 200, 240),
}
_PAL_R3 = {
    "tile_style":  "girder",   # I.4.1 chapter tile vocabulary
    "bg":            (12, 10,  8),
    "grid":          (28, 22, 18),
    "ceiling_fill":  (22, 16, 14),
    "ceiling_line":  (255, 180, 120),
    "floor_fill":    (18, 14, 10),
    "floor_line":    (220, 150,  90),
    "platform":      (110, 70, 30),
    "platform_hi":   (220, 150, 70),
    "light":         (255, 200, 130),
}


# ---------------------------------------------------------------------------
def _bg_r1(surf, camera_x, t, pal):
    """Entry corridor — handwritten signs, photos on the walls."""
    surf.fill(pal["bg"])
    # Subtle grid
    for y in range(CEIL_Y, FLOOR_Y, 40):
        pygame.draw.line(surf, pal["grid"], (0, y), (CORRIDOR_W, y), 1)
    # Ceiling / floor lines
    pygame.draw.line(surf, pal["ceiling_line"], (0, CEIL_Y), (CORRIDOR_W, CEIL_Y), 2)
    pygame.draw.line(surf, pal["floor_line"], (0, FLOOR_Y), (CORRIDOR_W, FLOOR_Y), 2)

    # Names Wall — a column of dim rectangles representing printed photos
    f8 = get_font(8)
    off = int(camera_x * 0.3)
    for col in range(8):
        cx = 60 + col * 90 - off
        if -60 < cx < CORRIDOR_W + 60:
            for row in range(3):
                ry = CEIL_Y + 30 + row * 50
                photo = pygame.Rect(cx, ry, 36, 30)
                pygame.draw.rect(surf, (30, 22, 16), photo)
                pygame.draw.rect(surf, (90, 60, 30), photo, 1)
                # Faint name label below
                label = f8.render(f"#{(col*3 + row) * 31:05d}", True, (110, 80, 50))
                surf.blit(label, (cx, ry + 32))

    # Warm hanging bulb
    glow = 0.7 + 0.3 * math.sin(t * 1.3)
    for bx in range(120, CORRIDOR_W, 280):
        rx = bx - int(camera_x * 0.4)
        if -40 < rx < CORRIDOR_W + 40:
            pygame.draw.circle(surf, (int(255 * glow), int(180 * glow), 90),
                               (rx, CEIL_Y + 18), 5)
            pygame.draw.line(surf, (60, 40, 20), (rx, CEIL_Y), (rx, CEIL_Y + 14), 1)


def _bg_r2(surf, camera_x, t, pal):
    """Chen's workshop — cool blue, schematics on whiteboards."""
    surf.fill(pal["bg"])
    pygame.draw.line(surf, pal["ceiling_line"], (0, CEIL_Y), (CORRIDOR_W, CEIL_Y), 2)
    pygame.draw.line(surf, pal["floor_line"], (0, FLOOR_Y), (CORRIDOR_W, FLOOR_Y), 2)

    # Whiteboards on the back wall — Chen's design notes
    f8 = get_font(8)
    off = int(camera_x * 0.25)
    for i, label in enumerate(("LEDGER ROOT TABLE",
                                "INTEREST CASCADE",
                                "CLONE FEE LOOP",
                                "EXPLOIT: ZERO-WRITE")):
        bx = 80 + i * 320 - off
        if -100 < bx < CORRIDOR_W + 100:
            board = pygame.Rect(bx, CEIL_Y + 22, 240, 110)
            pygame.draw.rect(surf, (220, 230, 240), board)
            pygame.draw.rect(surf, (90, 140, 180), board, 1)
            # Faux schematic lines
            for j in range(5):
                pygame.draw.line(surf, (60, 100, 140),
                                 (bx + 14, CEIL_Y + 40 + j * 16),
                                 (bx + 220, CEIL_Y + 40 + j * 16), 1)
            tag = f8.render(label, True, (40, 70, 110))
            surf.blit(tag, (bx + 8, CEIL_Y + 26))


def _bg_r3(surf, camera_x, t, pal):
    """Chen's office — warm again, single desk, single light."""
    surf.fill(pal["bg"])
    pygame.draw.line(surf, pal["ceiling_line"], (0, CEIL_Y), (CORRIDOR_W, CEIL_Y), 2)
    pygame.draw.line(surf, pal["floor_line"], (0, FLOOR_Y), (CORRIDOR_W, FLOOR_Y), 2)
    # Desk silhouette at center
    desk = pygame.Rect(180, FLOOR_Y - 36, 140, 36)
    pygame.draw.rect(surf, (60, 40, 20), desk)
    pygame.draw.rect(surf, (160, 100, 50), desk, 1)
    # Lamp glow
    glow = 0.7 + 0.3 * math.sin(t * 1.7)
    pygame.draw.circle(surf, (int(255 * glow), int(200 * glow), 130),
                       (250, FLOOR_Y - 80), 6)
    pygame.draw.line(surf, (60, 40, 20), (250, FLOOR_Y - 36), (250, FLOOR_Y - 74), 1)


# ---------------------------------------------------------------------------
# Chen — boss-room encounter. The "interrogation" is the terminal flow,
# this on-corridor encounter just hands the drive over.
_CHEN_RESPONSES = [
    {"keywords": ["thank", "thanks", "appreciate", "honour", "honor"],
     "credits": 0, "lore": "Chen nods. 'Don't thank me. Just don't die.'",
     "outcome": "release"},
    {"keywords": ["take it", "give me", "ready", "let's go", "lets go"],
     "credits": 0, "lore": "Chen hands you the drive. 'Floor twelve. Ninety seconds. Go.'",
     "outcome": "release"},
    {"keywords": ["why", "how does it work", "what is it"],
     "credits": 0, "lore": "Chen: 'It zeros the field. Every entry, galactic. Plug in, hold the line.'",
     "outcome": "release"},
    {"penalty_default": True,
     "credits": 0, "lore": "Chen waits, drive in hand. Says nothing.",
     "outcome": "penalty"},
]


# ---------------------------------------------------------------------------
def build() -> Corridor:
    """Build chapter 5 — the Remnants' station."""
    # Room 1: NAMES WALL — long, quiet, no platforming
    r1_len = 1200
    r1_elms = [
        # A single low platform to walk on; this is mostly a scrolling beat
        Platform(120, FLOOR_Y - 8, 200, path_tag=None),
        # Collectibles scattered like coins on the floor — old credit chits
        Collectible(280, FLOOR_Y - 26, 200),
        Collectible(460, FLOOR_Y - 26, 200),
        Collectible(640, FLOOR_Y - 26, 200),
        Collectible(820, FLOOR_Y - 26, 200),
        Collectible(980, FLOOR_Y - 26, 200),
        # The wall itself — Bax's first reaction
        LoreRoom(
            420,
            "Pinned to the wall: a name, an amount, a date. Hundreds of them. "
            "Some have small notes. 'She made it three years.' 'Owed seventeen. Cloned twice.'",
            chapter=5, npc_voice="THE WALL", path_tag=None,
        ),
        # Hidden — a child's drawing taped behind a panel
        Secret(900, FLOOR_Y - 60, value=400,
               lore="A child's drawing of a starship, pinned behind a service panel. "
                    "Signed 'For mom. love, Tey.' Tey's mom is on the wall.",
               path_tag=None),
        Checkpoint(1130),
    ]
    room1 = Room(
        length      = r1_len,
        palette     = _PAL_R1,
        elements    = r1_elms,
        bg_draw_fn  = _bg_r1,
        bax_enter_line = "...take a breath. This is The Edge. Marrow's people. Don't shoot anyone.",
        star3_t     = 25.0,
        star2_t     = 45.0,
        name        = "THE NAMES WALL",
    )

    # Room 2: WORKSHOP — Chen's whiteboards
    r2_len = 1100
    r2_elms = [
        Platform(120, FLOOR_Y - 8, 200, path_tag=None),
        # The schematic itself — explains the exploit
        LoreRoom(
            260,
            "Chen's design notes: 'The ledger writes interest as a side effect of any read. "
            "It can't be paid down. It was never meant to be. I left one root-level zero-write. "
            "I called it MERCY. It's been waiting fifteen years.'",
            chapter=5, npc_voice="CHEN", path_tag=None,
        ),
        Collectible(400, FLOOR_Y - 30, 200),
        Collectible(560, FLOOR_Y - 30, 200),
        Collectible(720, FLOOR_Y - 30, 200),
        # A Remnant working on a drone — short overheard exchange
        Secret(880, FLOOR_Y - 60, value=300,
               lore="A Remnant looks up from her workbench. 'You're the one Marrow keeps "
                    "talking about. Try not to die. We've been waiting a long time.'",
               path_tag=None),
        Checkpoint(1040),
    ]
    room2 = Room(
        length      = r2_len,
        palette     = _PAL_R2,
        elements    = r2_elms,
        bg_draw_fn  = _bg_r2,
        bax_enter_line = "Workshop. They built somethin' down here. Look at the whiteboards.",
        star3_t     = 22.0,
        star2_t     = 38.0,
        name        = "THE WORKSHOP",
    )

    # Room 3: CHEN — boss room. Chen hands over the drive.
    r3_len = 600
    r3_elms = [
        NPCEncounter(
            260,
            "CHEN — ARCHITECT",
            "I built the cage. I made the key. Take it.",
            _CHEN_RESPONSES,
        ),
        BossRoomTrigger(
            120,
            bax_line="That's her. Chen. She wrote the whole damn ledger. "
                     "Be polite. She's the one with the way out.",
        ),
        # Fitz's shortcut — free, but he wants a word
        NPCShortcut(
            420, "FITZ",
            flavor="Engineering hatch. Fitz says walk out his way. He won't take credits.",
            skip_x=560, cost=0, path_tag=None,
        ),
    ]
    room3 = Room(
        length     = r3_len,
        palette    = _PAL_R3,
        elements   = r3_elms,
        bg_draw_fn = _bg_r3,
        bax_enter_line = "She's right there. Don't muck this up.",
        star3_t    = 60.0,
        star2_t    = 90.0,
        name       = "CHEN'S OFFICE",
    )

    # Delivery v2 I.3b — parity pass: The Edge was the leanest corridor;
    # four new rooms in the warm, hand-built Remnants register.
    from delivery.corridor.rooms_v2 import (spring_yard, crate_warren,
                                            lift_shaft, pipe_junction)
    greenhouse = spring_yard(
        _PAL_R1, "THE GREENHOUSE",
        secret_lore="Seed packets in a coffee tin. Hand-labelled: "
                    "'FOR AFTER. There is an after.'",
        bax_enter_line="A greenhouse. On a station. These people GROW things. I love them.")
    hold = crate_warren(
        _PAL_R2, "SUPPLY HOLD",
        secret_lore="Ration crate, false bottom: children's drawings of "
                    "ships. All of them are leaving Nova Soma.",
        bax_enter_line="Supply hold. Everything's mended twice and labelled by hand.")
    tower = lift_shaft(
        _PAL_R2, "WATER TOWER",
        bax_enter_line="Water tower. The lifts run on counterweights. Bax approves of honest machinery.")
    reclaim = pipe_junction(
        _PAL_R3, "RECLAIM DUCTS",
        secret_lore="Stencilled inside the duct: 'BUILT BY THE FIRST "
                    "HUNDRED.' Names beneath, worn smooth by hands.",
        bax_enter_line="Reclaim ducts. Nothing wasted out here. Not even shortcuts.")

    return Corridor(
        chapter          = 5,
        rooms            = [room1, greenhouse, room2, hold, tower, reclaim, room3],
        cargo_silhouette = "drive",
    )
