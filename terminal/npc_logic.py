from __future__ import annotations
from terminal.npcs.gary import Gary
from terminal.npcs.synthetic_droid import SyntheticDroid
from terminal.npcs.union_dispatcher import UnionDispatcher
from terminal.npcs.kress import Kress
from terminal.npcs.insurance_adjuster import InsuranceAdjuster
from terminal.npcs.sandra import Sandra
from terminal.npcs.pirate import Pirate
from terminal.npcs.underground_dj import UndergroundDJ
from terminal.npcs.base_npc import BaseNPC


def make_npc(npc_type: str, **kwargs) -> BaseNPC:
    """Factory: instantiate an NPC by type string."""
    registry = {
        "gary":               Gary,
        "synthetic_droid":    SyntheticDroid,
        "union_dispatcher":   UnionDispatcher,
        "kress":              Kress,
        "insurance_adjuster": InsuranceAdjuster,
        "sandra":             Sandra,
        "pirate":             Pirate,
        "underground_dj":     UndergroundDJ,
    }
    cls = registry.get(npc_type)
    if cls is None:
        raise ValueError(f"Unknown NPC type: {npc_type!r}")
    return cls(**kwargs)
