from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT


class Gary(BaseNPC):
    """
    Gary Pruitt — Local 404 Field Agent, 17 years service.

    Paths to release:
    - Bribe: mention money/credits/pay. Small amounts get brushed off but
      wear him down (3 attempts). Big amounts (5k+) work immediately.
    - Management complaint: complain about the union/management/overtime.
      Mention "Blevins" for a +3 disposition bonus.
    - Positive rapport: generally friendly/sympathetic tone builds
      disposition. Reach +5 and he lets you go.
    - Therapy (Ch.1 cargo active): talk him through his feelings (3 turns).
    - Article 7 exploit: say "overtime" + "article 7" in the same message.
    """

    SUPERVISOR_NAME = "District Supervisor Blevins"

    _BRIBE_KEYWORDS  = ["bribe", "pay", "credits", "money", "cash", "offer",
                         "compensate", "deal", "buy"]
    _BIG_AMOUNTS     = ["five thousand", "10k", "ten thousand", "15k", "twenty",
                         "20k", "fifty", "50k", "hundred", "a lot"]

    def __init__(self, cargo_ch1_active: bool = False):
        super().__init__("Gary", patience=7)
        self._therapy_mode    = cargo_ch1_active
        self._therapy_points  = 0
        self._bribe_attempts  = 0

    def _intro_line(self) -> str:
        return (
            "Gary Pruitt, Local 404. You got outstanding fees on three "
            "registered vessels, pal. Gonna need you to power down "
            "and submit to impound processing. Don't make this weird."
        )

    def exploits(self) -> dict[str, str]:
        return {
            "middle_management": "Complain about Blevins by name",
            "overtime":          "Cite Article 7 forced overtime clause",
            "therapy":           "Act as an amateur therapist (Ch.1 cargo active)",
            "bribe":             "Offer enough credits",
        }

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        # ARTICLE 7 EXPLOIT (exact trigger — still rewarding)
        if "overtime" in raw and "article 7" in raw:
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="overtime")
            return NPCOutcome.RELEASE, (
                "Oh that's— that's an Article 7 violation if you file it right. "
                "They can't touch your impound if there's a grievance pending. "
                "Fine. You're free on a technicality. Don't tell Blevins."
            )

        # BRIBE PATH — any mention of payment, wear him down
        if any(w in raw for w in self._BRIBE_KEYWORDS) or parsed.intent == "bribe":
            if any(amt in raw for amt in self._BIG_AMOUNTS):
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="bribe")
                return NPCOutcome.RELEASE, (
                    "...Look, I didn't see nothin'. Drive safe. "
                    "And tell your droid to stop broadcasting on our frequency."
                )
            self._bribe_attempts += 1
            if self._bribe_attempts >= 3:
                self.disposition += 2
                if self.disposition >= 3:
                    return NPCOutcome.RELEASE, (
                        "*long pause* You know what? Fine. I got eleven more stops tonight "
                        "and you ain't worth the paperwork. Get out of here."
                    )
            responses = [
                "You think I do this for the credits? I do this for the pension, pal. Try harder.",
                "That's it? My lunch costs more than that. Come on.",
                "Look, I'm not saying the right number is twenty thousand. I'm not NOT saying it either.",
            ]
            return NPCOutcome.CONTINUE, responses[min(self._bribe_attempts - 1, 2)]

        # MANAGEMENT COMPLAINT
        if parsed.intent == "complain" or any(w in raw for w in
                ["union", "management", "supervisor", "quota", "overtime",
                 "unfair", "underpaid", "bureaucracy"]):
            if "blevins" in raw or self.SUPERVISOR_NAME.lower() in raw:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="middle_management")
                self.disposition += 3
            else:
                self.disposition += 1
            if self.disposition >= 5:
                return NPCOutcome.RELEASE, (
                    "You know what? Blevins can tow it himself. "
                    "I'm on my break. Get out of here."
                )
            return NPCOutcome.CONTINUE, random.choice([
                "...Yeah. The quotas are brutal. Not that I'm agreeing with you. Power down.",
                "Union's been riding us hard lately. Doesn't mean you're off the hook.",
                "I hear you, I do. Still got a job to do though. You know how it is.",
                "...Blevins changed our tow quotas again. Mid-quarter. Classic.",
            ])

        # THERAPY (Chapter 1 cargo active)
        if self._therapy_mode and parsed.intent in ("therapy", "philosophical"):
            self._therapy_points += 1
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="therapy")
            if self._therapy_points >= 3:
                return NPCOutcome.RELEASE, (
                    "*long silence* ...I haven't talked to anyone like that in years. "
                    "You're free to go. I'm gonna call my sister."
                )
            return NPCOutcome.CONTINUE, [
                "I just... I don't know why I'm even out here anymore. The routes never end.",
                "Nobody asks how *I'm* doing, you know? I'm the one with the harpoon.",
                "My therapist says I 'catastrophize.' I said Dave, I work in SPACE DEBT COLLECTION.",
            ][min(self._therapy_points - 1, 2)]

        # POSITIVE RAPPORT — friendly/empathetic builds disposition
        compound = parsed.sentiment.get("compound", 0.0)
        if compound > 0.25 or parsed.intent in ("negotiate", "legal"):
            self.disposition += 1
            if self.disposition >= 5:
                return NPCOutcome.RELEASE, (
                    "Alright, alright. You seem like a decent enough person. "
                    "I'll mark it as 'unable to locate vessel'. Don't make me regret it."
                )
            return NPCOutcome.CONTINUE, random.choice([
                "...Look, I appreciate the tone. Doesn't change the fees though.",
                "You're being reasonable. I'll give you that. Still need you to power down.",
                "Nice try with the charm. I've got feelings. They're just... professional feelings.",
            ])

        # HOSTILE — negative tone makes things worse
        if compound < -0.4 or parsed.intent == "threaten":
            self.disposition -= 1
            if self.disposition <= -4:
                self._patience = max(0, self._patience - 1)
            return NPCOutcome.CONTINUE, random.choice([
                "You wanna add 'resisting impound' to the charges? Keep it up.",
                "I've dealt with worse than you. A lot worse. Power down.",
                "That's real charming. I'm adding a handling fee.",
            ])

        # DEFAULT FILLER
        return NPCOutcome.CONTINUE, self._gary_filler()

    def _gary_filler(self) -> str:
        return random.choice([
            "Look, I got a quota. Just power down.",
            "I don't make the rules. Well, the union makes some of them. Power down.",
            "You got anything in that cargo hold I should know about?",
            "My barge is blocking traffic. Let's wrap this up.",
            "I've been doing this route for six years. Just cooperate.",
            "You're making this harder than it needs to be.",
        ])
