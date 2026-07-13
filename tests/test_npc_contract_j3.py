"""Terminal V2 Phase J.3.6 — roster contract tests (C1–C10).

The parity lock. Every terminal NPC must honour the shared contract so the
dossier, portrait, scan chips, quips, and Records tab all work for all of them —
the kind of drift that let Chen/Bowen ship crashing for two chapters. Numbers
and shapes are pulled live; a refactor that breaks the contract fails here.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path
import pygame
import pytest

from terminal.npc_logic import make_npc
from terminal.npc_portraits import draw_portrait
from terminal.terminal import _pick_courier_quip
from terminal.vault_keys import canonical_key, resolve_keys


@pytest.fixture(autouse=True, scope="module")
def _pygame():
    pygame.init()
    pygame.font.init()
    yield


# (make_npc key, source filename)
ROSTER = [
    ("gary", "gary"),
    ("synthetic_droid", "synthetic_droid"),
    ("union_dispatcher", "union_dispatcher"),
    ("kress", "kress"),
    ("insurance_adjuster", "insurance_adjuster"),
    ("sandra", "sandra"),
    ("pirate", "pirate"),
    ("underground_dj", "underground_dj"),
    ("toll_authority", "toll_authority"),
    ("nervous_fence", "nervous_fence"),
    ("cargo_inspector", "cargo_inspector"),
    ("dray", "dray"),
    ("nova_soma_collections", "nova_soma"),
    ("mira_voss", "mira_voss"),
    ("idealist_rep", "idealist_rep"),
    ("corrupt_rep", "corrupt_rep"),
    ("chen", "chen"),
    ("bowen", "bowen"),
    ("lost_frequency", "lost_frequency"),
]
KEYS = [k for k, _ in ROSTER]

# NPCs that expose a shell/REPL systems path (curated showcases).
SYSTEMS_NPCS = {
    "synthetic_droid", "toll_authority", "chen", "lost_frequency",  # shell
    "nova_soma_collections", "bowen",                               # REPL
}


def _npc(key):
    try:
        return make_npc(key, run_context={})
    except TypeError:
        return make_npc(key)


# ── C1 — get_path_progress is a list of (name:str, cur:int, max:int) ────────

@pytest.mark.parametrize("key", KEYS)
def test_c1_path_progress_is_three_tuples(key):
    for row in _npc(key).get_path_progress():
        assert len(row) == 3, f"{key}: {row!r} is not a 3-tuple"
        name, cur, mx = row
        assert isinstance(name, str) and isinstance(cur, int) and isinstance(mx, int)
        assert mx > 0 and cur >= 0


# ── C2 — exploits() is a non-empty str->str map ─────────────────────────────

@pytest.mark.parametrize("key", KEYS)
def test_c2_exploits_reachable(key):
    ex = _npc(key).exploits()
    assert isinstance(ex, dict) and ex
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in ex.items())


# ── C3 — the portrait renders without crashing ──────────────────────────────

@pytest.mark.parametrize("key", KEYS)
def test_c3_portrait_renders(key):
    npc = _npc(key)
    surf = pygame.Surface((300, 260))
    draw_portrait(surf, npc.name, pygame.Rect(0, 0, 300, 260))  # must not raise


# ── C6 — the MUTTER quip lookup resolves for the NPC's (any-case) name ──────

@pytest.mark.parametrize("key", KEYS)
def test_c6_quip_lookup_never_crashes(key):
    npc = _npc(key)
    q = _pick_courier_quip("just some neutral text", npc.name)
    assert isinstance(q, str) and q


# ── C7 — every curated systems NPC actually exposes a working session ───────

@pytest.mark.parametrize("key", sorted(SYSTEMS_NPCS))
def test_c7_systems_npcs_expose_a_session(key):
    npc = _npc(key)
    assert (npc.shell_session() is not None) or (npc.repl_session() is not None)


# ── C9 — no NPC references the non-existent parsed.text (the Ch5/6 crash) ────

@pytest.mark.parametrize("key,filename", ROSTER)
def test_c9_no_parsed_text(key, filename):
    src = Path(f"terminal/npcs/{filename}.py").read_text(encoding="utf-8")
    assert "parsed.text" not in src, f"{filename}: uses parsed.text (ParsedInput has .raw)"


# ── C10 — the canonical vault key resolves and round-trips ──────────────────

@pytest.mark.parametrize("key,filename", ROSTER)
def test_c10_vault_key_resolves(key, filename):
    npc = _npc(key)
    canon = canonical_key(npc)
    assert canon and canon == key           # canonical key == make_npc/file key
    assert canon in resolve_keys(npc)        # and it's the first resolved alias


def test_records_vulnerability_db_lists_entire_terminal_roster():
    from renderer.records_screen import _NPC_LABEL

    labels = {key for key, _label in _NPC_LABEL}
    assert set(KEYS).issubset(labels)


# ── bonus — the whole roster survives a first input headless ────────────────

@pytest.mark.parametrize("key", KEYS)
def test_every_npc_survives_first_input(key):
    from terminal.terminal import Terminal
    npc = _npc(key)
    term = Terminal(npc, econ=None)
    term.activate()
    term._input = "hello, what are my options here"
    term._submit()          # respond + analysis + (no crash on dossier tuples)
    assert term.outcome in ("continue", "release", "impound", "exploit", "breach", "abort")
