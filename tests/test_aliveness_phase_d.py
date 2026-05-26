"""Aliveness Phase D: graphics and visual-feedback hooks."""
from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from config import settings as S
from physics.body import Vec2
from renderer.vector_renderer import VectorRenderer
from roguelite.run_manager import RunManager


def _renderer() -> VectorRenderer:
    pygame.init()
    return VectorRenderer(pygame.Surface((S.SCREEN_W, S.SCREEN_H)))


def _surface_has_nonblack(surface: pygame.Surface) -> bool:
    w, h = surface.get_size()
    for step in (8, 1):
        for x in range(0, w, step):
            for y in range(0, min(h, S.FLIGHT_H), step):
                if surface.get_at((x, y))[:3] != (0, 0, 0):
                    return True
    return False


class _Body:
    def __init__(self, vel: Vec2 | None = None):
        self.vel = vel or Vec2()

    def apply_impulse(self, impulse: Vec2) -> None:
        self.vel.x += impulse.x
        self.vel.y += impulse.y


def test_scan_ping_acknowledges_when_ring_reaches_ship():
    vr = _renderer()
    ship = SimpleNamespace(pos=Vec2(200, 200), is_alive=True)
    vr._scan_pings = [[200.0, 200.0, 0.0, False]]

    vr._draw_scan_pings(0.2, ship)

    assert vr._scan_ack_t > 0.0
    assert vr._scan_pings[0][3] is True


def test_renderer_phase_d_overlays_draw_pixels():
    vr = _renderer()
    ship = SimpleNamespace(
        pos=Vec2(500, 300),
        is_alive=True,
        hull_pct=0.08,
        body=SimpleNamespace(vel=Vec2(S.MAX_VELOCITY, 0)),
    )

    vr._on_sector_start(theme="TOLL AUTHORITY")
    vr._draw_theme_skybox(1.0)
    vr._on_alien_sighting()
    vr._draw_alien_sighting_witness(0.016, 1.0)
    vr._on_solar_wind(direction=(1.0, 0.2), duration=2.0, strength=55.0)
    vr._draw_solar_wind(0.016, 1.0)
    vr._draw_velocity_chromatic_aberration(ship, 1.0)
    vr._draw_viewport_cracks(ship, 1.0)
    vr._draw_ship_damage_overlays(ship, ship.pos, 0.0, ship.hull_pct, 1.0)

    assert _surface_has_nonblack(vr.surface)


def test_solar_wind_pushes_ship_and_debris():
    rm = RunManager.__new__(RunManager)
    rock = SimpleNamespace(pos=Vec2(120, 100), vel=Vec2())
    rm._ship = SimpleNamespace(
        pos=Vec2(100, 100),
        is_alive=True,
        body=_Body(),
    )
    rm._debris = [rock]
    rm._shower_rocks = []
    rm._canisters = []
    rm._solar_wind_t = 1.0
    rm._solar_wind_vec = Vec2(40.0, 0.0)

    rm._update_solar_wind(0.5)

    assert rm._ship.body.vel.x > 0.0
    assert rock.vel.x > 0.0
    assert rm._solar_wind_t == 0.5


def test_debris_wake_pushes_nearby_rock():
    rm = RunManager.__new__(RunManager)
    rock = SimpleNamespace(pos=Vec2(145, 100), vel=Vec2())
    neighbor = SimpleNamespace(pos=Vec2(158, 100), vel=Vec2())
    rm._ship = SimpleNamespace(
        pos=Vec2(100, 100),
        is_alive=True,
        body=_Body(Vec2(220.0, 0.0)),
    )
    rm._debris = [rock, neighbor]
    rm._shower_rocks = []

    rm._apply_debris_wake(0.5)

    assert rock.vel.x > 0.0
    assert neighbor.vel.x > rock.vel.x
