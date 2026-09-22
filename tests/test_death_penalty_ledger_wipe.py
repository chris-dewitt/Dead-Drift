"""Post-campaign death must not resurrect unpayable clone-tank debt.

pay_off already banks income after Ch6 clear (ledger_wiped). apply_death_penalty
used to mutate `_data["debt"]` directly, so a dossier/replay death after campaign
clear left ~26.5k that income could never reduce.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from config import settings as S
from roguelite.meta_progression import MetaProgression


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    pygame.font.init()
    yield


def _meta(tmp_path: Path, *, completed=None, debt=0, clone_count=3):
    m = MetaProgression(save_path=tmp_path / "meta.json")
    if completed is not None:
        m._data["chapters_completed"] = list(completed)
    m._data["debt"] = debt
    m._data["clone_count"] = clone_count
    m.save()
    return m


def test_apply_death_penalty_noops_debt_after_ledger_wipe(tmp_path):
    meta = _meta(tmp_path, completed=[1, 2, 3, 4, 5, 6], debt=0, clone_count=7)
    assert meta.ledger_wiped

    meta.apply_death_penalty(sector_index=0)

    assert meta.clone_count == 8
    assert meta.debt == 0
    assert meta._data["debt"] == 0

    # Income still banks; debt must stay gone.
    meta.pay_off(5000, source="TEST PAYOUT")
    assert meta.debt == 0
    assert meta.bar_credits == 5000


def test_apply_death_penalty_refuses_even_with_pre_fix_ghost_balance(tmp_path):
    """Pre-fix saves may still carry leftover `_data['debt']` after Ch6."""
    meta = _meta(tmp_path, completed=[1, 2, 3, 4, 5, 6], debt=84000, clone_count=2)
    meta.apply_death_penalty(sector_index=5)

    assert meta.clone_count == 3
    # Must not grow the ghost / resurrect further charges.
    assert meta._data["debt"] == 84000


def test_apply_death_penalty_still_charges_before_wipe(tmp_path):
    meta = _meta(tmp_path, completed=[1, 2, 3], debt=100000, clone_count=1)
    assert not meta.ledger_wiped

    meta.apply_death_penalty(sector_index=0)
    expected = S.BASE_CLONE_DEBT + S.CLONE_FLUID_FEE + S.WRECKAGE_TOW_FEE
    assert meta.clone_count == 2
    assert meta.debt == 100000 + expected
