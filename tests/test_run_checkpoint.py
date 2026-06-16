"""Round-trip tests for mid-run checkpoint serialization."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
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


def test_encrypted_drive_compliance_and_emp_roundtrip(mini_game, tmp_path):
    from antagonists.compliance_vessel import ComplianceVessel
    from cargo.encrypted_drive import EncryptedDrive
    from physics.body import Vec2
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager
    from ship.ship import PlayerShip

    drive = EncryptedDrive()
    drive.trace_level = 0.75
    drive._ping_t = 8.5
    mini_game.ship.cargo = drive
    mini_game.run_mgr._chapter_override = 5
    mini_game.run_mgr._compliance_spawn_cd = 3.25
    mini_game.run_mgr._emp_burst_available = True
    mini_game.run_mgr._emp_burst_active_t = 0.2

    vessel = ComplianceVessel(123.0, 234.0, mini_game.run_mgr)
    vessel.vel = Vec2(11.0, -7.0)
    vessel.state = "stunned"
    vessel._state_t = 1.5
    vessel._hits = 1
    vessel._stun_t = 4.0
    vessel._hit_flash_t = 0.1
    vessel.heading = 42.0
    mini_game.run_mgr._compliance_vessels = [vessel]

    data = build_checkpoint(mini_game)
    assert data["ship"]["cargo"]["type"] == "EncryptedDrive"
    assert any(e["t"] == "compliance_vessel" for e in data["entities"])

    meta2 = MetaProgression(save_path=tmp_path / "meta2.json")
    rm2 = RunManager(meta2)
    ship2 = PlayerShip()
    game2 = SimpleNamespace(
        run_mgr=rm2,
        ship=ship2,
        states=MagicMock(state=GameState.FLIGHT),
        _state_before_pause=None,
    )

    assert restore_checkpoint(game2, data) is True
    assert isinstance(ship2.cargo, EncryptedDrive)
    assert ship2.cargo.trace_level == pytest.approx(0.75)
    assert ship2.cargo._ping_t == pytest.approx(8.5)
    assert rm2._current_chapter() == 5
    assert rm2._compliance_spawn_cd == pytest.approx(3.25)
    assert rm2._emp_burst_available is True
    assert rm2._emp_burst_active_t == pytest.approx(0.2)
    assert len(rm2._compliance_vessels) == 1
    restored = rm2._compliance_vessels[0]
    assert restored.pos.x == pytest.approx(123.0)
    assert restored.pos.y == pytest.approx(234.0)
    assert restored.vel.x == pytest.approx(11.0)
    assert restored.vel.y == pytest.approx(-7.0)
    assert restored.state == "stunned"
    assert restored._hits == 1
    assert restored._stun_t == pytest.approx(4.0)
    assert restored.run_mgr is rm2


@pytest.mark.parametrize("paused_state", [
    GameState.TERMINAL,
    GameState.DELIVERY,
    GameState.INTERSTITIAL,
])
def test_non_reconstructable_pause_states_resume_to_flight(mini_game, paused_state):
    mini_game.states = MagicMock(state=GameState.PAUSED)
    mini_game._state_before_pause = paused_state

    data = build_checkpoint(mini_game)

    assert data["game_state"] == "FLIGHT"
