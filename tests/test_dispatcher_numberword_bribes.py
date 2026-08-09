"""Regression: Dispatcher bare number-words must not auto-bribe.

`_BIG_BRIBES` used to list "twenty" / "thirty" / "fifty", and the amount
gate accepted any parsed.amount >= 10000. Combined with common bribe-intent
words (deal/offer/compensate) and extract_credit_amount's val>=5 → *1000
heuristic, ordinary dialogue like "deal for twenty minutes" RELEASEd and
dual-ledger charged 20k–50k.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from terminal.npcs.base_npc import NPCOutcome
from terminal.npcs.union_dispatcher import UnionDispatcher


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    pygame.font.init()
    yield


@pytest.mark.parametrize("text", [
    "want to make a deal for twenty minutes of your time?",
    "let's make a deal in thirty seconds",
    "deal - fifty percent off?",
    "I can offer fifty",
    "compensate me - I lost fifty already",
    "I have a deal involving twenty forms",
])
def test_bare_numberwords_do_not_accept_dispatcher_bribe(text):
    d = UnionDispatcher(run_context={"credits": 100_000})
    out, _line = d.respond(text)
    assert d.bribe_cost() == 0, (
        f"{text!r} charged bribe_cost={d.bribe_cost()} via path={d._current_path!r}"
    )
    assert "BRIBE [" not in (d._current_path or "").upper()
    # Bribe-intent chatter without a real figure should stay on the line
    # (or take an unrelated free path — never a paid BRIBE close).
    assert out in (NPCOutcome.CONTINUE, NPCOutcome.RELEASE)
    if out == NPCOutcome.RELEASE:
        assert "BRIBE" not in (d._current_path or "").upper()


@pytest.mark.parametrize("text,expected", [
    ("I can bribe you 10000 credits", 10000),
    ("bribe 20k", 20000),
    ("offer twenty thousand credits as a bribe", 20000),
    ("pay thirty thousand credits bribe", 30000),
    ("transfer fifty thousand credits bribe", 50000),
])
def test_explicit_large_bribes_still_charge(text, expected):
    d = UnionDispatcher(run_context={"credits": 100_000})
    out, _line = d.respond(text)
    assert out == NPCOutcome.RELEASE
    assert d.bribe_cost() == expected
    assert "BRIBE" in (d._current_path or "").upper()
