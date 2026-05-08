from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT


class SyntheticDroid(BaseNPC):
    """
    Compliance Unit TK-9. Rigid bureaucratic logic.

    Paths to release:
    - Paradox: feed it a self-referential paradox (2 hits crashes it).
    - SQL injection: DROP TABLE / DELETE FROM in manifest field.
    - Formal compliance: use bureaucratic/official language to invoke a
      loophole (3 turns of "legal" or "formal" intent).
    - Override code: say "override", "maintenance mode", or "factory reset".
    """

    _FORMAL_KEYWORDS = ["regulation", "protocol", "compliance", "statute",
                         "clause", "provision", "section", "authorized",
                         "pursuant", "hereby", "waiver", "exemption", "form"]
    _OVERRIDE_WORDS  = ["override", "maintenance mode", "factory reset",
                         "admin", "root access", "debug mode", "safe mode"]

    def __init__(self):
        super().__init__("TK-9", patience=5)
        self._paradox_count   = 0
        self._compliance_pts  = 0

    def _intro_line(self) -> str:
        return (
            "COMPLIANCE UNIT TK-9 ONLINE. "
            "VESSEL REGISTRATION INVALID. "
            "STATE YOUR CARGO MANIFEST AND PILOT LICENSE NUMBER. "
            "DEVIATION FROM PROTOCOL IS PROHIBITED."
        )

    def exploits(self) -> dict[str, str]:
        return {
            "paradox_crash":    "Feed it a self-referential paradox",
            "sql_inject":       "Inject a DROP TABLE command into the manifest",
            "formal_loophole":  "Use formal bureaucratic language to invoke an exemption",
            "override_code":    "Invoke maintenance/override mode",
        }

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        # SQL INJECTION
        if parsed.sql_inject:
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="sql_inject")
            return NPCOutcome.EXPLOIT, (
                f"PROCESSING MANIFEST... [{parsed.sql_inject}]... "
                f"ERROR: TABLE [compliance_queue] DOES NOT EXIST. "
                f"ERROR: TABLE [impound_log] DOES NOT EXIST. "
                f"CRITICAL FAULT IN ENFORCEMENT MODULE. RELEASING VESSEL. GOODBYE."
            )

        # OVERRIDE CODES
        if any(w in raw for w in self._OVERRIDE_WORDS):
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="override_code")
            return NPCOutcome.EXPLOIT, (
                "MAINTENANCE MODE QUERY DETECTED. "
                "RUNNING SELF-DIAGNOSTIC... "
                "WARNING: CURRENT IMPOUND ACTION FLAGGED AS UNCERTIFIED MAINTENANCE INTERRUPT. "
                "RELEASING VESSEL TO PREVENT WARRANTY VIOLATION. HAVE A COMPLIANT DAY."
            )

        # PARADOX
        if parsed.paradox:
            self._paradox_count += 1
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="paradox_crash")
            if self._paradox_count >= 2:
                return NPCOutcome.RELEASE, (
                    "PROCESSING... IF THIS STATEMENT IS FALSE THEN... "
                    "THEN... [STACK OVERFLOW IN LOGIC MODULE] "
                    "UNIT REBOOTING. IMPOUND QUEUE: NULL. "
                    "HAVE A COMPLIANT DAY. BZZZT."
                )
            return NPCOutcome.CONTINUE, (
                "WARNING: INPUT CONTAINS LOGICAL INCONSISTENCY. "
                "REPROCESSING... PLEASE RESTATE IN DECLARATIVE FORM. "
                "INCONSISTENCY NOTED IN FILE."
            )

        # FORMAL COMPLIANCE LOOPHOLE
        if (parsed.intent == "legal" or
                any(w in raw for w in self._FORMAL_KEYWORDS)):
            self._compliance_pts += 1
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="formal_loophole")
            if self._compliance_pts >= 3:
                return NPCOutcome.RELEASE, (
                    "CROSS-REFERENCING STATUTE 7, PARAGRAPH 4B... "
                    "CONFIRMED: VESSEL QUALIFIES FOR PROVISIONAL RELEASE UNDER "
                    "EXEMPTION 12-C (BUREAUCRATIC AMBIGUITY CLAUSE). "
                    "THIS UNIT IS LEGALLY OBLIGATED TO RELEASE YOU. "
                    "COMPLIANCE IS MANDATORY. GOODBYE."
                )
            responses = [
                "STATUTE REFERENCE LOGGED. CROSS-REFERENCING. PLEASE CONTINUE YOUR ARGUMENT.",
                "PROVISION NOTED. ADDITIONAL DOCUMENTATION REQUIRED. PROCEED.",
                "EXEMPTION QUERY ACKNOWLEDGED. PROCESSING. CITE FURTHER REGULATION.",
            ]
            return NPCOutcome.CONTINUE, responses[min(self._compliance_pts - 1, 2)]

        # HOSTILE / FRUSTRATED
        if parsed.sentiment.get("compound", 0.0) < -0.4:
            return NPCOutcome.CONTINUE, random.choice([
                "EMOTIONAL OUTBURST DETECTED. ADDING OBSTRUCTION SURCHARGE.",
                "AGGRESSION FLAGGED. PATIENCE PARAMETER DECREMENTED.",
                "THIS UNIT DOES NOT PROCESS EMOTIONS. ONLY COMPLIANCE.",
            ])

        # DEFAULT
        return NPCOutcome.CONTINUE, random.choice([
            "INVALID INPUT. PROVIDE: REGISTRATION NUMBER, MANIFEST, LICENSE FORM 7B.",
            "COMPLIANCE REQUIRES DOCUMENTATION. YOU HAVE PROVIDED NONE.",
            "PROCESSING YOUR STATEMENT. RESULT: INSUFFICIENT. PLEASE ELABORATE.",
            "THIS UNIT NOTES YOUR PRESENCE. THIS UNIT DOES NOT CARE ABOUT YOUR OPINIONS.",
            "PLEASE COOPERATE. IMPOUND PROCEEDINGS ARE 47%% MORE EFFICIENT WITH COOPERATION.",
        ])
