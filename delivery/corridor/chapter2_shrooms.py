"""
Chapter 2 — Mycorrhizal Payload corridor.
Theme: bioluminescent biolab. Walls breathe. Reality flickers.
"""
from __future__ import annotations
import math
import random
import pygame

from core.text import get_font
from delivery.corridor.elements import (
    Platform, MovingPlatform, Hazard, MovingHazard, Ladder,
    ToggleBeam, NPCEncounter, Collectible, Secret, Checkpoint,
    BossRoomTrigger, StealthZone, SporeZone,
    SteamVent, Tripwire, SecurityBeam,
    BossRoomActor, boss_actor_mycelium_chamber,
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
    "brick":         (50, 30, 90),
    "brick_hi":      (140, 100, 255),
    "light":         (120, 180, 255),
    # Epic 10.4 — sterile cold biolab lighting
    "light_tint":    (60,  120, 200),
    "light_alpha":   22,
    "deep_struct":   (8,   20,  40),
    "panel_num":     (90, 130, 200),
    "crack":         (30,  50,  90),
    "branding":      (70,  90, 130),
    "scrub":         (30,  40,  80),
    "floor_grid":    (40,  60, 100),
    "floor_wear":    (30,  44,  72),
    "drip":          (120, 200, 255),
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
    """Decontam chamber — drifting spores, UV strips, vivid biohazard signs, warning lines."""
    bg_off = camera_x * 0.5
    f8 = get_font(8)

    # ── Clean lab wall panels ─────────────────────────────────────────────
    for wx in range(0, 2600, 190):
        sx = int(wx - bg_off * 0.4)
        if -20 < sx < CORRIDOR_W + 20:
            pygame.draw.rect(surf, (5, 9, 22), (sx, CEIL_Y + 2, 170, FLOOR_Y - CEIL_Y - 4))
            pygame.draw.rect(surf, (16, 32, 72), (sx, CEIL_Y + 2, 170, FLOOR_Y - CEIL_Y - 4), 1)
            s = f8.render("DECONTAM ZONE", True, (16, 32, 72))
            surf.blit(s, (sx + 4, CEIL_Y + 6))

    # ── UV light strip zones (purple-washed overlays) ─────────────────────
    uv_off = camera_x * 0.45
    for wx in range(120, 2400, 380):
        sx = int(wx - uv_off)
        if -20 < sx < CORRIDOR_W + 20:
            uv_pulse = int(18 + 12 * math.sin(t * 1.8 + wx * 0.005))
            uv_s = pygame.Surface((60, FLOOR_Y - CEIL_Y), pygame.SRCALPHA)
            uv_s.fill((100, 20, 200, uv_pulse))
            surf.blit(uv_s, (sx, CEIL_Y))
            # UV strip light on ceiling
            pygame.draw.line(surf, (140, 60, 255), (sx, CEIL_Y + 3), (sx + 60, CEIL_Y + 3), 2)

    # ── Warning hazard lines on floor ─────────────────────────────────────
    stripe_off = int(camera_x * 0.5) % 40
    for sx in range(-stripe_off, CORRIDOR_W + 40, 40):
        # Yellow/black chevron stripes near floor
        col_stripe = (160, 140, 0) if (sx // 40) % 2 == 0 else (20, 20, 20)
        pygame.draw.rect(surf, col_stripe, (sx, FLOOR_Y - 8, 20, 6))

    # ── Floating spore particles (deterministic drift) ────────────────────
    for i in range(18):
        seed = i * 137 + 42
        wx_base = (seed * 31 + int(t * 25 + i * 137)) % (CORRIDOR_W + 60) - 30
        # Vertical: drift upward slowly, wrapping in wall zone
        wy_base = CEIL_Y + 5 + ((seed * 53 + int(t * 18 + i * 97)) % (FLOOR_Y - CEIL_Y - 10))
        # Horizontal parallax with camera
        sx = int(wx_base - camera_x * 0.3) % (CORRIDOR_W + 60) - 30
        sy = wy_base
        radius = 2 + (i % 3)
        alpha = 110 + (i * 13) % 50
        sp_s = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        # Teal/cyan spores in decontam
        r_col = (30 + (i * 17) % 40, 160 + (i * 23) % 80, 200 + (i * 11) % 55)
        pygame.draw.circle(sp_s, (*r_col, alpha), (radius + 2, radius + 2), radius)
        surf.blit(sp_s, (sx - radius - 2, sy - radius - 2))

    # ── Biohazard signs (vivid, animated outer glow rings) ────────────────
    for wx2 in range(360, 2500, 580):
        sx2 = int(wx2 - bg_off)
        if -40 < sx2 < CORRIDOR_W + 40:
            pul = abs(math.sin(t * 2.2 + wx2 * 0.0012))
            bright = int(120 + 120 * pul)
            col_bh = (bright, max(0, bright // 5), 0)
            # Outer pulsing glow rings
            glow_r = int(20 + 6 * pul)
            for gr_i, gr_r in enumerate([glow_r + 8, glow_r + 4, glow_r]):
                ga = int(30 - gr_i * 10)
                gr_s = pygame.Surface((gr_r * 2 + 4, gr_r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(gr_s, (*col_bh, ga), (gr_r + 2, gr_r + 2), gr_r, 2)
                surf.blit(gr_s, (sx2 - gr_r - 2, FLOOR_Y - 54 - gr_r - 2))
            # Main ring
            pygame.draw.circle(surf, col_bh, (sx2, FLOOR_Y - 54), 16, 3)
            # Inner circle
            pygame.draw.circle(surf, col_bh, (sx2, FLOOR_Y - 54), 5)
            # Three curved segments (simplified biohazard)
            for seg in range(3):
                ang = math.radians(seg * 120 + t * 30)
                ex = sx2 + int(11 * math.cos(ang))
                ey = FLOOR_Y - 54 + int(11 * math.sin(ang))
                pygame.draw.circle(surf, col_bh, (ex, ey), 4, 2)


def _bg_r2(surf, camera_x, t, pal):
    """Growth gallery — breathing wall glow, elaborate floor+ceiling fungi, spores, bio streaks."""
    bg_off = camera_x * 0.4

    # ── Breathing wall glow (6s cyan↔green cycle, dramatic) ──────────────
    pulse6 = 0.5 + 0.5 * math.sin(t * math.pi / 3.0)  # 6s cycle
    r_c = int(4  + 6  * (1 - pulse6))
    g_c = int(30 + 60 * pulse6)
    b_c = int(18 + 50 * (1 - pulse6))
    wall_s = pygame.Surface((CORRIDOR_W, FLOOR_Y - CEIL_Y), pygame.SRCALPHA)
    wall_s.fill((r_c, g_c, b_c, 38))
    surf.blit(wall_s, (0, CEIL_Y))

    # ── Color-cycling wall patches ────────────────────────────────────────
    patch_off = camera_x * 0.35
    for i, wx in enumerate(range(80, 2600, 180)):
        sx = int(wx - patch_off) % (CORRIDOR_W + 80) - 40
        phase = t * 0.8 + i * 2.1
        pr = int(20 * abs(math.sin(phase)))
        pg = int(60 + 80 * abs(math.sin(phase + 2.1)))
        pb = int(40 + 60 * abs(math.sin(phase + 4.2)))
        patch = pygame.Surface((50, 30), pygame.SRCALPHA)
        patch.fill((pr, pg, pb, 28))
        surf.blit(patch, (sx, CEIL_Y + 20 + (i % 3) * 15))

    # ── Bioluminescent floor streaks (horizontal glowing lines) ──────────
    streak_off = camera_x * 0.55
    for i in range(6):
        rng_s = random.Random(i * 41 + 200)
        sx_start = int(rng_s.randint(0, 2400) - streak_off) % (CORRIDOR_W + 200) - 100
        streak_len = rng_s.randint(60, 140)
        streak_y = FLOOR_Y - 4 - rng_s.randint(0, 8)
        glow_str = int(80 + 100 * abs(math.sin(t * 1.4 + i * 1.7)))
        for thickness in [3, 1]:
            alpha_str = 60 if thickness == 3 else 140
            str_s = pygame.Surface((streak_len, thickness + 2), pygame.SRCALPHA)
            str_s.fill((0, glow_str, int(glow_str * 0.5), alpha_str))
            surf.blit(str_s, (sx_start, streak_y))

    # ── Elaborate fungi on FLOOR (dense clusters) ─────────────────────────
    rng_f = random.Random(77)
    for wx in range(60, 2800, 90):
        sx = int(wx - bg_off) % (CORRIDOR_W + 100) - 50
        for _ in range(rng_f.randint(3, 7)):
            fx = sx + rng_f.randint(-18, 18)
            fh = rng_f.randint(8, 28)
            fw = rng_f.randint(2, 6)
            base_glow = int(70 + 100 * abs(math.sin(t * 1.3 + wx * 0.048)))
            # Stem
            stem_g = min(255, base_glow)
            pygame.draw.rect(surf, (0, stem_g, int(stem_g * 0.38)),
                             (fx - fw // 2, FLOOR_Y - fh, fw, fh))
            # Cap (wider ellipse-like with circle)
            cap_r = fw + 2
            cap_g = min(255, base_glow + 50)
            pygame.draw.circle(surf, (0, cap_g, int(cap_g * 0.55)),
                               (fx, FLOOR_Y - fh), cap_r)
            # Bright tip glow
            tip_s = pygame.Surface((cap_r * 2 + 4, cap_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(tip_s, (20, min(255, cap_g + 40), 80, 60),
                               (cap_r + 2, cap_r + 2), cap_r)
            surf.blit(tip_s, (fx - cap_r - 2, FLOOR_Y - fh - cap_r - 2))

    # ── Elaborate fungi hanging from CEILING (inverted) ───────────────────
    rng_c = random.Random(123)
    for wx in range(100, 2600, 130):
        sx = int(wx - bg_off * 0.5) % (CORRIDOR_W + 100) - 50
        for _ in range(rng_c.randint(2, 5)):
            fx = sx + rng_c.randint(-16, 16)
            fh = rng_c.randint(6, 18)  # hangs downward
            fw = rng_c.randint(2, 5)
            base_glow = int(60 + 90 * abs(math.sin(t * 1.1 + wx * 0.052 + 1.3)))
            # Stem hanging down from ceiling
            pygame.draw.rect(surf, (0, base_glow, int(base_glow * 0.45)),
                             (fx - fw // 2, CEIL_Y + 2, fw, fh))
            # Cap at the bottom
            cap_r = fw + 2
            cap_g = min(255, base_glow + 45)
            pygame.draw.circle(surf, (0, cap_g, int(cap_g * 0.5)),
                               (fx, CEIL_Y + 2 + fh), cap_r)

    # ── Floating spore particles (SRCALPHA, drifting slowly upward) ───────
    for i in range(22):
        seed = i * 97 + 13
        sx = int(seed * 43 - camera_x * 0.32) % (CORRIDOR_W + 40) - 20
        # Drift upward: wy decreases with t, wraps in wall zone
        raw_y = (seed * 67 - int(t * 15 + i * 55)) % (FLOOR_Y - CEIL_Y - 6)
        sy = CEIL_Y + 3 + raw_y
        r = 1 + (i % 4)
        a = 100 + (i * 19) % 60
        sp_col = (20 + (i * 13) % 30, 160 + (i * 17) % 95, 100 + (i * 31) % 155)
        sp_s = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(sp_s, (*sp_col, a), (r + 2, r + 2), r)
        surf.blit(sp_s, (sx - r - 2, sy - r - 2))


def _bg_r3(surf, camera_x, t, pal):
    """Receiving lab — tendrils on walls, glowing patches, dense fungi, spore fog, detailed researcher."""
    bg_off = camera_x * 0.4

    # ── Spore fog layers (low-opacity SRCALPHA rects) ─────────────────────
    for fi in range(4):
        fog_off = camera_x * (0.28 + fi * 0.05)
        fx = int(fi * 190 - fog_off) % (CORRIDOR_W + 120) - 60
        fog_h = 20 + fi * 8
        fog_y = FLOOR_Y - fog_h - fi * 4
        fa = int(14 + 8 * math.sin(t * 0.6 + fi * 1.9))
        fog_s = pygame.Surface((CORRIDOR_W, fog_h), pygame.SRCALPHA)
        fog_s.fill((10, 80 + fi * 20, 40 + fi * 15, fa))
        surf.blit(fog_s, (0, fog_y))

    # ── Tendrils/vines growing on walls (sinuous polylines) ───────────────
    tendril_off = camera_x * 0.36
    for wi in range(6):
        rng_t = random.Random(wi * 53 + 300)
        base_x = int(rng_t.randint(80, 2400) - tendril_off) % (CORRIDOR_W + 60) - 30
        # From floor upward
        pts = []
        cx2, cy2 = base_x, FLOOR_Y - 2
        for step in range(10):
            drift = int(6 * math.sin(t * 0.8 + wi * 1.3 + step * 0.7))
            cy2 -= rng_t.randint(5, 10)
            cx2 += drift + rng_t.randint(-3, 3)
            pts.append((cx2, cy2))
        if len(pts) >= 2:
            glow_t = int(60 + 100 * abs(math.sin(t * 1.1 + wi * 0.9)))
            pygame.draw.lines(surf, (0, glow_t, int(glow_t * 0.4)), False, pts, 2)
            # Bioluminescent nodes on tendril
            for pt in pts[::3]:
                nd_s = pygame.Surface((8, 8), pygame.SRCALPHA)
                pygame.draw.circle(nd_s, (0, min(255, glow_t + 60), 60, 80), (4, 4), 3)
                surf.blit(nd_s, (pt[0] - 4, pt[1] - 4))
        # From ceiling downward
        cx3, cy3 = base_x + rng_t.randint(-20, 20), CEIL_Y + 2
        pts2 = []
        for step in range(7):
            drift2 = int(5 * math.sin(t * 0.7 + wi * 2.1 + step * 1.1))
            cy3 += rng_t.randint(4, 8)
            cx3 += drift2
            pts2.append((cx3, cy3))
        if len(pts2) >= 2:
            glow_t2 = int(50 + 80 * abs(math.sin(t * 0.9 + wi * 1.4 + 2.0)))
            pygame.draw.lines(surf, (20, glow_t2, int(glow_t2 * 0.6)), False, pts2, 2)

    # ── Glowing floor patches (large SRCALPHA circles near floor) ─────────
    patch_off = camera_x * 0.45
    for pi in range(5):
        rng_p = random.Random(pi * 71 + 400)
        px = int(rng_p.randint(60, 2400) - patch_off) % (CORRIDOR_W + 80) - 40
        pr_size = rng_p.randint(18, 36)
        pa = int(25 + 18 * math.sin(t * 1.3 + pi * 1.7))
        patch_s = pygame.Surface((pr_size * 2 + 4, pr_size * 2 + 4), pygame.SRCALPHA)
        pg = int(100 + 100 * abs(math.sin(t * 1.0 + pi * 2.3)))
        pygame.draw.circle(patch_s, (0, pg, int(pg * 0.5), pa),
                           (pr_size + 2, pr_size + 2), pr_size)
        surf.blit(patch_s, (px - pr_size - 2, FLOOR_Y - pr_size - 6))

    # ── Dense fungi growth on lab benches ─────────────────────────────────
    for bx in range(50, CORRIDOR_W, 110):
        by = FLOOR_Y - 38
        # Bench
        pygame.draw.rect(surf, (8, 20, 12), (bx, by, 94, 28))
        pygame.draw.rect(surf, (20, 70, 35), (bx, by, 94, 28), 1)
        # Dense fungi covering benches
        for ex in range(bx + 4, bx + 90, 10):
            rng_e = random.Random(ex * 7 + 99)
            eh = rng_e.randint(6, 22)
            ew = rng_e.randint(2, 5)
            glow_e = int(100 + 120 * abs(math.sin(t * 1.6 + ex * 0.085)))
            pygame.draw.rect(surf, (0, glow_e, int(glow_e * 0.45)),
                             (ex - ew // 2, by - eh, ew, eh))
            cap_g = min(255, glow_e + 55)
            pygame.draw.circle(surf, (0, cap_g, int(cap_g * 0.65)),
                               (ex, by - eh), ew + 2)

    # ── Detailed researcher silhouette with spore trails ──────────────────
    rx, ry = CORRIDOR_W - 72, FLOOR_Y - 1
    col_coat = (18, 28, 20)
    # Legs
    pygame.draw.line(surf, col_coat, (rx - 3, ry), (rx - 4, ry - 14), 3)
    pygame.draw.line(surf, col_coat, (rx + 3, ry), (rx + 5, ry - 12), 3)
    # Body/coat
    pygame.draw.rect(surf, col_coat, (rx - 7, ry - 30, 14, 18))
    # Head
    pygame.draw.circle(surf, col_coat, (rx, ry - 36), 8)
    # Arm (bent — holding a jar)
    pygame.draw.line(surf, col_coat, (rx + 7, ry - 26), (rx + 16, ry - 20), 3)
    # Jar being held
    pygame.draw.rect(surf, (10, 50, 30), (rx + 14, ry - 26, 10, 14))
    pygame.draw.rect(surf, (40, 200, 100), (rx + 14, ry - 26, 10, 14), 1)
    jar_glow = int(80 + 60 * abs(math.sin(t * 2.0)))
    jar_gs = pygame.Surface((14, 18), pygame.SRCALPHA)
    jar_gs.fill((0, jar_glow, int(jar_glow * 0.5), 60))
    surf.blit(jar_gs, (rx + 12, ry - 28))
    # Spore trail particles floating off researcher
    for i in range(5):
        sp_t_offset = t * 0.7 + i * 0.6
        sp_x = rx - 8 + int(i * 5 * math.sin(sp_t_offset * 1.3))
        sp_y = ry - 20 - int(i * 6 + 4 * math.sin(sp_t_offset))
        if CEIL_Y < sp_y < FLOOR_Y:
            sp_a = max(0, 120 - i * 22)
            sp_s2 = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(sp_s2, (0, 200, 100, sp_a), (3, 3), 2)
            surf.blit(sp_s2, (sp_x - 3, sp_y - 3))


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
        # Epic 14.1 — Bio-pressure vents — vapor blasts from the cultivation tanks
        SteamVent(400, FLOOR_Y, phase_offset=0.0),
        SteamVent(620, FLOOR_Y, phase_offset=2.1),
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
        name       = "DECONTAMINATION CHAMBER",
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
        name       = "GROWTH GALLERY",
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
        # Epic 14.1 — mycelium chamber tableau: pulsing wall nodes,
        # drifting spore motes, panicking researcher silhouette.
        BossRoomActor(380, boss_actor_mycelium_chamber),
    ]
    room3 = Room(
        length     = 450,
        palette    = _PAL_R3,
        elements   = r3_elms,
        bg_draw_fn = _bg_r3,
        bax_enter_line = "Almost done. The lab's alive in here. Try not to touch anything.",
        star3_t    = 60.0,
        star2_t    = 90.0,
        name       = "RECEIVING LAB",
    )

    return Corridor(
        chapter          = 2,
        rooms            = [room1, room2, room3],
        cargo_silhouette = "shroom",
    )
