from __future__ import annotations

from types import SimpleNamespace

import pytest


NPC_TYPES = [
    "gary",
    "synthetic_droid",
    "union_dispatcher",
    "kress",
    "insurance_adjuster",
    "sandra",
    "pirate",
    "underground_dj",
    "toll_authority",
    "nervous_fence",
    "cargo_inspector",
    "dray",
    "nova_soma_collections",
    "mira_voss",
    "idealist_rep",
    "corrupt_rep",
]

CARGO_CONTEXTS = [
    {
        "cargo_type": "AcousticArchive",
        "cargo_name": "CONTRABAND ACOUSTIC ARCHIVE",
        "cargo_state": None,
    },
    {
        "cargo_type": "EpistemologicalShrooms",
        "cargo_name": "WEAPONIZED EPISTEMOLOGICAL SHROOMS",
        "cargo_state": None,
    },
    {
        "cargo_type": "SentientPaperwork",
        "cargo_name": "SENTIENT TELEPATHIC PAPERWORK",
        "cargo_state": None,
    },
    {
        "cargo_type": "SchrodingerVIP",
        "cargo_name": "THE SCHRODINGER VIP",
        "cargo_state": "unobserved",
    },
]


@pytest.mark.parametrize("npc_type", NPC_TYPES)
@pytest.mark.parametrize("ctx", CARGO_CONTEXTS)
def test_all_npc_intros_include_cargo_specific_dialogue(npc_type: str, ctx: dict):
    from terminal.npc_logic import make_npc
    from terminal.npcs.cargo_dialogue import cargo_line_for

    npc = make_npc(npc_type, run_context=ctx)
    expected = cargo_line_for(npc.name, ctx)

    assert expected
    assert expected in npc.intro()


def test_cargo_dialogue_is_used_once_per_encounter():
    from terminal.npc_logic import make_npc
    from terminal.npcs.cargo_dialogue import cargo_line_for

    ctx = {
        "cargo_type": "AcousticArchive",
        "cargo_name": "CONTRABAND ACOUSTIC ARCHIVE",
    }
    npc = make_npc("gary", run_context=ctx)
    expected = cargo_line_for(npc.name, ctx)

    assert expected in npc.intro()
    _outcome, response = npc.respond("what")
    assert expected not in response


def test_direct_response_gets_cargo_dialogue_when_intro_was_not_called():
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome
    from terminal.npcs.cargo_dialogue import cargo_line_for

    ctx = {
        "cargo_type": "SentientPaperwork",
        "cargo_name": "SENTIENT TELEPATHIC PAPERWORK",
    }
    npc = make_npc("gary", run_context=ctx)
    expected = cargo_line_for(npc.name, ctx)

    outcome, response = npc.respond("what")

    assert outcome == NPCOutcome.CONTINUE
    assert expected in response


def test_run_context_includes_cargo_identity():
    from cargo.acoustic_archive import AcousticArchive
    from config import settings as S
    from roguelite.run_manager import RunManager

    cargo = AcousticArchive()
    cargo.integrity = 64.0
    cargo.is_damaged = True

    run_mgr = RunManager.__new__(RunManager)
    run_mgr._sector_index = 2
    run_mgr._run_debt_reduced = 1200
    run_mgr._run_snaps = 1
    run_mgr._run_slingshots = 3
    run_mgr._ship = SimpleNamespace(hull=S.HULL_MAX * 0.75, cargo=cargo)

    ctx = run_mgr._build_run_context()

    assert ctx["cargo_type"] == "AcousticArchive"
    assert ctx["cargo_name"] == "CONTRABAND ACOUSTIC ARCHIVE"
    assert ctx["cargo_integrity"] == 64.0
    assert ctx["cargo_damaged"] is True
