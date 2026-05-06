from ship.modules.base_module import BaseModule


class LifeSupport(BaseModule):
    """
    Dampens heat and radiation bleed from hotwired thrusters.
    Disabling it frees up significant power — but running a military
    thruster without it triggers system meltdown within ~20 seconds.
    """

    def __init__(self):
        super().__init__(
            name       = "LIFE SUPPORT DAMPENERS",
            power_cost = 3.5,
            heat_gen   = 0.0,
            tags       = ["dampener", "life_support"],
        )
        self.heat_absorption = 18.0   # heat units/s absorbed from thruster
        self.rad_shield      = 0.7    # 70% radiation reduction

    def update(self, dt: float):
        pass   # absorption applied by SignalChain when routing power
