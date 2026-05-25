"""Aliveness A.2 — Ch.2 shroom control inversion reliability.

Playtest (Chris, May 2026) reported the periodic control inversion wasn't
firing in flight. The cargo logic worked in isolation, but the first
trigger window of `random.uniform(10, 20)` overlapped the 20s sector
jump window — about half of all runs lost their first inversion to the
terminal opening on top of it. These tests pin the fix:

  1. First trigger lands inside the first sector (SPORE_FIRST_TRIGGER_*).
  2. Telegraph flags fire on enter + clear so the renderer can flash.
  3. force_clear_inversion() drops a stale flag at run-end / delivery.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import random
import pygame


def test_first_trigger_lands_inside_first_sector_window_every_seed():
    """Every seed should produce a first inversion before the 20s jump.

    Loops 500 fresh cargos to span the random distribution. With the
    new SPORE_FIRST_TRIGGER_MIN/MAX of 6..9 s, _every_ first trigger
    must fall comfortably inside the 20s jump-ready window."""
    pygame.init()
    from cargo.epi_shrooms import EpistemologicalShrooms
    from config import settings as S

    earliest = 999.0
    latest   = 0.0
    for seed in range(500):
        random.seed(seed)
        cargo = EpistemologicalShrooms()
        first_cd = cargo._next_cd
        assert S.SPORE_FIRST_TRIGGER_MIN <= first_cd <= S.SPORE_FIRST_TRIGGER_MAX, \
            f"seed {seed}: first _next_cd {first_cd:.2f} outside window"
        earliest = min(earliest, first_cd)
        latest   = max(latest,   first_cd)

    # Window must give the player time to settle, but fire BEFORE the 20s
    # jump-ready window opens.
    assert earliest >= 4.0, f"earliest first trigger too tight: {earliest:.2f}s"
    assert latest <= 15.0, f"latest first trigger too late: {latest:.2f}s"
    assert latest <= S.SPORE_FIRST_TRIGGER_MAX, \
        f"distribution leaked past max: {latest:.2f}s"


def test_first_inversion_telegraph_flag_fires_on_enter():
    pygame.init()
    from cargo.epi_shrooms import EpistemologicalShrooms
    from ship.ship import PlayerShip

    pygame.font.init()
    ship = PlayerShip()
    ship.cargo = EpistemologicalShrooms()
    ship.cargo._next_cd = 0.05    # force imminent fire
    assert ship.cargo._just_triggered_t == 0.0

    ship.cargo.update(0.06, ship)
    assert ship.cargo._invert_active is True
    assert ship.controls_inverted is True
    # Telegraph flag set so renderer can flash a short burst.
    assert ship.cargo._just_triggered_t > 0.0


def test_clear_telegraph_flag_fires_on_exit():
    pygame.init()
    pygame.font.init()
    from cargo.epi_shrooms import EpistemologicalShrooms
    from ship.ship import PlayerShip

    ship = PlayerShip()
    ship.cargo = EpistemologicalShrooms()
    ship.cargo._next_cd = 0.05
    ship.cargo.update(0.06, ship)
    # Run out the full inversion duration.
    ship.cargo.update(99.0, ship)
    assert ship.cargo._invert_active is False
    assert ship.controls_inverted is False
    assert ship.cargo._just_cleared_t > 0.0


def test_force_clear_inversion_drops_stale_flag():
    """Run-end must clear inversion so it doesn't bleed into delivery."""
    pygame.init()
    pygame.font.init()
    from cargo.epi_shrooms import EpistemologicalShrooms
    from ship.ship import PlayerShip

    ship = PlayerShip()
    ship.cargo = EpistemologicalShrooms()
    ship.cargo._next_cd = 0.05
    ship.cargo.update(0.06, ship)
    assert ship.controls_inverted is True
    ship.cargo.force_clear_inversion(ship)
    assert ship.cargo._invert_active is False
    assert ship.controls_inverted is False


def test_telegraph_decays_to_zero_within_a_second():
    pygame.init()
    pygame.font.init()
    from cargo.epi_shrooms import EpistemologicalShrooms
    from ship.ship import PlayerShip

    ship = PlayerShip()
    ship.cargo = EpistemologicalShrooms()
    ship.cargo._next_cd = 0.05
    ship.cargo.update(0.06, ship)
    # Tick a full second — the telegraph should decay.
    ship.cargo.update(1.0, ship)
    assert ship.cargo._just_triggered_t == 0.0


def test_run_manager_clears_inversion_on_run_end():
    """The run-end branch in run_manager._advance_sector calls force_clear."""
    from pathlib import Path
    src = Path("roguelite/run_manager.py").read_text(encoding="utf-8")
    assert "force_clear_inversion" in src, \
        "run_manager must clear shroom inversion at run-end"
