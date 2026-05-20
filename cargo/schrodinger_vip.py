from __future__ import annotations
import random
from cargo.cargo_base import BaseCargo
from core.event_bus import bus, EVT_BAX_SPEAK

_ALIVE_ODDS = [True, True, False]   # 2:1 alive bias

_BAX_UNOBSERVED = [
    "Don't open the box. I mean it. Actually, maybe open the box.",
    "Passenger status: undefined. Which I think means fine. Maybe.",
    "Quantum passenger update: still Schrödinger's problem, not mine.",
    "They may or may not be conscious. Legally we say 'probably'.",
    "The passenger's alive status is technically a matter of philosophy at this speed.",
]
_BAX_ALIVE = [
    "Passenger status confirmed: ALIVE. They look annoyed about it. Standard.",
    "VIP status: conscious, irritable, three complaints filed. Alive.",
    "The box has been metaphorically opened. They're fine. Very annoyed, but fine.",
]
_BAX_DEAD = [
    "...passenger status is... look, it's complicated. Fly fast.",
    "Cargo status: quantum collapse resolved. Unfavourably. Increase speed.",
    "The box has been opened, theoretically. Don't think about it.",
]


class SchrodingerVIP(BaseCargo):
    """Ch.4: Passenger in quantum superposition — observation collapses state."""

    def __init__(self):
        super().__init__("THE SCHRÖDINGER VIP")
        self.alive_state: bool | None = None
        self._high_speed_t = 0.0
        self._comment_cd   = random.uniform(22.0, 38.0)

    def update(self, dt: float, ship) -> None:
        speed = ship.body.speed()

        if speed > 200.0:
            self._high_speed_t += dt
            if self._high_speed_t > 4.0 and self.alive_state is None:
                self.alive_state   = random.choice(_ALIVE_ODDS)
                self._high_speed_t = 0.0
        else:
            self._high_speed_t = max(0.0, self._high_speed_t - dt * 0.4)

        self._comment_cd -= dt
        if self._comment_cd <= 0.0:
            self._comment_cd = random.uniform(28.0, 50.0)
            if self.alive_state is None:
                bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_UNOBSERVED))
            elif self.alive_state:
                bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_ALIVE))
            else:
                bus.emit(EVT_BAX_SPEAK, line=random.choice(_BAX_DEAD))

    def _on_damage(self) -> None:
        if self.alive_state is None and random.random() < 0.45:
            self.alive_state = random.choice(_ALIVE_ODDS)

    def observe(self) -> str:
        if self.alive_state is None:
            self.alive_state = random.choice(_ALIVE_ODDS)
        return "ALIVE" if self.alive_state else "DECEASED"

    def terminal_climax(self) -> str:
        # Ch.4 — insurance adjuster Morwenna gets to decide if the passenger ever existed
        return "insurance_adjuster"
