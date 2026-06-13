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


def test_checkpoint_roundtrip_preserves_fuel(mini_game, tmp_path):
    mini_game.ship.fuel = 17.5

    path = tmp_path / "fuel-run.json"
    save_checkpoint_file(path, mini_game)
    data = load_checkpoint_file(path)
    assert data is not None

    mini_game.ship.fuel = S.FUEL_MAX
    assert restore_checkpoint(mini_game, data) is True

    assert mini_game.ship.fuel == pytest.approx(17.5)


def test_checkpoint_roundtrip_preserves_encrypted_drive(mini_game, tmp_path):
    from cargo.encrypted_drive import EncryptedDrive

    drive = EncryptedDrive()
    drive.trace_level = 0.75
    drive._ping_t = 9.5
    mini_game.ship.cargo = drive

    path = tmp_path / "drive-run.json"
    save_checkpoint_file(path, mini_game)
    data = load_checkpoint_file(path)
    assert data is not None

    mini_game.ship.cargo = None
    assert restore_checkpoint(mini_game, data) is True

    restored = mini_game.ship.cargo
    assert isinstance(restored, EncryptedDrive)
    assert restored.trace_level == pytest.approx(0.75)
    assert restored._ping_t == pytest.approx(9.5)


def test_checkpoint_roundtrip_preserves_gun_upgrades(mini_game, tmp_path):
    mini_game.ship.gun.fire_rate_mult = 2.0
    mini_game.ship.gun.damage_mult = 2

    path = tmp_path / "gun-run.json"
    save_checkpoint_file(path, mini_game)
    data = load_checkpoint_file(path)
    assert data is not None

    mini_game.ship.gun.fire_rate_mult = 1.0
    mini_game.ship.gun.damage_mult = 1
    assert restore_checkpoint(mini_game, data) is True

    assert mini_game.ship.gun.fire_rate_mult == pytest.approx(2.0)
    assert mini_game.ship.gun.damage_mult == 2


def test_checkpoint_roundtrip_preserves_compliance_state(mini_game, tmp_path):
    from antagonists.compliance_vessel import ComplianceVessel

    vessel = ComplianceVessel(220.0, 180.0, mini_game.run_mgr)
    vessel.vel.x = 12.0
    vessel.vel.y = -8.0
    vessel.heading = 33.0
    vessel.state = "stunned"
    vessel._state_t = 1.25
    vessel._hits = 1
    vessel._stun_t = 3.5
    vessel._hit_flash_t = 0.1
    mini_game.run_mgr._compliance_vessels = [vessel]
    mini_game.run_mgr._compliance_spawn_cd = 4.25
    mini_game.run_mgr._emp_burst_available = True
    mini_game.run_mgr._emp_burst_active_t = 0.2

    path = tmp_path / "compliance-run.json"
    save_checkpoint_file(path, mini_game)
    data = load_checkpoint_file(path)
    assert data is not None

    mini_game.run_mgr._compliance_vessels = []
    mini_game.run_mgr._compliance_spawn_cd = 12.0
    mini_game.run_mgr._emp_burst_available = False
    mini_game.run_mgr._emp_burst_active_t = 0.0
    assert restore_checkpoint(mini_game, data) is True

    assert mini_game.run_mgr._compliance_spawn_cd == pytest.approx(4.25)
    assert mini_game.run_mgr._emp_burst_available is True
    assert mini_game.run_mgr._emp_burst_active_t == pytest.approx(0.2)
    assert len(mini_game.run_mgr._compliance_vessels) == 1
    restored = mini_game.run_mgr._compliance_vessels[0]
    assert restored.pos.x == pytest.approx(220.0)
    assert restored.pos.y == pytest.approx(180.0)
    assert restored.vel.x == pytest.approx(12.0)
    assert restored.vel.y == pytest.approx(-8.0)
    assert restored.heading == pytest.approx(33.0)
    assert restored.state == "stunned"
    assert restored._hits == 1
    assert restored._stun_t == pytest.approx(3.5)
