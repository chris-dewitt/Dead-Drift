from __future__ import annotations
import random
from cargo.cargo_base import BaseCargo
from core.event_bus import bus, EVT_CARGO_DAMAGED


class SchrodingerVIP(BaseCargo):
    """
    Ch.4: Sealed lead box. Contents simultaneously alive and dead.
    Damage effect: pure RNG — randomizes ship inventory every 30 seconds.
    Terminal climax: prove the ship doesn't exist → debt deleted.
    """

    SCRAMBLE_INTERVAL = 30.0

    def __init__(self):
        super().__init__("THE SCHRÖDINGER VIP")
        self._scramble_timer = self.SCRAMBLE_INTERVAL
        self._observed       = False    # observing collapses the wave function

    def _on_damage(self):
        self._scramble_timer = max(5.0, self._scramble_timer - 10.0)
        bus.emit(EVT_CARGO_DAMAGED, cargo=self, severity=1.0)

    def update(self, dt: float, ship):
        if not self.is_damaged:
            return
        self._scramble_timer -= dt
        if self._scramble_timer <= 0:
            self._scramble_timer = self.SCRAMBLE_INTERVAL
            self._scramble_loadout(ship)

    def _scramble_loadout(self, ship):
        from ship.modules.thruster import Thruster
        from ship.modules.life_support import LifeSupport
        tiers = ["salvage", "standard", "military"]
        new_thruster = Thruster(tier=random.choice(tiers))
        ship.chain.install(new_thruster, 1)

    def observe(self):
        """Opening the box collapses the superposition."""
        self._observed = True
        return random.choice(["ALIVE", "DEAD"])

    def terminal_climax(self) -> str:
        return "union_dispatcher"
