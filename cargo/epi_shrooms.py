from __future__ import annotations
import random
from cargo.cargo_base import BaseCargo
from core.event_bus import bus, EVT_CARGO_DAMAGED, EVT_SPORE_INVERTED
from config import settings as S


class EpistemologicalShrooms(BaseCargo):
    """
    Ch.2 — bioluminescent psychic fungi.
    Every SPORE_INTERVAL seconds, controls invert for SPORE_DURATION seconds.
    spore_level rises over time (pressure curve — creates urgency even without damage)
    AND rises on cargo damage (hits shorten the inversion interval further).
    Both drivers are intentional: time ensures the mechanic always fires,
    damage makes careful flying matter.
    """

    def __init__(self):
        super().__init__("WEAPONIZED EPISTEMOLOGICAL SHROOMS")
        self.spore_level     = 0.0
        self._invert_active  = False
        self._invert_t       = 0.0
        self._next_cd        = random.uniform(S.SPORE_INTERVAL_MIN, S.SPORE_INTERVAL_MAX)

    # ------------------------------------------------------------------
    def update(self, dt: float, ship) -> None:
        # Spore pressure builds gradually — drives pre-warning vignette in renderer
        self.spore_level = min(1.0, self.spore_level + dt * 0.018)

        if self._invert_active:
            self._invert_t -= dt
            if self._invert_t <= 0.0:
                self._invert_active    = False
                ship.controls_inverted = False
                bus.emit(EVT_SPORE_INVERTED, active=False)
                self.spore_level       = max(0.0, self.spore_level - 0.35)
                interval = random.uniform(S.SPORE_INTERVAL_MIN, S.SPORE_INTERVAL_MAX)
                self._next_cd = interval * max(0.4, 1.0 - self.spore_level * 0.5)
            return

        self._next_cd -= dt
        if self._next_cd <= 0.0:
            self._trigger(ship)

    def _trigger(self, ship):
        self._invert_active    = True
        self._invert_t         = S.SPORE_DURATION
        ship.controls_inverted = True
        bus.emit(EVT_SPORE_INVERTED, active=True)
        # More damaged → more frequent
        interval = random.uniform(S.SPORE_INTERVAL_MIN, S.SPORE_INTERVAL_MAX)
        self._next_cd = interval * max(0.4, 1.0 - self.spore_level * 0.6)

    # ------------------------------------------------------------------
    @property
    def inversion_active(self) -> bool:
        return self._invert_active

    @property
    def invert_pct(self) -> float:
        return self._invert_t / S.SPORE_DURATION if self._invert_active else 0.0

    def _on_damage(self):
        self.spore_level = min(1.0, self.spore_level + 0.25)
        bus.emit(EVT_CARGO_DAMAGED, cargo=self, severity=self.spore_level)

    def terminal_climax(self) -> str:
        # Ch.2 — exploit a TK-9 droid still seeing the universe sideways
        return "synthetic_droid"
