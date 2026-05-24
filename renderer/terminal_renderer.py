from __future__ import annotations

import math
import pygame

from terminal.terminal import Terminal


class TerminalRenderer:
    """
    Wraps Terminal.draw() with light CRT polish only.
    Avoid BLEND_MULT / stacked vignettes — they crush mid-tones to black.
    """

    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self._scanlines: pygame.Surface | None = None

    def draw(self, terminal: Terminal | None):
        if terminal is None:
            return
        terminal.draw(self.surface)
        self._draw_light_scanlines()
        self._draw_edge_vignette()
        self._draw_rgb_fringe()

    def _draw_light_scanlines(self):
        w, h = self.surface.get_size()
        if self._scanlines is None or self._scanlines.get_size() != (w, h):
            self._scanlines = pygame.Surface((w, h), pygame.SRCALPHA)
            for y in range(0, h, 3):
                pygame.draw.line(self._scanlines, (0, 0, 0, 14), (0, y), (w, y))
        self.surface.blit(self._scanlines, (0, 0))

    def _draw_edge_vignette(self):
        """Darken only the outer rim — never stack opaque rects over the center."""
        w, h = self.surface.get_size()
        rim = pygame.Surface((w, h), pygame.SRCALPHA)
        band = max(48, min(w, h) // 8)
        for i in range(band):
            a = int(55 * (i / band) ** 1.4)
            pygame.draw.rect(rim, (0, 0, 0, a), (i, i, w - 2 * i, h - 2 * i), 1)
        self.surface.blit(rim, (0, 0))

    def _draw_rgb_fringe(self):
        t = pygame.time.get_ticks() / 1000.0
        w, h = self.surface.get_size()
        shift = 2 + int(math.sin(t * 1.2))
        fringe = pygame.Surface((w, h), pygame.SRCALPHA)
        fringe.fill((255, 40, 40, 8), (0, 0, shift, h))
        fringe.fill((40, 200, 255, 8), (w - shift, 0, shift, h))
        self.surface.blit(fringe, (0, 0))
