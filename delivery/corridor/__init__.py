"""
delivery.corridor — chapter-based delivery corridor system.

Public API:
    make_corridor(chapter: int) -> Corridor
"""
from __future__ import annotations
from delivery.corridor.base import Corridor


def make_corridor(chapter: int) -> Corridor:
    """Factory: build a Corridor for the given chapter (1-4)."""
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
    return build()


__all__ = ["make_corridor", "Corridor"]
