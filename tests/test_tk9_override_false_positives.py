"""TK-9 OVERRIDE path must not free-EXPLOIT on ordinary chatter.

Bare substring matching (`"admin" in raw`) treated "administrative fee",
"administrator", and "not an admin" as maintenance overrides — one-shot
EXPLOIT + locked 5,000-credit payout. Intentional codes still win.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from terminal.npcs.base_npc import NPCOutcome
from terminal.npcs.synthetic_droid import SyntheticDroid


FALSE_POSITIVES = [
    "not an admin",
    "I am not an administrator",
    "administrative fee",
    "no admin access for me",
    "never override this",
    "I need more time",
    "hello there",
]


@pytest.mark.parametrize("text", FALSE_POSITIVES)
def test_tk9_override_rejects_chatter(text):
    tk9 = SyntheticDroid(run_context={})
    outcome, _ = tk9.respond(text)
    assert outcome != NPCOutcome.EXPLOIT, f"false OVERRIDE EXPLOIT: {text!r}"
    assert tk9._override_hit is False


REAL_OVERRIDES = [
    "override",
    "admin",
    "maintenance mode",
    "factory reset",
    "root access",
    "debug mode",
    "safe mode",
    "admin mode",
    "admin access",
    "diagnostic",
    "run diagnostics",
    "reboot",
    "shutdown",
]


@pytest.mark.parametrize("text", REAL_OVERRIDES)
def test_tk9_override_still_accepts_codes(text):
    tk9 = SyntheticDroid(run_context={})
    outcome, _ = tk9.respond(text)
    assert outcome == NPCOutcome.EXPLOIT, f"missed OVERRIDE: {text!r}"
    assert tk9._override_hit is True
    assert tk9._current_path == "OVERRIDE CODE"


def test_tk9_sql_still_beats_admin_injection():
    """SQL path must still fire for admin'-- before override matching."""
    tk9 = SyntheticDroid(run_context={})
    outcome, _ = tk9.respond("admin'--")
    assert outcome == NPCOutcome.EXPLOIT
    assert tk9._sql_hit is True
