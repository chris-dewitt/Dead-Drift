"""Regression coverage for Nova Soma compliance vessel rendering."""
from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


def test_compliance_vessel_is_drawn_when_present():
    pygame.init()
    pygame.font.init()

    from antagonists.compliance_vessel import ComplianceVessel
    from renderer.vector_renderer import VectorRenderer

    surface = pygame.Surface((320, 240))
    renderer = VectorRenderer(surface)
    vessel = ComplianceVessel(160.0, 120.0, SimpleNamespace(_ship=None))
    run_mgr = SimpleNamespace(compliance_vessels=[vessel])

    before = surface.get_at((160, 120))[:3]
    renderer._draw_compliance_vessels(run_mgr, t=0.0)
    after = surface.get_at((160, 120))[:3]

    assert after != before
