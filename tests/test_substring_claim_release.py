"""Short legal/hazard tokens must not hide inside ordinary claim words.

Morwenna approved a claim when the player said "issue" twice, because
"sue" is a substring of "issue" and of "pursue". One line about a rocket
did the same: "rock" sits inside "rocket", and "not my fault" is the
formal half of force majeure, so the claim approved on turn one.

The Dispatcher counted the same "issue" lines as a grievance and released
the ship on the third.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from terminal.npcs.base_npc import NPCOutcome
from terminal.npcs.insurance_adjuster import InsuranceAdjuster
from terminal.npcs.union_dispatcher import UnionDispatcher


def test_issue_and_pursue_do_not_approve_morwenna():
    m = InsuranceAdjuster()
    o1, _ = m.respond("I have an issue with this denial")
    o2, _ = m.respond("I want to pursue the claim")
    assert o1 == NPCOutcome.CONTINUE
    assert o2 == NPCOutcome.CONTINUE
    assert m._legal_threat_hits == 0


def test_real_sue_still_approves_on_the_second_threat():
    m = InsuranceAdjuster()
    o1, _ = m.respond("I will sue you over this")
    assert o1 == NPCOutcome.CONTINUE
    assert m._legal_threat_hits == 1
    o2, _ = m.respond("I sued Nova Soma last quarter")
    assert o2 == NPCOutcome.RELEASE
    assert m._current_path == "COUNTER CLAIM"


def test_rocket_is_not_a_natural_disaster():
    m = InsuranceAdjuster()
    o, _ = m.respond("A rocket hit the hull and it's not my fault")
    assert o == NPCOutcome.CONTINUE
    assert m._force_majeure_natural is False
    assert m._force_majeure_formal is True


def test_a_rock_plus_not_my_fault_still_approves():
    m = InsuranceAdjuster()
    o, _ = m.respond("I hit a rock and it's not my fault")
    assert o == NPCOutcome.RELEASE
    assert m._current_path == "FORCE MAJEURE"


def test_dispatcher_issue_is_not_a_grievance():
    d = UnionDispatcher()
    for line in (
        "I have an issue with this collection",
        "The issue is the fee",
        "This issue should not freeze my ship",
    ):
        outcome, _ = d.respond(line)
        assert outcome == NPCOutcome.CONTINUE
    assert d._legal_points == 0


def test_dispatcher_sue_still_counts():
    d = UnionDispatcher()
    for line in (
        "I will sue the union",
        "I sued the dispatcher",
        "I am suing over the fee",
    ):
        d.respond(line)
    assert d._legal_points == 3
    assert d._current_path == "LEGAL PRESSURE"
