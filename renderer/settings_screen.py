"""renderer/settings_screen.py — CRT-styled settings panel."""
from __future__ import annotations
import math
import pygame
from core.text import get_font
from config import settings as S

_AMBER = S.AMBER_TERM
_GREEN = S.GREEN_TERM
_GREY  = (80, 80, 100)
_DIM   = (40, 42, 50)

ROWS = ("MASTER VOLUME", "FULLSCREEN", "BACK")
VOL_STEP = 0.05   # arrow key increment


def draw(screen: pygame.Surface, cursor: int,
         master_volume: float, fullscreen: bool, t: float) -> None:
    """Draw the settings panel centred on screen."""
    pulse = 0.55 + 0.45 * math.sin(t * 2.0)
    W, H  = S.SCREEN_W, S.SCREEN_H
    cx    = W // 2

    font_hd  = get_font(22, bold=True)
    font_row = get_font(18, bold=True)
    font_val = get_font(16)
    font_sm  = get_font(12)

    panel_w = 500
    panel_h = 230
    panel_x = cx - panel_w // 2
    panel_y = H // 2 - panel_h // 2 - 30

    # Background
    bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    bg.fill((4, 6, 12, 245))
    screen.blit(bg, (panel_x, panel_y))
    pygame.draw.rect(screen, (120, 90, 30), (panel_x, panel_y, panel_w, panel_h), 1)

    # Header
    hdr      = font_hd.render("SYSTEM CONFIG", True, _AMBER)
    hdr_y    = panel_y + 16
    screen.blit(hdr, (cx - hdr.get_width() // 2, hdr_y))
    sep_y = hdr_y + hdr.get_height() + 6
    pygame.draw.line(screen, _DIM, (panel_x + 12, sep_y), (panel_x + panel_w - 12, sep_y), 1)

    row_y0 = sep_y + 14
    row_h  = 46

    for i, label in enumerate(ROWS):
        sel = i == cursor
        y   = row_y0 + i * row_h

        if sel:
            hi = (int(180 + 75 * pulse), int(200 + 55 * pulse), int(120 + 40 * pulse))
        else:
            hi = (130, 130, 150)

        pfx = ">" if sel else " "
        name_s = font_row.render(f"{pfx}  {label}", True, hi)
        screen.blit(name_s, (panel_x + 20, y + 4))

        if label == "MASTER VOLUME":
            _draw_slider(screen, panel_x, panel_w, y + 4, master_volume, sel, pulse, font_val, font_sm)
        elif label == "FULLSCREEN":
            val_text = "ON " if fullscreen else "OFF"
            val_col  = _GREEN if (fullscreen or sel) else _GREY
            val_s    = font_val.render(f"[ {val_text} ]", True, val_col)
            screen.blit(val_s, (panel_x + panel_w - val_s.get_width() - 20, y + 6))

    # Hint bar
    hint_y = panel_y + panel_h - 22
    hint   = font_sm.render(
        "↑↓ select   ← → adjust   ENTER / SPACE toggle   ESC back",
        True, (55, 55, 70),
    )
    screen.blit(hint, (cx - hint.get_width() // 2, hint_y))


def _draw_slider(screen, panel_x, panel_w, row_y,
                 master_volume, selected, pulse, font_val, font_sm) -> None:
    bar_x  = panel_x + 240
    bar_w  = panel_w - 270
    bar_y  = row_y + 14
    bar_h  = 8
    filled = max(0, int(bar_w * master_volume))

    pygame.draw.rect(screen, (20, 22, 30), (bar_x, bar_y, bar_w, bar_h))
    pygame.draw.rect(screen, (40, 42, 50), (bar_x, bar_y, bar_w, bar_h), 1)

    if filled > 0:
        fill_col = (
            (int(0 + 200 * pulse), int(200 * pulse), int(50 * pulse))
            if selected else (70, 100, 45)
        )
        pygame.draw.rect(screen, fill_col, (bar_x, bar_y, filled, bar_h))

    thumb_x = bar_x + filled - 3
    pygame.draw.rect(
        screen,
        (200, 180, 80) if selected else (110, 110, 130),
        (thumb_x, bar_y - 3, 6, bar_h + 6),
    )

    pct_s = font_sm.render(f"{int(master_volume * 100)}%", True, (160, 160, 180))
    screen.blit(pct_s, (bar_x + bar_w + 8, bar_y - 2))
