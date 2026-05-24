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
