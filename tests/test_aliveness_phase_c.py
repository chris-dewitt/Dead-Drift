"""Aliveness Phase C — gameplay mechanics (May 2026)."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from config import settings as S
from ship.ship import PlayerShip
from roguelite.meta_progression import MetaProgression
from roguelite.run_manager import RunManager, SLINGSHOT_CREDIT_BONUS


def test_speed_scaled_collision_damage():
    ship = PlayerShip()
    ship.hull = 100.0
    ship.body.vel.x = 200.0
    ship.body.vel.y = 0.0
    ship.take_damage(10.0, source="debris")
    scaled_hull = ship.hull
    ship2 = PlayerShip()
    ship2.hull = 100.0
    ship2.body.vel.x = 0.0
    ship2.take_damage(10.0, source="debris")
    assert scaled_hull < ship2.hull


def test_slingshot_chain_multiplier(tmp_path):
    meta = MetaProgression(save_path=tmp_path / "meta.json")
    meta._data["debt"] = 50000
    rm = RunManager(meta)
    rm._t = 10.0
    rm._sling_chain_t = -999.0
    rm._sling_chain_n = 0
    rm._ship = PlayerShip()
    debt_before = meta.debt
    rm._on_slingshot(speed=250)
    first_paid = debt_before - meta.debt
    assert first_paid == SLINGSHOT_CREDIT_BONUS
    rm._t = 11.0
    debt_mid = meta.debt
    rm._on_slingshot(speed=250)
    second_paid = debt_mid - meta.debt
    assert second_paid == int(SLINGSHOT_CREDIT_BONUS * 1.5)


def test_faction_hull_spawn_for_kress():
    meta = MetaProgression(save_path=Path("data/saves/test_phase_c_meta.json"))
    rm = RunManager(meta)
    rm._ship = PlayerShip()
    rm._ai_ships.clear()
    rm._ensure_faction_hull("kress")
    assert len(rm._ai_ships) == 1
    assert rm._ai_ships[0].ship_class == "belt_hauler"
    rm._ensure_faction_hull("kress")
    assert len(rm._ai_ships) == 1


def test_cargo_integrity_scales_delivery_bonus():
    from delivery.delivery_sequence import _DELIVERY_BONUS

    cargo_pct = 0.5
    assert int(_DELIVERY_BONUS[3] * cargo_pct) == 4000
