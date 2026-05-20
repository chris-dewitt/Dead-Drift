from __future__ import annotations
from cargo.cargo_base import BaseCargo
from core.event_bus import bus, EVT_CARGO_DAMAGED, EVT_BARGE_NEARBY


class AcousticArchive(BaseCargo):
    """
    Ch.1: Last uncompressed dark blues recordings.
    Barge proximity degrades HUD with static noise (sorrow_level drives the effect).
    """

    def __init__(self):
        super().__init__("CONTRABAND ACOUSTIC ARCHIVE")
        self.sorrow_level = 0.0   # 0.0–1.0 — drives HUD static + desaturation
        self._barge_dist  = 9999.0
        bus.subscribe(EVT_BARGE_NEARBY, self._on_barge_nearby)

    def update(self, dt: float, ship) -> None:
        # Distance estimate decays toward infinity when no proximity event fires
        self._barge_dist = min(9999.0, self._barge_dist + dt * 160.0)
        target = max(0.0, 1.0 - self._barge_dist / 320.0)
        self.sorrow_level += (target - self.sorrow_level) * min(1.0, dt * 0.9)
        self.sorrow_level  = max(0.0, min(1.0, self.sorrow_level))

    def _on_barge_nearby(self, distance=9999.0, **_) -> None:
        self._barge_dist = float(distance)

    def _on_damage(self) -> None:
        self.sorrow_level = min(1.0, self.sorrow_level + 0.3)
        bus.emit(EVT_CARGO_DAMAGED, cargo=self, severity=self.sorrow_level)

    def terminal_climax(self) -> str:
        # Ch.1 — therapy session with Gary, the repo man who used to play sax
        return "gary"
