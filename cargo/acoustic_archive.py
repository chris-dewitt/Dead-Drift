from __future__ import annotations
from cargo.cargo_base import BaseCargo
from core.event_bus import bus, EVT_CARGO_DAMAGED


class AcousticArchive(BaseCargo):
    """
    Ch.1: Last uncompressed dark blues recordings.
    Barge proximity degrades HUD with static noise (sorrow_level drives the effect).
    run_manager pushes nearest-barge distance each frame via set_nearest_barge().
    """

    def __init__(self):
        super().__init__("CONTRABAND ACOUSTIC ARCHIVE")
        self.sorrow_level = 0.0   # 0.0–1.0 — drives HUD static + desaturation
        self._barge_dist  = 9999.0

    def set_nearest_barge(self, distance: float) -> None:
        """Called by run_manager each frame with the closest barge distance."""
        self._barge_dist = float(distance)

    def update(self, dt: float, ship) -> None:
        target = max(0.0, 1.0 - self._barge_dist / 360.0)
        self.sorrow_level += (target - self.sorrow_level) * min(1.0, dt * 1.4)
        self.sorrow_level  = max(0.0, min(1.0, self.sorrow_level))
        # Decay barge_dist so a barge that flew out of range stops driving sorrow
        self._barge_dist = min(9999.0, self._barge_dist + dt * 220.0)

    def _on_damage(self) -> None:
        self.sorrow_level = min(1.0, self.sorrow_level + 0.3)
        bus.emit(EVT_CARGO_DAMAGED, cargo=self, severity=self.sorrow_level)

    def terminal_climax(self) -> str:
        # Ch.1 — therapy session with Gary, the repo man who used to play sax
        return "gary"
