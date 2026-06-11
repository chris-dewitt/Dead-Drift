"""Regression coverage for chapter 5/6 progression and compliance vessels."""

from __future__ import annotations

from types import SimpleNamespace


def test_chapter_four_interstitial_advances_to_chapter_five():
    from core.game import Game
    from core.state_manager import GameState

    game = Game.__new__(Game)
    game._delivery_chapter = 4
    game.meta = SimpleNamespace(chapters_completed=[1, 2, 3, 4])
    game._goto = lambda state: setattr(game, "_next_state", state)

    Game._enter_interstitial(game)

    assert game._interstitial_next == 5
    assert game._interstitial_campaign_end is False
    assert game._next_state is GameState.INTERSTITIAL


def test_chapter_six_interstitial_ends_campaign():
    from core.game import Game

    game = Game.__new__(Game)
    game._delivery_chapter = 6
    game.meta = SimpleNamespace(chapters_completed=[1, 2, 3, 4, 5, 6])
    game._goto = lambda state: setattr(game, "_next_state", state)

    Game._enter_interstitial(game)

    assert game._interstitial_campaign_end is True


def test_compliance_vessel_destroyed_event_is_not_treated_as_pirate():
    from roguelite.run_manager import RunManager

    ship_without_pirate_flag = object()

    RunManager._on_aiship_destroyed(None, ship=ship_without_pirate_flag)
