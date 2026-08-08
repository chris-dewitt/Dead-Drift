"""Basic tests for NLP parser and terminal NPC logic (no pygame display required)."""
from __future__ import annotations

import os
import random

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture(autouse=True)
def _fixed_rng(monkeypatch: pytest.MonkeyPatch):
    """Deterministic toll RNG in tests."""
    monkeypatch.setattr(random, "random", lambda: 0.99)  # favour non-random releases off
    monkeypatch.setattr(random, "choice", lambda seq: seq[0])


def test_extract_credit_skips_local_404():
    from terminal.nlp_parser import extract_credit_amount

    assert extract_credit_amount("local 404 stole my quota") is None
    assert extract_credit_amount("pay 1500 credits") == 1500


def test_extract_credit_comma_and_decimal_k():
    """Comma groups and decimal-k must not silently under/over-parse."""
    from terminal.nlp_parser import extract_credit_amount

    assert extract_credit_amount("I will pay 1,500 credits") == 1500
    assert extract_credit_amount("payment of 1,500 credits") == 1500
    assert extract_credit_amount("transfer 2,500 credits") == 2500
    assert extract_credit_amount("pay 10,000 credits") == 10000
    assert extract_credit_amount("pay 1.5k credits") == 1500
    assert extract_credit_amount("pay 12.5k credits") == 12500
    assert extract_credit_amount("pay 5k credits") == 5000


def test_toll_comma_amount_charges_full_toll():
    """'1,500' must not fall into the 40% LOW_BRIBE (500cr) path."""
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    t = make_npc("toll_authority")
    o, _ = t.respond("I will pay 1,500 credits")
    assert o == NPCOutcome.RELEASE
    assert t._paid
    assert t.bribe_cost() == 1500


def test_toll_decimal_k_charges_parsed_amount():
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    t = make_npc("toll_authority")
    o, _ = t.respond("pay 1.5k credits")
    assert o == NPCOutcome.RELEASE
    assert t._paid
    assert t.bribe_cost() == 1500


def test_gary_sympathy_two_turns():
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    g = make_npc("gary")
    o1, _ = g.respond("please my family is starving")
    assert o1 == NPCOutcome.CONTINUE
    assert g._sympathy_turns == 1
    o2, _ = g.respond("I am desperate, sorry about this")
    assert o2 == NPCOutcome.RELEASE
    assert g._sympathy_turns >= 2


def test_gary_bribe_minimum_on_persistent_path():
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    g = make_npc("gary")
    g.disposition = 3
    g._bribe_attempts = 2
    o, _ = g.respond("I could pay something maybe")
    g._bribe_attempts = 3
    g.disposition = 3
    o, _ = g.respond("fine take some credits")
    if o == NPCOutcome.RELEASE:
        assert g.bribe_cost() >= 3000


def test_toll_pay_requires_amount_not_bare_pay():
    from terminal.nlp_parser import NLPParser
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    t = make_npc("toll_authority")
    p = NLPParser()
    # Bare "pay" without amount should NOT auto-release
    o, _ = t.respond("I want to pay")
    assert o == NPCOutcome.CONTINUE
    assert not t._paid

    t2 = make_npc("toll_authority")
    o2, _ = t2.respond("I will pay fifteen hundred credits")
    assert o2 == NPCOutcome.RELEASE
    assert t2.bribe_cost() == 1500


def test_toll_path_progress():
    from terminal.npc_logic import make_npc

    t = make_npc("toll_authority")
    paths = dict((n, (c, m)) for n, c, m in t.get_path_progress())
    assert "PAY 1500+" in paths
    assert "UNION GRIPE" in paths
    assert paths["UNION GRIPE"][1] == 2


def test_corridor_update_smoke():
    import pygame

    pygame.init()
    from delivery.corridor import make_corridor

    c = make_corridor(chapter=1)
    for _ in range(180):
        c.update(1 / 60)
    assert c is not None
