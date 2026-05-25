"""Aliveness A.5 — Pirate / Marrow / Kress / Sandra get distinct hulls.

Design lock (Chris, May 2026): non-Union NPCs each get their own
in-flight silhouette so the player can identify them by ship shape
before any comm opens. Random ambient traffic doesn't accidentally
spawn one of these character ships."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


_NEW_CLASSES = (
    "pirate_skiff",
    "broadcast_relay",
    "belt_hauler",
    "compliance_courier",
)

_NEW_CLASS_NPC_MAP = {
    "pirate_skiff":       "pirate",
    "broadcast_relay":    "underground_dj",
    "belt_hauler":        "kress",
    "compliance_courier": "sandra",
}


def test_new_classes_exposed():
    """Module-level constants exist."""
    from antagonists.ai_ship import (
        CLASS_PIRATE_SKIFF, CLASS_BROADCAST_RELAY,
        CLASS_BELT_HAULER, CLASS_COMPLIANCE_COURIER,
        ALL_CLASSES,
    )
    for cls in (CLASS_PIRATE_SKIFF, CLASS_BROADCAST_RELAY,
                CLASS_BELT_HAULER, CLASS_COMPLIANCE_COURIER):
        assert cls in ALL_CLASSES


def test_new_classes_have_hull_and_radius_defaults():
    from antagonists.ai_ship import _DEFAULT_HULL, _DEFAULT_RADIUS
    for cls in _NEW_CLASSES:
        assert cls in _DEFAULT_HULL, f"{cls} missing default hull"
        assert cls in _DEFAULT_RADIUS, f"{cls} missing default radius"


def test_new_classes_map_to_correct_npc_keys():
    from antagonists.ai_ship import _HAIL_NPC_BY_CLASS
    for cls, expected_npc in _NEW_CLASS_NPC_MAP.items():
        assert _HAIL_NPC_BY_CLASS.get(cls) == expected_npc


def test_random_ambient_spawn_does_not_pick_character_classes():
    """Aliveness A.5 — Sandra/Marrow/Kress/Krellborn ships are scripted
    in. The random ambient spawn pool only samples the generic faction
    classes so a Ch.1 sector doesn't accidentally surface Sandra."""
    from antagonists.ai_ship import AIShip, _AMBIENT_CLASSES

    pygame.init()
    pygame.font.init()
    seen: set[str] = set()
    for _ in range(500):
        s = AIShip()
        seen.add(s.ship_class)
    assert not (seen & set(_NEW_CLASSES)), (
        f"character-only ship classes leaked into ambient spawn: "
        f"{seen & set(_NEW_CLASSES)}"
    )
    assert seen.issubset(set(_AMBIENT_CLASSES))


def test_each_new_hull_renders_without_error_and_paints_pixels():
    """The four new draw methods each paint something on the surface."""
    pygame.init()
    pygame.font.init()
    from antagonists.ai_ship import AIShip
    from physics.body import Vec2
    from renderer.vector_renderer import VectorRenderer

    screen = pygame.Surface((1280, 720))
    vr = VectorRenderer(screen)
    for cls in _NEW_CLASSES:
        screen.fill((0, 0, 0))
        ship = AIShip(ship_class=cls,
                      pos=Vec2(640, 360),
                      vel=Vec2(100, 0))
        ship.heading = 0.0
        vr._draw_ai_ship(ship, t=1.5)
        # Sample around the ship's anchor.
        non_black = False
        for dy in (-12, -4, 0, 4, 12):
            for dx in (-30, -10, 0, 10, 30):
                if screen.get_at((640 + dx, 360 + dy))[:3] != (0, 0, 0):
                    non_black = True
                    break
            if non_black:
                break
        assert non_black, f"{cls} did not paint near its anchor"
