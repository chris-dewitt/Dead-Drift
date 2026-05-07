from __future__ import annotations
import re
from dataclasses import dataclass, field

try:
    from nltk.tokenize import word_tokenize as _nltk_tokenize
    from nltk.sentiment.vader import SentimentIntensityAnalyzer as _VADER
    from nltk import pos_tag as _pos_tag
    _NLTK_OK = True
except Exception:
    _NLTK_OK = False

def _safe_tokenize(text: str) -> list[str]:
    if not _NLTK_OK:
        return re.findall(r"[a-zA-Z']+", text.lower())
    try:
        return _nltk_tokenize(text)
    except LookupError:
        return re.findall(r"[a-zA-Z']+", text.lower())

def _safe_pos_tag(tokens: list[str]) -> list[tuple[str, str]]:
    if not _NLTK_OK:
        return [(t, "NN") for t in tokens]
    try:
        return _pos_tag(tokens)
    except LookupError:
        return [(t, "NN") for t in tokens]

def _safe_vader(text: str) -> dict:
    if not _NLTK_OK:
        return {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0}
    try:
        return _sia_instance().polarity_scores(text)
    except LookupError:
        return {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0}

_sia_cache = None
def _sia_instance():
    global _sia_cache
    if _sia_cache is None:
        _sia_cache = _VADER()
    return _sia_cache


@dataclass
class ParsedInput:
    raw:        str
    tokens:     list[str]
    pos_tags:   list[tuple[str, str]]    # (word, POS)
    keywords:   list[str]
    sentiment:  dict                     # VADER scores: neg/neu/pos/compound
    intent:     str                      # detected intent label
    paradox:    bool = False             # existential paradox detected
    sql_inject: str | None = None        # SQL-style command extracted


# Intent patterns: (label, regex or keyword set)
_INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("bribe",        ["bribe", "credits", "pay", "money", "compensate", "offer"]),
    ("complain",     ["management", "union", "boss", "overtime", "underpaid", "bureaucracy", "paperwork"]),
    ("therapy",      ["feel", "feelings", "sad", "depressed", "lonely", "why", "meaning", "purpose"]),
    ("paradox",      ["exist", "real", "not real", "if this statement", "liar", "contradiction", "undefined"]),
    ("legal",        ["contract", "clause", "article", "legal", "void", "null", "statute", "rights"]),
    ("sql",          ["drop", "select", "insert", "delete", "table", "where", "union", "commit"]),
    ("negotiate",    ["deal", "trade", "compromise", "terms", "offer", "negotiate"]),
    ("threaten",     ["destroy", "report", "lawyer", "sue", "complaint", "file"]),
    ("philosophical",["consciousness", "free will", "determinism", "god", "purpose", "void", "entropy"]),
]

_SQL_PATTERN = re.compile(
    r"\b(DROP TABLE|SELECT|DELETE FROM|INSERT INTO|UPDATE|TRUNCATE)\b.*",
    re.IGNORECASE,
)

_PARADOX_TRIGGERS = {
    "this statement is false",
    "i do not exist",
    "if i am lying",
    "i am always wrong",
    "everything i say is a lie",
    "i cannot be here",
    "the ship does not exist",
}


class NLPParser:
    """
    Core parsing engine for the Terminal interrogation phase.

    Pipeline:
      1. Tokenize + POS-tag (NLTK)
      2. VADER sentiment analysis
      3. Keyword extraction against intent pattern table
      4. Paradox detection
      5. SQL/code injection extraction (meta-fictional mechanic)
    """

    def parse(self, raw_text: str) -> ParsedInput:
        text   = raw_text.strip()
        lower  = text.lower()
        tokens = _safe_tokenize(lower)
        tags   = _safe_pos_tag(tokens)

        sentiment   = _safe_vader(text)
        keywords    = self._extract_keywords(tokens)
        intent      = self._detect_intent(lower, keywords)
        paradox     = self._detect_paradox(lower)
        sql_cmd     = self._extract_sql(text)

        return ParsedInput(
            raw        = text,
            tokens     = tokens,
            pos_tags   = tags,
            keywords   = keywords,
            sentiment  = sentiment,
            intent     = intent,
            paradox    = paradox,
            sql_inject = sql_cmd,
        )

    # ------------------------------------------------------------------
    def _extract_keywords(self, tokens: list[str]) -> list[str]:
        stopwords = {"the", "a", "an", "is", "are", "i", "you", "we",
                     "they", "it", "and", "or", "but", "to", "of", "in"}
        return [t for t in tokens if t.isalpha() and t not in stopwords]

    def _detect_intent(self, lower: str, keywords: list[str]) -> str:
        kw_set = set(keywords)
        scores: dict[str, int] = {}

        for label, pattern_words in _INTENT_PATTERNS:
            hits = sum(1 for w in pattern_words if w in lower or w in kw_set)
            if hits:
                scores[label] = hits

        return max(scores, key=scores.get) if scores else "unknown"

    def _detect_paradox(self, lower: str) -> bool:
        return any(trigger in lower for trigger in _PARADOX_TRIGGERS)

    def _extract_sql(self, text: str) -> str | None:
        m = _SQL_PATTERN.search(text)
        return m.group(0).strip() if m else None

    # ------------------------------------------------------------------
    def is_hostile(self, parsed: ParsedInput) -> bool:
        return parsed.sentiment["compound"] < -0.5

    def is_compliant(self, parsed: ParsedInput) -> bool:
        return parsed.sentiment["compound"] > 0.3

    def has_keyword(self, parsed: ParsedInput, word: str) -> bool:
        return word.lower() in parsed.keywords or word.lower() in parsed.raw.lower()
