from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class BaseModule:
    """
    A single node in the Hotwired Signal Chain.

    Modules consume power_cost and optionally produce power_output
    (e.g. a reactor module).  They can be active or inactive depending
    on whether the signal chain has routed power to them.
    """
    name:         str
    power_cost:   float = 0.0
    power_output: float = 0.0
    heat_gen:     float = 0.0    # heat units/s while active
    integrity:    float = 100.0  # drops when repo men unbolt it
    active:       bool  = False
    tags:         list[str] = field(default_factory=list)

    def on_activate(self):
        self.active = True

    def on_deactivate(self):
        self.active = False

    def on_unbolt(self, severity: float = 25.0):
        """Called when a repo man's plasma torch hits this module."""
        self.integrity = max(0.0, self.integrity - severity)
        if self.integrity <= 0.0:
            self.on_deactivate()

    def update(self, dt: float):
        pass   # override in subclasses

    def is_functional(self) -> bool:
        return self.integrity > 0.0

    def __repr__(self) -> str:
        status = "ON" if self.active else "OFF"
        return f"[{self.name} | {status} | {self.integrity:.0f}% | cost={self.power_cost}W]"
