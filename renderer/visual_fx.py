"""Post-process and shared retro-sci-fi polish (pygame, no shaders)."""

from __future__ import annotations

import math
import random
import pygame

from config import settings as S


def _hsv(h: float, s: float = 1.0, v: float = 1.0) -> tuple[int, int, int]:
    h = h % 1.0
    if s == 0:
        c = int(v * 255)
        return (c, c, c)
    i = int(h * 6)
    f = h * 6 - i
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r, g, b = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i % 6]
    return (int(r * 255), int(g * 255), int(b * 255))


class VisualFX:
    """Screen-space grade: vignette, bloom pass, scanlines, film grain."""

    def __init__(self) -> None:
        self._grain_seed = random.randint(0, 99999)
        self._menu_glow_t = 0.0

    def apply_flight_grade(self, surface: pygame.Surface, dt: float,
                           *, hull_pct: float = 1.0, sector_intensity: float = 0.0) -> None:
        w, h = surface.get_size()
        t = pygame.time.get_ticks() / 1000.0
        stress = 1.0 - hull_pct
        intensity = 0.55 + sector_intensity * 0.35

        self._draw_vignette(surface, strength=0.42 + stress * 0.22)
        self._draw_scanlines(surface, alpha=int(14 + stress * 18), spacing=3)
        self._draw_chromatic_edge(surface, offset=int(2 + stress * 3))
        self._draw_grain(surface, alpha=int(10 + stress * 12))
        self._draw_ambient_bloom_tint(surface, t, intensity)

    def apply_menu_grade(self, surface: pygame.Surface, dt: float) -> None:
        self._menu_glow_t += dt
        t = self._menu_glow_t
        w, h = surface.get_size()

        # Radial amber wash behind title zone
        glow = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, int(h * 0.22)
        for r in range(420, 80, -28):
            a = max(0, int(8 * (1.0 - r / 420) * (0.7 + 0.3 * math.sin(t * 0.6))))
            col = _hsv(0.09 + 0.02 * math.sin(t * 0.4), 0.7, 0.35)
            pygame.draw.circle(glow, (*col, a), (cx, cy), r)
        surface.blit(glow, (0, 0))

        self._draw_vignette(surface, strength=0.58)
        self._draw_scanlines(surface, alpha=18, spacing=4)
        self._draw_grain(surface, alpha=14)
        self._draw_chromatic_edge(surface, offset=3)

    def draw_soft_glow_line(self, surface: pygame.Surface, p1, p2,
                            color: tuple[int, int, int], width: int = 2) -> None:
        """Multi-pass neon line."""
        for w, alpha in ((width + 6, 28), (width + 3, 55), (width, 255)):
            ls = pygame.Surface((S.SCREEN_W, S.FLIGHT_H), pygame.SRCALPHA)
            pygame.draw.line(ls, (*color, alpha), p1, p2, w)
            surface.blit(ls, (0, 0))

    def draw_pulsing_ring(self, surface: pygame.Surface, center: tuple[int, int],
                          radius: int, hue: float, t: float, *, rings: int = 4) -> None:
        pulse = 0.5 + 0.5 * math.sin(t * 2.2)
        for i in range(rings):
            r = int(radius + i * 14 + pulse * 6)
            a = max(0, int(90 - i * 22 - (1 - pulse) * 30))
            col = _hsv(hue + i * 0.04, 0.75, 0.85)
            pygame.draw.circle(surface, (*col, a), center, r, 2)

    # ------------------------------------------------------------------
    def _draw_vignette(self, surface: pygame.Surface, *, strength: float) -> None:
        w, h = surface.get_size()
        v = pygame.Surface((w, h), pygame.SRCALPHA)
        steps = 14
        for i in range(steps):
            frac = i / steps
            a = int(255 * strength * (frac ** 1.8))
            margin_x = int(w * 0.08 * frac)
            margin_y = int(h * 0.10 * frac)
            pygame.draw.rect(v, (0, 0, 0, a),
                             (margin_x, margin_y, w - margin_x * 2, h - margin_y * 2), 0)
        surface.blit(v, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

    def _draw_scanlines(self, surface: pygame.Surface, *, alpha: int, spacing: int) -> None:
        w, h = surface.get_size()
        sl = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, spacing):
            pygame.draw.line(sl, (0, 0, 0, alpha), (0, y), (w, y))
        surface.blit(sl, (0, 0))

    def _draw_grain(self, surface: pygame.Surface, *, alpha: int) -> None:
        w, h = surface.get_size()
        rng = random.Random(self._grain_seed + pygame.time.get_ticks() // 80)
        grain = pygame.Surface((w, h), pygame.SRCALPHA)
        n = (w * h) // 900
        for _ in range(n):
            x, y = rng.randint(0, w - 1), rng.randint(0, h - 1)
            b = rng.randint(0, 255)
            grain.set_at((x, y), (b, b, b, alpha))
        surface.blit(grain, (0, 0))

    def _draw_chromatic_edge(self, surface: pygame.Surface, *, offset: int) -> None:
        if offset <= 0:
            return
        w, h = surface.get_size()
        strip = max(2, offset)
        edge = pygame.Surface((w, h), pygame.SRCALPHA)
        for x in range(strip):
            a = int(35 * (1 - x / strip))
            pygame.draw.line(edge, (255, 40, 40, a), (x, 0), (x, h))
            pygame.draw.line(edge, (40, 200, 255, a), (w - 1 - x, 0), (w - 1 - x, h))
        surface.blit(edge, (0, 0))

    def _draw_ambient_bloom_tint(self, surface: pygame.Surface, t: float, intensity: float) -> None:
        w, h = surface.get_size()
        tint = pygame.Surface((w, h), pygame.SRCALPHA)
        hue = (0.58 + t * 0.02) % 1.0
        col = _hsv(hue, 0.35, 0.12)
        tint.fill((*col, int(18 * intensity)))
        surface.blit(tint, (0, 0))
