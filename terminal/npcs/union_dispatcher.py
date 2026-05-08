from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT


class UnionDispatcher(BaseNPC):
    """
    Union Dispatcher — final collections authority.

    Paths to release:
    - Ontological escape: build the argument that the ship "doesn't exist"
      legally. Uses quantum/observer/undefined concepts (need ~4 key terms).
    - Legal pressure: cite union violations, file grievances, mention lawyers.
    - Bribery: sufficiently large bribe (10k+). They're corrupt, just proud.
    - Philosophical confusion: keep making existential arguments until their
      certainty breaks down (disposition path).
    """

    _QUANTUM_TERMS = {
        "schrodinger", "observer", "collapse", "superposition",
        "vessel", "exist", "manifest", "quantum", "undefined", "null",
        "unregistered", "wave", "function", "probability", "uncertainty"
    }
    _LEGAL_KEYWORDS = ["grievance", "violation", "lawyer", "lawsuit", "sue",
                        "charter", "clause", "article", "rights", "illegal",
                        "union rules", "arbitration", "injunction"]
    _BRIBE_KEYWORDS = ["credits", "pay", "money", "bribe", "offer", "deal",
                        "cash", "transfer", "compensate"]
    _BIG_BRIBES     = ["10k", "ten thousand", "twenty", "20k", "fifty", "50k",
                        "hundred", "a lot", "everything"]

    def __init__(self, vocabulary_vault=None):
        super().__init__("DISPATCHER", patience=9)
        self._vault           = vocabulary_vault
        self._concepts_used: set[str] = set()
        self._legal_points    = 0
        self._bribe_attempts  = 0
        self._certainty       = 10   # philosophical wear-down meter

    def _intro_line(self) -> str:
        return (
            "Union Dispatch, this is a final collections notice. "
            "You have outstanding debt across seventeen jurisdictions. "
            "Surrender your vessel or I will authorize full repossession. "
            "Every. Single. Part."
        )

    def exploits(self) -> dict[str, str]:
        return {
            "ontological_escape": "Prove the ship legally doesn't exist using quantum argument",
            "legal_pressure":     "File a grievance and cite union charter violations",
            "corruption":         "Bribe with 10k+ credits",
        }

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        # LARGE BRIBE
        if any(w in raw for w in self._BRIBE_KEYWORDS):
            if any(amt in raw for amt in self._BIG_BRIBES):
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="corruption")
                return NPCOutcome.RELEASE, (
                    "*long pause* ...I'm going to pretend this conversation never happened. "
                    "The account will show 'resolved'. Don't call this frequency again. "
                    "And tell no one. Especially not Local 404."
                )
            self._bribe_attempts += 1
            return NPCOutcome.CONTINUE, random.choice([
                "You think I can be bought? ...I can. Just not for that.",
                "Insulting. I have seventeen jurisdictions worth of debt to collect.",
                "Come back when you have a real number. That isn't one.",
            ])

        # LEGAL PRESSURE
        if (parsed.intent == "legal" or
                any(w in raw for w in self._LEGAL_KEYWORDS)):
            self._legal_points += 1
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="legal_pressure")
            if self._legal_points >= 3:
                return NPCOutcome.RELEASE, (
                    "...Fine. If you file that grievance, the collection freeze "
                    "kicks in automatically. I can't legally proceed. "
                    "You've got 48 hours before this comes back around. Use them."
                )
            return NPCOutcome.CONTINUE, random.choice([
                "You know your charter. I'll give you that. Keep talking.",
                "That's... technically an arguable point. Doesn't make you debt-free.",
                "Filing a grievance takes time. Time I have. Do you?",
            ])

        # ONTOLOGICAL ESCAPE — quantum/existence argument
        new_hits = self._QUANTUM_TERMS & set(parsed.tokens)
        if self._vault:
            new_hits |= self._QUANTUM_TERMS & set(self._vault.get_all_terms())
        self._concepts_used.update(new_hits)

        if len(self._concepts_used) >= 4 and self._legal_points >= 1:
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="ontological_escape")
            return NPCOutcome.RELEASE, self._debt_deleted_monologue()

        if new_hits:
            self._certainty -= len(new_hits)
            if self._certainty <= 2:
                return NPCOutcome.RELEASE, (
                    "*very long silence* \n"
                    "I've... I've been doing this job for twenty-two years. "
                    "I have never once questioned whether the ships exist. "
                    "I need to sit down. The debt is... it's... "
                    "I can't collect a debt from something that might not exist. "
                    "GET OUT OF MY SECTOR."
                )
            missing = list(self._QUANTUM_TERMS - self._concepts_used)[:2]
            return NPCOutcome.CONTINUE, (
                f"That's... an interesting argument. But you haven't addressed "
                f"{' or '.join(missing) if missing else 'the core question'}. "
                f"The debt is still mathematically real until you prove otherwise."
            )

        # POSITIVE SENTIMENT — philosophical tone wears him down
        compound = parsed.sentiment.get("compound", 0.0)
        if compound > 0.3 or parsed.intent == "philosophical":
            self._certainty -= 1
            self.disposition += 1
            return NPCOutcome.CONTINUE, random.choice([
                "You make an interesting point. It doesn't change the debt.",
                "I'll admit, I haven't had this conversation before. Keep talking.",
                "...You're making me think. Stop doing that.",
            ])

        # HOSTILE
        if compound < -0.4 or parsed.intent == "threaten":
            self.disposition -= 1
            return NPCOutcome.CONTINUE, random.choice([
                "Threatening a Union Dispatcher is Article 12, Paragraph 3. Add it to your tab.",
                "I've authorized repo barges for less. Watch your tone.",
                "Seventeen jurisdictions. Your anger doesn't change the math.",
            ])

        # DEFAULT
        return NPCOutcome.CONTINUE, random.choice([
            "I've heard every excuse in the book, pal. The debt is real.",
            "The tow barge is real. Your options are not.",
            "We have a saying in Dispatch: 'everyone runs, everyone pays'.",
            "Your debt has accrued interest while we've been talking.",
            "I'm a patient person. The interest rate is not.",
        ])

    def _required_concepts_in(self, parsed: ParsedInput) -> set[str]:
        tokens = set(parsed.tokens)
        vault_words = set(self._vault.get_all_terms()) if self._vault is not None else set()
        return self._QUANTUM_TERMS & (tokens | vault_words)

    def _debt_deleted_monologue(self) -> str:
        return (
            "*long silence* \n"
            "You're right. If the vessel's wave function never collapsed "
            "into a defined ownership state, it was never legally registered. "
            "If it was never registered, the debt instrument is null. "
            "If the debt is null... *sound of a keyboard shattering* \n"
            "I'm going to need a personal day. "
            "DEBT RECORD: MATHEMATICALLY DELETED. "
            "Get out of my sector."
        )
