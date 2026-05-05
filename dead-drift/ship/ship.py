from __future__ import annotations
import pygame
from physics.body import RigidBody2D, Vec2
from ship.loadout import SignalChain
from ship.modules.thruster import Thruster
from ship.modules.life_support import LifeSupport
from config import settings as S
from core.event_bus import bus, EVT_HULL_DAMAGE, EVT_HULL_CRITICAL, EVT_SHIP_DESTROYED


class PlayerShip:
    """
    The rust-bucket.  Owns the physics body, signal chain, and cargo slot.
    Input is sampled directly from pygame key state each frame.
    """

    def __init__(self):
        self.body       = RigidBody2D(S.SCREEN_W / 2, S.SCREEN_H / 2, mass=S.SHIP_MASS)
        self.hull       = S.HULL_MAX
        self.chain      = SignalChain()
        self.cargo      = None   # set by RunManager at run start
        self._destroyed = False

        # Default starting loadout
        self._thruster   = Thruster(tier="salvage")
        self._life_sup   = LifeSupport()
        self.chain.install(self._life_sup, 0)
        self.chain.install(self._thruster, 1)

    # ------------------------------------------------------------------
    def update(self, dt: float):
        if self._destroyed:
            return

        self._read_input(dt)
        self.chain.update(dt)
        self.body.integrate(dt)
        self._wrap_screen()

    def _read_input(self, dt: float):
        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            self.body.rotate(-S.ROTATION_SPEED * dt)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.body.rotate(S.ROTATION_SPEED * dt)

        thrusters = self.chain.get_active("propulsion")
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            for t in thrusters:
                self.body.apply_thrust(t.force * dt)

        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            for t in thrusters:
                self.body.apply_thrust(-t.force * 0.4 * dt)

    def _wrap_screen(self):
        """Toroidal wrapping — fly off one edge, appear at the other."""
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
        self.cargo      = None
