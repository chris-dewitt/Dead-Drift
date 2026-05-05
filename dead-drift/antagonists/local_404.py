from __future__ import annotations
from roguelite.meta_progression import MetaProgression


class Local404:
    """
    The Repo Union's faction system.
    Reputation with individual agents persists across clones.
    High positive rep: Gary might "miss" a shot.
    High negative rep: barges spawn faster and tether harder.
    """

    AGENTS = ["gary", "tk9", "dispatcher", "blevins"]

    def __init__(self, meta: MetaProgression):
        self.meta = meta

    def get_rep(self, agent_id: str) -> int:
        return self.meta.get_reputation(agent_id)

    def adjust(self, agent_id: str, delta: int):
        self.meta.adjust_reputation(agent_id, delta)

    def gary_miss_chance(self) -> float:
        """Returns probability that Gary deliberately misses a harpoon shot."""
        rep = self.get_rep("gary")
        if rep >= 7:   return 0.40
        if rep >= 4:   return 0.15
        if rep >= 1:   return 0.05
        return 0.0

    def spawn_rate_modifier(self) -> float:
        """Negative rep increases barge spawn rate."""
        rep = self.get_rep("dispatcher")
        if rep <= -7:  return 2.0
        if rep <= -4:  return 1.5
        return 1.0
