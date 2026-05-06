from __future__ import annotations
from physics.body import RigidBody2D, Vec2
from config import settings as S


class GravityWell:
    """
    A massive body that pulls RigidBody2D objects toward its center.
    Uses Newton's law of universal gravitation scaled for gameplay.
    """

    def __init__(self, x: float, y: float, mass: float, radius: float = 60.0):
        self.pos    = Vec2(x, y)
        self.mass   = mass
        self.radius = radius      # visual + collision radius

    def apply_to(self, body: RigidBody2D):
        delta     = self.pos - body.pos
        dist_sq   = delta.length_sq()

        if dist_sq < 1.0:
            return   # prevent singularity

        force_mag = S.GRAVITY_CONSTANT * self.mass * body.mass / dist_sq
        force     = delta.normalized() * force_mag
        body.apply_force(force)

    def is_colliding(self, body: RigidBody2D) -> bool:
        return (self.pos - body.pos).length() < self.radius

    def __repr__(self) -> str:
        return f"GravityWell(pos={self.pos}, mass={self.mass})"


class ThreeBodySystem:
    """
    Manages multiple gravity wells for procedural sector generation.
    Three-body orbital mechanics: all bodies attract each other.
    """

    def __init__(self, wells: list[GravityWell] | None = None):
        self.wells: list[GravityWell] = wells or []

    def add(self, well: GravityWell):
        self.wells.append(well)

    def apply_all(self, body: RigidBody2D):
        for well in self.wells:
            well.apply_to(body)

    def update(self, dt: float):
        """Wells attract each other (simplified — treat them as fixed for now)."""
        pass   # TODO: mutual attraction between wells for full three-body chaos

    def check_collisions(self, body: RigidBody2D) -> GravityWell | None:
        for well in self.wells:
            if well.is_colliding(body):
                return well
        return None
