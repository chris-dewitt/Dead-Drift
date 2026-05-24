"""Vector Bax portrait for menus and loadout — scales cleanly."""
from __future__ import annotations

import math
import pygame


def draw_bax_droid(
    surface: pygame.Surface,
    cx: int,
    cy: int,
    t: float,
    *,
    scale: float = 1.0,
    speaking: bool = False,
) -> None:
    """Draw Bax head + torso centered on (cx, cy)."""
    s = scale

    def pt(x: float, y: float) -> tuple[int, int]:
        return int(cx + x * s), int(cy + y * s)

    def poly(points: list[tuple[float, float]], fill, edge=None, width: int = 1):
        pts = [pt(x, y) for x, y in points]
        pygame.draw.polygon(surface, fill, pts)
        if edge is not None:
            pygame.draw.polygon(surface, edge, pts, max(1, int(width * s)))

    # Shoulder block
    poly(
        [(-34, 8), (34, 8), (30, 42), (-30, 42)],
        (22, 18, 10),
        (120, 85, 20),
        2,
    )
    pygame.draw.rect(
        surface,
        (45, 38, 18),
        pygame.Rect(pt(-18, 14)[0], pt(-18, 14)[1], int(36 * s), int(22 * s)),
        1,
    )

    # Neck
    pygame.draw.rect(
        surface,
        (30, 28, 22),
        pygame.Rect(pt(-8, -2)[0], pt(-8, -2)[1], int(16 * s), int(12 * s)),
    )

    # Head shell
    poly(
        [(-26, -38), (26, -38), (32, -6), (-32, -6)],
        (18, 18, 28),
        (150, 110, 25),
        2,
    )

    # CRT scanlines on visor band
    for sy in range(-36, -8, 4):
        y = int(cy + sy * s)
        x0, x1 = pt(-28, sy)[0], pt(28, sy)[0]
        pygame.draw.line(surface, (35, 28, 8), (x0, y), (x1, y), 1)

    # Visor glow band
    visor = pygame.Surface((int(60 * s), int(14 * s)), pygame.SRCALPHA)
    visor.fill((0, 80, 120, 40))
    surface.blit(visor, (pt(-30, -28)[0], pt(-30, -28)[1]))

    glow = 0.55 + 0.45 * abs(math.sin(t * (3.2 if speaking else 0.9)))
    eye_c = (int(60 + 195 * glow), int(200 * glow), int(255 * glow))
    eye_r = max(2, int(5 * s))
    for ex in (-11, 11):
        ecx, ecy = pt(ex, -22)
        pygame.draw.circle(surface, eye_c, (ecx, ecy), eye_r)
        pygame.draw.circle(surface, (255, 255, 255), (ecx, ecy), max(1, int(s)))

    # Mouth grille
    mouth_y = -10 + (2 * math.sin(t * 14.0) if speaking else 0)
    for mx in range(-12, 13, 6):
        pygame.draw.line(
            surface,
            (200, 145, 35),
            pt(mx, mouth_y),
            pt(mx + 4, mouth_y + 1),
            max(1, int(2 * s)),
        )

    # Antenna + tip pulse
    ax0, ay0 = pt(20, -36)
    ax1, ay1 = pt(28, -54)
    pygame.draw.line(surface, (140, 100, 30), (ax0, ay0), (ax1, ay1), max(1, int(2 * s)))
    tip_pulse = 0.6 + 0.4 * math.sin(t * 5.0)
    tip_c = (int(255 * tip_pulse), int(200 * tip_pulse), int(50 * tip_pulse))
    pygame.draw.circle(surface, tip_c, (ax1, ay1), max(2, int(4 * s)))
    pygame.draw.circle(surface, (255, 240, 180), (ax1, ay1), max(1, int(s)))

    # Ear bolts
    for ex in (-34, 34):
        pygame.draw.circle(surface, (90, 70, 25), pt(ex, -18), max(2, int(4 * s)))
        pygame.draw.circle(surface, (180, 140, 40), pt(ex, -18), max(1, int(2 * s)), 1)
