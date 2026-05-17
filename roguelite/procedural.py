from __future__ import annotations
import random
from dataclasses import dataclass, field
from physics.gravity import GravityWell, ThreeBodySystem
from config import settings as S


@dataclass
class SectorLayout:
    index:        int
    gravity:      ThreeBodySystem
    hazards:      list[str]       # e.g. ["solar_flare", "asteroid_field"]
    enemy_budget: int             # how many barge spawns to allow
    is_ambush:    bool            # stealth repo barge present from start
    name:         str = ""        # corporate-speak sector designation
    formerly:     str = ""        # what locals used to call it, if anything


_HAZARD_POOL = [
    "asteroid_field",
    "solar_flare",
    "collapsing_gravity_well",
    "debris_cloud",
    "toll_checkpoint",
]


# Corporate-speak sector designations — Nova Soma management consultant brain
_SECTOR_NAMES = [
    "OPTIMISED COMPLIANCE ZONE",
    "LEGACY EXTRACTION CORRIDOR",
    "MERIDIAN DEBT RECLAMATION AREA",
    "POST-PROFITABILITY WASTE FIELD",
    "HERITAGE ASSET RECOVERY GRID",
    "TIER-2 SYNERGY VOID",
    "RATIONALISED PATROL SECTOR",
    "MONETISED DARK BAND",
    "QUARTERLY OBJECTIVES OVERLAP REGION",
    "DOWNSTREAM VALUE EXTRACTION CORRIDOR",
    "ACTIONABLE INTERCEPT BUFFER",
    "NON-CORE POPULATION DENSITY GRID",
]

# What people used to call them before Nova Soma "rationalised the nomenclature"
_FORMERLY_NAMES = [
    "HOME",
    "THE QUIET BELT",
    "ST. ANN'S PASSAGE",
    "THE OLD ROUTE",
    "GRANDFATHER REACH",
    "FREE HARBOUR",
    "THE WIDOW'S CROSSING",
    "MILLER STATION",
    "THE COMMONS",
]


def generate_sector(index: int, difficulty: float = 1.0) -> SectorLayout:
    """
    Procedurally generate a sector layout.
    difficulty scales 1.0 (sector 1) → 2.0 (sector 10).
    """
    rng = random.Random()   # seeded per run externally if determinism needed

    gravity = _generate_gravity(index, difficulty)
    hazards = _pick_hazards(index, difficulty, rng)
    budget  = max(1, int(1 + difficulty * 1.5))
    ambush  = index >= 5 and rng.random() < 0.25 * difficulty

    name     = rng.choice(_SECTOR_NAMES)
    # ~45% chance the sector has a "formerly" name people remember
    formerly = rng.choice(_FORMERLY_NAMES) if rng.random() < 0.45 else ""

    return SectorLayout(
        index        = index,
        gravity      = gravity,
        hazards      = hazards,
        enemy_budget = budget,
        is_ambush    = ambush,
        name         = name,
        formerly     = formerly,
    )


def _generate_gravity(index: int, difficulty: float) -> ThreeBodySystem:
    system = ThreeBodySystem()
    num_wells = 1 + (index // 3)   # more wells deeper in the run

    for _ in range(min(num_wells, 3)):
        x     = random.randint(100, S.SCREEN_W - 100)
        y     = random.randint(100, S.SCREEN_H - 100)
        mass  = random.uniform(800, 2000) * difficulty
        rad   = random.randint(30, 80)
        system.add(GravityWell(x, y, mass, rad))

    return system


def _pick_hazards(index: int, difficulty: float, rng: random.Random) -> list[str]:
    count   = 1 + int(difficulty)
    pool    = _HAZARD_POOL[:]
    if index < 3:
        pool = [h for h in pool if h != "collapsing_gravity_well"]
    return rng.sample(pool, min(count, len(pool)))
