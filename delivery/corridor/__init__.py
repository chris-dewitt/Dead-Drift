"""
delivery.corridor — chapter-based delivery corridor system.

Public API:
    make_corridor(chapter: int, hardcore: bool = False, meta=None,
                  cargo=None, force_time_pressure: bool = False) -> Corridor
"""
from __future__ import annotations
from delivery.corridor.base import Corridor
from delivery.corridor.elements import Checkpoint


def make_corridor(chapter: int, hardcore: bool = False,
                  meta=None, cargo=None,
                  force_time_pressure: bool = False) -> Corridor:
    """Factory: build a Corridor for the given chapter (1-6).

    ``cargo`` is forwarded so Aliveness G.9 mutators can activate.
    ``force_time_pressure`` (G.10) overrides the cargo mutator with a timer.
    """
    if chapter == 1:
        from delivery.corridor.chapter1_archive import build
    elif chapter == 2:
        from delivery.corridor.chapter2_shrooms import build
    elif chapter == 3:
        from delivery.corridor.chapter3_paperwork import build
    elif chapter == 4:
        from delivery.corridor.chapter4_vip import build
    elif chapter == 5:
        from delivery.corridor.chapter5_edge import build
    elif chapter == 6:
        from delivery.corridor.chapter6_compliance import build
    else:
        from delivery.corridor.chapter1_archive import build
    if chapter == 1:
        corridor = build(meta=meta)
    else:
        corridor = build()
    # Aliveness G.9 / G.10 — wire cargo mutator after build
    from delivery.corridor.mutators import get_corridor_mutator
    corridor._mutator = get_corridor_mutator(cargo, force_time_pressure=force_time_pressure)
    if hardcore:
        for room in corridor.rooms:
            room.elements = [el for el in room.elements
                             if not isinstance(el, Checkpoint)]
        corridor.hardcore = True
    else:
        corridor.hardcore = False
    return corridor


__all__ = ["make_corridor", "Corridor"]
