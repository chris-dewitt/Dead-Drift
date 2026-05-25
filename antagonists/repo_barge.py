from __future__ import annotations
import math
import random
from physics.body import RigidBody2D, Vec2
from physics.tether import Tether
from config import settings as S
from core.event_bus import bus, EVT_MODULE_UNBOLTED, EVT_TETHER_HIT, EVT_BARGE_INTERCEPT, EVT_BAX_SPEAK, EVT_TORCH_ACTIVE, EVT_HARPOON_ARMING, EVT_BARGE_KILLED
from terminal.npcs.base_npc import NPCOutcome


class BargeState:
    PATROL    = "patrol"
    CHASE     = "chase"
    AIM       = "aim"        # tracking ship before firing — visible warning beam
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

    DETECT_RANGE       = 260.0
    CLAMP_RANGE        = 72.0
    AIM_DURATION       = 2.8    # seconds barge tracks before firing harpoon — escape window
    AIM_BREAK_RANGE    = 130.0  # if ship gets this far during AIM, barge aborts back to CHASE
    TORCH_INTERVAL     = 5.0
    PATROL_SPEED       = 55.0
    CHASE_SPEED        = 44.0
    AIM_SPEED          = 24.0   # barge slows hard while locking on
    RETREAT_DURATION   = 24.0   # seconds barge runs away after losing negotiation
    INTERCEPT_COOLDOWN = 45.0   # seconds before barge can intercept again
    DISRUPTION_HITS    = 2      # bullets needed to force a retreat
    DISRUPTION_RETREAT = 22.0   # seconds of retreat after being disrupted

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
        self._aim_t          = 0.0    # countdown while in AIM state
        self.hit_flash_t     = 0.0   # > 0 when recently hit (for renderer)

    # ------------------------------------------------------------------
    def update(self, dt: float):
        if self.is_destroyed:
            return

        self._intercept_cd = max(0.0, self._intercept_cd - dt)
        self.hit_flash_t   = max(0.0, self.hit_flash_t - dt)

        ship = self._get_ship()
        if ship is None:
            return

        dist_sq = (ship.pos - self.body.pos).length_sq()

        if self.state == BargeState.PATROL:
            self._patrol(dt)
            if dist_sq < self.DETECT_RANGE * self.DETECT_RANGE:
                self.state = BargeState.CHASE

        elif self.state == BargeState.CHASE:
            self._move_toward(ship.pos, self.CHASE_SPEED, dt)
            if dist_sq < self.CLAMP_RANGE * self.CLAMP_RANGE:
                if self._intercept_cd <= 0:
                    self._open_comm()
                else:
                    self._enter_aim()

        elif self.state == BargeState.AIM:
            self._move_toward(ship.pos, self.AIM_SPEED, dt)
            self._aim_t -= dt
            if dist_sq > self.AIM_BREAK_RANGE * self.AIM_BREAK_RANGE:
                # Player escaped the targeting cone — abort to chase
                self.state = BargeState.CHASE
            elif self._aim_t <= 0:
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
            # Patience ran out — start the aim sequence (player still gets warning)
            self._enter_aim()

    # ------------------------------------------------------------------
    def _enter_aim(self):
        self.state  = BargeState.AIM
        self._aim_t = self.AIM_DURATION
        bus.emit(EVT_HARPOON_ARMING, barge=self, countdown=self.AIM_DURATION)

    def _open_comm(self):
        """Open a mid-flight comm terminal instead of immediately clamping."""
        self.state = BargeState.INTERCEPT
        bus.emit(EVT_BARGE_INTERCEPT, barge=self)
        self.run_mgr.open_barge_terminal(self)

    def _patrol(self, dt: float):
        dist_sq = (self._patrol_target - self.body.pos).length_sq()
        if dist_sq < 20.0 * 20.0:
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
        """Called when a player bullet connects. Two hits force a retreat."""
        if self.state == BargeState.RETREAT:
            return
        self.hit_flash_t = 0.25
        self._disruption_hits += 1
        if self._disruption_hits >= self.DISRUPTION_HITS:
            self._disruption_hits = 0
            self._retreat_t = self.DISRUPTION_RETREAT
            self.state = BargeState.RETREAT
            if self._tether:
                self._tether.active = False
                self._tether = None
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                "Nice shootin'! They're pullin' back! Move it!",
                "Disrupted their nav! You've got twenty seconds — GO!",
                "Ha! Union property, dented. Get out of 'ere!",
                "Their instruments are screamin'. Leg it!",
                "Direct hit! Barge is breaking off — window's open!",
            ]))
        else:
            # First hit — immediate audio feedback
            bus.emit(EVT_BAX_SPEAK, line=random.choice([
                "Hit! Keep goin'! One more and they'll back off!",
                "Round connected! They felt that — one more!",
                "Good hit! Their shields are rattlin'!",
            ]))

    def take_damage(self, amount: float):
        self._hp -= amount
        if self._hp <= 0:
            self.is_destroyed = True
            if self._tether:
                self._tether.active = False
            bus.emit(EVT_BARGE_KILLED, barge=self)

    def _get_ship(self):
        try:
            return self.run_mgr._ship
        except AttributeError:
            return None

    @property
    def pos(self) -> Vec2:
        return self.body.pos
