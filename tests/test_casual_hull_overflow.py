"""Regression: selecting CASUAL difficulty crashed the ship render.

CASUAL starts the run with hull above HULL_MAX (+30 headroom, applied by
the Epic 18 difficulty picker). `PlayerShip.hull_pct` returned the raw
ratio (1.3), and the DELTA-7 frame's damage-glow computed a negative red
channel from `(1.0 - hp)` → `ValueError: invalid color argument` on the
first FLIGHT frame of a casual run.

hull_pct is a display fraction — it must clamp to 0..1 while the raw
hull value keeps its casual headroom.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from config import settings as S


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    pygame.font.init()
    yield


def test_hull_pct_clamps_above_max_and_below_zero():
    from ship.ship import PlayerShip
    ship = PlayerShip()
    ship.hull = S.HULL_MAX + 30          # casual start bonus
    assert ship.hull_pct == 1.0
    ship.hull = -5.0
    assert ship.hull_pct == 0.0
    ship.hull = S.HULL_MAX * 0.5
    assert ship.hull_pct == pytest.approx(0.5)


def test_casual_hull_renders_all_ship_frames():
    """The actual crash path: every ship frame must draw at hull 130."""
    from ship.ship import PlayerShip
    from renderer.vector_renderer import VectorRenderer

    surface = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
    r = VectorRenderer(surface)
    ship = PlayerShip()
    ship.hull = S.HULL_MAX + 30
    for frame in ("SCRAP DELTA-7", "REINFORCED JUNK MK2", "RUSTBUCKET"):
        r._draw_ship(ship, t=1.0, frame_name=frame)


def test_difficulty_hull_delta_still_exceeds_max():
    """The casual headroom itself is intentional — only the fraction clamps."""
    from ship.ship import PlayerShip
    ship = PlayerShip()
    delta = 30
    ship.hull = max(1.0, min(S.HULL_MAX + delta, ship.hull + delta))
    assert ship.hull == S.HULL_MAX + 30
    assert ship.hull_pct == 1.0
