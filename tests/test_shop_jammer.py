"""The EM jammer must still be in effect when the next sector's barges spawn.

The black market opens between sectors. Leaving it loads a fresh sector and
discards every barge that was on the field when the player paid. Arming those
doomed barges' intercept cooldown did nothing — and a high intercept cooldown
is what starts the harpoon, not what disables it.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path
from types import SimpleNamespace

import pygame
import pytest

from config import settings as S


def _jammer():
    from roguelite.shop import _POOL_ALL
    return next(item for item in _POOL_ALL if item.tag == "jammer")


def test_jammer_arms_spawn_suppression_not_the_barges_about_to_be_deleted():
    doomed = SimpleNamespace(_intercept_cd=0.0)
    run_mgr = SimpleNamespace(_barges=[doomed], _barge_suppression_t=0.0)

    _jammer().apply(SimpleNamespace(), run_mgr)

    assert run_mgr._barge_suppression_t == pytest.approx(S.JAMMER_COOLDOWN)
    # The completed sector's barge is not the carrier of the purchase.
    assert doomed._intercept_cd == 0.0


def test_jammer_extends_an_existing_suppression_window():
    run_mgr = SimpleNamespace(_barges=[], _barge_suppression_t=12.0)

    _jammer().apply(SimpleNamespace(), run_mgr)

    assert run_mgr._barge_suppression_t == pytest.approx(S.JAMMER_COOLDOWN)


def test_jammer_blocks_the_barge_the_next_sector_would_spawn():
    pygame.init()
    pygame.font.init()
    from roguelite.meta_progression import MetaProgression
    from roguelite.run_manager import RunManager

    path = Path("data/saves") / "test_shop_jammer_meta.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    rm = RunManager(MetaProgression(save_path=path))
    _jammer().apply(SimpleNamespace(), rm)

    # Same wipe the shop exit performs before the new sector asks for a barge.
    rm._barges.clear()
    rm._spawn_barge(immediate_chase=True)

    assert rm._barges == []
    assert rm._barge_suppression_t == pytest.approx(S.JAMMER_COOLDOWN)
