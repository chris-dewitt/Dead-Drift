from __future__ import annotations
import random
from dataclasses import dataclass, field
from physics.gravity import GravityWell, ThreeBodySystem
from config import settings as S


# ---------------------------------------------------------------------------
# Sector themes — 8 distinct flavour presets (Epic 3.3)
# ---------------------------------------------------------------------------
THEME_COMPLIANCE        = "COMPLIANCE ZONE"
THEME_WRECKAGE_BELT     = "WRECKAGE BELT"
THEME_INDUSTRIAL_GRAVEYARD = "INDUSTRIAL GRAVEYARD"
THEME_JUNK_BELT         = "JUNK-BELT"
THEME_MINE_STRIP        = "MINE STRIP"
THEME_FROZEN_TRAIL      = "FROZEN TRAIL"
THEME_FLARE_CORRIDOR    = "FLARE CORRIDOR"
THEME_TOLL_AUTHORITY    = "TOLL AUTHORITY"

_ALL_THEMES = [
    THEME_COMPLIANCE, THEME_WRECKAGE_BELT, THEME_INDUSTRIAL_GRAVEYARD,
    THEME_JUNK_BELT, THEME_MINE_STRIP, THEME_FROZEN_TRAIL,
    THEME_FLARE_CORRIDOR, THEME_TOLL_AUTHORITY,
]

# Per-chapter curated theme sets (5 sectors per run — Epic 3.4)
_CHAPTER_THEMES: dict[int, list[str]] = {
    1: [THEME_COMPLIANCE, THEME_WRECKAGE_BELT, THEME_JUNK_BELT,
        THEME_FLARE_CORRIDOR, THEME_INDUSTRIAL_GRAVEYARD],
    2: [THEME_COMPLIANCE, THEME_INDUSTRIAL_GRAVEYARD, THEME_WRECKAGE_BELT,
        THEME_MINE_STRIP, THEME_FROZEN_TRAIL],
    3: [THEME_COMPLIANCE, THEME_JUNK_BELT, THEME_TOLL_AUTHORITY,
        THEME_FLARE_CORRIDOR, THEME_FROZEN_TRAIL],
    4: [THEME_COMPLIANCE, THEME_FROZEN_TRAIL, THEME_INDUSTRIAL_GRAVEYARD,
        THEME_WRECKAGE_BELT, THEME_MINE_STRIP],
}

# Theme → one-line description shown on intro card
THEME_DESCRIPTIONS: dict[str, str] = {
    THEME_COMPLIANCE:           "standard flight, minimal hazards",
    THEME_WRECKAGE_BELT:        "derelicts drift here — fly with respect",
    THEME_INDUSTRIAL_GRAVEYARD: "dead stations, no fuel here — picked over",
    THEME_JUNK_BELT:            "trash sector — salvage if you're brave",
    THEME_MINE_STRIP:           "proximity mines — shoot them or dodge them",
    THEME_FROZEN_TRAIL:         "comet ice — thrusters slip, things slide",
    THEME_FLARE_CORRIDOR:       "solar weather — shields down, gun fizzles",
    THEME_TOLL_AUTHORITY:       "checkpoint gate — pay up or run",
}


@dataclass
class SectorLayout:
    index:        int
    gravity:      ThreeBodySystem
    hazards:      list[str]       # e.g. ["solar_flare", "asteroid_field"]
    enemy_budget: int             # how many barge spawns to allow
    is_ambush:    bool            # stealth repo barge present from start
    theme:        str = THEME_COMPLIANCE  # sector theme (Epic 3.3)
    name:         str = ""        # corporate-speak sector designation
    formerly:     str = ""        # what locals used to call it, if anything
    # Epic 12.3 — per-sector dominant hazard + opportunity rolls (display only)
    hazard_roll:      str = ""
    opportunity_roll: str = ""


# Epic 12.3 — hazard/opportunity rolls displayed in sector intro card
SECTOR_HAZARD_ROLLS: dict[str, str] = {
    "gravity_tide":      "GRAVITY TIDE — wells shift direction every 30s",
    "sensor_jamming":    "SENSOR JAMMING — barge radar disabled this sector",
    "scan_infestation":  "SCAN PING INFESTATION — Union scanners fire every 12s",
    "asteroid_shower":   "ASTEROID SHOWER — debris count doubled for 45s",
    "comms_blackout":    "COMMUNICATION BLACKOUT — terminal patience -30%",
}

SECTOR_OPPORTUNITY_ROLLS: dict[str, str] = {
    "wells_favorable":   "GRAVITY WELLS FAVORABLE — slingshot within first 20s",
    "salvage_cache":     "SALVAGE CACHE — extra canister cluster near sector centre",
    "friendly_signal":   "FRIENDLY SIGNAL — an NPC ship will hail",
    "abandoned_station": "ABANDONED STATION — loot cache (+1200 cr if unlocked)",
    "weak_barge":        "WEAK BARGE — this sector's barge spawns at 50% HP",
}


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


def generate_sector(index: int, difficulty: float = 1.0,
                    rng: random.Random | None = None,
                    chapter: int = 1) -> SectorLayout:
    """
    Procedurally generate a sector layout.
    difficulty scales 1.0 (sector 1) → 2.0 (sector 10).
    Pass a seeded rng for deterministic/replay runs.
    chapter selects the curated theme pool.
    """
    if rng is None:
        rng = random.Random()

    gravity = _generate_gravity(index, difficulty, rng)
    theme   = _pick_theme(index, chapter, rng)
    hazards = _hazards_for_theme(theme, index, difficulty, rng)
    budget  = max(1, int(1 + difficulty * 1.5))
    ambush  = index >= 5 and rng.random() < 0.25 * difficulty

    name     = rng.choice(_SECTOR_NAMES)
    # ~45% chance the sector has a "formerly" name people remember
    formerly = rng.choice(_FORMERLY_NAMES) if rng.random() < 0.45 else ""

    # Epic 12.3 — each sector rolls one dominant hazard and one dominant
    # opportunity. Sector 0 is always a clean baseline.
    if index == 0:
        hazard_roll = ""
        opp_roll    = ""
    else:
        hazard_roll = rng.choice(list(SECTOR_HAZARD_ROLLS.keys()))
        opp_roll    = rng.choice(list(SECTOR_OPPORTUNITY_ROLLS.keys()))

    return SectorLayout(
        index            = index,
        gravity          = gravity,
        hazards          = hazards,
        enemy_budget     = budget,
        is_ambush        = ambush,
        theme            = theme,
        name             = name,
        formerly         = formerly,
        hazard_roll      = hazard_roll,
        opportunity_roll = opp_roll,
    )


def _pick_theme(index: int, chapter: int, rng: random.Random) -> str:
    pool = _CHAPTER_THEMES.get(chapter, _ALL_THEMES)
    # Sector 0 is always COMPLIANCE ZONE (orientation)
    if index == 0:
        return THEME_COMPLIANCE
    candidates = [t for t in pool if t != THEME_COMPLIANCE]
    if not candidates:
        return rng.choice(pool)
    # Use index to pick deterministically within the chapter pool
    return pool[min(index, len(pool) - 1)]


def _hazards_for_theme(theme: str, index: int, difficulty: float,
                       rng: random.Random) -> list[str]:
    """Map theme → canonical hazards. Cap at 2 per sector."""
    mapping: dict[str, list[str]] = {
        THEME_COMPLIANCE:           [],
        THEME_WRECKAGE_BELT:        [],   # wrecks handled by obstacle spawner
        THEME_INDUSTRIAL_GRAVEYARD: [],   # dead_station handled by obstacle spawner
        THEME_JUNK_BELT:            [],   # trash_field handled by obstacle spawner
        THEME_MINE_STRIP:           [],   # mine_field handled by obstacle spawner
        THEME_FROZEN_TRAIL:         [],   # ice_field + comet handled by obstacle spawner
        THEME_FLARE_CORRIDOR:       ["solar_flare"],
        THEME_TOLL_AUTHORITY:       ["toll_checkpoint"],
    }
    base = mapping.get(theme, [])
    # At high difficulty add one extra from the pool
    if difficulty > 1.5 and len(base) < 2 and index >= 2:
        extras = [h for h in _HAZARD_POOL if h not in base and h != "toll_checkpoint"]
        if extras:
            base = base + [rng.choice(extras)]
    return base[:2]


_SHIP_SPAWN = None   # lazy-initialised on first call


def _generate_gravity(index: int, difficulty: float,
                      rng: random.Random) -> ThreeBodySystem:
    """Generate gravity wells with safe spawn positions."""
    global _SHIP_SPAWN
    if _SHIP_SPAWN is None:
        from config import settings as _S
        _SHIP_SPAWN = (_S.SCREEN_W / 2, _S.FLIGHT_H / 2)

    system    = ThreeBodySystem()
    num_wells = 1 + (index // 3)   # more wells deeper in the run
    placed: list[GravityWell] = []

    margin   = 100
    x_lo, x_hi = margin, S.SCREEN_W - margin
    y_lo, y_hi = margin, S.FLIGHT_H - margin   # use FLIGHT_H, not SCREEN_H

    for _ in range(min(num_wells, 3)):
        # Reject-sample: far enough from other wells and from ship spawn
        for _attempt in range(40):
            x    = rng.uniform(x_lo, x_hi)
            y    = rng.uniform(y_lo, y_hi)
            dx   = x - _SHIP_SPAWN[0]
            dy   = y - _SHIP_SPAWN[1]
            if dx * dx + dy * dy < 220 * 220:
                continue
            too_close = False
            for other in placed:
                odx = x - other.pos.x
                ody = y - other.pos.y
                if odx * odx + ody * ody < 180 * 180:
                    too_close = True
                    break
            if not too_close:
                break

        mass = rng.uniform(800, 2000) * difficulty
        rad  = rng.randint(30, 80)
        well = GravityWell(x, y, mass, rad)
        placed.append(well)
        system.add(well)

    return system


