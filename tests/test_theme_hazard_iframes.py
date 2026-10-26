"""Theme chip hazards must respect the post-hit mercy window.

Junk-belt trash, frozen-trail comet fragments, and the industrial-graveyard
station ring all call ``ship.take_damage`` every frame the overlap lasts.
Their source strings were not in ``PlayerShip._IMPACT_SOURCES``, so the 1.5s
iframe never applied. At 60 Hz a single contact deleted the ship:

- trash: 2 hull × 60 = 120/s (hull is 200)
- comet ice: 3 hull × 60 while a fragment overlaps
- station ring: 11.2 hull × 60 for the whole sweep (~0.3s to death)

Debris, mines, and the station core already chip once per mercy window.
These three should too.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from types import SimpleNamespace

import pygame

from config import settings as S


def _run_manager(ship):
    pygame.init()
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager

    meta = MetaProgression(save_path="data/saves/test_theme_hazard_iframes.json")
    rm = RunManager(meta)
    rm._ship = ship
    rm._sector = SimpleNamespace(theme="")
    rm._wrecks = []
    rm._dead_station = None
    rm._trash_field = None
    rm._mine_field = None
    rm._ice_field = None
    rm._comet_trail = None
    rm._collapsing_well = None
    rm._debris_cloud = None
    return rm


def _hold_overlap(rm, frames: int = 45) -> None:
    """Overlap lasts well under the 1.5s mercy window at 60 Hz."""
    dt = 1.0 / S.FPS
    for _ in range(frames):
        rm._update_theme_obstacles(dt)


def test_trash_overlap_chips_once():
    from antagonists.trash_field import TrashField
    from physics.body import Vec2
    from ship.ship import PlayerShip

    ship = PlayerShip()
    rm = _run_manager(ship)
    field = TrashField(count=2)
    for piece in field.pieces:
        piece.pos = Vec2(ship.pos.x, ship.pos.y)
        piece.vel = Vec2(0.0, 0.0)
        piece.radius = 12
    rm._trash_field = field

    _hold_overlap(rm)

    assert ship.is_alive
    assert ship.hull == S.HULL_MAX - 2.0


def test_comet_overlap_chips_once():
    from antagonists.comet_trail import CometTrail
    from physics.body import Vec2
    from ship.ship import PlayerShip

    ship = PlayerShip()
    rm = _run_manager(ship)
    trail = CometTrail(num_lanes=2)
    parked = False
    for frag in trail.all_fragments():
        frag.vel = Vec2(0.0, 0.0)
        if not parked:
            frag.pos = Vec2(ship.pos.x, ship.pos.y)
            parked = True
        else:
            frag.pos = Vec2(-1000.0, -1000.0)
    rm._comet_trail = trail

    _hold_overlap(rm)

    assert ship.is_alive
    assert ship.hull == S.HULL_MAX - 3.0


def test_station_ring_sweep_chips_once():
    from antagonists.dead_station import DeadStation
    from physics.body import Vec2
    from ship.ship import PlayerShip

    ship = PlayerShip()
    rm = _run_manager(ship)
    station = DeadStation(x=500.0, y=300.0)
    station.ring_speed = 0.0
    station.ring_angle = 0.0
    ship.body.pos = Vec2(station.pos.x + station.ring_radius, station.pos.y)
    assert station.collides_ring(ship.pos)
    assert not station.collides_body(ship.pos)
    rm._dead_station = station

    _hold_overlap(rm)

    assert ship.is_alive
    assert ship.hull == S.HULL_MAX - station.ring_damage
