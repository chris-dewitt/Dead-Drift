"""Regression coverage for Chapter 5/6 progression wiring."""
from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


def test_loadout_renders_drive_cargo_for_chapters_five_and_six():
    pygame.init()
    pygame.font.init()

    from config import settings as S
    from roguelite.loadout_draft import LoadoutDraft

    surface = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
    for chapter in (5, 6):
        draft = LoadoutDraft(chapter=chapter)
        draft.render(surface)


def test_interstitial_advances_after_chapter_four_and_ends_after_six():
    from core.game import Game
    from core.state_manager import GameState

    seen = []
    game = Game.__new__(Game)
    game._goto = lambda state: seen.append(state)
    game._delivery_chapter = 4
    game.meta = SimpleNamespace(
        chapters_completed=[1, 2, 3, 4],
        campaign_cleared_at_least_once=False,
    )

    Game._enter_interstitial(game)

    assert seen[-1] == GameState.INTERSTITIAL
    assert game._interstitial_next == 5
    assert game._interstitial_campaign_end is False

    game._delivery_chapter = 6
    game.meta = SimpleNamespace(
        chapters_completed=[1, 2, 3, 4, 5, 6],
        campaign_cleared_at_least_once=True,
    )

    Game._enter_interstitial(game)

    assert game._interstitial_next == 7
    assert game._interstitial_campaign_end is True


def test_encrypted_drive_final_terminal_is_chapter_aware():
    from cargo.encrypted_drive import EncryptedDrive
    from config import settings as S
    from roguelite.run_manager import RunManager

    opened = []
    rm = RunManager.__new__(RunManager)
    rm._sector_index = S.SECTORS_PER_RUN - 1
    rm._ship = SimpleNamespace(cargo=EncryptedDrive())
    rm._ensure_faction_hull = lambda npc_type: None
    rm.open_terminal = lambda npc_type: opened.append(npc_type)
    rm._pending_advance = False

    rm._current_chapter = lambda: 5
    RunManager._open_jump_terminal(rm)
    assert opened[-1] == "chen"

    rm._current_chapter = lambda: 6
    RunManager._open_jump_terminal(rm)
    assert opened[-1] == "bowen"
