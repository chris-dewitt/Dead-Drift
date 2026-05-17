from __future__ import annotations
import math
import random
from physics.body import RigidBody2D, Vec2
from physics.tether import Tether
from config import settings as S
from core.event_bus import bus, EVT_MODULE_UNBOLTED, EVT_TETHER_HIT, EVT_BARGE_INTERCEPT, EVT_BAX_SPEAK, EVT_TORCH_ACTIVE
from terminal.npcs.base_npc import NPCOutcome


class BargeState:
    PATROL    = "patrol"
    CHASE     = "chase"
    INTERCEPT = "intercept"  # holding position while comm terminal is open
    CLAMP     = "clamp"      # tether fired, dragging player
    TORCH     = "torch"      # plasma torch unbolting modules
    RETREAT   = "retreat"    # backing off after failed negotiation


class RepoBarge:
    """
    Local 404 field unit.  A massive industrial barge with amber hazard
    lights and very bad intentions toward your upgrades.

    AI state machine:
    PATROL → CHASE → INTERCEPT (comm terminal opens mid-flight)
      → RELEASE/EXPLOIT: RETREAT (backs off, long cooldown before next intercept)
      → IMPOUND/timeout: CLAMP → TORCH → PATROL
    If already retreated recently, skip INTERCEPT and CLAMP immediately.
    """

    DETECT_RANGE       = 400.0
    CLAMP_RANGE        = 120.0
    TORCH_INTERVAL     = 5.0
    PATROL_SPEED       = 60.0
    CHASE_SPEED        = 140.0
    RETREAT_DURATION   = 14.0   # seconds barge runs away after losing negotiation
    INTERCEPT_COOLDOWN = 45.0   # seconds before barge can intercept again
    DISRUPTION_HITS    = 3      # bullets needed to force a retreat
    DISRUPTION_RETREAT = 11.0   # seconds of retreat after being disrupted

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
        self.is_destroyed    = False
        self._hp             = 60.0
        self._retreat_t      = 0.0
        self._intercept_cd   = 0.0   # cooldown before next intercept attempt
        self._disruption_hits = 0    # bullet hits since last disruption reset
        self._torch_warned   = False  # track if torch_active event was emitted

    # ------------------------------------------------------------------
    def update(self, dt: float):
        if self.is_destroyed:
            return

        self._intercept_cd = max(0.0, self._intercept_cd - dt)

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
                if self._intercept_cd <= 0:
                    self._open_comm()
                else:
                    self._fire_harpoon(ship)

        elif self.state == BargeState.INTERCEPT:
            # Hold position — braking force so we don't drift away
            brake = self.body.vel * (-self.body.mass * 4.0)
            self.body.apply_force(brake)

        elif self.state == BargeState.CLAMP:
            if self._tether:
                self._tether.barge_pos = self.body.pos
                self._tether.update(dt)
                if not self._tether.is_active:
                    self._tether = None
                    self._torch_warned = False
                    self.state = BargeState.PATROL
                else:
                    self.state = BargeState.TORCH

        elif self.state == BargeState.TORCH:
            if not self._torch_warned:
                self._torch_warned = True
                bus.emit(EVT_TORCH_ACTIVE, barge=self, countdown=self.TORCH_INTERVAL)
            self._torch_cd -= dt
            if self._torch_cd <= 0:
                self._unbolt_module(ship)
                self._torch_cd = self.TORCH_INTERVAL
                # Re-emit so countdown resets each cycle
                bus.emit(EVT_TORCH_ACTIVE, barge=self, countdown=self.TORCH_INTERVAL)
            if self._tether:
                self._tether.barge_pos = self.body.pos
                self._tether.update(dt)
                if not self._tether.is_active:
                    self._tether = None
                    self._torch_warned = False
                    self.state = BargeState.PATROL

        elif self.state == BargeState.RETREAT:
            self._retreat_t -= dt
            # Move directly away from ship
            away = (self.body.pos - ship.pos).normalized()
            self.body.apply_force(away * self.CHASE_SPEED * self.body.mass)
            if self._retreat_t <= 0:
                self.state = BargeState.PATROL

        self.body.integrate(dt)

    # ------------------------------------------------------------------
    def on_terminal_outcome(self, outcome: str):
        """Called by RunManager when the comm terminal closes."""
        if outcome in (NPCOutcome.RELEASE, NPCOutcome.EXPLOIT):
            # Player won — barge backs off with a long cooldown
            self._retreat_t    = self.RETREAT_DURATION
            self._intercept_cd = self.INTERCEPT_COOLDOWN
            self.state         = BargeState.RETREAT
        else:
            # Patience ran out — fire the harpoon
            ship = self._get_ship()
            if ship is not None:
                self._fire_harpoon(ship)

    # ------------------------------------------------------------------
    def _open_comm(self):
        """Open a mid-flight comm terminal instead of immediately clamping."""
        self.state = BargeState.INTERCEPT
        bus.emit(EVT_BARGE_INTERCEPT, barge=self)
        self.run_mgr.open_barge_terminal(self)

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
        from core.event_bus import EVT_TETHER_HIT
        self._tether = Tether(ship.body, self.body.pos, barge_ref=self)
        self.state   = BargeState.CLAMP
        bus.emit(EVT_TETHER_HIT, barge=self)

    def _unbolt_module(self, ship):
        ship.chain.unbolt_random()

    # ------------------------------------------------------------------
    def take_hit(self):
        """Called when a player bullet connects. Three hits forces a retreat."""
        if self.state == BargeState.RETREAT:
            return
        self._disruption_hits += 1
        if self._disruption_hits >= self.DISRUPTION_HITS:
            self._disruption_hits = 0
            self._retreat_t = self.DISRUPTION_RETREAT
            self.state = BargeState.RETREAT
            if self._tether:
                self._tether.active = False
                self._tether = None
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                "THREE HITS. They're pullin' back! Move it!",
                "Disrupted their nav! You've got eleven seconds — GO!",
                "Ha! Union property, dented. Get out of 'ere!",
                "Their instruments are screamin'. Leg it!",
            ]))

    def take_damage(self, amount: float):
        self._hp -= amount
        if self._hp <= 0:
            self.is_destroyed = True
            if self._tether:
                self._tether.active = False

    def _get_ship(self):
        try:
            return self.run_mgr._ship
        except AttributeError:
            return None

    @property
    def pos(self) -> Vec2:
        return self.body.pos
