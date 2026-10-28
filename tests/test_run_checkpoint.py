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


class _DeliveryPhase:
    PHASE_RESULT = "result"

    def __init__(self, phase: str):
        self._phase = phase


def _pause_during_delivery(mini_game, phase: str, chapter: int):
    mini_game.states.state = GameState.PAUSED
    mini_game._state_before_pause = GameState.DELIVERY
    mini_game._delivery = _DeliveryPhase(phase)
    mini_game._delivery_chapter = chapter
    # Stale interstitial fields from an earlier chapter must not leak.
    mini_game._interstitial_completed = 1
    mini_game._interstitial_next = 2
    mini_game._interstitial_campaign_end = False
    mini_game._interstitial_t = 0.0


def test_pause_on_result_card_does_not_replay_payout(mini_game, monkeypatch):
    """Corridor payout is already in the campaign save when the result
    card is up. Resuming that pause must not start delivery over."""
    meta = mini_game.run_mgr.meta
    meta._data["debt"] = 40_000
    meta.pay_off(8_000, source="DELIVERY PAYOUT")
    meta.complete_chapter(1)
    assert meta.debt == 32_000

    _pause_during_delivery(mini_game, "result", 1)
    data = build_checkpoint(mini_game)

    assert data["game_state"] == "INTERSTITIAL"
    flow = data["game_flow"]
    assert flow["delivery_chapter"] == 1
    assert flow["delivery_pending"] is False
    assert flow["interstitial_completed"] == 1
    assert flow["interstitial_next"] == 2
    assert flow["interstitial_campaign_end"] is False
    assert flow["interstitial_t"] == 11.0

    def _boom(*_a, **_k):
        raise AssertionError("settled delivery must not construct a new sequence")

    monkeypatch.setattr(
        "delivery.delivery_sequence.DeliverySequence", _boom
    )
    assert restore_checkpoint(mini_game, data) is True
    assert mini_game._delivery is None
    assert meta.debt == 32_000
    assert mini_game._interstitial_completed == 1
    assert mini_game._interstitial_next == 2
    assert mini_game._interstitial_campaign_end is False
    assert mini_game._interstitial_t == 11.0


def test_pause_on_chapter_six_result_is_campaign_end(mini_game):
    _pause_during_delivery(mini_game, "result", 6)
    data = build_checkpoint(mini_game)
    flow = data["game_flow"]
    assert data["game_state"] == "INTERSTITIAL"
    assert flow["interstitial_completed"] == 6
    assert flow["interstitial_next"] == 7
    assert flow["interstitial_campaign_end"] is True


def test_pause_mid_corridor_still_resumes_delivery(mini_game):
    """Payout has not been applied yet — resume still restarts delivery."""
    meta = mini_game.run_mgr.meta
    meta._data["debt"] = 40_000
    _pause_during_delivery(mini_game, "run", 3)
    data = build_checkpoint(mini_game)
    assert data["game_state"] == "DELIVERY"

    assert restore_checkpoint(mini_game, data) is True
    from delivery.delivery_sequence import DeliverySequence
    assert isinstance(mini_game._delivery, DeliverySequence)
    assert mini_game._delivery._phase == DeliverySequence.PHASE_APPROACH
    assert meta.debt == 40_000
