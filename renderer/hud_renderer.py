from __future__ import annotations
import pygame
from ship.hud import HUD
from ship.ship import PlayerShip


class HUDRenderer:
    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self._hud: HUD | None = None

    def attach(self, ship: PlayerShip):
        self._hud = HUD(ship)

    def draw(self, ship: PlayerShip):
        if self._hud is None or self._hud.ship is not ship:
            self._hud = HUD(ship)
        self._hud.update(1 / 60)
        self._hud.draw(self.surface)
