"""Smoke coverage for chapter 5-6 compliance vessel visibility."""
from __future__ import annotations

from types import SimpleNamespace

import pygame


def _area_has_non_black_pixel(surface: pygame.Surface, cx: int, cy: int, radius: int) -> bool:
    for x in range(cx - radius, cx + radius + 1):
        for y in range(cy - radius, cy + radius + 1):
            if surface.get_at((x, y))[:3] != (0, 0, 0):
                return True
    return False


def test_compliance_vessel_renders_visible_hull():
    from antagonists.compliance_vessel import ComplianceVessel
    from config import settings as S
    from renderer.vector_renderer import VectorRenderer

    surface = pygame.Surface((S.SCREEN_W, S.FLIGHT_H))
    renderer = VectorRenderer(surface)
    run_mgr = SimpleNamespace()
    vessel = ComplianceVessel(320.0, 240.0, run_mgr)
    run_mgr.compliance_vessels = [vessel]

    renderer._draw_compliance_vessels(run_mgr, t=0.0)

    assert _area_has_non_black_pixel(surface, 320, 240, 40)
