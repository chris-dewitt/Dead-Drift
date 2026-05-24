"""
Run mutators — Epic 12.1.

Each run starts with one mutator (or none for the first run of a chapter,
or if the player opts out). The mutator is shown as a banner in the loadout
draft and its effects are queried by gameplay systems via `get_active()`.

Implemented effects:
  - DEBT_SURGE      : debt interest x3, credit pickups x2
  - FRAGILE_FRAME   : hull max -30, slingshot overdrive duration x2
  - VETERAN_CLONE   : start +50k debt, start full hull + torch (run-start only)
  - OPEN_SEASON     : barge kills pay x3
  - NO_SHOP         : shops don't spawn, credits banked as end-of-run bonus

Banner-only (flag present, full effect plumbing deferred):
  - COLD_SECTOR, SYSTEM_GLITCH, SLINGSHOT_ONLY, QUIET_SECTOR, NOVICE_PASS
"""
from __future__ import annotations
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Mutator:
    key:      str
    name:     str
    blurb:    str
    full:     bool = True   # True = fully wired effects; False = banner-only flag


MUTATORS: dict[str, Mutator] = {
    "debt_surge": Mutator(
        "debt_surge", "DEBT SURGE",
        "Interest rate x3 — but credit pickups x2.", full=True),
    "cold_sector": Mutator(
        "cold_sector", "COLD SECTOR",
        "Every sector is Frozen Trail or Mine Strip.", full=False),
    "open_season": Mutator(
        "open_season", "OPEN SEASON",
        "Barges aggressive. Barge kills pay x3.", full=True),
    "system_glitch": Mutator(
        "system_glitch", "SYSTEM GLITCH",
        "Gun malfunctions x3 — but shots that connect pay +50 cr.", full=False),
    "slingshot_only": Mutator(
        "slingshot_only", "SLINGSHOT ONLY",
        "Jump timer reduces only from slingshots — not sector time.", full=False),
    "no_shop": Mutator(
        "no_shop", "NO SHOP",
        "Shops don't appear. Credits banked as end-of-run bonus.", full=True),
    "fragile_frame": Mutator(
        "fragile_frame", "FRAGILE FRAME",
        "Hull max -30. Slingshot overdrive duration x2.", full=True),
    "veteran_clone": Mutator(
        "veteran_clone", "VETERAN CLONE",
        "Start +50k debt. Start with full hull and military torch.", full=True),
    "quiet_sector": Mutator(
        "quiet_sector", "QUIET SECTOR",
        "Barges don't spawn sectors 1-3; sector 4-5 spawn 2.", full=False),
    "novice_pass": Mutator(
        "novice_pass", "NOVICE PASS",
        "First death of run free (no debt fee). CASUAL only.", full=False),
}


class MutatorRegistry:
    """
    Per-run mutator state. Owned by RunManager.

    The first run of each chapter has no mutator (forces a clean baseline).
    On subsequent runs, `roll_for_run()` picks one randomly. Player can opt
    out by setting `active = None` before the run starts.
    """
    def __init__(self):
        self._active: Mutator | None = None
        self._rng = random.Random()

    @property
    def active(self) -> Mutator | None:
        return self._active

    @active.setter
    def active(self, m: Mutator | None) -> None:
        self._active = m

    def clear(self) -> None:
        self._active = None

    def roll_for_run(self, first_run_of_chapter: bool = False) -> Mutator | None:
        if first_run_of_chapter:
            self._active = None
            return None
        # Roll any mutator — equal weight.
        self._active = self._rng.choice(list(MUTATORS.values()))
        return self._active

    # ── Effect query helpers ──────────────────────────────────────────────
    def is_active(self, key: str) -> bool:
        return self._active is not None and self._active.key == key

    def debt_interest_multiplier(self) -> float:
        return 3.0 if self.is_active("debt_surge") else 1.0

    def credit_pickup_multiplier(self) -> float:
        return 2.0 if self.is_active("debt_surge") else 1.0

    def barge_kill_multiplier(self) -> float:
        return 3.0 if self.is_active("open_season") else 1.0

    def hull_max_delta(self) -> int:
        return -30 if self.is_active("fragile_frame") else 0

    def slingshot_overdrive_multiplier(self) -> float:
        return 2.0 if self.is_active("fragile_frame") else 1.0

    def starting_debt_bonus(self) -> int:
        return 50000 if self.is_active("veteran_clone") else 0

    def shops_enabled(self) -> bool:
        return not self.is_active("no_shop")
