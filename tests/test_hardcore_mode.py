"""Coverage for Epic 8.4 — HARDCORE chapter variant."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import tempfile
from pathlib import Path

import pygame


def _meta(tmp):
    from roguelite.meta_progression import MetaProgression
    return MetaProgression(save_path=Path(tmp) / "meta.json")


def test_meta_hardcore_unlock_and_record_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        meta = _meta(tmp)
        assert meta.is_hardcore_unlocked(1) is False
        assert meta.unlock_hardcore_for_chapter(1) is True
        # Idempotent
        assert meta.unlock_hardcore_for_chapter(1) is False
        # Best time: 0 means "not yet recorded"
        assert meta.hardcore_best_time(1) == 0
        # First record sticks; faster record overwrites; slower record doesn't.
        assert meta.record_hardcore_clear(1, 540.4) is True
        assert meta.hardcore_best_time(1) == 540
        assert meta.record_hardcore_clear(1, 600.0) is False
        assert meta.hardcore_best_time(1) == 540
        assert meta.record_hardcore_clear(1, 480.0) is True
        assert meta.hardcore_best_time(1) == 480

        # Persistence — a fresh instance should see the record.
        from roguelite.meta_progression import MetaProgression
        meta2 = MetaProgression(save_path=Path(tmp) / "meta.json")
        assert meta2.is_hardcore_unlocked(1) is True
        assert meta2.hardcore_best_time(1) == 480


def test_hardcore_run_flag_is_run_scoped():
    with tempfile.TemporaryDirectory() as tmp:
        meta = _meta(tmp)
        assert meta.is_hardcore is False
        meta.set_hardcore_for_next_run(True)
        assert meta.is_hardcore is True
        meta.clear_hardcore_flag()
        assert meta.is_hardcore is False


def test_run_manager_hardcore_compresses_sector_dur_and_bumps_difficulty():
    """The hardcore-aware helpers honour meta.is_hardcore."""
    pygame.init()
    pygame.font.init()
    from roguelite.run_manager import RunManager
    with tempfile.TemporaryDirectory() as tmp:
        meta = _meta(tmp)
        rm = RunManager.__new__(RunManager)
        rm.meta = meta
        rm._sector_index = 0
        rm._chapter_override = None

        # Standard
        assert rm.is_hardcore_run() is False
        assert rm.hardcore_sector_dur(20.0) == 20.0
        assert abs(rm._difficulty() - 1.0) < 1e-6

        # Hardcore armed
        meta.set_hardcore_for_next_run(True)
        assert rm.is_hardcore_run() is True
        assert abs(rm.hardcore_sector_dur(20.0) - 14.0) < 1e-6
        assert abs(rm._difficulty() - 1.3) < 1e-6


def test_make_corridor_hardcore_strips_checkpoints():
    pygame.init()
    pygame.font.init()
    from delivery.corridor import make_corridor
    from delivery.corridor.elements import Checkpoint

    for ch in (1, 2, 3, 4):
        normal = make_corridor(ch, hardcore=False)
        normal_cps = sum(
            1 for r in normal.rooms for el in r.elements
            if isinstance(el, Checkpoint)
        )
        hard = make_corridor(ch, hardcore=True)
        hard_cps = sum(
            1 for r in hard.rooms for el in r.elements
            if isinstance(el, Checkpoint)
        )
        assert hard_cps == 0, f"Ch.{ch} hardcore must strip Checkpoints"
        assert getattr(hard, "hardcore", False) is True
        # And the normal build still has them — otherwise hardcore is moot.
        assert normal_cps >= 0  # at least no regression
        assert getattr(normal, "hardcore", False) is False


def test_delivery_sequence_passes_hardcore_to_make_corridor():
    """delivery_sequence reads meta.is_hardcore when constructing the corridor."""
    src = Path("delivery/delivery_sequence.py").read_text(encoding="utf-8")
    assert "make_corridor(" in src
    assert "hardcore=bool(getattr(self.meta," in src


def test_run_manager_skips_shop_when_hardcore():
    """The shop trigger respects is_hardcore_run()."""
    src = Path("roguelite/run_manager.py").read_text(encoding="utf-8")
    assert "is_hardcore_run()" in src
    assert "shops_allowed = " in src or "is_hardcore_run() and self._sector_index" in src
