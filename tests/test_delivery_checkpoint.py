"""A finished run must stay resumable until the delivery payout is saved.

Closing the window during approach or the corridor used to drop the whole
chapter: run-end deleted the checkpoint, and delivery never wrote another.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from config import settings as S
from core.state_manager import GameState
from roguelite.meta_progression import MetaProgression
from roguelite.run_checkpoint import load_checkpoint_file


def _redirect_saves(monkeypatch, tmp_path):
    root = tmp_path / "data"
    saves = root / "saves"
    saves.mkdir(parents=True)
    monkeypatch.setattr(S, "DATA_DIR", str(root))
    monkeypatch.setattr(S, "SAVES_DIR", str(saves))
    monkeypatch.setattr(S, "MANIFEST_FILE", str(saves / "manifest.json"))
    monkeypatch.setattr(S, "RUN_HISTORY_FILE", str(root / "run_history.json"))
    monkeypatch.setattr(S, "BAX_VOCAB_FILE", str(root / "bax_vocabulary.json"))
    monkeypatch.setattr(S, "REPO_LEDGER_FILE", str(root / "repo_ledger.json"))


def _game(monkeypatch, tmp_path):
    _redirect_saves(monkeypatch, tmp_path)
    from core.game import Game

    game = Game()
    game.run_mgr.start_run(game.ship)
    game.run_mgr.apply_draft(game.ship)
    game.run_mgr._run_total_time = 321.5
    game.states.transition(GameState.TERMINAL)
    return game


def test_run_end_keeps_checkpoint_and_persists_the_debt_chunk(monkeypatch, tmp_path):
    game = _game(monkeypatch, tmp_path)
    before = game.meta.debt

    game._on_run_end(success=True)

    assert game._delivery_pending is True
    assert game.save_mgr.has_run_checkpoint()
    data = load_checkpoint_file(game.save_mgr.run_checkpoint_path())
    assert data is not None
    # Still inside the jump terminal when the last sector clears. Resume
    # must come back as the drop-off, not as a flight with nowhere to jump.
    assert data["game_state"] == "DELIVERY"
    assert data["game_flow"]["delivery_pending"] is True
    assert data["run_mgr"]["run_total_time"] == 321.5

    on_disk = MetaProgression(save_path=game.save_mgr.active_save_path())
    assert on_disk.debt == before - 50000


def test_resume_rebuilds_delivery_with_the_flight_clock(monkeypatch, tmp_path):
    game = _game(monkeypatch, tmp_path)
    game._on_run_end(success=True)
    path = game.save_mgr.active_save_path()

    from core.game import Game

    resumed = Game()
    assert resumed.save_mgr.load_run_checkpoint(resumed) is True
    assert resumed._delivery is not None
    assert resumed._delivery._total_time_for_hardcore == 321.5
    assert MetaProgression(save_path=path).debt == resumed.meta.debt


def test_committed_payout_drops_the_checkpoint(monkeypatch, tmp_path):
    game = _game(monkeypatch, tmp_path)
    game._on_run_end(success=True)
    game._delivery_delay_t = 0.0
    game.states.transition(GameState.FLIGHT)
    game._update(0.016)

    assert game.states.state == GameState.DELIVERY
    assert game.save_mgr.has_run_checkpoint()
    assert game._delivery._total_time_for_hardcore == 321.5

    debt_at_dropoff = game.meta.debt
    game._delivery._compute_result()
    assert game._delivery._reward_committed is True
    game._update(0.016)

    assert game.save_mgr.has_run_checkpoint() is False
    # Pause-save during the result card must not write the corridor back.
    game._pause_to_main_menu(save=True)
    assert game.save_mgr.has_run_checkpoint() is False
    assert MetaProgression(save_path=game.save_mgr.active_save_path()).debt == debt_at_dropoff
