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


# ---------------------------------------------------------------------------
# Credit amount extraction
# ---------------------------------------------------------------------------

_WORD_NUMS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "hundred": 100,
}

def extract_credit_amount(text: str) -> int | None:
    """
    Pull a credit amount from natural language input.
    Handles: '5000', '5k', 'five grand', 'ten thousand credits', etc.
    """
    lower = text.lower()
    # '5k' / '10k' style
    m = re.search(r'\b(\d+)\s*k\b', lower)
    if m:
        return int(m.group(1)) * 1000
    # Raw digits 3–7 digits (skip Local 404 union designation)
    for m in re.finditer(r'\b(\d{3,7})\b', lower):
        val = int(m.group(1))
        if val == 404 and re.search(r'local\s*404', lower):
            continue
        return val
    # 'fifteen hundred' / 'five hundred' style (before bare 'five' -> 5000 heuristic)
    if "hundred" in lower and "thousand" not in lower:
        for word, val in _WORD_NUMS.items():
            if re.search(rf"\b{re.escape(word)}\b", lower):
                return val * 100
    # 'five thousand' / 'twenty grand' style
    for word, val in _WORD_NUMS.items():
        if re.search(rf"\b{re.escape(word)}\b", lower):
            if "thousand" in lower or "grand" in lower or "k" in lower:
                return val * 1000
            if val >= 5:
                return val * 1000
    return None


@dataclass
class ParsedInput:
    raw:        str
    tokens:     list[str]
    pos_tags:   list[tuple[str, str]]
    keywords:   list[str]
    sentiment:  dict
    intent:     str
    paradox:    bool = False
    sql_inject: str | None = None
    amount:     int | None = None      # detected credit amount


# ---------------------------------------------------------------------------
# Intent patterns
# NOTE: "union" intentionally removed from sql — players legitimately complain
# about the Union and it was misclassifying their messages.
# ---------------------------------------------------------------------------

_INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("bribe",         ["bribe", "credits", "pay", "money", "compensate", "offer",
                       "cash", "fund", "buy", "transfer"]),
    ("complain",      ["management", "union", "boss", "overtime", "underpaid",
                       "bureaucracy", "paperwork", "quota", "unfair", "corrupt"]),
    ("sympathy",      ["desperate", "please", "family", "kids", "children",
                       "survive", "struggling", "help", "dying", "last", "need",
                       "sorry", "apolog", "rough", "hard time", "begging"]),
    ("therapy",       ["feel", "feelings", "sad", "depressed", "lonely", "why",
                       "meaning", "purpose", "okay", "alright"]),
    ("paradox",       ["exist", "real", "not real", "if this statement",
                       "liar", "contradiction", "undefined", "cannot"]),
    ("legal",         ["contract", "clause", "article", "legal", "void", "null",
                       "statute", "rights", "regulation", "provision", "exempt"]),
    ("sql",           ["drop table", "select from", "insert into", "delete from",
                       "truncate", "commit", "where clause"]),   # full phrases only
    ("negotiate",     ["deal", "trade", "compromise", "terms", "offer",
                       "negotiate", "settlement", "reduction", "discount",
                       "percent", "waive", "reduce"]),
    ("threaten",      ["destroy", "report", "lawyer", "sue", "complaint", "file",
                       "expose", "record", "evidence"]),
    ("philosophical", ["consciousness", "free will", "determinism", "god",
                       "purpose", "void", "entropy", "existence"]),
]

_SQL_PATTERN = re.compile(
    r"(?:^|\b)(DROP\s+TABLE|SELECT\s+[\*\w]|DELETE\s+FROM|INSERT\s+INTO|UPDATE\s+\w+\s+SET|TRUNCATE)(?=[\s;.,)]|$).*",
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
    "this is a lie",
    "if this is true it is false",
    "nothing is real",
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
      6. Credit amount extraction
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
        amount      = extract_credit_amount(text)

        return ParsedInput(
            raw        = text,
            tokens     = tokens,
            pos_tags   = tags,
            keywords   = keywords,
            sentiment  = sentiment,
            intent     = intent,
            paradox    = paradox,
            sql_inject = sql_cmd,
            amount     = amount,
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
