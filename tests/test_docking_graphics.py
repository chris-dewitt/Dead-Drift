"""Smoke coverage for chapter-specific docking visuals."""
from __future__ import annotations

from types import SimpleNamespace

import pygame


def _pixel_signature(surface: pygame.Surface) -> bytes:
    return pygame.image.tobytes(surface, "RGB")


def test_chapter_station_exteriors_are_distinct():
    from delivery.delivery_sequence import _draw_chapter_station_exterior

    pygame.font.init()
    signatures = []
    for chapter in range(1, 5):
        surface = pygame.Surface((360, 300))
        surface.fill((0, 0, 0))
        _draw_chapter_station_exterior(surface, 180, 150, 1.0, 1.25, chapter)
        assert pygame.mask.from_surface(surface).count() > 500
        signatures.append(_pixel_signature(surface))

    assert len(set(signatures)) == 4


def test_delivery_sequence_renders_chapter_bay_dressing():
    from delivery.delivery_sequence import DeliverySequence

    pygame.font.init()
    signatures = []
    for chapter in range(1, 5):
        delivery = DeliverySequence(SimpleNamespace(), chapter=chapter)
        delivery._phase = delivery.PHASE_LAND
        surface = pygame.Surface((960, 720))
        delivery.draw(surface)
        assert pygame.mask.from_surface(surface).count() > 1000
        signatures.append(_pixel_signature(surface))

    assert len(set(signatures)) == 4
