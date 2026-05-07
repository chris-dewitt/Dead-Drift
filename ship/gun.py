from __future__ import annotations
import math
import random
from physics.body import Vec2
from config import settings as S
from core.event_bus import bus, EVT_GUN_FIRE, EVT_GUN_MALFUNCTION


class Bullet:
    __slots__ = ("pos", "vel", "lifetime")

    def __init__(self, pos: Vec2, angle_deg: float):
        rad = math.radians(angle_deg)
        self.pos      = Vec2(pos.x, pos.y)
        self.vel      = Vec2(math.cos(rad) * S.BULLET_SPEED,
                             math.sin(rad) * S.BULLET_SPEED)
        self.lifetime = S.BULLET_LIFETIME

    def update(self, dt: float):
        self.pos.x   += self.vel.x * dt
        self.pos.y   += self.vel.y * dt
        self.lifetime -= dt

    @property
    def alive(self) -> bool:
        return self.lifetime > 0


class Gun:
    def __init__(self):
        self.bullets: list[Bullet] = []
        self._cooldown = 0.0
        self._jam_t    = 0.0   # > 0 while jammed after malfunction

    def fire(self, pos: Vec2, angle_deg: float):
        if self._cooldown > 0 or self._jam_t > 0:
            return
        if random.random() < S.GUN_MALFUNCTION_CHANCE:
            bus.emit(EVT_GUN_MALFUNCTION)
            self._jam_t    = S.GUN_JAM_DURATION
            self._cooldown = S.GUN_COOLDOWN
            return
        self.bullets.append(Bullet(pos, angle_deg))
        bus.emit(EVT_GUN_FIRE)
        self._cooldown = S.GUN_COOLDOWN

    def update(self, dt: float):
        self._cooldown = max(0.0, self._cooldown - dt)
        self._jam_t    = max(0.0, self._jam_t    - dt)
        for b in self.bullets:
            b.update(dt)
        self.bullets   = [b for b in self.bullets if b.alive]

    @property
    def is_jammed(self) -> bool:
        return self._jam_t > 0

    @property
    def jam_pct(self) -> float:
        return self._jam_t / S.GUN_JAM_DURATION if self._jam_t > 0 else 0.0
