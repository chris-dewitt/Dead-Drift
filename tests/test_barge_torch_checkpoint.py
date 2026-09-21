"""Regression: TORCH without a tether must not melt modules after resume."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from antagonists.repo_barge import BargeState, RepoBarge
from physics.body import Vec2
from physics.tether import Tether
from roguelite.run_checkpoint import _barge_dict, _barge_from, build_checkpoint, restore_checkpoint
from ship.ship import PlayerShip


def _active_ship() -> PlayerShip:
    ship = PlayerShip()
    for mod in ship.chain.slots:
        if mod is not None:
            mod.active = True
    ship.chain._rebalance()
    return ship


def test_torch_without_tether_does_not_unbolt_modules():
    """Checkpoint restore drops tether; TORCH must not remote-melt loadout."""
    rm = MagicMock()
    rm.meta = None
    ship = _active_ship()
    ship.body.pos = Vec2(3000.0, 3000.0)
    rm._ship = ship

    barge = RepoBarge(100.0, 100.0, rm)
    barge.state = BargeState.TORCH
    barge._tether = None
    barge._torch_cd = 0.0

    before = [m.integrity for m in ship.chain.slots if m is not None]
    for _ in range(160):  # 16s — several torch intervals
        barge.update(0.1)
    after = [m.integrity for m in ship.chain.slots if m is not None]

    assert barge.state == BargeState.PATROL
    assert after == before


def test_barge_from_demotes_tether_dependent_states():
    rm = MagicMock()
    rm.meta = None
    for state in (BargeState.TORCH, BargeState.CLAMP, BargeState.INTERCEPT):
        src = RepoBarge(10.0, 20.0, rm)
        src.state = state
        src._tether = Tether(PlayerShip().body, src.body.pos, barge_ref=src)
        restored = _barge_from(_barge_dict(src), rm)
        assert restored.state == BargeState.PATROL
        assert restored._tether is None


# --- full checkpoint path ---

@pytest.fixture
def mini_game(tmp_path, monkeypatch):
    from config import settings as S
    from core.state_manager import GameState
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager

    monkeypatch.setattr(S, "SAVES_DIR", str(tmp_path / "saves"))
    monkeypatch.setattr(S, "MANIFEST_FILE", str(tmp_path / "saves/manifest.json"))

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


def test_checkpoint_restored_torch_barge_stops_torching(mini_game):
    rm = mini_game.run_mgr
    ship = mini_game.ship
    for mod in ship.chain.slots:
        if mod is not None:
            mod.active = True
    ship.chain._rebalance()
    ship.body.pos = Vec2(2800.0, 2800.0)

    barge = RepoBarge(120.0, 140.0, rm)
    barge.state = BargeState.TORCH
    barge._tether = Tether(ship.body, barge.body.pos, barge_ref=barge)
    barge._torch_cd = 0.0
    rm._barges = [barge]

    data = build_checkpoint(mini_game)
    assert any(e.get("t") == "barge" and e.get("state") == "torch" for e in data["entities"])

    rm._barges = []
    assert restore_checkpoint(mini_game, data) is True
    assert len(rm._barges) == 1
    restored = rm._barges[0]
    assert restored.state == BargeState.PATROL
    assert restored._tether is None

    before = [m.integrity for m in ship.chain.slots if m is not None]
    for _ in range(160):
        restored.update(0.1)
    after = [m.integrity for m in ship.chain.slots if m is not None]
    assert after == before
