"""
Collapsing gravity well — one sector well whose mass ramps 800 → 3 500 over
the sector's lifetime.  Wraps an existing GravityWell from the ThreeBodySystem
so the physics engine picks up the change automatically.

Visual cues (read by vector_renderer via well.collapsing_pct):
  0.0  → normal well appearance
  1.0  → hue shifted fully to red, ring count expanded, rotation slowed
"""
from __future__ import annotations
import math
from physics.gravity import GravityWell, ThreeBodySystem

_START_MASS  = 800.0
_END_MASS    = 3_500.0
_DURATION    = 90.0   # ramp over ~full sector


class CollapsingGravityWell:
    def __init__(self, gravity: ThreeBodySystem):
        self._well: GravityWell | None = None
        if gravity.wells:
            # Pick the heaviest well so the one players already avoid gets worse.
            self._well = max(gravity.wells, key=lambda w: w.mass)
            self._orig_mass   = self._well.mass
            self._orig_radius = self._well.radius
            self._well.mass   = _START_MASS
            self._well.collapsing_pct = 0.0
        self._t = 0.0

    def update(self, dt: float):
        if self._well is None:
            return
        self._t = min(self._t + dt, _DURATION)
        pct = self._t / _DURATION
        self._well.mass           = _START_MASS + (_END_MASS - _START_MASS) * pct
        self._well.radius         = self._orig_radius + 30.0 * pct
        self._well.collapsing_pct = pct

    def reset(self):
        if self._well is not None:
            self._well.mass   = self._orig_mass
            self._well.radius = self._orig_radius
            self._well.collapsing_pct = 0.0

    @property
    def collapse_pct(self) -> float:
        return self._t / _DURATION
