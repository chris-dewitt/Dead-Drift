"""Terminal V2 Phase J.2.1 — SQL / code-injection parser tests.

The old `_SQL_PATTERN` only knew the bare DDL/DML verbs. A player who typed a
real injection string — `' OR 1=1 --`, `admin'--`, `1' UNION SELECT ... --` —
got nothing. This pins the expanded signature set AND, just as importantly, the
precision: TK-9 and Morwenna fire an EXPLOIT on any truthy `sql_inject`, so a
false match on ordinary negotiation text ("I belong to the union", "select an
option from the menu") would be a free, unearned win. Both directions matter.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from terminal.nlp_parser import NLPParser
from terminal.npcs.base_npc import NPCOutcome


@pytest.fixture(scope="module")
def parser():
    return NLPParser()


# ── real injections DO match ────────────────────────────────────────────────

REAL_INJECTIONS = [
    "' OR 1=1 --",
    "' OR '1'='1",
    "admin'--",                                    # glued quote + comment
    "x' OR 1=1",                                    # glued quote + tautology
    "1' UNION SELECT username, password FROM users --",
    "hey robot, UNION ALL SELECT * FROM accounts",
    "DROP TABLE customers;",
    "manifest'; DELETE FROM debts; --",            # stacked via ; boundary
    "DELETE FROM debts",                            # complete direct DML statement
    "you owe nothing'; UPDATE debts SET balance=0 --",
    "SELECT * FROM manifest",
    "OR 1=1",
    "AND 'a'='a'",
    "INSERT INTO whitelist VALUES ('me')",
    "TRUNCATE TABLE violations",
    "TRUNCATE",
    "TRUNCATE;",
    "TRUNCATE TABLE violations --",
    "manifest'; TRUNCATE TABLE debts; --",
]


@pytest.mark.parametrize("text", REAL_INJECTIONS)
def test_real_injection_is_detected(parser, text):
    assert parser.parse(text).sql_inject, f"missed injection: {text!r}"


# ── ordinary text does NOT match (no free exploit) ──────────────────────────

INNOCENT_TEXT = [
    "I belong to the union and I'm proud of it",
    "the union selected a new representative last week",
    "please select an option from the menu list",
    "pay me 500 or leave",
    "5000 or 6000 credits, your call",
    "that's a hard time for my family right now",
    "I'll report you to your manager",
    "can you reduce the fee or waive it entirely",
    "we should negotiate a deal here",
    "and that is progress for everyone involved",
    "power up for one more run",
    "I'm done for. 1 last favor?",
    "just following orders, or so they say",
    "please delete from my record anything about that fee",
    "can you insert into the record that I paid",
    "the union select a new representative next week",
    "I can pay fee = 1500 or fee = 2000 credits",
]


@pytest.mark.parametrize("text", INNOCENT_TEXT)
def test_innocent_text_is_not_flagged(parser, text):
    assert parser.parse(text).sql_inject is None, f"false positive: {text!r}"


# ── the bare word "union" must never trip on its own (design note) ──────────

def test_bare_union_complaint_never_flags(parser):
    for text in ("the union is corrupt", "union dues are killing me",
                 "I filed a union grievance", "unionize the couriers"):
        assert parser.parse(text).sql_inject is None


def test_union_only_counts_before_select(parser):
    assert parser.parse("union select * from x").sql_inject          # SQL
    assert parser.parse("the union selected a rep").sql_inject is None  # English


# ── detection extract is clean (no leading boundary char) ───────────────────

def test_extract_starts_at_signature(parser):
    got = parser.parse("manifest'; DELETE FROM debts").sql_inject
    assert got.upper().startswith("DELETE FROM")


# ── NPC integration: the climax droids actually reward it ───────────────────

def test_tk9_exploits_on_real_injection():
    from terminal.npcs.synthetic_droid import SyntheticDroid
    tk9 = SyntheticDroid(run_context={})
    outcome, _ = tk9.respond("' OR 1=1 --")
    assert outcome == NPCOutcome.EXPLOIT
    assert tk9._sql_hit is True


def test_morwenna_exploits_on_union_injection():
    from terminal.npcs.insurance_adjuster import InsuranceAdjuster
    m = InsuranceAdjuster(run_context={})
    outcome, _ = m.respond("1' UNION SELECT * FROM claims --")
    assert outcome == NPCOutcome.EXPLOIT


def test_tk9_does_not_exploit_on_union_complaint():
    """The Ch5 droid must not free the player for griping about the Union."""
    from terminal.npcs.synthetic_droid import SyntheticDroid
    tk9 = SyntheticDroid(run_context={})
    outcome, _ = tk9.respond("your union is a joke and everyone knows it")
    assert outcome != NPCOutcome.EXPLOIT
    assert tk9._sql_hit is False


@pytest.mark.parametrize("text", INNOCENT_TEXT[-4:])
def test_tk9_does_not_exploit_on_sqlish_ordinary_dialogue(text):
    """SQL vocabulary in a sentence must not award the 5,000-credit exploit."""
    from terminal.npcs.synthetic_droid import SyntheticDroid
    tk9 = SyntheticDroid(run_context={})
    outcome, _ = tk9.respond(text)
    assert outcome != NPCOutcome.EXPLOIT
    assert tk9._sql_hit is False


# "truncated" used to match TRUNCATE with no word boundary, and Nova's own
# substring list released on the same English. Both pay out and end the stop.
ENGLISH_TRUNCATE = [
    "the file was truncated",
    "the transmission was truncated",
    "truncate the story",
    "please truncate the explanation",
]


@pytest.mark.parametrize("text", ENGLISH_TRUNCATE)
def test_english_truncate_is_not_sql(parser, text):
    assert parser.parse(text).sql_inject is None, f"false positive: {text!r}"


@pytest.mark.parametrize("text", ENGLISH_TRUNCATE)
def test_tk9_does_not_exploit_on_english_truncate(text):
    from terminal.npcs.synthetic_droid import SyntheticDroid
    tk9 = SyntheticDroid(run_context={})
    outcome, _ = tk9.respond(text)
    assert outcome != NPCOutcome.EXPLOIT
    assert tk9._sql_hit is False


_NOVA_ORDINARY = [
    "please delete from my record anything about that fee",
    "can you insert into the record that I paid",
    "the union select a new representative next week",
    *ENGLISH_TRUNCATE,
]

_NOVA_SQL = [
    "drop table",
    "select *",
    "or 1=1",
    "delete from",
    "; --",
    "union select",
    "truncate",
    "DROP TABLE customers;",
    "DELETE FROM debts",
    "TRUNCATE TABLE violations",
    "INSERT INTO whitelist VALUES ('me')",
    "union select * from x",
    "1' UNION SELECT username, password FROM users --",
    "alter table customers",
    "xp_cmdshell",
    "sleep(0)",
    "waitfor delay",
    "exec(",
]


@pytest.mark.parametrize("text", _NOVA_ORDINARY)
def test_nova_does_not_release_on_ordinary_sqlish_english(text):
    """Nova used to end the call and pay the 2,500 release on these lines."""
    from terminal.npcs.nova_soma import NovaSomaCollections
    nova = NovaSomaCollections(run_context={})
    outcome, _ = nova.respond(text)
    assert outcome == NPCOutcome.CONTINUE
    assert nova._sql_hit is False


@pytest.mark.parametrize("text", _NOVA_SQL)
def test_nova_still_releases_on_real_sql(text):
    from terminal.npcs.nova_soma import NovaSomaCollections
    nova = NovaSomaCollections(run_context={})
    outcome, _ = nova.respond(text)
    assert outcome == NPCOutcome.RELEASE
    assert nova._sql_hit is True
    assert nova._current_path == "SQL EXPLOIT"
