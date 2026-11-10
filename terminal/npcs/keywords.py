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
# These only negate the following verb ("unable to comply"). "I'm unhappy
# but I'll wait" is still a surrender — "understand" is not in this set.
_UN_TO_NEGATORS = ("unable", "unwilling", "unhappy")
# "n't" contractions survive tokenizing as their own trailing word.
_NEG_SUFFIX = re.compile(r"n['’]t\b")

_WORD_SPLIT = re.compile(r"[a-z0-9']+")

# "no" is a negator, except where it opens an agreement idiom. A trailing
# window that treated every "no" as refusal turned "I'll wait, no problem"
# and "I will wait here no matter what" into refusals.
_POSITIVE_NO = (
    "no problem", "no matter", "no worries", "no issue", "no rush",
    "no question",
)


def _is_negator_at(words: Sequence[str], index: int) -> bool:
    """True if `words[index]` negates an agreement elsewhere in the sentence."""
    word = words[index]
    if word in _UN_TO_NEGATORS:
        return index + 1 < len(words) and words[index + 1] == "to"
    return word in _NEGATORS or _NEG_SUFFIX.search(word) is not None


def _trailing_negator(words: Sequence[str], index: int) -> bool:
    """True if `words[index]` negates the agreement that precedes it.

    Bare "no" does, unless it opens "no problem" / "no matter" / the other
    positive idioms above.
    """
    word = words[index]
    if word == "no":
        tail = " ".join(words[index:index + 3])
        if any(tail.startswith(phrase) for phrase in _POSITIVE_NO):
            return False
        return True
    return _is_negator_at(words, index)


def negated(raw: str, token: str, window: int = 3) -> bool:
    """True if a negator sits within `window` words before `token` in `raw`.

    Window rather than whole-sentence, so "no problem, I'll wait right here"
    doesn't read as a negation of *wait* four words later. For a multi-word
    phrase the first word is the anchor: "not hold position" negates
    *hold position*. A negator that follows the phrase ("of course not") is
    handled by `affirmed_phrase_hit`, which looks past the whole phrase.
    """
    raw = normalize(raw)
    words = _WORD_SPLIT.findall(raw)
    target = normalize(token).split()[0]
    for i, w in enumerate(words):
        if w != target:
            continue
        for j in range(max(0, i - window), i):
            if _is_negator_at(words, j):
                return True
    return False


def _has_trailing_negation(words: Sequence[str], token: str, window: int) -> bool:
    """True if any whole-word hit of `token` has a negator in the next `window` words."""
    target = normalize(token).split()[0]
    for i, word in enumerate(words):
        if word != target:
            continue
        end = min(len(words), i + 1 + window)
        if any(_trailing_negator(words, j) for j in range(i + 1, end)):
            return True
    return False


def affirmed_hit(raw: str, tokens: Iterable[str], window: int = 3) -> bool:
    """Whole-word match on `tokens`, ignoring any hit that is negated.

    Negation counts on either side of the token. "I'm not sure" is the
    backward case; "certainly not" and "I certainly will not" put the
    negator after the agreement word, and taking those as consent impounded
    a refusal.
    """
    norm = normalize(raw)
    words = _WORD_SPLIT.findall(norm)
    return any(
        _word_re(t).search(norm) is not None
        and not negated(norm, t, window)
        and not _has_trailing_negation(words, t, window)
        for t in tokens
    )


def _bounded_phrase_at(norm: str, phrase: str, start: int) -> int:
    """Index of the next word-bounded occurrence of `phrase`, or -1.

    Substring matching is right for "hold position" and wrong for a phrase
    that begins inside another word: "happy to" is not inside "unhappy to".
    """
    while True:
        i = norm.find(phrase, start)
        if i < 0:
            return -1
        end = i + len(phrase)
        before_ok = i == 0 or not (norm[i - 1].isalnum() or norm[i - 1] == "'")
        after_ok = end == len(norm) or not (norm[end].isalnum() or norm[end] == "'")
        if before_ok and after_ok:
            return i
        start = i + 1


def affirmed_phrase_hit(raw: str, phrases: Iterable[str],
                        window: int = 3) -> bool:
    """Word-bounded phrase match, ignoring any hit that is negated.

    A surrender phrase is no more inherently unambiguous than a surrender
    word. "hold position" is agreement and "I will not hold position" is
    the opposite. The negator is not always in front of the first word:
    "of course not", "will do, not a chance", and "yes sir, no" all refuse
    by putting it after the phrase. Matching the phrase bare impounded the
    player for refusing.
    """
    norm = normalize(raw)
    spans = [(m.group(), m.start(), m.end()) for m in _WORD_SPLIT.finditer(norm)]
    words = [w for w, _, _ in spans]
    for phrase in phrases:
        p = normalize(phrase)
        if not p:
            continue
        start = 0
        while True:
            i = _bounded_phrase_at(norm, p, start)
            if i < 0:
                break
            end = i + len(p)
            start = i + 1
            covered = [
                wi for wi, (_, s, e) in enumerate(spans)
                if e > i and s < end
            ]
            if not covered:
                continue
            first, last = covered[0], covered[-1]
            pre = range(max(0, first - window), first)
            post = range(last + 1, min(len(words), last + 1 + window))
            if any(_is_negator_at(words, j) for j in pre):
                continue
            if any(_trailing_negator(words, j) for j in post):
                continue
            return True
    return False
