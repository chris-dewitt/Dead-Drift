"""Delivery v2 Phase I.3a — level-system regression tests.

Covers the new element vocabulary (springs, conveyors, breakables,
?-blocks, warp pipes, timed lifts), the three power-ups, chase-room
camera behaviour, and the hit-budget rebalance.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from delivery.corridor.base import (
    Corridor, Room, FLOOR_Y, PLAYER_H, MAX_HITS, LONG_RUN_MAX_HITS,
)
from delivery.corridor.elements import (
    Spring, ConveyorBelt, BreakableBlock, QuestionBlock, PowerUp,
    WarpPipe, TimedLift, Collectible, Checkpoint,
)

DT = 1.0 / 60.0


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


def _bare(els=None, length: int = 100_000, auto_scroll: float = 0.0) -> Corridor:
    return Corridor(chapter=1, rooms=[Room(
        length=length, palette={}, elements=els or [],
        auto_scroll=auto_scroll)])


def _hold(monkeypatch, *keys):
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: _Keys(keys))


# ── I.3.2 elements ──────────────────────────────────────────────────────────

def test_spring_launches_far_above_jump_height(monkeypatch):
    c = _bare([Spring(120)])
    c._px = 120.0
    top = c._py
    for _ in range(150):
        c.update(DT)
        top = min(top, c._py)
    rise = (FLOOR_Y - PLAYER_H) - top
    assert rise > 180, f"spring rise {rise:.0f}px must beat a full jump (~109px)"


def test_spring_rise_ignores_jump_cut(monkeypatch):
    """A spring launch is not a jump — releasing the jump key must not
    cut its rise (the I.1 jump-cut gravity only applies to real jumps)."""
    c = _bare([Spring(120)])
    c._px = 120.0
    # no keys held at all — worst case for the old jump-cut behaviour
    top = c._py
    for _ in range(150):
        c.update(DT)
        top = min(top, c._py)
    assert (FLOOR_Y - PLAYER_H) - top > 180


def test_conveyor_drags_standing_courier(monkeypatch):
    belt = ConveyorBelt(300, FLOOR_Y - 60, 200, drift=90.0)
    c = _bare([belt])
    c._px, c._py = 300.0, belt.y - PLAYER_H - 1
    c._pvy = 10.0
    x0 = None
    for _ in range(60):
        c.update(DT)
        if x0 is None and isinstance(c._ground_el, ConveyorBelt):
            x0 = c._px
    assert x0 is not None and c._px > x0 + 40


def test_breakable_blocks_walk_but_shatters_sprint(monkeypatch):
    blk = BreakableBlock(520, chips=3)
    c = _bare([blk])
    c._px = 60.0
    _hold(monkeypatch, pygame.K_d)
    for _ in range(300):
        c.update(DT)
    assert not blk.broken and c._px < 520

    blk2 = BreakableBlock(520, chips=3)
    c2 = _bare([blk2])
    c2._px = 60.0
    before = c2._collectibles_total
    _hold(monkeypatch, pygame.K_d, pygame.K_LSHIFT)
    for _ in range(300):
        c2.update(DT)
        if blk2.broken:
            break
    assert blk2.broken
    assert c2._collectibles_total == before + 3, "crate chips must join the room"


def test_qblock_pops_from_below_and_spawns_powerup(monkeypatch):
    qb = QuestionBlock(200, FLOOR_Y - 150, contains="hardhat")
    c = _bare([qb])
    c._px = 200.0
    c.handle_key(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
    _hold(monkeypatch, pygame.K_SPACE)
    for _ in range(120):
        c.update(DT)
        if qb.used:
            break
    assert qb.used
    pus = [e for e in c.rooms[0].elements if isinstance(e, PowerUp)]
    assert len(pus) == 1 and pus[0].kind == "hardhat"


def test_qblock_chips_extend_collection_totals(monkeypatch):
    qb = QuestionBlock(200, FLOOR_Y - 150, contains="chips", n_chips=3)
    c = _bare([qb])
    c._px = 200.0
    before = c._collectibles_total
    c.handle_key(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE}))
    _hold(monkeypatch, pygame.K_SPACE)
    for _ in range(120):
        c.update(DT)
        if qb.used:
            break
    assert c._collectibles_total == before + 3


def test_warp_pipe_teleports_on_down(monkeypatch):
    pipe = WarpPipe(300, exit_x=900)
    c = _bare([pipe])
    c._px, c._py = 300.0, pipe.y_top - PLAYER_H
    c._grounded = True
    c.handle_key(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_DOWN}))
    assert c._px == 900.0


def test_timed_lift_carries_rider(monkeypatch):
    lift = TimedLift(500, y_top=180, y_bot=300, speed=60)
    c = _bare([lift])
    c._px, c._py = 500.0, lift.y - PLAYER_H - 2
    c._pvy = 5.0
    for _ in range(90):
        c.update(DT)
    assert isinstance(c._ground_el, TimedLift)
    assert abs((c._py + PLAYER_H) - lift.y) < 2.0


# ── I.3.3 power-ups ─────────────────────────────────────────────────────────

def test_hardhat_eats_one_hit(monkeypatch):
    c = _bare([])
    c._grant_power("hardhat")
    h0 = c._hits
    c._take_hit()
    assert c._hits == h0
    assert c._power_kind is None
    c._take_hit()          # second hit is real
    assert c._hits == h0 + 1


def test_stimsoles_raise_speed_cap_then_expire(monkeypatch):
    c = _bare([])
    c._grant_power("stimsoles")
    _hold(monkeypatch, pygame.K_d, pygame.K_LSHIFT)
    for _ in range(240):
        c.update(DT)
    assert c._pvx > 360          # 320 sprint × 1.25 = 400 cap
    c._power_t = 0.01
    c.update(DT)
    assert c._power_kind is None


def test_magboots_pull_chips(monkeypatch):
    chip = Collectible(260, FLOOR_Y - 90)
    c = _bare([chip])
    c._grant_power("magboots")
    c._px = 200.0
    for _ in range(30):
        c.update(DT)
    assert chip.x < 250, "chip must drift toward the courier"


def test_powerup_pickup_via_collect_path(monkeypatch):
    pu = PowerUp(240, FLOOR_Y - 30, "stimsoles")
    c = _bare([pu])
    c._px, c._py = 240.0, FLOOR_Y - PLAYER_H
    c._check_collectibles(c.rooms[0])
    assert c._power_kind == "stimsoles"


# ── I.3.4 chase room ────────────────────────────────────────────────────────

def test_chase_camera_sweeps_and_crushes(monkeypatch):
    c = _bare([], auto_scroll=140.0)
    h0 = c._hits
    for _ in range(600):
        c.update(DT)
        if c._hits > h0:
            break
    assert c._cam_x > 0, "camera must sweep on its own"
    assert c._hits > h0, "standing still must eventually cost a hit"


def test_normal_room_camera_stays_player_locked(monkeypatch):
    c = _bare([])
    for _ in range(60):
        c.update(DT)
    assert c._cam_x == pytest.approx(c._px - 100.0)


# ── I.3.5 hit budget ────────────────────────────────────────────────────────

def test_max_hits_scales_with_room_count(monkeypatch):
    short = Corridor(chapter=1, rooms=[
        Room(length=800, palette={}, elements=[]) for _ in range(3)])
    long_ = Corridor(chapter=1, rooms=[
        Room(length=800, palette={}, elements=[]) for _ in range(6)])
    assert short.max_hits == MAX_HITS
    assert long_.max_hits == LONG_RUN_MAX_HITS


def test_checkpoint_patches_one_hit(monkeypatch):
    c = _bare([Checkpoint(400)])
    c._hits = 2
    c._px = 300.0
    _hold(monkeypatch, pygame.K_d)
    for _ in range(120):
        c.update(DT)
        if c._px > 420:
            break
    assert c._hits == 1


# ── integration ─────────────────────────────────────────────────────────────

def test_all_chapters_still_build_update_draw(monkeypatch):
    from delivery.corridor import make_corridor
    _hold(monkeypatch, pygame.K_d)
    for ch in range(1, 7):
        c = make_corridor(ch)
        for _ in range(30):
            c.update(DT)
        c.draw(None, 0, 0)


def test_ch1_contains_new_vocabulary(monkeypatch):
    from delivery.corridor import make_corridor
    c = make_corridor(1)
    els = [e for room in c.rooms for e in room.elements]
    assert any(isinstance(e, Spring) for e in els)
    assert any(isinstance(e, QuestionBlock) for e in els)
    assert any(isinstance(e, BreakableBlock) for e in els)
