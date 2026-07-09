"""Delivery v2 Phase I.5 — approach rings, landing grade, RESULT tally."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import tempfile
import pygame
import pytest

from delivery.delivery_sequence import (
    DeliverySequence, _APPROACH_DURATION, _RESULT_HOLD,
    _RING_CREDIT, _RING_LINE_BONUS,
)


class _Keys:
    def __init__(self, held=()):
        self._held = set(held)

    def __getitem__(self, k):
        return k in self._held


@pytest.fixture(autouse=True)
def _pygame(monkeypatch):
    pygame.init()
    pygame.font.init()
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: _Keys())
    yield


def _seq():
    from roguelite.meta_progression import MetaProgression
    from ship.ship import PlayerShip
    meta = MetaProgression(save_path=tempfile.mkdtemp() + "/meta.json")
    return DeliverySequence(meta, chapter=1, ship=PlayerShip())


# ── I.5.1 approach rings ─────────────────────────────────────────────────────

def test_rings_are_preplaced_and_start_unevaluated():
    ds = _seq()
    assert ds._rings_total == 5
    assert all(not r[2] for r in ds._rings)
    assert ds._ring_cr == 0


def test_flying_the_line_pays_credits_and_line_bonus(monkeypatch):
    ds = _seq()
    screen = pygame.Surface((1600, 900))

    def _next_ring_y():
        pend = [r for r in ds._rings if not r[2]]
        return pend[0][1] if pend else ds._ship_screen_y

    frames = 0
    while ds._phase == "approach" and frames < 60 * 8:
        frames += 1
        target = _next_ring_y()
        if ds._ship_screen_y < target - 3:
            monkeypatch.setattr(pygame.key, "get_pressed", lambda: _Keys({pygame.K_s}))
        elif ds._ship_screen_y > target + 3:
            monkeypatch.setattr(pygame.key, "get_pressed", lambda: _Keys({pygame.K_w}))
        else:
            monkeypatch.setattr(pygame.key, "get_pressed", lambda: _Keys())
        ds.update(1 / 60)
        ds.draw(screen)
    assert ds._rings_hit == 5
    assert ds._ring_line_done is True
    assert ds._ring_cr == 5 * _RING_CREDIT + _RING_LINE_BONUS


def test_missing_all_rings_pays_nothing(monkeypatch):
    ds = _seq()
    # Park the ship far above every ring so none register a clean pass.
    for _ in range(int(_APPROACH_DURATION * 60) + 30):
        ds._ship_screen_y = 40.0
        if ds._phase != "approach":
            break
        ds.update(1 / 60)
    assert ds._rings_hit == 0
    assert ds._ring_cr == 0
    assert ds._ring_line_done is False


def test_approach_waits_for_rings_before_lock(monkeypatch):
    """Magnetic lock must not end the approach before the rings play."""
    ds = _seq()
    ds._ship_angle = 0.0    # perfectly aligned from frame 1
    ds.update(1 / 60)
    ds.update(1 / 60)
    # still in approach even though aligned, because rings aren't done
    assert ds._phase == "approach"


# ── I.5.2 landing grade ──────────────────────────────────────────────────────

@pytest.mark.parametrize("zone,total,over,idle,grade", [
    (10.0, 10.0, 0, 0.0, "SILK"),
    (5.0, 10.0, 0, 0.0, "FIRM"),
    (1.0, 10.0, 3, 0.0, "ROUGH"),
    (10.0, 10.0, 0, 4.0, "ROUGH"),
])
def test_landing_grade_matrix(zone, total, over, idle, grade):
    ds = _seq()
    ds._dock_in_zone_t = zone
    ds._dock_total_t = total
    ds._dock_overshoots = over
    ds._dock_idle_t = idle
    ds._finish_dock()
    assert ds._land_grade == grade
    assert ds._phase == "beat3"


def test_grade_stamp_renders_each_grade():
    for grade in ("SILK", "FIRM", "ROUGH"):
        ds = _seq()
        ds._land_grade = grade
        ds._grade_stamp_t = 0.5
        screen = pygame.Surface((1600, 900))
        ds._draw_landing_grade_stamp(screen, 1600, 900)


# ── I.5.3 RESULT tally ───────────────────────────────────────────────────────

def test_ring_credits_fold_into_payout():
    ds = _seq()
    ds._ring_cr = 900
    ds._run_stars = 3
    ds._run = None
    ds._compute_result()
    assert ds._bonus >= 900


def test_result_tally_reveals_and_completes():
    ds = _seq()
    ds._ring_cr = 750
    ds._run_stars = 3
    ds._land_grade = "SILK"
    ds._phase = "result"
    ds._result_t = _RESULT_HOLD
    ds._compute_result()
    screen = pygame.Surface((1600, 900))
    done = False
    for _ in range(int(_RESULT_HOLD * 60) + 10):
        ds.update(1 / 60)
        ds.draw(screen)      # every reveal stage must render
        if ds.is_done:
            done = True
            break
    assert done


def test_full_chain_runs_for_every_chapter(monkeypatch):
    """Each chapter's delivery sequence constructs and its result card draws."""
    from roguelite.meta_progression import MetaProgression
    from ship.ship import PlayerShip
    meta = MetaProgression(save_path=tempfile.mkdtemp() + "/meta.json")
    screen = pygame.Surface((1600, 900))
    for ch in range(1, 7):
        ds = DeliverySequence(meta, chapter=ch, ship=PlayerShip())
        ds._run_stars = 2
        ds._land_grade = "FIRM"
        ds._phase = "result"
        ds._result_t = _RESULT_HOLD
        ds._compute_result()
        for _ in range(20):
            ds.update(1 / 60)
            ds.draw(screen)
