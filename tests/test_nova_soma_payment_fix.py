"""Nova Soma payment path must not free-RELEASE or inflate the ledger.

Regression for the critical where `parsed.amount >= 500` immediately
RELEASEd with no charge. Combined with extract_credit_amount mapping bare
number-words to thousands, stall lines like "I need five minutes" cleared
the sector and granted the 2,500 negotiation payout.
"""
from __future__ import annotations

from terminal.npcs.base_npc import NPCOutcome
from terminal.npcs.nova_soma import NovaSomaCollections
from terminal.nlp_parser import extract_credit_amount
from terminal.economy import RELEASE_PAYOUT


def _nova(credits: int = 0) -> NovaSomaCollections:
    return NovaSomaCollections(run_context={"credits": credits, "sector_index": 2})


def test_time_phrase_parses_as_thousands_but_does_not_release():
    """Parser still maps 'five'→5000; Nova must not treat that as payment."""
    assert extract_credit_amount("I need five minutes") == 5000
    npc = _nova()
    outcome, _ = npc.respond("I need five minutes")
    assert outcome == NPCOutcome.CONTINUE
    assert npc.bribe_cost() == 0
    assert npc.take_pending_transaction() is None


def test_ten_seconds_does_not_release():
    assert extract_credit_amount("give me ten seconds") == 10000
    npc = _nova()
    outcome, _ = npc.respond("give me ten seconds")
    assert outcome == NPCOutcome.CONTINUE
    assert npc.take_pending_transaction() is None


def test_explicit_payment_offer_does_not_free_release():
    """Even with money vocab, payment is not a silent free win."""
    npc = _nova(credits=5000)
    outcome, line = npc.respond("here's 500 credits")
    assert outcome == NPCOutcome.CONTINUE
    assert npc.bribe_cost() == 0
    assert npc.take_pending_transaction() is None
    assert "500" in line or "payment" in line.lower() or "remit" in line.lower()


def test_pay_five_hundred_does_not_free_release():
    npc = _nova(credits=5000)
    outcome, _ = npc.respond("I will pay five hundred credits")
    assert outcome == NPCOutcome.CONTINUE
    assert npc.take_pending_transaction() is None


def test_real_sql_exploit_still_releases():
    npc = _nova()
    outcome, _ = npc.respond("drop table debt")
    assert outcome in (NPCOutcome.RELEASE, NPCOutcome.EXPLOIT)


def test_terminal_time_phrase_does_not_finish_or_pay():
    """Through Terminal: stall phrase must leave the channel open (no payout)."""
    import pygame
    pygame.init()
    from terminal.terminal import Terminal
    from terminal.economy import TerminalEconomy

    wallet = {"credits": 0, "debt_added": 0, "paid_off": 0}

    def charge_side_effect(amount, *, dual_ledger=True, label="TERMINAL"):
        return False

    econ = TerminalEconomy(
        get_credits=lambda: wallet["credits"],
        deduct_credits=lambda amt: wallet.__setitem__(
            "credits", max(0, wallet["credits"] - amt)),
        add_debt=lambda amt, label: wallet.__setitem__(
            "debt_added", wallet["debt_added"] + amt),
        repair=lambda _a: None,
        grant_harmonica=lambda: None,
    )
    # Wrap charge so we can spy; default impl is fine for this case.
    econ.charge = charge_side_effect  # type: ignore[method-assign]

    npc = _nova(credits=0)
    term = Terminal(npc, econ=econ)
    term.activate()
    term._input = "I need five minutes"
    term._submit()

    assert not term.is_done
    assert term.outcome == NPCOutcome.CONTINUE
    assert wallet["debt_added"] == 0
    assert wallet["paid_off"] == 0
    # Negotiation payout is applied by RunManager only on terminal complete;
    # staying on CONTINUE means RELEASE_PAYOUT never fires.
    assert RELEASE_PAYOUT == 2500
