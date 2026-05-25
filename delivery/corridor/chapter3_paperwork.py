"""
Chapter 3 — The Paperwork corridor.
Theme: fluorescent government office. Bureaucracy weaponized.
"""
from __future__ import annotations
import math
import random
import pygame

from core.text import get_font
from delivery.corridor.elements import (
    Platform, MovingPlatform, CollapsingPlatform, Ladder,
    OneWayWall, NPCEncounter, Collectible, Secret, Checkpoint,
    BossRoomTrigger,
    SteamVent, Tripwire, SecurityBeam,
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
    """Open-plan office — surveillance cameras, worker silhouettes, propaganda banner, extreme flicker."""
    bg_off_slow = camera_x * 0.3
    bg_off = camera_x * 0.5

    WALL_TOP = CEIL_Y
    WALL_BOT = FLOOR_Y
    WALL_H = WALL_BOT - WALL_TOP  # 80

    # --- Extreme fluorescent flicker ---
    blackout_seed = int(t * 3.7)
    blackout_rng = random.Random(blackout_seed)
    if blackout_rng.random() < 0.045:
        pygame.draw.rect(surf, (3, 3, 1), (0, WALL_TOP, CORRIDOR_W, WALL_H))
        return

    flk_raw = (1.0
               - 0.30 * abs(math.sin(t * 61.0))
               - 0.20 * abs(math.sin(t * 19.7))
               - 0.10 * abs(math.sin(t * 7.3)))
    flk = max(0.08, flk_raw)

    # Sickly yellow-green base tint on wall
    base_r = int(18 * flk)
    base_g = int(22 * flk)
    base_b = int(8 * flk)
    pygame.draw.rect(surf, (base_r, base_g, base_b), (0, WALL_TOP, CORRIDOR_W, WALL_H))

    # Fluorescent tube fixtures along ceiling
    for lx in range(0, CORRIDOR_W + 1400, 130):
        lsx = int(lx - bg_off_slow * 0.15)
        if -130 < lsx < CORRIDOR_W + 20:
            # Housing channel
            pygame.draw.rect(surf, (28, 28, 18), (lsx, WALL_TOP + 1, 108, 5))
            # Tube glow (the actual light bar)
            tube_r = int(200 * flk)
            tube_g = int(220 * flk)
            tube_b = int(100 * flk)
            pygame.draw.rect(surf, (tube_r, tube_g, tube_b), (lsx + 2, WALL_TOP + 2, 104, 3))
            # Soft cone of light below tube
            glow_a = int(45 * flk)
            if glow_a > 0:
                glow_surf = pygame.Surface((108, 18), pygame.SRCALPHA)
                for gy in range(18):
                    alpha = int(glow_a * (1.0 - gy / 18.0))
                    glow_surf.fill((int(180 * flk), int(210 * flk), int(80 * flk), alpha),
                                   (0, gy, 108, 1))
                surf.blit(glow_surf, (lsx, WALL_TOP + 5))
            # End caps
            pygame.draw.rect(surf, (50, 50, 30), (lsx, WALL_TOP + 1, 4, 5))
            pygame.draw.rect(surf, (50, 50, 30), (lsx + 104, WALL_TOP + 1, 4, 5))

    # --- Surveillance cameras (ceiling-mounted, heavy parallax) ---
    for wx_cam in range(80, CORRIDOR_W + 1600, 190):
        sx_cam = int(wx_cam - bg_off)
        if -25 < sx_cam < CORRIDOR_W + 25:
            # Mount bracket: 2px horizontal arm dropping from ceiling
            pygame.draw.line(surf, (55, 55, 32), (sx_cam, WALL_TOP), (sx_cam, WALL_TOP + 9), 2)
            pygame.draw.line(surf, (55, 55, 32), (sx_cam, WALL_TOP + 9), (sx_cam + 11, WALL_TOP + 9), 2)
            # Camera body (8x5 rect)
            pygame.draw.rect(surf, (38, 38, 24), (sx_cam + 6, WALL_TOP + 6, 8, 5))
            pygame.draw.rect(surf, (80, 80, 45), (sx_cam + 6, WALL_TOP + 6, 8, 5), 1)
            # Lens
            pygame.draw.circle(surf, (8, 8, 4), (sx_cam + 10, WALL_TOP + 8), 2)
            pygame.draw.circle(surf, (0, 60, 20), (sx_cam + 10, WALL_TOP + 8), 2, 1)
            # Red LED blink (individual phase per camera)
            blink_phase = (t * 1.7 + wx_cam * 0.013) % 2.4
            led_col = (230, 15, 8) if blink_phase < 0.25 else (70, 6, 3)
            led_r = 2 if blink_phase < 0.25 else 1
            pygame.draw.circle(surf, led_col, (sx_cam + 15, WALL_TOP + 7), led_r)
            # Scan sweep line (faint, only when LED is lit)
            if blink_phase < 0.25:
                sweep_a = int(18 * flk)
                sweep_surf = pygame.Surface((40, WALL_H), pygame.SRCALPHA)
                sweep_surf.fill((200, 30, 10, sweep_a))
                surf.blit(sweep_surf, (sx_cam + 10, WALL_TOP))

    # --- Cubicle divider panels (parallax mid) ---
    for wx_div in range(240, CORRIDOR_W + 1400, 310):
        sx_div = int(wx_div - bg_off)
        if -15 < sx_div < CORRIDOR_W + 15:
            # Divider wall
            pygame.draw.rect(surf, (26, 26, 16), (sx_div - 1, WALL_TOP + 30, 3, WALL_H - 30))
            # Fabric texture strips
            for ty in range(WALL_TOP + 32, WALL_BOT - 4, 6):
                pygame.draw.line(surf, (34, 34, 20), (sx_div - 4, ty), (sx_div + 4, ty), 1)
            # Top cap
            pygame.draw.rect(surf, (50, 50, 30), (sx_div - 4, WALL_TOP + 28, 7, 4))

    # --- Huge propaganda banner spanning most of the wall ---
    # Slow parallax so banner drifts at 0.2x
    ban_world_off = int(camera_x * 0.2)
    banner_period = 660
    for boff in range(-banner_period, CORRIDOR_W + banner_period + 1, banner_period):
        bx = boff - (ban_world_off % banner_period)
        if -640 < bx < CORRIDOR_W + 20:
            bw = 560
            bh = 30
            by = WALL_TOP + 10
            # Dark backing
            pygame.draw.rect(surf, (12, 4, 2), (bx, by, bw, bh))
            # Thick red border
            pygame.draw.rect(surf, (160, 18, 10), (bx, by, bw, bh), 2)
            # Inner accent line
            pygame.draw.line(surf, (100, 12, 6), (bx + 4, by + 4), (bx + bw - 4, by + 4), 1)
            pygame.draw.line(surf, (100, 12, 6), (bx + 4, by + bh - 4), (bx + bw - 4, by + bh - 4), 1)
            # Main slogan text
            f_big = get_font(11, bold=True)
            txt_surf = f_big.render("YOUR DEBT IS YOUR PURPOSE", True, (210, 28, 14))
            surf.blit(txt_surf, (bx + 12, by + 9))
            # Union logo block on left
            pygame.draw.rect(surf, (90, 12, 6), (bx - 28, by, 26, bh))
            pygame.draw.rect(surf, (170, 25, 18), (bx - 28, by, 26, bh), 1)
            f_tiny = get_font(7)
            surf.blit(f_tiny.render("URM", True, (210, 38, 28)), (bx - 26, by + 4))
            surf.blit(f_tiny.render("L404", True, (210, 38, 28)), (bx - 26, by + 13))
            surf.blit(f_tiny.render("INTL", True, (210, 38, 28)), (bx - 26, by + 21))

    # --- Desk rows with monitors and hunched worker silhouettes ---
    f_mon = get_font(7)
    mon_lines = ["DEBT:", "QUOTA", "CLONE", "STATUS", "ARREARS", "FILING", "DELINQ"]
    for wx_d in range(140, CORRIDOR_W + 1600, 250):
        sx_d = int(wx_d - bg_off)
        if -160 < sx_d < CORRIDOR_W + 20:
            rng_d = random.Random(wx_d)
            # Desk surface (wide, flat, grey-beige horror)
            desk_col = (22, 22, 14)
            pygame.draw.rect(surf, desk_col, (sx_d, WALL_BOT - 28, 115, 20))
            pygame.draw.rect(surf, (40, 40, 24), (sx_d, WALL_BOT - 28, 115, 20), 1)
            # Desk legs
            pygame.draw.line(surf, (30, 30, 18), (sx_d + 6, WALL_BOT - 8), (sx_d + 6, WALL_BOT), 2)
            pygame.draw.line(surf, (30, 30, 18), (sx_d + 108, WALL_BOT - 8), (sx_d + 108, WALL_BOT), 2)
            # Monitor (flickering amber-green)
            mon_flk = max(0.04, flk * (0.6 + 0.4 * rng_d.random()))
            mon_bg = (int(5 * mon_flk * 8), int(10 * mon_flk * 8), int(4 * mon_flk * 8))
            pygame.draw.rect(surf, mon_bg, (sx_d + 3, WALL_BOT - 50, 30, 20))
            pygame.draw.rect(surf, (int(70 * mon_flk), int(100 * mon_flk), int(35 * mon_flk)),
                             (sx_d + 3, WALL_BOT - 50, 30, 20), 1)
            # Scrolling text on monitor
            scroll = int((t * 12 + wx_d * 0.06) % (len(mon_lines) * 7))
            for li, ln in enumerate(mon_lines):
                ly = WALL_BOT - 49 + li * 7 - scroll
                if WALL_BOT - 50 < ly < WALL_BOT - 32:
                    surf.set_clip(pygame.Rect(sx_d + 4, WALL_BOT - 49, 26, 16))
                    surf.blit(f_mon.render(ln, True,
                              (int(65 * mon_flk), int(95 * mon_flk), int(32 * mon_flk))),
                              (sx_d + 4, ly))
                    surf.set_clip(None)
            # Monitor stand
            pygame.draw.rect(surf, (28, 28, 17), (sx_d + 15, WALL_BOT - 30, 5, 2))
            # Paper tray beside monitor
            pygame.draw.rect(surf, (36, 36, 22), (sx_d + 40, WALL_BOT - 30, 24, 3))
            pygame.draw.rect(surf, (50, 50, 30), (sx_d + 40, WALL_BOT - 30, 24, 3), 1)

            # Worker silhouette — hunched, never looks up, ever
            wx_off = sx_d + 72
            wy_desk = WALL_BOT - 28
            # Torso: slumped forward, widening at shoulders
            body = [(wx_off - 7, wy_desk), (wx_off + 6, wy_desk),
                    (wx_off + 10, wy_desk - 16), (wx_off - 9, wy_desk - 16)]
            pygame.draw.polygon(surf, (14, 12, 7), body)
            # Head bowed toward the desk
            pygame.draw.circle(surf, (14, 12, 7), (wx_off + 8, wy_desk - 20), 6)
            # Arm resting on desk
            pygame.draw.line(surf, (14, 12, 7), (wx_off + 5, wy_desk - 10),
                             (wx_off + 22, wy_desk - 2), 3)
            # Second arm (other side)
            pygame.draw.line(surf, (14, 12, 7), (wx_off - 5, wy_desk - 8),
                             (wx_off - 12, wy_desk - 2), 2)

    # --- Fallen forms and papers scattered near floor ---
    for wx_p in range(30, CORRIDOR_W + 1500, 95):
        sx_p = int(wx_p - bg_off)
        if -10 < sx_p < CORRIDOR_W + 10:
            rng_p = random.Random(wx_p + 7)
            pw = rng_p.randint(10, 30)
            ph = rng_p.randint(2, 5)
            # Beige-grey horror paper colour
            pr = 80 + rng_p.randint(0, 35)
            pg = 76 + rng_p.randint(0, 28)
            pb = 50 + rng_p.randint(0, 22)
            pygame.draw.rect(surf, (pr, pg, pb), (sx_p, WALL_BOT - ph - 2, pw, ph))
            # Occasional red OVERDUE diagonal stamp stripe
            if rng_p.random() < 0.28:
                pygame.draw.line(surf, (150, 16, 12),
                                 (sx_p + 1, WALL_BOT - ph - 1),
                                 (sx_p + pw - 1, WALL_BOT - 3), 1)
            # Folded corner on some papers
            if rng_p.random() < 0.4:
                cx_fold = sx_p + pw - 4
                cy_fold = WALL_BOT - ph - 2
                pygame.draw.polygon(surf, (60, 56, 36),
                                    [(cx_fold, cy_fold), (cx_fold + 4, cy_fold),
                                     (cx_fold + 4, cy_fold + 4)])


def _bg_r2(surf, camera_x, t, pal):
    """File Room 4 — towering shelves floor-to-ceiling, falling papers, OVERDUE stamp, teetering stacks."""
    bg_off = camera_x * 0.4
    bg_off_slow = camera_x * 0.25

    WALL_H = FLOOR_Y - CEIL_Y  # 80

    # Dim base fill — oppressive grey-brown
    pygame.draw.rect(surf, (10, 8, 5), (0, CEIL_Y, CORRIDOR_W, WALL_H))

    # --- TOWERING shelf walls: fill the entire height from CEIL_Y to FLOOR_Y ---
    shelf_colors = [
        (72, 54, 18), (54, 70, 24), (64, 44, 34),
        (84, 58, 16), (50, 65, 28), (70, 52, 20),
        (80, 62, 12), (58, 48, 30), (40, 62, 22),
    ]
    shelf_unit_w = 140
    shelf_spacing = 15  # gap between horizontal boards

    for wx in range(0, CORRIDOR_W + 2000, shelf_unit_w + 8):
        sx = int(wx - bg_off)
        if -shelf_unit_w - 10 < sx < CORRIDOR_W + 20:
            rng_s = random.Random(wx + 99)

            # Back panel (darker fill behind files)
            pygame.draw.rect(surf, (8, 6, 3), (sx + 3, CEIL_Y, shelf_unit_w - 6, WALL_H))

            # Left and right uprights
            for post_x in (sx, sx + shelf_unit_w - 3):
                pygame.draw.rect(surf, (44, 34, 12), (post_x, CEIL_Y, 3, WALL_H))
                # Bolt marks every 20px
                for bolt_y in range(CEIL_Y + 8, FLOOR_Y - 4, 20):
                    pygame.draw.circle(surf, (60, 48, 18), (post_x + 1, bolt_y), 1)

            # Horizontal shelf boards — run full height
            for yi in range(CEIL_Y, FLOOR_Y + 1, shelf_spacing):
                # Board itself
                pygame.draw.line(surf, (38, 28, 10), (sx + 3, yi), (sx + shelf_unit_w - 3, yi), 2)
                # Underside shadow
                pygame.draw.line(surf, (22, 16, 6),
                                 (sx + 3, yi + 2), (sx + shelf_unit_w - 3, yi + 2), 1)

                # Files standing on this shelf (between yi and yi-shelf_spacing)
                if yi > CEIL_Y:
                    fx = sx + 4
                    shelf_rng = random.Random(wx * 200 + yi)
                    avail_w = shelf_unit_w - 10
                    while fx < sx + avail_w:
                        fc = shelf_colors[shelf_rng.randint(0, len(shelf_colors) - 1)]
                        fw = shelf_rng.randint(9, 22)
                        fh = shelf_rng.randint(8, shelf_spacing - 2)
                        if fx + fw > sx + avail_w:
                            break
                        fy = yi - fh
                        # File body
                        pygame.draw.rect(surf, fc, (fx, fy, fw, fh))
                        # Spine highlight (left edge brighter)
                        spine_r = min(255, int(fc[0] * 1.4))
                        spine_g = min(255, int(fc[1] * 1.4))
                        spine_b = min(255, int(fc[2] * 1.4))
                        pygame.draw.line(surf, (spine_r, spine_g, spine_b),
                                         (fx, fy), (fx, yi - 1), 1)
                        # Label strip near top
                        pygame.draw.rect(surf, (185, 175, 145), (fx + 2, fy + 2, fw - 4, 3))
                        # Occasional red "URGENT" band across label
                        if shelf_rng.random() < 0.2:
                            pygame.draw.rect(surf, (150, 12, 8), (fx + 2, fy + 2, fw - 4, 2))
                        fx += fw + shelf_rng.randint(1, 3)

            # Depth shadow on right side of unit
            shad_surf = pygame.Surface((5, WALL_H), pygame.SRCALPHA)
            shad_surf.fill((0, 0, 0, 70))
            surf.blit(shad_surf, (sx + shelf_unit_w - 3, CEIL_Y))

    # --- Falling papers (animated, deterministic, with wobble) ---
    for i in range(22):
        fall_rng = random.Random(i * 317 + 5)
        wx_fall = fall_rng.randint(0, CORRIDOR_W + 1600)
        sx_fall = int(wx_fall - bg_off)
        if -24 < sx_fall < CORRIDOR_W + 24:
            fall_y = int((t * 20 + i * 73) % WALL_H) + CEIL_Y
            # Horizontal drift with sin wobble
            drift_x = int(math.sin(t * 1.8 + i * 0.9) * 5)
            pw = fall_rng.randint(10, 22)
            ph = fall_rng.randint(5, 9)
            angle_wobble = math.sin(t * 2.3 + i * 0.7) * 12
            paper_surf = pygame.Surface((pw + 2, ph + 2), pygame.SRCALPHA)
            pr = fall_rng.randint(155, 205)
            pg = fall_rng.randint(148, 195)
            pb = fall_rng.randint(105, 155)
            paper_surf.fill((pr, pg, pb, 195))
            # Red stamp mark on some falling papers
            if fall_rng.random() < 0.35:
                pygame.draw.line(paper_surf, (155, 16, 10), (2, 2), (pw - 2, ph - 1), 1)
            # Faint text line
            pygame.draw.line(paper_surf, (int(pr * 0.6), int(pg * 0.6), int(pb * 0.5)),
                             (2, ph // 2), (pw - 2, ph // 2), 1)
            rotated_p = pygame.transform.rotate(paper_surf, angle_wobble)
            surf.blit(rotated_p, (sx_fall + drift_x, fall_y))

    # --- OVERDUE stamp on floor (large, rotated, repeating) ---
    f_stamp = get_font(17, bold=True)
    stamp_period = 380
    stamp_world_off = int(camera_x * 0.15)
    for soff in range(-stamp_period, CORRIDOR_W + stamp_period + 1, stamp_period):
        sx_stamp = soff - (stamp_world_off % stamp_period)
        if -50 < sx_stamp < CORRIDOR_W + 50:
            stamp_txt = f_stamp.render("OVERDUE", True, (170, 16, 10))
            rot_stamp = pygame.transform.rotate(stamp_txt, -14)
            sw, sh = rot_stamp.get_size()
            # Place near floor
            sy_stamp = FLOOR_Y - sh - 3
            surf.blit(rot_stamp, (sx_stamp, sy_stamp))
            # Red border box around stamp
            pygame.draw.rect(surf, (120, 12, 7),
                             (sx_stamp - 1, sy_stamp - 1, sw + 2, sh + 2), 1)

    # --- Impossible teetering paper stacks (leaning polygon towers) ---
    for i_stack in range(8):
        rng_st = random.Random(i_stack * 991 + 3)
        wx_st = rng_st.randint(20, CORRIDOR_W + 1400)
        sx_st = int(wx_st - bg_off_slow)
        if -40 < sx_st < CORRIDOR_W + 40:
            num_layers = rng_st.randint(5, 9)
            lean = rng_st.randint(-10, 12)  # lean direction and severity
            # wobble: tiny oscillation makes stack look precarious
            wobble = math.sin(t * 0.8 + i_stack * 1.3) * 1.5
            for layer in range(num_layers):
                layer_rng = random.Random(i_stack * 200 + layer)
                lw = rng_st.randint(16, 34)
                lh = 4
                ly_bot = FLOOR_Y - 2 - layer * (lh + 1)
                # lean accumulates upward + wobble
                lx = int(sx_st + lean * layer * 0.6 + wobble * layer * 0.3)
                pr = layer_rng.randint(145, 200)
                pg = layer_rng.randint(138, 190)
                pb = layer_rng.randint(94, 148)
                pygame.draw.rect(surf, (pr, pg, pb), (lx - lw // 2, ly_bot - lh, lw, lh))
                # Edge shadow on bottom of each sheet
                pygame.draw.line(surf, (70, 62, 36),
                                 (lx - lw // 2, ly_bot - 1),
                                 (lx + lw // 2, ly_bot - 1), 1)
                # Occasional red mark
                if layer_rng.random() < 0.25:
                    pygame.draw.line(surf, (140, 10, 6),
                                     (lx - lw // 2 + 2, ly_bot - lh + 1),
                                     (lx + lw // 2 - 2, ly_bot - lh + 1), 1)


def _bg_r3(surf, camera_x, t, pal):
    """Executive processing office — mahogany desk, EMPLOYEE OF INFINITY plaque, portrait, grey planet window."""
    bg_off = camera_x * 0.3

    WALL_TOP = CEIL_Y
    WALL_BOT = FLOOR_Y
    WALL_H = WALL_BOT - WALL_TOP

    # --- Rich dark background fill ---
    pygame.draw.rect(surf, (14, 10, 5), (0, WALL_TOP, CORRIDOR_W, WALL_H))

    # --- Gold trim border lines along top and bottom of wall zone ---
    pygame.draw.line(surf, (160, 120, 30), (0, WALL_TOP + 2), (CORRIDOR_W, WALL_TOP + 2), 3)
    pygame.draw.line(surf, (100, 75, 18), (0, WALL_TOP + 5), (CORRIDOR_W, WALL_TOP + 5), 1)
    pygame.draw.line(surf, (160, 120, 30), (0, WALL_BOT - 3), (CORRIDOR_W, WALL_BOT - 3), 3)
    pygame.draw.line(surf, (100, 75, 18), (0, WALL_BOT - 6), (CORRIDOR_W, WALL_BOT - 6), 1)

    # --- Fancy carpet pattern: diamond grid in muted gold ---
    diamond_size = 18
    for gx in range(-diamond_size, CORRIDOR_W + diamond_size, diamond_size):
        gx_off = int(gx - bg_off * 0.1)
        for gy in range(WALL_BOT - 26, WALL_BOT, diamond_size // 2):
            # Diamond outline at grid intersections
            if (gx // diamond_size + gy // (diamond_size // 2)) % 2 == 0:
                pts = [
                    (gx_off, gy - diamond_size // 3),
                    (gx_off + diamond_size // 2, gy),
                    (gx_off, gy + diamond_size // 3),
                    (gx_off - diamond_size // 2, gy),
                ]
                pygame.draw.polygon(surf, (38, 28, 10), pts, 1)

    # --- Window: grey planet and red corporate sun ---
    win_wx = 60  # world-space anchor
    wx_off = int(win_wx - bg_off)
    win_w, win_h = 90, WALL_H - 14
    if -win_w - 10 < wx_off < CORRIDOR_W + 10:
        # Window frame (thick dark border, gold inner line)
        pygame.draw.rect(surf, (6, 4, 2), (wx_off, WALL_TOP + 7, win_w, win_h))
        pygame.draw.rect(surf, (80, 60, 15), (wx_off, WALL_TOP + 7, win_w, win_h), 3)
        pygame.draw.rect(surf, (130, 100, 25), (wx_off + 3, WALL_TOP + 10, win_w - 6, win_h - 6), 1)
        # Stars in window
        win_clip = pygame.Rect(wx_off + 1, WALL_TOP + 8, win_w - 2, win_h - 2)
        surf.set_clip(win_clip)
        star_rng = random.Random(77)
        for _ in range(24):
            star_x = wx_off + star_rng.randint(4, win_w - 4)
            star_y = WALL_TOP + 8 + star_rng.randint(2, win_h - 10)
            star_br = star_rng.randint(60, 160)
            pygame.draw.circle(surf, (star_br, star_br, star_br), (star_x, star_y), 1)
        # Grey planet (slowly drifting)
        planet_cx = wx_off + win_w // 2 + int(math.sin(t * 0.04) * 4)
        planet_cy = WALL_TOP + 7 + win_h - 20
        pygame.draw.circle(surf, (65, 62, 70), (planet_cx, planet_cy), 22)
        # Planet band stripes
        pygame.draw.line(surf, (80, 76, 85), (planet_cx - 18, planet_cy - 6),
                         (planet_cx + 18, planet_cy - 6), 3)
        pygame.draw.line(surf, (55, 52, 60), (planet_cx - 20, planet_cy + 4),
                         (planet_cx + 20, planet_cy + 4), 2)
        # Red corporate sun (top-right of window)
        sun_cx = wx_off + win_w - 12
        sun_cy = WALL_TOP + 16
        sun_pulse = 0.7 + 0.3 * abs(math.sin(t * 0.5))
        pygame.draw.circle(surf, (int(200 * sun_pulse), int(20 * sun_pulse), int(8 * sun_pulse)),
                           (sun_cx, sun_cy), 7)
        pygame.draw.circle(surf, (int(255 * sun_pulse), int(50 * sun_pulse), 0),
                           (sun_cx, sun_cy), 5)
        surf.set_clip(None)

    # --- "EMPLOYEE OF INFINITY" plaque with running timer ---
    plaque_wx = 200
    px_off = int(plaque_wx - bg_off * 0.2)
    if -180 < px_off < CORRIDOR_W + 20:
        pw, ph = 180, 38
        py = WALL_TOP + 8
        pygame.draw.rect(surf, (24, 16, 4), (px_off, py, pw, ph))
        pygame.draw.rect(surf, (160, 120, 30), (px_off, py, pw, ph), 2)
        # Inner decorative border
        pygame.draw.rect(surf, (100, 75, 18), (px_off + 3, py + 3, pw - 6, ph - 6), 1)
        f_plaque_big = get_font(9, bold=True)
        f_plaque_sm = get_font(7)
        s1 = f_plaque_big.render("EMPLOYEE OF INFINITY", True, (190, 145, 38))
        surf.blit(s1, (px_off + 6, py + 6))
        # Running timer (counts up relentlessly)
        total_secs = int(t * 3600)  # pretend counting years
        hours = (total_secs // 3600) % 10000
        mins = (total_secs // 60) % 60
        secs = total_secs % 60
        timer_str = f"TENURE: {hours:04d}H {mins:02d}M {secs:02d}S"
        s2 = f_plaque_sm.render(timer_str, True, (120, 90, 20))
        surf.blit(s2, (px_off + 6, py + 22))

    # --- Executive portrait silhouette (framed on wall) ---
    portrait_wx = 360
    port_off = int(portrait_wx - bg_off * 0.15)
    if -60 < port_off < CORRIDOR_W + 20:
        fr_w, fr_h = 46, 56
        fr_y = WALL_TOP + 6
        # Frame
        pygame.draw.rect(surf, (18, 12, 4), (port_off, fr_y, fr_w, fr_h))
        pygame.draw.rect(surf, (140, 105, 24), (port_off, fr_y, fr_w, fr_h), 2)
        pygame.draw.rect(surf, (90, 68, 14), (port_off + 3, fr_y + 3, fr_w - 6, fr_h - 6), 1)
        # Suit body silhouette (dark polygon — broad shoulders, jacket lapels)
        body_cx = port_off + fr_w // 2
        body_top = fr_y + fr_h - 20
        suit_pts = [
            (body_cx - 14, fr_y + fr_h - 2),  # bottom-left
            (body_cx + 14, fr_y + fr_h - 2),  # bottom-right
            (body_cx + 16, body_top),           # shoulder-right
            (body_cx + 8, body_top - 2),        # lapel-right
            (body_cx, body_top + 4),            # collar-centre
            (body_cx - 8, body_top - 2),        # lapel-left
            (body_cx - 16, body_top),           # shoulder-left
        ]
        pygame.draw.polygon(surf, (10, 8, 3), suit_pts)
        # Head
        pygame.draw.circle(surf, (10, 8, 3), (body_cx, body_top - 9), 8)

    # --- Large mahogany executive desk ---
    desk_x = CORRIDOR_W - 160
    desk_w = 145
    desk_h = 30
    desk_y = WALL_BOT - desk_h - 2
    # Desk surface (deep brown)
    pygame.draw.rect(surf, (20, 9, 3), (desk_x, desk_y, desk_w, desk_h))
    # Gold trim edge
    pygame.draw.rect(surf, (110, 80, 18), (desk_x, desk_y, desk_w, desk_h), 2)
    pygame.draw.line(surf, (80, 58, 12), (desk_x + 4, desk_y + 4), (desk_x + desk_w - 4, desk_y + 4), 1)
    # Wood grain lines
    grain_rng = random.Random(55)
    for _ in range(8):
        gx1 = desk_x + grain_rng.randint(4, desk_w - 8)
        gx2 = gx1 + grain_rng.randint(20, 60)
        gy = desk_y + grain_rng.randint(6, desk_h - 6)
        pygame.draw.line(surf, (28, 12, 4), (gx1, gy), (min(gx2, desk_x + desk_w - 2), gy), 1)
    # Desk legs
    for leg_x in (desk_x + 6, desk_x + desk_w - 10):
        pygame.draw.rect(surf, (16, 7, 2), (leg_x, WALL_BOT - 6, 6, 6))
    # Papers on desk
    pygame.draw.rect(surf, (100, 92, 65), (desk_x + 12, desk_y + 6, 30, 18))
    pygame.draw.rect(surf, (70, 65, 44), (desk_x + 14, desk_y + 8, 30, 18))
    pygame.draw.rect(surf, (160, 12, 8), (desk_x + 15, desk_y + 9, 28, 3))  # red stamp
    # Name plate
    pygame.draw.rect(surf, (30, 20, 6), (desk_x + 55, desk_y + 18, 55, 8))
    pygame.draw.rect(surf, (130, 100, 22), (desk_x + 55, desk_y + 18, 55, 8), 1)
    f_name = get_font(6)
    surf.blit(f_name.render("DISPATCHER", True, (160, 120, 28)), (desk_x + 57, desk_y + 20))

    # --- Executive seated silhouette (just head + shoulders above desk) ---
    ex_cx = desk_x + desk_w - 30
    ex_desk_top = desk_y
    # Upper body visible above desk
    pygame.draw.rect(surf, (10, 7, 2), (ex_cx - 10, ex_desk_top - 16, 20, 14))
    pygame.draw.circle(surf, (10, 7, 2), (ex_cx, ex_desk_top - 21), 7)


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
        # Epic 14.1 — Security beam scanning the bureaucratic hellscape;
        # tripwire pings the compliance system if you brush it.
        SecurityBeam(540, CEIL_Y + 12, length=240, phase=0.0),
        Tripwire(820, FLOOR_Y - 16, w=40,
                 bax_line="Nova Soma compliance scanner pinged. You're on a list now."),
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
        name       = "INTAKE FLOOR",
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
        name       = "FILE ROOM 4",
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
        name       = "EXECUTIVE PROCESSING",
    )

    return Corridor(
        chapter          = 3,
        rooms            = [room1, room2, room3],
        cargo_silhouette = "forms",
    )
