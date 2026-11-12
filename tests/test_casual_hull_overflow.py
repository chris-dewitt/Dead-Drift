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
    ship.set_hull_cap(S.HULL_MAX + delta)
    assert ship.hull == S.HULL_MAX + 30
    assert ship.hull_cap == S.HULL_MAX + 30
    assert ship.hull_pct == 1.0


def test_fuel_canister_does_not_delete_casual_headroom():
    """Grabbing a canister used to clamp repair() at HULL_MAX.

    Casual starts at 230. The first fuel pickup called repair(12) and
    the ship landed on 200 — the difficulty bonus was gone.
    """
    from roguelite.run_manager import RunManager
    from ship.ship import PlayerShip

    ship = PlayerShip()
    ship.set_hull_cap(S.HULL_MAX + 30)
    rm = RunManager.__new__(RunManager)
    rm._ship = ship
    rm._on_canister_grab()
    assert ship.hull == pytest.approx(S.HULL_MAX + 30)

    ship.hull = S.HULL_MAX + 10
    rm._on_canister_grab()
    assert ship.hull == pytest.approx(S.HULL_MAX + 22)


def test_shop_hull_patch_heals_toward_casual_cap():
    from roguelite.shop import _ShopItem
    from ship.ship import PlayerShip

    ship = PlayerShip()
    ship.set_hull_cap(S.HULL_MAX + 30)
    ship.hull = S.HULL_MAX + 30
    patch = _ShopItem("Hull Patch Pack", "", "", 1000, "hull_patch")
    patch.apply(ship, None)
    assert ship.hull == pytest.approx(S.HULL_MAX + 30)

    ship.hull = S.HULL_MAX - 40
    drone = _ShopItem("Auto-Repair Drone", "", "", 2200, "repair_drone")
    drone.apply(ship, None)
    assert ship.hull == pytest.approx(S.HULL_MAX + 30)


def _run_with_frame(tmp_path, frame_name: str):
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager
    from ship.ship import PlayerShip

    ship = PlayerShip()
    rm = RunManager(MetaProgression(save_path=tmp_path / "meta.json"))
    rm.start_run(ship)
    frames = rm.draft._choices[0]
    for i, frame in enumerate(frames):
        if frame["name"] == frame_name:
            rm.draft._selected[0] = i
            return ship, rm
    raise AssertionError(f"{frame_name} missing from the draft")


def test_reinforced_frame_hull_bonus_is_real(tmp_path):
    """REINFORCED JUNK MK2 advertises +20 hull and 1.3x mass.

    apply_draft used to min() the bonus away, so the heavy frame was
    strictly worse than the stock hull.
    """
    ship, rm = _run_with_frame(tmp_path, "REINFORCED JUNK MK2")
    rm.apply_draft(ship)
    assert ship.hull == pytest.approx(S.HULL_MAX + 20)
    assert ship.hull_cap == pytest.approx(S.HULL_MAX + 20)
    assert ship.body.mass == pytest.approx(S.SHIP_MASS * 1.3)


def test_casual_and_reinforced_stack_on_confirm(tmp_path):
    from core.game import Game

    ship, rm = _run_with_frame(tmp_path, "REINFORCED JUNK MK2")
    rm.apply_draft(ship)

    host = type("Host", (), {})()
    host._DIFF_OPTS = Game._DIFF_OPTS
    host.meta = rm.meta
    host.ship = ship
    host.run_mgr = rm
    host._diff_cursor = 0  # CASUAL
    host._goto = lambda _state: None
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    Game._handle_difficulty_key(host, event)
    assert ship.hull == pytest.approx(S.HULL_MAX + 20 + 30)
    assert ship.hull_cap == pytest.approx(S.HULL_MAX + 50)
    assert ship.hull_pct == pytest.approx(1.0)

    ship.hull -= 40
    assert ship.hull_pct == pytest.approx((S.HULL_MAX + 10) / (S.HULL_MAX + 50))
    ship.repair(12)
    assert ship.hull == pytest.approx(S.HULL_MAX + 22)
