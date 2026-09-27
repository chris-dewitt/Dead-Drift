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


def test_flight_autosave_persists_debt_before_shop_spend(mini_game, tmp_path, monkeypatch):
    """Closing the window after a checkpoint must not restore credits on a stale ledger.

    pay_off reduces debt in memory only. RESUME used to load the last
    explicit save (difficulty select / Save & Return) while restoring
    _run_debt_reduced. The next shop purchase then add_debt'd on top.
    """
    from core.game import Game
    from roguelite.meta_progression import MetaProgression
    from roguelite.save_manager import SaveManager

    saves = tmp_path / "debt-saves"
    monkeypatch.setattr(S, "SAVES_DIR", str(saves))
    monkeypatch.setattr(S, "MANIFEST_FILE", str(saves / "manifest.json"))
    monkeypatch.setattr(S, "MAX_SAVE_SLOTS", 3)

    mgr = SaveManager()
    slot = mgr.active_save_path()
    meta = MetaProgression(save_path=slot)
    start_debt = meta.debt
    meta.pay_off(20_000, source="SECTOR CLEAR")
    assert meta.debt == start_debt - 20_000

    mini_game.run_mgr.meta = meta
    mini_game.run_mgr._run_debt_reduced = 20_000
    mini_game.meta = meta
    mini_game.save_mgr = mgr

    Game._save_run_checkpoint(mini_game)

    resumed = MetaProgression(save_path=slot)
    assert resumed.debt == start_debt - 20_000
    resumed.add_debt(5_000, source="SHOP: HULL PATCH")
    assert resumed.debt == start_debt - 15_000


def test_meta_save_keeps_previous_slot_if_dump_fails(tmp_path, monkeypatch):
    from roguelite.meta_progression import MetaProgression

    path = tmp_path / "slot.json"
    meta = MetaProgression(save_path=path)
    meta.pay_off(1_000, source="SECTOR CLEAR")
    meta.save()
    good = path.read_text(encoding="utf-8")

    def boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("roguelite.meta_progression.json.dump", boom)
    meta.pay_off(5_000, source="SLINGSHOT")
    with pytest.raises(OSError):
        meta.save()
    assert path.read_text(encoding="utf-8") == good
    reloaded = MetaProgression(save_path=path)
    assert reloaded.debt == meta.debt + 5_000


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
