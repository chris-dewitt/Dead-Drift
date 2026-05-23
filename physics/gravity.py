from __future__ import annotations
import math
from physics.body import RigidBody2D, Vec2
from config import settings as S

# Bounding box wells bounce inside (px from screen edges).
_WELL_MARGIN = 100
_WELL_MAX_SPEED = 30.0   # px/s cap on inter-well drift
_WELL_REPULSE_R = 80.0   # soft repulsion inside this radius


class GravityWell:
    """
    A massive body that pulls RigidBody2D objects toward its center.
    Uses Newton's law of universal gravitation scaled for gameplay.
    """

    def __init__(self, x: float, y: float, mass: float, radius: float = 60.0):
        self.pos    = Vec2(x, y)
        self.vel    = Vec2()      # wells can drift via three-body interactions
        self.mass   = mass
        self.radius = radius      # visual + collision radius

    def apply_to(self, body: RigidBody2D):
        delta     = self.pos - body.pos
        dist_sq   = delta.length_sq()

        if dist_sq < 1.0:
            return   # prevent singularity

        # Softening: inside 1.4x well radius, treat distance as that radius.
        # Uniform-sphere approximation — prevents the player getting trapped
        # in a force singularity when they overshoot a slingshot.
        soft_r    = self.radius * 1.4
        soft_sq   = soft_r * soft_r
        eff_sq    = max(dist_sq, soft_sq)

        force_mag = S.GRAVITY_CONSTANT * self.mass * body.mass / eff_sq
        # Cap force at 80% of thrust so a directed burn can always pull free.
        force_mag = min(force_mag, S.THRUSTER_FORCE * 0.8)

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
        """Mutual gravitational attraction between wells — three-body drift."""
        wells = self.wells
        if len(wells) < 2:
            return

        # Accumulate forces on each well from all others (15% of player-strength).
        forces = [Vec2() for _ in wells]
        for i, a in enumerate(wells):
            for j, b in enumerate(wells):
                if j <= i:
                    continue
                delta  = b.pos - a.pos
                dist_sq = delta.length_sq()
                if dist_sq < 1.0:
                    continue
                # Soft repulsion when wells get too close
                dist = math.sqrt(dist_sq)
                if dist < _WELL_REPULSE_R:
                    repulse = delta.normalized() * ((_WELL_REPULSE_R - dist) * 0.5)
                    forces[i] = forces[i] - repulse
                    forces[j] = forces[j] + repulse
                    continue
                # Mutual attraction at 15% player-attraction strength
                eff_sq   = max(dist_sq, (a.radius * 1.4) ** 2)
                fmag     = S.GRAVITY_CONSTANT * a.mass * b.mass / eff_sq * 0.15
                fmag     = min(fmag, S.THRUSTER_FORCE * 0.1)
                fdir     = delta.normalized() * fmag
                forces[i] = forces[i] + fdir
                forces[j] = forces[j] - fdir

        # Integrate well positions
        m = _WELL_MARGIN
        bx_lo, bx_hi = m, S.SCREEN_W - m
        by_lo, by_hi = m, S.FLIGHT_H - m

        for well, force in zip(wells, forces):
            well.vel = well.vel + force * dt
            # Cap well speed
            spd = well.vel.length()
            if spd > _WELL_MAX_SPEED:
                well.vel = well.vel * (_WELL_MAX_SPEED / spd)
            well.pos = well.pos + well.vel * dt
            # Bounce off bounding box
            if well.pos.x < bx_lo:
                well.pos.x  = bx_lo
                well.vel.x  = abs(well.vel.x)
            elif well.pos.x > bx_hi:
                well.pos.x  = bx_hi
                well.vel.x  = -abs(well.vel.x)
            if well.pos.y < by_lo:
                well.pos.y  = by_lo
                well.vel.y  = abs(well.vel.y)
            elif well.pos.y > by_hi:
                well.pos.y  = by_hi
                well.vel.y  = -abs(well.vel.y)

    def check_collisions(self, body: RigidBody2D) -> GravityWell | None:
        for well in self.wells:
            if well.is_colliding(body):
                return well
        return None
