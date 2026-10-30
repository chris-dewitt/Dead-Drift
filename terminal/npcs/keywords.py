"""One matcher for NPC pickup words.

Every NPC evaluator recognises the player's intent by scanning the raw input
for vocabulary. Historically that was always a bare substring test:

    if any(w in raw for w in _REFUSE_KEYWORDS):   # _REFUSE_KEYWORDS = ["no", ...]

which is right for multi-word phrases ("same boat", "floor thirty one") and
badly wrong for short tokens. `"no"` lives inside *know*, *nothing*, *now*,
*cannot* and *Nova* — so at the Chapter 6 climax "I'm not sure I understand"
matched Bowen's COMPLY word `"sure"` (inside *unsure*) and impounded the run on
turn one. Marrow's `"hi"` fired his greeting path on any sentence containing
*this*. Felix's `"owe"` fired sympathy on *power*.

Two NPCs (Holt, the Dispatcher) had already grown their own local fix — a
phrase list matched by substring plus a token list matched on word boundaries.
This module is that fix, once, for everyone:

    _REFUSE_PHRASES = ["not happening", "go to hell"]   # substring
    _REFUSE_WORDS   = ("no", "never", "won't")          # whole word

    if hit(raw, _REFUSE_PHRASES, _REFUSE_WORDS):
        ...

Both list names still end in `_PHRASES` / `_WORDS`, so the vocabulary counts in
`tests/test_npc_schema_b1.py` keep seeing every pickup word.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable, Sequence


# Typographic apostrophes reach the parser from pasted text and from input
# methods that autocorrect. Every pickup word in the roster is written with a
# straight quote, so a curly one silently defeated both the word matcher
# ("won’t" never matched the token "won't") and the negation guard
# ("that isn’t fine" read as consent). Fold them together before matching.
_SMART_QUOTES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "´": "'"})


def normalize(raw: str) -> str:
    """Lowercase-preserving fold of the apostrophe variants onto `'`."""
    return raw.translate(_SMART_QUOTES)


@lru_cache(maxsize=512)
def _word_re(token: str) -> re.Pattern[str]:
    """Whole-word matcher for one token, cached (evaluators re-scan every turn).

    `\\b` on both sides handles the roster's tokens, including the ones with an
    apostrophe (`won't`) or a hyphen (`tk-9`) — those break into two words, and
    the boundaries still land on the outer edges.
    """
    return re.compile(rf"\b{re.escape(normalize(token))}\b")


def word_hit(raw: str, tokens: Iterable[str]) -> bool:
    """True if any token appears in `raw` as a whole word."""
    raw = normalize(raw)
    return any(_word_re(t).search(raw) is not None for t in tokens)


def phrase_hit(raw: str, phrases: Iterable[str]) -> bool:
    """True if any phrase appears in `raw` as a substring."""
    raw = normalize(raw)
    return any(normalize(p) in raw for p in phrases)


def hit(raw: str, phrases: Iterable[str] = (),
        tokens: Iterable[str] = ()) -> bool:
    """The combined test: phrases by substring, tokens on word boundaries.

    `raw` is expected lowercased, the way every evaluator already holds it.
    """
    return phrase_hit(raw, phrases) or word_hit(raw, tokens)


# Amount-gated NPCs (Holt, Felix, Dray, Mira) used to treat every parsed
# number as cash. `extract_credit_amount` maps any 3–7 digit run, so
# "the crate weighs 1200 kilos" and "serial number 4120" closed the
# terminal and billed that figure. A real offer is either the whole line
# (scan chips light on bare "600" / "800") or a line that actually talks
# about money.
_MONEY_WORDS = (
    "credit", "credits", "cr", "pay", "paid", "paying", "payment",
    "bribe", "cash", "money", "grand", "thousand", "fee", "fees",
    "offer", "transfer", "wire", "compensate",
)
_BARE_FIGURE = re.compile(
    r"^\$?\d{1,7}(?:\.\d+)?\s*(?:k|cr|credits?|grand)?$",
    re.IGNORECASE,
)


def is_money_offer(raw: str) -> bool:
    """True when `raw` is a price, not a number that happens to be nearby.

    Bare figures ("600", "2k", "1500 credits") stay offers so the scan
    chips still land. A weight, a serial, or a wait ("1200 kilos",
    "serial number 4120", "waiting 600 seconds") does not.
    """
    text = normalize(raw).strip()
    bare = text.replace(",", "").strip(".,!?;:'\"")
    if _BARE_FIGURE.fullmatch(bare):
        return True
    if word_hit(text, _MONEY_WORDS):
        return True
    return re.search(r"\b\d+\s*k\b", text) is not None


def all_words(*groups: Sequence[str]) -> tuple[str, ...]:
    """Flatten phrase + token groups into one deduped tuple.

    Handy for `get_path_progress` hints and for tests that want the full pickup
    vocabulary of a path without caring which half matched how.
    """
    out: list[str] = []
    for g in groups:
        for w in g:
            if w not in out:
                out.append(w)
    return tuple(out)


# ---------------------------------------------------------------------------
# Negation
# ---------------------------------------------------------------------------
# An affirmation is only an affirmation until someone puts "not" in front of
# it. Bowen's compliance path turns on words like *sure* and *fine*; "I'm not
# sure" and "that's not fine" are the opposite of compliance, and taking them
# at face value impounded the run. Any NPC keying off agreement words should
# run them past `negated_hit` rather than a bare match.

_NEGATORS = (
    "not", "never", "no", "nor", "none", "nothing", "nobody",
    "cannot", "cant", "wont", "dont", "aint", "hardly", "barely",
    "refuse", "refusing", "decline", "hell",
)
# "n't" contractions survive tokenizing as their own trailing word.
_NEG_SUFFIX = re.compile(r"n['’]t\b")

_WORD_SPLIT = re.compile(r"[a-z0-9']+")


def negated(raw: str, token: str, window: int = 3) -> bool:
    """True if a negator sits within `window` words before `token` in `raw`.

    Window rather than whole-sentence, so "no problem, I'll wait right here"
    doesn't read as a negation of *wait* four words later. For a multi-word
    phrase the first word is the anchor: "not hold position" negates
    *hold position*.
    """
    raw = normalize(raw)
    words = _WORD_SPLIT.findall(raw)
    target = normalize(token).split()[0]
    for i, w in enumerate(words):
        if w != target:
            continue
        for prev in words[max(0, i - window):i]:
            if prev in _NEGATORS or _NEG_SUFFIX.search(prev):
                return True
    return False


def affirmed_hit(raw: str, tokens: Iterable[str], window: int = 3) -> bool:
    """Whole-word match on `tokens`, ignoring any hit that is negated."""
    norm = normalize(raw)
    return any(_word_re(t).search(norm) is not None and not negated(raw, t, window)
               for t in tokens)


def affirmed_phrase_hit(raw: str, phrases: Iterable[str],
                        window: int = 3) -> bool:
    """Substring match on `phrases`, ignoring any hit that is negated.

    A surrender phrase is no more inherently unambiguous than a surrender
    word: "hold position" is agreement, "I will not hold position" is the
    opposite, and matching the phrase bare impounded the player for refusing.
    """
    norm = normalize(raw)
    return any(normalize(p) in norm and not negated(raw, p, window)
               for p in phrases)
