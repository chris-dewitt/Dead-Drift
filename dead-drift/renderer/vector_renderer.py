from __future__ import annotations
import math
import pygame
from config import settings as S


class VectorRenderer:
    """
    Draws the flight scene: ship, barges, gravity wells, exhaust.
    All geometry is procedural vector art — no sprite sheets.
    """

    def __init__(self, surface: pygame.Surface):
        self.surface = surface

    def draw(self, run_mgr, ship):
        self._draw_gravity_wells(run_mgr)
        self._draw_barges(run_mgr)
        self._draw_ship(ship)
        self._draw_exhaust(ship)

    # ------------------------------------------------------------------
    def _draw_ship(self, ship):
        if not ship.is_alive:
            return

        pos   = ship.pos
        angle = ship.angle
        color = S.WHITE_VEC

        # Asymmetrical hull polygon (5 points)
        raw_pts = [
            ( 18,   0),   # nose
            (  5,  -9),   # upper shoulder
            (-14,  -7),   # upper aft
            (-14,   9),   # lower aft
            (  5,  10),   # lower shoulder
        ]
        pts = [self._rotate_pt(p, angle, pos) for p in raw_pts]
        pygame.draw.polygon(self.surface, color, pts, 1)

        # Engine nozzle (small rect at aft)
        nozzle_pts = [
            self._rotate_pt((-14, -5), angle, pos),
            self._rotate_pt((-20, -3), angle, pos),
            self._rotate_pt((-20,  5), angle, pos),
            self._rotate_pt((-14,  7), angle, pos),
        ]
        pygame.draw.polygon(self.surface, S.GREY_DEAD, nozzle_pts, 1)

    def _draw_exhaust(self, ship):
        keys = pygame.key.get_pressed()
        if not (keys[pygame.K_UP] or keys[pygame.K_w]):
            return

        pos   = ship.pos
        angle = ship.angle
        hp_pct = ship.hull_pct

        # Exhaust color degrades with hull damage
        r  = int(30  * hp_pct)
        g  = int(80  * hp_pct)
        b  = 255
        color = (max(0, min(255, r)), max(0, min(255, g)), b)

        exhaust_pts = [
            self._rotate_pt((-14, -3), angle, pos),
            self._rotate_pt((-32,  0), angle, pos),
            self._rotate_pt((-14,  5), angle, pos),
        ]
        pygame.draw.polygon(self.surface, color, exhaust_pts)

    def _draw_gravity_wells(self, run_mgr):
        if run_mgr.sector is None:
            return
        for well in run_mgr.sector.gravity.wells:
            # Outer glow ring
            pygame.draw.circle(
                self.surface, (30, 20, 60),
                (int(well.pos.x), int(well.pos.y)),
                int(well.radius), 1,
            )
            # Inner mass
            pygame.draw.circle(
                self.surface, (60, 40, 120),
                (int(well.pos.x), int(well.pos.y)),
                max(4, int(well.radius * 0.3)),
            )

    def _draw_barges(self, run_mgr):
        for barge in run_mgr.barges:
            self._draw_barge(barge)

    def _draw_barge(self, barge):
        pos = barge.pos
        # Big ugly rectangle
        rect = pygame.Rect(pos.x - 30, pos.y - 16, 60, 32)
        pygame.draw.rect(self.surface, S.AMBER_TERM, rect, 2)

        # Hazard light blinking (use time mod)
        ticks = pygame.time.get_ticks()
        if (ticks // 400) % 2 == 0:
            pygame.draw.circle(self.surface, S.AMBER_TERM,
                               (int(pos.x - 22), int(pos.y - 10)), 4)
            pygame.draw.circle(self.surface, S.AMBER_TERM,
                               (int(pos.x + 22), int(pos.y + 10)), 4)

    # ------------------------------------------------------------------
    @staticmethod
    def _rotate_pt(pt: tuple, angle_deg: float, origin) -> tuple:
        rad = math.radians(angle_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        x, y = pt
        rx = x * cos_a - y * sin_a + origin.x
        ry = x * sin_a + y * cos_a + origin.y
        return (int(rx), int(ry))
