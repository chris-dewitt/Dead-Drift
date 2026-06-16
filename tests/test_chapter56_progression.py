"""Regression coverage for Chapter 5/6 campaign progression."""
from __future__ import annotations

from types import SimpleNamespace


def _game_stub(completed_chapter: int, completed: list[int]):
    from core.game import Game

    game = Game.__new__(Game)
    game._delivery_chapter = completed_chapter
    game.meta = SimpleNamespace(chapters_completed=completed)
    game._goto = lambda state: None
    return game


def test_chapter_four_interstitial_advances_to_chapter_five():
    from core.game import Game

    game = _game_stub(4, [1, 2, 3, 4])
    Game._enter_interstitial(game)

    assert game._interstitial_next == 5
    assert game._interstitial_campaign_end is False


def test_chapter_six_interstitial_marks_campaign_complete():
    from core.game import Game

    game = _game_stub(6, [1, 2, 3, 4, 5, 6])
    Game._enter_interstitial(game)

    assert game._interstitial_next == 7
    assert game._interstitial_campaign_end is True


def test_chapter_five_final_terminal_uses_chen_not_drive_default():
    from config import settings as S
    from roguelite.run_manager import RunManager

    opened = {}
    rm = RunManager.__new__(RunManager)
    rm._sector_index = S.SECTORS_PER_RUN - 1
    rm._current_chapter = lambda: 5
    rm._ship = SimpleNamespace(
        cargo=SimpleNamespace(terminal_climax=lambda: "bowen")
    )
    rm.open_terminal = lambda npc_type: opened.setdefault("npc_type", npc_type)

    RunManager._open_jump_terminal(rm)

    assert opened["npc_type"] == "chen"
