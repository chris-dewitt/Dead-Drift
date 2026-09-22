"""Post-campaign ledger wipe must keep debt gone forever.

pay_off already banks income to bar_credits after Ch6 clear, but add_debt
(dock fees / bribes / shop / veteran fees) still mutated `_data["debt"]`,
and complete_chapter(6) never zeroed the balance — so a rough 1★ dossier
replay could resurrect unpayable debt on a wiped ledger.
"""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from roguelite.meta_progression import MetaProgression


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    pygame.font.init()
    yield


def _meta(tmp_path, *, completed=None, debt=50000):
    m = MetaProgression(save_path=tmp_path / "meta.json")
    if completed is not None:
        m._data["chapters_completed"] = list(completed)
    m._data["debt"] = debt
    m.save()
    return m


def test_complete_chapter_six_zeros_debt(tmp_path):
    meta = _meta(tmp_path, completed=[1, 2, 3, 4, 5], debt=84000)
    meta.complete_chapter(6)
    assert meta.ledger_wiped
    assert meta.debt == 0
    assert meta._data["debt"] == 0


def test_add_debt_noops_after_ledger_wipe(tmp_path):
    meta = _meta(tmp_path, completed=[1, 2, 3, 4, 5, 6], debt=12000)
    meta.add_debt(2200, source="DOCK FEES")
    assert meta.debt == 0
    # Storage ghost (pre-fix saves) must not grow either.
    assert meta._data["debt"] == 12000


def test_debt_property_hides_pre_fix_ghost_balance(tmp_path):
    meta = _meta(tmp_path, completed=[1, 2, 3, 4, 5, 6], debt=99999)
    assert meta.debt == 0
    assert meta.is_debt_cleared


def test_rough_one_star_delivery_after_wipe_does_not_readd_debt(tmp_path):
    from delivery.delivery_sequence import DeliverySequence
    from ship.ship import PlayerShip

    meta = _meta(tmp_path, completed=[1, 2, 3, 4, 5, 6], debt=12000)
    ds = DeliverySequence(meta, chapter=2, ship=PlayerShip())
    ds._run_stars = 1
    ds._dock_bonus_cr = -200
    ds._ring_cr = 0
    ds._run = type("R", (), {"credits_earned": 0})()
    ds._compute_result()
    assert meta.debt == 0
    assert meta._data["debt"] == 12000  # add_debt refused; ghost unchanged
    assert meta.bar_credits == 0


def test_positive_delivery_after_wipe_still_banks_bar_credits(tmp_path):
    from delivery.delivery_sequence import DeliverySequence
    from ship.ship import PlayerShip

    meta = _meta(tmp_path, completed=[1, 2, 3, 4, 5, 6], debt=12000)
    ds = DeliverySequence(meta, chapter=2, ship=PlayerShip())
    ds._run_stars = 3
    ds._dock_bonus_cr = 500
    ds._ring_cr = 900
    ds._run = type("R", (), {"credits_earned": 2000})()
    ds._compute_result()
    assert meta.debt == 0
    assert meta.bar_credits == 8000 + 500 + 900 + 2000
