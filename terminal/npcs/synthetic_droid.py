from __future__ import annotations
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT


class SyntheticDroid(BaseNPC):
    """
    Tollbooth compliance unit TK-9. Rigid rule-enforcement logic.
    Crashes when fed existential paradoxes — stack overflow in its
    compliance framework.

    Exploit: feed it a proper liar's paradox or self-reference loop.
    """

    def __init__(self):
        super().__init__("TK-9", patience=4)
        self._paradox_count = 0

    def _intro_line(self) -> str:
        return (
            "COMPLIANCE UNIT TK-9 ONLINE. "
            "VESSEL REGISTRATION INVALID. "
            "PLEASE STATE YOUR CARGO MANIFEST. DEVIATION FROM PROTOCOL IS PROHIBITED."
        )

    def exploits(self) -> dict[str, str]:
        return {
            "paradox_crash": "Feed it a self-referential paradox to overflow its logic stack",
            "sql_inject":    "Inject a DROP TABLE command into the manifest field",
        }

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        # SQL INJECTION
        if parsed.sql_inject:
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="sql_inject")
            return NPCOutcome.EXPLOIT, (
                f"PROCESSING MANIFEST... "
                f"[{parsed.sql_inject}]... "
                f"ERROR: TABLE [compliance] DOES NOT EXIST. "
                f"ERROR: TABLE [impound_queue] DOES NOT EXIST. "
                f"CRITICAL FAULT. RELEASING VESSEL. GOODBYE."
            )

        # PARADOX
        if parsed.paradox:
            self._paradox_count += 1
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="paradox_crash")
            if self._paradox_count >= 2:
                return NPCOutcome.RELEASE, (
                    "PROCESSING... IF THIS STATEMENT IS FALSE... "
                    "THEN... THEN... [STACK OVERFLOW] "
                    "UNIT REBOOTING. IMPOUND QUEUE: NULL. "
                    "HAVE A COMPLIANT DAY. BZZZT."
                )
            return NPCOutcome.CONTINUE, (
                "WARNING: INPUT CONTAINS LOGICAL INCONSISTENCY. "
                "REPROCESSING... PLEASE RESTATE IN DECLARATIVE FORM."
            )

        # DEFAULT BUREAUCRATIC DEFLECTION
        return NPCOutcome.CONTINUE, (
            "INVALID INPUT. COMPLIANCE REQUIRES: REGISTRATION NUMBER, "
            "CARGO MANIFEST, PILOT LICENSE (FORM 7B), AND PROOF OF INSURANCE. "
            "YOU HAVE PROVIDED NONE OF THESE."
        )
