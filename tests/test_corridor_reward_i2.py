"""Delivery v2 Phase I.2 — reward loop regression tests.

Covers style-over-speed scoring, the staged tally screen, chip chains,
placement helpers, room-clear tallies, and the COURIER'S PRIDE stamp.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from delivery.corridor.base import (
    Corridor, Room, FLOOR_Y,
    CHIP_CHAIN_MAX, PUNCTUALITY_BONUS, STAR3_CHIP_PCT, STAR2_CHIP_PCT,
)
from delivery.corridor.elements import Collectible, Secret, chip_arc, chip_line

DT = 1.0 / 60.0


class _Keys:
    def __init__(self, held=()):
        self._held = set(held)

    def __getitem__(self, k):
        return k in self._held


class _FakeMeta:
    def __init__(self):
        self.pride: list[int] = []

    def mark_courier_pride(self, chapter: int) -> bool:
        self.pride.append(chapter)
        return True


@pytest.fixture(autouse=True)
def _pygame(monkeypatch):
    pygame.init()
    pygame.font.init()
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: _Keys())
    yield


def _room_with(n_chips: int = 6, n_secrets: int = 0, length: int = 3000) -> Room:
    els: list = [Collectible(200 + i * 40, FLOOR_Y - 16, value=200)
                 for i in range(n_chips)]
    els += [Secret(1200 + i * 60, FLOOR_Y - 16, value=500)
            for i in range(n_secrets)]
    return Room(length=length, palette={}, elements=els, name="TEST BAY")


def _collect_chip(c: Corridor, chip: Collectible):
    c._px, c._py = chip.x, chip.y - 4
    c._check_collectibles(c.rooms[c._room_idx])


# ── I.2.3 chip chains ───────────────────────────────────────────────────────

def test_chain_builds_within_window_and_caps():
    room = _room_with(7)
    c = Corridor(chapter=1, rooms=[room])
    chains = []
    from core.event_bus import bus, EVT_CORRIDOR_CHIP
    bus.subscribe(EVT_CORRIDOR_CHIP, lambda chain=1, **_: chains.append(chain))
    for chip in room.elements:
        _collect_chip(c, chip)
        c.update(0.2)                    # inside the 1.5 s window
    assert chains == [1, 2, 3, 4, 5, 5, 5]
    assert c._best_chain == CHIP_CHAIN_MAX


def test_chain_resets_after_window_expires():
    room = _room_with(2)
    c = Corridor(chapter=1, rooms=[room])
    _collect_chip(c, room.elements[0])
    for _ in range(12):
        c.update(0.2)                    # 2.4 s ≫ window
    assert c._chain == 0
    _collect_chip(c, room.elements[1])
    assert c._chain == 1                 # fresh chain, not ×2


def test_chained_chips_multiply_credits():
    room = _room_with(3)
    c = Corridor(chapter=1, rooms=[room])
    for chip in room.elements:
        _collect_chip(c, chip)
        c.update(0.05)
    # 200×1 + 200×2 + 200×3
    assert c._credits == 200 + 400 + 600
    assert c._floaters, "pickup pop text must spawn"


# ── I.2.2 placement helpers ─────────────────────────────────────────────────

def test_chip_arc_rises_between_endpoints():
    arc = chip_arc(100, 300, 260, 300, n=5)
    assert len(arc) == 5
    assert arc[0].y == pytest.approx(300) and arc[-1].y == pytest.approx(300)
    assert min(ch.y for ch in arc) < 300 - 30


def test_chip_line_spacing():
    line = chip_line(50, 280, n=4, dx=34)
    assert [ch.x for ch in line] == [50, 84, 118, 152]
    assert all(ch.y == 280 for ch in line)


# ── I.2.1 style scoring ─────────────────────────────────────────────────────

def test_full_sweep_slow_run_still_three_stars():
    """Time must never rate the run — the entire point of I.2.1."""
    room = _room_with(6)
    c = Corridor(chapter=1, rooms=[room])
    for chip in room.elements:
        _collect_chip(c, chip)
        c.update(0.05)
    c._elapsed = 999.0                   # absurdly slow
    c._finish()
    assert c._stars == 3
    assert c._punctual is False          # no bonus, but no punishment


def test_low_collection_fast_clean_run_one_star():
    room = _room_with(10)
    c = Corridor(chapter=1, rooms=[room])
    c._collectibles_found = 3            # 30% < STAR2_CHIP_PCT
    c._elapsed = 5.0
    c._hits = 0
    c._finish()
    assert c._stars == 1


def test_mid_collection_two_stars_and_punctuality_pays_credits():
    room = _room_with(10)
    c = Corridor(chapter=1, rooms=[room])
    c._collectibles_found = 5            # 50%
    c._elapsed = 1.0                     # under par
    c._finish()
    assert c._stars == 2
    assert c._punctual is True
    assert c._result_credits >= PUNCTUALITY_BONUS


def test_hits_gate_three_stars():
    room = _room_with(4)
    c = Corridor(chapter=1, rooms=[room])
    c._collectibles_found = 4            # 100%
    c._hits = 2                          # too battered for 3★
    c._finish()
    assert c._stars == 2


# ── I.2.1 tally screen ──────────────────────────────────────────────────────

def test_tally_emits_ticks_stars_and_bax_grade():
    from core.event_bus import bus, EVT_CORRIDOR_TALLY, EVT_CORRIDOR_STAR
    counts = {"tally": 0, "star": 0}
    bus.subscribe(EVT_CORRIDOR_TALLY, lambda **_: counts.__setitem__("tally", counts["tally"] + 1))
    bus.subscribe(EVT_CORRIDOR_STAR,  lambda **_: counts.__setitem__("star",  counts["star"] + 1))
    room = _room_with(6)
    c = Corridor(chapter=1, rooms=[room])
    for chip in room.elements:
        _collect_chip(c, chip)
        c.update(0.05)
    c._finish()
    for _ in range(900):
        c.update(DT)
        c.draw(None, 0, 0)               # every stage must render
        if c._tally_t >= c._tally_done_t:
            break
    assert counts["star"] == c._stars == 3
    assert counts["tally"] > 4           # chip ticks + row stamps
    assert c._bax_graded is True


def test_enter_skips_then_exits_tally():
    room = _room_with(6)
    c = Corridor(chapter=1, rooms=[room])
    c._finish()
    assert not c.is_done                 # tally holds the corridor open
    ev = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN})
    c.handle_key(ev)                     # fast-forward the count-up
    assert c._tally_t >= c._tally_done_t
    assert c._stars_shown == c._stars
    assert not c.is_done
    c.handle_key(ev)                     # second press hands off
    assert c.is_done


# ── I.2.4 room-clear flourish ───────────────────────────────────────────────

def test_room_wipe_reports_chip_tally():
    r1 = _room_with(2, length=800)
    r2 = _room_with(0, length=800)
    c = Corridor(chapter=1, rooms=[r1, r2])
    for chip in r1.elements:
        _collect_chip(c, chip)
    c._start_wipe_out()
    assert c._transition_subcaption.startswith("CHIPS 2/2")
    assert "CLEAN SWEEP" in c._transition_subcaption


def test_room_wipe_reports_missed_chips():
    r1 = _room_with(4, length=800)
    r2 = _room_with(0, length=800)
    c = Corridor(chapter=1, rooms=[r1, r2])
    _collect_chip(c, r1.elements[0])
    c._start_wipe_out()
    assert c._transition_subcaption == "CHIPS 1/4"


# ── I.2.5 COURIER'S PRIDE ───────────────────────────────────────────────────

def test_perfect_sweep_marks_pride():
    room = _room_with(3, n_secrets=1)
    c = Corridor(chapter=4, rooms=[room])
    c.meta = _FakeMeta()
    for el in room.elements:
        if isinstance(el, Collectible):
            _collect_chip(c, el)
            c.update(0.05)
    sec = [el for el in room.elements if isinstance(el, Secret)][0]
    c._px, c._py = sec.x, sec.y - 4
    c._check_collectibles(room)
    c._finish()
    assert c.meta.pride == [4]


def test_partial_sweep_does_not_mark_pride():
    room = _room_with(3, n_secrets=1)
    c = Corridor(chapter=4, rooms=[room])
    c.meta = _FakeMeta()
    _collect_chip(c, room.elements[0])   # 1 of 3 chips, no secret
    c._finish()
    assert c.meta.pride == []


def test_meta_progression_persists_pride(tmp_path):
    from roguelite.meta_progression import MetaProgression
    meta = MetaProgression(save_path=tmp_path / "meta.json")
    assert meta.mark_courier_pride(2) is True
    assert meta.mark_courier_pride(2) is False       # already earned
    assert meta.has_courier_pride(2)
    reloaded = MetaProgression(save_path=tmp_path / "meta.json")
    assert reloaded.has_courier_pride(2)
    assert not reloaded.has_courier_pride(5)


def test_carousel_renders_with_pride_stamp(tmp_path):
    from roguelite.meta_progression import MetaProgression
    from renderer.cargo_carousel import draw_carousel
    meta = MetaProgression(save_path=tmp_path / "meta.json")
    meta._data["chapters_completed"] = [1]
    meta.mark_courier_pride(1)
    screen = pygame.Surface((1280, 720))
    draw_carousel(screen, meta=meta, stats=None, cursor=0, t=0.0)


# ── factory wiring ──────────────────────────────────────────────────────────

def test_make_corridor_attaches_meta():
    from delivery.corridor import make_corridor
    fake = _FakeMeta()
    c = make_corridor(2, meta=fake)
    assert c.meta is fake
