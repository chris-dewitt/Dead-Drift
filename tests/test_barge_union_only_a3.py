"""Aliveness A.3 — repo barges carry Union personnel only.

Design lock (Chris, May 2026): only Local 404 / Union operates repo
barges. Pirates, TK-9 / Synthetic droids, and Morwenna / Insurance
Adjuster used to piggyback the barge relay; they no longer do. They
have their own comm channels (terminal-only / flight-events comms).

This test pins the contract and guards against accidental regression."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


_BANNED_BARGE_NPCS = {"pirate", "synthetic_droid", "insurance_adjuster"}
_ALLOWED_BARGE_NPCS = {"gary", "idealist_rep", "corrupt_rep",
                        "union_dispatcher"}


def test_barge_intercept_pool_contains_no_non_union_npcs():
    """`open_barge_terminal` source must never put a non-Union NPC into
    the pool."""
    from pathlib import Path
    import re
    src = Path("roguelite/run_manager.py").read_text(encoding="utf-8")
    fn_start = src.find("def open_barge_terminal")
    assert fn_start != -1
    # End at the next `def ` after a newline.
    after = src[fn_start + 1:]
    fn_end = after.find("\n    def ")
    body = src[fn_start: fn_start + 1 + fn_end] if fn_end != -1 else src[fn_start:]
    for banned in _BANNED_BARGE_NPCS:
        assert banned not in body, (
            f"banned NPC {banned!r} still referenced inside "
            f"open_barge_terminal  Union-only design lock violated"
        )


def test_barge_intercept_pool_only_contains_allowed_union_npcs():
    """Every NPC type string in `open_barge_terminal` must be a Union role."""
    from pathlib import Path
    import re
    src = Path("roguelite/run_manager.py").read_text(encoding="utf-8")
    fn_start = src.find("def open_barge_terminal")
    after = src[fn_start + 1:]
    fn_end = after.find("\n    def ")
    body = src[fn_start: fn_start + 1 + fn_end] if fn_end != -1 else src[fn_start:]
    # Find every quoted NPC-type-looking identifier in the function body.
    candidates = set(re.findall(r'"([a-z_]+)"', body))
    # Ignore obvious non-NPC strings (lines / framing keys are quoted too).
    npc_like = {c for c in candidates
                if c in _ALLOWED_BARGE_NPCS or c in _BANNED_BARGE_NPCS}
    assert npc_like.issubset(_ALLOWED_BARGE_NPCS), (
        f"non-Union NPC slipped back into open_barge_terminal: "
        f"{npc_like - _ALLOWED_BARGE_NPCS}"
    )


def test_simulated_pool_returns_only_union_keys():
    """Headless probe: invoke the barge-terminal NPC selection 200 times
    and verify every result is Union personnel.

    We bypass the full RunManager.__init__ (which boots audio) and call
    open_barge_terminal directly with a stub barge."""
    from types import SimpleNamespace
    from roguelite.run_manager import RunManager
    from roguelite.meta_progression import MetaProgression
    import tempfile
    import pathlib
    import random as rnd

    seen: set[str] = set()
    with tempfile.TemporaryDirectory() as tmp:
        meta = MetaProgression(save_path=pathlib.Path(tmp) / "meta.json")
        rm = RunManager.__new__(RunManager)
        # Minimal scaffold the function needs.
        rm.meta = meta
        rm._barges = []
        rm._intercepting_barge = None
        rm._last_winning_path = ""
        rm._vault = None
        rm._sector_index = 0
        rm._last_voice_char_t = -10.0
        rm._t = 0.0
        rm._active_terminal = None
        rm._pending_terminal = None
        rm._terminal_arm_t = -1.0

        def _open_terminal(npc_type, **kwargs):
            seen.add(npc_type)
            return None
        rm.open_terminal = _open_terminal  # patch the dispatch
        rm._build_run_context = lambda: {}

        for sector_idx in range(0, 5):
            rm._sector_index = sector_idx
            for _ in range(40):
                rnd.seed(sector_idx * 100 + _)
                rm.open_barge_terminal(SimpleNamespace())

    assert seen, "no NPC types were ever selected"
    leak = seen - _ALLOWED_BARGE_NPCS
    assert not leak, (
        f"Union-only design lock violated  saw non-Union NPC(s) on the "
        f"barge channel: {leak}"
    )
