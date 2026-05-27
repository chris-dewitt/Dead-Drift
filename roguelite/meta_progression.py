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
        "debt":               350000,
        "clone_count":        1,
        "chapters_completed": [],
        "bax_level":          1,
        "reputation":         {},     # npc_id -> int (-10..10)
        "bax_hums_heard":     [],     # list[int] — hum indices the player has heard
        "unlocks":            [],     # list[str] — earned unlock keys (Epic 12.2)
        "milestone_counters": {},     # str -> int (e.g. "slingshots_total")
        "difficulty":         "standard",  # "casual" / "standard" / "irons"
        # Epic 8.3 — Bax's Records: lore fragments collected from corridor secrets.
        # List of {"text": str, "chapter": int} so the Records tab can group them.
        "lore_fragments":     [],
        # Epic 8.4 — HARDCORE chapter variant.
        # Chapters whose hardcore mode the player has unlocked (any normal clear).
        "hardcore_unlocked":  [],
        # Best HARDCORE clear time per chapter (seconds, int). 0 = no record yet.
        "hardcore_best_s":    {},
        # Whether the *next/current* run is being played in hardcore. Run-scoped;
        # cleared on run start unless explicitly opted in via set_hardcore_for_next_run.
        "hardcore_active":    False,
        # Aliveness Phase E -- cross-run story state. Kept inside the slot
        # save so campaign choices do not bleed between save files.
        "lore_progress":      {},
        "npc_state":          {},
        # Aliveness F.5 — Bax player-style observations (cumulative across runs)
        "bax_style":          {"bribe": 0, "brute": 0, "exploit": 0},
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
        bus.emit(EVT_DEBT_UPDATE, delta=penalty, total=self.debt,
                 source="CLONE TANK")
        self.save()

    def pay_off(self, amount: int, source: str = ""):
        """Reduce debt by amount (sector, terminal win, tether snap, etc.).

        Epic 13.1 — `source` is a short human-readable tag that floats
        beside the HUD debt counter so the player can see where each
        change came from."""
        actual = min(amount, self._data["debt"])
        self._data["debt"] = max(0, self._data["debt"] - amount)
        if actual > 0:
            bus.emit(EVT_DEBT_UPDATE, delta=-actual, total=self.debt,
                     source=source)

    def add_debt(self, amount: int, source: str = ""):
        """Increase debt (shop purchases re-add previously reduced credits)."""
        self._data["debt"] += amount
        bus.emit(EVT_DEBT_UPDATE, delta=amount, total=self.debt,
                 source=source)

    def clear_debt_chunk(self, amount: int = 50000, source: str = ""):
        self._data["debt"] = max(0, self._data["debt"] - amount)
        bus.emit(EVT_DEBT_UPDATE, delta=-amount, total=self.debt,
                 source=source)

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

    # ── Lore fragments (Epic 8.3 — Bax's Records, Tab 4) ─────────────────
    def add_lore_fragment(self, text: str, chapter: int = 0) -> bool:
        """Record a lore scrap from a corridor secret. Returns True if newly stored."""
        text = (text or "").strip()
        if not text:
            return False
        frags = self._data.setdefault("lore_fragments", [])
        for entry in frags:
            if entry.get("text") == text:
                return False
        frags.append({"text": text, "chapter": int(chapter)})
        self.save()
        return True

    @property
    def lore_fragments(self) -> list[dict]:
        return [dict(e) for e in self._data.get("lore_fragments", [])]

    # -- Aliveness Phase E: persistent world/story state ----------------
    def lore_stage(self, key: str) -> int:
        progress = self._data.setdefault("lore_progress", {})
        entry = progress.get(key, 0)
        if isinstance(entry, dict):
            return int(entry.get("stage", 0))
        return int(entry or 0)

    def advance_lore_stage(self, key: str, max_stage: int) -> tuple[int, bool]:
        """Advance a progressive lore beat by one. Returns (stage, changed)."""
        progress = self._data.setdefault("lore_progress", {})
        old_stage = self.lore_stage(key)
        new_stage = min(int(max_stage), old_stage + 1)
        if new_stage == old_stage:
            return old_stage, False
        progress[key] = new_stage
        self.save()
        return new_stage, True

    def mark_lore_flag(self, key: str) -> bool:
        flags = self._data.setdefault("lore_progress", {}).setdefault("flags", {})
        if flags.get(key):
            return False
        flags[key] = True
        self.save()
        return True

    def has_lore_flag(self, key: str) -> bool:
        flags = self._data.setdefault("lore_progress", {}).setdefault("flags", {})
        return bool(flags.get(key, False))

    def npc_state(self, npc_id: str) -> dict:
        book = self._data.setdefault("npc_state", {})
        return dict(book.get(npc_id, {}))

    def mark_npc_dead(self, npc_id: str, reason: str = "") -> bool:
        book = self._data.setdefault("npc_state", {})
        state = book.setdefault(npc_id, {})
        if state.get("dead"):
            return False
        state["dead"] = True
        if reason:
            state["death_reason"] = reason
        self.save()
        return True

    def is_npc_dead(self, npc_id: str) -> bool:
        return bool(self._data.setdefault("npc_state", {})
                    .get(npc_id, {}).get("dead", False))

    def set_npc_flag(self, npc_id: str, flag: str, value=True) -> bool:
        book = self._data.setdefault("npc_state", {})
        state = book.setdefault(npc_id, {})
        old_value = state.get(flag)
        if old_value == value:
            return False
        state[flag] = value
        self.save()
        return True

    def get_npc_flag(self, npc_id: str, flag: str, default=False):
        return self._data.setdefault("npc_state", {}).get(npc_id, {}).get(flag, default)

    def consume_npc_flag(self, npc_id: str, flag: str) -> bool:
        book = self._data.setdefault("npc_state", {})
        state = book.setdefault(npc_id, {})
        if not state.get(flag):
            return False
        state[flag] = False
        self.save()
        return True

    def record_union_schism(self, side: str, path: str = "") -> bool:
        """Record pressure on Local 404's internal split.

        Returns True only when both the idealist and corrupt reps have now
        been played against each other and the schism resolves.
        """
        book = self._data.setdefault("npc_state", {})
        state = book.setdefault("local_404", {})
        sides = set(state.get("schism_sides", []))
        before_resolved = bool(state.get("schism_resolved", False))
        sides.add(side)
        state["schism_sides"] = sorted(sides)
        if path:
            paths = state.setdefault("schism_paths", [])
            if path not in paths:
                paths.append(path)
        if {"idealist", "corrupt"}.issubset(sides):
            state["schism_resolved"] = True
        changed = bool(state.get("schism_resolved", False)) and not before_resolved
        self.save()
        return changed

    # ── Hardcore mode (Epic 8.4) ──────────────────────────────────────────
    def unlock_hardcore_for_chapter(self, chapter: int) -> bool:
        """Mark a chapter as having a hardcore variant available. Called on
        first successful clear of that chapter. Returns True if newly unlocked."""
        unlocked = self._data.setdefault("hardcore_unlocked", [])
        if chapter in unlocked:
            return False
        unlocked.append(int(chapter))
        self.save()
        return True

    def is_hardcore_unlocked(self, chapter: int) -> bool:
        return int(chapter) in self._data.get("hardcore_unlocked", [])

    @property
    def is_hardcore(self) -> bool:
        """Whether the current run is being played in hardcore mode."""
        return bool(self._data.get("hardcore_active", False))

    def set_hardcore_for_next_run(self, active: bool) -> None:
        """Opt the next run into hardcore. Cleared by `clear_hardcore_flag()`
        once the run starts so the flag doesn't sticky-stick across menus."""
        self._data["hardcore_active"] = bool(active)
        self.save()

    def clear_hardcore_flag(self) -> None:
        """Reset the run-scoped flag — called at the end of a hardcore run."""
        self._data["hardcore_active"] = False
        self.save()

    def hardcore_best_time(self, chapter: int) -> int:
        """Best HARDCORE clear time for a chapter, in whole seconds (0 = none)."""
        book = self._data.get("hardcore_best_s", {}) or {}
        return int(book.get(str(int(chapter)), 0))

    def record_hardcore_clear(self, chapter: int, total_seconds: float) -> bool:
        """Save a hardcore clear time. Returns True if a new record was set."""
        if total_seconds <= 0:
            return False
        book = self._data.setdefault("hardcore_best_s", {})
        key = str(int(chapter))
        prev = int(book.get(key, 0))
        new_t = int(round(total_seconds))
        if prev == 0 or new_t < prev:
            book[key] = new_t
            self.save()
            return True
        return False

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
