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
