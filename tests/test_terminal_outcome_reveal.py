from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


class _ScriptedNPC:
    def __init__(self, outcome: str):
        from terminal.npcs.base_npc import BaseNPC

        class Scripted(BaseNPC):
            def __init__(self, scripted_outcome: str):
                super().__init__("TEST NPC", patience=2)
                self._scripted_outcome = scripted_outcome

            def _intro_line(self) -> str:
                return "test channel open"

            def _evaluate(self, parsed):
                return self._scripted_outcome, "test outcome line"

            def exploits(self) -> dict[str, str]:
                return {}

        self.instance = Scripted(outcome)


@pytest.mark.parametrize("outcome", ["release", "exploit", "impound"])
def test_terminal_outcome_banner_draws_for_all_terminal_outcomes(outcome: str):
    import pygame
    from terminal.terminal import Terminal

    pygame.init()
    terminal = Terminal(_ScriptedNPC(outcome).instance)
    terminal._input = "go"
    terminal._submit()

    surface = pygame.Surface((960, 540))
    terminal.draw(surface)

    assert terminal.is_done
    assert terminal.outcome == outcome
    assert terminal._outcome_t is not None
    assert surface.get_at((480, 270))[:3] != (10, 22, 14)


def test_game_holds_impound_terminal_outcome_before_completing():
    from core.game import Game
    from terminal.npcs.base_npc import NPCOutcome

    game = Game.__new__(Game)
    game._terminal_win_hold_t = 0.0
    game._terminal_win_str = ""

    assert game._start_terminal_outcome_hold(NPCOutcome.IMPOUND)
    assert game._terminal_win_str == "TERMINAL TERMINATED"
    assert 1.0 <= game._terminal_win_hold_t <= 2.0


def test_completed_terminal_cannot_pause_before_outcome_is_applied():
    from core.game import Game
    from core.state_manager import GameState

    transition = MagicMock()
    game = Game.__new__(Game)
    game.states = SimpleNamespace(state=GameState.TERMINAL, transition=transition)
    game.run_mgr = SimpleNamespace(active_terminal=SimpleNamespace(is_done=True))
    game._state_before_pause = None

    game._pause_game()

    transition.assert_not_called()
    assert game._state_before_pause is None


def test_in_progress_terminal_remains_pauseable():
    from core.game import Game
    from core.state_manager import GameState

    transition = MagicMock()
    game = Game.__new__(Game)
    game.states = SimpleNamespace(state=GameState.TERMINAL, transition=transition)
    game.run_mgr = SimpleNamespace(active_terminal=SimpleNamespace(is_done=False))
    game._state_before_pause = None

    game._pause_game()

    transition.assert_called_once_with(GameState.PAUSED)
    assert game._state_before_pause == GameState.TERMINAL

