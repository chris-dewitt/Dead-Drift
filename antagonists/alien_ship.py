from __future__ import annotations
import math
import random
from physics.body import Vec2
from config import settings as S


# Body polygon — local space, nose pointing +x. Deliberately asymmetric.
HULL_PTS = [
    ( 44,   0),
    ( 24, -14),
    (  0, -24),
    (-12,  -9),
    (-32,  -4),
    (-30,   0),
    (-32,   6),
    (-12,  15),
    (  0,  34),   # lower fin extends further than upper (alien asymmetry)
    ( 24,  20),
]

INNER_PTS = [
    ( 36,  0), ( 14, -7), ( -8, -9),
    (-20,  0), ( -8,  9), ( 14,  8),
]


class AlienShip:
    """
    Passes through the sector once at high speed. Non-hostile.
    Disappears off-screen and never returns.
    """

    def __init__(self):
        speed = random.uniform(520, 780)
        side  = random.choice(["left", "right", "top", "bottom"])
        if side == "left":
            self.pos = Vec2(-80, random.uniform(60, S.FLIGHT_H - 60))
            self.vel = Vec2(speed, random.uniform(-80, 80))
        elif side == "right":
            self.pos = Vec2(S.SCREEN_W + 80, random.uniform(60, S.FLIGHT_H - 60))
            self.vel = Vec2(-speed, random.uniform(-80, 80))
        elif side == "top":
            self.pos = Vec2(random.uniform(60, S.SCREEN_W - 60), -80)
            self.vel = Vec2(random.uniform(-80, 80), speed)
        else:
            self.pos = Vec2(random.uniform(60, S.SCREEN_W - 60), S.FLIGHT_H + 80)
            self.vel = Vec2(random.uniform(-80, 80), -speed)

        self.heading = math.degrees(math.atan2(self.vel.y, self.vel.x))
        self.alive   = True
        self._trail: list[tuple[float, float]] = []

    def update(self, dt: float):
        self._trail.append((self.pos.x, self.pos.y))
        if len(self._trail) > 14:
            self._trail.pop(0)
        self.pos.x += self.vel.x * dt
        self.pos.y += self.vel.y * dt
        if (self.pos.x < -400 or self.pos.x > S.SCREEN_W + 400 or
                self.pos.y < -400 or self.pos.y > S.FLIGHT_H + 400):
            self.alive = False

    def world_pts(self, raw_pts: list) -> list[tuple[int, int]]:
        rad = math.radians(self.heading)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        return [
            (int(lx * cos_a - ly * sin_a + self.pos.x),
             int(lx * sin_a + ly * cos_a + self.pos.y))
            for lx, ly in raw_pts
        ]
