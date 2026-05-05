from __future__ import annotations
from ship.modules.base_module import BaseModule
from core.event_bus import bus, EVT_MODULE_UNBOLTED


class SignalChain:
    """
    The Hotwired Signal Chain: a linear power routing graph.

    Modules are chained in order.  Power flows from index 0 onward.
    If a module's power_cost exceeds available power, it and everything
    downstream deactivate.  This creates the core tension: you can't
    run everything at once.

    Total power budget is determined by whatever reactor/generator
    modules are installed (power_output).
    """

    MAX_SLOTS = 6

    def __init__(self):
        self.slots: list[BaseModule | None] = [None] * self.MAX_SLOTS

    # ------------------------------------------------------------------
    def install(self, module: BaseModule, slot: int) -> bool:
        if slot < 0 or slot >= self.MAX_SLOTS:
            return False
        self.slots[slot] = module
        self._rebalance()
        return True

    def remove(self, slot: int) -> BaseModule | None:
        module = self.slots[slot]
        self.slots[slot] = None
        self._rebalance()
        return module

    # ------------------------------------------------------------------
    def _rebalance(self):
        """Route power left-to-right, activating what the budget allows."""
        budget = self._total_power_output()
        for module in self.slots:
            if module is None:
                continue
            if module.power_cost <= budget and module.is_functional():
                module.on_activate()
                budget -= module.power_cost
            else:
                module.on_deactivate()

    def _total_power_output(self) -> float:
        return sum(
            m.power_output for m in self.slots
            if m is not None and m.power_output > 0 and m.is_functional()
        ) or 10.0   # baseline power even with no generator installed

    # ------------------------------------------------------------------
    def unbolt_random(self) -> BaseModule | None:
        """Repo Man plasma torch hits a random active module."""
        import random
        active = [m for m in self.slots if m is not None and m.active]
        if not active:
            return None
        target = random.choice(active)
        target.on_unbolt()
        bus.emit(EVT_MODULE_UNBOLTED, module=target)
        self._rebalance()
        return target

    def update(self, dt: float):
        for module in self.slots:
            if module is not None:
                module.update(dt)

    # ------------------------------------------------------------------
    def get_active(self, tag: str) -> list[BaseModule]:
        return [m for m in self.slots if m and m.active and tag in m.tags]

    def total_heat(self) -> float:
        return sum(m.heat_gen for m in self.slots if m and m.active)

    def __repr__(self) -> str:
        chain = " -> ".join(str(m) if m else "[EMPTY]" for m in self.slots)
        return f"SignalChain[{chain}]"
