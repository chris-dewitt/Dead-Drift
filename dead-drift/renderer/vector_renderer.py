from __future__ import annotations
import math
import random
import pygame
from config import settings as S
from core.event_bus import bus, EVT_SLINGSHOT


# ---------------------------------------------------------------------------
def _hsv(h: float, s: float = 1.0, v: float = 1.0) -> tuple:
    """Inline HSV→RGB — no colorsys import needed."""
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
    Draws the flight scene: ship, barges, gravity wells, exhaust.
    All geometry is procedural — no sprite sheets.
    Aesthetic: psychedelic minimalist. Dark void, neon glow, color cycling.
    """

    _STAR_SEED  = 7
    _STAR_COUNT = 140

    def __init__(self, surface: pygame.Surface):
        self.surface    = surface
        self._stars     = self._gen_stars()
        self._flash_t   = 0.0        # slingshot white flash
        self._flash_col = (180, 220, 255)
        bus.subscribe(EVT_SLINGSHOT, self._on_slingshot)

    def _on_slingshot(self, **_):
        self._flash_t   = 0.45
        self._flash_col = (160, 210, 255)

    # ------------------------------------------------------------------
    def draw(self, run_mgr, ship, dt: float = 0.016):
        t = pygame.time.get_ticks() / 1000.0
        self._draw_stars()
        self._draw_gravity_wells(run_mgr, t)
        self._draw_debris(run_mgr, t)
        self._draw_canisters(run_mgr, t)
        self._draw_barges(run_mgr, ship)
        self._draw_trail(ship, t)
        self._draw_velocity_indicator(ship)
        self._draw_ship(ship)
        self._draw_exhaust(ship, t)
        self._draw_proximity_alarm(run_mgr, ship, t)
        self._draw_flash(dt)

    # ------------------------------------------------------------------  STARS
    def _gen_stars(self) -> list:
        rng = random.Random(self._STAR_SEED)
        stars = []
        for _ in range(self._STAR_COUNT):
            x   = rng.randint(0, S.SCREEN_W - 1)
            y   = rng.randint(0, S.SCREEN_H - 1)
            lum = rng.random()
            hue = rng.random()
            stars.append((x, y, lum, hue))
        return stars

    def _draw_stars(self):
        surf = self.surface
        for x, y, lum, hue in self._stars:
            if lum < 0.50:
                # Plain dim white
                v = int(lum * 40)
                surf.set_at((x, y), (v, v, v + 8))
            elif lum < 0.82:
                # Mid grey-blue
                v = int(48 + lum * 65)
                surf.set_at((x, y), (v - 14, v - 14, v))
            elif lum < 0.94:
                # Bright white point
                pygame.draw.circle(surf, (200, 200, 228), (x, y), 1)
            else:
                # Neon accent — cyan / magenta / amber
                neon = [
                    (0, 220, 255),   # cyan
                    (220, 0, 255),   # magenta
                    (255, 180, 0),   # amber
                ][int(hue * 3) % 3]
                pygame.draw.circle(surf, neon, (x, y), 1)

    # ------------------------------------------------------------------  GRAVITY WELLS
    def _draw_gravity_wells(self, run_mgr, t: float):
        if run_mgr.sector is None:
            return
        for well in run_mgr.sector.gravity.wells:
            self._draw_well(well, t)

    def _draw_well(self, well, t: float):
        cx, cy = int(well.pos.x), int(well.pos.y)
        r      = well.radius
        drift  = (t * 0.07) % 1.0      # full hue cycle ~14s
        pulse  = math.sin(t * 1.4) * 3.5

        # 5 concentric rings — hue spreads across 0.35 of the wheel
        rings = [
            (r * 3.9 + pulse * 1.3, 0.00, 0.22),
            (r * 2.7 + pulse * 0.9, 0.08, 0.38),
            (r * 1.7 + pulse * 0.5, 0.17, 0.58),
            (r * 1.1 + pulse * 0.2, 0.26, 0.80),
            (r * 0.65,              0.35, 0.95),
        ]
        for radius, hue_off, val in rings:
            ir = max(1, int(radius))
            hue   = (drift + hue_off) % 1.0
            color = _hsv(hue, 0.92, val)
            pygame.draw.circle(self.surface, color, (cx, cy), ir, 1)
            # Soft glow ring on innermost three
            if val > 0.55:
                glow = _hsv(hue, 0.7, val * 0.22)
                pygame.draw.circle(self.surface, glow, (cx, cy), ir + 4, 1)

        # Slowly rotating radial lines (8-fold symmetry)
        line_hue = (drift + 0.12) % 1.0
        line_col = _hsv(line_hue, 0.75, 0.32)
        for i in range(8):
            ang = math.radians(i * 45 + t * 9)   # rotate ~1.5 rpm
            x1 = cx + int(math.cos(ang) * r * 1.6)
            y1 = cy + int(math.sin(ang) * r * 1.6)
            x2 = cx + int(math.cos(ang) * r * 0.88)
            y2 = cy + int(math.sin(ang) * r * 0.88)
            pygame.draw.line(self.surface, line_col, (x1, y1), (x2, y2), 1)

        # Pulsing core
        core_r   = max(4, int(r * 0.22))
        core_hue = (drift + 0.5) % 1.0
        pygame.draw.circle(self.surface, _hsv(core_hue, 0.55, 0.85),
                           (cx, cy), core_r + 4)
        pygame.draw.circle(self.surface, _hsv(core_hue, 0.15, 1.0),
                           (cx, cy), core_r)

    # ------------------------------------------------------------------  DEBRIS
    def _draw_debris(self, run_mgr, t: float):
        debris = getattr(run_mgr, 'debris', [])
        for rock in debris:
            pts = rock.world_pts()
            if len(pts) < 3:
                continue
            if rock.is_hit:
                fill  = (60, 40, 80)
                edge  = (200, 160, 255)
            else:
                fill  = (20, 16, 32)
                edge  = (65, 52, 88)
            pygame.draw.polygon(self.surface, fill, pts)
            pygame.draw.polygon(self.surface, edge, pts, 1)

    # ------------------------------------------------------------------  CANISTERS
    def _draw_canisters(self, run_mgr, t: float):
        canisters = getattr(run_mgr, 'canisters', [])
        for can in canisters:
            if can.picked_up:
                continue
            self._draw_canister(can, t)

    def _draw_canister(self, can, t: float):
        cx, cy = int(can.pos.x), int(can.pos.y)
        pulse  = math.sin(t * 3.2 + can.pulse) * 2.5
        size   = int(10 + pulse)
        hue    = (0.33 + can.hue_offset * 0.15 + math.sin(t * 0.6) * 0.08) % 1.0

        c_bright = _hsv(hue, 0.9, 1.0)
        c_glow   = _hsv(hue, 0.7, 0.30)

        # Outer glow diamond
        glow_pts = [(cx, cy - size - 5), (cx + size + 5, cy),
                    (cx, cy + size + 5), (cx - size - 5, cy)]
        pygame.draw.polygon(self.surface, c_glow, glow_pts)

        # Inner bright diamond
        pts = [(cx, cy - size), (cx + size, cy),
               (cx, cy + size), (cx - size, cy)]
        pygame.draw.polygon(self.surface, c_bright, pts, 1)

        # Crosshair centre
        pygame.draw.line(self.surface, c_bright,
                         (cx - 3, cy), (cx + 3, cy), 1)
        pygame.draw.line(self.surface, c_bright,
                         (cx, cy - 3), (cx, cy + 3), 1)

    # ------------------------------------------------------------------  SHIP
    def _draw_trail(self, ship, t: float):
        if not ship.is_alive:
            return
        vel   = ship.body.vel
        speed = vel.length()
        if speed < 30:
            return
        pos = ship.pos
        for i in range(1, 7):
            frac = i / 7.0
            gx = int(pos.x - vel.x * 0.010 * i)
            gy = int(pos.y - vel.y * 0.010 * i)
            if 0 <= gx < S.SCREEN_W and 0 <= gy < S.SCREEN_H:
                # Chromatic smear: blue→purple→red with age
                hue   = 0.58 - frac * 0.42
                val   = max(0.0, 0.65 - frac * 0.09)
                color = _hsv(hue, 0.95, val)
                pygame.draw.circle(self.surface, color, (gx, gy),
                                   max(1, 3 - i // 2))

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

        # Prograde chevron
        tip  = (int(pos.x + nx * (dist + 5)), int(pos.y + ny * (dist + 5)))
        arm1 = (int(pos.x + nx * (dist - 4) + px_ * 5),
                int(pos.y + ny * (dist - 4) + py_ * 5))
        arm2 = (int(pos.x + nx * (dist - 4) - px_ * 5),
                int(pos.y + ny * (dist - 4) - py_ * 5))
        pygame.draw.line(self.surface, (50, 60, 95), arm1, tip, 1)
        pygame.draw.line(self.surface, (50, 60, 95), arm2, tip, 1)

        # Retrograde circle + crossbar
        rx = int(pos.x - nx * dist)
        ry = int(pos.y - ny * dist)
        pygame.draw.circle(self.surface, (70, 28, 28), (rx, ry), 4, 1)
        pygame.draw.line(self.surface, (70, 28, 28),
                         (rx - int(px_ * 3), ry - int(py_ * 3)),
                         (rx + int(px_ * 3), ry + int(py_ * 3)), 1)

    def _draw_ship(self, ship):
        if not ship.is_alive:
            return
        pos   = ship.pos
        angle = ship.angle
        raw   = [(18,0),(5,-9),(-14,-7),(-14,9),(5,10)]
        pts   = [self._rotate_pt(p, angle, pos) for p in raw]

        # Neon glow halo (wider dim layer first)
        pygame.draw.polygon(self.surface, (0, 55, 115), pts, 4)
        # Crisp bright outline on top
        pygame.draw.polygon(self.surface, S.WHITE_VEC, pts, 2)

        nozzle = [self._rotate_pt(p, angle, pos) for p in
                  ((-14,-5),(-20,-3),(-20,5),(-14,7))]
        pygame.draw.polygon(self.surface, (0, 35, 75), nozzle, 3)
        pygame.draw.polygon(self.surface, S.GREY_DEAD, nozzle, 1)

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
            # Hue: electric blue (healthy) → magenta (damaged)
            hue      = 0.58 + (1.0 - hp_pct) * 0.26
            c_outer  = _hsv(hue, 0.75, 0.32 * flick)
            c_mid    = _hsv(hue, 0.92, 0.72 * flick)
            c_core   = _hsv(hue - 0.04, 0.25, 1.0)

            outer = [self._rotate_pt(p, angle, pos) for p in
                     ((-14,-9),(-54,0),(-14,11))]
            mid   = [self._rotate_pt(p, angle, pos) for p in
                     ((-14,-5),(-36,0),(-14,7))]
            core  = [self._rotate_pt(p, angle, pos) for p in
                     ((-14,-2),(-22,0),(-14,4))]

            pygame.draw.polygon(self.surface, c_outer, outer)
            pygame.draw.polygon(self.surface, c_mid,   mid)
            pygame.draw.polygon(self.surface, c_core,  core)

        if reversing:
            retro = [self._rotate_pt(p, angle, pos) for p in
                     ((18,-2),(28,0),(18,2))]
            pygame.draw.polygon(self.surface, (200, 80, 20), retro)

    # ------------------------------------------------------------------  BARGES
    def _draw_barges(self, run_mgr, ship):
        for barge in run_mgr.barges:
            self._draw_barge(barge, ship)

    def _draw_barge(self, barge, ship):
        pos   = barge.pos
        ticks = pygame.time.get_ticks()

        # Hull — neon amber glow + bright outline
        rect = pygame.Rect(int(pos.x - 30), int(pos.y - 16), 60, 32)
        pygame.draw.rect(self.surface, (55, 35, 0), rect, 4)   # glow
        pygame.draw.rect(self.surface, S.AMBER_TERM, rect, 2)  # outline

        # Interior spine
        pygame.draw.line(self.surface, (70, 44, 0),
                         (int(pos.x - 22), int(pos.y)),
                         (int(pos.x + 22), int(pos.y)), 1)

        # Alternating hazard lights with glow
        blink = (ticks // 380) % 2 == 0
        for (lx, ly), on in (
            ((int(pos.x - 24), int(pos.y - 11)), blink),
            ((int(pos.x + 24), int(pos.y + 11)), not blink),
        ):
            if on:
                pygame.draw.circle(self.surface, (100, 62, 0), (lx, ly), 7)
                pygame.draw.circle(self.surface, S.AMBER_TERM,  (lx, ly), 4)
            else:
                pygame.draw.circle(self.surface, (50, 32, 0),  (lx, ly), 4)

        # Tether line — tension-tinted green→red
        tether = getattr(barge, '_tether', None)
        if tether and tether.is_active and ship and ship.is_alive:
            bx, by = int(pos.x), int(pos.y)
            sx, sy = int(ship.pos.x), int(ship.pos.y)
            stretch = min(1.0, math.hypot(sx-bx, sy-by) / S.TETHER_MAX_LENGTH)
            tr = int(40  + 195 * stretch)
            tg = int(200 - 165 * stretch)
            pygame.draw.line(self.surface, (min(255,tr), max(0,tg), 40),
                             (bx, by), (sx, sy), 1)

    # ------------------------------------------------------------------  EFFECTS
    def _draw_proximity_alarm(self, run_mgr, ship, t: float):
        if not ship.is_alive or not run_mgr.barges:
            return
        min_dist = min(
            (barge.pos - ship.pos).length() for barge in run_mgr.barges
        )
        if min_dist > 340:
            return
        intensity = (1.0 - min_dist / 340.0) * abs(math.sin(t * 5.5))
        if intensity < 0.04:
            return
        r   = min(255, int(intensity * 240))
        col = (r, 0, 0)
        ew  = max(1, int(intensity * 38))
        fh  = S.FLIGHT_H
        pygame.draw.rect(self.surface, col, pygame.Rect(0,        0,        S.SCREEN_W, ew))
        pygame.draw.rect(self.surface, col, pygame.Rect(0,        fh - ew,  S.SCREEN_W, ew))
        pygame.draw.rect(self.surface, col, pygame.Rect(0,        0,        ew,         fh))
        pygame.draw.rect(self.surface, col, pygame.Rect(S.SCREEN_W - ew, 0, ew,         fh))

    def _draw_flash(self, dt: float):
        if self._flash_t <= 0:
            return
        alpha = min(210, int(self._flash_t * 520))
        overlay = pygame.Surface((S.SCREEN_W, S.FLIGHT_H), pygame.SRCALPHA)
        overlay.fill((*self._flash_col, alpha))
        self.surface.blit(overlay, (0, 0))
        self._flash_t -= dt

    # ------------------------------------------------------------------
    @staticmethod
    def _rotate_pt(pt: tuple, angle_deg: float, origin) -> tuple:
        rad = math.radians(angle_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        x, y = pt
        return (int(x * cos_a - y * sin_a + origin.x),
                int(x * sin_a + y * cos_a + origin.y))
