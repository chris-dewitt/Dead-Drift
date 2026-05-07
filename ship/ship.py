from __future__ import annotations
import math
import pygame
from physics.body import RigidBody2D, Vec2
from ship.loadout import SignalChain
from ship.modules.thruster import Thruster
from ship.modules.life_support import LifeSupport
from ship.gun import Gun
from config import settings as S
from core.event_bus import bus, EVT_HULL_DAMAGE, EVT_HULL_CRITICAL, EVT_SHIP_DESTROYED


class PlayerShip:
    """
    The rust-bucket.  Owns the physics body, signal chain, gun, and cargo slot.
    Input is sampled directly from pygame key state each frame.
    """

    def __init__(self):
        self.body       = RigidBody2D(S.SCREEN_W / 2, S.SCREEN_H / 2, mass=S.SHIP_MASS)
        self.hull       = S.HULL_MAX
        self.chain      = SignalChain()
        self.gun        = Gun()
        self.cargo      = None
        self._destroyed = False
        self._thrusting = False   # set each frame; used for post-integrate RCS

        self._thruster  = Thruster(tier="salvage")
        self._life_sup  = LifeSupport()
        self.chain.install(self._life_sup, 0)
        self.chain.install(self._thruster, 1)

    # ------------------------------------------------------------------
    def update(self, dt: float):
        if self._destroyed:
            return

        self._read_input(dt)
        self.chain.update(dt)
        self.body.integrate(dt)

        # Post-integrate RCS: rotates velocity vector toward facing.
        # Happens AFTER the velocity cap so the redirect is never undone.
        if self._thrusting:
            self.body.redirect_velocity(
                self.body.facing_vector(), S.STEER_RCS_DEG, dt
            )

        self.gun.update(dt)
        self._wrap_screen()

    def _read_input(self, dt: float):
        keys = pygame.key.get_pressed()
        self._thrusting = False

        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            self.body.rotate(-S.ROTATION_SPEED * dt)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.body.rotate(S.ROTATION_SPEED * dt)

        thrusters = self.chain.get_active("propulsion")
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self._thrusting = True
            for t in thrusters:
                self.body.apply_thrust(t.force)

        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            for t in thrusters:
                self.body.apply_thrust(-t.force * 0.4)

        if keys[pygame.K_SPACE]:
            rad = math.radians(self.body.angle)
            nose = Vec2(self.body.pos.x + math.cos(rad) * 22,
                        self.body.pos.y + math.sin(rad) * 22)
            self.gun.fire(nose, self.body.angle)

    def _wrap_screen(self):
        pos = self.body.pos
        if pos.x < 0:            pos.x = S.SCREEN_W
        elif pos.x > S.SCREEN_W: pos.x = 0
        if pos.y < 0:            pos.y = S.SCREEN_H
        elif pos.y > S.SCREEN_H: pos.y = 0

    # ------------------------------------------------------------------
    def take_damage(self, amount: float):
        self.hull = max(0.0, self.hull - amount)
        bus.emit(EVT_HULL_DAMAGE, amount=amount)
        if self.hull <= S.HUD_SCRAMBLE_HP:
            bus.emit(EVT_HULL_CRITICAL, hp=self.hull)
        if self.hull <= 0.0 and not self._destroyed:
            self._destroyed = True
            bus.emit(EVT_SHIP_DESTROYED)

    def repair(self, amount: float):
        self.hull = min(S.HULL_MAX, self.hull + amount)

    # ------------------------------------------------------------------
    @property
    def hull_pct(self) -> float:
        return self.hull / S.HULL_MAX

    @property
    def pos(self) -> Vec2:
        return self.body.pos

    @property
    def angle(self) -> float:
        return self.body.angle

    @property
    def velocity(self) -> Vec2:
        return self.body.vel

    @property
    def is_alive(self) -> bool:
        return not self._destroyed

    def reset(self):
        self.body       = RigidBody2D(S.SCREEN_W / 2, S.SCREEN_H / 2, mass=S.SHIP_MASS)
        self.hull       = S.HULL_MAX
        self._destroyed = False
        self._thrusting = False
        self.cargo      = None
        self.gun        = Gun()
