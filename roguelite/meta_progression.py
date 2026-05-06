from __future__ import annotations
import json
import os
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
    }

    def __init__(self):
        self._data: dict = {}
        self.load()

    # ------------------------------------------------------------------
    def load(self):
        if os.path.exists(S.RUN_HISTORY_FILE):
            with open(S.RUN_HISTORY_FILE, "r") as f:
                self._data = {**self._DEFAULTS, **json.load(f)}
        else:
            self._data = dict(self._DEFAULTS)

    def save(self):
        os.makedirs(os.path.dirname(S.RUN_HISTORY_FILE), exist_ok=True)
        with open(S.RUN_HISTORY_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    # ------------------------------------------------------------------
    def apply_death_penalty(self):
        penalty = S.BASE_CLONE_DEBT + S.CLONE_FLUID_FEE + S.WRECKAGE_TOW_FEE
        self._data["debt"]        += penalty
        self._data["clone_count"] += 1
        bus.emit(EVT_DEBT_UPDATE, delta=penalty, total=self.debt)
        self.save()

    def clear_debt_chunk(self, amount: int = 50000):
        self._data["debt"] = max(0, self._data["debt"] - amount)
        bus.emit(EVT_DEBT_UPDATE, delta=-amount, total=self.debt)

    def complete_chapter(self, chapter: int):
        if chapter not in self._data["chapters_completed"]:
            self._data["chapters_completed"].append(chapter)
            if len(self._data["chapters_completed"]) % 2 == 0:
                self._data["bax_level"] += 1

    def adjust_reputation(self, npc_id: str, delta: int):
        current = self._data["reputation"].get(npc_id, 0)
        self._data["reputation"][npc_id] = max(-10, min(10, current + delta))

    def get_reputation(self, npc_id: str) -> int:
        return self._data["reputation"].get(npc_id, 0)

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
