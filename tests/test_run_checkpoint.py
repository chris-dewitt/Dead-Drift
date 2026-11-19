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


def _disk_debt(meta) -> int | None:
    if not meta._save_path.is_file():
        return None
    return int(json.loads(meta._save_path.read_text(encoding="utf-8"))["debt"])


def test_payoff_stays_in_memory_until_the_checkpoint_commits_it(mini_game):
    """Resume Run reloads the slot file, then the checkpoint.

    Sector clears, exploits, and shop prices only changed the in-memory
    ledger. The 25s autosave stored the ship. Closing the game and
    resuming restored the purchases and forgot the credits.
    """
    from roguelite.meta_progression import MetaProgression
    from roguelite.save_manager import SaveManager

    meta = mini_game.run_mgr.meta
    before = meta.debt
    meta.pay_off(12500, source="SECTOR CLEAR")
    meta.add_debt(1000, source="SHOP: HULL PATCH PACK")
    assert meta.debt == before - 11500
    assert _disk_debt(meta) != meta.debt

    mini_game.meta = meta
    SaveManager().save_run_checkpoint(mini_game)

    reloaded = MetaProgression(save_path=meta._save_path)
    assert reloaded.debt == before - 11500


def test_checkpoint_commits_post_campaign_bar_income(mini_game):
    from roguelite.meta_progression import MetaProgression
    from roguelite.save_manager import SaveManager

    meta = mini_game.run_mgr.meta
    meta._data["chapters_completed"] = [1, 2, 3, 4, 5, 6]
    meta.pay_off(4000, source="SECTOR CLEAR")
    assert meta.bar_credits == 4000
    assert not meta._save_path.is_file() or "bar_credits" not in json.loads(
        meta._save_path.read_text(encoding="utf-8"))

    mini_game.meta = meta
    SaveManager().save_run_checkpoint(mini_game)

    reloaded = MetaProgression(save_path=meta._save_path)
    assert reloaded.ledger_wiped
    assert reloaded.bar_credits == 4000
    assert reloaded.debt == meta.debt


def test_quit_snapshots_flight_and_skips_delivery(mini_game):
    from types import SimpleNamespace

    from core.game import Game
    from roguelite.meta_progression import MetaProgression
    from roguelite.save_manager import SaveManager

    meta = mini_game.run_mgr.meta
    before = meta.debt
    meta.pay_off(8000, source="EXPLOIT")
    mini_game.meta = meta
    mini_game.save_mgr = SaveManager()
    mini_game._PERSIST_ON_QUIT = Game._PERSIST_ON_QUIT
    mini_game._save_run_checkpoint = Game._save_run_checkpoint.__get__(mini_game)

    mini_game.states = SimpleNamespace(state=GameState.DELIVERY)
    mini_game._state_before_pause = None
    Game._persist_progress(mini_game)
    assert _disk_debt(meta) != meta.debt
    assert not mini_game.save_mgr.has_run_checkpoint()

    mini_game.states = SimpleNamespace(state=GameState.PAUSED)
    mini_game._state_before_pause = GameState.FLIGHT
    Game._persist_progress(mini_game)
    reloaded = MetaProgression(save_path=meta._save_path)
    assert reloaded.debt == before - 8000
    assert mini_game.save_mgr.has_run_checkpoint()
