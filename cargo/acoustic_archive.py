from cargo.cargo_base import BaseCargo
from core.event_bus import bus, EVT_CARGO_DAMAGED


class AcousticArchive(BaseCargo):
    """
    Ch.1: Leaky server rack — last uncompressed dark blues recordings.
    Damage effect: UI mutes to grayscale, thrusters sluggish, Bax quotes poetry.
    Terminal climax: therapy session with Gary.
    """

    def __init__(self):
        super().__init__("CONTRABAND ACOUSTIC ARCHIVE")
        self.sorrow_level = 0.0   # 0.0–1.0; drives HUD desaturation

    def _on_damage(self):
        self.sorrow_level = min(1.0, self.sorrow_level + 0.3)
        bus.emit(EVT_CARGO_DAMAGED, cargo=self, severity=self.sorrow_level)

    def terminal_climax(self) -> str:
        return "gary"   # Gary needs therapy
