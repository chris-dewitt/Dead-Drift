"""
Reusable element classes for all delivery corridors.
All positions are in world-space; callers pass camera_x when drawing.
"""
from __future__ import annotations
import math
import random
import pygame

from renderer.sci_fi_ui import draw_mario_brick_platform

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
        f = pygame.font.SysFont("monospace", 9)
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
        f = pygame.font.SysFont("monospace", 7)
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
        f = pygame.font.SysFont("monospace", 9, bold=True)
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
        f = pygame.font.SysFont("monospace", 9, bold=True)
        s = f.render("BOSS", True, col)
        surf.blit(s, (sx + 4, CEIL_Y + 4))


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
            f = pygame.font.SysFont("monospace", 9)
            txt = "UP" if self._state == "idle" else "OPEN" if self._state == "open" else ""
            if txt:
                s = f.render(txt, True, col)
                surf.blit(s, (sx - s.get_width() // 2, CEIL_Y + 4))
