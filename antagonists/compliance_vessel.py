"""
Nova Soma Compliance Vessel — chapter 5-6 pursuit ship.

Not a barge. No harpoon, no negotiation, no comm window. Just a fast,
expensive, ram-only pursuit drone dispatched by the company itself.
Spawns once the player picks up the EncryptedDrive in chapter 5 and
keeps coming through chapter 6.

Behaviour: closes on the player at high speed, rams, peels off, comes
back. Two hits force it into retreat (rebuild before re-engaging).
Can be EMP-burst stunned for 5s.
"""
from __future__ import annotations
import math
import random
from physics.body import Vec2
from config import settings as S
from core.event_bus import bus, EVT_BAX_SPEAK, EVT_AISHIP_DESTROYED


_STATE_INTERCEPT = "intercept"
_STATE_RAM       = "ram"
_STATE_REGROUP   = "regroup"
_STATE_STUNNED   = "stunned"
_STATE_DEAD      = "dead"


class ComplianceVessel:
    """Fast ram-only pursuer. Quiet, lethal, corporate."""

    DETECT_RANGE   = 1200.0      # always knows where you are
    RAM_RANGE      = 60.0
    BREAK_OFF      = 220.0
    SPEED_CRUISE   = 110.0
    SPEED_RAM      = 220.0
    RAM_DAMAGE     = 28.0
    HULL_HITS      = 2
    STUN_DURATION  = 5.0

    def __init__(self, x: float, y: float, run_manager):
        self.body_pos    = Vec2(x, y)
        self.vel         = Vec2(0.0, 0.0)
        self.run_mgr     = run_manager
        self.state       = _STATE_INTERCEPT
        self._state_t    = 0.0
        self._hits       = 0
        self._stun_t     = 0.0
        self._hit_flash_t = 0.0
        self.alive       = True
        self.radius      = 22.0
        # Visual / audio: faint chrome silhouette, no transponder
        self.heading     = 0.0

    @property
    def pos(self) -> Vec2:
        return self.body_pos

    @property
    def is_destroyed(self) -> bool:
        return not self.alive

    def update(self, dt: float):
        if not self.alive:
            return
        self._state_t   += dt
        self._hit_flash_t = max(0.0, self._hit_flash_t - dt)
        self._stun_t    = max(0.0, self._stun_t - dt)

        ship = getattr(self.run_mgr, "_ship", None)
        if ship is None:
            return

        if self.state == _STATE_STUNNED:
            # EMP'd — drift, no thrust
            if self._stun_t <= 0:
                self.state = _STATE_INTERCEPT
                self._state_t = 0.0
        else:
            to_ship = ship.pos - self.body_pos
            dist    = to_ship.length()
            if dist < 0.01:
                return
            dir_x, dir_y = to_ship.x / dist, to_ship.y / dist

            if self.state == _STATE_INTERCEPT:
                speed = self.SPEED_CRUISE
                self.vel.x += dir_x * speed * dt * 1.8
                self.vel.y += dir_y * speed * dt * 1.8
                if dist < self.RAM_RANGE * 2.0:
                    self.state = _STATE_RAM
                    self._state_t = 0.0

            elif self.state == _STATE_RAM:
                speed = self.SPEED_RAM
                self.vel.x += dir_x * speed * dt * 3.0
                self.vel.y += dir_y * speed * dt * 3.0
                if dist < self.RAM_RANGE:
                    ship.take_damage(self.RAM_DAMAGE, source="compliance_ram")
                    # Bounce off and switch to regroup
                    self.vel.x = -dir_x * 240.0
                    self.vel.y = -dir_y * 240.0
                    self.state = _STATE_REGROUP
                    self._state_t = 0.0
                if self._state_t > 4.0 and dist > self.BREAK_OFF:
                    self.state = _STATE_REGROUP
                    self._state_t = 0.0

            elif self.state == _STATE_REGROUP:
                # Drift outward, then re-intercept
                if self._state_t > 3.5:
                    self.state = _STATE_INTERCEPT
                    self._state_t = 0.0

        # Soft velocity cap
        sp = math.hypot(self.vel.x, self.vel.y)
        if sp > 260.0:
            self.vel.x = self.vel.x / sp * 260.0
            self.vel.y = self.vel.y / sp * 260.0
        self.body_pos.x += self.vel.x * dt
        self.body_pos.y += self.vel.y * dt
        if abs(self.vel.x) + abs(self.vel.y) > 1.0:
            self.heading = math.degrees(math.atan2(self.vel.y, self.vel.x))

    def take_hit(self, damage: int = 1):
        if not self.alive:
            return
        self._hits += damage
        self._hit_flash_t = 0.18
        if self._hits >= self.HULL_HITS:
            self.alive = False
            bus.emit(EVT_AISHIP_DESTROYED, ship=self)
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                "Compliance drone down. Corporate'll bill us for that one.",
                "Drone's a wreck. Don't slow down — they'll send another.",
                "Got 'im. Nova Soma's flush. Plenty more where that came from.",
            ]))

    def emp_stun(self):
        if not self.alive:
            return
        self.state   = _STATE_STUNNED
        self._stun_t = self.STUN_DURATION
        self.vel.x  *= 0.2
        self.vel.y  *= 0.2

    @property
    def hit_flash_t(self) -> float:
        return self._hit_flash_t

    @property
    def is_stunned(self) -> bool:
        return self.state == _STATE_STUNNED
