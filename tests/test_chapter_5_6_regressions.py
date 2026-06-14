"""Regression coverage for chapter 5/6 campaign wiring."""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


def _meta_with(tmp_path: Path, chapters_completed: list[int]):
    from roguelite.meta_progression import MetaProgression

    meta = MetaProgression(save_path=tmp_path / "meta.json")
    meta._data["chapters_completed"] = chapters_completed
    return meta


def test_chapter_five_and_six_loadout_preview_renders(tmp_path):
    pygame.init()
    pygame.font.init()

    from roguelite.loadout_draft import LoadoutDraft

    surface = pygame.Surface((1280, 720))
    for chapter in (5, 6):
        draft = LoadoutDraft(chapter=chapter)
        draft.render(surface)


def test_interstitial_advances_after_chapter_four_and_ends_after_six():
    from core.game import Game
    from core.state_manager import GameState

    game = Game.__new__(Game)
    game._goto = lambda state: setattr(game, "_last_state", state)

    game._delivery_chapter = 4
    game.meta = SimpleNamespace(chapters_completed=[1, 2, 3, 4])
    Game._enter_interstitial(game)
    assert game._interstitial_campaign_end is False
    assert game._interstitial_next == 5
    assert game._last_state == GameState.INTERSTITIAL

    game._delivery_chapter = 6
    game.meta = SimpleNamespace(chapters_completed=[1, 2, 3, 4, 5, 6])
    Game._enter_interstitial(game)
    assert game._interstitial_campaign_end is True


def test_chapter_six_run_starts_with_emp_after_chapter_five_clear(tmp_path):
    pygame.init()
    pygame.font.init()

    from roguelite.run_manager import RunManager
    from ship.ship import PlayerShip

    meta = _meta_with(tmp_path, [1, 2, 3, 4, 5])
    rm = RunManager(meta)
    rm.start_run(PlayerShip())

    assert rm._current_chapter() == 6
    assert rm._emp_burst_available is True


def test_encrypted_drive_and_emp_checkpoint_round_trip(tmp_path):
    pygame.init()
    pygame.font.init()

    from cargo.encrypted_drive import EncryptedDrive
    from core.state_manager import GameState, StateManager
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_checkpoint import build_checkpoint, restore_checkpoint
    from roguelite.run_manager import RunManager
    from ship.ship import PlayerShip

    meta = MetaProgression(save_path=tmp_path / "meta.json")
    rm = RunManager(meta)
    ship = PlayerShip()
    rm.start_run(ship)
    rm.apply_draft(ship)

    drive = EncryptedDrive()
    drive.trace_level = 0.75
    drive._ping_t = 4.5
    ship.cargo = drive
    rm._emp_burst_available = True
    rm._emp_burst_active_t = 0.2
    rm._compliance_spawn_cd = 3.0

    states = StateManager()
    states._state = GameState.FLIGHT
    data = build_checkpoint(SimpleNamespace(
        run_mgr=rm,
        ship=ship,
        states=states,
        _state_before_pause=None,
    ))

    rm2 = RunManager(meta)
    ship2 = PlayerShip()
    assert restore_checkpoint(SimpleNamespace(run_mgr=rm2, ship=ship2), data)

    assert type(ship2.cargo).__name__ == "EncryptedDrive"
    assert ship2.cargo.trace_level == 0.75
    assert ship2.cargo._ping_t == 4.5
    assert rm2._emp_burst_available is True
    assert rm2._emp_burst_active_t == 0.2
    assert rm2._compliance_spawn_cd == 3.0
