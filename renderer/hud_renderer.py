from __future__ import annotations
import pygame
from config import settings as S
from ship.hud import HUD
from ship.ship import PlayerShip


class HUDRenderer:
    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self._hud: HUD | None = None

    def attach(self, ship: PlayerShip):
        self._hud = HUD(ship)

    def draw(self, ship: PlayerShip, run_mgr=None):
        if self._hud is None or self._hud.ship is not ship:
            self._hud = HUD(ship)
        self._hud.update(1 / 60)
        self._hud.draw(self.surface, snap_charge=self._snap_charge(run_mgr))
        # Epic 11.1c — harmonica heal session indicator.
        self._draw_harm_session(run_mgr)

    def _draw_harm_session(self, run_mgr) -> None:
        if run_mgr is None or not getattr(run_mgr, "harm_session_active", False):
            return
        from core.text import get_font
        pct = float(run_mgr.harm_session_pct())
        # Small panel anchored to the upper-centre of the flight area.
        w, h = 240, 36
        cx = self.surface.get_width() // 2
        rect = pygame.Rect(cx - w // 2, 12, w, h)
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((20, 8, 14, 220))
        self.surface.blit(bg, rect.topleft)
        pygame.draw.rect(self.surface, (220, 140, 60), rect, 1)
        # Brass corner brackets — diegetic harp-case feel.
        for c, sx, sy in (
            (rect.topleft, 1, 1), (rect.topright, -1, 1),
            (rect.bottomleft, 1, -1), (rect.bottomright, -1, -1),
        ):
            pygame.draw.line(self.surface, (255, 180, 90),
                             c, (c[0] + sx * 10, c[1]), 2)
            pygame.draw.line(self.surface, (255, 180, 90),
                             c, (c[0], c[1] + sy * 10), 2)
        # Title
        f_h = get_font(10, bold=True)
        title = f_h.render("BAX  HARMONICA  HEAL", True, (240, 200, 120))
        self.surface.blit(title, (rect.left + 8, rect.top + 4))
        # Progress bar
        bar = pygame.Rect(rect.left + 8, rect.bottom - 10,
                          rect.width - 16, 6)
        pygame.draw.rect(self.surface, (60, 40, 18), bar)
        fill = bar.copy()
        fill.width = int(bar.width * pct)
        pygame.draw.rect(self.surface, (255, 180, 60), fill)
        pygame.draw.rect(self.surface, (160, 110, 40), bar, 1)

    def _snap_charge(self, run_mgr) -> float | None:
        if run_mgr is None:
            return None

        max_charge: float | None = None
        for barge in getattr(run_mgr, "barges", []):
            tether = getattr(barge, "_tether", None)
            if tether is None or not getattr(tether, "is_active", False):
                continue
            lateral_speed = max(0.0, float(getattr(tether, "lateral_speed", 0.0)))
            charge = min(1.0, lateral_speed / S.SNAP_VELOCITY)
            max_charge = charge if max_charge is None else max(max_charge, charge)

        return max_charge
