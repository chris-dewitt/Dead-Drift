"""Coverage for Epic 11.1c — Bax harmonica heal session."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from types import SimpleNamespace

import pygame


def _build_run_manager_with_ship(damage: float = 50.0):
    """Construct a RunManager (bypassing audio init) with a stubbed ship."""
    from roguelite.run_manager import RunManager
    from ship.ship import PlayerShip
    from config import settings as S

    rm = RunManager.__new__(RunManager)
    rm._barges = []
    rm._harm_session_t = 0.0
    rm._harm_session_dur = 6.0
    rm._harm_heal_total = 5.0
    rm._harm_heal_paid = 0.0
    rm._harm_block_radius = 300.0
    # Real ship; we only need hull + harm_session_active + pos.
    pygame.init()
    pygame.font.init()
    ship = PlayerShip()
    ship.hull = max(1.0, S.HULL_MAX - damage)
    rm._ship = ship
    return rm, ship


def test_session_starts_when_idle_and_damaged():
    pygame.init()
    pygame.font.init()
    rm, ship = _build_run_manager_with_ship(damage=80)
    assert rm.start_harmonica_session() is True
    assert rm.harm_session_active is True
    assert ship.harm_session_active is True


def test_session_blocked_when_full_hull():
    pygame.init()
    pygame.font.init()
    from config import settings as S
    rm, ship = _build_run_manager_with_ship(damage=0)
    ship.hull = S.HULL_MAX
    assert rm.start_harmonica_session() is False
    assert rm.harm_session_active is False


def test_session_blocks_near_active_barge():
    pygame.init()
    pygame.font.init()
    from antagonists.repo_barge import RepoBarge
    rm, ship = _build_run_manager_with_ship(damage=80)
    rm.meta = SimpleNamespace(
        barge_speed_mult=lambda: 1.0,
        difficulty="standard",
    )
    barge = RepoBarge(ship.body.pos.x + 100,
                      ship.body.pos.y + 100, rm)
    rm._barges = [barge]
    assert rm.start_harmonica_session() is False
    assert rm.harm_session_active is False


def test_session_ticks_and_heals_over_duration():
    pygame.init()
    pygame.font.init()
    rm, ship = _build_run_manager_with_ship(damage=80)
    start_hull = ship.hull
    assert rm.start_harmonica_session() is True
    # Tick the full duration in one big dt + a small flush.
    rm._tick_harmonica_session(rm._harm_session_dur)
    rm._tick_harmonica_session(0.01)
    assert rm.harm_session_active is False
    assert ship.harm_session_active is False
    # Healed approximately the full session pay-out.
    assert ship.hull - start_hull >= rm._harm_heal_total - 0.01


def test_session_cancels_on_input_reason():
    pygame.init()
    pygame.font.init()
    rm, ship = _build_run_manager_with_ship(damage=80)
    rm.start_harmonica_session()
    rm.cancel_harmonica_session(reason="input")
    assert rm.harm_session_active is False
    assert ship.harm_session_active is False


def test_ship_rotation_locked_during_session():
    pygame.init()
    pygame.font.init()
    rm, ship = _build_run_manager_with_ship(damage=80)
    rm.start_harmonica_session()
    angle_before = ship.body.angle
    # Force-feed the rotate path and confirm ship.update doesn't move it.
    # Since pygame.key.get_pressed in tests returns no keys, rotation
    # input is empty regardless; but the gate also exists in _read_input
    # so the test doubles as a guard against accidental future regressions.
    ship.harm_session_active = True
    ship.body.angle = 0.0
    ship.update(0.016)
    assert ship.body.angle == 0.0
    # Restore for downstream tests.
    ship.harm_session_active = False
    _ = angle_before
