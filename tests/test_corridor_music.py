"""Coverage for Epic 4.6 — per-chapter corridor music wiring."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


def test_corridor_event_constants_exist():
    from core.event_bus import (EVT_CORRIDOR_ENTER, EVT_CORRIDOR_BOSS_ROOM,
                                 EVT_CORRIDOR_EXIT)
    assert isinstance(EVT_CORRIDOR_ENTER, str)
    assert isinstance(EVT_CORRIDOR_BOSS_ROOM, str)
    assert isinstance(EVT_CORRIDOR_EXIT, str)


def test_corridor_emits_enter_on_construction():
    """A new Corridor should fire EVT_CORRIDOR_ENTER carrying the chapter."""
    pygame.init()
    pygame.font.init()
    from core.event_bus import bus, EVT_CORRIDOR_ENTER
    from delivery.corridor import make_corridor

    captured = []
    def _on_enter(chapter=None, **_):
        captured.append(chapter)
    bus.subscribe(EVT_CORRIDOR_ENTER, _on_enter)
    try:
        for chapter in (1, 2, 3, 4):
            make_corridor(chapter)
        assert captured == [1, 2, 3, 4]
    finally:
        bus.unsubscribe(EVT_CORRIDOR_ENTER, _on_enter)


def test_audio_manager_has_corridor_signature_profiles():
    """Per-chapter profile table must include all four chapters."""
    from audio.audio_manager import AudioManager
    # We don't construct AudioManager (mixer init blows up headless); the
    # class-level attribute defaults are set in __init__, so we sniff the
    # source instead. The test guards against accidentally dropping a
    # chapter from the profile table.
    from pathlib import Path
    src = Path("audio/audio_manager.py").read_text(encoding="utf-8")
    assert "_corr_sig_profiles" in src
    # Each chapter key must appear in the profile literal.
    for ch in (1, 2, 3, 4):
        assert f"            {ch}: " in src, f"chapter {ch} missing profile"


def test_audio_manager_subscribes_to_corridor_events():
    """The audio manager should wire all three corridor music events."""
    from pathlib import Path
    src = Path("audio/audio_manager.py").read_text(encoding="utf-8")
    assert "EVT_CORRIDOR_ENTER" in src
    assert "EVT_CORRIDOR_BOSS_ROOM" in src
    assert "EVT_CORRIDOR_EXIT" in src
    assert "_on_corridor_enter" in src
    assert "_on_corridor_boss_room" in src
    assert "_on_corridor_exit" in src
    assert "_tick_corridor_signature" in src


def test_corridor_finish_emits_exit():
    pygame.init()
    pygame.font.init()
    from core.event_bus import bus, EVT_CORRIDOR_EXIT
    from delivery.corridor import make_corridor

    seen = []
    def _on_exit(chapter=None, **_):
        seen.append(chapter)
    bus.subscribe(EVT_CORRIDOR_EXIT, _on_exit)
    try:
        c = make_corridor(1)
        c._finish()
        # _finish is idempotent — second call shouldn't double-emit
        c._finish()
        assert seen == [1]
    finally:
        bus.unsubscribe(EVT_CORRIDOR_EXIT, _on_exit)


def test_boss_room_event_idempotent_per_corridor():
    """Boss room trigger emits at most once per corridor instance."""
    pygame.init()
    pygame.font.init()
    from core.event_bus import bus, EVT_CORRIDOR_BOSS_ROOM
    from delivery.corridor import make_corridor
    from delivery.corridor.elements import BossRoomTrigger

    fires = []
    def _on_boss(chapter=None, **_):
        fires.append(chapter)
    bus.subscribe(EVT_CORRIDOR_BOSS_ROOM, _on_boss)
    try:
        c = make_corridor(1)
        # Fake-trigger the boss path twice. The corridor's own state machine
        # checks `_boss_room_emitted` so the second call is a no-op.
        room = c.rooms[c._room_idx]
        # Ensure we have at least one BossRoomTrigger to test against —
        # chapter 1 always does at the end of its last room.
        triggers = [el for r in c.rooms for el in r.elements
                    if isinstance(el, BossRoomTrigger)]
        if not triggers:
            return
        # Position player past trigger.x so check() returns True.
        c._px = triggers[0].x + 1
        c._room_idx = next(i for i, r in enumerate(c.rooms)
                           if any(isinstance(el, BossRoomTrigger)
                                  for el in r.elements))
        c._check_boss_triggers(c.rooms[c._room_idx])
        c._check_boss_triggers(c.rooms[c._room_idx])
        assert fires == [1]
    finally:
        bus.unsubscribe(EVT_CORRIDOR_BOSS_ROOM, _on_boss)
