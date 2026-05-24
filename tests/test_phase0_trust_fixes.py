"""Regression coverage for the Phase 0 trust fixes."""
from __future__ import annotations

from types import SimpleNamespace

import pygame
import pytest


def test_thruster_heats_only_when_firing_and_recovers():
    from core.event_bus import bus, EVT_THRUSTER_OVERHEAT
    from ship.loadout import SignalChain
    from ship.modules.thruster import Thruster

    chain = SignalChain()
    thruster = Thruster(tier="standard")
    chain.install(thruster, 1)

    chain.update(1.0)
    assert thruster.heat == pytest.approx(0.0)

    thruster.mark_firing()
    chain.update(1.0)
    assert thruster.heat == pytest.approx(12.0)

    chain.update(0.25)
    assert thruster.heat < 12.0

    events = []

    def _capture(**payload):
        events.append(payload)

    bus.subscribe(EVT_THRUSTER_OVERHEAT, _capture)
    try:
        thruster.heat = 99.0
        thruster.mark_firing()
        chain.update(1.0)
        assert thruster.overheated is True
        assert thruster.heat == pytest.approx(100.0)
        assert len(events) == 1

        for _ in range(3):
            chain.update(1.0)
        assert thruster.overheated is False
        assert thruster.heat <= 58.0
    finally:
        bus.unsubscribe(EVT_THRUSTER_OVERHEAT, _capture)


def test_life_support_absorbs_standard_thruster_heat():
    from ship.loadout import SignalChain
    from ship.modules.life_support import LifeSupport
    from ship.modules.thruster import Thruster

    chain = SignalChain()
    thruster = Thruster(tier="standard")
    chain.install(LifeSupport(), 0)
    chain.install(thruster, 1)

    thruster.mark_firing()
    chain.update(1.0)

    assert thruster.heat == pytest.approx(0.0)


def test_ice_field_applies_thrust_penalty_when_inside():
    from antagonists.ice_field import IceField
    from physics.body import Vec2

    scales = []
    ship = SimpleNamespace(
        pos=Vec2(150, 150),
        body=SimpleNamespace(vel=Vec2(10, 0), apply_force=lambda force: None),
        apply_thrust_scale=scales.append,
    )
    ice = IceField(x=100, y=100)

    assert ice.apply_to(ship) is True
    assert scales == [pytest.approx(0.70)]

    ship.pos = Vec2(20, 20)
    assert ice.apply_to(ship) is False
    assert len(scales) == 1


def test_shop_escape_routes_to_shop_before_pause():
    from core.game import Game
    from core.state_manager import GameState

    class _States:
        state = GameState.SHOP

    class _Shop:
        key = None

        def handle_key(self, event):
            self.key = event.key

    game = Game.__new__(Game)
    game.states = _States()
    game._shop = _Shop()
    game._pause_game = lambda: pytest.fail("shop ESC should not open pause")

    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    Game._route_keydown(game, event)

    assert game._shop.key == pygame.K_ESCAPE


def test_phase0_portraits_have_keys_and_render():
    from terminal import npc_portraits

    pygame.font.init()
    for npc_name, key in [
        ("INSPECTOR HOLT", "cargo_inspector"),
        ("RELAY-7 FELIX", "nervous_fence"),
    ]:
        assert npc_portraits._NAME_TO_KEY[npc_name] == key
        assert key in npc_portraits._DISPATCH
        assert key in npc_portraits._BACKDROPS

        surface = pygame.Surface((180, 240))
        npc_portraits.draw_portrait(surface, npc_name, pygame.Rect(0, 0, 180, 240), 0, 1.0)
        assert pygame.mask.from_surface(surface).count() > 0


def test_shop_module_no_longer_exposes_stale_shop_sectors():
    import roguelite.shop as shop

    assert not hasattr(shop, "SHOP_SECTORS")
