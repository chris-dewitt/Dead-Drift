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
