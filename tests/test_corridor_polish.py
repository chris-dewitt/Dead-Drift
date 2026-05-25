"""Coverage for Epic 10.4 corridor visuals + Epic 14.1 boss room polish."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


def test_each_chapter_room1_palette_includes_decay_and_light_keys():
    """Every chapter's first-room palette should declare the new
    decay-layer keys (Epic 10.4) so the directional light + numbered
    panels render with chapter-appropriate colour."""
    from delivery.corridor import make_corridor

    required_keys = ("light_tint", "deep_struct", "panel_num",
                     "floor_grid", "drip")
    for ch in (1, 2, 3, 4):
        c = make_corridor(ch)
        pal = c.rooms[0].palette
        for key in required_keys:
            assert key in pal, f"Ch.{ch} R1 palette missing '{key}'"


def test_corridor_decay_layer_paints_pixels_above_default_bg():
    """Render a brand-new corridor and confirm the decay layer paints
    over the bg fill colour at least somewhere."""
    pygame.init()
    pygame.font.init()
    from delivery.corridor import make_corridor

    for ch in (1, 2, 3, 4):
        c = make_corridor(ch)
        screen = pygame.Surface((1280, 720))
        screen.fill((0, 0, 0))
        c.draw(screen, 0, 0)
        # Sample a pixel inside the corridor surface band — the decay
        # layer should paint *something* there.
        cx = c._surf.get_width() // 2
        cy = (c._surf.get_height() // 2)
        col = c._surf.get_at((cx, cy))[:3]
        assert col != (0, 0, 0), \
            f"Ch.{ch} corridor surface is fully black — decay never painted"


def test_each_chapter_has_a_boss_room_actor():
    """Every chapter's final room should slot a BossRoomActor in."""
    from delivery.corridor import make_corridor
    from delivery.corridor.elements import BossRoomActor

    for ch in (1, 2, 3, 4):
        c = make_corridor(ch)
        last_room = c.rooms[-1]
        actors = [el for el in last_room.elements
                  if isinstance(el, BossRoomActor)]
        assert actors, f"Ch.{ch} last room has no BossRoomActor"


def test_boss_room_actor_draws_without_error():
    """Each chapter's boss actor must render its tableau without raising."""
    pygame.init()
    pygame.font.init()
    from delivery.corridor.elements import (
        boss_actor_gary_den, boss_actor_mycelium_chamber,
        boss_actor_compliance_tribunal, boss_actor_quantum_observation,
    )

    surf = pygame.Surface((1280, 720))
    pal = {
        "light_tint": (210, 120, 60),
        "deep_struct": (50, 20, 10),
        "panel_num": (200, 90, 40),
        "branding": (90, 60, 40),
        "scrub": (60, 30, 20),
        "floor_grid": (90, 40, 20),
        "floor_wear": (60, 34, 18),
        "drip": (255, 140, 60),
    }
    for fn in (boss_actor_gary_den, boss_actor_mycelium_chamber,
               boss_actor_compliance_tribunal, boss_actor_quantum_observation):
        surf.fill((0, 0, 0))
        fn(surf, 600, 1.5, pal)
        # At least some pixel near the anchor should now be non-black.
        # We sample several rows because the actors paint at different
        # vertical regions.
        non_black_found = False
        for y in (200, 250, 300):
            if surf.get_at((600, y))[:3] != (0, 0, 0):
                non_black_found = True
                break
        assert non_black_found, f"{fn.__name__} did not paint over the anchor"
