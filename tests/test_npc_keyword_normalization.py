"""Coverage for the NPC keyword normalization sweep (playtest backlog)."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def test_universal_escape_releases_every_npc():
    """The hidden 'fuck off' easter egg should release every NPC in the registry."""
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    npc_keys = [
        "gary", "synthetic_droid", "union_dispatcher", "kress",
        "insurance_adjuster", "sandra", "pirate", "underground_dj",
        "toll_authority", "nervous_fence", "cargo_inspector",
        "dray", "nova_soma_collections", "mira_voss",
        "idealist_rep", "corrupt_rep",
    ]
    for key in npc_keys:
        try:
            npc = make_npc(key)
        except TypeError:
            # Some NPCs require kwargs; pass empty dict.
            npc = make_npc(key, run_context={})
        out, line = npc.respond("fuck off")
        assert out == NPCOutcome.RELEASE, \
            f"{key} did not release on the universal escape phrase"
        assert line, f"{key} produced empty release line"


def test_universal_escape_phrase_is_not_in_any_keyword_hint():
    """The phrase is an easter egg — must NOT appear in any exploit
    description, dossier hint, or in-game readable text."""
    from pathlib import Path
    forbidden_phrase = "fuck off"
    # Search through everything except the BaseNPC and the
    # idealist/corrupt rep bodies (which legitimately ship with custom
    # close-out lines).
    repo_files = list(Path(".").rglob("*.py"))
    leakage = []
    allowed = {
        Path("terminal/npcs/base_npc.py"),
        Path("terminal/npcs/idealist_rep.py"),
        Path("terminal/npcs/corrupt_rep.py"),
        Path("tests/test_new_union_reps.py"),
        Path("tests/test_npc_keyword_normalization.py"),
    }
    for fp in repo_files:
        rel = fp.relative_to(".")
        if rel in allowed:
            continue
        try:
            content = fp.read_text(encoding="utf-8").lower()
        except Exception:
            continue
        if forbidden_phrase in content:
            leakage.append(str(rel))
    assert not leakage, (
        "universal-escape phrase leaked into player-visible files: "
        + ", ".join(leakage)
    )


def test_dray_recognises_gripe_and_complain():
    """Playtest fix: bare 'gripe' / 'complain' should arm Dray's commiserate path."""
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome
    dray = make_npc("dray")
    for phrase in ("just here to gripe a bit",
                   "I'm complaining about the barges",
                   "let me whinge for a sec"):
        d2 = make_npc("dray")
        out, _ = d2.respond(phrase)
        assert out == NPCOutcome.CONTINUE
        assert d2._gripe_count >= 1


def test_dray_dossier_uses_standard_bribe_format():
    """The dossier label must read 'BRIBE [<amount>+ cr]' not 'BRIBED'."""
    from terminal.npc_logic import make_npc
    dray = make_npc("dray")
    rows = dray.get_path_progress()
    labels = [r[0] for r in rows]
    assert any("BRIBE [" in lbl and " cr" in lbl for lbl in labels), \
        f"Dray dossier missing standardised BRIBE label: {labels}"


def test_felix_gossip_keyword_arms_path_without_npc_name():
    """Playtest fix: bare 'gossip' should now respond and arm the path,
    not fall through to filler."""
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome
    felix = make_npc("nervous_fence")
    out, line = felix.respond("got any gossip on the comm tonight")
    assert out == NPCOutcome.CONTINUE
    assert felix._gossip_t >= 1
    assert "name" in line.lower() or "whom" in line.lower() or "rumour" in line.lower()


def test_felix_ill_tell_you_is_not_a_barge_call():
    """HOSTILE used to substring-match 'i'll tell' / 'going to tell', so
    cooperative lines — including the advertised DEAL phrase 'I'll tell
    you what' — 1-turn IMPOUNDed a Felix intercept."""
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    for line in (
        "I'll tell you what's in the hold",
        "I'll tell you what I've got",
        "I'm going to tell you the truth",
        "I'll tell you why I'm here",
        "the authorities keep chasing me",
        "I don't snitch",
        "I won't report you",
    ):
        felix = make_npc("nervous_fence")
        out, _ = felix.respond(line)
        assert out != NPCOutcome.IMPOUND, f"{line!r} called a barge"


def test_felix_tell_you_what_still_deals():
    """The DEAL pickup 'tell you what' must reach DEAL, not HOSTILE."""
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    felix = make_npc("nervous_fence")
    out, _ = felix.respond("I'll tell you what I've got")
    assert out == NPCOutcome.RELEASE
    assert felix._current_path == "DEAL"


def test_felix_real_threats_still_impound():
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    for line in (
        "I'll report you",
        "I'll snitch",
        "turn you in to dispatch",
        "I'll tell the authorities",
        "expose you to the union",
        "I'm going to tell them about this relay",
    ):
        felix = make_npc("nervous_fence")
        out, _ = felix.respond(line)
        assert out == NPCOutcome.IMPOUND, f"{line!r} should still call a barge"


def test_holt_personal_effects_is_compliant_not_impound():
    """Documented COMPLY phrase 'personal effects' used to substring-match
    HONEST token 'person' and IMPOUND instead of waving the player through."""
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    holt = make_npc("cargo_inspector")
    out, _ = holt.respond("personal effects")
    assert out == NPCOutcome.RELEASE
    assert holt._current_path == "COMPLIANT"


def test_holt_admitting_a_person_still_impounds():
    """Whole-word 'person' must still catch an honest VIP admission."""
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    holt = make_npc("cargo_inspector")
    out, _ = holt.respond("there's a person in the hold")
    assert out == NPCOutcome.IMPOUND


def test_holt_dont_know_the_code_is_not_a_citation():
    """Holt's intro asks for classification codes. Ordinary 'I don't know
    the code' must not fire the one-turn CODE CITATION RELEASE."""
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    holt = make_npc("cargo_inspector")
    out, _ = holt.respond("I don't know the code")
    assert out == NPCOutcome.CONTINUE
    assert holt._current_path != "CODE CITATION"


def test_holt_actual_cargo_code_still_releases():
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    holt = make_npc("cargo_inspector")
    out, _ = holt.respond("cargo code class c, tariff code 0403")
    assert out == NPCOutcome.RELEASE
    assert holt._current_path == "CODE CITATION"


def test_dispatcher_interest_is_not_a_coffee_break():
    """Dispatcher's intro talks about compound interest. Substring 'rest'
    inside 'interest' used to fire the one-turn COFFEE BREAK RELEASE."""
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    dispatcher = make_npc("union_dispatcher")
    out, _ = dispatcher.respond("what's the compound interest on this")
    assert out == NPCOutcome.CONTINUE
    assert dispatcher._current_path != "COFFEE BREAK"
    assert dispatcher._coffee_hit is False


def test_dispatcher_create_is_not_a_coffee_break():
    """'eat' must not substring-match ordinary verbs like 'create'."""
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    dispatcher = make_npc("union_dispatcher")
    out, _ = dispatcher.respond("I didn't create this debt")
    assert out == NPCOutcome.CONTINUE
    assert dispatcher._current_path != "COFFEE BREAK"
    assert dispatcher._coffee_hit is False


def test_dispatcher_actual_coffee_break_still_releases():
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    dispatcher = make_npc("union_dispatcher")
    out, _ = dispatcher.respond("you should take a coffee break")
    assert out == NPCOutcome.RELEASE
    assert dispatcher._current_path == "COFFEE BREAK"
    assert dispatcher._coffee_hit is True


def test_dispatcher_whole_word_rest_still_releases():
    """Bare 'rest' / 'get some rest' is still the designed coffee path."""
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome

    dispatcher = make_npc("union_dispatcher")
    out, _ = dispatcher.respond("you should get some rest")
    assert out == NPCOutcome.RELEASE
    assert dispatcher._current_path == "COFFEE BREAK"


def test_pirate_extended_threat_keywords_land():
    """Playtest fix: more menacing phrasing should still register as a
    threat path, not bounce to filler."""
    from terminal.npc_logic import make_npc
    from terminal.npcs.base_npc import NPCOutcome
    pirate = make_npc("pirate", run_context={"run_snaps": 3})
    # 'vent your hold' is one of the new phrases; with 2+ snaps the
    # credibility check passes on the first qualifying turn.
    out, _ = pirate.respond("vent your hold and walk away")
    assert out in (NPCOutcome.CONTINUE, NPCOutcome.RELEASE)
    assert pirate._current_path == "INTIMIDATE"
