from __future__ import annotations
import math
import random
from physics.body import Vec2
from config import settings as S


class SpinningSatellite:
    """
    Derelict orbital hardware. Spins slowly, drifts gently.
    Two hit points. Collision takes hull damage.
    ~25% carry a scavenged fuel cache (pulsing beacon).
    """
    HULL_DAMAGE = 10

    def __init__(self, x: float | None = None, y: float | None = None):
        self.pos = Vec2(
            x if x is not None else random.randint(80, S.SCREEN_W - 80),
            y if y is not None else random.randint(60, S.FLIGHT_H - 60),
        )
        self.vel       = Vec2(random.uniform(-10, 10), random.uniform(-10, 10))
        self.angle     = random.uniform(0, 360)
        self.rot_speed = random.uniform(-14, 14)
        self.arm_len   = random.randint(20, 32)
        self.alive     = True
        self.hp        = 2
        self.has_fuel  = random.random() < 0.25
        self._fuel_t   = 0.0
        self._hit_t    = 0.0

    def update(self, dt: float):
        self.angle = (self.angle + self.rot_speed * dt) % 360
        self.pos.x = (self.pos.x + self.vel.x * dt) % S.SCREEN_W
        self.pos.y = (self.pos.y + self.vel.y * dt) % S.FLIGHT_H
        if self.has_fuel:
            self._fuel_t += dt
        if self._hit_t > 0:
            self._hit_t = max(0.0, self._hit_t - dt)

    def collides(self, pos: Vec2) -> bool:
        return (self.pos - pos).length() < self.arm_len + 6

    def hit(self) -> bool:
        """Decrement HP. Returns True when destroyed."""
        self.hp -= 1
        self._hit_t = 0.14
        if self.hp <= 0:
            self.alive = False
            return True
        return False
