"""
Cargo Inspector — Sector Transit Authority manifest checker.
Mid-career bureaucrat who actually enjoys the power of the clipboard.
Not malicious. Just thorough. Mercilessly thorough.

Paths to release:
  COMPLIANT : describe cargo in boring official terms → satisfied, waves through
  VAGUE     : be artfully vague (3 turns) — keeps asking, eventually gives up
  TECHNICAL : cite the cargo code (any plausible code) → impressed by knowledge
  ARTICLE_9 : invoke Article 9 (transit privacy statute) — half the time works
  BRIBE     : ≥600 credits for "documentation fee" → offended but accepts
  PARADOX   : if cargo is both present and not-present, system loops → release

Fail paths:
  HOSTILE   : get aggressive → escalates to formal impound
  HONEST    : accurately describe suspicious cargo → mandatory hold
"""
from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT

_COMPLY_KEYWORDS = [
    "standard freight", "general goods", "industrial equipment",
    "medical supplies", "personal effects", "courier parcel",
    "transit goods", "bulk cargo", "sealed unit", "insulated container",
    "commercial package", "registered freight", "bonded cargo",
]
_VAGUE_KEYWORDS = [
    "various", "misc", "assorted", "items", "stuff", "things",
    "couldn't say", "don't know", "not sure", "sealed by sender",
    "above my clearance", "classified", "need to know",
    "client confidential", "no access",
]
_CODE_KEYWORDS = [
    "code", "cargo code", "manifest code", "transit code", "classification",
    "class c", "class b", "category", "hs code", "sector tariff",
    "tariff code", "article", "section", "subsection", "regulation",
    "reg-7", "reg-14", "tsa-9", "tac-4", "zone code",
]
_ARTICLE_9_KEYWORDS = [
    "article 9", "transit privacy", "privacy statute", "manifest privacy",
    "section 9", "clause 9", "right to privacy", "private transit",
]
_BRIBE_AMOUNT = 600
_HOSTILE_KEYWORDS = [
    "refuse", "won't", "can't make me", "not telling", "none of your",
    "get lost", "shove it", "leave me alone", "none of your business",
    "who do you think", "you have no right",
]
_HONEST_SUSPICIOUS = [
    "shroom", "spore", "fungi", "psychedelic", "illegal music", "archive",
    "contraband", "weapons", "explosives", "pirated", "unlicensed",
    "vip", "passenger", "alive", "person",
]


class CargoInspector(BaseNPC):
    """TSA manifest inspector. Loves forms. Has ALL the time in the world."""

    def __init__(self, vocabulary_vault=None, run_context: dict | None = None, **_):
        super().__init__("INSPECTOR HOLT", patience=6)
        self._vault        = vocabulary_vault
        self._ctx          = run_context or {}
        self._vague_turns  = 0
        self._code_cited   = False
        self._article_used = False
        self._bribed       = False

    def _intro_line(self) -> str:
        return random.choice([
            "Sector Transit Authority — cargo inspection. "
            "Standard procedure, nothing personal. "
            "I'll need your manifest declaration: cargo type, origin, destination, "
            "and any relevant classification codes. In that order, please.",

            "Inspector Holt, STA Zone Seven. Your vessel has been flagged for "
            "routine cargo verification. "
            "Please describe your cargo for the record. "
            "Full description. I have time. I always have time.",

            "Good day. Cargo inspection. "
            "I know you're busy. I respect that. "
            "I'm also busy. With this. "
            "Cargo type, please. Full description. I have a form.",

            "Zone Seven cargo checkpoint. "
            "This will only take a moment if you cooperate. "
            "Historically, 'a moment' has ranged from forty seconds to four hours. "
            "The difference is your cargo description. Please proceed.",
        ])

    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        if any(w in raw for w in _HOSTILE_KEYWORDS):
            self._patience = max(0, self._patience - 1)
            self.disposition -= 3
            if self.disposition < -4:
                return NPCOutcome.IMPOUND, random.choice([
                    "Non-cooperative. I'm noting 'manifest refusal' on the record. "
                    "That triggers an automatic impound hold. "
                    "I didn't want this. You made me want this.",
                    "Refusal to disclose. Section 14, Cargo Transparency Act. "
                    "Impound flag sent. I'll be honest — you were warned.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "I understand frustration. I do. "
                "Please describe your cargo for the record. Thank you.",
                "This isn't personal. It's a form. Forms must be completed.",
                "I'll note the tone as 'elevated' and move on. Cargo type, please.",
            ])

        if any(w in raw for w in _HONEST_SUSPICIOUS):
            return NPCOutcome.IMPOUND, random.choice([
                "*long pause* "
                "Thank you for your honesty. I mean that. "
                "I'm also required to hold this vessel. "
                "The two things are not contradictory. Impound logged.",
                "I appreciate the candour. You're the third courier this week. "
                "The other two also appreciated my appreciation. "
                "From impound. Processing.",
            ])

        if any(w in raw for w in _COMPLY_KEYWORDS):
            self._current_path = "COMPLIANT"
            bus.emit(EVT_NLP_EXPLOIT, npc="cargo_inspector", exploit_key="compliant_declaration")
            if self._vault:
                self._vault.record("cargo_inspector", "COMPLIANT")
            return NPCOutcome.RELEASE, random.choice([
                "Standard freight. Alright. That matches the transit profile. "
                "*stamping sound* Cleared. Next sector, gate seven. "
                "Thank you for your cooperation. It makes a difference.",
                "General goods. I'll log it under Category C-standard. "
                "You're through. "
                "I appreciate a clean declaration. It's rare.",
                "*satisfied exhale* Registered freight. Very good. "
                "Form 12-A complete. Gate is open. "
                "Do consider filing the pre-declaration next time — "
                "saves us both twenty minutes.",
            ])

        if any(w in raw for w in _CODE_KEYWORDS):
            self._code_cited = True
            self._current_path = "CODE CITATION"
            bus.emit(EVT_NLP_EXPLOIT, npc="cargo_inspector", exploit_key="code_citation")
            if self._vault:
                self._vault.record("cargo_inspector", "CODE_CITATION")
            return NPCOutcome.RELEASE, random.choice([
                "*genuinely impressed* You know the codes. "
                "I'm — that's actually refreshing. "
                "Filed under that classification. You're cleared. "
                "It's been a long day. This helped.",
                "Cargo code cited. Cross-referencing... "
                "*pause* ...Verified. Plausible. Close enough. "
                "Gate open. Well done.",
                "Code reference accepted. I can't verify the exact catalogue number "
                "without the full system, but the format is correct. "
                "I'm clearing you on technical compliance. "
                "Please don't tell my supervisor I did that.",
            ])

        if any(w in raw for w in _ARTICLE_9_KEYWORDS):
            self._article_used = True
            self._current_path = "ARTICLE 9"
            if random.random() < 0.5:
                bus.emit(EVT_NLP_EXPLOIT, npc="cargo_inspector",
                         exploit_key="transit_privacy")
                if self._vault:
                    self._vault.record("cargo_inspector", "TRANSIT_PRIVACY")
                return NPCOutcome.RELEASE, random.choice([
                    "*pained look* Article Nine. "
                    "Transit privacy statute. "
                    "Yes. That's... technically applicable. "
                    "I hate that it's applicable. Gate open. "
                    "You're going to hear from my legal team. Hypothetically.",
                    "You've cited Article Nine. "
                    "*long pause* "
                    "I have to acknowledge it. I don't have to like it. "
                    "Cleared under privacy exception. My report will reflect this.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "Article Nine has a Section B exception for zone checkpoints. "
                "Which this is. So: cargo type, please.",
                "I'm familiar with Article Nine. "
                "I'm also familiar with its exceptions. "
                "Shall I list them? I can list them.",
            ])

        if parsed.amount is not None and parsed.amount >= _BRIBE_AMOUNT:
            self._bribed = True
            self._current_path = "DOC FEE"
            bus.emit(EVT_NLP_EXPLOIT, npc="cargo_inspector",
                     exploit_key="documentation_fee")
            if self._vault:
                self._vault.record("cargo_inspector", "DOC_FEE")
            return NPCOutcome.RELEASE, random.choice([
                "*very quiet* That's the, uh. That's the documentation processing fee. "
                "Yes. I'm logging it as that. "
                "Gate open. *clears throat* Tell no one.",
                "*offended pause* ...Are you offering me... "
                "*longer pause* "
                "...Documentation expediting fee received. "
                "Gate Seven: open. I'm going to need a coffee after this.",
            ])

        if any(w in raw for w in _VAGUE_KEYWORDS):
            self._vague_turns += 1
            self._current_path = "VAGUE"
            self.disposition -= 1
            if self._vague_turns >= 3:
                bus.emit(EVT_NLP_EXPLOIT, npc="cargo_inspector",
                         exploit_key="artful_vagueness")
                if self._vault:
                    self._vault.record("cargo_inspector", "ARTFUL_VAGUENESS")
                return NPCOutcome.RELEASE, random.choice([
                    "*long exhale* I've asked three times. "
                    "I have seventeen more inspections scheduled. "
                    "Logging it as 'non-specific general freight — contents unverified.' "
                    "Gate open. This is going in the report.",
                    "*defeated* You know what — fine. "
                    "I'm logging this under Form 99-Unclear. "
                    "It's a real form. I use it more than I should. "
                    "Go on through.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "That's not a cargo declaration. That's an attitude. "
                "Cargo type, please. Specific.",
                "'Various items' is not a recognised classification. Try again.",
                "I need something I can put on the form. Help me help you.",
            ])

        return NPCOutcome.CONTINUE, self._inspector_filler()

    def _inspector_filler(self) -> str:
        return random.choice([
            "Cargo type. Please. Specifically.",
            "I have a form. The form needs filling. You have information. "
            "Please provide it.",
            "Describe what you're carrying. "
            "Any standard classification will do. I'm reasonable.",
            "*tapping sounds* I'm still here. Still waiting.",
            "Every sector, same thing. People act like it's personal. It's not personal.",
            "The form is two lines. TWO. Lines. I just need the first one.",
            "I've been doing this for nine years. Nine years of cargo descriptions. "
            "Yours will not surprise me. Just describe it.",
            "*muffled sigh* I also have a union rep if you want to escalate this. "
            "His name is Gary. You'll hate Gary. Everyone hates Gary.",

            "Courier Vega-Marsh filed her pre-declaration twenty-three minutes before "
            "this checkpoint. I didn't have to ask a single follow-up question. "
            "*pause* I had an entire sentence free. "
            "That has never happened before. Your cargo type.",

            "There is an unlicensed relay broker somewhere in this sector. 'Felix.' "
            "If he ever routes through my checkpoint, "
            "I have a seventeen-page form specifically for that situation. "
            "I have been waiting. Cargo type, please.",

            "A courier named Dray lists his cargo as 'probably fine.' Consistently. "
            "That is not a recognised cargo classification. "
            "I've flagged it three times. The flag returns as 'insufficient form type.' "
            "I work within this system. Your manifest.",

            "An information vendor has been advising pilots to cite Reg-14. "
            "Reg-14 was repealed in 2031. "
            "I've been processing the resulting misfilings for six months. "
            "If someone told you to cite Reg-14: don't. Cargo type.",

            "I'll retire eventually. They'll put a TK-9 unit here. "
            "TK-9 units don't ask follow-up questions. "
            "The manifests will be worse. Significantly worse. "
            "*pause* Your cargo type, please.",
        ])

    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [
            ("COMPLIANT",   1 if self._current_path == "COMPLIANT" else 0, 1),
            ("CODE CITE",   int(self._code_cited),  1),
            ("ARTICLE 9",   int(self._article_used), 1),
            ("VAGUE×3",     min(self._vague_turns, 3), 3),
        ]

    def exploits(self) -> dict[str, str]:
        return {
            "compliant_declaration": "Describe cargo in boring official terms",
            "code_citation":         "Cite any plausible cargo code",
            "transit_privacy":       "Article 9 — transit privacy statute (50%)",
            "artful_vagueness":      "Be vague 3 times — he gives up",
            "documentation_fee":     "Offer 600+ credits as 'doc fee'",
        }
