"""Landscape letterbox: render at 1600×900, scale to the device.

Phone (19.5:9) and tablet (16:10 / 4:3) both letterbox. Touch coords
map back into logical space so overlays stay aligned with the HUD.
"""
from __future__ import annotations

import pygame
from config import settings as S

from mobile.mode import is_mobile


class LetterboxDisplay:
    def __init__(self, window: pygame.Surface):
        self.window = window
        self.surface = window
        self.dest = pygame.Rect(0, 0, *window.get_size())
        self.scale = 1.0

    def relayout(self) -> None:
        ww, wh = self.window.get_size()
        if ww <= 0 or wh <= 0:
            return
        lw, lh = S.SCREEN_W, S.SCREEN_H
        scale = min(ww / lw, wh / lh)
        dw, dh = int(lw * scale), int(lh * scale)
        self.scale = scale
        self.dest = pygame.Rect((ww - dw) // 2, (wh - dh) // 2, dw, dh)

    def present(self) -> None:
        if self.surface is self.window:
            pygame.display.flip()
            return
        self.window.fill((0, 0, 0))
        scaled = pygame.transform.scale(self.surface, (self.dest.w, self.dest.h))
        self.window.blit(scaled, self.dest.topleft)
        pygame.display.flip()

    def to_logical(self, sx: float, sy: float) -> tuple[float, float]:
        if self.dest.w <= 0 or self.dest.h <= 0:
            return sx, sy
        lx = (sx - self.dest.x) * S.SCREEN_W / self.dest.w
        ly = (sy - self.dest.y) * S.SCREEN_H / self.dest.h
        return lx, ly

    def norm_to_logical(self, nx: float, ny: float) -> tuple[float, float]:
        ww, wh = self.window.get_size()
        return self.to_logical(nx * ww, ny * wh)

    def in_letterbox(self, sx: float, sy: float) -> bool:
        return self.dest.collidepoint(int(sx), int(sy))


def _native_size() -> tuple[int, int]:
    info = pygame.display.Info()
    w, h = int(info.current_w or 0), int(info.current_h or 0)
    if w <= 0 or h <= 0:
        return S.SCREEN_W, S.SCREEN_H
    # Manifest locks landscape; if a device reports portrait, swap.
    if h > w:
        w, h = h, w
    return w, h


def attach_display(window: pygame.Surface) -> LetterboxDisplay:
    """Keep the desktop window as-is. On mobile, go fullscreen and letterbox."""
    disp = LetterboxDisplay(window)
    if not is_mobile():
        return disp
    w, h = _native_size()
    flags = pygame.FULLSCREEN
    try:
        disp.window = pygame.display.set_mode((w, h), flags)
    except pygame.error:
        disp.window = window
    if disp.window.get_size() == (S.SCREEN_W, S.SCREEN_H):
        disp.surface = disp.window
        disp.relayout()
        return disp
    disp.surface = pygame.Surface((S.SCREEN_W, S.SCREEN_H))
    disp.relayout()
    return disp
