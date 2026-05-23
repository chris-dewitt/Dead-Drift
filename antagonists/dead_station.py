"""
Dead space station — large derelict with a rotating ring sub-component.
The ring sweeps a 40-degree collision arc; players must time their approach.
One per sector max.
"""
from __future__ import annotations
import math
import random
from physics.body import Vec2
from config import settings as S

_RING_DAMAGE  = S.DEBRIS_DAMAGE * 1.4
_RING_ARC_DEG = 40.0   # degrees of collision arc


class DeadStation:
    def __init__(self, x: float | None = None, y: float | None = None):
        self.pos  = Vec2(
            x if x is not None else random.randint(220, S.SCREEN_W - 220),
            y if y is not None else random.randint(140, S.FLIGHT_H - 140),
        )
        self.body_radius = random.randint(55, 80)   # core hull radius
        self.ring_radius = self.body_radius + random.randint(50, 80)  # ring orbit
        self.ring_angle  = random.uniform(0, 360)
        self.ring_speed  = random.choice([-1, 1]) * random.uniform(18, 35)  # deg/s

        self._col_body = (60, 50, 80)
        self._col_ring = (100, 80, 120)

    def update(self, dt: float):
        self.ring_angle = (self.ring_angle + self.ring_speed * dt) % 360

    def collides_body(self, pos: Vec2, radius: float = 12.0) -> bool:
        """Collision with the static core structure."""
        return (pos - self.pos).length_sq() < (self.body_radius + radius) ** 2

    def collides_ring(self, pos: Vec2, radius: float = 12.0) -> bool:
        """Collision with the rotating ring sweep arc."""
        delta     = pos - self.pos
        dist_sq   = delta.length_sq()
        ring_inner = (self.ring_radius - 14) ** 2
        ring_outer = (self.ring_radius + 14 + radius) ** 2
        if dist_sq < ring_inner or dist_sq > ring_outer:
            return False
        # Check if within the 40-degree arc currently occupied by the ring segment
        angle_to = math.degrees(math.atan2(delta.y, delta.x)) % 360
        diff      = (angle_to - self.ring_angle) % 360
        return diff < _RING_ARC_DEG or diff > 360 - 6

    @property
    def ring_damage(self) -> float:
        return _RING_DAMAGE
