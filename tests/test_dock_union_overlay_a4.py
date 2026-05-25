"""Aliveness A.4 — Union 404 dock overlay + Gary at the receiving window."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


def test_overlay_paints_amber_pixels_for_every_chapter():
    pygame.init()
    pygame.font.init()
    from delivery.delivery_sequence import _draw_union_404_overlay

    for chapter in (1, 2, 3, 4):
        surf = pygame.Surface((1280, 720))
        surf.fill((10, 10, 10))   # non-pure-black so we can tell what changed
        _draw_union_404_overlay(surf, 1280, 720, t=1.0, chapter=chapter)
        # Sample the roundel area (top centre).
        r, g, b = surf.get_at((1280 // 2, 76))[:3]
        # Roundel uses amber accents — at least one of (r, g) should
        # be significantly above the background grey we filled with.
        assert r >= 60 and g >= 30 and b <= 120, (
            f"Ch.{chapter}: amber roundel never painted at top centre "
            f"(got {(r, g, b)})"
        )


def test_dock_master_window_rendered_in_right_band():
    """Gary's receiving window should sit on the right-hand side."""
    pygame.init()
    pygame.font.init()
    from delivery.delivery_sequence import _draw_union_404_overlay

    surf = pygame.Surface((1280, 720))
    surf.fill((10, 10, 10))
    _draw_union_404_overlay(surf, 1280, 720, t=0.5, chapter=1)
    # The window pane is roughly centred at x = 1280 - 184 + 32 = 1128
    # at y = 720 - 192 + 35 = 563. Should be amber-lit (warm yellow).
    r, g, b = surf.get_at((1128, 563))[:3]
    assert r > g > b, f"window glass not amber-lit (got {(r, g, b)})"


def test_overlay_is_called_from_both_beat2_and_beat3():
    """Aliveness A.4 — Union overlay must render in Beat 2 (land) AND Beat 3."""
    from pathlib import Path
    src = Path("delivery/delivery_sequence.py").read_text(encoding="utf-8")
    # Two call sites: _draw_land for Beat 2, _draw_beat3 for Beat 3.
    assert src.count("_draw_union_404_overlay(surface") >= 2, (
        "Union overlay should fire on both Beat 2 and Beat 3 renders"
    )
