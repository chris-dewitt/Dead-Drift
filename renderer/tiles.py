"""
Delivery v2 I.4.1 — the corridor tile vocabulary.

Six chapter-flavoured platform tile styles, all procedural, all in the
16-bit register: chunky 2px black outlines, two-tone dither shading, a
fat top highlight. A platform picks its style from the room palette's
``tile_style`` key, so whole chapters re-skin without touching layout:

    brick    — ch1 Archive (warm masonry under the record shop)
    fungus   — ch2 Shrooms (organic shelf, lumpy top, spore pocks)
    cabinet  — ch3 Paperwork (filing drawers with little labels)
    chrome   — ch4 VIP (polished hotel banding + specular line)
    girder   — ch5 Edge (hand-riveted Remnants steelwork)
    glass    — ch6 Compliance (Nova Soma's frosted panels)

`draw_tile_platform` is the only entry point; unknown styles fall back
to brick so palettes can never crash a draw.
"""
from __future__ import annotations
import math
import pygame

_OUTLINE = (12, 10, 10)


def _dither(surf, x, y, w, h, col, step: int = 4):
    """Checkerboard dither — the era's gradient."""
    for dy in range(0, h, step):
        for dx in range(((dy // step) % 2) * step, w, step * 2):
            pygame.draw.rect(surf, col, (x + dx, y + dy, step, step))


def _frame(surf, x, y, w, h, hi):
    """Chunky outline + fat top highlight shared by every style."""
    pygame.draw.rect(surf, _OUTLINE, (x, y, w, h), 2)
    pygame.draw.rect(surf, hi, (x + 2, y + 2, w - 4, 3))


def _tile_brick(surf, x, y, w, h, base, hi, t):
    pygame.draw.rect(surf, base, (x, y, w, h))
    shade = tuple(int(c * 0.72) for c in base)
    _dither(surf, x, y + h // 2, w, h - h // 2, shade)
    course = 12
    for ty in range(y, y + h, course // 2):
        off = course // 2 if ((ty - y) // (course // 2)) % 2 else 0
        for tx in range(x + off, x + w, course):
            pygame.draw.rect(surf, tuple(int(c * 0.5) for c in base),
                             (tx, ty, 1, course // 2))
        pygame.draw.line(surf, tuple(int(c * 0.5) for c in base),
                         (x, ty), (x + w - 1, ty), 1)
    _frame(surf, x, y, w, h, hi)


def _tile_girder(surf, x, y, w, h, base, hi, t):
    web = tuple(int(c * 0.55) for c in base)
    pygame.draw.rect(surf, web, (x, y, w, h))
    pygame.draw.rect(surf, base, (x, y, w, 4))
    pygame.draw.rect(surf, base, (x, y + h - 4, w, 4))
    # X cross-braces
    brace = tuple(min(255, int(c * 1.15)) for c in base)
    seg = 34
    for bx in range(x, x + w - seg, seg):
        pygame.draw.line(surf, brace, (bx, y + 3), (bx + seg, y + h - 3), 2)
        pygame.draw.line(surf, brace, (bx, y + h - 3), (bx + seg, y + 3), 2)
    # rivets
    for rx in range(x + 5, x + w - 3, 12):
        pygame.draw.rect(surf, hi, (rx, y + 1, 2, 2))
        pygame.draw.rect(surf, hi, (rx, y + h - 3, 2, 2))
    _frame(surf, x, y, w, h, hi)


def _tile_glass(surf, x, y, w, h, base, hi, t):
    pale = tuple(min(255, int(c * 0.9 + 60)) for c in base)
    pygame.draw.rect(surf, base, (x, y, w, h))
    _dither(surf, x, y, w, h // 2, pale, step=3)
    # diagonal shine streaks
    for sx0 in range(x + 8, x + w - 4, 26):
        pygame.draw.line(surf, pale, (sx0, y + h - 2), (sx0 + 8, y + 2), 2)
    # steel end caps
    cap = tuple(int(c * 0.5) for c in base)
    pygame.draw.rect(surf, cap, (x, y, 5, h))
    pygame.draw.rect(surf, cap, (x + w - 5, y, 5, h))
    _frame(surf, x, y, w, h, hi)


def _tile_fungus(surf, x, y, w, h, base, hi, t):
    pygame.draw.rect(surf, base, (x, y + 3, w, h - 3))
    shade = tuple(int(c * 0.68) for c in base)
    _dither(surf, x, y + h // 2, w, h - h // 2, shade)
    # lumpy organic top
    for lx in range(x + 6, x + w - 4, 14):
        r = 5 + (lx * 7 + int(t)) % 3
        pygame.draw.circle(surf, base, (lx, y + 3), r)
        pygame.draw.circle(surf, _OUTLINE, (lx, y + 3), r, 1)
    # spore pocks
    pock = tuple(min(255, int(c * 1.3)) for c in base)
    for px_ in range(x + 9, x + w - 4, 22):
        pygame.draw.circle(surf, pock, (px_, y + h - 5), 2)
    pygame.draw.rect(surf, _OUTLINE, (x, y + 3, w, h - 3), 2)
    pygame.draw.rect(surf, hi, (x + 2, y + 4, w - 4, 2))


def _tile_cabinet(surf, x, y, w, h, base, hi, t):
    pygame.draw.rect(surf, base, (x, y, w, h))
    shade = tuple(int(c * 0.7) for c in base)
    drawer_w = 26
    for dx in range(x, x + w - 4, drawer_w):
        dw = min(drawer_w - 3, x + w - dx - 3)
        pygame.draw.rect(surf, shade, (dx + 2, y + 3, dw, h - 6), 1)
        # handle slot + label
        pygame.draw.rect(surf, _OUTLINE, (dx + dw // 2 - 4, y + h // 2, 8, 2))
        pygame.draw.rect(surf, hi, (dx + 4, y + 4, 8, 3))
    _frame(surf, x, y, w, h, hi)


def _tile_chrome(surf, x, y, w, h, base, hi, t):
    light = tuple(min(255, int(c * 1.25)) for c in base)
    dark  = tuple(int(c * 0.55) for c in base)
    pygame.draw.rect(surf, light, (x, y, w, h // 2))
    pygame.draw.rect(surf, dark,  (x, y + h // 2, w, h - h // 2))
    _dither(surf, x, y + h // 2 - 2, w, 4, base, step=2)
    # specular line that drifts slowly — polished, alive
    spec_x = x + int((math.sin(t * 0.7) * 0.5 + 0.5) * max(1, w - 20))
    pygame.draw.line(surf, (255, 255, 255),
                     (spec_x, y + 2), (spec_x + 10, y + 2), 2)
    _frame(surf, x, y, w, h, hi)


_STYLES = {
    "brick":   _tile_brick,
    "girder":  _tile_girder,
    "glass":   _tile_glass,
    "fungus":  _tile_fungus,
    "cabinet": _tile_cabinet,
    "chrome":  _tile_chrome,
}

TILE_STYLES = tuple(_STYLES)


def draw_tile_platform(surf: pygame.Surface, sx: int, y: int, w: int, h: int,
                       palette: dict, t: float = 0.0,
                       base: tuple | None = None,
                       hi: tuple | None = None) -> None:
    """Draw a platform in the room's chapter tile style.

    ``sx`` is the platform's centre x in screen space (matching the old
    `draw_mario_brick_platform` contract). ``base``/``hi`` override the
    palette's platform colours when a caller needs an accent (moving
    platforms, lifts)."""
    style = _STYLES.get(palette.get("tile_style", "brick"), _tile_brick)
    if base is None:
        base = palette.get("brick", palette.get("platform", (140, 70, 20)))
    if hi is None:
        hi = palette.get("brick_hi", palette.get("platform_hi", (220, 140, 40)))
    x = int(sx - w // 2)
    style(surf, x, int(y), int(w), int(h), base, hi, t)
