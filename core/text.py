"""
Text rendering helpers.

Centralised font loading + readable text rendering for the whole game.
All text should ideally go through these helpers so it's consistent
across platforms and easy to globally retune readability.

Usage:
    from core.text import get_font, render_text, draw_text

    f = get_font(14)                    # cached, returns pygame.font.Font
    surf = render_text("HULL 100", 14, (255, 176, 0))
    draw_text(screen, "HULL 100", (12, 8), 14, (255, 176, 0))
"""
from __future__ import annotations
import os
import pygame

# ── Font discovery ───────────────────────────────────────────────────────
_FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                          "assets", "fonts")
_BUNDLED_REGULAR = os.path.join(_FONTS_DIR, "DejaVuSansMono.ttf")
_BUNDLED_BOLD    = os.path.join(_FONTS_DIR, "DejaVuSansMono-Bold.ttf")

# SysFont fallback chain — first match wins on each OS
_SYSFONT_FALLBACK = "consolas,jetbrainsmono,dejavusansmono,menlo,monospace"

# Global readability bump — adds this many points to every requested size
_SIZE_BUMP = 2

# Font instance cache. Keyed by (size, bold, italic).
_FONT_CACHE: dict[tuple[int, bool, bool], pygame.font.Font] = {}


def get_font(size: int, bold: bool = False,
             italic: bool = False) -> pygame.font.Font:
    """Return a cached pygame Font at the requested size (with size bump).

    `italic` is honoured by setting `pygame.font.Font.set_italic(True)` on
    the cached instance — pygame's bundled-font path doesn't expose an
    italic constructor, but the bitmap-skew approximation is faithful
    enough for the in-game CRT look.
    """
    effective_size = max(8, size + _SIZE_BUMP)
    key = (effective_size, bold, italic)
    cached = _FONT_CACHE.get(key)
    if cached is not None:
        return cached

    path = _BUNDLED_BOLD if bold else _BUNDLED_REGULAR
    if os.path.exists(path):
        font = pygame.font.Font(path, effective_size)
    else:
        font = pygame.font.SysFont(_SYSFONT_FALLBACK, effective_size,
                                   bold=bold, italic=italic)
    if italic:
        try:
            font.set_italic(True)
        except Exception:
            pass
    _FONT_CACHE[key] = font
    return font


def render_text(text: str, size: int, color: tuple,
                bold: bool = False, shadow: bool = True,
                shadow_color: tuple = (0, 0, 0)) -> pygame.Surface:
    """Render text with an optional 1px drop shadow for readability."""
    font = get_font(size, bold=bold)
    fg = font.render(text, True, color)
    if not shadow:
        return fg
    sh = font.render(text, True, shadow_color)
    w, h = fg.get_width() + 1, fg.get_height() + 1
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    out.blit(sh, (1, 1))
    out.blit(fg, (0, 0))
    return out


def draw_text(surface: pygame.Surface, text: str, pos: tuple,
              size: int, color: tuple, bold: bool = False,
              shadow: bool = True, shadow_color: tuple = (0, 0, 0)) -> pygame.Rect:
    """Blit shadowed text and return its rect."""
    surf = render_text(text, size, color, bold=bold,
                       shadow=shadow, shadow_color=shadow_color)
    return surface.blit(surf, pos)


def draw_text_centered(surface: pygame.Surface, text: str, center: tuple,
                       size: int, color: tuple, bold: bool = False,
                       shadow: bool = True) -> pygame.Rect:
    """Blit shadowed text with center at (cx, cy)."""
    surf = render_text(text, size, color, bold=bold, shadow=shadow)
    rect = surf.get_rect(center=center)
    return surface.blit(surf, rect)


# ── Global readability patch ─────────────────────────────────────────────
# Wrap pygame.font.SysFont so existing 385 render call sites automatically
# get the bundled DejaVu Sans Mono font with a +2pt size bump — no per-site
# edits required. The patch is idempotent and only intercepts the
# "monospace" alias which the codebase uses everywhere.

_PATCH_INSTALLED = False


def install_font_patch():
    """Monkey-patch pygame.font.SysFont so every monospace request resolves
    to the bundled font at +2pt for instant readability across the codebase.
    Call this once after pygame.init() and before any font is constructed."""
    global _PATCH_INSTALLED
    if _PATCH_INSTALLED:
        return
    import pygame.font as _pf

    _orig_sysfont = _pf.SysFont

    def _patched_sysfont(name, size, bold=False, italic=False, constructor=None):
        # Identify monospace requests via the family alias the game uses.
        name_l = (name or "").lower()
        if ("mono" in name_l or "consolas" in name_l
                or "courier" in name_l or "menlo" in name_l):
            try:
                return get_font(size, bold=bold, italic=italic)
            except Exception:
                pass
        return _orig_sysfont(name, size, bold=bold, italic=italic,
                             constructor=constructor)

    _pf.SysFont = _patched_sysfont
    _PATCH_INSTALLED = True
