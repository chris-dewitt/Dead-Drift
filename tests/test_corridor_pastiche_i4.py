"""Delivery v2 Phase I.4 — 16-bit pastiche regression tests."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from renderer.tiles import draw_tile_platform, TILE_STYLES


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    pygame.font.init()
    yield


def test_every_tile_style_renders_with_outline():
    surf = pygame.Surface((200, 40))
    pal = {"brick": (140, 90, 40), "brick_hi": (230, 180, 90)}
    for style in TILE_STYLES:
        surf.fill((0, 0, 0))
        pal["tile_style"] = style
        draw_tile_platform(surf, 100, 10, 160, 16, pal, 1.0)
        assert surf.get_at((100, 16))[:3] != (0, 0, 0), style


def test_unknown_style_falls_back_to_brick():
    surf = pygame.Surface((200, 40))
    draw_tile_platform(surf, 100, 10, 160, 16,
                       {"tile_style": "nonsense"}, 0.0)
    assert surf.get_at((100, 16))[:3] != (0, 0, 0)


def test_every_chapter_palette_declares_a_tile_style():
    from delivery.corridor import make_corridor
    expected = {1: "brick", 2: "fungus", 3: "cabinet",
                4: "chrome", 5: "girder", 6: "glass"}
    for ch, style in expected.items():
        c = make_corridor(ch)
        for i, room in enumerate(c.rooms):
            assert room.palette.get("tile_style") == style, \
                f"ch{ch} room {i}: {room.palette.get('tile_style')}"


def test_iris_wipe_renders_hole_on_player():
    from delivery.corridor.base import Corridor, Room
    c = Corridor(chapter=1, rooms=[Room(length=2000, palette={}, elements=[])])
    # Half-open iris: player spot must be visible, corner must be black
    c._wipe_t, c._wipe_dir = 0.25, 1
    c.draw(None, 0, 0)
    surf = c.get_surface()
    corner = surf.get_at((2, 2))[:3]
    player_spot = surf.get_at((100, int(c._py) + 16))[:3]
    assert corner == (0, 0, 0)
    assert player_spot != (0, 0, 0), "iris hole must expose the courier"


def test_hud_helmets_track_hit_budget():
    from delivery.corridor.base import Corridor, Room
    c = Corridor(chapter=1, rooms=[Room(length=2000, palette={},
                                        elements=[]) for _ in range(6)])
    assert c.max_hits == 5
    for hits in (0, 2, 5):
        c._hits = hits
        c.draw(None, 0, 0)   # helmet row renders at every budget state


def test_all_chapters_render_with_pastiche(monkeypatch):
    class _Keys:
        def __getitem__(self, k):
            return False
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: _Keys())
    from delivery.corridor import make_corridor
    for ch in range(1, 7):
        c = make_corridor(ch)
        for _ in range(5):
            c.update(1 / 60)
        c.draw(None, 0, 0)
