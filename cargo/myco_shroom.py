from __future__ import annotations
import random
from cargo.cargo_base import BaseCargo
from core.event_bus import bus, EVT_SPORE_INVERTED
from config import settings as S


class MycoShroom(BaseCargo):
    """Ch.2: Psychoactive fungal spores — periodically inverts controls."""

    def __init__(self):
        super().__init__("EPISTEMOLOGICAL SHROOMS")
        self.inversion_active = False
        self.invert_pct       = 0.0   # 1.0→0.0 while inverted (used by renderer)
        self.spore_level      = 0.0   # 0.0–1.0 ambient pressure meter
        self._invert_t        = 0.0
        self._next_trigger    = random.uniform(S.SPORE_INTERVAL_MIN, S.SPORE_INTERVAL_MAX)

    def update(self, dt: float, ship) -> None:
        self.spore_level = min(1.0, self.spore_level + dt * 0.018)

        if self.inversion_active:
            self._invert_t -= dt
            self.invert_pct = max(0.0, self._invert_t / S.SPORE_DURATION)
            if self._invert_t <= 0.0:
                self.inversion_active  = False
                self.invert_pct        = 0.0
                ship.controls_inverted = False
                bus.emit(EVT_SPORE_INVERTED, active=False)
                self.spore_level       = max(0.0, self.spore_level - 0.35)
                self._next_trigger     = random.uniform(S.SPORE_INTERVAL_MIN,
                                                        S.SPORE_INTERVAL_MAX)
        else:
            self._next_trigger -= dt
            if self._next_trigger <= 0.0:
                self.inversion_active  = True
                self._invert_t         = S.SPORE_DURATION
                self.invert_pct        = 1.0
                ship.controls_inverted = True
                bus.emit(EVT_SPORE_INVERTED, active=True)

    def _on_damage(self) -> None:
        self._next_trigger = max(0.0, self._next_trigger - 6.0)
        self.spore_level   = min(1.0, self.spore_level + 0.22)

    def terminal_climax(self) -> str:
        return "gary"
