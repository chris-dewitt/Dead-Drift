"""Over-cap drag must brake, never reverse and explode after a hitch."""

from __future__ import annotations

import math

from config import settings as S
from physics.body import RigidBody2D, Vec2


def test_hitch_while_over_cap_does_not_explode_velocity():
    """Slingshot overdrive expires during a 0.5s stall.

    Unclamped drag multiplies velocity by a negative factor, then the
    following 60fps frames run away to inf. The ship must stay finite,
    keep its direction, and settle at or under the normal cap.
    """
    body = RigidBody2D(0.0, 0.0, mass=1.0)
    body.vel = Vec2(S.MAX_VELOCITY * 1.5, 0.0)
    body._vel_cap_override = S.MAX_VELOCITY * 1.5
    body._overdrive_t = 0.01

    body.integrate(0.5)

    assert math.isfinite(body.speed())
    assert body.vel.x >= 0.0
    assert body.speed() <= S.MAX_VELOCITY * 1.5

    for _ in range(8):
        body.integrate(1.0 / 60.0)
        assert math.isfinite(body.speed())
        assert body.vel.x >= 0.0

    assert body.speed() <= S.MAX_VELOCITY + 1.0


def test_well_impulse_plus_hitch_does_not_explode_velocity():
    """Core knockback (+200 px/s) stacked on cruise speed, then a stall."""
    body = RigidBody2D(0.0, 0.0, mass=1.0)
    body.vel = Vec2(S.MAX_VELOCITY, 0.0)
    body.apply_impulse(Vec2(200.0, 0.0))

    body.integrate(0.4)

    assert math.isfinite(body.speed())
    assert body.vel.x >= 0.0

    for _ in range(6):
        body.integrate(1.0 / 60.0)
        assert math.isfinite(body.speed())
        assert body.vel.x >= 0.0
    assert body.speed() <= S.MAX_VELOCITY + 1.0


def test_normal_frame_still_brakes_overdrive_expiry():
    """At 60fps the clamp must not change the existing brake."""
    body = RigidBody2D(0.0, 0.0, mass=1.0)
    body.vel = Vec2(S.MAX_VELOCITY * 1.5, 0.0)
    body._vel_cap_override = S.MAX_VELOCITY * 1.5
    body._overdrive_t = 0.01

    body.integrate(1.0 / 60.0)

    assert body.vel.x > 0.0
    assert body.speed() < S.MAX_VELOCITY * 1.5
    assert body.speed() > S.MAX_VELOCITY
