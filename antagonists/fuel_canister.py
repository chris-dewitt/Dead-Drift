from __future__ import annotations
import math
import random
from physics.body import Vec2
from config import settings as S
from core.event_bus import bus, EVT_CANISTER_GRAB


class FuelCanister:
    """
    Drifting fuel drum. Fly through it for a thruster boost.
    Pulsing diamond shape — hard to miss, worth chasing.
    """

    def __init__(self, x: float | None = None, y: float | None = None):
        self.pos = Vec2(
            x if x is not None else random.randint(120, S.SCREEN_W - 120),
            y if y is not None else random.randint(80, S.FLIGHT_H - 80),
        )
        self.picked_up  = False
        self._phase     = random.uniform(0, math.pi * 2)   # pulse offset
        self._hue_off   = random.uniform(0, 1.0)

    # ------------------------------------------------------------------
    def update(self, dt: float, ship_pos: Vec2) -> bool:
        if self.picked_up:
            return False
        if (self.pos - ship_pos).length() < S.CANISTER_PICKUP_R:
            self.picked_up = True
            bus.emit(EVT_CANISTER_GRAB)
            return True
        return False

    @property
    def pulse(self) -> float:
        return self._phase

    @property
    def hue_offset(self) -> float:
        return self._hue_off
