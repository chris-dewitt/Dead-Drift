"""Character pass — keyword precision, roster parity, bribes that cost money.

Three classes of regression are locked here:

  * The pickup-word matcher. Short tokens matched as bare substrings turned
    ordinary dialogue into path hits — worst of all at the Chapter 6 climax,
    where "I'm not sure I understand" matched Bowen's compliance word *sure*
    and impounded the run on turn one.
  * Roster parity for the three J.3.1 climax NPCs, which shipped without
    exploit events, vault records, portrait geometry or escape lines.
  * `bribe_cost()`. The run deducts what that reports and nothing else, so an
    NPC that accepts credits without overriding it is handing out free wins.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path

import pygame
import pytest

from terminal.npc_logic import make_npc
from terminal.npcs.base_npc import NPCOutcome
from terminal.npcs.keywords import affirmed_hit, hit, negated, word_hit


@pytest.fixture(autouse=True, scope="module")
def _pygame():
    pygame.init()
    pygame.font.init()
    yield


CLIMAX_NPCS = ["chen", "bowen", "lost_frequency"]


def _npc(key, **kw):
    try:
        return make_npc(key, run_context={}, **kw)
    except TypeError:
        return make_npc(key, **kw)


# ── the matcher itself ──────────────────────────────────────────────────────

def test_word_hit_respects_boundaries():
    assert word_hit("say no to them", ("no",))
    assert not word_hit("i don't know anything", ("no",))
    assert not word_hit("that ship has a lot of power", ("owe",))
    assert not word_hit("we are in a different sector", ("rent",))
    assert not word_hit("this is nothing to do with him", ("hi",))


def test_phrases_still_match_as_substrings():
    assert hit("well, no problem at all", ["no problem"])
    assert hit("i saw the clone tanks", ["clone tanks"])


def test_negation_guard():
    assert negated("i'm not sure i understand", "sure")
    assert negated("that isn't fine", "fine")
    assert not negated("sure, whatever you say", "sure")
    assert affirmed_hit("fine. i'll wait.", ("fine",))
    assert not affirmed_hit("i'm not sure i understand", ("sure",))


# ── Bowen: the Chapter 6 turn-one impound ───────────────────────────────────

@pytest.mark.parametrize("line", [
    "I'm not sure I understand",
    "I don't know what you're talking about",
    "nothing is in the hold",
    "now hold on a second",
    "I have nothing to declare",
    "that is not fine with me",
])
def test_bowen_does_not_impound_on_ordinary_dialogue(line):
    bowen = _npc("bowen")
    outcome, _ = bowen.respond(line)
    assert outcome != NPCOutcome.IMPOUND, (
        f"Bowen impounded on {line!r} — a false compliance/refusal match")


@pytest.mark.parametrize("line", ["okay, I'll wait right here", "sure",
                                  "fine, whatever you say", "no problem"])
def test_bowen_still_impounds_on_real_compliance(line):
    bowen = _npc("bowen")
    outcome, _ = bowen.respond(line)
    assert outcome == NPCOutcome.IMPOUND
    assert bowen._current_path == "COMPLY"


def test_bowen_refusal_still_releases_on_the_second_pass():
    bowen = _npc("bowen")
    assert bowen.respond("no")[0] == NPCOutcome.CONTINUE
    assert bowen.respond("not happening, I'm leaving")[0] == NPCOutcome.RELEASE


def test_bowen_personal_and_expose_still_crack_him():
    assert _npc("bowen").respond("who's in the photo on your lanyard")[0] == NPCOutcome.EXPLOIT
    bowen = _npc("bowen")
    bowen.respond("I saw the clone tanks on floor 31")
    assert bowen.respond("the people in the vats have my face")[0] == NPCOutcome.EXPLOIT


# ── Marrow and Felix: paths that fired on almost any sentence ───────────────

def test_marrow_greeting_needs_an_actual_greeting():
    """His greeting branch warms him by +2. Bare "hi" inside *this* and
    *nothing* meant nearly every line the player typed did that."""
    cold = _npc("underground_dj")
    cold.respond("this is nothing to do with his cargo")
    assert cold.disposition < 2

    warm = _npc("underground_dj")
    warm.respond("hi there marrow")
    assert warm.disposition >= 2


def test_felix_sympathy_needs_an_actual_appeal():
    felix = _npc("nervous_fence")
    felix.respond("that ship has a lot of power in the current sector")
    assert felix._sympathy_t == 0
    felix2 = _npc("nervous_fence")
    felix2.respond("I'm broke and in debt, same as you")
    assert felix2._sympathy_t == 1


# ── bribes that actually cost money ─────────────────────────────────────────

@pytest.mark.parametrize("key,line,expected", [
    ("dray", "here, take 800 credits", 800),
    ("nervous_fence", "5000 credits", 5000),
])
def test_credit_bribes_report_their_cost(key, line, expected):
    """`RunManager` deducts `npc.bribe_cost()`; a bribe that reports 0 is free."""
    npc = _npc(key)
    outcome, _ = npc.respond(line)
    assert outcome == NPCOutcome.RELEASE
    assert npc.bribe_cost() == expected


def test_every_bribeable_npc_overrides_bribe_cost():
    """Any NPC whose source tracks a paid amount must report it."""
    from terminal.npcs import base_npc
    offenders = []
    for key in ("gary", "union_dispatcher", "toll_authority", "nervous_fence",
                "cargo_inspector", "dray", "corrupt_rep"):
        npc = _npc(key)
        if type(npc).bribe_cost is base_npc.BaseNPC.bribe_cost:
            offenders.append(key)
    assert not offenders, f"accept credits but never charge: {offenders}"


# ── the three climax NPCs, brought up to roster parity ──────────────────────

@pytest.mark.parametrize("key", CLIMAX_NPCS)
def test_climax_npcs_file_their_wins(key):
    """A win has to reach Bax's vault, or Records never learns the path."""
    from core.event_bus import bus, EVT_NLP_EXPLOIT

    seen = []

    def _listen(npc, exploit_key, **_):
        seen.append(exploit_key)

    bus.subscribe(EVT_NLP_EXPLOIT, _listen)
    try:
        winning = {
            "chen":           ["wipe it for everyone"],
            "bowen":          ["who's in the photo on your lanyard"],
            "lost_frequency": ["goodbye, old man"],
        }[key]
        npc = _npc(key)
        for line in winning:
            npc.respond(line)
    finally:
        bus.unsubscribe(EVT_NLP_EXPLOIT, _listen)
    assert seen, f"{key}: winning path emitted no exploit event"


@pytest.mark.parametrize("key", CLIMAX_NPCS)
def test_climax_npcs_record_to_the_vault(key):
    class _Vault:
        def __init__(self): self.rows = []
        def record(self, npc_type, phrase): self.rows.append((npc_type, phrase))

    vault = _Vault()
    npc = make_npc(key, vocabulary_vault=vault, run_context={})
    for line in ("wipe it for everyone", "who's in the photo on your lanyard",
                 "goodbye, old man"):
        npc.respond(line)
    assert vault.rows, f"{key}: nothing filed in the vocabulary vault"


@pytest.mark.parametrize("key", CLIMAX_NPCS)
def test_climax_npcs_answer_the_escape_in_character(key):
    """`BaseNPC` ships a generic close-out; the roster's leads override it."""
    from terminal.npcs import base_npc
    npc = _npc(key)
    assert type(npc)._universal_escape_line is not base_npc.BaseNPC._universal_escape_line
    outcome, line = npc.respond(base_npc.BaseNPC._UNIVERSAL_ESCAPE)
    assert outcome == NPCOutcome.RELEASE and line


@pytest.mark.parametrize("key", CLIMAX_NPCS)
def test_climax_npcs_have_their_own_portrait(key):
    """They shipped on the `_unknown` '?' placeholder — the two climax
    characters of the game had no face."""
    from terminal import npc_portraits as P
    assert key in P._DISPATCH and P._DISPATCH[key] is not P._unknown
    assert key in P._BACKDROPS


@pytest.mark.parametrize("key", CLIMAX_NPCS)
def test_climax_npcs_vary_their_lines(key):
    """One canned string per branch reads as a script; the roster randomises."""
    src = Path(f"terminal/npcs/{key if key != 'nova_soma_collections' else 'nova_soma'}.py")
    assert src.read_text(encoding="utf-8").count("random.choice") >= 6


def test_long_npc_names_do_not_overprint_the_relay_banner():
    """The callsign is right-aligned over a left-aligned banner; 'FREQUENCY
    LOST' and 'NOVA SOMA COLLECTIONS' used to print straight through it."""
    from terminal.npc_portraits import fit_relay_banner
    from core.text import get_font

    font = get_font(8, bold=True)
    left, right = 16, 286        # the strip a 300px portrait actually gets

    for name in ("GARY", "DRAY", "CHEN", "BOWEN", "KRESS",
                 "FREQUENCY LOST", "NOVA SOMA COLLECTIONS",
                 "TOLL AUTHORITY", "INSPECTOR HOLT", "RELAY-7 FELIX"):
        callsign_x = right - font.size(name)[0] - 6
        banner = fit_relay_banner(font, name, left, callsign_x)
        assert left + font.size(banner)[0] + 6 <= callsign_x, (
            f"{name}: banner {banner!r} runs into the callsign")

    # Short names keep the full banner; the longest name loses some of it.
    assert fit_relay_banner(font, "GARY", left,
                            right - font.size("GARY")[0] - 6) == \
        "LIVE COMM // NOVA SOMA RELAY 7-B"
    longest = "NOVA SOMA COLLECTIONS"
    assert fit_relay_banner(font, longest, left,
                            right - font.size(longest)[0] - 6) != \
        "LIVE COMM // NOVA SOMA RELAY 7-B"
