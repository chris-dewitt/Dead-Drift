"""
Comet trail — 2-3 lanes of ice fragments traveling perpendicular to the sector
axis at 180 px/s. Ships caught in a lane take chip damage.
"""
from __future__ import annotations
import random
from physics.body import Vec2
from config import settings as S

_FRAGMENT_SPEED  = 180.0   # px/s (perpendicular to lane direction)
_CHIP_DAMAGE     = 3.0     # per contact
_LANE_THICKNESS  = 28      # px
_FRAGMENT_RADIUS = 6


class CometFragment:
    def __init__(self, x: float, y: float, vx: float, vy: float):
        self.pos = Vec2(x, y)
        self.vel = Vec2(vx, vy)

    def update(self, dt: float):
        self.pos.x = (self.pos.x + self.vel.x * dt) % S.SCREEN_W
        self.pos.y = (self.pos.y + self.vel.y * dt) % S.FLIGHT_H

    def collides(self, pos: Vec2) -> bool:
        return (self.pos - pos).length_sq() < (_FRAGMENT_RADIUS + 8) ** 2


class CometLane:
    """One stream of comet fragments traveling in a fixed direction."""

    def __init__(self, lane_y: float, direction: int = 1):
        """direction: +1 = left-to-right, -1 = right-to-left."""
        vx = _FRAGMENT_SPEED * direction
        # Spawn fragments spaced evenly across the screen
        self.fragments = [
            CometFragment(
                x=i * 80 + random.uniform(-15, 15),
                y=lane_y + random.uniform(-_LANE_THICKNESS / 2, _LANE_THICKNESS / 2),
                vx=vx,
                vy=random.uniform(-8, 8),
            )
            for i in range(20)
        ]
        self.lane_y = lane_y
        self.direction = direction

    def update(self, dt: float):
        for f in self.fragments:
            f.update(dt)


class CometTrail:
    def __init__(self, num_lanes: int | None = None):
        n = num_lanes or random.randint(2, 3)
        # Space lanes across the flight area
        y_positions = sorted(random.sample(
            range(80, S.FLIGHT_H - 80, 40), min(n, (S.FLIGHT_H - 160) // 40)
        ))[:n]
        # Alternate directions
        self.lanes = [
            CometLane(y, direction=(1 if i % 2 == 0 else -1))
            for i, y in enumerate(y_positions[:n])
        ]

    def update(self, dt: float):
        for lane in self.lanes:
            lane.update(dt)

    @property
    def chip_damage(self) -> float:
        return _CHIP_DAMAGE

    def all_fragments(self):
        for lane in self.lanes:
            yield from lane.fragments
