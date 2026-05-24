"""
Stats tracker — Epic 12.4.

Two layers:
  1. Run summary  : in-memory accumulators reset each run, displayed on death
                    screen / sector cards.
  2. Career stats : persistent JSON at data/saves/stats.json; updated at every
                    sector clear and run end.

Subscribes to the event bus to avoid plumbing changes elsewhere — gameplay
systems only need to emit events as they already do.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path

from core.event_bus import (bus, EVT_SECTOR_CLEAR, EVT_RUN_END, EVT_RUN_START,
                             EVT_SLINGSHOT, EVT_TETHER_SNAP, EVT_BARGE_KILLED,
                             EVT_TERMINAL_CLOSE, EVT_DEBT_UPDATE,
                             EVT_SHIP_DESTROYED, EVT_WARP_JUMP)


_DEFAULT_CAREER = {
    "runs_started":     0,
    "runs_completed":   0,
    "total_debt_accrued": 0,
    "total_debt_paid":    0,
    "deepest_sector_per_chapter": {},   # "1"/"2"/"3"/"4" -> int
    "lifetime_slingshots": 0,
    "lifetime_snaps":      0,
    "lifetime_kills":      0,
    "best_single_run_credits":  0,
    "best_slingshot_speed":     0,
    "fastest_sector_1_s":       0,      # 0 = never recorded
    "longest_no_damage_run_s":  0,
    "npc_outcomes": {},                 # "<npc>": {"exploit":n,"release":n,"impound":n,"paradox":n}
}


class StatsTracker:
    def __init__(self, save_path: Path | str | None = None):
        from config import settings as S
        if save_path is None:
            save_path = Path(S.SAVES_DIR) / "stats.json"
        self._save_path = Path(save_path)
        self._career: dict = copy.deepcopy(_DEFAULT_CAREER)
        self.load()
        self._run = self._fresh_run()
        self._wire()

    # ── Persistence ───────────────────────────────────────────────────────
    def load(self) -> None:
        if self._save_path.is_file():
            try:
                with open(self._save_path, encoding="utf-8") as f:
                    loaded = json.load(f)
                merged = copy.deepcopy(_DEFAULT_CAREER)
                merged.update(loaded)
                # nested defaults
                merged.setdefault("deepest_sector_per_chapter", {})
                merged.setdefault("npc_outcomes", {})
                self._career = merged
            except (OSError, json.JSONDecodeError):
                self._career = copy.deepcopy(_DEFAULT_CAREER)

    def save(self) -> None:
        self._save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._save_path, "w", encoding="utf-8") as f:
            json.dump(self._career, f, indent=2)

    # ── Run summary ───────────────────────────────────────────────────────
    @staticmethod
    def _fresh_run() -> dict:
        return {
            "slingshots": 0,
            "snaps":      0,
            "kills":      0,
            "credits_earned": 0,
            "debt_added":     0,
            "best_slingshot_speed": 0,
            "npc_outcomes": {"exploit":0,"release":0,"impound":0,"paradox":0,"continue":0},
            "sectors_cleared": 0,
            "chapter": 1,
        }

    @property
    def run(self) -> dict:
        return self._run

    @property
    def career(self) -> dict:
        return self._career

    def reset_run(self, chapter: int = 1) -> None:
        self._run = self._fresh_run()
        self._run["chapter"] = chapter

    # ── Event wiring ──────────────────────────────────────────────────────
    def _wire(self) -> None:
        bus.subscribe(EVT_RUN_START,       self._on_run_start)
        bus.subscribe(EVT_RUN_END,         self._on_run_end)
        bus.subscribe(EVT_SECTOR_CLEAR,    self._on_sector_clear)
        bus.subscribe(EVT_SLINGSHOT,       self._on_slingshot)
        bus.subscribe(EVT_TETHER_SNAP,     self._on_tether_snap)
        bus.subscribe(EVT_BARGE_KILLED,    self._on_barge_killed)
        bus.subscribe(EVT_TERMINAL_CLOSE,  self._on_terminal_close)
        bus.subscribe(EVT_DEBT_UPDATE,     self._on_debt_update)
        bus.subscribe(EVT_SHIP_DESTROYED,  self._on_ship_destroyed)

    # ── Handlers ──────────────────────────────────────────────────────────
    def _on_run_start(self, **_) -> None:
        self.reset_run()
        self._career["runs_started"] = self._career.get("runs_started", 0) + 1
        self.save()

    def _on_run_end(self, success: bool = False, **_) -> None:
        if success:
            self._career["runs_completed"] = self._career.get("runs_completed", 0) + 1
        # Aggregate
        c = self._career
        c["lifetime_slingshots"] = c.get("lifetime_slingshots", 0) + self._run["slingshots"]
        c["lifetime_snaps"]      = c.get("lifetime_snaps", 0)      + self._run["snaps"]
        c["lifetime_kills"]      = c.get("lifetime_kills", 0)      + self._run["kills"]
        if self._run["credits_earned"] > c.get("best_single_run_credits", 0):
            c["best_single_run_credits"] = self._run["credits_earned"]
        if self._run["best_slingshot_speed"] > c.get("best_slingshot_speed", 0):
            c["best_slingshot_speed"] = self._run["best_slingshot_speed"]
        self.save()

    def _on_sector_clear(self, sector_num: int | None = None, **_) -> None:
        if sector_num is None:
            return
        self._run["sectors_cleared"] += 1
        ch_key = str(self._run.get("chapter", 1))
        deep   = self._career.setdefault("deepest_sector_per_chapter", {})
        if sector_num > deep.get(ch_key, 0):
            deep[ch_key] = sector_num
        self.save()

    def _on_slingshot(self, speed: float = 0, **_) -> None:
        self._run["slingshots"] += 1
        if speed > self._run["best_slingshot_speed"]:
            self._run["best_slingshot_speed"] = int(speed)

    def _on_tether_snap(self, **_) -> None:
        self._run["snaps"] += 1

    def _on_barge_killed(self, **_) -> None:
        self._run["kills"] += 1

    def _on_terminal_close(self, outcome: str = "continue",
                            npc: str = "", **_) -> None:
        # Track in run + career, keyed by outcome label
        bucket = self._run["npc_outcomes"]
        bucket[outcome] = bucket.get(outcome, 0) + 1
        if npc:
            npc_book = self._career.setdefault("npc_outcomes", {})
            np = npc_book.setdefault(npc, {"exploit":0,"release":0,
                                            "impound":0,"paradox":0,"continue":0})
            np[outcome] = np.get(outcome, 0) + 1

    def _on_debt_update(self, delta: int = 0, total: int = 0, **_) -> None:
        if delta > 0:
            self._run["debt_added"] += delta
            self._career["total_debt_accrued"] = self._career.get("total_debt_accrued", 0) + delta
        elif delta < 0:
            paid = -delta
            self._run["credits_earned"] += paid
            self._career["total_debt_paid"] = self._career.get("total_debt_paid", 0) + paid

    def _on_ship_destroyed(self, **_) -> None:
        # Run summary already accumulated; career update happens on RUN_END.
        pass

    def set_chapter(self, chapter: int) -> None:
        self._run["chapter"] = chapter

    # ── Convenience for HUD/cards ─────────────────────────────────────────
    def run_summary_lines(self) -> list[str]:
        r = self._run
        return [
            f"SLINGSHOTS  {r['slingshots']}",
            f"TETHER SNAPS  {r['snaps']}",
            f"KILLS  {r['kills']}",
            f"CREDITS EARNED  {r['credits_earned']:,}",
            f"BEST SLINGSHOT  {r['best_slingshot_speed']} px/s",
        ]

    def career_summary_lines(self) -> list[str]:
        c = self._career
        return [
            f"RUNS STARTED  {c.get('runs_started', 0)}",
            f"RUNS COMPLETED  {c.get('runs_completed', 0)}",
            f"TOTAL DEBT ACCRUED  {c.get('total_debt_accrued', 0):,} cr",
            f"TOTAL DEBT PAID  {c.get('total_debt_paid', 0):,} cr",
            f"LIFETIME SLINGSHOTS  {c.get('lifetime_slingshots', 0)}",
            f"LIFETIME SNAPS  {c.get('lifetime_snaps', 0)}",
            f"LIFETIME KILLS  {c.get('lifetime_kills', 0)}",
            f"BEST SINGLE-RUN CREDITS  {c.get('best_single_run_credits', 0):,}",
            f"BEST SLINGSHOT  {c.get('best_slingshot_speed', 0)} px/s",
        ]
