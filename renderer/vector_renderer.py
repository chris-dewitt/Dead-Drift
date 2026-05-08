from __future__ import annotations
import math
import random
import pygame
from config import settings as S
from core.event_bus import bus, EVT_SLINGSHOT, EVT_SCAN_PING


# ---------------------------------------------------------------------------
def _hsv(h: float, s: float = 1.0, v: float = 1.0) -> tuple:
    h = h % 1.0
    if s == 0:
        c = int(v * 255)
        return (c, c, c)
    i  = int(h * 6)
    f  = h * 6 - i
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r, g, b = [(v,t,p),(q,v,p),(p,v,t),(p,q,v),(t,p,v),(v,p,q)][i % 6]
    return (int(r * 255), int(g * 255), int(b * 255))


class VectorRenderer:
    """
    Draws the flight scene — all geometry procedural, no sprites.
    Aesthetic: psychedelic brutalist. Void black, heavy neon, color cycling.
    """

    _STAR_SEED  = 7
    _STAR_COUNT = 170

    def __init__(self, surface: pygame.Surface):
        self.surface     = surface
        self._stars      = self._gen_stars()
        self._nebulae    = self._gen_nebulae()
        self._dust       = self._gen_dust()
        self._flash_t    = 0.0
        self._flash_col  = (180, 220, 255)
        self._scan_pings: list[tuple[int, int, float]] = []
        bus.subscribe(EVT_SLINGSHOT,  self._on_slingshot)
        bus.subscribe(EVT_SCAN_PING,  self._on_scan_ping)

    def _on_slingshot(self, **_):
        self._flash_t   = 0.45
        self._flash_col = (160, 210, 255)

    def _on_scan_ping(self, pos_x, pos_y, **_):
        t = pygame.time.get_ticks() / 1000.0
        self._scan_pings.append((int(pos_x), int(pos_y), t))

    # ------------------------------------------------------------------
    def draw(self, run_mgr, ship, dt: float = 0.016):
        t = pygame.time.get_ticks() / 1000.0
        self._draw_nebulae(t)
        self._draw_dust(t)
        self._draw_stars(t)
        self._draw_scan_pings(t)
        self._draw_gravity_wells(run_mgr, t)
        self._draw_debris(run_mgr, t)
        self._draw_canisters(run_mgr, t)
        self._draw_bullets(ship)
        self._draw_barges(run_mgr, ship, t)
        self._draw_trail(ship, t)
        self._draw_velocity_indicator(ship)
        self._draw_ship(ship, t)
        self._draw_exhaust(ship, t)
        self._draw_proximity_alarm(run_mgr, ship, t)
        self._draw_flash(dt)
        self._draw_spore_effect(ship, t)

    def draw_menu_background(self, t: float):
        self._draw_nebulae(t)
        self._draw_dust(t)
        self._draw_stars(t)
        # Single decorative well centred behind the title
        class _FW:
            pass
        fw = _FW()
        fw.pos  = type("P", (), {"x": S.SCREEN_W / 2, "y": S.SCREEN_H / 2 - 50})()
        fw.radius = 60
        self._draw_well(fw, t * 0.35)

    # ------------------------------------------------------------------  NEBULAE
    def _gen_nebulae(self) -> list:
        rng = random.Random(self._STAR_SEED + 99)
        configs = [
            (0.62, 0.50, 260),
            (0.33, 0.40, 210),
            (0.80, 0.45, 190),
            (0.50, 0.35, 230),
            (0.12, 0.40, 170),
        ]
        out = []
        for hue, sat, r in configs:
            x = rng.randint(int(S.SCREEN_W * 0.10), int(S.SCREEN_W * 0.90))
            y = rng.randint(int(S.SCREEN_H * 0.08), int(S.SCREEN_H * 0.85))
            out.append((x, y, r, hue, sat))
        return out

    def _draw_nebulae(self, t: float):
        surf = pygame.Surface((S.SCREEN_W, S.SCREEN_H), pygame.SRCALPHA)
        for x, y, r, base_hue, sat in self._nebulae:
            hue = (base_hue + t * 0.0035) % 1.0
            col = _hsv(hue, sat * 0.60, 0.14)
            for scale, alpha in ((1.0, 20), (0.68, 32), (0.40, 44)):
                pygame.draw.circle(surf, (*col, alpha), (x, y), int(r * scale))
        self.surface.blit(surf, (0, 0))

    # ------------------------------------------------------------------  DUST
    def _gen_dust(self) -> list:
        rng = random.Random(self._STAR_SEED + 777)
        return [
            (rng.randint(0, S.SCREEN_W),
             rng.randint(0, S.SCREEN_H),
             rng.random(),                     # base hue
             rng.uniform(0.4, 1.8),            # drift freq
             rng.random() * math.tau,          # phase
             rng.uniform(12, 28))              # drift radius px
            for _ in range(90)
        ]

    def _draw_dust(self, t: float):
        surf = self.surface
        for ox, oy, hue, freq, phase, rad in self._dust:
            x = int((ox + math.cos(t * freq + phase) * rad) % S.SCREEN_W)
            y = int((oy + math.sin(t * freq * 0.7 + phase) * rad * 0.6) % S.SCREEN_H)
            brightness = 0.10 + 0.08 * abs(math.sin(t * freq * 1.3 + phase))
            col = _hsv((hue + t * 0.015) % 1.0, 0.65, brightness)
            surf.set_at((x, y), col)

    # ------------------------------------------------------------------  STARS
    def _gen_stars(self) -> list:
        rng = random.Random(self._STAR_SEED)
        stars = []
        for _ in range(self._STAR_COUNT):
            stars.append((
                rng.randint(0, S.SCREEN_W - 1),
                rng.randint(0, S.SCREEN_H - 1),
                rng.random(),              # lum
                rng.random(),              # hue
                rng.uniform(0.6, 2.5),     # twinkle speed
                rng.random() * math.tau,   # twinkle phase
            ))
        return stars

    def _draw_stars(self, t: float = 0.0):
        surf = self.surface
        for x, y, lum, hue, tw_speed, tw_phase in self._stars:
            twinkle = 0.5 + 0.5 * math.sin(t * tw_speed + tw_phase)
            if lum < 0.48:
                v = int(lum * 40 * (0.7 + 0.3 * twinkle))
                surf.set_at((x, y), (v, v, v + 9))
            elif lum < 0.80:
                v = int((50 + lum * 65) * (0.75 + 0.25 * twinkle))
                surf.set_at((x, y), (v - 12, v - 12, v))
            elif lum < 0.93:
                br = int(185 + 35 * twinkle)
                pygame.draw.circle(surf, (br - 10, br - 10, br),
                                   (x, y), 2 if twinkle > 0.85 else 1)
            else:
                neon = [(0, 230, 255), (230, 0, 255), (255, 190, 0),
                        (0, 255, 128), (255, 60, 120)][int(hue * 5) % 5]
                r = 2 if twinkle > 0.7 else 1
                pygame.draw.circle(surf, neon, (x, y), r)
                if twinkle > 0.88:
                    pygame.draw.line(surf, neon, (x - 4, y), (x + 4, y), 1)
                    pygame.draw.line(surf, neon, (x, y - 4), (x, y + 4), 1)

    # ------------------------------------------------------------------  SCAN PINGS
    def _draw_scan_pings(self, t: float):
        PING_DUR = 3.2
        alive = []
        for cx, cy, start_t in self._scan_pings:
            age  = t - start_t
            if age > PING_DUR:
                continue
            alive.append((cx, cy, start_t))
            frac   = age / PING_DUR
            radius = int(frac * 560)
            col    = (0, int(200 * (1 - frac)), int(255 * (1 - frac)))
            if radius > 0:
                pygame.draw.circle(self.surface, col, (cx, cy), radius, 2)
            if radius > 30:
                pygame.draw.circle(self.surface, (0, int(130 * (1-frac)), int(175 * (1-frac))),
                                   (cx, cy), radius // 2, 1)
        self._scan_pings = alive

    # ------------------------------------------------------------------  GRAVITY WELLS
    def _draw_gravity_wells(self, run_mgr, t: float):
        if run_mgr.sector is None:
            return
        for well in run_mgr.sector.gravity.wells:
            self._draw_well(well, t)

    def _draw_well(self, well, t: float):
        cx, cy = int(well.pos.x), int(well.pos.y)
        r      = well.radius
        drift  = (t * 0.07) % 1.0
        pulse  = math.sin(t * 1.4) * 4.5

        # 7 concentric rings, hue spread across 0.45 of wheel, width=2
        rings = [
            (r * 4.8 + pulse * 1.6, 0.00, 0.16, 2),
            (r * 3.6 + pulse * 1.3, 0.06, 0.24, 2),
            (r * 2.7 + pulse * 1.0, 0.12, 0.40, 2),
            (r * 2.0 + pulse * 0.7, 0.20, 0.58, 2),
            (r * 1.4 + pulse * 0.4, 0.28, 0.74, 3),
            (r * 1.0 + pulse * 0.2, 0.36, 0.88, 3),
            (r * 0.62,              0.45, 0.98, 3),
        ]
        for radius, hue_off, val, width in rings:
            ir    = max(2, int(radius))
            hue   = (drift + hue_off) % 1.0
            color = _hsv(hue, 0.95, val)
            pygame.draw.circle(self.surface, color, (cx, cy), ir, width)
            if val > 0.50:
                glow = _hsv(hue, 0.72, val * 0.20)
                pygame.draw.circle(self.surface, glow, (cx, cy), ir + 5, 2)

        # Primary rotating radial lines (8-fold, width=2)
        line_hue = (drift + 0.12) % 1.0
        line_col = _hsv(line_hue, 0.80, 0.38)
        for i in range(8):
            ang = math.radians(i * 45 + t * 9)
            x1 = cx + int(math.cos(ang) * r * 1.7)
            y1 = cy + int(math.sin(ang) * r * 1.7)
            x2 = cx + int(math.cos(ang) * r * 0.90)
            y2 = cy + int(math.sin(ang) * r * 0.90)
            pygame.draw.line(self.surface, line_col, (x1, y1), (x2, y2), 2)

        # Counter-rotating secondary spokes (4-fold, width=2)
        sec_col = _hsv((drift + 0.22) % 1.0, 0.55, 0.28)
        for i in range(4):
            ang = math.radians(i * 90 + 22.5 - t * 5)
            x1 = cx + int(math.cos(ang) * r * 2.4)
            y1 = cy + int(math.sin(ang) * r * 2.4)
            x2 = cx + int(math.cos(ang) * r * 1.2)
            y2 = cy + int(math.sin(ang) * r * 1.2)
            pygame.draw.line(self.surface, sec_col, (x1, y1), (x2, y2), 2)

        # Tertiary fine spokes (16-fold, very dim)
        fine_col = _hsv((drift + 0.35) % 1.0, 0.40, 0.14)
        for i in range(16):
            ang = math.radians(i * 22.5 + t * 3)
            x1 = cx + int(math.cos(ang) * r * 3.0)
            y1 = cy + int(math.sin(ang) * r * 3.0)
            x2 = cx + int(math.cos(ang) * r * 1.5)
            y2 = cy + int(math.sin(ang) * r * 1.5)
            pygame.draw.line(self.surface, fine_col, (x1, y1), (x2, y2), 1)

        # Pulsing core
        core_r   = max(5, int(r * 0.24))
        core_hue = (drift + 0.5) % 1.0
        pygame.draw.circle(self.surface, _hsv(core_hue, 0.60, 0.88),
                           (cx, cy), core_r + 6)
        pygame.draw.circle(self.surface, _hsv(core_hue, 0.20, 1.0),
                           (cx, cy), core_r)
        pygame.draw.circle(self.surface, (255, 255, 255), (cx, cy),
                           max(2, core_r // 3))

    # ------------------------------------------------------------------  DEBRIS
    def _draw_debris(self, run_mgr, t: float):
        for rock in getattr(run_mgr, "debris", []):
            self._draw_rock(rock, t, False)
        for rock in getattr(run_mgr, "shower_rocks", []):
            self._draw_rock(rock, t, True)

    def _draw_rock(self, rock, t: float, tint_hot: bool):
        pts = rock.world_pts()
        if len(pts) < 3:
            return
        # HP-based tint: brighter as damage accumulates
        if rock.is_hit:
            fill, edge = (70, 45, 90), (230, 175, 255)
        elif tint_hot:
            fill, edge = (38, 20, 24), (190, 80, 55)
        else:
            # Slightly lighter fill for rocks with low HP
            hp_frac = rock.hp / (3 if rock.radius >= 13 else 2)
            dim = int(22 * (1 - hp_frac) * 0.5)
            fill = (20 + dim, 16 + dim, 32 + dim)
            edge = (65, 52, 88)
        pygame.draw.polygon(self.surface, fill, pts)
        pygame.draw.polygon(self.surface, edge, pts, 2)
        # Glint on first vertex
        cx = sum(p[0] for p in pts) // len(pts)
        cy = sum(p[1] for p in pts) // len(pts)
        glint_phase = (t * 1.1 + cx * 0.01) % math.tau
        if math.sin(glint_phase) > 0.82:
            glint_col = (140, 115, 165) if not tint_hot else (210, 125, 80)
            pygame.draw.circle(self.surface, glint_col, pts[0], 2)

    # ------------------------------------------------------------------  CANISTERS
    def _draw_canisters(self, run_mgr, t: float):
        for can in getattr(run_mgr, "canisters", []):
            if not can.picked_up:
                self._draw_canister(can, t)

    def _draw_canister(self, can, t: float):
        cx, cy = int(can.pos.x), int(can.pos.y)
        pulse  = math.sin(t * 3.2 + can.pulse) * 2.5
        size   = int(10 + pulse)
        hue    = (0.33 + can.hue_offset * 0.15 + math.sin(t * 0.6) * 0.08) % 1.0
        c_bright = _hsv(hue, 0.9, 1.0)
        c_mid    = _hsv(hue, 0.7, 0.55)
        c_glow   = _hsv(hue, 0.7, 0.30)

        pygame.draw.polygon(self.surface, c_glow,
                            [(cx, cy-size-5),(cx+size+5,cy),(cx,cy+size+5),(cx-size-5,cy)])
        pygame.draw.polygon(self.surface, c_mid,
                            [(cx, cy-size-1),(cx+size+1,cy),(cx,cy+size+1),(cx-size-1,cy)])
        pygame.draw.polygon(self.surface, c_bright,
                            [(cx, cy-size),(cx+size,cy),(cx,cy+size),(cx-size,cy)], 2)
        ang_off = t * 1.2
        for i in range(4):
            ang = ang_off + i * math.pi / 2
            tx1 = int(cx + math.cos(ang) * (size - 5))
            ty1 = int(cy + math.sin(ang) * (size - 5))
            tx2 = int(cx + math.cos(ang) * (size - 2))
            ty2 = int(cy + math.sin(ang) * (size - 2))
            pygame.draw.line(self.surface, c_bright, (tx1, ty1), (tx2, ty2), 1)
        pygame.draw.line(self.surface, c_bright, (cx-3,cy), (cx+3,cy), 1)
        pygame.draw.line(self.surface, c_bright, (cx,cy-3), (cx,cy+3), 1)

    # ------------------------------------------------------------------  BULLETS
    def _draw_bullets(self, ship):
        if not hasattr(ship, "gun"):
            return
        for bullet in ship.gun.bullets:
            bx, by = int(bullet.pos.x), int(bullet.pos.y)
            # Direction line — bright green bolt
            dx = int(bullet.vel.x * 0.022)
            dy = int(bullet.vel.y * 0.022)
            age_frac = 1.0 - bullet.lifetime / S.BULLET_LIFETIME
            hue = 0.33 - age_frac * 0.18   # green → cyan as it ages
            col_core  = _hsv(hue, 0.8, 1.0)
            col_glow  = _hsv(hue, 0.6, 0.45)
            pygame.draw.line(self.surface, col_glow,
                             (bx - dx*2, by - dy*2), (bx + dx, by + dy), 3)
            pygame.draw.line(self.surface, col_core,
                             (bx - dx,   by - dy),   (bx + dx, by + dy), 1)
            pygame.draw.circle(self.surface, (220, 255, 220), (bx, by), 2)

    # ------------------------------------------------------------------  SHIP
    def _draw_trail(self, ship, t: float):
        if not ship.is_alive:
            return
        vel   = ship.body.vel
        speed = vel.length()
        if speed < 30:
            return
        pos       = ship.pos
        trail_len = min(12, 4 + int(speed / 60))
        for i in range(1, trail_len + 1):
            frac = i / (trail_len + 1.0)
            gx = int(pos.x - vel.x * 0.013 * i)
            gy = int(pos.y - vel.y * 0.013 * i)
            if 0 <= gx < S.SCREEN_W and 0 <= gy < S.SCREEN_H:
                hue   = 0.60 - frac * 0.48
                val   = max(0.0, 0.72 - frac * 0.06)
                color = _hsv(hue, 0.95, val)
                pygame.draw.circle(self.surface, color, (gx, gy),
                                   max(1, 4 - i // 3))

    def _draw_velocity_indicator(self, ship):
        if not ship.is_alive:
            return
        vel   = ship.body.vel
        speed = vel.length()
        if speed < 20:
            return
        pos = ship.pos
        nx, ny   = vel.x / speed, vel.y / speed
        px_, py_ = -ny, nx
        dist = 30
        tip  = (int(pos.x + nx * (dist + 5)), int(pos.y + ny * (dist + 5)))
        arm1 = (int(pos.x + nx * (dist-4) + px_*5), int(pos.y + ny * (dist-4) + py_*5))
        arm2 = (int(pos.x + nx * (dist-4) - px_*5), int(pos.y + ny * (dist-4) - py_*5))
        pygame.draw.line(self.surface, (50, 60, 95), arm1, tip, 1)
        pygame.draw.line(self.surface, (50, 60, 95), arm2, tip, 1)
        rx = int(pos.x - nx * dist)
        ry = int(pos.y - ny * dist)
        pygame.draw.circle(self.surface, (70, 28, 28), (rx, ry), 4, 1)
        pygame.draw.line(self.surface, (70, 28, 28),
                         (rx - int(px_*3), ry - int(py_*3)),
                         (rx + int(px_*3), ry + int(py_*3)), 1)

    def _draw_ship(self, ship, t: float = 0.0):
        if not ship.is_alive:
            return
        pos   = ship.pos
        angle = ship.angle
        raw   = [(18,0),(5,-9),(-14,-7),(-14,9),(5,10)]
        pts   = [self._rotate_pt(p, angle, pos) for p in raw]

        hp = ship.hull_pct
        glow_r = int((1.0 - hp) * 60)
        glow_col = (glow_r, max(0, 55 - int((1-hp)*42)), max(0, 115 - int((1-hp)*85)))

        pygame.draw.polygon(self.surface, glow_col, pts, 4)
        pygame.draw.polygon(self.surface, S.WHITE_VEC, pts, 2)

        # Interior spine
        nose  = self._rotate_pt((18, 0), angle, pos)
        belly = self._rotate_pt((-5, 0), angle, pos)
        pygame.draw.line(self.surface, (100, 100, 130), nose, belly, 1)

        nozzle = [self._rotate_pt(p, angle, pos) for p in
                  ((-14,-5),(-20,-3),(-20,5),(-14,7))]
        pygame.draw.polygon(self.surface, (0, 35, 75), nozzle, 3)
        pygame.draw.polygon(self.surface, S.GREY_DEAD, nozzle, 1)

        # RCS port dots
        for lx, ly in ((8,-8),(8,10),(-10,-6),(-10,8)):
            rpt = self._rotate_pt((lx, ly), angle, pos)
            pygame.draw.circle(self.surface, (40, 40, 60), rpt, 1)

        # Gun barrel indicator
        if hasattr(ship, "gun") and not ship.gun.is_jammed:
            barrel_tip  = self._rotate_pt((22, 0), angle, pos)
            barrel_base = self._rotate_pt((15, 0), angle, pos)
            pygame.draw.line(self.surface, (100, 220, 100), barrel_base, barrel_tip, 1)
        elif hasattr(ship, "gun") and ship.gun.is_jammed:
            jam_pulse = 0.5 + 0.5 * abs(math.sin(t * 8))
            jam_col   = (int(200 * jam_pulse), 0, 0)
            barrel_tip  = self._rotate_pt((22, 0), angle, pos)
            barrel_base = self._rotate_pt((15, 0), angle, pos)
            pygame.draw.line(self.surface, jam_col, barrel_base, barrel_tip, 1)

    def _draw_exhaust(self, ship, t: float):
        keys      = pygame.key.get_pressed()
        thrusting = keys[pygame.K_UP] or keys[pygame.K_w]
        reversing = keys[pygame.K_DOWN] or keys[pygame.K_s]
        if not thrusting and not reversing:
            return
        pos    = ship.pos
        angle  = ship.angle
        hp_pct = ship.hull_pct
        flick  = 1.0 + math.sin(t * 53.7) * 0.13

        if thrusting:
            hue     = 0.58 + (1.0 - hp_pct) * 0.26
            c_outer = _hsv(hue, 0.75, 0.32 * flick)
            c_mid   = _hsv(hue, 0.92, 0.72 * flick)
            c_core  = _hsv(hue - 0.04, 0.25, 1.0)
            outer = [self._rotate_pt(p, angle, pos) for p in ((-14,-9),(-58,0),(-14,11))]
            mid   = [self._rotate_pt(p, angle, pos) for p in ((-14,-5),(-38,0),(-14,7))]
            core  = [self._rotate_pt(p, angle, pos) for p in ((-14,-2),(-24,0),(-14,4))]
            pygame.draw.polygon(self.surface, c_outer, outer)
            pygame.draw.polygon(self.surface, c_mid,   mid)
            pygame.draw.polygon(self.surface, c_core,  core)

        if reversing:
            retro = [self._rotate_pt(p, angle, pos) for p in ((18,-2),(30,0),(18,2))]
            pygame.draw.polygon(self.surface, (200, 80, 20), retro)

    # ------------------------------------------------------------------  BARGES
    def _draw_barges(self, run_mgr, ship, t: float = 0.0):
        for barge in run_mgr.barges:
            self._draw_barge(barge, ship, t)

    def _draw_barge(self, barge, ship, t: float = 0.0):
        pos    = barge.pos
        ticks  = pygame.time.get_ticks()
        bx, by = int(pos.x), int(pos.y)

        rect = pygame.Rect(bx-30, by-16, 60, 32)
        pygame.draw.rect(self.surface, (55, 35, 0), rect, 4)
        pygame.draw.rect(self.surface, S.AMBER_TERM, rect, 2)

        # Cargo hold dividers
        for dx in (-14, 0, 14):
            pygame.draw.line(self.surface, (45, 28, 0), (bx+dx, by-14), (bx+dx, by+14), 1)
        pygame.draw.line(self.surface, (70, 44, 0), (bx-22, by), (bx+22, by), 1)

        # Engine pods (rear)
        engine_pulse = 0.55 + 0.45 * abs(math.sin(t * 4.1))
        pod_col  = _hsv(0.09, 0.9, engine_pulse)
        pod_glow = _hsv(0.09, 0.6, engine_pulse * 0.25)
        for py_off in (-10, 10):
            pcx, pcy = bx - 32, by + py_off
            pygame.draw.circle(self.surface, pod_glow, (pcx, pcy), 8)
            pygame.draw.circle(self.surface, pod_col,  (pcx, pcy), 4)
            pygame.draw.circle(self.surface, (255, 240, 200), (pcx, pcy), 2)

        # Forward sensor dome
        pygame.draw.circle(self.surface, (30, 30, 50),   (bx+32, by), 6)
        pygame.draw.circle(self.surface, (80, 80, 120),  (bx+32, by), 4, 1)
        pygame.draw.circle(self.surface, (150, 150, 200),(bx+32, by), 2)

        # Hazard lights
        blink = (ticks // 380) % 2 == 0
        for (lx, ly), on in (((bx-24, by-11), blink), ((bx+24, by+11), not blink)):
            if on:
                pygame.draw.circle(self.surface, (100, 62, 0), (lx, ly), 7)
                pygame.draw.circle(self.surface, S.AMBER_TERM,  (lx, ly), 4)
            else:
                pygame.draw.circle(self.surface, (50, 32, 0), (lx, ly), 4)

        # Tether — jagged lightning polyline
        tether = getattr(barge, "_tether", None)
        if tether and tether.is_active and ship and ship.is_alive:
            sx, sy  = int(ship.pos.x), int(ship.pos.y)
            stretch = min(1.0, math.hypot(sx-bx, sy-by) / S.TETHER_MAX_LENGTH)
            tr = int(40  + 195 * stretch)
            tg = int(200 - 165 * stretch)
            pts = [(bx, by)]
            for k in range(1, 7):
                frac = k / 7
                mx   = int(bx + (sx-bx) * frac)
                my   = int(by + (sy-by) * frac)
                jit  = int((1 - abs(frac - 0.5) * 2) * 6 * stretch)
                pts.append((mx + random.randint(-jit, jit),
                            my + random.randint(-jit, jit)))
            pts.append((sx, sy))
            pygame.draw.lines(self.surface, (min(255,tr), max(0,tg), 40), False, pts, 2)

    # ------------------------------------------------------------------  EFFECTS
    def _draw_proximity_alarm(self, run_mgr, ship, t: float):
        if not ship.is_alive or not run_mgr.barges:
            return
        min_dist = min((barge.pos - ship.pos).length() for barge in run_mgr.barges)
        if min_dist > 340:
            return
        intensity = (1.0 - min_dist / 340.0) * abs(math.sin(t * 5.5))
        if intensity < 0.04:
            return
        r   = min(255, int(intensity * 240))
        col = (r, 0, 0)
        ew  = max(1, int(intensity * 42))
        fh  = S.FLIGHT_H
        pygame.draw.rect(self.surface, col, pygame.Rect(0,               0,       S.SCREEN_W, ew))
        pygame.draw.rect(self.surface, col, pygame.Rect(0,               fh - ew, S.SCREEN_W, ew))
        pygame.draw.rect(self.surface, col, pygame.Rect(0,               0,       ew,         fh))
        pygame.draw.rect(self.surface, col, pygame.Rect(S.SCREEN_W - ew, 0,       ew,         fh))

    def _draw_flash(self, dt: float):
        if self._flash_t <= 0:
            return
        alpha   = min(210, int(self._flash_t * 520))
        overlay = pygame.Surface((S.SCREEN_W, S.FLIGHT_H), pygame.SRCALPHA)
        overlay.fill((*self._flash_col, alpha))
        self.surface.blit(overlay, (0, 0))
        self._flash_t -= dt

    # ------------------------------------------------------------------
    def _draw_spore_effect(self, ship, t: float):
        """Green psychedelic tint + warning text when MycoShroom inverts controls."""
        cargo = getattr(ship, "cargo", None)
        if cargo is None or not getattr(cargo, "inversion_active", False):
            return
        pct   = cargo.invert_pct
        alpha = int(28 + 22 * math.sin(t * 8.0))   # fast shimmer
        overlay = pygame.Surface((S.SCREEN_W, S.FLIGHT_H), pygame.SRCALPHA)
        overlay.fill((0, 180, 60, alpha))
        self.surface.blit(overlay, (0, 0))

        if int(t * 3) % 2 == 0:
            font = pygame.font.SysFont("monospace", 22, bold=True)
            msg  = font.render("⚠  CONTROLS INVERTED  ⚠", True, (0, 255, 80))
            self.surface.blit(msg, (S.SCREEN_W // 2 - msg.get_width() // 2,
                                    S.FLIGHT_H // 2 - 60))

    @staticmethod
    def _rotate_pt(pt: tuple, angle_deg: float, origin) -> tuple:
        rad = math.radians(angle_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        x, y = pt
        return (int(x * cos_a - y * sin_a + origin.x),
                int(x * sin_a + y * cos_a + origin.y))
