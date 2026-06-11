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


def test_checkpoint_preserves_recent_mutable_gameplay_state(mini_game):
    from antagonists.wreck import SpaceWreck
    from cargo.encrypted_drive import EncryptedDrive
    from physics.body import Vec2
    from ship.gun import Bullet

    drive = EncryptedDrive()
    drive.trace_level = 0.75
    drive._ping_t = 4.25
    mini_game.ship.cargo = drive
    mini_game.ship.fuel = 37.5
    mini_game.ship.gun.fire_rate_mult = 1.6
    mini_game.ship.gun.damage_mult = 2
    bullet = Bullet(Vec2(12, 34), 45, damage=2)
    bullet.lifetime = 0.9
    mini_game.ship.gun.bullets.append(bullet)

    wreck = SpaceWreck(222, 333, subtype=SpaceWreck.SUBTYPE_INTERACTIVE)
    wreck.angle = 17.0
    wreck.rot_speed = -1.25
    wreck.length = 180
    wreck.width = 62
    wreck.gap_frac = 0.42
    wreck.weak_hp = 1
    wreck.is_triggered = True
    wreck._trigger_t = 2.4
    mini_game.run_mgr._wrecks.append(wreck)
    mini_game.run_mgr._compliance_spawn_cd = 5.5
    mini_game.run_mgr._emp_burst_available = True
    mini_game.run_mgr._emp_burst_active_t = 0.2

    data = build_checkpoint(mini_game)

    mini_game.ship.cargo = None
    mini_game.ship.fuel = S.FUEL_MAX
    mini_game.ship.gun.fire_rate_mult = 1.0
    mini_game.ship.gun.damage_mult = 1
    mini_game.ship.gun.bullets.clear()
    mini_game.run_mgr._wrecks.clear()
    mini_game.run_mgr._compliance_spawn_cd = 12.0
    mini_game.run_mgr._emp_burst_available = False
    mini_game.run_mgr._emp_burst_active_t = 0.0

    assert restore_checkpoint(mini_game, data) is True
    assert type(mini_game.ship.cargo).__name__ == "EncryptedDrive"
    assert mini_game.ship.cargo.trace_level == pytest.approx(0.75)
    assert mini_game.ship.cargo._ping_t == pytest.approx(4.25)
    assert mini_game.ship.fuel == pytest.approx(37.5)
    assert mini_game.ship.gun.fire_rate_mult == pytest.approx(1.6)
    assert mini_game.ship.gun.damage_mult == 2
    assert mini_game.ship.gun.bullets[0].damage == 2
    restored_wreck = mini_game.run_mgr._wrecks[0]
    assert restored_wreck.subtype == SpaceWreck.SUBTYPE_INTERACTIVE
    assert restored_wreck.angle == pytest.approx(17.0)
    assert restored_wreck.rot_speed == pytest.approx(-1.25)
    assert restored_wreck.length == 180
    assert restored_wreck.width == 62
    assert restored_wreck.gap_frac == pytest.approx(0.42)
    assert restored_wreck.weak_hp == 1
    assert restored_wreck.is_triggered is True
    assert restored_wreck._trigger_t == pytest.approx(2.4)
    assert mini_game.run_mgr._compliance_spawn_cd == pytest.approx(5.5)
    assert mini_game.run_mgr._emp_burst_available is True
    assert mini_game.run_mgr._emp_burst_active_t == pytest.approx(0.2)
