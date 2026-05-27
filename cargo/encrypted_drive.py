from __future__ import annotations
from cargo.cargo_base import BaseCargo
from core.event_bus import bus, EVT_CARGO_DAMAGED


class EncryptedDrive(BaseCargo):
    """
    Ch.5–6 cargo: a USB drive carrying the Remnants' debt-wipe virus.

    Chen's payload. Inert until plugged in at Nova Soma's server room.
    Mechanically: while carried, the cargo emits a low-power signature
    that Nova Soma Compliance Vessels can track — pursuer spawn rate
    is elevated and a faint "ping" event fires on a cooldown so Bax
    can react.

    The drive itself doesn't break under fire — it's wrapped in a
    physical isolator. Damage events instead spike the trace_level,
    which makes the pursuit even more aggressive.
    """

    def __init__(self):
        super().__init__("ENCRYPTED DRIVE  //  PAYLOAD: UNKNOWN")
        self.trace_level = 0.0   # 0.0–1.0 — drives compliance vessel spawn weight
        self._ping_t     = 0.0

    def update(self, dt: float, ship) -> None:
        self._ping_t += dt
        # Slow trace decay so a clean run lets the level fall
        self.trace_level = max(0.0, self.trace_level - dt * 0.02)

    def _on_damage(self) -> None:
        # A hit doesn't destroy the drive — it spikes Nova Soma's interest
        self.trace_level = min(1.0, self.trace_level + 0.25)
        bus.emit(EVT_CARGO_DAMAGED, cargo=self, severity=self.trace_level)

    def terminal_climax(self) -> str:
        # The chapter 6 climax is Bowen — polite, terrifying.
        return "bowen"

    def state_for_terminal(self) -> str | None:
        if self.trace_level >= 0.6:
            return "high_trace"
        if self.trace_level >= 0.3:
            return "noticed"
        return "clean"
