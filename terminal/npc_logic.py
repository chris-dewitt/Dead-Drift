from __future__ import annotations
from terminal.npcs.gary import Gary
from terminal.npcs.synthetic_droid import SyntheticDroid
from terminal.npcs.union_dispatcher import UnionDispatcher
from terminal.npcs.kress import Kress
from terminal.npcs.insurance_adjuster import InsuranceAdjuster
from terminal.npcs.sandra import Sandra
from terminal.npcs.pirate import Pirate
from terminal.npcs.underground_dj import UndergroundDJ
from terminal.npcs.toll_authority import TollAuthority
from terminal.npcs.nervous_fence import NervousFence
from terminal.npcs.cargo_inspector import CargoInspector
from terminal.npcs.dray import Dray
from terminal.npcs.nova_soma import NovaSomaCollections
from terminal.npcs.mira_voss import MiraVoss
from terminal.npcs.idealist_rep import IdealistRep
from terminal.npcs.corrupt_rep import CorruptRep
from terminal.npcs.lost_frequency import LostFrequency
from terminal.npcs.chen import Chen
from terminal.npcs.bowen import Bowen
from terminal.npcs.base_npc import BaseNPC


def make_npc(npc_type: str, **kwargs) -> BaseNPC:
    """Factory: instantiate an NPC by type string."""
    registry = {
        "gary":                    Gary,
        "synthetic_droid":         SyntheticDroid,
        "union_dispatcher":        UnionDispatcher,
        "kress":                   Kress,
        "insurance_adjuster":      InsuranceAdjuster,
        "sandra":                  Sandra,
        "pirate":                  Pirate,
        "underground_dj":          UndergroundDJ,
        "toll_authority":          TollAuthority,
        "nervous_fence":           NervousFence,
        "cargo_inspector":         CargoInspector,
        "dray":                    Dray,
        "nova_soma_collections":   NovaSomaCollections,
        "mira_voss":               MiraVoss,
        "idealist_rep":            IdealistRep,
        "corrupt_rep":             CorruptRep,
        "lost_frequency":          LostFrequency,
        "chen":                    Chen,
        "bowen":                   Bowen,
    }
    cls = registry.get(npc_type)
    if cls is None:
        raise ValueError(f"Unknown NPC type: {npc_type!r}")
    return cls(**kwargs)
