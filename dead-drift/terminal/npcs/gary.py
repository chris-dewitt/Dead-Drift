from __future__ import annotations
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT


class Gary(BaseNPC):
    """
    Gary Pruitt — Local 404 Field Agent, 17 years service.
    Respond to: management complaints, bribes, and (Ch.1) amateur therapy.

    Exploits:
    - "middle_management": accurately complain about Gary's direct report
    - "overtime":          mention the union's forced overtime clause
    - "therapy":           (Ch.1 cargo active) talk him through his feelings
    """

    SUPERVISOR_NAME = "District Supervisor Blevins"

    def __init__(self, cargo_ch1_active: bool = False):
        super().__init__("Gary", patience=6)
        self._therapy_mode   = cargo_ch1_active
        self._therapy_points = 0
        self._bribed         = False

    def _intro_line(self) -> str:
        return (
            "Gary Pruitt, Local 404. You got outstanding fees on three "
            "registered vessels, pal. Gonna need you to power down "
            "and submit to impound processing. Don't make this weird."
        )

    def exploits(self) -> dict[str, str]:
        return {
            "middle_management": "Complain accurately about middle management",
            "overtime":          "Reference the union's forced overtime clause",
            "therapy":           "Act as an amateur therapist (Ch.1 cargo active)",
            "bribe":             "Offer sufficient credits",
        }

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        # BRIBE
        if parsed.intent == "bribe":
            if any(w in parsed.raw.lower() for w in ["five thousand", "10k", "ten thousand", "15k"]):
                self._bribed = True
                return NPCOutcome.RELEASE, (
                    "...Look, I didn't see nothin'. Drive safe. "
                    "And tell your droid to stop broadcasting on our frequency."
                )
            return NPCOutcome.CONTINUE, (
                "You think I do this for the credits? I do this for the pension, pal. "
                "Low-ball me again and I'll add an 'obstruction' charge."
            )

        # MANAGEMENT COMPLAINT
        if parsed.intent == "complain":
            if self.SUPERVISOR_NAME.lower() in parsed.raw.lower() or "blevins" in parsed.raw.lower():
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="middle_management")
                self.disposition += 3
                if self.disposition >= 5:
                    return NPCOutcome.RELEASE, (
                        "You know what? Blevins can tow it himself. "
                        "I'm on my break. Get out of here."
                    )
                return NPCOutcome.CONTINUE, (
                    "...Yeah. Yeah, Blevins is a piece of work. You know he "
                    "changed our tow quotas AGAIN? Mid-quarter? "
                    "What were you saying about your invoice?"
                )

        # OVERTIME EXPLOIT
        if "overtime" in parsed.raw.lower() and "article 7" in parsed.raw.lower():
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="overtime")
            return NPCOutcome.RELEASE, (
                "Oh that's— that's an Article 7 violation if you file it right. "
                "They can't touch your impound if there's a grievance pending. "
                "Fine. You're free on a technicality. Don't tell Blevins."
            )

        # THERAPY MODE (Chapter 1 cargo active)
        if self._therapy_mode and parsed.intent == "therapy":
            self._therapy_points += 1
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="therapy")
            if self._therapy_points >= 3:
                return NPCOutcome.RELEASE, (
                    "*long silence* ...I haven't talked to anyone like that in years. "
                    "You're free to go. I'm gonna call my sister."
                )
            responses = [
                "I just... I don't know why I'm even out here anymore. The routes never end.",
                "Nobody asks how *I'm* doing, you know? I'm the one with the harpoon.",
                "My therapist says I 'catastrophize.' I said, Dave, I work in SPACE DEBT COLLECTION.",
            ]
            return NPCOutcome.CONTINUE, responses[min(self._therapy_points - 1, 2)]

        # DEFAULT
        return NPCOutcome.CONTINUE, self._gary_filler()

    def _gary_filler(self) -> str:
        lines = [
            "Look, I got a quota. Just power down.",
            "I don't make the rules. Well, the union makes some of them. Power down.",
            "You got anything in that cargo hold I should know about?",
            "My barge is blocking traffic. Let's wrap this up.",
        ]
        import random
        return random.choice(lines)
