"""Regression: frame hull bonuses and difficulty headroom were discarded.

`apply_draft` used `min(HULL_MAX, HULL_MAX + bonus)`, which can never
apply a positive frame bonus — REINFORCED JUNK MK2 advertised +20 and
launched at 200. Shop / harmonica / repair then clamped to HULL_MAX, so
a CASUAL courier at 210 hull who bought a hull patch *lost* 10 hp.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from types import SimpleNamespace

import pygame
import pytest

from config import settings as S


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    pygame.font.init()
    yield


def _rm_with_bonus(bonus: int, difficulty_delta: int = 0):
    from roguelite.run_manager import RunManager
    rm = RunManager.__new__(RunManager)
    rm._frame_hull_bonus = bonus
    rm.meta = SimpleNamespace(hull_start_delta=lambda: difficulty_delta)
    return rm


def test_hull_cap_applies_positive_frame_bonus():
    rm = _rm_with_bonus(20)
    assert rm.hull_cap() == S.HULL_MAX + 20


def test_hull_cap_applies_negative_frame_bonus():
    rm = _rm_with_bonus(-15)
    assert rm.hull_cap() == S.HULL_MAX - 15


def test_hull_cap_stacks_reinforced_and_casual():
    rm = _rm_with_bonus(20, difficulty_delta=30)
    assert rm.hull_cap() == S.HULL_MAX + 50


def test_hull_cap_stacks_scrap_and_irons():
    rm = _rm_with_bonus(-15, difficulty_delta=-20)
    assert rm.hull_cap() == S.HULL_MAX - 35


def test_apply_draft_reinforced_starts_above_hull_max(tmp_path):
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager
    from ship.ship import PlayerShip

    meta = MetaProgression(save_path=tmp_path / "meta.json")
    ship = PlayerShip()
    rm = RunManager(meta)
    rm.start_run(ship)
    rm.draft._choices[0] = [{
        "name": "REINFORCED JUNK MK2",
        "hull_bonus": 20,
        "mass_mod": 1.3,
        "bax": "Built like a vault.",
    }]
    rm.draft._selected = [0, 0, 0]
    rm.apply_draft(ship)
    assert ship.hull == pytest.approx(S.HULL_MAX + 20)
    assert ship.hull_max == pytest.approx(S.HULL_MAX + 20)


def test_apply_draft_scrap_starts_below_hull_max(tmp_path):
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager
    from ship.ship import PlayerShip

    meta = MetaProgression(save_path=tmp_path / "meta.json")
    ship = PlayerShip()
    rm = RunManager(meta)
    rm.start_run(ship)
    rm.draft._choices[0] = [{
        "name": "SCRAP DELTA-7",
        "hull_bonus": -15,
        "mass_mod": 0.8,
        "bax": "Light frame.",
    }]
    rm.draft._selected = [0, 0, 0]
    rm.apply_draft(ship)
    assert ship.hull == pytest.approx(S.HULL_MAX - 15)
    assert ship.hull_max == pytest.approx(S.HULL_MAX - 15)


def test_difficulty_fill_stacks_on_frame_bonus():
    from ship.ship import PlayerShip
    rm = _rm_with_bonus(20, difficulty_delta=30)
    ship = PlayerShip()
    rm.sync_hull_cap(ship, fill=True)
    assert ship.hull == pytest.approx(S.HULL_MAX + 50)
    assert ship.hull_max == pytest.approx(S.HULL_MAX + 50)


def test_shop_hull_patch_does_not_cut_casual_headroom():
    from roguelite.shop import _ShopItem
    from ship.ship import PlayerShip

    ship = PlayerShip()
    ship.hull_max = S.HULL_MAX + 30
    ship.hull = S.HULL_MAX + 10          # took 20 damage from a 230 start
    item = _ShopItem("Hull Patch Pack", "+50", "grey market", 1000, "hull_patch")
    item.apply(ship, run_mgr=None)
    assert ship.hull == pytest.approx(S.HULL_MAX + 30)
    assert ship.hull > S.HULL_MAX


def test_ship_repair_respects_hull_max_not_global_constant():
    from ship.ship import PlayerShip
    ship = PlayerShip()
    ship.hull_max = S.HULL_MAX + 20
    ship.hull = S.HULL_MAX - 5
    ship.repair(40.0)
    assert ship.hull == pytest.approx(S.HULL_MAX + 20)


def test_harmonica_starts_when_casual_hull_is_between_max_and_cap():
    """CASUAL at 200/230 used to be treated as 'full hull' and refused."""
    from ship.ship import PlayerShip
    from roguelite.run_manager import RunManager

    rm = RunManager.__new__(RunManager)
    rm._barges = []
    rm._harm_session_t = 0.0
    rm._harm_session_dur = 6.0
    rm._harm_heal_total = 5.0
    rm._harm_heal_paid = 0.0
    rm._harm_block_radius = 300.0
    rm._frame_hull_bonus = 0
    rm.meta = SimpleNamespace(hull_start_delta=lambda: 30)
    ship = PlayerShip()
    ship.hull = S.HULL_MAX
    ship.hull_max = S.HULL_MAX + 30
    rm._ship = ship
    assert rm.start_harmonica_session() is True


def test_respawn_fills_to_run_ceiling_not_global_max():
    from ship.ship import PlayerShip
    from roguelite.run_manager import RunManager

    rm = RunManager.__new__(RunManager)
    rm._frame_hull_bonus = 20
    rm.meta = SimpleNamespace(hull_start_delta=lambda: 30)
    rm._active_terminal = None
    rm._intercepting_barge = None
    rm._pending_advance = False
    rm._shower_rocks = []
    rm._run_seed = 1
    rm._sector_index = 0
    rm._barges = []
    rm._spawn_queue = []
    rm._sling_well_t = {}
    rm._well_hit_times = {}
    rm._jump_ready_fired = False
    rm._kress_called_this_sector = False
    rm._fuel_warned = False
    rm._sector_slingshots = 0
    rm._sector_snaps = 0
    rm._sector_credits = 0
    rm.mutators = SimpleNamespace(is_active=lambda *_: False)
    rm._sector = SimpleNamespace(theme="", name="", formerly="")
    rm._current_chapter = lambda: 1
    rm._difficulty = lambda: 1.0
    rm._cold_sector_theme = lambda rng: None
    rm._spawn_sector_objects = lambda: None
    from roguelite.procedural import generate_sector
    rm._restart_current_sector = lambda ship: setattr(rm, "_ship", ship)

    ship = PlayerShip()
    ship._destroyed = True
    ship.hull = 0.0
    rm.respawn_after_death(ship)
    assert ship.hull == pytest.approx(S.HULL_MAX + 50)
    assert ship.hull_max == pytest.approx(S.HULL_MAX + 50)
    assert ship._destroyed is False
