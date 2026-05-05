from __future__ import annotations
import pygame
from terminal.terminal import Terminal


class TerminalRenderer:
    """
    Wraps Terminal.draw() and adds CRT post-processing effects:
    scanlines, screen curvature vignette.
    """

    def __init__(self, surface: pygame.Surface):
        self.surface  = surface
        self._overlay: pygame.Surface | None = None

    def draw(self, terminal: Terminal | None):
        if terminal is None:
            return
        terminal.draw(self.surface)
        self._draw_scanlines()

    def _draw_scanlines(self):
        w, h = self.surface.get_size()
        if self._overlay is None or self._overlay.get_size() != (w, h):
            self._overlay = self._build_scanline_overlay(w, h)
        self.surface.blit(self._overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    @staticmethod
    def _build_scanline_overlay(w: int, h: int) -> pygame.Surface:
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((255, 255, 255, 255))
        for y in range(0, h, 3):
            pygame.draw.line(surf, (0, 0, 0, 60), (0, y), (w, y))
        return surf
