"""
Mine field — 6-10 proximity mines.
Inert until ship within ARM_RANGE; arms (amber pulse).
Detonates FUSE_TIME seconds later if ship still within DET_RANGE.
Shooting a mine while armed defuses it (+50 cr).
"""
from __future__ import annotations
import random
from physics.body import Vec2
from config import settings as S

_ARM_RANGE    = 100.0
_DET_RANGE    = 60.0
_FUSE_TIME    = 1.5
_MINE_DAMAGE  = S.DEBRIS_DAMAGE * 2.0
_DEFUSE_BONUS = 50


class Mine:
    STATE_INERT   = "inert"
    STATE_ARMED   = "armed"
    STATE_DEAD    = "dead"

    def __init__(self):
        self.pos    = Vec2(random.randint(80, S.SCREEN_W - 80),
                           random.randint(60, S.FLIGHT_H - 60))
        self.state  = self.STATE_INERT
        self._fuse  = _FUSE_TIME
        self.alive  = True
        self._pulse = 0.0   # visual pulse phase

    def update(self, dt: float, ship_pos: Vec2) -> str | None:
        """Returns 'detonate' if mine explodes, 'defused' if shot, else None."""
        if not self.alive:
            return None

        self._pulse = (self._pulse + dt * 4.0) % (2 * 3.14159)
        dist_sq = (ship_pos - self.pos).length_sq()

        if self.state == self.STATE_INERT:
            if dist_sq < _ARM_RANGE * _ARM_RANGE:
                self.state = self.STATE_ARMED
                self._fuse = _FUSE_TIME

        elif self.state == self.STATE_ARMED:
            self._fuse -= dt
            if dist_sq > _ARM_RANGE * _ARM_RANGE:
                # Ship moved away — disarm
                self.state = self.STATE_INERT
                return None
            if dist_sq < _DET_RANGE * _DET_RANGE and self._fuse <= 0:
                self.alive = False
                return "detonate"

        return None

    def try_shoot(self, bullet_pos: Vec2) -> bool:
        """Returns True if bullet defuses this mine."""
        if not self.alive or self.state == self.STATE_DEAD:
            return False
        if (bullet_pos - self.pos).length_sq() < 20 * 20:
            self.alive = False
            return True
        return False

    @property
    def is_armed(self) -> bool:
        return self.state == self.STATE_ARMED

    @property
    def fuse_pct(self) -> float:
        return max(0.0, 1.0 - self._fuse / _FUSE_TIME) if self.is_armed else 0.0

    @property
    def damage(self) -> float:
        return _MINE_DAMAGE

    @property
    def defuse_bonus(self) -> int:
        return _DEFUSE_BONUS


class MineField:
    def __init__(self, count: int | None = None):
        n = count or random.randint(6, 10)
        self.mines: list[Mine] = [Mine() for _ in range(n)]

    def update(self, dt: float, ship_pos: Vec2) -> list[str]:
        """Returns list of results: 'detonate' events."""
        results = []
        for mine in self.mines:
            r = mine.update(dt, ship_pos)
            if r:
                results.append(r)
        return results

    @property
    def alive_mines(self) -> list[Mine]:
        return [m for m in self.mines if m.alive]
