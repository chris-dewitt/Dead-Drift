from __future__ import annotations
from ship.modules.base_module import BaseModule
from config import settings as S


class Thruster(BaseModule):
    """
    Main propulsion module.  Force output scales with integrity.
    Generates significant heat — requires life support or risks meltdown.
    """

    def __init__(self, name: str = "PLASMA THRUSTER MK-I", tier: str = "salvage"):
        tiers = {
            "salvage":  {"power_cost": 2.0, "heat_gen": 8.0,  "force": S.THRUSTER_FORCE * 0.7},
            "standard": {"power_cost": 3.0, "heat_gen": 12.0, "force": S.THRUSTER_FORCE},
            "military": {"power_cost": 6.0, "heat_gen": 28.0, "force": S.THRUSTER_FORCE * 1.8},
        }
        cfg = tiers.get(tier, tiers["salvage"])
        super().__init__(
            name         = name,
            power_cost   = cfg["power_cost"],
            heat_gen     = cfg["heat_gen"],
            tags         = ["propulsion", tier],
        )
        self.base_force = cfg["force"]
        self.heat       = 0.0
        self.overheated = False

    @property
    def force(self) -> float:
        if self.overheated:
            return 0.0
        return self.base_force * (self.integrity / 100.0)

    def update(self, dt: float):
        if not self.active or not self.is_functional():
            self.heat = max(0.0, self.heat - 15.0 * dt)
            if self.heat <= 0.0:
                self.overheated = False
            return

        self.heat += self.heat_gen * dt
        if self.heat >= 100.0:
            self.overheated = True

    def inject_fuel_mix(self, buff_multiplier: float, duration: float):
        """Bax's mixologist injects a volatile concoction."""
        self._buff_mult     = buff_multiplier
        self._buff_remaining = duration

    def __repr__(self) -> str:
        heat_bar = f"heat={self.heat:.0f}°"
        return f"[THRUSTER | force={self.force:.0f}N | {heat_bar} | {'OVERHEATED' if self.overheated else 'OK'}]"
