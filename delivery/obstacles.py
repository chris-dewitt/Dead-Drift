"""
Delivery run obstacles — all rendered as pygame.draw primitives.
Each obstacle operates in world-space X; caller passes camera_x to draw.
"""
from __future__ import annotations
import math
import random
import pygame

CORRIDOR_H  = 360   # total corridor pixel height
FLOOR_Y     = 320   # y of the floor surface (within corridor)
CEIL_Y      = 40    # y of ceiling
PLAYER_H    = 32    # player character height (for collision checks)


class Guard:
    """Patrols left-right on the floor; player must jump over."""
    W, H = 28, 42

    def __init__(self, x: float):
        self.x      = x
        self.y      = FLOOR_Y - self.H
        self._dir   = 1
        self._speed = random.uniform(38.0, 58.0)
        self._range = random.uniform(60.0, 100.0)
        self._ox    = x   # origin of patrol
        self._alert = 0.0  # flash timer when near player
        self.alive  = True

    def update(self, dt: float, player_x: float, player_world_x: float):
        self.x += self._dir * self._speed * dt
        if abs(self.x - self._ox) > self._range:
            self._dir *= -1
        dist = abs(player_world_x - self.x)
        if dist < 160:
            self._alert = 0.3
        self._alert = max(0.0, self._alert - dt)

    def collides(self, px: float, py: float) -> bool:
        return (abs(px - self.x) < (self.W // 2 + 12) and
                py + PLAYER_H > self.y and py < self.y + self.H)

    def draw(self, surface: pygame.Surface, camera_x: float, t: float):
        sx = int(self.x - camera_x)
        sy = int(self.y)
        body_col = (200, 45, 45) if self._alert > 0 else (165, 38, 38)
        # Body
        pygame.draw.rect(surface, body_col, (sx - self.W // 2, sy, self.W, self.H))
        pygame.draw.rect(surface, (220, 80, 80), (sx - self.W // 2, sy, self.W, self.H), 1)
        # Visor
        pygame.draw.rect(surface, (255, 200, 0) if self._alert > 0 else (90, 90, 90),
                         (sx - 8, sy + 6, 16, 8))
        # Antenna
        pygame.draw.line(surface, (200, 80, 80),
                         (sx, sy), (sx, sy - 12), 2)
        pygame.draw.circle(surface, (255, 60, 60) if self._alert > 0 else (120, 50, 50),
                           (sx, sy - 14), 4)
        # Alert exclamation
        if self._alert > 0:
            f = pygame.font.SysFont("monospace", 14, bold=True)
            s = f.render("!", True, (255, 230, 0))
            surface.blit(s, (sx - s.get_width() // 2, sy - 30))


class Gate:
    """Timed checkpoint — bars from ceiling and floor with a sliding gap."""
    BAR_W = 18

    def __init__(self, x: float):
        self.x       = x
        self._period = random.uniform(1.8, 3.2)   # open/close cycle
        self._phase  = random.uniform(0.0, math.pi)
        self._gap_h  = 80    # opening height in px
        self.alive   = True

    def _gap_top(self, t: float) -> float:
        mid   = (FLOOR_Y + CEIL_Y) / 2
        swing = ((FLOOR_Y - CEIL_Y) / 2 - self._gap_h / 2) * 0.7
        return mid - self._gap_h / 2 + swing * math.sin(
            2 * math.pi * t / self._period + self._phase)

    def update(self, dt: float, *_):
        pass

    def collides(self, px: float, py: float, t: float) -> bool:
        if abs(px - self.x) > self.BAR_W + 10:
            return False
        gap_top = self._gap_top(t)
        gap_bot = gap_top + self._gap_h
        in_upper = py < gap_top
        in_lower = py + PLAYER_H > gap_bot
        return in_upper or in_lower

    def draw(self, surface: pygame.Surface, camera_x: float, t: float):
        sx      = int(self.x - camera_x)
        gap_top = self._gap_top(t)
        gap_bot = gap_top + self._gap_h
        # Upper bar
        pygame.draw.rect(surface, (200, 140, 0),
                         (sx - self.BAR_W // 2, CEIL_Y, self.BAR_W,
                          int(gap_top - CEIL_Y)))
        pygame.draw.rect(surface, (255, 180, 0),
                         (sx - self.BAR_W // 2, CEIL_Y, self.BAR_W,
                          int(gap_top - CEIL_Y)), 1)
        # Lower bar
        lower_top = int(gap_bot)
        pygame.draw.rect(surface, (200, 140, 0),
                         (sx - self.BAR_W // 2, lower_top, self.BAR_W,
                          FLOOR_Y - lower_top))
        pygame.draw.rect(surface, (255, 180, 0),
                         (sx - self.BAR_W // 2, lower_top, self.BAR_W,
                          FLOOR_Y - lower_top), 1)
        # Gap indicator arrows
        mid_gap = int((gap_top + gap_bot) / 2)
        arrow_col = (255, 230, 100)
        pygame.draw.polygon(surface, arrow_col,
                            [(sx - 6, mid_gap - 4), (sx + 6, mid_gap - 4),
                             (sx, mid_gap - 12)])
        pygame.draw.polygon(surface, arrow_col,
                            [(sx - 6, mid_gap + 4), (sx + 6, mid_gap + 4),
                             (sx, mid_gap + 12)])


class MovingPlatform:
    """Floating platform over a floor gap — moves vertically."""
    W, H = 90, 12

    def __init__(self, x: float, gap_width: float = 160.0):
        self.x         = x
        self.gap_width = gap_width
        self._cy       = FLOOR_Y - 90   # centre y of oscillation
        self._amp      = 55.0
        self._period   = random.uniform(2.0, 3.5)
        self._phase    = random.uniform(0.0, math.pi * 2)
        self.alive     = True

    @property
    def top_y(self) -> float:
        return self._cy + self._amp * math.sin(
            2 * math.pi * pygame.time.get_ticks() / 1000.0 / self._period + self._phase)

    def update(self, dt: float, *_):
        pass

    def collides_top(self, px: float, py: float, pvy: float) -> bool:
        """Returns True if player is landing on top of platform."""
        if abs(px - self.x) > self.W // 2 + 10:
            return False
        ty = self.top_y
        return pvy >= 0 and py + PLAYER_H >= ty and py + PLAYER_H <= ty + 20

    def draw(self, surface: pygame.Surface, camera_x: float, t: float):
        sx  = int(self.x - camera_x)
        ty  = int(self.top_y)
        col = (0, 160, 90)
        pygame.draw.rect(surface, col,
                         (sx - self.W // 2, ty, self.W, self.H))
        pygame.draw.rect(surface, (0, 220, 120),
                         (sx - self.W // 2, ty, self.W, self.H), 1)
        # Hazard stripes on the gap floor beneath
        gap_x = sx - self.W // 2
        pygame.draw.rect(surface, (40, 8, 8),
                         (gap_x, FLOOR_Y - 4, int(self.gap_width), 4))
        for i in range(0, int(self.gap_width), 20):
            pygame.draw.line(surface, (100, 30, 30),
                             (gap_x + i, FLOOR_Y - 4),
                             (gap_x + i + 10, FLOOR_Y), 1)


class ScannerBeam:
    """Horizontal sweep beam rising and falling across the corridor."""

    def __init__(self, x: float, width: float = 120.0):
        self.x      = x
        self.width  = width
        self._speed = random.uniform(55.0, 95.0) * random.choice([-1, 1])
        self._y     = random.uniform(CEIL_Y + 30, FLOOR_Y - 60)
        self.alive  = True

    def update(self, dt: float, *_):
        self._y += self._speed * dt
        if self._y < CEIL_Y + 20 or self._y > FLOOR_Y - 20:
            self._speed *= -1
            self._y = max(CEIL_Y + 20, min(FLOOR_Y - 20, self._y))

    def collides(self, px: float, py: float) -> bool:
        if not (self.x - self.width / 2 < px < self.x + self.width / 2):
            return False
        return self._y - 8 < py + PLAYER_H / 2 < self._y + 8

    def draw(self, surface: pygame.Surface, camera_x: float, t: float):
        sx  = int(self.x - camera_x)
        sy  = int(self._y)
        x0  = sx - int(self.width / 2)
        x1  = sx + int(self.width / 2)
        pulse = int(180 + 75 * math.sin(t * 8.0))
        col   = (0, pulse, int(pulse * 0.3))
        pygame.draw.line(surface, col, (x0, sy), (x1, sy), 3)
        # Glow fade
        for off in (1, 2, 3):
            a_col = (0, max(0, pulse - off * 50), 0)
            pygame.draw.line(surface, a_col, (x0, sy - off), (x1, sy - off), 1)
            pygame.draw.line(surface, a_col, (x0, sy + off), (x1, sy + off), 1)
        # Scan tick markers on wall
        pygame.draw.rect(surface, col, (x0, sy - 5, 6, 10))
        pygame.draw.rect(surface, col, (x1 - 6, sy - 5, 6, 10))
