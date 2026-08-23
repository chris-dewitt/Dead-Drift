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

Outcomes:
  COMPLY   : agree to hold position → IMPOUND (his whole trick)
  EXPOSE   : name what you saw on the way down (2 turns) → EXPLOIT
  PERSONAL : mention the lanyard photo → EXPLOIT, the mask drops
  REFUSE   : refuse the frame, twice → RELEASE
  STALL    : say nothing useful for three turns → IMPOUND
  audit_repl : `python` at his audit console; break the sandbox → EXPLOIT
"""
from __future__ import annotations
import random

from core.event_bus import bus, EVT_NLP_EXPLOIT
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.npcs.keywords import affirmed_hit, affirmed_phrase_hit, hit
from terminal.nlp_parser import ParsedInput

# Unambiguous surrender — whole phrases, so no negation guard is needed.
# "no problem" has to be tested before the refusal words or its bare "no"
# reads as defiance.
_COMPLY_PHRASES = [
    "i'll wait", "ill wait", "i will wait", "wait here", "hold position",
    "yes sir", "of course", "as you wish", "happy to", "no problem",
    "whatever you say", "you're the boss", "youre the boss", "will do",
    "i'll hold", "ill hold", "i'll cooperate", "ill cooperate",
]
# Agreement words. Matched whole-word AND negation-checked: "I'm not sure"
# and "that's not fine" used to read as consent and impound the run on turn
# one, at the climax of the game.
_COMPLY_WORDS = (
    "okay", "ok", "sure", "fine", "alright", "yes", "yeah", "yep",
    "comply", "compliance", "remain", "understood", "agreed", "certainly",
)
_REFUSE_PHRASES = [
    "not happening", "make me", "go to hell", "screw you", "piss off",
    "drop dead", "not a chance", "absolutely not", "hard no", "no way",
    "i'm leaving", "im leaving", "i'm going", "im going", "get lost",
    "not staying", "not waiting", "you can't hold me", "you cant hold me",
    "try and stop me", "shut up",
]
_REFUSE_WORDS = (
    "no", "never", "won't", "wont", "refuse", "refusing", "nope",
    "leaving", "goodbye", "done", "enough",
)
_EXPOSE_PHRASES = [
    "clone tanks", "floor 31", "floor thirty one", "floor thirty-one",
    "the names", "i saw them", "the bullpen", "human cost", "what you did",
    "what you do", "the people", "you keep them", "everyone here",
    "your employees", "your workers", "the tanks", "the vats",
    "growth vats", "how many of me", "how many are down there",
]
_EXPOSE_WORDS = ("collectors", "trapped", "clones", "harvested", "bodies")
_PERSONAL_PHRASES = [
    "your family", "your kid", "your kids", "your son", "your daughter",
    "your wife", "your husband", "the photo", "you go home", "do you sleep",
    "look in the mirror", "your name", "what's your first name",
    "whats your first name", "who's in the picture", "whos in the picture",
    "does she know", "does he know", "do they know what you do",
]
_PERSONAL_WORDS = ("lanyard", "photograph")


class Bowen(BaseNPC):
    """Assistant Director of Compliance. Smiley evil."""

    def __init__(self, vocabulary_vault=None, run_context: dict | None = None, **_):
        super().__init__("Bowen", patience=4)
        self._vault         = vocabulary_vault
        self._comply_turns  = 0
        self._refuse_turns  = 0
        self._expose_turns  = 0
        self._personal_hits = 0
        self._ctx = run_context or {}

    # ------------------------------------------------------------------
    def _win(self, key: str, path: str) -> None:
        """File a path as discovered so it reaches Bax's vault and Records."""
        self._current_path = path
        bus.emit(EVT_NLP_EXPLOIT, npc="bowen", exploit_key=key)
        if self._vault:
            self._vault.record("bowen", key.upper())

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

            "Case 8840-C. That's you. Sorry — I know people don't love being "
            "a number, it's just how the console sorts things. My name's "
            "Bowen. I'm going to help you get this straightened out.",

            "Good evening. I'm told the ledger did something strange about "
            "ninety seconds ago and that you were the nearest transponder. "
            "I'm sure there's an explanation. Would you stay on the line "
            "while I find it?",
        ])

    def _universal_escape_line(self) -> str:
        return (
            "*a small, wounded pause* ...There's no call for language like "
            "that. I was being polite with you. *the channel closes softly, "
            "the way a door closes when someone is very disappointed* "
            "Go on, then. Before I change my mind about how polite I'm being."
        )

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        text = parsed.raw.lower()

        # Surrender phrases first — "no problem" is agreement, not the refusal
        # its bare "no" would otherwise match. They still go through the
        # negation guard: "I will not hold position" is a refusal that happens
        # to contain a surrender phrase, and matching it bare impounded the
        # player for refusing, which is the exact bug this NPC had before.
        if affirmed_phrase_hit(text, _COMPLY_PHRASES):
            return self._comply()

        if hit(text, _EXPOSE_PHRASES, _EXPOSE_WORDS):
            self._expose_turns += 1
            self._current_path = "EXPOSE"
            if self._expose_turns >= 2:
                self._win("expose", "EXPOSE")
                return NPCOutcome.EXPLOIT, random.choice([
                    "I... I don't know what you saw. The floors are restricted "
                    "for safety reasons. I follow protocol. I do my work. I— "
                    "you should go. Please. Just go before they get here.",

                    "*the pleasantness goes out of his voice like heat out of "
                    "a room* Thirty-one is a maintenance level. It's on the "
                    "plan as a maintenance level. I've read the plan. I've read "
                    "it a lot. *quietly* Go. I'll log the channel as dropped.",

                    "Don't— don't say the number again, the console indexes "
                    "on the number. *typing* There. Session's a transcription "
                    "error now. That's all I can do for you and it's more than "
                    "I should. The doors are still open. Run.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "Those areas are restricted, courier. I don't know what you "
                "think you saw. Please remain on the line.",

                "That level isn't cleared for couriers, so whatever you're "
                "describing, you're describing it wrong. *a beat too long* "
                "Please remain on the line.",

                "I'd be careful with that. Not a threat — genuinely, I'd be "
                "careful. Descriptions like that get people scheduled for "
                "interviews. Let's stay on the irregularity.",
            ])

        if hit(text, _PERSONAL_PHRASES, _PERSONAL_WORDS):
            self._personal_hits += 1
            self._win("personal", "PERSONAL")
            return NPCOutcome.EXPLOIT, random.choice([
                "That's — that's not appropriate. My family has nothing "
                "to do with this. Please. Just— go. The blast doors "
                "close in forty seconds. Go.",

                "*a long silence, and then the sound of a lanyard being "
                "turned face-down on a desk* She's nine. That's all you get. "
                "That's all anyone here gets. The doors close in forty "
                "seconds and I am going to be looking at my screen.",

                "You don't— *he stops*. Everybody who works here has a photo. "
                "That's not a defence, I know that, I know exactly what that "
                "is. *unsteady* Forty seconds on the blast doors. I never "
                "flagged your channel. Go.",
            ])

        if hit(text, _REFUSE_PHRASES, _REFUSE_WORDS):
            self._refuse_turns += 1
            self._current_path = "REFUSE"
            if self._refuse_turns >= 2:
                self._win("refuse", "REFUSE")
                return NPCOutcome.RELEASE, random.choice([
                    "I see. Well. I had to ask. You should know — the doors "
                    "won't wait. Neither will I. Goodbye, courier.",

                    "Right. *he sounds almost relieved* Some people just say "
                    "no. I've always wondered what that's like. I'll note the "
                    "channel as uncooperative and close it. Mind the doors.",

                    "Understood. For what it's worth — and it isn't worth "
                    "anything — I did hope you'd stay. It's easier for me when "
                    "they stay. *click* Good luck, 8840-C.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "I understand you're upset. Please reconsider. We can resolve "
                "this amicably. There's no need for things to escalate.",

                "That's your right, of course. I'd just point out that every "
                "courier who has said that to me is now on a payment plan. "
                "I'd rather you weren't. Shall we start again?",

                "You're allowed to be angry with me. Genuinely. It doesn't "
                "change the irregularity, but you're allowed. Now — will you "
                "hold position?",
            ])

        # Agreement words last, and only when nobody negated them. "I'm not
        # sure I understand" is not consent.
        if affirmed_hit(text, _COMPLY_WORDS):
            return self._comply()

        if self._turn >= 3:
            self._current_path = "STALL"
            return NPCOutcome.IMPOUND, random.choice([
                "I'm sorry. Security has reached your position. I really did "
                "want this to go differently. Have a good day, courier.",

                "There we are. That's them at your hatch. *kindly* Don't make "
                "it difficult for them, they're on shift like the rest of us. "
                "Thank you for your patience, 8840-C.",
            ])

        return NPCOutcome.CONTINUE, self._concerned_filler()

    def _comply(self) -> tuple[str, str]:
        self._comply_turns += 1
        self._current_path = "COMPLY"
        return NPCOutcome.IMPOUND, random.choice([
            "Wonderful. Security will be with you in just a moment. "
            "Thank you for your patience. This is the right choice.",

            "Oh, thank you. Honestly — thank you. It's so much easier when "
            "people are reasonable. Someone will be along shortly. "
            "You've done the right thing.",

            "Marvellous. I'll note that you cooperated fully; that does count "
            "for something at the hearing. *warmly* Sit tight. Nearly over.",
        ])

    def _concerned_filler(self) -> str:
        return random.choice([
            "I'm not sure I follow. Could you clarify?",
            "Take your time. I'm here.",
            "I'm just trying to do my job. Help me help you.",
            "Your companion — the Bax unit — it can't route you out of this one. "
            "I've already flagged the channel. Let's just talk.",
            "Take a breath. Nobody's shouting. I never shout.",
            "I've got your file open. Sixty-one deliveries. That's a good "
            "record. I'd hate to be the one who ends a good record.",
            "Nova Soma isn't a villain, you know. It's a payroll. I'm on it. "
            "So is everyone who's ever come through this channel.",
            "Collections tried you last quarter, I see. They're blunt "
            "instruments. I'd like to think I'm not.",
            "Somebody's cargo inspector — Holt? — flagged you as 'compliant "
            "but slippery'. I thought that was rather unfair of him.",
            "I do this eleven hours a day and everyone I speak to thinks "
            "they're the first person to try being clever. Not a criticism.",
            "There's a broadcaster the audit team can't shut up about. Marrow. "
            "Was. *a small cough* Anyway. The irregularity.",
            "If you're waiting for me to lose my temper, I'd settle in. It "
            "hasn't happened since the tanks— *pause* —since I started.",
            "You've gone quiet. That's alright. Silence is a kind of answer "
            "and I do log it as one.",
            "Whatever the ledger did ninety seconds ago, it's doing it "
            "galaxy-wide now. I'd very much like to know how. Wouldn't you?",
        ])

    def exploits(self) -> dict[str, str]:
        return {
            "expose":   "Name what you saw on the way down, twice — he cracks",
            "personal": "Mention the lanyard photo — the mask drops",
            "refuse":   "Refuse to comply, hard, twice — he gives up",
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
            ("EXPOSE",     min(self._expose_turns, 2),   2),
            ("PERSONAL",   min(self._personal_hits, 1),  1),
            ("REFUSE",     min(self._refuse_turns, 2),   2),
            ("COMPLY",     min(self._comply_turns, 1),   1),
            ("AUDIT REPL", int(getattr(self, "_systems_hit", False)), 1),
        ]
