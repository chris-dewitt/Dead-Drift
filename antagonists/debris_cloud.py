"""
Debris cloud — 40 non-damaging particles drifting horizontally across the
sector.  Reduces background visibility (~6% alpha) as a pure mood layer.

Rendered by vector_renderer via run_mgr.debris_cloud property.
"""
from __future__ import annotations
import random
from physics.body import Vec2
from config import settings as S

_COUNT     = 40
_SPD_MIN   = 15.0
_SPD_MAX   = 45.0
_ALPHA_OV  = 15   # ~6% of 255


class _Particle:
    def __init__(self):
        self.pos    = Vec2(random.uniform(0, S.SCREEN_W),
                           random.uniform(20, S.FLIGHT_H - 20))
        self.vx     = random.uniform(_SPD_MIN, _SPD_MAX)
        self.vy     = random.uniform(-8.0, 8.0)
        self.radius = random.uniform(1.5, 4.0)
        self.alpha  = random.randint(55, 130)

    def update(self, dt: float):
        self.pos.x += self.vx * dt
        self.pos.y += self.vy * dt
        if self.pos.x > S.SCREEN_W + 60:
            self.pos.x = -60
            self.pos.y = random.uniform(20, S.FLIGHT_H - 20)


class DebrisCloud:
    def __init__(self):
        self.particles: list[_Particle] = [_Particle() for _ in range(_COUNT)]

    def update(self, dt: float):
        for p in self.particles:
            p.update(dt)

    @property
    def alpha_overlay(self) -> int:
        return _ALPHA_OV
