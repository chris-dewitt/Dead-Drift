"""
AI-driven NPC ships that share the sector with the player.

Five run-down silhouettes (FIGHTER / FREIGHTER / HAULER / GUNBOAT /
DERELICT), three behaviors (TRAFFIC / HAILER / PIRATE), wrapped in a
finite state machine.

Behaviors:
    TRAFFIC — drifts past on a straight line. No interaction.
    HAILER  — drifts in, matches player velocity, opens a terminal.
    PIRATE  — closes on player, deals ram damage on contact, dies to guns.

State machine:
    SPAWN  → WANDER  → (approach trigger?) → APPROACH
    APPROACH → (in range?) → HAIL  / ATTACK
    HAIL    → (terminal opened or timeout) → DEPART
    ATTACK  → (player dead or self dead) → DEPART
    DEPART  → off-screen → dies
"""
from __future__ import annotations
import math
import random
from physics.body import Vec2
from config import settings as S
from core.event_bus import bus, EVT_AISHIP_HAIL, EVT_AISHIP_DESTROYED, EVT_BAX_SPEAK


# Silhouette classes — drive the renderer's shape selection
CLASS_FIGHTER   = "fighter"
CLASS_FREIGHTER = "freighter"
CLASS_HAULER    = "hauler"
CLASS_GUNBOAT   = "gunboat"
CLASS_DERELICT  = "derelict"
# Aliveness A.5 (May 2026 design lock): non-Union NPCs each get a
# distinct in-flight silhouette so the player can see them by hull,
# not just by terminal opening. Players had no visual cue that
# Pirate / Marrow / Kress / Sandra existed in the void; these classes
# fix that.
CLASS_PIRATE_SKIFF       = "pirate_skiff"        # Krellborn's outer-belt skiff
CLASS_BROADCAST_RELAY    = "broadcast_relay"     # Marrow's pirate-radio dish ship
CLASS_BELT_HAULER        = "belt_hauler"         # Kress's beat-up Outer Belt hauler
CLASS_COMPLIANCE_COURIER = "compliance_courier"  # Sandra's pristine union courier

ALL_CLASSES = (CLASS_FIGHTER, CLASS_FREIGHTER, CLASS_HAULER,
               CLASS_GUNBOAT, CLASS_DERELICT,
               CLASS_PIRATE_SKIFF, CLASS_BROADCAST_RELAY,
               CLASS_BELT_HAULER, CLASS_COMPLIANCE_COURIER)

# Aliveness A.5 — restrict random sampling for ambient traffic to the
# generic-faction classes so we don't accidentally spawn a 'Sandra'-
# class ship in random traffic. The character classes are spawned
# explicitly when their NPCs are scripted in.
_AMBIENT_CLASSES = (CLASS_FIGHTER, CLASS_FREIGHTER, CLASS_HAULER,
                    CLASS_GUNBOAT, CLASS_DERELICT)

# Behaviors
BEHAVIOR_TRAFFIC = "traffic"
BEHAVIOR_HAILER  = "hailer"
BEHAVIOR_PIRATE  = "pirate"

# States
ST_WANDER   = "wander"
ST_APPROACH = "approach"
ST_HAIL     = "hail"
ST_ATTACK   = "attack"
ST_DEPART   = "depart"

# Hull thresholds — derelicts already wrecked; gunboats tough.
_DEFAULT_HULL = {
    CLASS_FIGHTER:                3,
    CLASS_FREIGHTER:              4,
    CLASS_HAULER:                 5,
    CLASS_GUNBOAT:                6,
    CLASS_DERELICT:               1,
    CLASS_PIRATE_SKIFF:           4,
    CLASS_BROADCAST_RELAY:        3,
    CLASS_BELT_HAULER:            5,
    CLASS_COMPLIANCE_COURIER:     3,
}

_DEFAULT_RADIUS = {
    CLASS_FIGHTER:                20,
    CLASS_FREIGHTER:              30,
    CLASS_HAULER:                 34,
    CLASS_GUNBOAT:                22,
    CLASS_DERELICT:               26,
    CLASS_PIRATE_SKIFF:           22,
    CLASS_BROADCAST_RELAY:        32,  # dish array makes it visually wide
    CLASS_BELT_HAULER:            38,
    CLASS_COMPLIANCE_COURIER:     22,
}

# Behavior → NPC type for the terminal lookup
_HAIL_NPC_BY_CLASS = {
    CLASS_FIGHTER:                "dray",            # other off-channel courier
    CLASS_FREIGHTER:              "nervous_fence",   # relay broker peer
    CLASS_HAULER:                 "mira_voss",       # back-alley hull medic
    CLASS_GUNBOAT:                "pirate",          # generic outer-belt hail
    CLASS_DERELICT:               None,              # never hails
    # Aliveness A.5 — character-specific NPCs each get their own hull
    # so the player can see who they're meeting before the comm opens.
    CLASS_PIRATE_SKIFF:           "pirate",          # Krellborn specifically
    CLASS_BROADCAST_RELAY:        "underground_dj",  # Marrow's pirate radio
    CLASS_BELT_HAULER:            "kress",           # Kress's intel freighter
    CLASS_COMPLIANCE_COURIER:     "sandra",          # Sandra Vega-Marsh
}


class AIShip:
    """Procedural NPC ship with a small FSM and procedural wear."""

    def __init__(self,
                 ship_class: str | None = None,
                 behavior: str | None = None,
                 pos: Vec2 | None = None,
                 vel: Vec2 | None = None):
        # Aliveness A.5 — character-specific classes must be requested
        # explicitly. Random ambient traffic only samples the generic pool.
        self.ship_class = ship_class or random.choice(_AMBIENT_CLASSES)
        self.behavior   = behavior or self._default_behavior(self.ship_class)

        # Spawn from a random edge if no pos given
        if pos is None or vel is None:
            self.pos, self.vel = self._spawn_from_edge()
        else:
            self.pos, self.vel = pos, vel

        self.heading      = math.degrees(math.atan2(self.vel.y, self.vel.x))
        self.hull         = _DEFAULT_HULL[self.ship_class]
        self.radius       = _DEFAULT_RADIUS[self.ship_class]
        self.wear         = random.uniform(0.3, 0.95)   # 0 pristine .. 1 wrecked
        self.alive        = True
        self.state        = ST_WANDER
        self._state_t     = 0.0
        self._hail_fired  = False
        self._hit_t       = 0.0
        self._has_hit_player = False    # so pirate ram only damages once per pass

        # Deterministic per-ship visual seed (panel patterns, scratches)
        self._art_seed = random.randint(0, 999_999)

        # Soft motion noise so ships feel hand-piloted, not on rails
        self._wobble_phase = random.uniform(0.0, math.tau)

        # Lifespan safety net — pirates that fail to engage eventually leave
        self._lifetime_t = 0.0
        self._max_lifetime = random.uniform(45.0, 70.0)

    # ------------------------------------------------------------------
    @staticmethod
    def _default_behavior(ship_class: str) -> str:
        if ship_class == CLASS_DERELICT:
            return BEHAVIOR_TRAFFIC
        if ship_class in (CLASS_GUNBOAT, CLASS_PIRATE_SKIFF):
            return BEHAVIOR_PIRATE
        return BEHAVIOR_HAILER

    @staticmethod
    def _spawn_from_edge() -> tuple[Vec2, Vec2]:
        speed = random.uniform(80.0, 140.0)
        side = random.choice(("left", "right", "top", "bottom"))
        if side == "left":
            pos = Vec2(-60, random.uniform(60, S.FLIGHT_H - 60))
            vel = Vec2(speed, random.uniform(-30, 30))
        elif side == "right":
            pos = Vec2(S.SCREEN_W + 60, random.uniform(60, S.FLIGHT_H - 60))
            vel = Vec2(-speed, random.uniform(-30, 30))
        elif side == "top":
            pos = Vec2(random.uniform(60, S.SCREEN_W - 60), -60)
            vel = Vec2(random.uniform(-30, 30), speed)
        else:
            pos = Vec2(random.uniform(60, S.SCREEN_W - 60), S.FLIGHT_H + 60)
            vel = Vec2(random.uniform(-30, 30), -speed)
        return pos, vel

    # ------------------------------------------------------------------
    def update(self, dt: float, ship) -> None:
        self._state_t    += dt
        self._lifetime_t += dt
        self._wobble_phase += dt * 0.7
        if self._hit_t > 0:
            self._hit_t = max(0.0, self._hit_t - dt)

        if not self.alive:
            return

        if self.state == ST_WANDER:
            self._tick_wander(dt, ship)
        elif self.state == ST_APPROACH:
            self._tick_approach(dt, ship)
        elif self.state == ST_HAIL:
            self._tick_hail(dt, ship)
        elif self.state == ST_ATTACK:
            self._tick_attack(dt, ship)
        elif self.state == ST_DEPART:
            self._tick_depart(dt)

        # Integrate
        self.pos.x += self.vel.x * dt
        self.pos.y += self.vel.y * dt
        if self.vel.length() > 0.01:
            target_heading = math.degrees(math.atan2(self.vel.y, self.vel.x))
            # Smooth heading interpolation
            diff = (target_heading - self.heading + 180) % 360 - 180
            self.heading += diff * min(1.0, dt * 4.0)

        # World wraps for stationary cruisers, but ships leaving on DEPART
        # should be allowed to exit and despawn
        if self.state in (ST_WANDER, ST_HAIL):
            if self.pos.x < -120:   self.pos.x += S.SCREEN_W + 240
            if self.pos.x > S.SCREEN_W + 120: self.pos.x -= S.SCREEN_W + 240
            if self.pos.y < -120:   self.pos.y += S.FLIGHT_H + 240
            if self.pos.y > S.FLIGHT_H + 120: self.pos.y -= S.FLIGHT_H + 240

        # Hard lifetime cap so a pirate that lost interest doesn't loiter forever
        if self._lifetime_t > self._max_lifetime and self.state != ST_DEPART:
            self.state = ST_DEPART
            self._state_t = 0.0

        # Off-screen during DEPART → die
        if self.state == ST_DEPART:
            if (self.pos.x < -200 or self.pos.x > S.SCREEN_W + 200 or
                    self.pos.y < -200 or self.pos.y > S.FLIGHT_H + 200):
                self.alive = False

    # ------------------------------------------------------------------
    def _tick_wander(self, dt: float, ship) -> None:
        # Derelicts drift forever in a straight line
        if self.behavior == BEHAVIOR_TRAFFIC:
            if (self.pos.x < -60 or self.pos.x > S.SCREEN_W + 60 or
                    self.pos.y < -60 or self.pos.y > S.FLIGHT_H + 60):
                self.alive = False
            return

        if ship is None or not ship.is_alive:
            return

        # After ~3s of wandering, check distance and decide to engage
        if self._state_t < 2.5:
            return

        dist = (ship.pos - self.pos).length()
        if dist < 280.0:
            self.state = ST_APPROACH
            self._state_t = 0.0

    def _tick_approach(self, dt: float, ship) -> None:
        if ship is None or not ship.is_alive:
            self.state = ST_DEPART
            self._state_t = 0.0
            return

        to_player = ship.pos - self.pos
        dist = to_player.length()
        if dist < 0.01:
            return

        # Epic 14.3 — Pilot give-up rule. Non-pirates that have spent 8s in
        # APPROACH at dist > 480px disengage. Pirates never give up.
        if self.behavior != BEHAVIOR_PIRATE:
            if dist > 480.0:
                self._approach_far_t = getattr(self, "_approach_far_t", 0.0) + dt
            else:
                self._approach_far_t = 0.0
            if getattr(self, "_approach_far_t", 0.0) >= 8.0:
                self.state = ST_DEPART
                self._state_t = 0.0
                self._approach_far_t = 0.0
                if not getattr(self, "_gave_up_fired", False):
                    self._gave_up_fired = True
                    bus.emit(EVT_BAX_SPEAK,
                             line="Lost interest. Lucky.")
                return

        # Steer velocity toward player but with the ship's own max thrust
        accel = 80.0 if self.behavior == BEHAVIOR_HAILER else 120.0
        desired_speed = 90.0 if self.behavior == BEHAVIOR_HAILER else 160.0
        dir_x, dir_y = to_player.x / dist, to_player.y / dist
        # Add wobble so motion feels hand-flown
        wob = math.sin(self._wobble_phase * 3.0) * 0.12
        nx = dir_x * math.cos(wob) - dir_y * math.sin(wob)
        ny = dir_x * math.sin(wob) + dir_y * math.cos(wob)
        target_vx = nx * desired_speed
        target_vy = ny * desired_speed
        self.vel.x += (target_vx - self.vel.x) * min(1.0, accel * dt / max(60.0, desired_speed))
        self.vel.y += (target_vy - self.vel.y) * min(1.0, accel * dt / max(60.0, desired_speed))

        # Range thresholds for next state
        if self.behavior == BEHAVIOR_HAILER and dist < 160.0:
            self.state = ST_HAIL
            self._state_t = 0.0
        elif self.behavior == BEHAVIOR_PIRATE and dist < 90.0:
            self.state = ST_ATTACK
            self._state_t = 0.0

    def _tick_hail(self, dt: float, ship) -> None:
        if ship is None or not ship.is_alive:
            self.state = ST_DEPART
            self._state_t = 0.0
            return

        # Match player velocity and ease in
        target_v = ship.body.vel
        ease = min(1.0, dt * 1.4)
        self.vel.x += (target_v.x - self.vel.x) * ease
        self.vel.y += (target_v.y - self.vel.y) * ease

        # Fire hail event once
        if not self._hail_fired:
            self._hail_fired = True
            npc_type = _HAIL_NPC_BY_CLASS.get(self.ship_class)
            if npc_type is not None:
                bus.emit(EVT_AISHIP_HAIL, ship=self, npc_type=npc_type,
                         ship_class=self.ship_class)

        # Hail window — 10s, then depart
        if self._state_t > 10.0:
            self.state = ST_DEPART
            self._state_t = 0.0

    def _tick_attack(self, dt: float, ship) -> None:
        if ship is None or not ship.is_alive:
            self.state = ST_DEPART
            self._state_t = 0.0
            return

        # Charge straight at player at high speed
        to_player = ship.pos - self.pos
        dist = to_player.length()
        if dist < 0.01:
            return
        dir_x, dir_y = to_player.x / dist, to_player.y / dist
        boost = 200.0
        self.vel.x += dir_x * boost * dt
        self.vel.y += dir_y * boost * dt

        # Ram damage on contact (once per attack window)
        if dist < self.radius + 14 and not self._has_hit_player:
            self._has_hit_player = True
            ship.take_damage(S.AISHIP_RAM_DAMAGE, source="ai_ship_ram")
            # Bounce off
            self.vel.x = -dir_x * 200.0
            self.vel.y = -dir_y * 200.0
            self.state = ST_DEPART
            self._state_t = 0.0

        # If we miss the pass (passed through and now moving away), depart
        if self._state_t > 4.0 and dist > 220.0:
            self.state = ST_DEPART
            self._state_t = 0.0

    def _tick_depart(self, dt: float) -> None:
        # Maintain velocity; no steering. Off-screen check is in update().
        return

    # ------------------------------------------------------------------
    def take_hit(self, damage: int = 1) -> bool:
        """Returns True when ship is destroyed."""
        self.hull -= damage
        self._hit_t = 0.18
        if self.hull <= 0:
            self.alive = False
            bus.emit(EVT_AISHIP_DESTROYED, ship=self)
            return True
        # Turn pirates into deserters when hurt
        if self.behavior == BEHAVIOR_PIRATE and self.hull <= 2:
            self.state = ST_DEPART
            self._state_t = 0.0
        return False

    @property
    def is_destroyed(self) -> bool:
        return not self.alive

    @property
    def is_hailer(self) -> bool:
        return self.behavior == BEHAVIOR_HAILER

    @property
    def is_pirate(self) -> bool:
        return self.behavior == BEHAVIOR_PIRATE
