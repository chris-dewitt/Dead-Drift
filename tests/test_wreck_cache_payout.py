"""Interactive wreck cache must pay real credits, not a phantom HUD tally.

Cracking a wreck weak point used to increment only `_run_debt_reduced`.
The shop spends that tally via `add_debt`, so a 'jackpot' that never called
`pay_off` let players buy hull patches while meta debt went UP.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from antagonists.wreck import SpaceWreck
from physics.body import Vec2
from ship.gun import Bullet


@pytest.fixture
def armed_run(tmp_path, monkeypatch):
    from config import settings as S
    monkeypatch.setattr(S, "SAVES_DIR", str(tmp_path / "saves"))
    monkeypatch.setattr(S, "MANIFEST_FILE", str(tmp_path / "saves/manifest.json"))

    pygame.init()
    pygame.font.init()

    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager
    from ship.ship import PlayerShip

    meta = MetaProgression(save_path=tmp_path / "meta.json")
    ship = PlayerShip()
    rm = RunManager(meta)
    rm.start_run(ship)
    rm.apply_draft(ship)
    return rm, ship, meta


def _weak_point(wreck: SpaceWreck) -> Vec2:
    import math
    rad = math.radians(wreck.angle)
    wplx = wreck.length * 0.2 - wreck.length / 2
    return Vec2(
        wreck.pos.x + wplx * math.cos(rad),
        wreck.pos.y + wplx * math.sin(rad),
    )


def _crack_interactive_wreck(rm) -> SpaceWreck:
    wreck = SpaceWreck(400.0, 300.0, subtype=SpaceWreck.SUBTYPE_INTERACTIVE)
    wreck.angle = 0.0
    rm._wrecks = [wreck]
    weak = _weak_point(wreck)
    for _ in range(3):
        bullet = Bullet(weak, 0.0)
        bullet.pos = Vec2(weak.x, weak.y)
        bullet.lifetime = 1.0
        rm._ship.gun.bullets = [bullet]
        rm._check_bullets()
    return wreck


def test_wreck_cache_pays_off_debt_and_both_credit_wallets(armed_run):
    rm, _ship, meta = armed_run
    debt_before = meta.debt
    recovered_before = rm._run_debt_reduced
    sector_before = rm._sector_credits

    wreck = _crack_interactive_wreck(rm)

    assert wreck.is_triggered is True
    assert meta.debt == debt_before - 1200
    assert rm._run_debt_reduced == recovered_before + 1200
    assert rm._sector_credits == sector_before + 1200


def test_wreck_cache_is_not_spendable_phantom_shop_money(armed_run):
    """Shop spends `_run_debt_reduced` and adds the cost back as debt.

    After a real cache payout, buying a 1,000-cr patch should net -200 vs
    the pre-wreck ledger — not +1,000 on an unpaid jackpot.
    """
    from roguelite.shop import ShopScreen

    rm, ship, meta = armed_run
    rm._run_debt_reduced = 0
    rm._sector_credits = 0
    debt_before = meta.debt

    _crack_interactive_wreck(rm)
    assert rm._run_debt_reduced == 1200
    assert meta.debt == debt_before - 1200

    shop = ShopScreen(rm, ship)
    shop._phase = "browse"
    hull_idx = next(i for i, item in enumerate(shop._items) if item.tag == "hull_patch")
    shop._cursor = hull_idx
    shop._try_purchase()

    assert hull_idx in shop._bought
    assert rm._run_debt_reduced == 200
    assert meta.debt == debt_before - 200
