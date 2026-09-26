"""Round-trip tests for mid-run checkpoint serialization."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from config import settings as S
from core.state_manager import GameState
from roguelite.run_checkpoint import (
    CHECKPOINT_VERSION,
    build_checkpoint,
    load_checkpoint_file,
    restore_checkpoint,
    save_checkpoint_file,
)


@pytest.fixture
def mini_game(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "SAVES_DIR", str(tmp_path / "saves"))
    monkeypatch.setattr(S, "MANIFEST_FILE", str(tmp_path / "saves/manifest.json"))

    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager
    from ship.ship import PlayerShip

    meta = MetaProgression(save_path=tmp_path / "meta.json")
    ship = PlayerShip()
    rm = RunManager(meta)
    rm.start_run(ship)
    rm.apply_draft(ship)

    game = MagicMock()
    game.run_mgr = rm
    game.ship = ship
    game.states = MagicMock(state=GameState.FLIGHT)
    game._state_before_pause = None
    game._delivery_chapter = 1
    game._delivery_pending = False
    game._delivery_delay_t = 0.0
    game._delivery = None
    game._terminal_win_hold_t = 0.0
    game._terminal_win_str = ""
    game._interstitial_completed = 1
    game._interstitial_next = 2
    game._interstitial_campaign_end = False
    game._interstitial_t = 0.0
    return game


def test_checkpoint_roundtrip(mini_game, tmp_path):
    path = tmp_path / "run.json"
    save_checkpoint_file(path, mini_game)
    data = load_checkpoint_file(path)
    assert data is not None
    assert data["version"] == CHECKPOINT_VERSION
    assert data["draft_applied"] is True
    assert data["run_mgr"]["sector_index"] == 0

    mini_game.run_mgr._sector_index = 99
    mini_game.ship.hull = 12.0
    assert restore_checkpoint(mini_game, data) is True
    assert mini_game.run_mgr._sector_index == 0
    assert mini_game.ship.hull == pytest.approx(
        float(json.loads(path.read_text())["ship"]["hull"])
    )


def test_checkpoint_roundtrips_chapter_six_drive_and_pursuit_state(mini_game):
    from antagonists.compliance_vessel import ComplianceVessel
    from cargo.encrypted_drive import EncryptedDrive
    from physics.body import Vec2

    drive = EncryptedDrive()
    drive.trace_level = 0.75
    drive._ping_t = 4.25
    mini_game.ship.cargo = drive
    mini_game.ship.fuel = 19.5
    mini_game.ship.gun.fire_rate_mult = 1.4
    mini_game.ship.gun.damage_mult = 2

    rm = mini_game.run_mgr
    rm._compliance_spawn_cd = 3.5
    rm._emp_burst_available = True
    rm._emp_burst_active_t = 0.2
    vessel = ComplianceVessel(101.0, 202.0, rm)
    vessel.vel = Vec2(7.0, -5.0)
    vessel.state = "stunned"
    vessel._state_t = 1.5
    vessel._hits = 1
    vessel._stun_t = 2.25
    vessel.heading = 33.0
    rm._compliance_vessels = [vessel]

    data = build_checkpoint(mini_game)

    mini_game.ship.cargo = None
    mini_game.ship.fuel = S.FUEL_MAX
    mini_game.ship.gun.fire_rate_mult = 1.0
    mini_game.ship.gun.damage_mult = 1
    rm._compliance_spawn_cd = 12.0
    rm._emp_burst_available = False
    rm._emp_burst_active_t = 0.0
    rm._compliance_vessels.clear()

    assert restore_checkpoint(mini_game, data) is True

    restored_drive = mini_game.ship.cargo
    assert isinstance(restored_drive, EncryptedDrive)
    assert restored_drive.trace_level == pytest.approx(0.75)
    assert restored_drive._ping_t == pytest.approx(4.25)
    assert mini_game.ship.fuel == pytest.approx(19.5)
    assert mini_game.ship.gun.fire_rate_mult == pytest.approx(1.4)
    assert mini_game.ship.gun.damage_mult == 2
    assert rm._compliance_spawn_cd == pytest.approx(3.5)
    assert rm._emp_burst_available is True
    assert rm._emp_burst_active_t == pytest.approx(0.2)
    assert len(rm._compliance_vessels) == 1
    restored_vessel = rm._compliance_vessels[0]
    assert restored_vessel.pos.x == pytest.approx(101.0)
    assert restored_vessel.pos.y == pytest.approx(202.0)
    assert restored_vessel.vel.x == pytest.approx(7.0)
    assert restored_vessel.vel.y == pytest.approx(-5.0)
    assert restored_vessel.state == "stunned"
    assert restored_vessel._hits == 1


def test_terminal_checkpoint_resumes_safe_state(mini_game):
    mini_game.states = MagicMock(state=GameState.TERMINAL)
    mini_game._state_before_pause = None
    mini_game._delivery_pending = False

    data = build_checkpoint(mini_game)

    assert data["game_state"] == "FLIGHT"

    mini_game._delivery_pending = True
    data = build_checkpoint(mini_game)

    assert data["game_state"] == "DELIVERY"


def _resumed_game(tmp_path, name):
    """A process that loaded the menu and has not called start_run()."""
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager
    from ship.ship import PlayerShip

    meta = MetaProgression(save_path=tmp_path / f"{name}.json")
    ship = PlayerShip()
    game = MagicMock()
    game.run_mgr = RunManager(meta)
    game.ship = ship
    game.meta = meta
    game.states = MagicMock(state=GameState.FLIGHT)
    game._state_before_pause = None
    game._delivery_chapter = 1
    game._delivery_pending = False
    game._delivery_delay_t = 0.0
    game._delivery = None
    game._terminal_win_hold_t = 0.0
    game._terminal_win_str = ""
    game._interstitial_completed = 1
    game._interstitial_next = 2
    game._interstitial_campaign_end = False
    game._interstitial_t = 0.0
    return game


def test_resume_keeps_dossier_replay_on_its_chapter(mini_game, tmp_path):
    """Save & Continue during a dossier replay must not clear the next chapter.

    Natural progression after chapter 1 is chapter 2. A chapter 1 replay sets
    `_chapter_override`. Resume used to drop the override, so finishing the
    run called `complete_chapter(2)`.
    """
    mini_game.run_mgr.meta._data["chapters_completed"] = [1]
    mini_game.run_mgr.set_chapter_override(1)
    data = build_checkpoint(mini_game)

    resumed = _resumed_game(tmp_path, "replay")
    resumed.meta._data["chapters_completed"] = [1]
    assert resumed.run_mgr._current_chapter() == 2

    assert restore_checkpoint(resumed, data) is True
    assert resumed.run_mgr._chapter_override == 1
    assert resumed.run_mgr._current_chapter() == 1


def test_legacy_replay_checkpoint_does_not_advance_the_campaign(mini_game, tmp_path):
    """Saves written before chapter_override existed still stored `chapter`."""
    mini_game.run_mgr.meta._data["chapters_completed"] = [1]
    mini_game.run_mgr.set_chapter_override(1)
    data = build_checkpoint(mini_game)
    del data["chapter_override"]

    resumed = _resumed_game(tmp_path, "legacy-replay")
    resumed.meta._data["chapters_completed"] = [1]
    assert restore_checkpoint(resumed, data) is True
    assert resumed.run_mgr._current_chapter() == 1


def test_resume_of_a_natural_run_does_not_invent_an_override(mini_game, tmp_path):
    mini_game.run_mgr.meta._data["chapters_completed"] = [1]
    mini_game.run_mgr.set_chapter_override(None)
    data = build_checkpoint(mini_game)
    assert data["chapter"] == 2
    assert data["chapter_override"] is None

    resumed = _resumed_game(tmp_path, "natural")
    resumed.meta._data["chapters_completed"] = [1]
    assert restore_checkpoint(resumed, data) is True
    assert resumed.run_mgr._chapter_override is None
    assert resumed.run_mgr._current_chapter() == 2


def test_resume_keeps_slingshot_only_from_advancing_the_timer(mini_game, tmp_path):
    from roguelite.mutators import MUTATORS

    mini_game.run_mgr.mutators.active = MUTATORS["slingshot_only"]
    mini_game.run_mgr._sector_timer = 4.0
    data = build_checkpoint(mini_game)

    resumed = _resumed_game(tmp_path, "sling")
    assert resumed.run_mgr.mutators.active is None
    assert restore_checkpoint(resumed, data) is True
    assert resumed.run_mgr.mutators.is_active("slingshot_only")

    before = resumed.run_mgr._sector_timer
    resumed.run_mgr.update(1.0)
    assert resumed.run_mgr._sector_timer == pytest.approx(before)


def test_resume_keeps_quiet_sector_from_spawning_barges(mini_game, tmp_path):
    from roguelite.mutators import MUTATORS

    rm = mini_game.run_mgr
    rm.mutators.active = MUTATORS["quiet_sector"]
    rm._sector_index = 1
    rm._barges.clear()
    data = build_checkpoint(mini_game)

    resumed = _resumed_game(tmp_path, "quiet")
    assert restore_checkpoint(resumed, data) is True
    assert resumed.run_mgr.mutators.is_active("quiet_sector")
    resumed.run_mgr._spawn_barge()
    assert resumed.run_mgr._barges == []


def test_resume_restores_veteran_clone_without_adding_debt(mini_game, tmp_path):
    from roguelite.mutators import MUTATORS

    mini_game.run_mgr.mutators.active = MUTATORS["veteran_clone"]
    mini_game.run_mgr.meta._data["debt"] = 150_000
    data = build_checkpoint(mini_game)

    resumed = _resumed_game(tmp_path, "veteran")
    resumed.meta._data["debt"] = 150_000
    assert restore_checkpoint(resumed, data) is True
    assert resumed.run_mgr.mutators.is_active("veteran_clone")
    assert resumed.meta.debt == 150_000


def test_resume_remembers_a_spent_novice_pass(mini_game, tmp_path):
    from roguelite.mutators import MUTATORS
    from ship.gun import Gun

    mini_game.run_mgr.mutators.active = MUTATORS["novice_pass"]
    mini_game.run_mgr._novice_pass_consumed = True
    data = build_checkpoint(mini_game)

    Gun.malfunction_multiplier = 3.0
    resumed = _resumed_game(tmp_path, "novice")
    try:
        assert restore_checkpoint(resumed, data) is True
        assert resumed.run_mgr.mutators.is_active("novice_pass")
        assert resumed.run_mgr._novice_pass_consumed is True
        # A non-glitch resume must not keep another run's malfunction rate.
        assert Gun.malfunction_multiplier == 1.0
    finally:
        Gun.malfunction_multiplier = 1.0


def test_resume_reapplies_system_glitch_malfunction_rate(mini_game, tmp_path):
    from roguelite.mutators import MUTATORS
    from ship.gun import Gun

    mini_game.run_mgr.mutators.active = MUTATORS["system_glitch"]
    data = build_checkpoint(mini_game)
    Gun.malfunction_multiplier = 1.0
    resumed = _resumed_game(tmp_path, "glitch")
    try:
        assert restore_checkpoint(resumed, data) is True
        assert Gun.malfunction_multiplier == 3.0
    finally:
        Gun.malfunction_multiplier = 1.0


def test_checkpoint_roundtrips_wreck_state(mini_game):
    from antagonists.wreck import SpaceWreck

    rm = mini_game.run_mgr
    wreck = SpaceWreck(400.0, 300.0, subtype=SpaceWreck.SUBTYPE_INTERACTIVE)
    wreck.angle = 123.0
    wreck.rot_speed = -1.25
    wreck.length = 170
    wreck.width = 55
    wreck.gap_frac = 0.42
    wreck.weak_hp = 1          # two weak-point hits already landed
    rm._wrecks = [wreck]

    data = build_checkpoint(mini_game)
    rm._wrecks = []
    assert restore_checkpoint(mini_game, data) is True

    assert len(rm._wrecks) == 1
    restored = rm._wrecks[0]
    assert restored.subtype == SpaceWreck.SUBTYPE_INTERACTIVE
    assert restored.angle == pytest.approx(123.0)
    assert restored.rot_speed == pytest.approx(-1.25)
    assert (restored.length, restored.width) == (170, 55)
    assert restored.gap_frac == pytest.approx(0.42)
    assert restored.weak_hp == 1
    assert restored.is_triggered is False
