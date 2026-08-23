#!/usr/bin/env python3
"""Generate a 512×512 Play-store icon (void + amber vector wedge)."""
from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_OUT = os.path.join(_HERE, "assets", "android", "icon.png")


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    size = 512
    surf = pygame.Surface((size, size))
    surf.fill((4, 4, 8))
    cx, cy = size // 2, size // 2
    pygame.draw.circle(surf, (18, 22, 28), (cx, cy), 220, 3)
    pygame.draw.circle(surf, (40, 28, 8), (cx, cy), 168, 2)
    wedge = [(cx + 150, cy), (cx - 90, cy - 70), (cx - 90, cy + 70)]
    pygame.draw.polygon(surf, (255, 176, 0), wedge, 0)
    pygame.draw.polygon(surf, (4, 4, 8), [
        (cx + 70, cy), (cx - 50, cy - 28), (cx - 50, cy + 28),
    ])
    os.makedirs(os.path.dirname(_OUT), exist_ok=True)
    pygame.image.save(surf, _OUT)
    print(f"[icon] wrote {_OUT}")


if __name__ == "__main__":
    main()
    sys.exit(0)
