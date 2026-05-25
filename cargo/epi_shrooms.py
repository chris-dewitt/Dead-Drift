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
        # Aliveness A.2: the FIRST inversion lands inside the first 6–9s so the
        # player reliably experiences it before the 20s jump window opens.
        # Without this, ~50% of runs lost the first trigger to the jump terminal
        # and Chris's playtest (May 2026) couldn't see the mechanic fire at all.
        self._next_cd        = random.uniform(
            S.SPORE_FIRST_TRIGGER_MIN, S.SPORE_FIRST_TRIGGER_MAX)
        # Telegraph beat — short visual burst on first-trigger transition.
        self._just_triggered_t = 0.0
        self._just_cleared_t   = 0.0

    # ------------------------------------------------------------------
    def update(self, dt: float, ship) -> None:
        # Spore pressure builds gradually — drives pre-warning vignette in renderer
        self.spore_level = min(1.0, self.spore_level + dt * 0.018)
        # Decay the telegraph beats so the renderer can show a short flash.
        self._just_triggered_t = max(0.0, self._just_triggered_t - dt)
        self._just_cleared_t   = max(0.0, self._just_cleared_t   - dt)

        if self._invert_active:
            self._invert_t -= dt
            if self._invert_t <= 0.0:
                self._invert_active    = False
                ship.controls_inverted = False
                self._just_cleared_t   = 0.8
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
        self._just_triggered_t = 0.8
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

    def force_clear_inversion(self, ship) -> None:
        """Aliveness A.2: clear any active inversion at run-end / delivery so
        a stale flag can't bleed into the next sector or run. Called when the
        cargo leaves active flight context (delivery start, ship destroyed)."""
        if self._invert_active:
            self._invert_active = False
            self._invert_t      = 0.0
            try:
                ship.controls_inverted = False
            except Exception:
                pass
            bus.emit(EVT_SPORE_INVERTED, active=False)
