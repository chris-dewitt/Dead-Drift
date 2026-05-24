"""Regression coverage for the discrete tether snap-charge HUD."""
from __future__ import annotations

from types import SimpleNamespace

import pygame
import pytest


def test_hud_renderer_reports_active_tether_snap_charge():
    from renderer.hud_renderer import HUDRenderer

    surface = pygame.Surface((320, 220))
    renderer = HUDRenderer(surface)
    active_tether = SimpleNamespace(is_active=True, lateral_speed=1000.0)
    inactive_tether = SimpleNamespace(is_active=False, lateral_speed=1000.0)
    run_mgr = SimpleNamespace(barges=[
        SimpleNamespace(_tether=inactive_tether),
        SimpleNamespace(_tether=active_tether),
    ])

    assert renderer._snap_charge(run_mgr) == pytest.approx(1.0)
    assert renderer._snap_charge(SimpleNamespace(barges=[])) is None


def test_snap_charge_draws_only_when_tethered():
    from ship.hud import HUD

    pygame.font.init()
    ship = SimpleNamespace(
        hull=200.0,
        hull_pct=1.0,
        body=SimpleNamespace(speed=lambda: 0.0),
        angle=0.0,
        cargo=None,
        chain=SimpleNamespace(slots=[]),
    )
    hud = HUD(ship)

    surface = pygame.Surface((320, 220))
    hud.draw(surface, snap_charge=None)
    assert surface.get_at((60, 176))[:3] == (0, 0, 0)

    hud.draw(surface, snap_charge=0.5)
    assert surface.get_at((60, 176))[:3] != (0, 0, 0)
