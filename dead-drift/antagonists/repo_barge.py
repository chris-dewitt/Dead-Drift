from __future__ import annotations
import math
import random
from physics.body import RigidBody2D, Vec2
from physics.tether import Tether
from config import settings as S
from core.event_bus import bus, EVT_MODULE_UNBOLTED


class BargeState:
    PATROL  = "patrol"
    CHASE   = "chase"
    CLAMP   = "clamp"     # tether fired, dragging player
    TORCH   = "torch"     # plasma torch unbolting modules
    RETREAT = "retreat"


class RepoBarge:
    """
    Local 404 field unit.  A massive industrial barge with amber hazard
    lights and very bad intentions toward your upgrades.

    AI state machine:
    PATROL → (player in range) → CHASE → (close enough) → CLAMP
    → (tether active) → TORCH → (module unbolted or tether snapped) → PATROL
    """

    DETECT_RANGE   = 400.0
    CLAMP_RANGE    = 120.0
    TORCH_INTERVAL = 5.0     # seconds between unbolt attempts
    PATROL_SPEED   = 60.0
    CHASE_SPEED    = 140.0

    def __init__(self, x: float, y: float, run_manager):
        self.body       = RigidBody2D(x, y, mass=8.0)
        self.run_mgr    = run_manager
        self.state      = BargeState.PATROL
        self._tether: Tether | None = None
        self._torch_cd  = self.TORCH_INTERVAL
        self._patrol_target = Vec2(
            random.randint(100, S.SCREEN_W - 100),
            random.randint(100, S.SCREEN_H - 100),
        )
        self.is_destroyed = False
        self._hp          = 60.0

    # ------------------------------------------------------------------
    def update(self, dt: float):
        if self.is_destroyed:
            return

        ship = self._get_ship()
        if ship is None:
            return

        dist = (ship.pos - self.body.pos).length()

        if self.state == BargeState.PATROL:
            self._patrol(dt)
            if dist < self.DETECT_RANGE:
                self.state = BargeState.CHASE

        elif self.state == BargeState.CHASE:
            self._move_toward(ship.pos, self.CHASE_SPEED, dt)
            if dist < self.CLAMP_RANGE:
                self._fire_harpoon(ship)

        elif self.state == BargeState.CLAMP:
            if self._tether:
                self._tether.barge_pos = self.body.pos
                self._tether.update(dt)
                if not self._tether.is_active:
                    self._tether = None
                    self.state = BargeState.PATROL
                else:
                    self.state = BargeState.TORCH

        elif self.state == BargeState.TORCH:
            self._torch_cd -= dt
            if self._torch_cd <= 0:
                self._unbolt_module(ship)
                self._torch_cd = self.TORCH_INTERVAL
            if self._tether:
                self._tether.barge_pos = self.body.pos
                self._tether.update(dt)
                if not self._tether.is_active:
                    self._tether = None
                    self.state = BargeState.PATROL

        self.body.integrate(dt)

    # ------------------------------------------------------------------
    def _patrol(self, dt: float):
        dist = (self._patrol_target - self.body.pos).length()
        if dist < 20.0:
            self._patrol_target = Vec2(
                random.randint(100, S.SCREEN_W - 100),
                random.randint(100, S.SCREEN_H - 100),
            )
        self._move_toward(self._patrol_target, self.PATROL_SPEED, dt)

    def _move_toward(self, target: Vec2, speed: float, dt: float):
        direction = (target - self.body.pos).normalized()
        self.body.apply_force(direction * speed * self.body.mass)

    def _fire_harpoon(self, ship):
        self._tether = Tether(ship.body, self.body.pos, barge_ref=self)
        self.state   = BargeState.CLAMP

    def _unbolt_module(self, ship):
        ship.chain.unbolt_random()

    # ------------------------------------------------------------------
    def take_damage(self, amount: float):
        self._hp -= amount
        if self._hp <= 0:
            self.is_destroyed = True
            if self._tether:
                self._tether.active = False

    def _get_ship(self):
        """Grab player ship through run_manager without circular import."""
        try:
            return self.run_mgr._ship
        except AttributeError:
            return None

    @property
    def pos(self) -> Vec2:
        return self.body.pos
