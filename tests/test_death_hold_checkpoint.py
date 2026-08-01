"""Death-hold Save & Quit must not softlock RESUME RUN.

Concrete trigger (pre-fix): die → during the 0.9s death flash (still FLIGHT)
press ESC/1 → Save & Quit → RESUME RUN. Checkpoint restored ship._destroyed=True
with _death_hold_t=0 and no second EVT_SHIP_DESTROYED, so DECANTING never
started and the ship ignored input forever.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from config import settings as S
from core.state_manager import GameState
from roguelite.run_checkpoint import build_checkpoint, restore_checkpoint


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


def test_destroyed_ship_checkpoint_routes_to_decanting(mini_game):
    mini_game.ship.hull = 0.0
    mini_game.ship._destroyed = True
    mini_game.states = MagicMock(state=GameState.FLIGHT)

    data = build_checkpoint(mini_game)
    assert data["game_state"] == "DECANTING"
    assert data["ship"]["destroyed"] is True


def test_destroyed_ship_paused_checkpoint_routes_to_decanting(mini_game):
    """Save & Quit from the pause menu still records the pre-pause FLIGHT state."""
    mini_game.ship.hull = 0.0
    mini_game.ship._destroyed = True
    mini_game.states = MagicMock(state=GameState.PAUSED)
    mini_game._state_before_pause = GameState.FLIGHT

    data = build_checkpoint(mini_game)
    assert data["game_state"] == "DECANTING"


def test_restore_destroyed_flight_checkpoint_keeps_destroyed_flag(mini_game):
    """Legacy softlock payloads (FLIGHT + destroyed) still restore the flag."""
    mini_game.ship.hull = 0.0
    mini_game.ship._destroyed = True
    data = build_checkpoint(mini_game)
    # Simulate a pre-fix payload that wrote FLIGHT instead of DECANTING.
    data["game_state"] = "FLIGHT"

    mini_game.ship._destroyed = False
    mini_game.ship.hull = S.HULL_MAX
    assert restore_checkpoint(mini_game, data) is True
    assert mini_game.ship._destroyed is True
    assert mini_game.ship.hull == pytest.approx(0.0)


def test_pause_blocked_during_death_hold():
    from core.game import Game

    game = Game.__new__(Game)
    game._death_hold_t = 0.9
    game.states = MagicMock(state=GameState.FLIGHT)
    game._state_before_pause = None
    game._pause_menu_cursor = 0

    Game._pause_game(game)

    assert game.states.state == GameState.FLIGHT
    assert game._state_before_pause is None


def test_pause_allowed_when_not_in_death_hold():
    from core.game import Game

    class _States:
        def __init__(self):
            self.state = GameState.FLIGHT

        def transition(self, new_state):
            self.state = new_state

    game = Game.__new__(Game)
    game._death_hold_t = 0.0
    game.states = _States()
    game._state_before_pause = None
    game._pause_menu_cursor = 0

    Game._pause_game(game)

    assert game.states.state == GameState.PAUSED
    assert game._state_before_pause == GameState.FLIGHT


def test_continue_routes_destroyed_ship_to_decanting(tmp_path, monkeypatch):
    from core.game import Game
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager
    from roguelite.save_manager import SaveManager
    from ship.ship import PlayerShip

    monkeypatch.setattr(S, "SAVES_DIR", str(tmp_path / "saves"))
    monkeypatch.setattr(S, "MANIFEST_FILE", str(tmp_path / "saves/manifest.json"))
    monkeypatch.setattr(S, "RUN_HISTORY_FILE", str(tmp_path / "run_history.json"))

    meta = MetaProgression(save_path=tmp_path / "meta.json")
    ship = PlayerShip()
    rm = RunManager(meta)
    rm.start_run(ship)
    rm.apply_draft(ship)
    # Death happens mid-run — after draft/loadout has already reset the hull.
    ship.hull = 0.0
    ship._destroyed = True

    save_mgr = SaveManager()
    game = Game.__new__(Game)
    game.save_mgr = save_mgr
    game.meta = meta
    game.ship = ship
    game.run_mgr = rm
    game.states = MagicMock()
    game._run_just_completed = False
    game._decant_from_destroyed_checkpoint = False
    game._shop = None
    game._menu_mode = "main"
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
    game._state_before_pause = None

    # Persist a legacy FLIGHT+destroyed softlock payload, then resume.
    payload_game = MagicMock()
    payload_game.run_mgr = rm
    payload_game.ship = ship
    payload_game.states = MagicMock(state=GameState.FLIGHT)
    payload_game._state_before_pause = None
    payload_game._delivery_chapter = 1
    payload_game._delivery_pending = False
    payload_game._delivery_delay_t = 0.0
    payload_game._delivery = None
    payload_game._terminal_win_hold_t = 0.0
    payload_game._terminal_win_str = ""
    payload_game._interstitial_completed = 1
    payload_game._interstitial_next = 2
    payload_game._interstitial_campaign_end = False
    payload_game._interstitial_t = 0.0
    from roguelite.run_checkpoint import build_checkpoint
    data = build_checkpoint(payload_game)
    assert data["game_state"] == "DECANTING"
    assert data["ship"]["destroyed"] is True
    data["game_state"] = "FLIGHT"  # pre-fix shape
    path = save_mgr.run_checkpoint_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    import json
    path.write_text(json.dumps(data), encoding="utf-8")

    went_to = []
    game._goto = went_to.append
    game._bind_meta_from_active_slot = lambda: None

    Game._continue_from_menu(game)

    assert went_to == [GameState.DECANTING]
    assert game._decant_from_destroyed_checkpoint is True


def test_decanting_enter_deletes_destroyed_checkpoint(tmp_path, monkeypatch):
    from core.game import Game
    from roguelite.save_manager import SaveManager

    monkeypatch.setattr(S, "SAVES_DIR", str(tmp_path / "saves"))
    monkeypatch.setattr(S, "MANIFEST_FILE", str(tmp_path / "saves/manifest.json"))
    monkeypatch.setattr(S, "RUN_HISTORY_FILE", str(tmp_path / "run_history.json"))

    save_mgr = SaveManager()
    ckpt = save_mgr.run_checkpoint_path()
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    ckpt.write_text("{}", encoding="utf-8")
    assert save_mgr.has_run_checkpoint()

    game = Game.__new__(Game)
    game.states = MagicMock(state=GameState.DECANTING)
    game.meta = MagicMock()
    game.save_mgr = save_mgr
    game._decant_from_destroyed_checkpoint = True
    game._menu_mode = "main"
    went_to = []
    game._goto = went_to.append

    import pygame
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    Game._route_keydown(game, event)

    assert not save_mgr.has_run_checkpoint()
    assert game._decant_from_destroyed_checkpoint is False
    assert went_to == [GameState.MAIN_MENU]
    game.meta.save.assert_called_once()
