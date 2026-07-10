"""
BOWEN — Assistant Director of Compliance, Nova Soma Station.

Polite. Sincere. Has a family photo on his lanyard. Calls you by a
case number, not a name. The most dangerous person in the game,
specifically because he is genuinely *nice*.

Fires at chapter 6 climax, after the upload has corrupted the ledger.
He doesn't get angry. He gets *concerned*. He'd like you to remain
where you are while he resolves this. He'll wait. He has all day.

There is no winning Bowen on his terms — every "polite" path he
offers ends in IMPOUND. The only way out is to refuse the frame
entirely: shut him down, walk out, or expose him.
"""
from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput

_COMPLY_KEYWORDS = [
    "okay", "sure", "fine", "alright", "i'll wait", "wait here",
    "remain", "comply", "compliance", "yes sir", "of course",
    "as you wish", "happy to", "no problem", "understood",
]
_REFUSE_KEYWORDS = [
    "no", "never", "won't", "wont", "not happening", "make me",
    "go to hell", "screw you", "piss off", "drop dead",
    "not a chance", "absolutely not", "hard no", "no way",
]
_EXPOSE_KEYWORDS = [
    "clone tanks", "floor 31", "floor thirty one", "the names",
    "i saw them", "the bullpen", "collectors", "your workers",
    "human cost", "what you did", "what you do", "the people",
    "you keep them", "trapped", "everyone here", "your employees",
]
_PERSONAL_KEYWORDS = [
    "your family", "your kid", "your kids", "your son", "your daughter",
    "your wife", "your husband", "lanyard", "the photo", "you go home",
    "do you sleep", "look in the mirror", "your name",
]


class Bowen(BaseNPC):
    """Assistant Director of Compliance. Smiley evil."""

    def __init__(self, run_context: dict | None = None, **_):
        super().__init__("Bowen", patience=4)
        self._comply_turns  = 0
        self._refuse_turns  = 0
        self._expose_turns  = 0
        self._personal_hits = 0
        self._ctx = run_context or {}

    def _intro_line(self) -> str:
        return random.choice([
            "Hello again, courier. I'm afraid we've detected an irregularity. "
            "Could you please remain where you are while we resolve this? I'd "
            "appreciate your patience.",

            "There appears to be a compliance matter. I'm sure it's nothing. "
            "If you could just hold position, we'll have this sorted in a "
            "moment. Thank you for your cooperation.",

            "Hi. So — and I'm sorry to bother you — but our systems are "
            "showing something unusual. Just a small misunderstanding, I'm "
            "sure. Stay right there for me?",
        ])

    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        text = parsed.raw.lower()

        if any(k in text for k in _COMPLY_KEYWORDS):
            self._comply_turns += 1
            self._current_path = "COMPLY"
            if self._comply_turns >= 1:
                return NPCOutcome.IMPOUND, (
                    "Wonderful. Security will be with you in just a moment. "
                    "Thank you for your patience. This is the right choice."
                )

        if any(k in text for k in _EXPOSE_KEYWORDS):
            self._expose_turns += 1
            self._current_path = "EXPOSE"
            if self._expose_turns >= 2:
                return NPCOutcome.EXPLOIT, (
                    "I... I don't know what you saw. The floors are restricted "
                    "for safety reasons. I follow protocol. I do my work. I— "
                    "you should go. Please. Just go before they get here."
                )
            return NPCOutcome.CONTINUE, (
                "Those areas are restricted, courier. I don't know what you "
                "think you saw. Please remain on the line."
            )

        if any(k in text for k in _PERSONAL_KEYWORDS):
            self._personal_hits += 1
            self._current_path = "PERSONAL"
            if self._personal_hits >= 1:
                return NPCOutcome.EXPLOIT, (
                    "That's — that's not appropriate. My family has nothing "
                    "to do with this. Please. Just— go. The blast doors "
                    "close in forty seconds. Go."
                )

        if any(k in text for k in _REFUSE_KEYWORDS):
            self._refuse_turns += 1
            self._current_path = "REFUSE"
            if self._refuse_turns >= 2:
                return NPCOutcome.RELEASE, (
                    "I see. Well. I had to ask. You should know — the doors "
                    "won't wait. Neither will I. Goodbye, courier."
                )
            return NPCOutcome.CONTINUE, (
                "I understand you're upset. Please reconsider. We can resolve "
                "this amicably. There's no need for things to escalate."
            )

        if self._turn >= 3:
            self._current_path = "STALL"
            return NPCOutcome.IMPOUND, (
                "I'm sorry. Security has reached your position. I really did "
                "want this to go differently. Have a good day, courier."
            )

        return NPCOutcome.CONTINUE, random.choice([
            "I'm not sure I follow. Could you clarify?",
            "Take your time. I'm here.",
            "I'm just trying to do my job. Help me help you.",
            "Your companion — the Bax unit — it can't route you out of this one. "
            "I've already flagged the channel. Let's just talk.",
        ])

    def exploits(self) -> dict[str, str]:
        return {
            "EXPOSE":   "Name what you saw on the way down — he cracks",
            "PERSONAL": "Mention his family photo — the mask drops",
            "REFUSE":   "Refuse to comply, hard — he gives up",
            "audit_repl": "Type `python` into his audit console; break the sandbox",
        }

    # J.3.1 — Bowen keeps you "on the line" through a compliance audit console.
    # It's a Python prompt. Any real break-out (import os / __class__ / eval)
    # dumps you out of his procedure before Security arrives.
    def repl_session(self):
        if getattr(self, "_repl", None) is None:
            from terminal.repl_session import ReplSession
            self._repl = ReplSession(
                exploit_key="audit_repl",
                motd="NOVA SOMA COMPLIANCE AUDIT CONSOLE — please hold for the Assistant Director.")
        return self._repl

    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [
            ("EXPOSE",     self._expose_turns,   2),
            ("PERSONAL",   self._personal_hits,  1),
            ("REFUSE",     self._refuse_turns,   2),
            ("COMPLY",     self._comply_turns,   1),
            ("AUDIT REPL", int(getattr(self, "_systems_hit", False)), 1),
        ]
