"""ComplianceVessel tuning guard (dialed back July 2026).

The Ch5/6 pursuit drones used to home from infinite range at near-player top
speed and ram for 28, so they were an inescapable death sentence the moment
they spawned. These pin the two properties that make them a *pest* instead:
you can outrun one at full throttle, and sitting in the open is survivable for
a good while rather than instantly fatal.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import types

from physics.body import Vec2
from config import settings as S
from antagonists.compliance_vessel import ComplianceVessel


class _FakeShip:
    def __init__(self, x, y, vx=0.0, vy=0.0):
        self._p = Vec2(x, y)
        self.vel = Vec2(vx, vy)
        self.dmg = 0.0

    @property
    def pos(self):
        return self._p

    def take_damage(self, d, source=""):
        self.dmg += d


def _vessel(ship, x, y):
    return ComplianceVessel(x, y, types.SimpleNamespace(_ship=ship))


def test_top_speed_is_below_player_max_velocity():
    # If this ever creeps back above MAX_VELOCITY the drone becomes inescapable.
    assert ComplianceVessel.MAX_SPEED < S.MAX_VELOCITY


def test_ram_damage_was_dialed_back():
    assert ComplianceVessel.RAM_DAMAGE <= 22.0


def test_a_full_throttle_sprint_opens_the_gap():
    ship = _FakeShip(0.0, 0.0, vx=S.MAX_VELOCITY)
    cv = _vessel(ship, -200.0, 0.0)
    dt = 1 / 60.0
    d0 = (ship.pos - cv.pos).length()
    for _ in range(int(6 / dt)):
        ship._p.x += ship.vel.x * dt        # player sprints away
        cv.update(dt)
    d1 = (ship.pos - cv.pos).length()
    assert d1 > d0 + 100.0, f"drone kept pace: {d0:.0f} -> {d1:.0f}"


def test_sitting_in_the_open_is_survivable_not_instant_death():
    ship = _FakeShip(0.0, 0.0)
    cv = _vessel(ship, -150.0, 0.0)
    dt = 1 / 60.0
    for _ in range(int(10 / dt)):
        cv.update(dt)
    # 10 seconds stationary against one drone should not shred a healthy hull.
    assert ship.dmg <= 60.0, f"too punishing: {ship.dmg:.0f} dmg in 10s"
    assert ship.dmg > 0.0, "a stationary target should still get rammed"
