"""Scan-chip / evaluate keyword-sync guard.

The live scan strip (`_SCAN_VOCAB`) and each NPC's evaluate keyword lists were
maintained separately and drifted: a player would type the EXACT word the strip
*highlighted as good*, and nothing would happen — the NPC just gave generic
filler and lost patience. This guard drives the real Terminal and asserts that
every scan-vocab keyword produces a VISIBLE reaction (an NPC line different from
generic filler, a state/path change, a system nudge, a mode switch, or a
terminal outcome). If a future edit re-introduces a dead chip, this fails and
names the exact NPC + word.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import random
import pytest
import pygame

from terminal.terminal import Terminal, _SCAN_VOCAB
from terminal.npc_portraits import _NAME_TO_KEY
from terminal.npc_logic import make_npc


@pytest.fixture(autouse=True, scope="module")
def _pygame():
    pygame.init()
    pygame.font.init()
    yield


_CONTROL = "zxqwvblorknub"   # a nonsense string: whatever generic filler it hits


def _mk(key):
    try:
        return make_npc(key, run_context={"credits": 0})
    except TypeError:
        return make_npc(key)


def _react(key, word):
    """Drive one submit and return (visible non-echo lines, outcome, path)."""
    npc = _mk(key)
    term = Terminal(npc, econ=None)
    term.activate()
    base = len(term._history)
    random.seed(0)               # deterministic filler so same-branch => same text
    term._input = word
    term._submit()
    lines = tuple((spk, txt) for spk, txt in term._history[base:]
                  if spk not in ("YOU", "MUTTER"))
    return lines, term.outcome, getattr(npc, "_current_path", "")


# One case per (npc, keyword) with a resolvable portrait key.
_CASES = [
    (disp, key, kw)
    for disp, vocab in _SCAN_VOCAB.items()
    if (key := _NAME_TO_KEY.get(disp))
    for kw in vocab
]


@pytest.mark.parametrize("disp,key,kw", _CASES, ids=lambda v: str(v))
def test_every_scan_keyword_gets_a_reaction(disp, key, kw):
    ctrl_lines, ctrl_out, _ = _react(key, _CONTROL)
    kw_lines, kw_out, kw_path = _react(key, kw)
    reacted = (kw_lines != ctrl_lines) or (kw_out != ctrl_out) or bool(kw_path)
    assert reacted, (
        f"{disp}: typing {kw!r} lights the scan chip "
        f"{_SCAN_VOCAB[disp][kw]!r} but produces the same generic filler as a "
        f"nonsense word — dead scan/eval desync. Add {kw!r} to the NPC's "
        f"evaluate keywords, give it a reaction, or drop it from _SCAN_VOCAB."
    )


def test_audit_covers_the_whole_roster():
    # Guard the guard: make sure we're actually exercising a real corpus.
    assert len(_CASES) > 250
