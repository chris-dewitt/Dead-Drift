from __future__ import annotations
import math
import random
from physics.body import Vec2
from config import settings as S


class DebrisRock:
    """
    Slowly tumbling space junk. Bumps the ship for minor hull damage.
    """

    def __init__(self, x: float | None = None, y: float | None = None):
        self.pos = Vec2(
            x if x is not None else random.randint(80, S.SCREEN_W - 80),
            y if y is not None else random.randint(60, S.FLIGHT_H - 60),
        )
        self.vel       = Vec2(random.uniform(-22, 22), random.uniform(-22, 22))
        self.angle     = random.uniform(0, 360)
        self.rot_speed = random.uniform(-25, 25)
        self.radius    = random.randint(9, 19)
        self.hp        = 3 if self.radius >= 13 else 2   # large=3 hits, small=2 hits
        self.is_hit    = False   # brief flash on collision
        self._hit_t    = 0.0
        self._ship_cd  = 0.0   # cooldown before this rock can damage the ship again

        # Irregular polygon: N points at slightly randomised angles + radii
        n = random.randint(5, 7)
        self._pts: list[tuple[float, float]] = []
        for i in range(n):
            a = (i / n) * 360 + random.uniform(-18, 18)
            r = self.radius * random.uniform(0.55, 1.0)
            self._pts.append((a, r))

    # ------------------------------------------------------------------
    def update(self, dt: float):
        self.angle = (self.angle + self.rot_speed * dt) % 360
        self.pos.x = (self.pos.x + self.vel.x * dt) % S.SCREEN_W
        self.pos.y = (self.pos.y + self.vel.y * dt) % S.SCREEN_H
        if self._hit_t > 0:
            self._hit_t = max(0.0, self._hit_t - dt)
            self.is_hit = self._hit_t > 0
        if self._ship_cd > 0:
            self._ship_cd = max(0.0, self._ship_cd - dt)

    def hit(self) -> bool:
        """Decrement HP, flash, knock away.  Returns True when destroyed."""
        self.hp    -= 1
        self.is_hit = True
        self._hit_t = 0.15
        self.vel.x += random.uniform(-30, 30)
        self.vel.y += random.uniform(-30, 30)
        return self.hp <= 0

    def can_damage_ship(self) -> bool:
        """True if this rock is ready to deal ship damage (0.8s cooldown per hit)."""
        return self._ship_cd <= 0.0

    def register_ship_hit(self):
        """Mark this rock as having just damaged the ship. Starts cooldown."""
        self._ship_cd = 0.8

    def collides(self, pos: Vec2) -> bool:
        return (self.pos - pos).length() < self.radius + 10

    def world_pts(self) -> list[tuple[int, int]]:
        result = []
        for a_off, r in self._pts:
            a = math.radians(self.angle + a_off)
            result.append((
                int(self.pos.x + math.cos(a) * r),
                int(self.pos.y + math.sin(a) * r),
            ))
        return result
