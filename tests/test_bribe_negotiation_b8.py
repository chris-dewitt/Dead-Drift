"""Aliveness B.8  bribe negotiation surfaces NPC floor on low offers.

Plan contract:
  Turn 1  Bribe verb only. NPC asks for a figure.
  Turn 2  Amount mentioned. NPC compares to their personal floor.
  Turn 3a  Floor met  RELEASE.
  Turn 3b  Below floor  NPC names the floor (counter-offer)."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame


def test_gary_counter_offers_with_floor_on_too_low_bribe():
    """Gary's floor is 3000 cr. A second-attempt offer of 500 must name
    the floor explicitly so the player knows what to pay."""
    pygame.init()
    pygame.font.init()
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    gary = make_npc("gary", run_context={})
    # Turn 1  bribe verb only, no figure.
    out1, _line1 = gary.respond("How much would a bribe take?")
    assert out1 == NPCOutcome.CONTINUE
    # Turn 2  too-low amount.
    out2, line2 = gary.respond("I can offer 500 credits, mate.")
    assert out2 == NPCOutcome.CONTINUE
    # Counter must name the floor.
    assert "3000" in line2 or "three thousand" in line2.lower(), \
        f"Gary did not surface his 3000 cr floor: {line2!r}"


def test_felix_counter_offers_with_floor_on_too_low_bribe():
    """Felix's broker floor is 800 cr. Offers below should surface 800."""
    pygame.init()
    pygame.font.init()
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    felix = make_npc("nervous_fence", run_context={})
    out, line = felix.respond("Here's 200 credits for safe passage.")
    assert out == NPCOutcome.CONTINUE
    assert "800" in line, \
        f"Felix did not surface his 800 cr floor: {line!r}"


def test_holt_counter_offers_with_floor_on_too_low_bribe():
    """Holt's documentation processing fee floor is 600 cr."""
    pygame.init()
    pygame.font.init()
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    holt = make_npc("cargo_inspector", run_context={})
    out, line = holt.respond("I'll cover the fee. 200 credits.")
    assert out == NPCOutcome.CONTINUE
    assert "600" in line, \
        f"Holt did not surface his 600 cr floor: {line!r}"


def test_meeting_floor_releases_npc():
    """Once the floor is met, the negotiation closes with RELEASE."""
    pygame.init()
    pygame.font.init()
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    felix = make_npc("nervous_fence", run_context={})
    out, _line = felix.respond("Take 1000 credits and clear my route.")
    assert out == NPCOutcome.RELEASE


def test_weights_and_serials_are_not_bribes():
    """A nearby number is not an offer. Holt bills it as a documentation
    fee, Felix and Dray pocket it, and Mira spends 700 run credits on a
    patch the player never bought — then the terminal closes."""
    pygame.init()
    pygame.font.init()
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    ordinary = (
        "the crate weighs 1200 kilos",
        "about 800 kilos of spare parts",
        "serial number 4120",
        "I've been waiting 600 seconds",
    )
    for line in ordinary:
        holt = make_npc("cargo_inspector")
        out, _ = holt.respond(line)
        assert out != NPCOutcome.RELEASE, line
        assert holt.bribe_cost() == 0
        assert not (holt._current_path or "").startswith("BRIBE")

        felix = make_npc("nervous_fence")
        out, _ = felix.respond(line)
        assert felix.bribe_cost() == 0, line
        assert not (felix._current_path or "").startswith("BRIBE")

        dray = make_npc("dray")
        # "crate" contains the snitch token "rat", which is a different gate.
        if "crate" not in line:
            out, _ = dray.respond(line)
            assert dray.bribe_cost() == 0, line
            assert not (dray._current_path or "").startswith("BRIBE")

    mira = make_npc("mira_voss", run_context={"credits": 5000})
    out, _ = mira.respond("the crack is 800 millimeters")
    assert out != NPCOutcome.RELEASE
    assert mira.take_pending_transaction() is None

    holt_paid = make_npc("cargo_inspector")
    assert holt_paid.respond("600")[0] == NPCOutcome.RELEASE
    assert holt_paid.bribe_cost() == 600

    felix_paid = make_npc("nervous_fence")
    assert felix_paid.respond("800")[0] == NPCOutcome.RELEASE
    assert felix_paid.bribe_cost() == 800

    dray_paid = make_npc("dray")
    assert dray_paid.respond("here's 500 credits")[0] == NPCOutcome.RELEASE
    assert dray_paid.bribe_cost() == 500

    mira_paid = make_npc("mira_voss", run_context={"credits": 5000})
    assert mira_paid.respond("here's 700 credits for a patch")[0] == NPCOutcome.RELEASE
    txn = mira_paid.take_pending_transaction()
    assert txn is not None and txn["amount"] == 700


def test_low_bribe_keeps_dossier_label_generic_until_amount_clears_floor():
    """Below-floor turn keeps `_current_path` at the generic `BRIBE` so
    the chip strip doesn't show a misleading paid label."""
    pygame.init()
    pygame.font.init()
    from terminal.npc_logic import make_npc

    holt = make_npc("cargo_inspector", run_context={})
    holt.respond("I can offer 200 credits.")
    assert holt._current_path == "BRIBE"
    # Floor met  label switches to the standardised paid label.
    holt.respond("Fine. 800 credits.")
    assert holt._current_path.startswith("BRIBE [")
    assert "cr]" in holt._current_path
