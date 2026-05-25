"""
Reusable element classes for all delivery corridors.
All positions are in world-space; callers pass camera_x when drawing.
"""
from __future__ import annotations
import math
import random
import pygame

from renderer.sci_fi_ui import draw_mario_brick_platform
from core.text import get_font

CORRIDOR_W = 400
CORRIDOR_H = 360
FLOOR_Y    = 320
CEIL_Y     = 40
PLAYER_H   = 32
PLAYER_W   = 18


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Element:
    """Abstract base for all corridor elements."""
    def __init__(self, x: float, path_tag: str | None = None):
        self.x        = x
        self.path_tag = path_tag  # None / "high" / "low"
        self.active   = True

    def update(self, dt: float, player_x: float, player_y: float) -> None:
        pass

    def draw(self, surf: pygame.Surface, camera_x: float, t: float,
             palette: dict) -> None:
        pass


# ---------------------------------------------------------------------------
# Platforms
# ---------------------------------------------------------------------------

class Platform(Element):
    """Static walkable platform."""
    def __init__(self, x: float, y: float, w: int, h: int = 12,
                 path_tag: str | None = None):
        super().__init__(x, path_tag)
        self.y  = y
        self.w  = w
        self.h  = h

    def collides_top(self, px: float, py: float, pvy: float) -> bool:
        if not (self.x - self.w // 2 - PLAYER_W // 2 < px
                < self.x + self.w // 2 + PLAYER_W // 2):
            return False
        return (pvy >= 0
                and py + PLAYER_H >= self.y
                and py + PLAYER_H <= self.y + self.h + 14)

    def draw(self, surf, camera_x, t, palette):
        sx = int(self.x - camera_x)
        brick = palette.get("brick", palette.get("platform", (140, 70, 20)))
        hi = palette.get("brick_hi", palette.get("platform_hi", (220, 140, 40)))
        draw_mario_brick_platform(surf, sx, int(self.y), self.w, self.h, brick, hi, t)


class MovingPlatform(Element):
    """Patrol platform — moves between two x positions at fixed y."""
    W, H = 90, 12

    def __init__(self, x: float, y: float, left: float, right: float,
                 speed: float = 60.0, path_tag: str | None = None):
        super().__init__(x, path_tag)
        self.y      = y
        self._left  = left
        self._right = right
        self._speed = speed
        self._dir   = 1

    def update(self, dt, player_x, player_y):
        self.x += self._dir * self._speed * dt
        if self.x >= self._right:
            self.x   = self._right
            self._dir = -1
        elif self.x <= self._left:
            self.x   = self._left
            self._dir = 1

    def collides_top(self, px: float, py: float, pvy: float) -> bool:
        if abs(px - self.x) > self.W // 2 + PLAYER_W // 2:
            return False
        return (pvy >= 0
                and py + PLAYER_H >= self.y
                and py + PLAYER_H <= self.y + self.H + 14)

    def draw(self, surf, camera_x, t, palette):
        sx = int(self.x - camera_x)
        brick = palette.get("moving_platform", (60, 100, 180))
        hi = palette.get("moving_platform_hi", (120, 200, 255))
        draw_mario_brick_platform(surf, sx, int(self.y), self.W, self.H, brick, hi, t)
        ax = sx + (14 if self._dir > 0 else -14)
        pygame.draw.polygon(surf, (255, 255, 200),
                            [(ax - 5 * self._dir, int(self.y) + 2),
                             (ax + 5 * self._dir, int(self.y) + 6),
                             (ax - 5 * self._dir, int(self.y) + 10)])


class CollapsingPlatform(Element):
    """Stable until stepped on; collapses 0.6s after contact, respawns 4s later."""
    W, H = 80, 10

    def __init__(self, x: float, y: float, path_tag: str | None = None):
        super().__init__(x, path_tag)
        self.y       = y
        self._state  = "stable"   # stable | shaking | collapsed
        self._timer  = 0.0
        self._shake  = 0.0

    def step_on(self):
        if self._state == "stable":
            self._state = "shaking"
            self._timer = 0.6

    def update(self, dt, player_x, player_y):
        if self._state == "shaking":
            self._timer -= dt
            self._shake = (random.random() - 0.5) * 4
            if self._timer <= 0:
                self._state = "collapsed"
                self._timer = 4.0
        elif self._state == "collapsed":
            self._timer -= dt
            if self._timer <= 0:
                self._state = "stable"
                self._shake = 0.0

    def collides_top(self, px: float, py: float, pvy: float) -> bool:
        if self._state == "collapsed":
            return False
        if abs(px - self.x) > self.W // 2 + PLAYER_W // 2:
            return False
        return (pvy >= 0
                and py + PLAYER_H >= self.y
                and py + PLAYER_H <= self.y + self.H + 14)

    def draw(self, surf, camera_x, t, palette):
        if self._state == "collapsed":
            return
        sx  = int(self.x - camera_x + self._shake)
        col = palette.get("collapsing", (180, 100, 0)) if self._state == "shaking" \
              else palette.get("platform", (0, 140, 70))
        hi  = (255, 160, 0) if self._state == "shaking" \
              else palette.get("platform_hi", (0, 200, 100))
        pygame.draw.rect(surf, col,
                         (sx - self.W // 2, int(self.y), self.W, self.H))
        pygame.draw.rect(surf, hi,
                         (sx - self.W // 2, int(self.y), self.W, self.H), 1)


class Ladder(Element):
    """Vertical traversal element. Player must overlap and press UP/DOWN."""
    W = 14

    def __init__(self, x: float, y_top: float, y_bot: float,
                 path_tag: str | None = None):
        super().__init__(x, path_tag)
        self.y_top = y_top
        self.y_bot = y_bot

    def overlaps(self, px: float, py: float) -> bool:
        return (abs(px - self.x) < self.W
                and py < self.y_bot and py + PLAYER_H > self.y_top)

    def draw(self, surf, camera_x, t, palette):
        sx  = int(self.x - camera_x)
        col = palette.get("ladder", (160, 120, 60))
        # Uprights
        for ox in (-self.W // 2, self.W // 2):
            pygame.draw.line(surf, col,
                             (sx + ox, int(self.y_top)),
                             (sx + ox, int(self.y_bot)), 2)
        # Rungs
        rung_y = self.y_top + 12
        while rung_y < self.y_bot:
            pygame.draw.line(surf, col,
                             (sx - self.W // 2, int(rung_y)),
                             (sx + self.W // 2, int(rung_y)), 1)
            rung_y += 18


# ---------------------------------------------------------------------------
# Hazards
# ---------------------------------------------------------------------------

class Hazard(Element):
    """Static damage zone."""
    def __init__(self, x: float, y: float, w: int, h: int,
                 label: str = "", path_tag: str | None = None):
        super().__init__(x, path_tag)
        self.y     = y
        self.w     = w
        self.h     = h
        self.label = label

    def collides(self, px: float, py: float) -> bool:
        return (self.x - self.w // 2 < px < self.x + self.w // 2
                and py < self.y + self.h and py + PLAYER_H > self.y)

    def draw(self, surf, camera_x, t, palette):
        sx    = int(self.x - camera_x)
        pulse = int(180 + 75 * math.sin(t * 6.0))
        col   = (pulse, int(pulse * 0.2), 0)
        pygame.draw.rect(surf, (40, 8, 8),
                         (sx - self.w // 2, int(self.y), self.w, self.h))
        pygame.draw.rect(surf, col,
                         (sx - self.w // 2, int(self.y), self.w, self.h), 1)
        # Hazard chevrons
        for i in range(0, self.w - 10, 16):
            x0 = sx - self.w // 2 + i
            pygame.draw.line(surf, col,
                             (x0, int(self.y) + self.h),
                             (x0 + 8, int(self.y)), 1)


class MovingHazard(Element):
    """Patrol damage zone — moves between two x positions."""
    def __init__(self, x: float, y: float, w: int, h: int,
                 left: float, right: float, speed: float = 55.0,
                 path_tag: str | None = None):
        super().__init__(x, path_tag)
        self.y      = y
        self.w      = w
        self.h      = h
        self._left  = left
        self._right = right
        self._speed = speed
        self._dir   = 1

    def update(self, dt, player_x, player_y):
        self.x += self._dir * self._speed * dt
        if self.x >= self._right:
            self.x    = self._right
            self._dir = -1
        elif self.x <= self._left:
            self.x    = self._left
            self._dir = 1

    def collides(self, px: float, py: float) -> bool:
        return (abs(px - self.x) < self.w // 2 + PLAYER_W // 2
                and py < self.y + self.h and py + PLAYER_H > self.y)

    def draw(self, surf, camera_x, t, palette):
        sx    = int(self.x - camera_x)
        pulse = int(160 + 60 * math.sin(t * 5.0))
        col   = (pulse, int(pulse * 0.15), 0)
        pygame.draw.rect(surf, (50, 10, 10),
                         (sx - self.w // 2, int(self.y), self.w, self.h))
        pygame.draw.rect(surf, col,
                         (sx - self.w // 2, int(self.y), self.w, self.h), 2)
        # Blinking warning light on top
        if abs(math.sin(t * 4.0)) > 0.6:
            pygame.draw.circle(surf, (255, 80, 80),
                               (sx, int(self.y) - 4), 3)


class ToggleBeam(Element):
    """Hazard beam that toggles on/off on a timed cycle (Chapter 2)."""
    def __init__(self, x: float, w: float, y: float,
                 period: float = 1.5, phase: float = 0.0,
                 path_tag: str | None = None):
        super().__init__(x, path_tag)
        self.w      = w
        self.y      = y
        self._period = period
        self._phase  = phase

    def _is_on(self, t: float) -> bool:
        return math.sin(2 * math.pi * t / self._period + self._phase) > 0

    def collides(self, px: float, py: float, t: float) -> bool:
        if not self._is_on(t):
            return False
        if not (self.x - self.w / 2 < px < self.x + self.w / 2):
            return False
        return self.y - 10 < py + PLAYER_H / 2 < self.y + 10

    def draw(self, surf, camera_x, t, palette):
        sx  = int(self.x - camera_x)
        x0  = sx - int(self.w / 2)
        x1  = sx + int(self.w / 2)
        if self._is_on(t):
            col = (120, 0, 255)
            pygame.draw.line(surf, col, (x0, int(self.y)), (x1, int(self.y)), 4)
            pygame.draw.line(surf, (180, 80, 255),
                             (x0, int(self.y) - 1), (x1, int(self.y) - 1), 1)
        else:
            pygame.draw.line(surf, (40, 10, 60),
                             (x0, int(self.y)), (x1, int(self.y)), 1)
        # End brackets
        for ex in (x0, x1):
            pygame.draw.rect(surf, (80, 30, 120), (ex - 3, int(self.y) - 8, 6, 16))


class OneWayWall(Element):
    """Cubicle wall that blocks movement from one direction (Chapter 3)."""
    def __init__(self, x: float, y_top: float, y_bot: float,
                 blocks_right: bool = True, path_tag: str | None = None):
        super().__init__(x, path_tag)
        self.y_top       = y_top
        self.y_bot       = y_bot
        self.blocks_right = blocks_right

    def blocks(self, px: float, py: float, vx: float) -> bool:
        if py + PLAYER_H <= self.y_top or py >= self.y_bot:
            return False
        if self.blocks_right and vx > 0:
            return abs(px - self.x) < PLAYER_W // 2 + 2
        if not self.blocks_right and vx < 0:
            return abs(px - self.x) < PLAYER_W // 2 + 2
        return False

    def draw(self, surf, camera_x, t, palette):
        sx  = int(self.x - camera_x)
        col = palette.get("wall", (60, 60, 60))
        pygame.draw.line(surf, col,
                         (sx, int(self.y_top)), (sx, int(self.y_bot)), 3)
        # Arrow indicating allowed direction
        mid_y = int((self.y_top + self.y_bot) / 2)
        d = -1 if self.blocks_right else 1
        pygame.draw.polygon(surf, (120, 120, 120),
                            [(sx + d * 8, mid_y),
                             (sx + d * 2, mid_y - 5),
                             (sx + d * 2, mid_y + 5)])


# ---------------------------------------------------------------------------
# Interactive elements
# ---------------------------------------------------------------------------

class NPCEncounter(Element):
    """Triggers a mini inline dialog when courier walks into trigger zone."""
    TRIGGER_W = 60

    def __init__(self, x: float, npc_name: str, prompt: str,
                 responses: list[dict], path_tag: str | None = None):
        super().__init__(x, path_tag)
        self.npc_name  = npc_name
        self.prompt    = prompt
        self.responses = responses   # list of {keywords, credits, lore, outcome}
        self._triggered = False
        self._done      = False

    @property
    def triggered(self) -> bool:
        return self._triggered and not self._done

    def trigger(self):
        if not self._triggered and not self._done:
            self._triggered = True

    def complete(self):
        self._done = True

    def collides_trigger(self, px: float) -> bool:
        return (not self._done
                and abs(px - self.x) < self.TRIGGER_W)

    def draw(self, surf, camera_x, t, palette):
        if self._done:
            return
        sx  = int(self.x - camera_x)
        pul = int(140 + 60 * math.sin(t * 3.0))
        col = (0, pul, int(pul * 0.5))
        # Marker diamond
        pygame.draw.polygon(surf, col,
                            [(sx, FLOOR_Y - 60),
                             (sx + 10, FLOOR_Y - 50),
                             (sx, FLOOR_Y - 40),
                             (sx - 10, FLOOR_Y - 50)])
        pygame.draw.polygon(surf, (0, 255, 140),
                            [(sx, FLOOR_Y - 60),
                             (sx + 10, FLOOR_Y - 50),
                             (sx, FLOOR_Y - 40),
                             (sx - 10, FLOOR_Y - 50)], 1)
        f = get_font(9)
        s = f.render(self.npc_name[:8], True, col)
        surf.blit(s, (sx - s.get_width() // 2, FLOOR_Y - 78))


class Collectible(Element):
    """Credit chip. Touch to collect."""
    def __init__(self, x: float, y: float, value: int = 200,
                 path_tag: str | None = None):
        super().__init__(x, path_tag)
        self.y         = y
        self.value     = value
        self._collected = False

    def try_collect(self, px: float, py: float) -> int:
        if self._collected:
            return 0
        if abs(px - self.x) < 22 and abs((py + PLAYER_H / 2) - self.y) < 22:
            self._collected = True
            return self.value
        return 0

    def draw(self, surf, camera_x, t, palette):
        if self._collected:
            return
        sx  = int(self.x - camera_x)
        sy  = int(self.y)
        pul = 0.7 + 0.3 * math.sin(t * 4.0)
        col = (int(255 * pul), int(210 * pul), 0)
        pygame.draw.polygon(surf, col,
                            [(sx, sy - 8), (sx + 8, sy),
                             (sx, sy + 8), (sx - 8, sy)])
        pygame.draw.polygon(surf, (255, 255, 180),
                            [(sx, sy - 8), (sx + 8, sy),
                             (sx, sy + 8), (sx - 8, sy)], 1)


class Secret(Element):
    """Off-path secret — credits or lore fragment."""
    def __init__(self, x: float, y: float, value: int = 500,
                 lore: str = "", path_tag: str | None = None):
        super().__init__(x, path_tag)
        self.y          = y
        self.value      = value
        self.lore       = lore
        self._collected = False

    def try_collect(self, px: float, py: float) -> tuple[int, str]:
        if self._collected:
            return 0, ""
        if abs(px - self.x) < 24 and abs((py + PLAYER_H / 2) - self.y) < 24:
            self._collected = True
            return self.value, self.lore
        return 0, ""

    def draw(self, surf, camera_x, t, palette):
        if self._collected:
            return
        sx  = int(self.x - camera_x)
        sy  = int(self.y)
        # Pulsing star shape
        pul = 0.5 + 0.5 * abs(math.sin(t * 2.5))
        col = (int(200 * pul), int(160 * pul), int(255 * pul))
        for a in range(5):
            ang  = math.radians(a * 72 - 90)
            ang2 = math.radians(a * 72 + 36 - 90)
            p1 = (sx + int(10 * math.cos(ang)),  sy + int(10 * math.sin(ang)))
            p2 = (sx + int(4  * math.cos(ang2)), sy + int(4  * math.sin(ang2)))
            p3 = (sx + int(10 * math.cos(math.radians((a + 1) * 72 - 90))),
                  sy + int(10 * math.sin(math.radians((a + 1) * 72 - 90))))
            pygame.draw.polygon(surf, col, [p1, p2, p3])
        f = get_font(7)
        s = f.render("★", True, col)
        surf.blit(s, (sx - s.get_width() // 2, sy - 22))


class Checkpoint(Element):
    """Banner. Courier passing it sets respawn point."""
    def __init__(self, x: float, path_tag: str | None = None):
        super().__init__(x, path_tag)
        self._passed = False

    def check_pass(self, px: float) -> bool:
        if not self._passed and px > self.x:
            self._passed = True
            return True
        return False

    def draw(self, surf, camera_x, t, palette):
        sx  = int(self.x - camera_x)
        col = (0, 200, 100) if self._passed else (200, 200, 0)
        pygame.draw.line(surf, col, (sx, CEIL_Y), (sx, FLOOR_Y), 2)
        # Banner
        pygame.draw.rect(surf, col, (sx, CEIL_Y + 10, 50, 16))
        f = get_font(9, bold=True)
        s = f.render("SAVE", True, (0, 0, 0))
        surf.blit(s, (sx + 4, CEIL_Y + 12))


class StealthZone(Element):
    """Detection zone with sweeping light cone(s). Detection = damage + retreat."""

    def __init__(self, x: float, y: float, w: int, h: int,
                 patrols: list[dict], path_tag: str | None = None):
        """
        patrols: list of {ox, oy, angle_min, angle_max, speed, cone_deg, range}
          All angles in degrees. cone_deg is full width of cone.
        """
        super().__init__(x, path_tag)
        self.y       = y
        self.w       = w
        self.h       = h
        self._agents = []
        for p in patrols:
            self._agents.append({
                "ox":        float(p["ox"]),
                "oy":        float(p["oy"]),
                "angle":     float(p.get("angle_min", -60)),
                "angle_min": float(p["angle_min"]),
                "angle_max": float(p["angle_max"]),
                "speed":     float(p.get("speed", 30)),
                "dir":       1,
                "cone_deg":  float(p.get("cone_deg", 40)),
                "range":     float(p.get("range", 160)),
            })

    def update(self, dt, player_x, player_y):
        for a in self._agents:
            a["angle"] += a["dir"] * a["speed"] * dt
            if a["angle"] >= a["angle_max"]:
                a["angle"] = a["angle_max"]
                a["dir"]   = -1
            elif a["angle"] <= a["angle_min"]:
                a["angle"] = a["angle_min"]
                a["dir"]   = 1

    def detects(self, px: float, py: float) -> bool:
        if not (self.x <= px <= self.x + self.w
                and self.y <= py + PLAYER_H / 2 <= self.y + self.h):
            return False
        for a in self._agents:
            ax  = self.x + a["ox"]
            ay  = self.y + a["oy"]
            dx  = px - ax
            dy  = (py + PLAYER_H / 2) - ay
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > a["range"]:
                continue
            player_angle = math.degrees(math.atan2(dy, dx))
            # Normalise to [-180, 180]
            diff = (player_angle - a["angle"] + 180) % 360 - 180
            if abs(diff) <= a["cone_deg"] / 2:
                return True
        return False

    def draw(self, surf, camera_x, t, palette):
        sx = int(self.x - camera_x)
        # Zone tint
        z = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        z.fill((200, 0, 0, 12))
        surf.blit(z, (sx, int(self.y)))

        for a in self._agents:
            ax = int(sx + a["ox"])
            ay = int(self.y + a["oy"])
            r  = int(a["range"])
            half_c = math.radians(a["cone_deg"] / 2)
            ang_r  = math.radians(a["angle"])
            # Cone polygon
            pts = [(ax, ay)]
            for da in range(-int(a["cone_deg"] / 2), int(a["cone_deg"] / 2) + 1, 4):
                fa = ang_r + math.radians(da)
                pts.append((ax + int(r * math.cos(fa)),
                             ay + int(r * math.sin(fa))))
            if len(pts) >= 3:
                cone_surf = pygame.Surface((CORRIDOR_W, CORRIDOR_H), pygame.SRCALPHA)
                pygame.draw.polygon(cone_surf, (255, 220, 0, 35), pts)
                surf.blit(cone_surf, (0, 0))
                pygame.draw.polygon(surf, (180, 150, 0, 80), pts, 1)
            # Patroller body
            pygame.draw.circle(surf, (200, 160, 0), (ax, ay), 8)
            pygame.draw.circle(surf, (255, 200, 0), (ax, ay), 8, 1)


class BossRoomTrigger(Element):
    """Entry to the final boss room — fires Bax line once."""
    def __init__(self, x: float, bax_line: str = "", path_tag: str | None = None):
        super().__init__(x, path_tag)
        self.bax_line = bax_line
        self._fired   = False

    def check(self, px: float) -> bool:
        if not self._fired and px > self.x:
            self._fired = True
            return True
        return False

    def draw(self, surf, camera_x, t, palette):
        sx = int(self.x - camera_x)
        pul = int(180 + 75 * math.sin(t * 2.0))
        col = (pul, int(pul * 0.5), 0)
        pygame.draw.line(surf, col, (sx, CEIL_Y), (sx, FLOOR_Y), 3)
        f = get_font(9, bold=True)
        s = f.render("BOSS", True, col)
        surf.blit(s, (sx + 4, CEIL_Y + 4))


# ---------------------------------------------------------------------------
# Epic 14.1 — Boss room set-piece tableau
# ---------------------------------------------------------------------------

class BossRoomActor(Element):
    """A pure-render boss-room set piece.

    Each chapter's final room slots in one of these to give the boss
    encounter physical presence (Gary doing something absurd, the
    mycelium chamber breathing, three Form 7-B officials, the quantum
    observation deck). The draw function receives `(surf, sx, t,
    palette)` where `sx` is the screen-space x of the actor's anchor.
    """
    def __init__(self, x: float, draw_fn, path_tag: str | None = None):
        super().__init__(x, path_tag)
        self._draw_fn = draw_fn

    def draw(self, surf, camera_x, t, palette):
        sx = int(self.x - camera_x)
        if -240 < sx < CORRIDOR_W + 240:
            try:
                self._draw_fn(surf, sx, t, palette)
            except Exception:
                pass


def boss_actor_gary_den(surf, sx, t, palette):
    """Ch.1 — Gary at his desk, mid-microwave-meal, harpoon controller down.

    Gary is leaned back, harpoon controller dropped on the desk, eating
    a microwave meal. His radio is playing static blues. A 'NOT NOW'
    sign hangs on the wall behind him. This is the most off-duty
    Gary will ever look on the job."""
    # Desk
    desk_y = FLOOR_Y - 36
    pygame.draw.rect(surf, (90, 50, 20),
                     pygame.Rect(sx - 50, desk_y, 110, 32))
    pygame.draw.rect(surf, (140, 80, 30),
                     pygame.Rect(sx - 50, desk_y, 110, 32), 2)
    # Microwave meal — steam wisps
    pygame.draw.rect(surf, (160, 120, 40),
                     pygame.Rect(sx - 18, desk_y - 8, 22, 8))
    pygame.draw.rect(surf, (200, 160, 60),
                     pygame.Rect(sx - 18, desk_y - 8, 22, 8), 1)
    for i in range(3):
        sw_y = desk_y - 14 - int(6 * abs(math.sin(t * 1.4 + i)))
        pygame.draw.line(surf, (200, 200, 220),
                         (sx - 14 + i * 8, sw_y),
                         (sx - 14 + i * 8, sw_y - 6), 1)
    # Harpoon controller — tossed casually on the desk (cable trailing)
    pygame.draw.rect(surf, (60, 60, 80),
                     pygame.Rect(sx + 12, desk_y - 4, 36, 6))
    pygame.draw.line(surf, (80, 80, 100),
                     (sx + 12, desk_y - 1), (sx - 4, desk_y + 14), 1)
    # Gary — leaned back, head + body silhouette
    body_y = desk_y - 30
    pygame.draw.rect(surf, (210, 140, 50),
                     pygame.Rect(sx - 14, body_y, 28, 30))   # hi-vis torso
    pygame.draw.circle(surf, (230, 200, 170),
                       (sx, body_y - 10), 10)                 # head
    # Eyes — closed (eating)
    pygame.draw.line(surf, (40, 40, 30),
                     (sx - 4, body_y - 12), (sx, body_y - 12), 1)
    pygame.draw.line(surf, (40, 40, 30),
                     (sx + 1, body_y - 12), (sx + 5, body_y - 12), 1)
    # 'NOT NOW' sign hung on the wall
    sign_y = CEIL_Y + 30
    sign_rect = pygame.Rect(sx - 30, sign_y, 60, 20)
    pygame.draw.rect(surf, (60, 30, 30), sign_rect)
    pygame.draw.rect(surf, (220, 80, 60), sign_rect, 1)
    f = get_font(8, bold=True)
    sg = f.render("NOT NOW", True, (220, 80, 60))
    surf.blit(sg, (sign_rect.centerx - sg.get_width() // 2,
                   sign_rect.centery - sg.get_height() // 2))
    # Radio — flickering speaker glow
    rad_y = desk_y - 6
    pygame.draw.rect(surf, (40, 40, 50),
                     pygame.Rect(sx + 50, rad_y, 22, 14))
    pulse = 0.5 + 0.5 * math.sin(t * 5.0)
    pygame.draw.circle(surf, (int(200 * pulse), int(80 * pulse), 30),
                       (sx + 61, rad_y + 7), 3)


def boss_actor_mycelium_chamber(surf, sx, t, palette):
    """Ch.2 — the walls are *alive*. Bioluminescent threads, breathing pulse.

    Three pulsing nodes sprout from the walls + ceiling, each connected
    by glowing fungal threads. A panicking researcher stands centre,
    hands on head, while spore motes drift across the room."""
    breath = 0.55 + 0.45 * math.sin(t * 1.2)
    glow_col = (int(80 * breath), int(220 * breath), int(140 * breath))
    # Three nodes
    for off in (-100, 0, 100):
        nx = sx + off
        ny = CEIL_Y + 24 + int(6 * math.sin(t * 1.4 + off * 0.04))
        pygame.draw.circle(surf, glow_col, (nx, ny), 14, 0)
        pygame.draw.circle(surf, (180, 255, 200), (nx, ny), 5, 0)
        # Threads — spiral down toward floor
        for k in range(3):
            angle = t * 0.6 + k * math.tau / 3 + off * 0.01
            ex = nx + int(40 * math.cos(angle))
            ey = ny + 60 + int(20 * math.sin(angle * 1.3))
            pygame.draw.line(surf, glow_col, (nx, ny), (ex, ey), 1)
    # Spore motes drifting
    for i in range(8):
        mx = (sx - 60 + (t * 30 + i * 30) % 240)
        my = CEIL_Y + 80 + int(20 * math.sin(t * 1.1 + i * 0.7))
        pygame.draw.circle(surf, (120, 220, 100, 220), (int(mx), int(my)), 1)
    # Researcher silhouette — hands on head
    rx, ry = sx - 6, FLOOR_Y - 38
    pygame.draw.rect(surf, (210, 210, 220),
                     pygame.Rect(rx - 7, ry, 14, 26))         # lab coat
    pygame.draw.circle(surf, (220, 200, 180),
                       (rx, ry - 8), 6)                         # head
    # Hands on head — angled
    pygame.draw.line(surf, (220, 200, 180),
                     (rx - 4, ry), (rx - 8, ry - 14), 2)
    pygame.draw.line(surf, (220, 200, 180),
                     (rx + 4, ry), (rx + 8, ry - 14), 2)


def boss_actor_compliance_tribunal(surf, sx, t, palette):
    """Ch.3 — three officials behind a panel, reading Form 7-B aloud.

    Three identical silhouettes at a long table. Their heads scan
    in slow sync. A 'FORM 7-B' header floats overhead. A small podium
    in front holds the form being read. They never look up."""
    # Long bench
    bench_y = FLOOR_Y - 30
    bench_rect = pygame.Rect(sx - 90, bench_y, 180, 28)
    pygame.draw.rect(surf, (120, 100, 60), bench_rect)
    pygame.draw.rect(surf, (180, 160, 90), bench_rect, 2)
    # Three officials
    for i, off in enumerate((-60, 0, 60)):
        ox = sx + off
        # Body — grey suit
        pygame.draw.rect(surf, (90, 90, 110),
                         pygame.Rect(ox - 12, bench_y - 30, 24, 30))
        # Head — slight scan rotation, in sync
        scan = math.sin(t * 0.9) * 4
        pygame.draw.circle(surf, (230, 220, 200),
                           (int(ox + scan), bench_y - 40), 8)
        # Glasses
        pygame.draw.rect(surf, (40, 40, 60),
                         pygame.Rect(int(ox + scan) - 7, bench_y - 41, 14, 4),
                         1)
        # Form clutched in front
        pygame.draw.rect(surf, (240, 230, 200),
                         pygame.Rect(ox - 6, bench_y - 6, 12, 14))
    # FORM 7-B header
    f = get_font(11, bold=True)
    hdr = f.render("FORM 7-B :: COMPLIANCE TRIBUNAL", True, (180, 200, 80))
    surf.blit(hdr, (sx - hdr.get_width() // 2, CEIL_Y + 18))
    # Stamp pulse — 'APPROVED / DENIED' alternating in red, low
    stamp = "APPROVED" if int(t) % 2 == 0 else "DENIED"
    stamp_col = (60, 200, 90) if stamp == "APPROVED" else (200, 80, 60)
    sf = get_font(9, bold=True)
    ss = sf.render(stamp, True, stamp_col)
    surf.blit(ss, (sx - ss.get_width() // 2, CEIL_Y + 36))


def boss_actor_quantum_observation(surf, sx, t, palette):
    """Ch.4 — the observation deck. A box on a pedestal. Reality flickers.

    A central crate sits on a low pedestal. The crate's lid jitters
    between open and closed faster than the eye can catch. A '?' icon
    flicks between visible and not. Spectator silhouettes line the
    back wall. The room palette periodically glitches to its inverse
    for a single frame — 'observation collapses payout' made visual."""
    # Pedestal
    pad_y = FLOOR_Y - 18
    pygame.draw.rect(surf, (180, 160, 100),
                     pygame.Rect(sx - 30, pad_y, 60, 18))
    pygame.draw.rect(surf, (240, 220, 140),
                     pygame.Rect(sx - 30, pad_y, 60, 18), 2)
    # The box itself — superposition flicker
    box_y = pad_y - 32
    flicker = (t * 9.0) % 1.0
    if flicker < 0.5:
        # Closed
        pygame.draw.rect(surf, (40, 24, 60),
                         pygame.Rect(sx - 18, box_y, 36, 32))
        pygame.draw.rect(surf, (180, 130, 220),
                         pygame.Rect(sx - 18, box_y, 36, 32), 2)
        f = get_font(14, bold=True)
        q = f.render("?", True, (220, 180, 255))
        surf.blit(q, (sx - q.get_width() // 2,
                      box_y + (32 - q.get_height()) // 2))
    else:
        # Open  - lid pops up, swirling glow inside
        pygame.draw.rect(surf, (40, 24, 60),
                         pygame.Rect(sx - 18, box_y + 6, 36, 26))
        pygame.draw.rect(surf, (180, 130, 220),
                         pygame.Rect(sx - 18, box_y + 6, 36, 26), 2)
        # Lid floating
        pygame.draw.rect(surf, (180, 130, 220),
                         pygame.Rect(sx - 18, box_y - 10, 36, 4))
        # Inner swirl
        for k in range(5):
            ang = t * 4 + k * math.tau / 5
            sx_in = sx + int(math.cos(ang) * 8)
            sy_in = box_y + 18 + int(math.sin(ang) * 6)
            pygame.draw.circle(surf, (220, 200, 255), (sx_in, sy_in), 2)
    # Spectators — back wall silhouettes, motionless
    for off in (-90, -50, 50, 90):
        sxs = sx + off
        pygame.draw.rect(surf, (20, 12, 30),
                         pygame.Rect(sxs - 6, CEIL_Y + 30, 12, 26))
        pygame.draw.circle(surf, (20, 12, 30),
                           (sxs, CEIL_Y + 26), 4)
    # Glitch frame: every ~1.4s, flash an inverse-colour overlay strip
    if (t * 0.7) % 1.4 < 0.04:
        ov = pygame.Surface((CORRIDOR_W // 4, FLOOR_Y - CEIL_Y - 4),
                            pygame.SRCALPHA)
        ov.fill((255, 255, 255, 60))
        surf.blit(ov, (sx - CORRIDOR_W // 8, CEIL_Y + 2))


# ---------------------------------------------------------------------------
# Chapter-specific elements
# ---------------------------------------------------------------------------

class SporeZone(Element):
    """Chapter 2: brief control inversion when courier passes through."""
    def __init__(self, x: float, w: float, path_tag: str | None = None):
        super().__init__(x, path_tag)
        self.w = w

    def overlaps(self, px: float) -> bool:
        return self.x - self.w / 2 < px < self.x + self.w / 2

    def draw(self, surf, camera_x, t, palette):
        sx  = int(self.x - camera_x)
        alpha = int(50 + 30 * math.sin(t * 2.5))
        w     = int(self.w)
        z = pygame.Surface((w, FLOOR_Y - CEIL_Y), pygame.SRCALPHA)
        z.fill((140, 255, 80, alpha))
        surf.blit(z, (sx - w // 2, CEIL_Y))
        # Spore particles
        rng = random.Random(int(self.x))
        for _ in range(12):
            px2 = rng.randint(0, w - 1)
            py2 = rng.randint(0, FLOOR_Y - CEIL_Y - 1)
            bri = rng.randint(80, 200)
            offset_t = math.sin(t * rng.uniform(0.5, 2.0) + rng.random() * 6) * 4
            pygame.draw.circle(surf, (bri, 255, int(bri * 0.6)),
                               (sx - w // 2 + px2, CEIL_Y + py2 + int(offset_t)), 2)


class QuantumDoor(Element):
    """Chapter 4: door that may or may not be real."""
    W, H = 32, FLOOR_Y - CEIL_Y

    def __init__(self, x: float, outcome: str = "nothing",
                 path_tag: str | None = None):
        """outcome: 'nothing' | 'secret' | 'shortcut' | 'bellhop'"""
        super().__init__(x, path_tag)
        self.outcome   = outcome
        self._state    = "idle"   # idle | open | passed
        self._flicker  = 0.0

    @property
    def is_real(self) -> bool:
        return self.outcome != "nothing"

    def interact(self):
        if self._state == "idle":
            if self.is_real:
                self._state = "open"
            else:
                self._flicker = 0.4
                self._state   = "passed"

    def update(self, dt, player_x, player_y):
        self._flicker = max(0.0, self._flicker - dt)

    def overlaps(self, px: float) -> bool:
        return abs(px - self.x) < self.W // 2 + PLAYER_W // 2

    def draw(self, surf, camera_x, t, palette):
        sx  = int(self.x - camera_x)
        if self._state == "passed" and self._flicker <= 0:
            return
        pul  = 0.6 + 0.4 * math.sin(t * 3.0 + self.x * 0.01)
        flk  = random.random() < 0.3 if self._flicker > 0 else False
        col  = (int(255 * pul), int(215 * pul), int(100 * pul)) if self.is_real \
               else (int(80 * pul), int(80 * pul), int(100 * pul))
        if not flk:
            pygame.draw.rect(surf, (10, 10, 20),
                             (sx - self.W // 2, CEIL_Y, self.W, self.H))
            pygame.draw.rect(surf, col,
                             (sx - self.W // 2, CEIL_Y, self.W, self.H), 2)
            # Door knob
            pygame.draw.circle(surf, col, (sx + self.W // 2 - 6, (CEIL_Y + FLOOR_Y) // 2), 4)
            f = get_font(9)
            txt = "UP" if self._state == "idle" else "OPEN" if self._state == "open" else ""
            if txt:
                s = f.render(txt, True, col)
                surf.blit(s, (sx - s.get_width() // 2, CEIL_Y + 4))


# ---------------------------------------------------------------------------
# Epic 14.1 — Corridor hazards
# ---------------------------------------------------------------------------

class SteamVent(Element):
    """
    Wall- or floor-mounted steam vent.
      - 0.6s telegraph (hiss) → 1.8s eruption (15 hp damage) → 4s cooldown.
      - Pressure gauge above the vent displays the cycle countdown.
      - Shootable: if shot during cooldown or telegraph, disables for 12s.
    """
    PHASE_COOLDOWN  = "cool"
    PHASE_TELEGRAPH = "tele"
    PHASE_ERUPT     = "erupt"
    PHASE_DISABLED  = "off"

    TELEGRAPH_S = 0.6
    ERUPT_S     = 1.8
    COOLDOWN_S  = 4.0
    DISABLE_S   = 12.0
    PLUME_H     = 64           # vertical reach of steam
    DAMAGE      = 15

    def __init__(self, x: float, y: float = FLOOR_Y,
                 phase_offset: float = 0.0, mount: str = "floor",
                 path_tag: str | None = None):
        super().__init__(x, path_tag)
        self.y      = y
        self.mount  = mount   # "floor" or "wall_left" or "wall_right"
        self._t     = phase_offset
        self._phase = self.PHASE_COOLDOWN

    def disable(self) -> None:
        self._phase = self.PHASE_DISABLED
        self._t     = 0.0

    def update(self, dt: float, player_x: float, player_y: float) -> None:
        self._t += dt
        if self._phase == self.PHASE_COOLDOWN and self._t >= self.COOLDOWN_S:
            self._phase = self.PHASE_TELEGRAPH
            self._t = 0.0
        elif self._phase == self.PHASE_TELEGRAPH and self._t >= self.TELEGRAPH_S:
            self._phase = self.PHASE_ERUPT
            self._t = 0.0
        elif self._phase == self.PHASE_ERUPT and self._t >= self.ERUPT_S:
            self._phase = self.PHASE_COOLDOWN
            self._t = 0.0
        elif self._phase == self.PHASE_DISABLED and self._t >= self.DISABLE_S:
            self._phase = self.PHASE_COOLDOWN
            self._t = 0.0

    def collides(self, px: float, py: float) -> bool:
        if self._phase != self.PHASE_ERUPT:
            return False
        if abs(px - self.x) > 16:
            return False
        # Floor vents shoot up; wall vents shoot horizontally
        if self.mount == "floor":
            return self.y - self.PLUME_H < py + PLAYER_H and py < self.y
        # wall vents: hazard zone is at constant y, extending ~PLUME_H horizontally
        return abs(py + PLAYER_H / 2 - self.y) < 20

    def draw(self, surf, camera_x, t, palette):
        sx = int(self.x - camera_x)
        base_col = (90, 90, 100)
        # Vent body
        if self.mount == "floor":
            pygame.draw.rect(surf, (24, 24, 32), (sx - 14, int(self.y) - 8, 28, 10))
            pygame.draw.rect(surf, base_col,    (sx - 14, int(self.y) - 8, 28, 10), 1)
            pygame.draw.rect(surf, (10, 10, 16), (sx - 10, int(self.y) - 6, 20, 4))
        # Pressure gauge above
        gauge_y = int(self.y) - 22
        pygame.draw.circle(surf, (16, 16, 22), (sx, gauge_y), 6)
        pygame.draw.circle(surf, base_col, (sx, gauge_y), 6, 1)
        # Gauge needle reflects phase progress
        if self._phase == self.PHASE_COOLDOWN:
            frac = self._t / self.COOLDOWN_S
            needle_c = (60, 180, 80)
        elif self._phase == self.PHASE_TELEGRAPH:
            frac = 0.5 + 0.5 * self._t / self.TELEGRAPH_S
            needle_c = (220, 160, 0)
        elif self._phase == self.PHASE_ERUPT:
            frac = 1.0
            needle_c = (220, 40, 40)
        else:  # disabled
            frac = 0.0
            needle_c = (60, 60, 60)
        ang = -math.pi * 0.75 + math.pi * 1.5 * frac
        nx, ny = sx + int(4 * math.cos(ang)), gauge_y + int(4 * math.sin(ang))
        pygame.draw.line(surf, needle_c, (sx, gauge_y), (nx, ny), 1)
        # Telegraph hiss: little curl puffs above vent
        if self._phase == self.PHASE_TELEGRAPH:
            puff_a = abs(math.sin(t * 9.0))
            for pi in range(3):
                yo = int(8 + pi * 4)
                pygame.draw.circle(surf, (200, 200, 220),
                                   (sx - 3 + int(2 * math.sin(t * 7.0 + pi)),
                                    int(self.y) - 8 - yo),
                                   max(1, int(2 * puff_a)), 1)
        # Eruption: white-grey steam column
        elif self._phase == self.PHASE_ERUPT:
            puff_t = self._t / self.ERUPT_S
            for layer in range(7):
                yo = int(layer * (self.PLUME_H / 7))
                wd = 14 + layer * 2
                alpha = int(220 * (1 - layer / 7))
                steam = pygame.Surface((wd * 2, 12), pygame.SRCALPHA)
                steam.fill((230, 230, 240, alpha))
                jitter = int(2 * math.sin(t * 12 + layer * 1.7))
                surf.blit(steam, (sx - wd + jitter, int(self.y) - 8 - yo - 4))
        # Disabled: dim grey, "DSBLD" tag
        elif self._phase == self.PHASE_DISABLED:
            f = get_font(7, bold=True)
            tg = f.render("OFFLINE", True, (90, 90, 90))
            surf.blit(tg, (sx - tg.get_width() // 2, int(self.y) - 36))


class Tripwire(Element):
    """
    Thin cyan laser across a corridor section. Crossing triggers an alarm:
    Bax line + visual flash for ~2s. Wire can be 'disarmed' (set armed=False).
    No direct hull damage but marks the player as alerted.
    """
    def __init__(self, x: float, y: float = FLOOR_Y - 32,
                 w: int = 48, path_tag: str | None = None,
                 bax_line: str | None = None):
        super().__init__(x, path_tag)
        self.y         = y
        self.w         = w
        self.armed     = True
        self.triggered = False
        self._flash_t  = 0.0
        self._bax_line = bax_line or (
            "Tripwire! Security alert. They KNOW you're here. Move.")

    def disarm(self) -> None:
        self.armed = False

    def collides(self, px: float, py: float) -> bool:
        if not self.armed or self.triggered:
            return False
        if abs(px - self.x) > self.w // 2:
            return False
        # Player legs cross the wire height
        return self.y - 6 < py + PLAYER_H < self.y + 6

    def trigger(self) -> None:
        self.triggered = True
        self._flash_t  = 2.0
        from core.event_bus import bus, EVT_BAX_SPEAK
        bus.emit(EVT_BAX_SPEAK, line=self._bax_line)

    def update(self, dt: float, player_x: float, player_y: float) -> None:
        self._flash_t = max(0.0, self._flash_t - dt)

    def draw(self, surf, camera_x, t, palette):
        sx = int(self.x - camera_x)
        x0 = sx - self.w // 2
        x1 = sx + self.w // 2
        if not self.armed:
            pygame.draw.line(surf, (30, 60, 60), (x0, int(self.y)), (x1, int(self.y)), 1)
            return
        if self.triggered and self._flash_t > 0:
            pulse = abs(math.sin(t * 14.0))
            col   = (255, int(180 * pulse), int(60 * pulse))
            pygame.draw.line(surf, col, (x0, int(self.y)), (x1, int(self.y)), 2)
            f = get_font(8, bold=True)
            al = f.render("ALERT", True, col)
            surf.blit(al, (sx - al.get_width() // 2, int(self.y) - 12))
        else:
            # Live cyan wire with a faint pulse
            pulse = 0.6 + 0.4 * math.sin(t * 4.0)
            col = (int(40 + 60 * pulse), int(200 + 55 * pulse), int(220))
            pygame.draw.line(surf, col, (x0, int(self.y)), (x1, int(self.y)), 1)
            # Mount points
            for px in (x0, x1):
                pygame.draw.rect(surf, (60, 60, 80), (px - 2, int(self.y) - 4, 4, 8))


class SecurityBeam(Element):
    """
    Ceiling-mounted spotlight that sweeps the floor. Player caught in the
    illuminated cone takes hull damage. Sweep angle is sinusoidal.
    Shadow zones (outside the cone) allow safe movement.
    """
    SWEEP_PERIOD = 4.2
    HALF_ANGLE   = math.radians(28)
    DAMAGE       = 10

    def __init__(self, x: float, y: float = CEIL_Y + 8,
                 length: float = 240.0, phase: float = 0.0,
                 path_tag: str | None = None):
        super().__init__(x, path_tag)
        self.y       = y
        self.length  = length
        self._phase  = phase

    def _angle(self, t: float) -> float:
        # Sweep from -1 to +1, mapped to ±60° around straight down
        s = math.sin(2 * math.pi * t / self.SWEEP_PERIOD + self._phase)
        return s * math.radians(50)

    def _cone_hits(self, px: float, py: float, t: float) -> bool:
        # Vector from beam origin to player
        dx = px - self.x
        dy = (py + PLAYER_H / 2) - self.y
        d  = math.hypot(dx, dy)
        if d < 8 or d > self.length:
            return False
        beam_a   = self._angle(t) + math.pi / 2  # downward
        actor_a  = math.atan2(dy, dx)
        diff     = ((actor_a - beam_a + math.pi) % (2 * math.pi)) - math.pi
        return abs(diff) < self.HALF_ANGLE

    def collides(self, px: float, py: float, t: float) -> bool:
        return self._cone_hits(px, py, t)

    def draw(self, surf, camera_x, t, palette):
        sx = int(self.x - camera_x)
        # Housing
        pygame.draw.rect(surf, (20, 20, 24), (sx - 10, int(self.y) - 6, 20, 8))
        pygame.draw.rect(surf, (90, 60, 60), (sx - 10, int(self.y) - 6, 20, 8), 1)
        # Cone — semi-transparent sweeping light
        beam_a = self._angle(t) + math.pi / 2
        for steps in range(5):
            r = self.length * (steps + 1) / 5
            for side in (-1, 1):
                ang = beam_a + side * self.HALF_ANGLE
                ex = sx + int(r * math.cos(ang))
                ey = int(self.y) + int(r * math.sin(ang))
                pygame.draw.line(surf, (180, 90, 60, 0), (sx, int(self.y)), (ex, ey), 0)
        # Filled cone via polygon with alpha
        ex_l = sx + int(self.length * math.cos(beam_a - self.HALF_ANGLE))
        ey_l = int(self.y) + int(self.length * math.sin(beam_a - self.HALF_ANGLE))
        ex_r = sx + int(self.length * math.cos(beam_a + self.HALF_ANGLE))
        ey_r = int(self.y) + int(self.length * math.sin(beam_a + self.HALF_ANGLE))
        cone = pygame.Surface((CORRIDOR_W, CORRIDOR_H), pygame.SRCALPHA)
        pygame.draw.polygon(cone, (220, 90, 50, 38),
                            [(sx, int(self.y)), (ex_l, ey_l), (ex_r, ey_r)])
        surf.blit(cone, (0, 0))
        # Bright centerline
        ex_c = sx + int(self.length * math.cos(beam_a))
        ey_c = int(self.y) + int(self.length * math.sin(beam_a))
        pygame.draw.line(surf, (255, 160, 80), (sx, int(self.y)), (ex_c, ey_c), 1)
        # Pulsing red "ARMED" lamp
        if abs(math.sin(t * 3.5)) > 0.5:
            pygame.draw.circle(surf, (220, 30, 30), (sx, int(self.y) - 8), 2)
