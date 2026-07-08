"""Delivery v2 Phase I.3b — level content regression tests.

Pins the room expansion: every chapter is 6+ rooms, checkpointed,
stocked with the new vocabulary, and — the load-bearing test — fully
traversable end-to-end by a scripted runner. Also pins the ch3
one-way-wall fix (they were floor-to-ceiling and soft-locked the
chapter) and the ch6 chase room placement.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from delivery.corridor.base import FLOOR_Y
from delivery.corridor.elements import (
    Spring, ConveyorBelt, BreakableBlock, QuestionBlock, WarpPipe,
    TimedLift, Checkpoint, Collectible, OneWayWall,
)

DT = 1.0 / 60.0


class _Keys:
    def __init__(self, held=()):
        self._held = set(held)

    def __getitem__(self, k):
        return k in self._held


def _ev(key, uni=" "):
    return pygame.event.Event(pygame.KEYDOWN, {"key": key, "unicode": uni})


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    pygame.font.init()
    yield


def _run_bot(corridor, max_s: float = 240.0) -> bool:
    """Sprint + full-jump runner: holds forward (inversion-aware),
    full-holds every jump, ESCs out of dialogs. Returns completion.
    Restores pygame.key.get_pressed so the patch never leaks into
    other tests."""
    original_get_pressed = pygame.key.get_pressed
    frames = 0
    jump_t = 0
    hold_jump = 0
    try:
        while not corridor._done and frames < 60 * max_s:
            frames += 1
            jump_t += 1
            held = {pygame.K_LSHIFT,
                    pygame.K_a if corridor._invert_t > 0 else pygame.K_d}
            if hold_jump > 0:
                hold_jump -= 1
                held.add(pygame.K_SPACE)
            pygame.key.get_pressed = (lambda h=frozenset(held): _Keys(h))
            if corridor._dialog is not None:
                corridor.handle_key(_ev(pygame.K_ESCAPE, "\x1b"))
            elif jump_t >= 30:
                jump_t = 0
                hold_jump = 24
                corridor.handle_key(_ev(pygame.K_SPACE))
            corridor.update(DT)
    finally:
        pygame.key.get_pressed = original_get_pressed
    return corridor._done


NEW_KINDS = (Spring, ConveyorBelt, BreakableBlock, QuestionBlock,
             WarpPipe, TimedLift)


@pytest.mark.parametrize("ch", [1, 2, 3, 4, 5, 6])
def test_chapter_structure_and_traversal(ch, monkeypatch):
    from delivery.corridor import make_corridor
    c = make_corridor(ch)

    assert len(c.rooms) >= 6, f"ch{ch}: {len(c.rooms)} rooms (< 6)"

    cps = sum(1 for r in c.rooms for e in r.elements
              if isinstance(e, Checkpoint))
    assert cps >= 2, f"ch{ch}: only {cps} checkpoints"

    kinds = {type(e) for r in c.rooms for e in r.elements}
    present = [k for k in NEW_KINDS if k in kinds]
    assert len(present) >= 3, \
        f"ch{ch}: only {len(present)} new element kinds present"

    chips = sum(1 for r in c.rooms for e in r.elements
                if isinstance(e, Collectible))
    assert chips >= 30, f"ch{ch}: only {chips} chips placed"

    assert c._par_total >= 120.0, f"ch{ch}: par {c._par_total:.0f}s too short"
    assert c.max_hits == 5, "6+ room corridors get the long-run hit budget"

    assert _run_bot(c), \
        f"ch{ch} not traversable — stuck room {c._room_idx} px {c._px:.0f}"


def test_ch6_chase_room_is_penultimate(monkeypatch):
    from delivery.corridor import make_corridor
    c = make_corridor(6)
    scroll_rooms = [i for i, r in enumerate(c.rooms) if r.auto_scroll > 0]
    assert scroll_rooms == [len(c.rooms) - 2], \
        f"chase must be exactly the penultimate room, got {scroll_rooms}"


def test_no_other_chapter_has_auto_scroll(monkeypatch):
    from delivery.corridor import make_corridor
    for ch in (1, 2, 3, 4, 5):
        c = make_corridor(ch)
        assert all(r.auto_scroll == 0 for r in c.rooms), \
            f"ch{ch} has an unexpected auto-scroll room"


def test_ch3_oneway_walls_are_hoppable(monkeypatch):
    """Regression: the A.6 walls spanned floor-to-ceiling, which made
    ch3 impossible to cross (no jump could clear them). Cubicle
    partitions must leave headroom for a full jump (~109px rise)."""
    from delivery.corridor import make_corridor
    c = make_corridor(3)
    walls = [e for r in c.rooms for e in r.elements
             if isinstance(e, OneWayWall)]
    assert walls, "ch3 should still have its cubicle zigzag"
    for w in walls:
        assert w.y_top >= FLOOR_Y - 110, \
            f"OneWayWall at x={w.x} y_top={w.y_top} is not jump-clearable"


def test_boss_finales_unchanged(monkeypatch):
    """The originals keep their finale: last room of ch1-4 still has
    its BossRoomActor (the room expansion inserts BEFORE the boss)."""
    from delivery.corridor import make_corridor
    from delivery.corridor.elements import BossRoomActor
    for ch in (1, 2, 3, 4):
        c = make_corridor(ch)
        assert any(isinstance(e, BossRoomActor)
                   for e in c.rooms[-1].elements), f"ch{ch} lost its boss"


def test_recipes_produce_valid_rooms(monkeypatch):
    from delivery.corridor.rooms_v2 import (
        spring_yard, conveyor_gallery, crate_warren, lift_shaft,
        pipe_junction, chase_sweep)
    pal = {}
    for recipe in (spring_yard, conveyor_gallery, crate_warren,
                   lift_shaft, pipe_junction):
        room = recipe(pal, "TEST")
        assert room.length >= 1000 and room.elements and room.name == "TEST"
        assert room.auto_scroll == 0
    chase = chase_sweep(pal, "SWEEP", speed=150.0)
    assert chase.auto_scroll == 150.0
