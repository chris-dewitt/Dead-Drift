from cargo.cargo_base import BaseCargo
from core.event_bus import bus, EVT_CARGO_DAMAGED


class EpistemologicalShrooms(BaseCargo):
    """
    Ch.2: Bioluminescent psychic fungi — destroy the concept of object permanence.
    Damage effect: vector graphics melt, physics inverts, Bax hallucinates.
    Terminal climax: navigate asteroid field while Bax screams about space badgers.
    """

    def __init__(self):
        super().__init__("WEAPONIZED EPISTEMOLOGICAL SHROOMS")
        self.spore_level = 0.0
        self.physics_inverted = False

    def _on_damage(self):
        self.spore_level = min(1.0, self.spore_level + 0.25)
        if self.spore_level >= 0.75 and not self.physics_inverted:
            self.physics_inverted = True
        bus.emit(EVT_CARGO_DAMAGED, cargo=self, severity=self.spore_level)

    def terminal_climax(self) -> str:
        return "synthetic_droid"
