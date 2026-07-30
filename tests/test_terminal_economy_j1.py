"""Terminal V2 Phase J.1 — economy regression tests.

The terminal used to lie about money. These pin the honest behaviour:
dual-ledger charges, the 5k/2.5k payout retune, the insufficient-funds
counter-offer, and the hull/stim wiring.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import random
import pygame
import pytest

from terminal.economy import (
    TerminalEconomy, EXPLOIT_PAYOUT, RELEASE_PAYOUT,
    EFFECT_REPAIR_25, EFFECT_REPAIR_45, EFFECT_STIM,
)
from terminal.npcs.base_npc import NPCOutcome


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    pygame.font.init()
    yield


def _econ(credits=9000):
    state = {"cr": credits, "debt": 0, "hull": 0.0, "harm": 5.0}
    econ = TerminalEconomy(
        get_credits=lambda: state["cr"],
        deduct_credits=lambda a: state.__setitem__("cr", state["cr"] - a),
        add_debt=lambda a, l: state.__setitem__("debt", state["debt"] + a),
        repair=lambda a: state.__setitem__("hull", state["hull"] + a),
        grant_harmonica=lambda: state.__setitem__("harm", state["harm"] + 5.0),
    )
    return econ, state


# ── payout constants (retune) ───────────────────────────────────────────────

def test_locked_payout_values():
    assert EXPLOIT_PAYOUT == 5000
    assert RELEASE_PAYOUT == 2500


def test_run_manager_uses_retuned_payouts_not_9000():
    src = open("roguelite/run_manager.py").read()
    assert "bonus = EXPLOIT_PAYOUT" in src
    assert "bonus = RELEASE_PAYOUT" in src
    assert "bonus = 9000" not in src


def test_outcome_banner_drops_the_9000_hardcode():
    src = open("terminal/terminal.py").read()
    assert "9,000 CR" not in src
    assert "TRANSACTION REROUTED" in src


# ── econ adapter ────────────────────────────────────────────────────────────

def test_dual_ledger_charge_moves_both_numbers():
    econ, state = _econ(3000)
    assert econ.charge(2000, dual_ledger=True, label="X") is True
    assert state["cr"] == 1000
    assert state["debt"] == 2000


def test_single_ledger_charge_leaves_debt_untouched():
    econ, state = _econ(3000)
    assert econ.charge(700, dual_ledger=False) is True
    assert state["cr"] == 2300
    assert state["debt"] == 0


def test_insufficient_charge_touches_nothing():
    econ, state = _econ(500)
    assert econ.charge(2000) is False
    assert state["cr"] == 500 and state["debt"] == 0


def test_effects_apply():
    econ, state = _econ()
    econ.apply_effect(EFFECT_REPAIR_25); assert state["hull"] == 25
    econ.apply_effect(EFFECT_REPAIR_45); assert state["hull"] == 70
    econ.apply_effect(EFFECT_STIM);      assert state["harm"] == 10.0
    econ.apply_effect(None);             assert state["hull"] == 70  # no-op


# ── Kress intel / contraband ────────────────────────────────────────────────

def _kress(credits):
    from terminal.npcs.kress import Kress
    return Kress(run_context={"credits": credits, "sector_index": 1})


def test_kress_priced_intel_stages_dual_ledger():
    k = _kress(9000)
    # deterministically pick a priced intel line
    menu = k._intel_menu(1)
    priced = next(l for l in menu if l[1] > 0)
    out, line = k._sell(priced[0], priced[1], effect=None, path="INTEL")
    assert out == NPCOutcome.RELEASE
    txn = k.take_pending_transaction()
    assert txn["amount"] == priced[1]
    assert txn["dual_ledger"] is True
    assert txn["label"] == "KRESS INTEL"


def test_kress_free_tip_charges_nothing():
    k = _kress(9000)
    menu = k._intel_menu(1)
    free = next(l for l in menu if l[1] == 0)
    out, line = k._sell(free[0], free[1], effect=None, path="INTEL")
    assert out == NPCOutcome.RELEASE
    assert k.take_pending_transaction() is None


def test_kress_broke_gives_counter_offer_not_free_intel():
    k = _kress(100)
    out, line = k._sell("x", 8000, effect=EFFECT_REPAIR_25, path="CONTRABAND")
    assert out == NPCOutcome.CONTINUE          # no silent success
    assert k._pending_txn is None              # no charge
    assert "100" in line and "8,000" in line   # counter-offer quotes both


def test_kress_contraband_hull_wires_repair_25():
    k = _kress(20000)
    hull_entry = next(e for e in k._CONTRABAND_MENU if e[2] == EFFECT_REPAIR_25)
    out, _ = k._sell(hull_entry[0], hull_entry[1], effect=hull_entry[2],
                     path="CONTRABAND")
    assert out == NPCOutcome.RELEASE
    assert k.take_pending_transaction()["effect"] == EFFECT_REPAIR_25


def test_kress_contraband_stims_wire_harmonica_charge():
    k = _kress(20000)
    stim_entry = next(e for e in k._CONTRABAND_MENU if e[2] == EFFECT_STIM)
    out, _ = k._sell(stim_entry[0], stim_entry[1], effect=stim_entry[2],
                     path="CONTRABAND")
    assert k.take_pending_transaction()["effect"] == EFFECT_STIM


# ── Mira paid repair (run-credits-only) ─────────────────────────────────────

def _mira(credits):
    from terminal.npcs.mira_voss import MiraVoss
    return MiraVoss(run_context={"credits": credits})


def test_mira_pay_charges_700_run_credits_only():
    m = _mira(5000)
    out, _ = m.respond("here's 700 credits for a patch")
    assert out == NPCOutcome.RELEASE
    txn = m.take_pending_transaction()
    assert txn["amount"] == 700
    assert txn["dual_ledger"] is False   # off-books medic, no meta debt
    assert txn["effect"] == EFFECT_REPAIR_45  # repair rides the txn, not a free pre-charge


def test_mira_broke_offer_gets_counter_not_free_patch():
    m = _mira(300)
    out, line = m.respond("i'll give you 700 credits")
    assert out == NPCOutcome.CONTINUE
    assert m._pending_txn is None
    assert "300" in line


# ── Terminal integration ────────────────────────────────────────────────────

def test_terminal_applies_transaction_and_prints_ledger(monkeypatch):
    from terminal.terminal import Terminal
    econ, state = _econ(9000)
    k = _kress(9000)
    term = Terminal(k, econ=econ)
    term.activate()

    # force the stim contraband entry
    stim = next(e for e in k._CONTRABAND_MENU if e[2] == EFFECT_STIM)
    real_choice = random.choice

    def pick(seq):
        if seq and isinstance(seq[0], tuple) and len(seq[0]) == 3:
            return stim
        return real_choice(seq)
    monkeypatch.setattr(random, "choice", pick)

    term._input = "sell me stims"
    term._submit()

    assert state["cr"] == 6000        # −3000
    assert state["debt"] == 3000      # +3000 (dual ledger)
    assert state["harm"] == 10.0      # +1 harmonica charge
    ledger = [t for spk, t in term._history if spk == "LEDGER"]
    assert ledger and "3,000 cr" in ledger[0] and "harmonica" in ledger[0]


def test_path_hardening_does_not_charge_before_the_win_sticks(monkeypatch):
    """Same paid path across consecutive terminals must not double-bill.

    Concrete trigger: win CONTRABAND once → next Kress terminal has that path
    blocked. Buying stims again stages a charge, path-hardening rewrites the
    RELEASE to CONTINUE, and the old code still applied the pending txn. Retry
    then charged again on the real RELEASE — silent dual-ledger corruption.
    """
    from terminal.terminal import Terminal
    econ, state = _econ(9000)
    k = _kress(9000)
    # Keep NPC wallet view in sync with econ so affordability checks stay honest.
    k._ctx["credits"] = state["cr"]
    term = Terminal(k, blocked_paths=frozenset({"CONTRABAND"}), econ=econ)
    term.activate()

    stim = next(e for e in k._CONTRABAND_MENU if e[2] == EFFECT_STIM)
    real_choice = random.choice

    def pick(seq):
        if seq and isinstance(seq[0], tuple) and len(seq[0]) == 3:
            return stim
        return real_choice(seq)
    monkeypatch.setattr(random, "choice", pick)

    term._input = "sell me stims"
    term._submit()
    assert term.is_done is False
    assert state["cr"] == 9000
    assert state["debt"] == 0
    assert state["harm"] == 5.0
    assert k._pending_txn is None

    # Second push breaks through hardening and charges exactly once.
    k._ctx["credits"] = state["cr"]
    term._input = "sell me stims"
    term._submit()
    assert term.is_done is True
    assert term.outcome == NPCOutcome.RELEASE
    assert state["cr"] == 6000
    assert state["debt"] == 3000
    assert state["harm"] == 10.0


def test_mira_paid_hardening_does_not_grant_free_repair():
    """Hardened Mira PAID must not patch hull before the charge sticks."""
    from terminal.terminal import Terminal
    econ, state = _econ(5000)
    m = _mira(5000)
    term = Terminal(m, blocked_paths=frozenset({"PAID"}), econ=econ)
    term.activate()

    term._input = "here's 700 credits for a patch"
    term._submit()
    assert term.is_done is False
    assert state["cr"] == 5000
    assert state["hull"] == 0.0
    assert m._pending_txn is None

    m._ctx["credits"] = state["cr"]
    term._input = "here's 700 credits for a patch"
    term._submit()
    assert term.is_done is True
    assert term.outcome == NPCOutcome.RELEASE
    assert state["cr"] == 4300
    assert state["hull"] == 45.0
    assert state["debt"] == 0


def test_terminal_without_econ_never_crashes():
    from terminal.terminal import Terminal
    k = _kress(9000)
    k.stage_transaction(2000, dual_ledger=True, label="X")
    term = Terminal(k, econ=None)      # no adapter injected
    term._apply_pending_transaction()  # must be a safe no-op
