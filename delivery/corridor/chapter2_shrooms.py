"""
Chapter 2 — Mycorrhizal Payload corridor.
Theme: bioluminescent biolab. Walls breathe. Reality flickers.
"""
from __future__ import annotations
import math
import random
import pygame

from delivery.corridor.elements import (
    Platform, MovingPlatform, Hazard, MovingHazard, Ladder,
    ToggleBeam, NPCEncounter, Collectible, Secret, Checkpoint,
    BossRoomTrigger, StealthZone, SporeZone,
    CORRIDOR_W, CORRIDOR_H, FLOOR_Y, CEIL_Y, PLAYER_H,
)
from delivery.corridor.base import Room, Corridor

_PAL_R1 = {
    "bg":            (4, 6, 12),
    "grid":          (10, 14, 28),
    "ceiling_fill":  (8, 10, 20),
    "ceiling_line":  (60, 80, 200),
    "floor_fill":    (6, 8, 18),
    "floor_line":    (50, 70, 180),
    "platform":      (20, 40, 100),
    "platform_hi":   (40, 80, 200),
    "light":         (60, 80, 200),
}
_PAL_R2 = {
    "bg":            (2, 6, 8),
    "grid":          (8, 18, 14),
    "ceiling_fill":  (4, 12, 10),
    "ceiling_line":  (60, 200, 100),
    "floor_fill":    (4, 10, 8),
    "floor_line":    (50, 180, 80),
    "platform":      (10, 80, 60),
    "platform_hi":   (40, 160, 100),
    "ladder":        (80, 180, 60),
    "light":         (80, 200, 100),
}
_PAL_R3 = {
    "bg":            (4, 10, 6),
    "grid":          (14, 28, 16),
    "ceiling_fill":  (8, 18, 10),
    "ceiling_line":  (100, 255, 120),
    "floor_fill":    (6, 14, 8),
    "floor_line":    (80, 220, 100),
    "platform":      (30, 120, 60),
    "platform_hi":   (80, 220, 120),
    "light":         (120, 255, 100),
}


def _bg_r1(surf, camera_x, t, pal):
    """Sterile decontam chamber — clean white-blue lab panels."""
    bg_off = camera_x * 0.5
    # Wall panels
    f = pygame.font.SysFont("monospace", 8)
    for wx in range(0, 2500, 200):
        sx = int(wx - bg_off)
        if -20 < sx < CORRIDOR_W + 20:
            pygame.draw.rect(surf, (6, 10, 22), (sx, CEIL_Y + 2, 180, 80))
            pygame.draw.rect(surf, (20, 40, 80), (sx, CEIL_Y + 2, 180, 80), 1)
            s = f.render("DECONTAM ZONE", True, (20, 40, 80))
            surf.blit(s, (sx + 4, CEIL_Y + 6))
    # Biohazard signs
    for wx2 in range(400, 2500, 600):
        sx2 = int(wx2 - bg_off)
        if -30 < sx2 < CORRIDOR_W + 30:
            pul = int(140 + 60 * abs(math.sin(t * 2.0 + wx2 * 0.001)))
            pygame.draw.circle(surf, (pul, pul // 4, 0), (sx2, FLOOR_Y - 50), 16, 2)
            pygame.draw.circle(surf, (pul, pul // 4, 0), (sx2, FLOOR_Y - 50), 5)


def _bg_r2(surf, camera_x, t, pal):
    """Growth gallery — breathing walls, bioluminescent fungi."""
    # Breathing wall pulse
    pulse = 0.5 + 0.5 * math.sin(t * 0.25 * 2 * math.pi)  # 4s cycle
    r_c   = int(8  + 4  * pulse)
    g_c   = int(20 + 10 * pulse)
    b_c   = int(12 + 6  * pulse)
    # Wall-wide glow
    wall_s = pygame.Surface((CORRIDOR_W, FLOOR_Y - CEIL_Y), pygame.SRCALPHA)
    wall_s.fill((int(r_c * 0.6), int(g_c * 0.6), int(b_c * 0.6), 30))
    surf.blit(wall_s, (0, CEIL_Y))
    # Fungi clusters
    rng = random.Random(77)
    bg_off = camera_x * 0.4
    for wx in range(100, 2800, 120):
        sx = int(wx - bg_off) % (CORRIDOR_W + 100) - 50
        fy = FLOOR_Y - rng.randint(10, 35)
        for _ in range(rng.randint(2, 5)):
            fx = sx + rng.randint(-15, 15)
            fh = rng.randint(6, 20)
            fw = rng.randint(3, 7)
            glow = int(80 + 60 * abs(math.sin(t * 1.2 + wx * 0.05)))
            pygame.draw.rect(surf, (0, glow, int(glow * 0.4)),
                             (fx - fw // 2, fy - fh, fw, fh))
            pygame.draw.circle(surf, (0, min(255, glow + 40), int(glow * 0.6)),
                               (fx, fy - fh), fw + 1)


def _bg_r3(surf, camera_x, t, pal):
    """Receiving lab — fully alive, overgrown equipment."""
    pulse = 0.5 + 0.5 * math.sin(t * 0.25 * 2 * math.pi)
    # Overgrown lab benches
    for bx in range(60, CORRIDOR_W, 120):
        by = FLOOR_Y - 40
        pygame.draw.rect(surf, (10, 24, 14), (bx, by, 100, 30))
        pygame.draw.rect(surf, (30, 80, 40), (bx, by, 100, 30), 1)
        # Equipment with fungi growing
        for ex in range(bx + 8, bx + 90, 18):
            eh = random.Random(ex * 3).randint(8, 22)
            glow = int(120 + 80 * abs(math.sin(t * 1.5 + ex * 0.08)))
            pygame.draw.rect(surf, (0, glow, int(glow * 0.5)),
                             (ex - 3, by - eh, 6, eh))
            pygame.draw.circle(surf, (0, min(255, glow + 50), int(glow * 0.7)),
                               (ex, by - eh), 4)
    # Researcher (spore-stained lab coat)
    rx, ry = CORRIDOR_W - 80, FLOOR_Y - 1
    pygame.draw.rect(surf, (20, 30, 22), (rx - 6, ry - 26, 12, 18))
    pygame.draw.circle(surf, (20, 30, 22), (rx, ry - 32), 8)
    for i in range(4):
        pygame.draw.circle(surf, (80, 220, 100),
                           (rx - 4 + i * 3, ry - 24 + i % 2 * 4), 2)


# NPC responses
_VALERIA_RESPONSES = [
    {
        "keywords": ["thank", "help", "kind", "compassion", "please", "good", "therapy"],
        "credits":  0,
        "lore":     "She opens the shortcut. Don't ask. Just walk.",
        "outcome":  "shortcut",
    },
    {
        "keywords": ["threat", "now", "hurry", "move", "security", "hostile"],
        "credits":  0,
        "lore":     "A StealthZone activates in Room 2. Nice work.",
        "outcome":  "penalty",
    },
    {
        "keywords": [],
        "credits":  0,
        "lore":     "",
        "outcome":  "pass",
    },
]
_LAB_TECH_RESPONSES = [
    {
        "keywords": ["hello", "here", "delivery", "jar", "package", "cargo", "fungi"],
        "credits":  200,
        "lore":     "The tech takes it gently. Their hands shake slightly.",
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
    # ── Room 1: DECONTAMINATION CHAMBER ─────────────────────────────────
    r1_elms = [
        # UV beams (toggling hazards)
        ToggleBeam(320, 180, (CEIL_Y + FLOOR_Y) // 2, period=1.5, phase=0.0),
        ToggleBeam(540, 180, (CEIL_Y + FLOOR_Y) // 2, period=1.5, phase=1.6),
        ToggleBeam(760, 180, (CEIL_Y + FLOOR_Y) // 2, period=1.8, phase=0.8),
        # Platforms to cross beams
        Platform(280, FLOOR_Y - 50, 80),
        Platform(460, FLOOR_Y - 50, 80),
        Platform(660, FLOOR_Y - 50, 80),
        # NPC Dr. Valeria
        NPCEncounter(
            500,
            "DR. VALERIA",
            "You're carrying growth material. Please — be careful with it. Are you... doing okay?",
            _VALERIA_RESPONSES,
        ),
        Checkpoint(880),
    ]
    room1 = Room(
        length     = 1000,
        palette    = _PAL_R1,
        elements   = r1_elms,
        bg_draw_fn = _bg_r1,
        bax_enter_line = "Biolab. Cabin smells funny. Don't breathe through your nose. Or your mouth. Just hold your breath the whole time, mate.",
        star3_t    = 22.0,
        star2_t    = 38.0,
    )

    # ── Room 2: GROWTH GALLERY (spore room) ─────────────────────────────
    r2_elms = [
        # Spore flicker zones
        SporeZone(280, 120),
        SporeZone(520, 100),
        SporeZone(780, 130),
        # Moving hazard drones
        MovingHazard(400, CEIL_Y + 40, 22, 18, left=340, right=500, speed=65),
        MovingHazard(700, CEIL_Y + 50, 22, 18, left=620, right=800, speed=75),
        # Platforms
        Platform(200, FLOOR_Y - 50, 80),
        Platform(480, FLOOR_Y - 55, 80),
        Platform(720, FLOOR_Y - 50, 80),
        # Branch — detour via ladder to ceiling vents
        Ladder(360, CEIL_Y, CEIL_Y + 80, path_tag="high"),
        Platform(400, CEIL_Y + 20, 200, path_tag="high"),
        Platform(650, CEIL_Y + 20, 160, path_tag="high"),
        # Secret in vent
        Secret(
            760, CEIL_Y + 30, value=600,
            lore="Memo: subject 4-A reported sensing a friend inside the spore cloud. Recommended therapy. Subject was decommissioned next quarter.",
            path_tag="high",
        ),
        Ladder(900, CEIL_Y, CEIL_Y + 80, path_tag="high"),
    ]
    room2 = Room(
        length     = 1100,
        palette    = _PAL_R2,
        elements   = r2_elms,
        bg_draw_fn = _bg_r2,
        branch_x   = 330.0,
        converge_x = 940.0,
        bax_enter_line = "Right, controls just went sideways. Sit with it. We've done this before.",
        star3_t    = 24.0,
        star2_t    = 42.0,
    )

    # ── Room 3: RECEIVING LAB (boss) ─────────────────────────────────────
    r3_elms = [
        BossRoomTrigger(
            180,
            bax_line="...the tech in there isn't okay. Be gentle. Hand over the jar. Don't make it weirder.",
        ),
        NPCEncounter(
            300,
            "LAB TECH (SPORE-STAINED)",
            "The... the jar. Yes. I'll take it now. Thank you for — for bringing it safely.",
            _LAB_TECH_RESPONSES,
        ),
    ]
    room3 = Room(
        length     = 450,
        palette    = _PAL_R3,
        elements   = r3_elms,
        bg_draw_fn = _bg_r3,
        bax_enter_line = "Almost done. The lab's alive in here. Try not to touch anything.",
        star3_t    = 60.0,
        star2_t    = 90.0,
    )

    return Corridor(
        chapter          = 2,
        rooms            = [room1, room2, room3],
        cargo_silhouette = "shroom",
    )
