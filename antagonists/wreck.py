"""
Space wrecks — large derelict vessels. Three sub-types:
  blocker     — pure obstacle, hull collision damage
  explorable  — navigable gap through middle; fuel/credits inside
  interactive — weak point; shooting it 3x triggers a side encounter
"""
from __future__ import annotations
import math
import random
from physics.body import Vec2
from config import settings as S

_WRECK_HULL_DAMAGE = S.DEBRIS_DAMAGE * 1.5
_WEAK_HITS_NEEDED  = 3


class SpaceWreck:
    SUBTYPE_BLOCKER     = "blocker"
    SUBTYPE_EXPLORABLE  = "explorable"
    SUBTYPE_INTERACTIVE = "interactive"

    def __init__(self, x: float | None = None, y: float | None = None,
                 subtype: str | None = None):
        self.pos     = Vec2(
            x if x is not None else random.randint(180, S.SCREEN_W - 180),
            y if y is not None else random.randint(100, S.FLIGHT_H - 100),
        )
        self.subtype  = subtype or random.choice([
            self.SUBTYPE_BLOCKER, self.SUBTYPE_EXPLORABLE, self.SUBTYPE_INTERACTIVE
        ])
        self.angle    = random.uniform(0, 360)
        self.rot_speed = random.uniform(-2, 2)   # very slow tumble

        # Size varies 120–200 px
        self.length   = random.randint(120, 200)
        self.width    = random.randint(40, 70)

        # Explorable: gap position (0.3–0.7 along length)
        self.gap_frac = random.uniform(0.3, 0.7)
        self.gap_w    = 32   # px wide gap

        # Interactive: weak-point hits remaining
        self.weak_hp  = _WEAK_HITS_NEEDED
        self.is_triggered = False
        self._trigger_t   = 0.0   # countdown after triggering

        # Colour: dim purple-grey, no fill
        self._col = (80, 60, 100)

    def update(self, dt: float):
        self.angle = (self.angle + self.rot_speed * dt) % 360
        if self._trigger_t > 0:
            self._trigger_t -= dt

    # ------------------------------------------------------------------
    def _hull_points(self) -> list[tuple[float, float]]:
        """Return rotated hull outline vertices (world space)."""
        hw, hh = self.length / 2, self.width / 2
        rad    = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
        pts = []
        for lx, ly in corners:
            wx = self.pos.x + lx * cos_a - ly * sin_a
            wy = self.pos.y + lx * sin_a + ly * cos_a
            pts.append((wx, wy))
        return pts

    def _gap_rect_world(self):
        """Return gap rect (cx, cy, half-width, half-height) in world space."""
        hw    = self.length / 2
        gx_l  = -hw + self.length * self.gap_frac - self.gap_w / 2
        gx_r  = gx_l + self.gap_w
        gcx   = (gx_l + gx_r) / 2
        rad   = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        wcx   = self.pos.x + gcx * cos_a
        wcy   = self.pos.y + gcx * sin_a
        return (wcx, wcy, self.gap_w / 2, self.width / 2)

    def collides(self, pos: Vec2, radius: float = 12.0) -> bool:
        """AABB collision in local space (rough but fast)."""
        dx = pos.x - self.pos.x
        dy = pos.y - self.pos.y
        rad = math.radians(-self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        lx = dx * cos_a - dy * sin_a
        ly = dx * sin_a + dy * cos_a
        hw, hh = self.length / 2 + radius, self.width / 2 + radius

        if abs(lx) > hw or abs(ly) > hh:
            return False

        # Explorable: skip gap region
        if self.subtype == self.SUBTYPE_EXPLORABLE:
            gap_cx = -self.length / 2 + self.length * self.gap_frac
            if abs(lx - gap_cx) < self.gap_w / 2 + radius:
                return False

        return True

    def hit_weak_point(self, bullet_pos: Vec2) -> bool:
        """Returns True when weak point is destroyed (3 hits)."""
        if self.subtype != self.SUBTYPE_INTERACTIVE or self.is_triggered:
            return False
        # Weak point at 20% from bow, centre-line
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        wplx = self.length * 0.2 - self.length / 2
        wpx  = self.pos.x + wplx * cos_a
        wpy  = self.pos.y + wplx * sin_a
        if (bullet_pos.x - wpx) ** 2 + (bullet_pos.y - wpy) ** 2 < 20 ** 2:
            self.weak_hp -= 1
            if self.weak_hp <= 0:
                self.is_triggered = True
                self._trigger_t   = 3.0
                return True
        return False

    @property
    def damage(self) -> float:
        return _WRECK_HULL_DAMAGE
