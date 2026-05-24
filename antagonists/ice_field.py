"""
Ice field — a 300×200 px zone where physics gets weird.
Inside: thruster force reduced 30%, ship slowly accelerates in current direction
(negative drag = slick comet ice residue).
"""
from __future__ import annotations
import random
from physics.body import Vec2
from config import settings as S

_ZONE_W = 300
_ZONE_H = 200
_THRUST_PENALTY  = 0.30   # 30% thrust reduction inside zone
_ACCELERATION    = 12.0   # px/s² added in current velocity direction (negative drag)


class IceField:
    def __init__(self, x: float | None = None, y: float | None = None):
        self.pos = Vec2(
            x if x is not None else random.randint(100, S.SCREEN_W - _ZONE_W - 100),
            y if y is not None else random.randint(60,  S.FLIGHT_H - _ZONE_H - 60),
        )
        self.w = _ZONE_W
        self.h = _ZONE_H

    def contains(self, pos: Vec2) -> bool:
        return (self.pos.x <= pos.x <= self.pos.x + self.w and
                self.pos.y <= pos.y <= self.pos.y + self.h)

    def apply_to(self, ship) -> bool:
        """Call each frame. Applies ice physics if ship is inside. Returns True if inside."""
        if not self.contains(ship.pos):
            return False
        if hasattr(ship, "apply_thrust_scale"):
            ship.apply_thrust_scale(1.0 - _THRUST_PENALTY)
        vel = ship.body.vel
        spd = vel.length()
        if spd > 0.5:
            # Add a small nudge in the direction of travel — makes the ship slick
            ship.body.apply_force(vel * (_ACCELERATION / spd))
        return True

    @property
    def thrust_penalty(self) -> float:
        return _THRUST_PENALTY
