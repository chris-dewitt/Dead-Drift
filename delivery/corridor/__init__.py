"""
delivery.corridor — chapter-based delivery corridor system.

Public API:
    make_corridor(chapter: int, hardcore: bool = False) -> Corridor
"""
from __future__ import annotations
from delivery.corridor.base import Corridor
from delivery.corridor.elements import Checkpoint


def make_corridor(chapter: int, hardcore: bool = False) -> Corridor:
    """Factory: build a Corridor for the given chapter (1-4).

    `hardcore=True` (Epic 8.4) strips the optional mid-room
    `Checkpoint` elements so the player only respawns at the start
    of each room.
    """
    if chapter == 1:
        from delivery.corridor.chapter1_archive import build
    elif chapter == 2:
        from delivery.corridor.chapter2_shrooms import build
    elif chapter == 3:
        from delivery.corridor.chapter3_paperwork import build
    elif chapter == 4:
        from delivery.corridor.chapter4_vip import build
    else:
        from delivery.corridor.chapter1_archive import build
    corridor = build()
    if hardcore:
        for room in corridor.rooms:
            room.elements = [el for el in room.elements
                             if not isinstance(el, Checkpoint)]
        corridor.hardcore = True
    else:
        corridor.hardcore = False
    return corridor


__all__ = ["make_corridor", "Corridor"]
