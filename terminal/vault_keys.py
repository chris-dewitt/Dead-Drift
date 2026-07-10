"""Terminal V2 Phase J.3.3 (spec T-6) — one vault-key resolver.

The Vulnerability / Records tab files a discovered exploit under a snake_case
key. Historically three different spellings were in play: NPCs recorded
snake_case (`synthetic_droid`), the systems-exploit write path used
`type(npc).__name__.lower()` (`syntheticdroid`), and the scan-chip lookup read a
display-name table (`_NPC_VAULT_KEYS["TK-9"]`). When they disagreed, a backdoor
the player had already discovered failed to light up as "known".

This module is the single resolver both the write path and the lookup use:
`canonical_key(npc)` is the one snake_case key the Records tab stores under, and
`resolve_keys(npc)` returns it plus historical aliases so old saves still match.
"""
from __future__ import annotations

import re

# Robust CamelCase / acronym → snake_case. Handles the roster's one acronym
# class ("UndergroundDJ" → "underground_dj") as well as the normal names.
_CAMEL_1 = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_2 = re.compile(r"([a-z0-9])([A-Z])")


def camel_to_snake(name: str) -> str:
    return _CAMEL_2.sub(r"\1_\2", _CAMEL_1.sub(r"\1_\2", name)).lower()


# Historical / cross-referenced aliases, keyed by the canonical snake_case key.
# Kept small: the canonical key is authoritative; these only preserve lookups
# that predate the registry (display-name spellings, character nicknames).
_ALIASES: dict[str, tuple[str, ...]] = {
    "synthetic_droid":        ("syntheticdroid", "tk_9", "tk9"),
    "union_dispatcher":       ("uniondispatcher", "dispatcher"),
    "insurance_adjuster":     ("insuranceadjuster", "morwenna"),
    "nervous_fence":          ("nervousfence", "relay_7_felix", "felix"),
    "cargo_inspector":        ("cargoinspector", "inspector_holt", "holt"),
    "nova_soma_collections":  ("novasomacollections", "nova_soma"),
    "underground_dj":         ("undergrounddj", "marrow"),
    "lost_frequency":         ("lostfrequency", "frequency_lost", "marrow"),
    "pirate":                 ("krellborn",),
    "idealist_rep":           ("idealistrep", "edmund", "eddie"),
    "corrupt_rep":            ("corruptrep", "vince", "vinny"),
    "mira_voss":              ("miravoss",),
    "toll_authority":         ("tollauthority",),
}


def canonical_key(npc) -> str:
    """The one snake_case key the Records tab files this NPC's exploits under."""
    return camel_to_snake(type(npc).__name__)


def resolve_keys(npc) -> tuple[str, ...]:
    """Canonical key first, then any historical aliases (deduped)."""
    canon = canonical_key(npc)
    out = [canon]
    for a in _ALIASES.get(canon, ()):
        if a not in out:
            out.append(a)
    return tuple(out)
