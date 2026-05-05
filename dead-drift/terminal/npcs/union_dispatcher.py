from __future__ import annotations
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT


class UnionDispatcher(BaseNPC):
    """
    Chapter 4 final boss: the Union Dispatcher.

    Must be convinced that the ship technically doesn't exist,
    forcing a mathematical deletion of the debt.
    Requires vocabulary unlocked across all four chapters.
    """

    _REQUIRED_CONCEPTS = {
        "schrodinger", "observer", "collapse", "superposition",
        "vessel", "exist", "manifest", "quantum", "undefined", "null"
    }

    def __init__(self, vocabulary_vault):
        super().__init__("DISPATCHER", patience=8)
        self._vault         = vocabulary_vault
        self._concepts_used: set[str] = set()
        self._legal_points  = 0

    def _intro_line(self) -> str:
        return (
            "Union Dispatch, this is a final collections notice. "
            "You have outstanding debt across seventeen jurisdictions. "
            "Surrender your vessel or I will authorize full repossession. "
            "Every. Single. Part."
        )

    def exploits(self) -> dict[str, str]:
        return {
            "ontological_escape": (
                "Prove the ship doesn't exist using quantum superposition argument "
                "with full vocabulary chain — requires all four chapter concepts"
            )
        }

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        # Track which required concepts the player has used
        new_hits = self._required_concepts_in(parsed)
        self._concepts_used.update(new_hits)

        # Check for legal/contract arguments
        if parsed.intent == "legal":
            self._legal_points += 1

        # Full ontological escape: need all required concepts + legal framing
        if (len(self._concepts_used) >= len(self._REQUIRED_CONCEPTS) * 0.7
                and self._legal_points >= 2):
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="ontological_escape")
            return NPCOutcome.RELEASE, self._debt_deleted_monologue()

        # Partial progress
        if self._concepts_used:
            missing = self._REQUIRED_CONCEPTS - self._concepts_used
            return NPCOutcome.CONTINUE, (
                f"That's... an interesting argument. But you haven't addressed "
                f"the question of {next(iter(missing), 'existence')}. "
                f"The debt is still mathematically real until you prove otherwise."
            )

        return NPCOutcome.CONTINUE, (
            "I've heard every excuse in the book, pal. "
            "The debt is real. The tow barge is real. Your options are not."
        )

    def _required_concepts_in(self, parsed: ParsedInput) -> set[str]:
        tokens = set(parsed.tokens)
        # Also check vault backdoors
        vault_words = set(self._vault.get_all_terms())
        available = tokens | vault_words
        return self._REQUIRED_CONCEPTS & available

    def _debt_deleted_monologue(self) -> str:
        return (
            "*long silence* \n"
            "You... you're right. If the vessel's wave function never collapsed "
            "into a defined ownership state, then legally it was never registered. "
            "If it was never registered, the debt instrument is null. "
            "If the debt is null... *sound of a keyboard shattering* \n"
            "I'm going to need to take a personal day. "
            "DEBT RECORD: MATHEMATICALLY DELETED. "
            "Get out of my sector."
        )
