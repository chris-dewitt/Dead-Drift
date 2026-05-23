from __future__ import annotations
from physics.body import RigidBody2D, Vec2
from config import settings as S
from core.event_bus import bus, EVT_TETHER_HIT, EVT_TETHER_SNAP


class Tether:
    """
    Electromagnetic harpoon anchor between a RepoBarge and the PlayerShip.

    Behaviour:
    - Acts as a spring: pulls ship toward barge when over rest_length.
    - Snaps if ship velocity perpendicular component exceeds SNAP_VELOCITY
      (the "drift to snap" mechanic).
    - Snaps automatically if stretched beyond TETHER_MAX_LENGTH.
    """

    def __init__(self, ship: RigidBody2D, barge_pos: Vec2, barge_ref):
        self.ship         = ship
        self.barge_pos    = barge_pos   # updated each frame by the barge
        self.barge_ref    = barge_ref
        self.rest_len     = 80.0        # px — slack before tension kicks in
        self.active       = True
        self.lateral_speed = 0.0       # updated each frame — used for snap-charge HUD + tether glow

        bus.emit(EVT_TETHER_HIT, barge=barge_ref)

    # ------------------------------------------------------------------
    def update(self, dt: float):
        if not self.active:
            return

        delta   = self.barge_pos - self.ship.pos
        dist_sq = delta.length_sq()

        if dist_sq > S.TETHER_MAX_LENGTH * S.TETHER_MAX_LENGTH:
            self._snap("overextended")
            return

        if dist_sq > self.rest_len * self.rest_len:
            dist       = dist_sq ** 0.5
            # Spring force pulling ship toward barge
            stretch    = dist - self.rest_len
            force_dir  = delta * (1.0 / dist)   # normalized, avoids second sqrt
            force_mag  = S.TETHER_FORCE * stretch / S.TETHER_MAX_LENGTH
            self.ship.apply_force(force_dir * force_mag)

            # Check if player is drifting hard enough perpendicular to tether
            perp = Vec2(-force_dir.y, force_dir.x)
            self.lateral_speed = abs(self.ship.vel.dot(perp))
            if self.lateral_speed >= S.SNAP_VELOCITY:
                self._snap("drift")
        else:
            self.lateral_speed = 0.0

    def _snap(self, reason: str):
        self.active = False
        bus.emit(EVT_TETHER_SNAP, reason=reason, barge=self.barge_ref)

    @property
    def is_active(self) -> bool:
        return self.active
