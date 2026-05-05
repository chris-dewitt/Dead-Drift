from __future__ import annotations
import math
import pygame
from config import settings as S


class Vec2:
    """Thin 2D vector wrapper (avoids pygame.math.Vector2 import overhead)."""
    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y

    def __add__(self, o: Vec2)  -> Vec2: return Vec2(self.x + o.x, self.y + o.y)
    def __sub__(self, o: Vec2)  -> Vec2: return Vec2(self.x - o.x, self.y - o.y)
    def __mul__(self, s: float) -> Vec2: return Vec2(self.x * s, self.y * s)
    def __truediv__(self, s)    -> Vec2: return Vec2(self.x / s, self.y / s)
    def __neg__(self)           -> Vec2: return Vec2(-self.x, -self.y)

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def length_sq(self) -> float:
        return self.x * self.x + self.y * self.y

    def normalized(self) -> Vec2:
        l = self.length()
        return Vec2(self.x / l, self.y / l) if l > 0 else Vec2()

    def dot(self, o: Vec2) -> float:
        return self.x * o.x + self.y * o.y

    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

    def to_pygame(self) -> pygame.Vector2:
        return pygame.Vector2(self.x, self.y)

    @staticmethod
    def from_angle(degrees: float, magnitude: float = 1.0) -> Vec2:
        rad = math.radians(degrees)
        return Vec2(math.cos(rad) * magnitude, math.sin(rad) * magnitude)

    def __repr__(self) -> str:
        return f"Vec2({self.x:.2f}, {self.y:.2f})"


class RigidBody2D:
    """
    Newtonian point mass.  No friction — forces must be explicitly applied
    each frame and are cleared after integration.
    """

    def __init__(self, x: float = 0.0, y: float = 0.0, mass: float = 1.0):
        self.pos      = Vec2(x, y)
        self.vel      = Vec2()
        self.mass     = mass
        self._force   = Vec2()     # accumulator, reset each tick
        self.angle    = 0.0        # degrees, 0 = right

    # ------------------------------------------------------------------
    def apply_force(self, force: Vec2):
        self._force = self._force + force

    def apply_impulse(self, impulse: Vec2):
        """Instantaneous velocity change (bypasses mass)."""
        self.vel = self.vel + impulse

    def apply_thrust(self, magnitude: float):
        """Thrust in the direction the body is facing."""
        direction = Vec2.from_angle(self.angle, magnitude)
        self.apply_force(direction)

    def rotate(self, degrees: float):
        self.angle = (self.angle + degrees) % 360.0

    # ------------------------------------------------------------------
    def integrate(self, dt: float):
        """Symplectic Euler integration."""
        accel   = self._force * (1.0 / self.mass)
        self.vel = self.vel + accel * dt

        # Hard velocity cap — the ship frame can only take so much.
        speed = self.vel.length()
        if speed > S.MAX_VELOCITY:
            self.vel = self.vel * (S.MAX_VELOCITY / speed)

        self.pos = self.pos + self.vel * dt
        self._force = Vec2()   # reset accumulator

    # ------------------------------------------------------------------
    def speed(self) -> float:
        return self.vel.length()

    def facing_vector(self) -> Vec2:
        return Vec2.from_angle(self.angle)

    def __repr__(self) -> str:
        return f"RigidBody2D(pos={self.pos}, vel={self.vel}, angle={self.angle:.1f}°)"
