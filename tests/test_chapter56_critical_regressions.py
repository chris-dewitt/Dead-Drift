"""Critical regressions around the Chapter 5/6 expansion."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from config import settings as S
from core.state_manager import GameState


def _meta_with(temp_dir, **overrides):
    from roguelite.meta_progression import MetaProgression

    save_path = Path(temp_dir) / "meta.json"
    meta = MetaProgression(save_path=save_path)
    for key, value in overrides.items():
        meta._data[key] = value
    return meta


def test_loadout_renders_chapter_five_and_six_cargo_choices():
    pygame.init()
    pygame.font.init()

    from roguelite.loadout_draft import LoadoutDraft

    screen = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
    for chapter in (5, 6):
        draft = LoadoutDraft(chapter=chapter)
        for pos, cargo_idx in enumerate(draft._cargo_idx):
            if cargo_idx in (4, 5):
                draft._selected[2] = pos
                draft.render(screen)
                return

    raise AssertionError("Chapter 5/6 draft did not include drive cargo")


def test_final_chapter_five_and_six_route_to_distinct_climax_npcs():
    from roguelite.run_manager import RunManager
    from cargo.encrypted_drive import EncryptedDrive

    def selected_npc_for(chapter: int, completed: list[int]) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            rm = RunManager.__new__(RunManager)
            rm.meta = _meta_with(tmp, chapters_completed=completed)
            rm._chapter_override = None
            rm._sector_index = S.SECTORS_PER_RUN - 1
            rm._ship = SimpleNamespace(cargo=EncryptedDrive())
            rm._pending_advance = False
            rm._ai_ships = []
            rm._ensure_faction_hull = lambda _npc_type: None
            seen: list[str] = []
            rm.open_terminal = lambda npc_type: seen.append(npc_type)
            assert rm._current_chapter() == chapter
            RunManager._open_jump_terminal(rm)
            return seen[-1]

    assert selected_npc_for(5, [1, 2, 3, 4]) == "chen"
    assert selected_npc_for(6, [1, 2, 3, 4, 5]) == "bowen"


def test_chapter_six_start_arms_emp_after_chapter_five_clear():
    pygame.init()
    pygame.font.init()

    from roguelite.run_manager import RunManager
    from ship.ship import PlayerShip

    with tempfile.TemporaryDirectory() as tmp:
        meta = _meta_with(tmp, chapters_completed=[1, 2, 3, 4, 5])
        rm = RunManager(meta)
        rm.start_run(PlayerShip())

    assert rm._current_chapter() == 6
    assert rm.emp_burst_available is True


def test_chapter_four_interstitial_no_longer_ends_campaign():
    from core.game import Game

    game = Game.__new__(Game)
    game._delivery_chapter = 4
    game.meta = SimpleNamespace(chapters_completed=[1, 2, 3, 4])
    game._goto = lambda state: setattr(game, "_last_goto", state)

    Game._enter_interstitial(game)

    assert game._interstitial_next == 5
    assert game._interstitial_campaign_end is False
    assert game._last_goto == GameState.INTERSTITIAL


def test_terminal_checkpoint_resumes_to_flight_not_blank_terminal():
    from roguelite.run_checkpoint import build_checkpoint
    from roguelite.run_manager import RunManager
    from ship.ship import PlayerShip

    with tempfile.TemporaryDirectory() as tmp:
        meta = _meta_with(tmp)
        rm = RunManager(meta)
        ship = PlayerShip()
        rm.start_run(ship)
        rm.apply_draft(ship)
        states = SimpleNamespace(state=GameState.PAUSED)
        game = SimpleNamespace(
            run_mgr=rm,
            ship=ship,
            states=states,
            _state_before_pause=GameState.TERMINAL,
        )

        data = build_checkpoint(game)

    assert data["game_state"] == "FLIGHT"
