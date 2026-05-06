from __future__ import annotations
import math
import random
import pygame
from config import settings as S


class VectorRenderer:
    """
    Draws the flight scene: ship, barges, gravity wells, exhaust.
    All geometry is procedural vector art — no sprite sheets.
    """

    _STAR_SEED = 7
    _STAR_COUNT = 130

    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self._stars  = self._gen_stars()

    # ------------------------------------------------------------------
    def draw(self, run_mgr, ship):
        t = pygame.time.get_ticks() / 1000.0
        self._draw_stars()
        self._draw_gravity_wells(run_mgr, t)
        self._draw_barges(run_mgr, ship)
        self._draw_trail(ship)
        self._draw_velocity_indicator(ship)
        self._draw_ship(ship)
        self._draw_exhaust(ship, t)

    # ------------------------------------------------------------------  STARS
    def _gen_stars(self) -> list:
        rng = random.Random(self._STAR_SEED)
        stars = []
        for _ in range(self._STAR_COUNT):
            x   = rng.randint(0, S.SCREEN_W - 1)
            y   = rng.randint(0, S.SCREEN_H - 1)
            lum = rng.random()
            stars.append((x, y, lum))
        return stars

    def _draw_stars(self):
        surf = self.surface
        for x, y, lum in self._stars:
            if lum < 0.55:
                v = int(lum * 36)
                surf.set_at((x, y), (v, v, v + 6))
            elif lum < 0.88:
                v = int(50 + lum * 70)
                surf.set_at((x, y), (v - 12, v - 12, v))
            else:
                pygame.draw.circle(surf, (200, 200, 225), (x, y), 1)

    # ------------------------------------------------------------------  GRAVITY WELLS
    def _draw_gravity_wells(self, run_mgr, t: float):
        if run_mgr.sector is None:
            return
        for well in run_mgr.sector.gravity.wells:
            self._draw_well(well, t)

    def _draw_well(self, well, t: float):
        cx, cy = int(well.pos.x), int(well.pos.y)
        r      = well.radius
        pulse  = math.sin(t * 1.4) * 3.5

        # Four concentric rings — outermost is barely visible
        rings = [
            (r * 3.8 + pulse * 1.2, (10,  6, 24)),
            (r * 2.6 + pulse * 0.8, (20, 12, 48)),
            (r * 1.6 + pulse * 0.4, (38, 22, 82)),
            (r       + pulse * 0.2, (62, 38, 128)),
        ]
        for radius, color in rings:
            ir = int(radius)
            if ir > 1:
                pygame.draw.circle(self.surface, color, (cx, cy), ir, 1)

        # Radial inward lines (8-fold, converge toward singularity)
        line_color = (28, 16, 58)
        for i in range(8):
            ang = math.radians(i * 45)
            x1  = cx + int(math.cos(ang) * r * 1.55)
            y1  = cy + int(math.sin(ang) * r * 1.55)
            x2  = cx + int(math.cos(ang) * r * 0.85)
            y2  = cy + int(math.sin(ang) * r * 0.85)
            pygame.draw.line(self.surface, line_color, (x1, y1), (x2, y2), 1)

        # Solid core
        core_r = max(3, int(r * 0.22))
        pygame.draw.circle(self.surface, (88, 52, 172), (cx, cy), core_r)

    # ------------------------------------------------------------------  SHIP
    def _draw_trail(self, ship):
        if not ship.is_alive:
            return
        vel   = ship.body.vel
        speed = vel.length()
        if speed < 30:
            return
        pos = ship.pos
        for i in range(1, 6):
            frac = i / 6.0
            gx   = int(pos.x - vel.x * 0.009 * i)
            gy   = int(pos.y - vel.y * 0.009 * i)
            if 0 <= gx < S.SCREEN_W and 0 <= gy < S.SCREEN_H:
                v = max(0, 55 - i * 10)
                pygame.draw.circle(self.surface, (v - 5, v - 5, v + 8), (gx, gy), max(1, 3 - i // 2))

    def _draw_velocity_indicator(self, ship):
        """Prograde/retrograde markers — show actual travel direction vs. heading."""
        if not ship.is_alive:
            return
        vel   = ship.body.vel
        speed = vel.length()
        if speed < 20:
            return

        pos  = ship.pos
        nx   = vel.x / speed      # velocity unit vector
        ny   = vel.y / speed
        px_  = -ny                # perpendicular
        py_  =  nx

        # Prograde: dim blue-grey chevron pointing in direction of travel
        dist = 30
        tip  = (int(pos.x + nx * (dist + 5)), int(pos.y + ny * (dist + 5)))
        arm1 = (int(pos.x + nx * (dist - 4) + px_ * 5),
                int(pos.y + ny * (dist - 4) + py_ * 5))
        arm2 = (int(pos.x + nx * (dist - 4) - px_ * 5),
                int(pos.y + ny * (dist - 4) - py_ * 5))
        c_pro = (50, 60, 95)
        pygame.draw.line(self.surface, c_pro, arm1, tip, 1)
        pygame.draw.line(self.surface, c_pro, arm2, tip, 1)

        # Retrograde: dim red circle, opposite side — "this is your brake target"
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
        pts   = [self._rotate_pt(p, angle, pos) for p in (
            ( 18,   0),
            (  5,  -9),
            (-14,  -7),
            (-14,   9),
            (  5,  10),
        )]
        pygame.draw.polygon(self.surface, S.WHITE_VEC, pts, 1)

        nozzle = [self._rotate_pt(p, angle, pos) for p in (
            (-14, -5), (-20, -3), (-20, 5), (-14, 7),
        )]
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
        flick  = 1.0 + math.sin(t * 53.7) * 0.12  # fast shimmer

        if thrusting:
            r = int((20 + 18 * hp_pct) * flick)
            g = int((70 + 45 * hp_pct) * flick)
            b = 255
            c_hot  = (min(255, r), min(255, g), b)
            c_cool = (min(255, r // 3), min(255, g // 3), 170)

            outer = [self._rotate_pt(p, angle, pos) for p in (
                (-14, -6), (-46, 0), (-14, 8),
            )]
            inner = [self._rotate_pt(p, angle, pos) for p in (
                (-14, -3), (-28, 0), (-14, 5),
            )]
            pygame.draw.polygon(self.surface, c_cool, outer)
            pygame.draw.polygon(self.surface, c_hot,  inner)

        if reversing:
            retro = [self._rotate_pt(p, angle, pos) for p in (
                (18, -2), (26, 0), (18, 2),
            )]
            pygame.draw.polygon(self.surface, (160, 65, 10), retro)

    # ------------------------------------------------------------------  BARGES
    def _draw_barges(self, run_mgr, ship):
        for barge in run_mgr.barges:
            self._draw_barge(barge, ship)

    def _draw_barge(self, barge, ship):
        pos   = barge.pos
        ticks = pygame.time.get_ticks()

        # Hull — thick amber outline
        rect = pygame.Rect(int(pos.x - 30), int(pos.y - 16), 60, 32)
        pygame.draw.rect(self.surface, S.AMBER_TERM, rect, 2)

        # Interior spine (industrial detail)
        pygame.draw.line(self.surface, (75, 48, 0),
                         (int(pos.x - 22), int(pos.y)),
                         (int(pos.x + 22), int(pos.y)), 1)

        # Alternating hazard lights
        blink    = (ticks // 380) % 2 == 0
        lit      = S.AMBER_TERM
        unlit    = (55, 35, 0)
        pygame.draw.circle(self.surface, lit   if blink else unlit,
                           (int(pos.x - 24), int(pos.y - 11)), 4)
        pygame.draw.circle(self.surface, unlit if blink else lit,
                           (int(pos.x + 24), int(pos.y + 11)), 4)

        # Tether line — tension-tinted, green → red as it stretches
        tether = getattr(barge, '_tether', None)
        if tether and tether.is_active and ship and ship.is_alive:
            bx, by = int(pos.x), int(pos.y)
            sx, sy = int(ship.pos.x), int(ship.pos.y)
            stretch = min(1.0, math.hypot(sx - bx, sy - by) / S.TETHER_MAX_LENGTH)
            tr = int(40  + 195 * stretch)
            tg = int(200 - 165 * stretch)
            pygame.draw.line(self.surface, (min(255, tr), max(0, tg), 40),
                             (bx, by), (sx, sy), 1)

    # ------------------------------------------------------------------
    @staticmethod
    def _rotate_pt(pt: tuple, angle_deg: float, origin) -> tuple:
        rad = math.radians(angle_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        x, y = pt
        rx = x * cos_a - y * sin_a + origin.x
        ry = x * sin_a + y * cos_a + origin.y
        return (int(rx), int(ry))
