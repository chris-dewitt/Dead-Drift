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
