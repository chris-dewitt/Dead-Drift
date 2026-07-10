"""
CHEN — former lead architect of the galactic debt ledger.

She wrote the cage. Then she walked into the belt and never came back.
The Remnants protect her. Marrow routes for her. She made the virus.

This NPC fires during Chapter 5 — when the Remnants vet you before
handing over the drive. There is no losing this interrogation. The
question is *how* the player gets the drive: respectfully, transactionally,
or with the kind of guilt that makes Chen quietly hand it over.
"""
from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput

_RESPECT_KEYWORDS = [
    "thank", "thanks", "honour", "honor", "respect", "grateful",
    "appreciate", "owe you", "owe", "indebted", "no idea", "wow",
    "incredible", "couldn't believe", "amazing what you",
]
_GUILT_KEYWORDS = [
    "the ledger", "your design", "you made", "you built", "you wrote",
    "your code", "your fault", "complicit", "you helped", "you let it",
    "you knew", "for years", "all these years",
]
_PURPOSE_KEYWORDS = [
    "everyone", "all of them", "wipe it", "wipe everyone", "free them",
    "clear it", "burn it down", "burn it", "no more debt", "everyone free",
    "the whole thing", "all of us", "all of it", "for everyone",
]
_QUESTION_KEYWORDS = [
    "why", "why now", "why us", "why me", "how does it work",
    "what does it do", "what is it", "how", "are you sure",
    "is it safe", "what happens", "what then",
]


class Chen(BaseNPC):
    """The Remnants' architect. Hands over the drive."""

    def __init__(self, run_context: dict | None = None, **_):
        super().__init__("Chen", patience=10)
        self._respect_turns = 0
        self._guilt_turns   = 0
        self._purpose_turns = 0
        self._asked         = 0
        self._ctx = run_context or {}

    def _intro_line(self) -> str:
        return random.choice([
            "Chen. They told you I'd be here. I assume you brought the cipher Marrow sent. Good. "
            "I have a drive. It does one thing. You can ask me about it — or you can take it and run.",
            "You came farther than most. Sit. I won't waste your time. The drive's already in your hold. "
            "I want to know who I just handed it to.",
            "I designed the system you've been bleeding under for fifteen years. "
            "I want you to know that before I give you the way out of it.",
        ])

    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        text = parsed.raw.lower()

        if any(k in text for k in _RESPECT_KEYWORDS):
            self._respect_turns += 1
            self._current_path = "RESPECT"
            if self._respect_turns >= 2:
                return NPCOutcome.RELEASE, (
                    "Don't thank me. I'm balancing a ledger that doesn't show on the books. "
                    "Drive's yours. The slot at Nova Soma is on floor twelve. "
                    "When you plug it in, hold the line for ninety seconds. That's all I ask."
                )
            return NPCOutcome.CONTINUE, (
                "You're polite. Most aren't. I'll take it. Tell me — what'll you do "
                "after the debt is gone?"
            )

        if any(k in text for k in _GUILT_KEYWORDS):
            self._guilt_turns += 1
            self._current_path = "ACKNOWLEDGE"
            if self._guilt_turns >= 2:
                return NPCOutcome.RELEASE, (
                    "Yes. I built it. I am the reason. I won't pretend otherwise. "
                    "Take the drive. The slot is on floor twelve. Don't die getting there."
                )
            return NPCOutcome.CONTINUE, (
                "You're right. I'm not going to argue. Keep going."
            )

        if any(k in text for k in _PURPOSE_KEYWORDS):
            self._purpose_turns += 1
            self._current_path = "FOR EVERYONE"
            if self._purpose_turns >= 1:
                return NPCOutcome.RELEASE, (
                    "Everyone. Every single ledger entry, galactic. Not just yours. "
                    "That's what the drive does. Plug it in. Hold for ninety seconds. "
                    "Run like you mean it."
                )
            return NPCOutcome.CONTINUE, (
                "Good answer. Go on."
            )

        if any(k in text for k in _QUESTION_KEYWORDS):
            self._asked += 1
            self._current_path = "QUESTION"
            if self._asked == 1:
                return NPCOutcome.CONTINUE, (
                    "I wrote every line of that ledger. I know exactly where the door is. "
                    "The drive injects a cascade write at root level — it doesn't delete "
                    "debt, it *zeroes the field across the whole table*. Anything else?"
                )
            if self._asked >= 2:
                return NPCOutcome.RELEASE, (
                    "Then you know enough. Drive's already aboard. Floor twelve. "
                    "Ninety seconds. Don't hesitate at the blast doors."
                )

        # Default: drift toward release after enough exchanges
        if self._turn >= 4:
            return NPCOutcome.RELEASE, (
                "Enough talk. The drive's in your hold. Floor twelve. Don't die."
            )
        return NPCOutcome.CONTINUE, random.choice([
            "Mm. Keep talking.",
            "I'm listening. Make it count.",
            "Say more.",
        ])

    def exploits(self) -> dict[str, str]:
        return {
            "RESPECT":         "Thank her — she'll explain the path quietly",
            "ACKNOWLEDGE":     "Name what she built — she releases under the weight",
            "FOR EVERYONE":    "Frame the goal as universal — she signs off fast",
            "QUESTION":        "Ask how the virus works — she'll teach you, then send you",
        }

    def get_path_progress(self) -> list[tuple[str, str, int, int]]:
        return [
            ("RESPECT",      "thank · honour · grateful",            self._respect_turns, 2),
            ("ACKNOWLEDGE",  "you built · your design · complicit",  self._guilt_turns,   2),
            ("FOR EVERYONE", "everyone · all of them · wipe it",     self._purpose_turns, 1),
            ("QUESTION",     "why · how · what does it do",          self._asked,         2),
        ]
