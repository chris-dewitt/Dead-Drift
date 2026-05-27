from __future__ import annotations
import math
import random
from physics.body import Vec2
from config import settings as S
from core.event_bus import bus, EVT_GUN_FIRE, EVT_GUN_MALFUNCTION


class Bullet:
    __slots__ = ("pos", "vel", "lifetime", "damage")

    def __init__(self, pos: Vec2, angle_deg: float, damage: int = 1):
        rad = math.radians(angle_deg)
        self.pos      = Vec2(pos.x, pos.y)
        self.vel      = Vec2(math.cos(rad) * S.BULLET_SPEED,
                             math.sin(rad) * S.BULLET_SPEED)
        self.lifetime = S.BULLET_LIFETIME
        self.damage   = damage

    def update(self, dt: float):
        self.pos.x   += self.vel.x * dt
        self.pos.y   += self.vel.y * dt
        self.lifetime -= dt

    @property
    def alive(self) -> bool:
        return self.lifetime > 0


class Gun:
    # Epic 12.1 — class-level multiplier set by RunManager when SYSTEM_GLITCH
    # mutator is active. 1.0 = baseline, 3.0 = mutator triples malfunction rate.
    malfunction_multiplier = 1.0

    def __init__(self):
        self.bullets: list[Bullet] = []
        self._cooldown = 0.0
        self._jam_t    = 0.0   # > 0 while jammed after malfunction
        self.fire_rate_mult = 1.0   # shop upgrade: multiplies fire rate
        self.damage_mult    = 1     # shop upgrade: bullets deal more damage

    def fire(self, pos: Vec2, angle_deg: float):
        if self._cooldown > 0 or self._jam_t > 0:
            return
        chance = min(0.95, S.GUN_MALFUNCTION_CHANCE * self.malfunction_multiplier)
        if random.random() < chance:
            bus.emit(EVT_GUN_MALFUNCTION)
            self._jam_t    = S.GUN_JAM_DURATION
            self._cooldown = S.GUN_COOLDOWN
            return
        self.bullets.append(Bullet(pos, angle_deg, damage=self.damage_mult))
        bus.emit(EVT_GUN_FIRE)
        self._cooldown = S.GUN_COOLDOWN / max(0.5, self.fire_rate_mult)

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
