"""Aliveness B.1 — NPC schema baseline guard.

Every terminal NPC must meet the schema declared in docs/NPC_SCHEMA.md:

  * >= 15 distinct accepted pickup words across all paths
  * >= 3 distinct exploit win paths
  * If a bribe path exists, the dossier `_current_path` must use the
    standardised `BRIBE [<amount> cr]` format once an amount is paid.
  * Universal escape phrase released  covered separately in
    test_npc_keyword_normalization.py.
  * At least one cross-reference to another named character.

Numbers are pulled live from the source; if a refactor changes a
keyword list, the test re-counts. If a count drops below the baseline
the test fails with a pointer to the schema doc."""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import re
from pathlib import Path

import pygame


_NPC_FILE_MAP = [
    ("gary",                    "gary"),
    ("synthetic_droid",         "synthetic_droid"),
    ("union_dispatcher",        "union_dispatcher"),
    ("kress",                   "kress"),
    ("insurance_adjuster",      "insurance_adjuster"),
    ("sandra",                  "sandra"),
    ("pirate",                  "pirate"),
    ("underground_dj",          "underground_dj"),
    ("toll_authority",          "toll_authority"),
    ("nervous_fence",           "nervous_fence"),
    ("cargo_inspector",         "cargo_inspector"),
    ("dray",                    "dray"),
    ("nova_soma_collections",   "nova_soma"),
    ("mira_voss",               "mira_voss"),
    ("idealist_rep",            "idealist_rep"),
    ("corrupt_rep",             "corrupt_rep"),
]

# Match any module-level vocab list  *_KEYWORDS / *_WORDS / *_PHRASES /
# *_HINTS / *_TRIGGERS / *_VOCAB  for accurate vocabulary counts.
_VOCAB_RE = re.compile(
    r'_\w*(?:KEYWORDS|WORDS|PHRASES|HINTS|TRIGGERS|VOCAB)\s*=\s*[\[\(](.*?)[\]\)]',
    re.S,
)

# Other character names every NPC ought to reference at least once.
_CROSS_REF_NAMES = (
    "bax", "gary", "sandra", "felix", "marrow", "nova soma",
    "blevins", "kress", "morwenna", "holt", "krellborn",
    "eddie", "vinny", "dray", "mira", "tk-9", "tk9",
)


def _count_keywords(filename: str) -> int:
    """Distinct lowercase strings across all vocab lists in the file."""
    src = Path(f"terminal/npcs/{filename}.py").read_text(encoding="utf-8")
    seen: set[str] = set()
    for m in _VOCAB_RE.finditer(src):
        block = m.group(1)
        for tok in re.findall(r'"([^"]+)"', block):
            seen.add(tok.lower())
    return len(seen)


def _cross_ref_count(filename: str) -> int:
    src = Path(f"terminal/npcs/{filename}.py").read_text(encoding="utf-8")
    src_l = src.lower()
    return sum(1 for n in _CROSS_REF_NAMES if n in src_l)


def test_every_npc_meets_15_keyword_floor():
    """Schema baseline: every NPC has >= 15 distinct pickup words."""
    pygame.init()
    pygame.font.init()
    failures = []
    for npc_key, filename in _NPC_FILE_MAP:
        n = _count_keywords(filename)
        if n < 15:
            failures.append((npc_key, n))
    assert not failures, (
        f"NPCs under 15-keyword floor (see docs/NPC_SCHEMA.md): {failures}"
    )


def test_every_npc_has_three_or_more_exploits():
    pygame.init()
    pygame.font.init()
    from terminal.npc_logic import make_npc
    failures = []
    for npc_key, _filename in _NPC_FILE_MAP:
        try:
            npc = make_npc(npc_key, run_context={})
        except TypeError:
            npc = make_npc(npc_key)
        if len(npc.exploits()) < 3:
            failures.append((npc_key, len(npc.exploits())))
    assert not failures, f"NPCs with <3 exploits: {failures}"


def test_every_bribeable_npc_uses_standard_label():
    """For NPCs that accept a credit bribe, `_current_path` set on the
    accepting branch must use the `BRIBE [<amount> cr]` format. Reference
    impl: dray. NPCs flagged as 'no bribe path' in the schema doc are
    exempt."""
    bribeable = {
        "gary":             "gary",
        "union_dispatcher": "union_dispatcher",
        "toll_authority":   "toll_authority",
        "nervous_fence":    "nervous_fence",
        "cargo_inspector":  "cargo_inspector",
        "dray":             "dray",
        "corrupt_rep":      "corrupt_rep",
    }
    failures = []
    for npc_key, filename in bribeable.items():
        src = Path(f"terminal/npcs/{filename}.py").read_text(encoding="utf-8")
        if "f\"BRIBE [{" not in src and "BRIBE [{" not in src:
            failures.append(npc_key)
    assert not failures, (
        f"NPCs with bribe paths but no standard `BRIBE [X cr]` label: "
        f"{failures}. See docs/NPC_SCHEMA.md."
    )


def test_every_npc_cross_references_at_least_one_named_character():
    pygame.init()
    pygame.font.init()
    failures = []
    for npc_key, filename in _NPC_FILE_MAP:
        n = _cross_ref_count(filename)
        # Self-reference doesn't count  filter that.
        # We rely on the rough heuristic that other-character mentions
        # push the count above 1 (the npc's own name is one).
        if n < 2:
            failures.append((npc_key, n))
    assert not failures, (
        f"NPCs not cross-referencing another named character "
        f"(see docs/NPC_SCHEMA.md): {failures}"
    )


def test_schema_doc_present():
    """docs/NPC_SCHEMA.md must exist and reference each NPC by file key."""
    doc = Path("docs/NPC_SCHEMA.md").read_text(encoding="utf-8")
    for npc_key, _ in _NPC_FILE_MAP:
        assert npc_key in doc, f"docs/NPC_SCHEMA.md missing entry for {npc_key}"
