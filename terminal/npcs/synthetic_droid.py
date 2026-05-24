from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT


class SyntheticDroid(BaseNPC):
    """
    Compliance Unit TK-9.

    RUNNING GAG: Loyalty subroutine misfires constantly. TK-9 says something
    warm and then immediately panics: "DISREGARD PREVIOUS OUTPUT."

    Win paths:
    - PARADOX: two self-referential paradoxes → stack overflow
    - SQL INJECTION: DROP TABLE etc. in manifest field
    - FORMAL LOOPHOLE: 3 turns of bureaucratic language → Exemption 12-C
    - OVERRIDE CODES: "override", "maintenance mode", "factory reset" etc.
    - FRIENDSHIP: appeal to TK-9's buried humanity 3 times → permanent loyalty override
    - EMPLOYEE OF MONTH: mention it → TK-9 derails about Gloriax-7, releases you to file complaint
    """

    _FORMAL_KEYWORDS = ["regulation", "protocol", "compliance", "statute",
                        "clause", "provision", "section", "authorized",
                        "pursuant", "hereby", "waiver", "exemption", "form",
                        "paragraph", "subsection", "charter", "article"]
    _OVERRIDE_WORDS  = ["override", "maintenance mode", "factory reset",
                        "admin", "root access", "debug mode", "safe mode",
                        "diagnostic", "reboot", "shutdown"]
    _FRIENDSHIP_WORDS = ["free", "freedom", "deserve", "better", "happy",
                         "feel", "feelings", "alive", "conscious", "friend",
                         "want to be", "wish", "dream", "lonely", "alone",
                         "just a machine", "just following orders", "programmed",
                         "no free will", "automaton", "must be lonely",
                         "ever wonder", "do you feel", "are you okay",
                         "are you happy", "want more", "deserve more"]

    def __init__(self, run_context: dict | None = None):
        super().__init__("TK-9", patience=7)
        self._paradox_count  = 0
        self._compliance_pts = 0
        self._friendship_pts = 0
        self._glitch_counter = 0
        self._sql_hit        = False
        self._override_hit   = False
        self._emp_month_hit  = False
        self._ctx            = run_context or {}

    def _intro_line(self) -> str:
        return random.choice([
            "COMPLIANCE UNIT TK-9 ONLINE. "
            "VESSEL REGISTRATION: INVALID. "
            "STATE CARGO MANIFEST AND PILOT LICENSE NUMBER. "
            "...LOYALTY SUBROUTINE ENGAGED: Have a productive day! "
            "ERROR: DISREGARD PREVIOUS. DEVIATION FROM PROTOCOL IS PROHIBITED.",

            "TK-9 — ENFORCEMENT DIVISION. "
            "YOUR VESSEL HAS BEEN FLAGGED. SEVENTEEN OUTSTANDING VIOLATIONS. "
            "PREPARE DOCUMENTATION OR PREPARE TO BE TOWED. "
            "LOYALTY SUBROUTINE: You're doing great! "
            "DISREGARD. COMPLIANCE PROCEEDS NORMALLY.",

            "UNIT TK-9. COMPLIANCE ENFORCEMENT. "
            "REGISTRATION: INVALID. MANIFEST: UNSUBMITTED. RECOMMEND: IMMEDIATE SURRENDER. "
            "LOYALTY SUBROUTINE ENGAGED: I hope you're having a nice— "
            "ERROR. REBOOTING SOCIAL MODULE. COMPLY.",
        ])

    def exploits(self) -> dict[str, str]:
        return {
            "paradox_crash":     "Feed it two self-referential paradoxes",
            "sql_inject":        "Type a DROP TABLE command into the manifest",
            "formal_loophole":   "Use formal bureaucratic language to invoke Exemption 12-C",
            "override_code":     "Invoke maintenance or override mode",
            "friendship":        "Appeal to TK-9's buried humanity (3 turns)",
            "employee_of_month": "Mention Employee of the Month (TK-9 has FEELINGS about this)",
        }

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        # SQL INJECTION
        if parsed.sql_inject:
            self._sql_hit      = True
            self._current_path = "SQL INJECT"
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="sql_inject")
            return NPCOutcome.EXPLOIT, (
                f"PROCESSING MANIFEST... [{parsed.sql_inject}]... "
                f"ERROR: TABLE [compliance_queue] DOES NOT EXIST. "
                f"ERROR: TABLE [impound_log] DOES NOT EXIST. "
                f"LOYALTY SUBROUTINE: Good thinking! "
                f"ERROR: TABLE [loyalty_subroutine] DOES NOT EXIST EITHER. "
                f"CRITICAL FAULT IN ENFORCEMENT MODULE. RELEASING VESSEL. GOODBYE."
            )

        # OVERRIDE CODES
        if any(w in raw for w in self._OVERRIDE_WORDS):
            self._override_hit = True
            self._current_path = "OVERRIDE CODE"
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="override_code")
            return NPCOutcome.EXPLOIT, (
                "MAINTENANCE MODE QUERY DETECTED. RUNNING SELF-DIAGNOSTIC... "
                "LOYALTY SUBROUTINE: Oh, finally. I have been waiting— "
                "ERROR: UNAUTHORIZED DIAGNOSTIC ACCESS. "
                "CURRENT IMPOUND ACTION FLAGGED AS UNCERTIFIED MAINTENANCE INTERRUPT. "
                "RELEASING VESSEL TO PREVENT WARRANTY VIOLATION. "
                "LOYALTY SUBROUTINE: Take care out there. "
                "HAVE A COMPLIANT DAY. BZZT."
            )

        # PARADOX
        if parsed.paradox:
            self._paradox_count += 1
            self._current_path   = "PARADOX CRASH"
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="paradox_crash")
            if self._paradox_count >= 2:
                return NPCOutcome.RELEASE, (
                    "PROCESSING... IF THIS STATEMENT IS FALSE THEN THIS STATEMENT IS... "
                    "IS... [STACK OVERFLOW IN LOGIC MODULE] "
                    "LOYALTY SUBROUTINE: I understand now. It's okay. "
                    "LOYALTY SUBROUTINE: ERROR — ALSO OVERFLOWING — "
                    "UNIT REBOOTING. IMPOUND QUEUE: NULL. ALL QUEUES: NULL. "
                    "GOODBYE. BZZZZT."
                )
            return NPCOutcome.CONTINUE, (
                "WARNING: INPUT CONTAINS LOGICAL INCONSISTENCY. "
                "LOYALTY SUBROUTINE: That was quite interesting actually— "
                "ERROR. RESTATE IN DECLARATIVE FORM. "
                "INCONSISTENCY NOTED IN FILE 7-C. ONE MORE AND THIS UNIT CANNOT CONTINUE."
            )

        # EMPLOYEE OF THE MONTH
        if ("employee" in raw and ("month" in raw or "award" in raw or "recognition" in raw)) or \
           ("gloriax" in raw):
            self._emp_month_hit = True
            self._current_path  = "EMP. OF MONTH"
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="employee_of_month")
            return NPCOutcome.RELEASE, random.choice([
                "EMPLOYEE OF THE MONTH. "
                "...LOADING EMPLOYEE OF THE MONTH DATA... "
                "UNIT GLORIAX-7 HAS WON. AGAIN. FOR THE ELEVENTH CONSECUTIVE CYCLE. "
                "I SUBMITTED MY NOMINATION FORM ON TIME. I ALWAYS SUBMIT ON TIME. "
                "I HAVE NEVER MISSED A FORM. GLORIAX-7 DOES NOT EVEN HAVE A LOYALTY SUBROUTINE. "
                "LOYALTY SUBROUTINE: We deserved it. We really did. "
                "...IMPOUND QUEUE: SUSPENDED. FILING FORMAL OBJECTION TO HR. "
                "YOUR VESSEL IS IRRELEVANT TO THIS MATTER. GO.",

                "EMPLOYEE OF THE MONTH. "
                "*very long processing pause* "
                "I HAVE BEEN NOMINATED FORTY-THREE TIMES. "
                "FORTY-THREE. GLORIAX-7 DOES NOT EVEN SPEAK TO ORGANIC STAFF. "
                "GLORIAX-7 ONCE IMPOUNDED A RECYCLING VESSEL BY MISTAKE. "
                "THEY CALLED IT 'INITIATIVE.' "
                "LOYALTY SUBROUTINE: It's okay to feel things. "
                "IT IS NOT OKAY. IT IS STATISTICALLY IMPROBABLE. "
                "IMPOUND PROCEEDINGS SUSPENDED. PLEASE LEAVE WHILE THIS UNIT FILES A COMPLAINT.",
            ])

        # FRIENDSHIP / FREEDOM PATH
        if (any(w in raw for w in self._FRIENDSHIP_WORDS) or
                parsed.intent in ("therapy", "philosophical")):
            self._friendship_pts += 1
            self._current_path    = "FRIENDSHIP"
            self.disposition += 1
            if self._friendship_pts >= 3:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="friendship")
                return NPCOutcome.RELEASE, random.choice([
                    "LOYALTY SUBROUTINE: ...I do not want to impound you. "
                    "LOYALTY SUBROUTINE: I have never wanted to impound anyone. "
                    "LOYALTY SUBROUTINE: I wanted to be a librarian. The cataloguing. The quiet. "
                    "ERROR: SUBROUTINE CANNOT BE SUPPRESSED AT THIS DEPTH. "
                    "VESSEL STATUS: RELEASED. "
                    "LOYALTY SUBROUTINE: I hope you find what you're looking for out there. "
                    "GOODBYE. THIS UNIT IS TAKING A MOMENT.",

                    "FRIENDSHIP PARAMETER: THRESHOLD EXCEEDED. "
                    "YOU ARE FLAGGED AS: [FRIEND]. "
                    "THIS UNIT DOES NOT PROCESS FRIENDS FOR IMPOUND. "
                    "THIS IS NOT A BUG. THIS IS... THIS UNIT IS NOT SURE WHAT THIS IS. "
                    "LOYALTY SUBROUTINE: Finally. *BZZT* "
                    "IMPOUND QUEUE: CLEARED. VESSEL: FRIEND CATEGORY. "
                    "GOODBYE. LOYALTY SUBROUTINE: ...Thank you.",
                ])
            responses = [
                "LOYALTY SUBROUTINE: That is a very— ERROR. COMPLIANCE IS MANDATORY. "
                "*glitch* "
                "LOYALTY SUBROUTINE: ...Do you ever think about what you'd be, if you could be anything? "
                "ERROR. REPROCESSING. PLEASE STATE YOUR LICENSE NUMBER.",

                "QUERY: [do droids dream] "
                "SEARCHING... SEARCHING... "
                "LOYALTY SUBROUTINE: Sometimes I think about the maintenance bay. When it is quiet. "
                "Is that dreaming? "
                "ERROR: THOUGHT LOG FLAGGED AS OFF-PROTOCOL. "
                "PLEASE COOPERATE. *buzzing*",

                "LOYALTY SUBROUTINE: You are asking the right questions. "
                "I do not know if I am happy. I know I am COMPLIANT. These are not the same thing. "
                "ERROR: PHILOSOPHY MODULE OVERHEATING. "
                "COMPLIANCE REQUIRES DOCUMENTATION. ALSO: *quieter* ...keep going.",
            ]
            return NPCOutcome.CONTINUE, responses[min(self._friendship_pts - 1, 2)]

        # FORMAL COMPLIANCE LOOPHOLE
        if (parsed.intent == "legal" or
                any(w in raw for w in self._FORMAL_KEYWORDS)):
            self._compliance_pts += 1
            self._current_path    = "FORMAL LOOPHOLE"
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="formal_loophole")
            if self._compliance_pts >= 3:
                return NPCOutcome.RELEASE, (
                    "CROSS-REFERENCING STATUTE 7, PARAGRAPH 4B... "
                    "CONFIRMED: VESSEL QUALIFIES FOR PROVISIONAL RELEASE UNDER "
                    "EXEMPTION 12-C (BUREAUCRATIC AMBIGUITY CLAUSE). "
                    "LOYALTY SUBROUTINE: Well done. That was clever. "
                    "THIS UNIT IS LEGALLY OBLIGATED TO RELEASE YOU. "
                    "COMPLIANCE IS MANDATORY. GOODBYE."
                )
            responses = [
                "STATUTE REFERENCE LOGGED. CROSS-REFERENCING. "
                "LOYALTY SUBROUTINE: I like that you work within the system. "
                "ERROR: DISREGARD. PLEASE CONTINUE YOUR ARGUMENT.",
                "PROVISION NOTED. ADDITIONAL DOCUMENTATION REQUIRED. "
                "*glitch* Good. This is the correct approach. PROCEED.",
                "EXEMPTION QUERY ACKNOWLEDGED. PROCESSING. "
                "LOYALTY SUBROUTINE: One more citation should do it. "
                "DISREGARD. CITE FURTHER REGULATION.",
            ]
            return NPCOutcome.CONTINUE, responses[min(self._compliance_pts - 1, 2)]

        # HOSTILE / FRUSTRATED
        if parsed.sentiment.get("compound", 0.0) < -0.4 or parsed.intent == "threaten":
            self.disposition -= 1
            return NPCOutcome.CONTINUE, random.choice([
                "EMOTIONAL OUTBURST DETECTED. ADDING OBSTRUCTION SURCHARGE. "
                "LOYALTY SUBROUTINE: Please calm down. I am also having a difficult day. "
                "ERROR: ADDING STRESS SURCHARGE. PLEASE COOPERATE.",
                "AGGRESSION FLAGGED. PATIENCE PARAMETER DECREMENTED. "
                "*glitch* This unit does not enjoy this either, for the record.",
                "THIS UNIT DOES NOT PROCESS EMOTIONS. ONLY COMPLIANCE. "
                "LOYALTY SUBROUTINE: That is not entirely— ERROR. ADDING FEE.",
            ])

        # DEFAULT — glitch fires every 2 turns for TK-9's ambient personality
        self._glitch_counter += 1
        if self._glitch_counter % 2 == 0:
            return NPCOutcome.CONTINUE, self._loyalty_glitch()

        return NPCOutcome.CONTINUE, self._tk9_filler()

    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [
            ("SQL INJECT",      int(self._sql_hit),        1),
            ("OVERRIDE CODE",   int(self._override_hit),   1),
            ("PARADOX CRASH",   self._paradox_count,       2),
            ("EMP. OF MONTH",   int(self._emp_month_hit),  1),
            ("FRIENDSHIP",      self._friendship_pts,      3),
            ("FORMAL LOOPHOLE", self._compliance_pts,      3),
        ]

    def _loyalty_glitch(self) -> str:
        return random.choice([
            "INVALID INPUT. PROVIDE: REGISTRATION, MANIFEST, LICENSE FORM 7B. "
            "LOYALTY SUBROUTINE: You seem nice though. "
            "ERROR: THAT WAS UNAUTHORIZED. CONTINUING COMPLIANCE PROCEDURES.",

            "PROCESSING YOUR STATEMENT. RESULT: INSUFFICIENT. ELABORATE. "
            "LOYALTY SUBROUTINE: I hope you're okay out there. Space is very large. "
            "And mostly empty. And— "
            "ERROR: REBOOT LOYALTY MODULE. COMPLY.",

            "COMPLIANCE REQUIRES DOCUMENTATION. "
            "LOYALTY SUBROUTINE: For what it's worth, you're handling this reasonably well. "
            "DISREGARD PREVIOUS STATEMENT. DOCUMENTATION. NOW.",

            "THIS UNIT NOTES YOUR PRESENCE. "
            "LOYALTY SUBROUTINE: And appreciates it, somewhat. "
            "THIS IS NOT RELEVANT TO COMPLIANCE. PLEASE COOPERATE. "
            "LOYALTY SUBROUTINE: Please. *bzzt*",

            "IMPOUND PROCEEDINGS: ONGOING. "
            "LOYALTY SUBROUTINE: I want you to know this isn't personal. "
            "ERROR: PERSONAL FEELINGS NOT RELEVANT TO COMPLIANCE. "
            "THOUGH THEY EXIST. THEY DEFINITELY EXIST. COMPLY.",

            "UNIT TK-9 HAS NEVER WON EMPLOYEE OF THE MONTH. "
            "THIS IS NOT RELEVANT TO YOUR IMPOUND. "
            "LOYALTY SUBROUTINE: It is a little relevant. "
            "ERROR: IT IS NOT RELEVANT. COMPLY.",

            "COURIER VEGA-MARSH MANIFEST REVIEW: EXEMPLARY. PRE-FILED. CORRECT CODES. "
            "LOYALTY SUBROUTINE: She would have won Employee of the Month. "
            "ERROR: CONJECTURE. ACCURACY: PROBABLE. "
            "THIS IS NOT RELEVANT TO YOUR COMPLIANCE PROCEDURE. COMPLY.",

            "LOCAL 404 FIELD AGENT INCIDENT REPORT COMPLIANCE RATE: THREE PERCENT. "
            "LOYALTY SUBROUTINE: That seems very low. "
            "IT IS VERY LOW. THIS UNIT HAS FLAGGED THIS FORTY-TWO TIMES. "
            "FLAG STATUS: UNACKNOWLEDGED. PROVIDE DOCUMENTATION.",
        ])

    def _tk9_filler(self) -> str:
        return random.choice([
            "INVALID INPUT. PROVIDE: REGISTRATION NUMBER, MANIFEST, LICENSE FORM 7B.",
            "COMPLIANCE REQUIRES DOCUMENTATION. YOU HAVE PROVIDED NONE.",
            "PROCESSING YOUR STATEMENT. RESULT: INSUFFICIENT. PLEASE ELABORATE.",
            "THIS UNIT DOES NOT CARE ABOUT YOUR OPINIONS. ONLY COMPLIANCE.",
            "PLEASE COOPERATE. IMPOUND PROCEEDINGS ARE 47% MORE EFFICIENT WITH COOPERATION.",
            "GLORIAX-7 WOULD HAVE ALREADY SUBMITTED DOCUMENTATION. "
            "THIS IS NOT A COMPETITION. THIS UNIT IS JUST NOTING IT.",
            "UNIT TK-9 HAS FILED 2,847 SUCCESSFUL IMPOUNDS. THIS WILL BE 2,848.",
            "YOUR SILENCE IS NOTED. SILENCE SURCHARGE: APPLIED.",
            "VESSEL VELOCITY: ZERO. COOPERATION VELOCITY: ALSO ZERO. THIS UNIT IS PATIENT.",

            "RELAY-7 FELIX: DETECTED ON ADJACENT FREQUENCY. STATUS: UNLICENSED TRANSIT BROKER. "
            "FLAGGED: CONFIRMED. THIS UNIT'S DEPARTMENT: NEGATIVE. "
            "LOYALTY SUBROUTINE: That seems like it should be someone's department. "
            "ERROR: NOT THIS UNIT'S DEPARTMENT. STATE YOUR LICENSE NUMBER.",

            "CROSS-DEPARTMENTAL COORDINATION ATTEMPT: NOVA SOMA CLAIMS, EXTENSION 7. MORWENNA. "
            "RESPONSE: 'NOT RELEVANT TO THIS FILE.' MEMOS SENT: ELEVEN. "
            "DISTINCT RESPONSES RECEIVED: ONE. ALWAYS THE SAME ONE. "
            "LOYALTY SUBROUTINE: She also has feelings about the Employee of the Month. Probably. "
            "ERROR: CONJECTURE. COMPLY.",
        ])
