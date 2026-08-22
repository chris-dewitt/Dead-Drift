"""
CHEN — former lead architect of the galactic debt ledger.

She wrote the cage. Then she walked into the belt and never came back.
The Remnants protect her. Marrow routes for her. She made the virus.

This NPC fires during Chapter 5 — when the Remnants vet you before
handing over the drive. There is no losing this interrogation. The
question is *how* the player gets the drive: respectfully, transactionally,
or with the kind of guilt that makes Chen quietly hand it over.

Outcomes:
  RESPECT      : thank her / acknowledge the work (2 turns) → RELEASE, quietly
  ACKNOWLEDGE  : name what she built (2 turns) → RELEASE, under the weight
  FOR EVERYONE : frame the goal as universal → RELEASE, fast
  QUESTION     : ask how the virus works (2 turns) → she teaches, then sends you
  ledger_shell : `shell`; read the root cascade-write in her own source mirror
"""
from __future__ import annotations
import random

from core.event_bus import bus, EVT_NLP_EXPLOIT
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.npcs.keywords import hit
from terminal.nlp_parser import ParsedInput

_RESPECT_PHRASES = [
    "thank", "honour", "honor", "grateful", "appreciate", "owe you",
    "indebted", "no idea", "incredible", "couldn't believe",
    "amazing what you", "you didn't have to", "you don't owe me",
    "respect", "means a lot", "i'm glad you're", "im glad you're",
]
_RESPECT_WORDS = ("thanks", "wow", "owe")
_GUILT_PHRASES = [
    "the ledger", "your design", "you made", "you built", "you wrote",
    "your code", "your fault", "you helped", "you let it", "you knew",
    "for years", "all these years", "you started this", "your signature",
    "you signed off", "you could have stopped", "why didn't you",
    "why did you build", "how do you live with",
]
_GUILT_WORDS = ("complicit", "blame", "responsible")
_PURPOSE_PHRASES = [
    "everyone", "all of them", "wipe it", "wipe everyone", "free them",
    "clear it", "burn it down", "burn it", "no more debt", "everyone free",
    "the whole thing", "all of us", "all of it", "for everyone",
    "not just me", "every courier", "every clone", "the whole table",
    "galactic", "all the ledgers",
]
_QUESTION_PHRASES = [
    "why now", "why us", "why me", "how does it work", "what does it do",
    "what is it", "are you sure", "is it safe", "what happens", "what then",
    "how long", "what do i do", "where does it go", "will it hold",
    "what's the catch", "whats the catch", "how do i use it",
]
_QUESTION_WORDS = ("why", "how", "what")


class Chen(BaseNPC):
    """The Remnants' architect. Hands over the drive."""

    def __init__(self, vocabulary_vault=None, run_context: dict | None = None, **_):
        super().__init__("Chen", patience=10)
        self._vault         = vocabulary_vault
        self._respect_turns = 0
        self._guilt_turns   = 0
        self._purpose_turns = 0
        self._asked         = 0
        self._ctx = run_context or {}

    # ------------------------------------------------------------------
    def _win(self, key: str, path: str) -> None:
        """File a path as discovered so it reaches Bax's vault and Records."""
        self._current_path = path
        bus.emit(EVT_NLP_EXPLOIT, npc="chen", exploit_key=key)
        if self._vault:
            self._vault.record("chen", key.upper())

    def _intro_line(self) -> str:
        return random.choice([
            "Chen. They told you I'd be here. I assume you brought the cipher Marrow sent. Good. "
            "I have a drive. It does one thing. You can ask me about it — or you can take it and run.",

            "You came farther than most. Sit. I won't waste your time. The drive's already in your hold. "
            "I want to know who I just handed it to.",

            "I designed the system you've been bleeding under for fifteen years. "
            "I want you to know that before I give you the way out of it.",

            "*a woman in a rebreather, forty metres of rock over her head* "
            "You're the courier Marrow vouched for. He doesn't vouch. "
            "So either he's slipping or you're worth the trip. Talk to me.",

            "Before you say anything: I'm not a hero and this isn't a rescue. "
            "I'm a woman fixing her own work. Sit down. Ask me whatever you like.",
        ])

    def _universal_escape_line(self) -> str:
        return (
            "*the smallest laugh you have heard in this belt* "
            "Fifteen years and that's the review. Fair. Honestly — fair. "
            "The drive's in your hold anyway, courier. Floor twelve, ninety "
            "seconds, and mind the blast doors on the way out. Go on."
        )

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        text = parsed.raw.lower()

        if hit(text, _RESPECT_PHRASES, _RESPECT_WORDS):
            self._respect_turns += 1
            self._current_path = "RESPECT"
            if self._respect_turns >= 2:
                self._win("respect", "RESPECT")
                return NPCOutcome.RELEASE, random.choice([
                    "Don't thank me. I'm balancing a ledger that doesn't show on the books. "
                    "Drive's yours. The slot at Nova Soma is on floor twelve. "
                    "When you plug it in, hold the line for ninety seconds. That's all I ask.",

                    "*she waves it off, badly* People keep doing that and I keep not "
                    "knowing where to put it. Floor twelve. Ninety seconds. "
                    "Tell your droid to keep the comm quiet while it writes — Bax units "
                    "chatter, and the audit floor listens.",

                    "You're the fourth person to thank me. The other three didn't make it "
                    "to the station. *evenly* That's not a warning, it's arithmetic. "
                    "Floor twelve. Ninety seconds. Be the one.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "You're polite. Most aren't. I'll take it. Tell me — what'll you do "
                "after the debt is gone?",

                "*she looks at you properly for the first time* Careful. Manners are "
                "how they get you down here. Go on, then — why does it matter to you?",

                "Noted, and filed somewhere I don't look at often. Keep going. "
                "I want to hear you say what this is for.",
            ])

        if hit(text, _GUILT_PHRASES, _GUILT_WORDS):
            self._guilt_turns += 1
            self._current_path = "ACKNOWLEDGE"
            if self._guilt_turns >= 2:
                self._win("acknowledge", "ACKNOWLEDGE")
                return NPCOutcome.RELEASE, random.choice([
                    "Yes. I built it. I am the reason. I won't pretend otherwise. "
                    "Take the drive. The slot is on floor twelve. Don't die getting there.",

                    "I wrote the clone-debt inheritance clause on a Tuesday. I remember "
                    "the Tuesday. I remember thinking it was elegant. "
                    "*she hands you nothing; it's already aboard* Floor twelve. Ninety seconds. Go.",

                    "You want me to argue. I'm not going to. Every courier Nova Soma has "
                    "ever ground down went through a function with my initials in the "
                    "comment header. Sandra's still flying it. Gary still eats off it. "
                    "Floor twelve. Undo it for me.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "You're right. I'm not going to argue. Keep going.",

                "*no flinch at all* Correct. Say the rest of it.",

                "Everything you're about to accuse me of is in the commit log with my "
                "name on it. I've read it more recently than you have. Continue.",
            ])

        if hit(text, _PURPOSE_PHRASES):
            self._purpose_turns += 1
            self._win("for_everyone", "FOR EVERYONE")
            return NPCOutcome.RELEASE, random.choice([
                "Everyone. Every single ledger entry, galactic. Not just yours. "
                "That's what the drive does. Plug it in. Hold for ninety seconds. "
                "Run like you mean it.",

                "*that's the answer she was waiting for* Everyone. Every entry, every "
                "sector, every clone line. It doesn't know how to do one person. "
                "I made sure it couldn't. Floor twelve. Ninety seconds. Go.",

                "Good. Because a courier who wanted their own row zeroed would get a "
                "drive that bricks on insert. That was the test. You passed it. "
                "Floor twelve — and when the alarm goes, keep your hand on the drive.",
            ])

        if hit(text, _QUESTION_PHRASES, _QUESTION_WORDS):
            self._asked += 1
            self._current_path = "QUESTION"
            if self._asked >= 2:
                self._win("question", "QUESTION")
                return NPCOutcome.RELEASE, random.choice([
                    "Then you know enough. Drive's already aboard. Floor twelve. "
                    "Ninety seconds. Don't hesitate at the blast doors.",

                    "That's the whole design. There isn't a clever part I'm holding back. "
                    "*she stands* Floor twelve. Ninety seconds. If the console asks you "
                    "to confirm, it's already too late to stop and you should say yes anyway.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "I wrote every line of that ledger. I know exactly where the door is. "
                "The drive injects a cascade write at root level — it doesn't delete "
                "debt, it *zeroes the field across the whole table*. Anything else?",

                "Fair question. It's not a virus, whatever Marrow's been calling it on "
                "the band. It's a migration script with no rollback. One field, every "
                "row, one pass. Ninety seconds because the table is very large. What else?",

                "Safe? No. It'll hold, which isn't the same thing. The write is atomic — "
                "either the whole galaxy clears or nothing does. There's no version where "
                "you clear half of it and they come after you for the rest. Ask me another.",
            ])

        # Default: drift toward release after enough exchanges
        if self._turn >= 4:
            self._current_path = "QUESTION"
            return NPCOutcome.RELEASE, random.choice([
                "Enough talk. The drive's in your hold. Floor twelve. Don't die.",
                "We're done. You've got what you came for and I've got rock to sit under. "
                "Floor twelve. Ninety seconds. Go.",
            ])
        return NPCOutcome.CONTINUE, self._architect_filler()

    def _architect_filler(self) -> str:
        return random.choice([
            "Mm. Keep talking.",
            "I'm listening. Make it count.",
            "Say more.",
            "*the rebreather hisses* Take your time. I have fifteen years of it.",
            "The Remnants let you through, so somebody trusts you. "
            "I'd like to know why before I do.",
            "Marrow routes for me. He's never once asked what for. "
            "You can, if you want. Nobody else has.",
            "There's a repo man out there called Gary who thinks the schedule "
            "he flies is a law of physics. I wrote that schedule. On a deadline.",
            "Sandra Vega-Marsh has the cleanest record in the sector and she is "
            "still, technically, property. That's a line of my code doing that.",
            "Felix fences the scraps of a system I designed to have no scraps. "
            "He found some anyway. I was almost proud.",
            "I don't ask couriers what they're hauling. It's never once been "
            "the interesting thing about them.",
            "Nova Soma sent a compliance man to the belt once. Polite. "
            "He asked after my family. *flat* I came further in after that.",
            "You want to know the worst part? It was a good system. "
            "It did exactly what it was specified to do.",
            "Ninety seconds is a long time when a station is telling you to stop. "
            "Start getting used to the number now.",
        ])

    def exploits(self) -> dict[str, str]:
        return {
            "respect":         "Thank her, twice — she'll explain the path quietly",
            "acknowledge":     "Name what she built — she releases under the weight",
            "for_everyone":    "Frame the goal as universal — she signs off fast",
            "question":        "Ask how the virus works — she'll teach you, then send you",
            "ledger_shell":    "Type `shell`; read the ledger's own root cascade-write",
        }

    # J.3.1 — Chen wrote the ledger; she'll let you read its source. The shell
    # exposes the cascade-write she described out loud — finding it yourself is
    # the architect's blessing (she respects a courier who reads the code).
    def shell_session(self):
        if getattr(self, "_shell", None) is None:
            from terminal.shell_session import ShellSession
            self._shell = ShellSession(
                host="ledger-root", user="remnant",
                motd="GALACTIC DEBT LEDGER // source mirror (Chen's copy)",
                files={
                    "/README": "I wrote every line of this. — C.\n"
                               "The door is where it always was: root level.",
                    "/ledger/schema.sql": "TABLE debt (entry_id, holder, balance, sector)\n"
                               "-- fifteen years. every courier. every clone.",
                    "/ledger/notes/marrow.txt": "Marrow routes the cipher. Trust the static.",
                    "/ledger/notes/leavers.txt": "names of everyone who signed the spec with me.\n"
                               "four went to Nova Soma compliance. one went to the belt.\n"
                               "the belt was cheaper. — C.",
                    "/ledger/root/cascade_write.rs": "// zeroes balance ACROSS THE WHOLE TABLE.\n"
                               "// not a delete. a field wipe. galactic.\n"
                               "// hold the line ninety seconds. — C.",
                },
                loot={"/ledger/root/cascade_write.rs": "ledger_shell"},
                denied=set(),
            )
        return self._shell

    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [
            ("RESPECT",      min(self._respect_turns, 2), 2),
            ("ACKNOWLEDGE",  min(self._guilt_turns, 2),   2),
            ("FOR EVERYONE", min(self._purpose_turns, 1), 1),
            ("QUESTION",     min(self._asked, 2),         2),
            ("LEDGER SHELL", int(getattr(self, "_systems_hit", False)), 1),
        ]
