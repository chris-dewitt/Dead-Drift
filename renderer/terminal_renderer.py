from __future__ import annotations

import math
import pygame

from terminal.terminal import Terminal


class TerminalRenderer:
    """
    Wraps Terminal.draw() and adds CRT post-processing:
    scanlines, vignette, subtle RGB fringe.
    """

    def __init__(self, surface: pygame.Surface):
        self.surface  = surface
        self._overlay: pygame.Surface | None = None
        self._vignette: pygame.Surface | None = None

    def draw(self, terminal: Terminal | None):
        if terminal is None:
            return
        terminal.draw(self.surface)
        self._draw_scanlines()
        self._draw_vignette()
        self._draw_rgb_fringe()

    def _draw_scanlines(self):
        w, h = self.surface.get_size()
        if self._overlay is None or self._overlay.get_size() != (w, h):
            self._overlay = self._build_scanline_overlay(w, h)
        self.surface.blit(self._overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    def _draw_vignette(self):
        w, h = self.surface.get_size()
        if self._vignette is None or self._vignette.get_size() != (w, h):
            self._vignette = pygame.Surface((w, h), pygame.SRCALPHA)
            for i in range(12):
                frac = i / 12
                a = int(200 * (frac ** 1.6))
                m = int(w * 0.06 * frac)
                my = int(h * 0.08 * frac)
                pygame.draw.rect(self._vignette, (0, 0, 0, a),
                                 (m, my, w - m * 2, h - my * 2))
        self.surface.blit(self._vignette, (0, 0))

    def _draw_rgb_fringe(self):
        t = pygame.time.get_ticks() / 1000.0
        w, h = self.surface.get_size()
        shift = 2 + int(math.sin(t * 1.2))
        fringe = pygame.Surface((w, h), pygame.SRCALPHA)
        fringe.fill((255, 40, 40, 12), (0, 0, shift, h))
        fringe.fill((40, 200, 255, 12), (w - shift, 0, shift, h))
        self.surface.blit(fringe, (0, 0))

    @staticmethod
    def _build_scanline_overlay(w: int, h: int) -> pygame.Surface:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((255, 255, 255, 255))
        for y in range(0, h, 2):
            pygame.draw.line(surf, (0, 0, 0, 72), (0, y), (w, y))
        for y in range(1, h, 4):
            pygame.draw.line(surf, (0, 40, 20, 18), (0, y), (w, y))
        return surf
