from __future__ import annotations
import copy
import json
from pathlib import Path

from config import settings as S
from core.event_bus import bus, EVT_DEBT_UPDATE


class MetaProgression:
    """
    Persistent cross-run state stored in data/run_history.json.

    Survives ship destruction (always saved to disk).
    Tracks: debt, clone count, chapters completed, and Bax's level.
    """

    _DEFAULTS = {
        "debt":               150000,
        "clone_count":        1,
        "chapters_completed": [],
        "bax_level":          1,
        "reputation":         {},     # npc_id -> int (-10..10)
        "bax_hums_heard":     [],     # list[int] — hum indices the player has heard
        "unlocks":            [],     # list[str] — earned unlock keys (Epic 12.2)
        "milestone_counters": {},     # str -> int (e.g. "slingshots_total")
        "difficulty":         "standard",  # "casual" / "standard" / "irons"
    }

    def __init__(self, save_path: Path | str | None = None):
        self._save_path = Path(save_path) if save_path else Path(S.RUN_HISTORY_FILE)
        self._data: dict = {}
        self._after_save = None  # optional callable — set by Game (SaveManager sync)
        self.load()

    # ------------------------------------------------------------------
    def load(self):
        path = self._save_path
        # Deep-copy defaults so the class-level mutable values (chapters_completed,
        # reputation, bax_hums_heard) aren't shared by reference across instances.
        defaults = copy.deepcopy(self._DEFAULTS)
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                self._data = {**defaults, **json.load(f)}
        else:
            self._data = defaults

    def save(self):
        path = self._save_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)
        if self._after_save:
            self._after_save()

    def reset_to_defaults(self) -> None:
        """Fresh campaign — Chapter 1, default debt, no completed chapters."""
        self._data = copy.deepcopy(self._DEFAULTS)

    # ------------------------------------------------------------------
    def apply_death_penalty(self, sector_index: int = 0):
        """Stepped tow fee: sectors 0-1 → 8k, 2-3 → 12k, 4+ → 16k."""
        if sector_index >= 4:
            tow_fee = 16000
        elif sector_index >= 2:
            tow_fee = 12000
        else:
            tow_fee = S.WRECKAGE_TOW_FEE  # 8000
        penalty = S.BASE_CLONE_DEBT + S.CLONE_FLUID_FEE + tow_fee
        self._data["debt"]        += penalty
        self._data["clone_count"] += 1
        bus.emit(EVT_DEBT_UPDATE, delta=penalty, total=self.debt)
        self.save()

    def pay_off(self, amount: int):
        """Reduce debt by amount (sector, terminal win, tether snap, etc.)."""
        actual = min(amount, self._data["debt"])
        self._data["debt"] = max(0, self._data["debt"] - amount)
        if actual > 0:
            bus.emit(EVT_DEBT_UPDATE, delta=-actual, total=self.debt)

    def add_debt(self, amount: int):
        """Increase debt (shop purchases re-add previously reduced credits)."""
        self._data["debt"] += amount
        bus.emit(EVT_DEBT_UPDATE, delta=amount, total=self.debt)

    def clear_debt_chunk(self, amount: int = 50000):
        self._data["debt"] = max(0, self._data["debt"] - amount)
        bus.emit(EVT_DEBT_UPDATE, delta=-amount, total=self.debt)

    def complete_chapter(self, chapter: int):
        if chapter not in self._data["chapters_completed"]:
            self._data["chapters_completed"].append(chapter)
            if len(self._data["chapters_completed"]) % 2 == 0:
                self._data["bax_level"] += 1
            self.save()

    def adjust_reputation(self, npc_id: str, delta: int):
        current = self._data["reputation"].get(npc_id, 0)
        self._data["reputation"][npc_id] = max(-10, min(10, current + delta))

    def get_reputation(self, npc_id: str) -> int:
        return self._data["reputation"].get(npc_id, 0)

    def mark_hum_heard(self, idx: int) -> bool:
        """Record that the player has heard hum `idx`.  Returns True if newly heard."""
        heard = self._data.setdefault("bax_hums_heard", [])
        if idx in heard:
            return False
        heard.append(idx)
        self.save()
        return True

    # ------------------------------------------------------------------
    @property
    def debt(self) -> int:
        return self._data["debt"]

    @property
    def clone_count(self) -> int:
        return self._data["clone_count"]

    @property
    def bax_level(self) -> int:
        return self._data["bax_level"]

    @property
    def chapters_completed(self) -> list[int]:
        return list(self._data["chapters_completed"])

    @property
    def is_debt_cleared(self) -> bool:
        return self._data["debt"] <= 0

    @property
    def bax_hums_heard(self) -> list[int]:
        return list(self._data.get("bax_hums_heard", []))

    @property
    def campaign_cleared_at_least_once(self) -> bool:
        """True if the player has completed all 4 chapters at any point."""
        return len(self._data.get("chapters_completed", [])) >= 4

    # ── Unlocks (Epic 12.2) ────────────────────────────────────────────────
    @property
    def unlocks(self) -> list[str]:
        return list(self._data.get("unlocks", []))

    def has_unlock(self, key: str) -> bool:
        return key in self._data.get("unlocks", [])

    def add_unlock(self, key: str) -> bool:
        """Add an unlock if not already earned. Returns True if newly earned."""
        unlocks = self._data.setdefault("unlocks", [])
        if key in unlocks:
            return False
        unlocks.append(key)
        self.save()
        from core.event_bus import bus, EVT_UNLOCK_EARNED
        bus.emit(EVT_UNLOCK_EARNED, key=key, label=key.replace("_", " ").upper())
        return True

    def inc_milestone(self, key: str, amount: int = 1) -> int:
        ctr = self._data.setdefault("milestone_counters", {})
        ctr[key] = ctr.get(key, 0) + amount
        return ctr[key]

    def milestone(self, key: str) -> int:
        return self._data.get("milestone_counters", {}).get(key, 0)

    # ── Difficulty (Epic 18) ───────────────────────────────────────────────
    @property
    def difficulty(self) -> str:
        return self._data.get("difficulty", "standard")

    def set_difficulty(self, value: str) -> None:
        if value in ("casual", "standard", "irons"):
            self._data["difficulty"] = value
            self.save()

    # Multipliers queried by game systems.
    def hull_start_delta(self) -> int:
        return {"casual": 30, "standard": 0, "irons": -20}.get(self.difficulty, 0)

    def debt_rate_mult(self) -> float:
        return {"casual": 0.7, "standard": 1.0, "irons": 1.5}.get(self.difficulty, 1.0)

    def barge_speed_mult(self) -> float:
        return {"casual": 0.75, "standard": 1.0, "irons": 1.30}.get(self.difficulty, 1.0)
