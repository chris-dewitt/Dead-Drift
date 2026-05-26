"""Aliveness hotfix  RunManager must be safe to update() from any
construction path.

Bug: launching the game with an existing mid-run checkpoint crashed on
first frame because `RunManager.update()` references `_run_total_time`,
but that field was only initialised by `start_run()`. Checkpoint
restore bypasses `start_run()` and goes straight to FLIGHT, so the
attribute was missing.

This test pins the contract that every field `update()` reads must
exist on the instance from `__init__` alone."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path
from types import SimpleNamespace

import pygame


# Every attribute `update()` reads outside the `_sector is None`
# early-return guard.
_REQUIRED_ATTRS = [
    "_t",
    "_sector",
    "_ship",
    "_sector_timer",
    "_sector_dur",
    "_sector_index",
    "_run_total_time",
    "_sling_cd",
    "_prox_cd",
    "_flash_t",
    "_close_call_cd",
    "_close_witness",
    "_barge_pursuit_t",
    "_barge_suppression_t",
    "_long_fight_emitted",
    "_harm_session_t",
    "_pending_terminal",
    "_terminal_arm_t",
    "_last_voice_char_t",
]


def _test_file(name: str) -> Path:
    path = Path("data/saves") / f"test_run_manager_boot_attrs_{name}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    return path


def _build_fresh_run_manager():
    pygame.init()
    pygame.font.init()
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager
    meta = MetaProgression(save_path=_test_file("meta.json"))
    rm = RunManager(meta)
    return rm


def test_run_manager_has_every_required_attr_after_init():
    rm = _build_fresh_run_manager()
    missing = [a for a in _REQUIRED_ATTRS if not hasattr(rm, a)]
    assert not missing, (
        f"RunManager.__init__ is missing fields update() reads: "
        f"{missing}. Boot from checkpoint will crash on first frame."
    )


def test_run_manager_update_safe_with_no_sector():
    """`update()` should no-op when no run is active  no crash."""
    rm = _build_fresh_run_manager()
    rm.update(0.016)   # must not raise


def test_run_manager_update_safe_with_sector_but_no_start_run():
    """If something bypasses `start_run()` and sets _sector + _ship
    directly (the way checkpoint restore does), update() must still
    work. This is the actual hotfix scenario."""
    rm = _build_fresh_run_manager()
    from ship.ship import PlayerShip
    from roguelite.procedural import generate_sector
    import random as rnd

    # Fake what restore_checkpoint does  set up _sector + _ship
    # WITHOUT calling start_run(). Uses a real procedural sector so
    # gravity / hazard reads inside update() find their attributes.
    rm._ship = PlayerShip()
    rm._sector = generate_sector(0, 1.0, rng=rnd.Random(1), chapter=1)
    # If `_run_total_time` ever regresses, this raises AttributeError.
    rm.update(0.016)
    assert rm._run_total_time >= 0.016


def test_checkpoint_round_trip_preserves_run_total_time():
    """The hotfix added _run_total_time to checkpoint persistence so
    a resumed hardcore run keeps its accumulated flight seconds."""
    from roguelite.run_checkpoint import (
        save_checkpoint_file, load_checkpoint_file, restore_checkpoint,
    )
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager
    from ship.ship import PlayerShip
    from core.state_manager import StateManager, GameState

    pygame.init()
    pygame.font.init()

    meta_path = _test_file("checkpoint_meta.json")
    chk_path = _test_file("checkpoint.json")
    meta = MetaProgression(save_path=meta_path)
    rm = RunManager(meta)
    ship = PlayerShip()
    rm.start_run(ship)
    rm._run_total_time = 42.5
    rm._kress_tip_pending = True
    rm._barge_suppression_t = 12.5

    # Build a minimal Game-shaped object for the helper.
    states = StateManager()
    states._state = GameState.FLIGHT
    game_stub = SimpleNamespace(
        run_mgr=rm, ship=ship, states=states,
        _state_before_pause=None,
    )

    save_checkpoint_file(chk_path, game_stub)
    data = load_checkpoint_file(chk_path)
    assert data is not None
    # Round-trip into a fresh RunManager.
    meta2 = MetaProgression(save_path=meta_path)
    rm2 = RunManager(meta2)
    ship2 = PlayerShip()
    game_stub2 = SimpleNamespace(
        run_mgr=rm2, ship=ship2, states=StateManager(),
        _state_before_pause=None,
    )
    restore_checkpoint(game_stub2, data)
    assert rm2._run_total_time == 42.5
    assert rm2._kress_tip_pending is True
    assert rm2._barge_suppression_t == 12.5
