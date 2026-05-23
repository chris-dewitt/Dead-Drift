"""
Trash field — 30-50 drifting junk pieces.
Each causes 2 hp chip damage on contact.
Shootable: +25 cr per kill; 1-in-8 are "good salvage" (+200 cr).
"""
from __future__ import annotations
import math
import random
from physics.body import Vec2
from config import settings as S

_CHIP_DAMAGE    = 2.0
_SALVAGE_ODDS   = 1 / 8
_SALVAGE_BONUS  = 200
_SCRAP_BONUS    = 25


class TrashPiece:
    def __init__(self):
        self.pos     = Vec2(random.randint(30, S.SCREEN_W - 30),
                            random.randint(30, S.FLIGHT_H - 30))
        self.vel     = Vec2(random.uniform(-18, 18), random.uniform(-12, 12))
        self.angle   = random.uniform(0, 360)
        self.rot_spd = random.uniform(-20, 20)
        self.radius  = random.randint(5, 12)
        self.is_good = random.random() < _SALVAGE_ODDS
        self.alive   = True

        # Irregular 4-6 vertex shape
        n = random.randint(4, 6)
        self._pts = [(i / n * 360 + random.uniform(-20, 20),
                      self.radius * random.uniform(0.5, 1.0))
                     for i in range(n)]

    def update(self, dt: float):
        self.angle = (self.angle + self.rot_spd * dt) % 360
        self.pos.x = (self.pos.x + self.vel.x * dt) % S.SCREEN_W
        self.pos.y = (self.pos.y + self.vel.y * dt) % S.FLIGHT_H

    def world_pts(self) -> list[tuple[int, int]]:
        pts = []
        for a_off, r in self._pts:
            a = math.radians(self.angle + a_off)
            pts.append((int(self.pos.x + math.cos(a) * r),
                        int(self.pos.y + math.sin(a) * r)))
        return pts

    def collides(self, pos: Vec2) -> bool:
        return (self.pos - pos).length_sq() < (self.radius + 8) ** 2

    @property
    def credit_reward(self) -> int:
        return _SALVAGE_BONUS if self.is_good else _SCRAP_BONUS

    @property
    def chip_damage(self) -> float:
        return _CHIP_DAMAGE


class TrashField:
    def __init__(self, count: int | None = None):
        n = count or random.randint(30, 50)
        self.pieces: list[TrashPiece] = [TrashPiece() for _ in range(n)]

    def update(self, dt: float):
        for p in self.pieces:
            if p.alive:
                p.update(dt)

    @property
    def alive_pieces(self) -> list[TrashPiece]:
        return [p for p in self.pieces if p.alive]
