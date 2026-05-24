"""Shared retro / satirical sci-fi UI drawing helpers (pygame)."""

from __future__ import annotations

import math
import random
import pygame


def draw_space_crawl(surface: pygame.Surface, lines: list[str], t: float,
                     *, y_start: int = 72, speed: float = 28.0) -> None:
    """Star-Wars parody crawl — yellow italic-ish block drifting upward."""
    w, h = surface.get_size()
    ov = pygame.Surface((w, h), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 140))
    surface.blit(ov, (0, 0))

    f_title = pygame.font.SysFont("monospace", 11, bold=True)
    f_body = pygame.font.SysFont("monospace", 10)
    block_h = 20 + len(lines) * 16
    scroll_y = y_start - int(t * speed) % (h + block_h + 80)

    title = f_title.render("A LONG TIME AGO IN A DEBT SYSTEM FAR, FAR OVERDUE", True, (255, 220, 80))
    ov.blit(title, (w // 2 - title.get_width() // 2, scroll_y))
    y = scroll_y + 22
    for line in lines:
        s = f_body.render(line, True, (255, 235, 120))
        ov.blit(s, (w // 2 - s.get_width() // 2, y))
        y += 16
    surface.blit(ov, (0, 0))


def draw_mario_brick_platform(surf: pygame.Surface, sx: int, y: int, w: int, h: int,
                            brick: tuple, hi: tuple, t: float = 0.0) -> None:
    """8-bit brick blocks with corporate hazard stripe."""
    tile = 14
    pygame.draw.rect(surf, brick, (sx - w // 2, y, w, h))
    for tx in range(sx - w // 2, sx - w // 2 + w, tile):
        for ty in range(y, y + h, tile // 2):
            pygame.draw.rect(surf, hi, (tx, ty, tile - 2, tile // 2 - 2), 1)
    # Mortar shadow
    pygame.draw.line(surf, (0, 0, 0), (sx - w // 2, y + h - 1), (sx + w // 2, y + h - 1), 1)
    # Blinking corporate bolt (question-block energy)
    if int(t * 3) % 2 == 0:
        cx = sx - w // 2 + w // 2
        pygame.draw.rect(surf, (255, 220, 60), (cx - 4, y + 2, 8, 4))
        pygame.draw.rect(surf, (200, 40, 40), (cx - 4, y + h - 6, 8, 3))


def draw_corporate_pipe(surf: pygame.Surface, sx: int, y: int, h: int,
                        body: tuple, hi: tuple) -> None:
    """Green pipe parody — Nova Soma drainage."""
    pw = 22
    pygame.draw.rect(surf, body, (sx - pw // 2, y, pw, h))
    lip_h = 10
    pygame.draw.rect(surf, hi, (sx - pw // 2 - 3, y - lip_h, pw + 6, lip_h))
    pygame.draw.rect(surf, (255, 80, 80), (sx - pw // 2 + 2, y + h // 3, pw - 4, 3))
    f = pygame.font.SysFont("monospace", 6)
    lbl = f.render("NS", True, (20, 20, 20))
    surf.blit(lbl, (sx - lbl.get_width() // 2, y + 4))


def draw_courier_sprite(surf: pygame.Surface, px: int, py: int, t: float, *,
                        inv: bool = False, grounded: bool = True) -> None:
    """Chunky 80s platformer courier in compliance orange."""
    body = (255, 120, 40) if not inv else (200, 80, 255)
    suit = (40, 90, 200) if not inv else (120, 40, 200)
    trim = (255, 240, 180)
    # Legs
    if grounded:
        lp = t * 9.0
        for side, phase in ((-5, 0), (5, math.pi)):
            ly = int(8 * math.sin(lp + phase))
            pygame.draw.rect(surf, suit, (px + side - 3, py + 22, 6, 10 + ly))
    else:
        pygame.draw.rect(surf, suit, (px - 8, py + 20, 6, 8))
        pygame.draw.rect(surf, suit, (px + 2, py + 18, 6, 8))
    # Torso + ID badge
    pygame.draw.rect(surf, suit, (px - 9, py + 8, 18, 16))
    pygame.draw.rect(surf, trim, (px - 9, py + 8, 18, 16), 1)
    pygame.draw.rect(surf, (255, 220, 0), (px - 2, py + 12, 8, 6))
    # Head + helmet
    pygame.draw.rect(surf, body, (px - 8, py - 4, 16, 14))
    pygame.draw.rect(surf, (0, 200, 255), (px - 5, py, 10, 4))
    pygame.draw.rect(surf, trim, (px - 8, py - 4, 16, 14), 1)
    # Jetpack crate
    pygame.draw.rect(surf, (80, 80, 90), (px + 8, py + 10, 6, 12))
    pygame.draw.rect(surf, (255, 60, 60), (px + 9, py + 12, 4, 2))


def _rgba(r: int, g: int, b: int, a: int) -> tuple[int, int, int, int]:
    """Clamp channel values for pygame SRCALPHA fills."""
    return (
        max(0, min(255, int(r))),
        max(0, min(255, int(g))),
        max(0, min(255, int(b))),
        max(0, min(255, int(a))),
    )


def draw_terminal_backdrop(surface: pygame.Surface, t: float) -> None:
    """Subtle phosphor wash — no full-screen stripe overlays (terminal draws its own scanlines)."""
    w, h = surface.get_size()
    pulse = 0.5 + 0.5 * math.sin(t * 0.6)
    wash = pygame.Surface((w, h), pygame.SRCALPHA)
    wash.fill(_rgba(14, 48, 26, int(5 + 3 * pulse)))
    surface.blit(wash, (0, 0))
    # Corner status LEDs
    for i, (lx, ly) in enumerate([(12, 12), (w - 20, 12), (12, h - 20), (w - 20, h - 20)]):
        on = math.sin(t * 2.5 + i) > 0.2
        col = (0, 255, 120) if on else (30, 50, 30)
        pygame.draw.circle(surface, col, (lx, ly), 3)


def draw_landing_star_destroyer(surface: pygame.Surface, cx: int, cy: int,
                                scale: float, t: float, col_hull: tuple,
                                col_trim: tuple) -> None:
    """Oversized wedge station — Spaceballs scale joke."""
    sw = int(380 * scale)
    sh = int(120 * scale)
    pts = [
        (cx + sw // 2, cy),
        (cx - sw // 2, cy - sh // 3),
        (cx - sw // 2, cy + sh // 3),
    ]
    pygame.draw.polygon(surface, col_hull, pts)
    pygame.draw.polygon(surface, col_trim, pts, max(2, int(2 * scale)))
    # Ridiculous bridge tower
    tw = int(40 * scale)
    th = int(90 * scale)
    pygame.draw.rect(surface, col_trim,
                     (cx + sw // 4, cy - th // 2, tw, th))
    # Running gag label
    if scale > 0.4:
        f = pygame.font.SysFont("monospace", max(8, int(10 * scale)), bold=True)
        s = f.render("DEFINITELY NOT A TRAP", True, (255, 80, 80))
        surface.blit(s, (cx - s.get_width() // 2, cy + sh // 3 + 6))
    # Engine glow
    pulse = 0.5 + 0.5 * math.sin(t * 5)
    pygame.draw.circle(surface, (int(255 * pulse), int(120 * pulse), 0),
                       (cx - sw // 2 - 8, cy), max(3, int(6 * scale)))
