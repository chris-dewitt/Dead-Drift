"""
DRAY — slacker fellow courier. Been in the game longer, cares less.
Runs into you on the relay band, bored, killing time between sectors.
Will share barge intel and gate codes if you complain enough about the job.
Clams up if you sound like a corpo or threaten to report him.

Outcomes:
  COMMISERATE : complain about the job / debt / barges / nova soma (3 turns) → free intel
  TRADE       : offer your own intel or something weird → he trades back
  FLAT-BRIBE  : offer credits ≥ 500 → he laughs then takes it → RELEASE
  CORPO       : sound professional / formal / compliance → he hangs up
  SNITCH      : mention authorities / report / flag → IMPOUND (he tips off his barge buddy)
  BORED       : short, vague replies → patience runs out, he just stops responding
"""
from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT

_COMMISERATE_KEYWORDS = [
    "hate", "hate this job", "rough", "awful", "worst", "terrible",
    "barge", "barges", "repo men", "repo", "debt", "clone",
    "nova soma", "corporation", "corpo", "bullshit", "unfair",
    "tired", "exhausted", "done", "over it", "can't believe",
    "same", "same boat", "feel you", "know what you mean",
    "underpaid", "no choice", "trapped", "stuck",
    "quota", "sector", "what are they even", "makes no sense",
    # Playtest fix: "gripe" / "griping" / "complain" should land here.
    "gripe", "griping", "gripes", "moan", "moaning", "whinge",
    "whinging", "complain", "complaining", "complaint", "vent",
    "venting", "bitching", "fed up", "had it",
]
_TRADE_KEYWORDS = [
    "intel", "tip", "route", "patrol", "heard", "scanner",
    "exchange", "swap", "trade", "got something", "know something",
    "found", "shortcut", "gate", "frequency", "channel",
    "something weird", "weird one", "check this out", "you'll never guess",
]
_BRIBE_AMOUNT = 500
_CORPO_KEYWORDS = [
    "regulation", "compliance", "protocol", "procedure", "properly",
    "official", "license", "certified", "authorised", "authorized",
    "formally", "policy", "in accordance", "required documentation",
    "transit authority", "form", "permit", "clearance code",
]
_SNITCH_KEYWORDS = [
    "report", "flag", "authority", "turn you in", "rat", "snitch",
    "arrest", "warrant", "illegal", "infraction", "violation",
    "documentation", "supervisor", "who are you really", "prove",
]


class Dray(BaseNPC):
    """Slacker courier on the relay band. Intel for commiseration."""

    def __init__(self, vocabulary_vault=None, run_context: dict | None = None, **_):
        super().__init__("DRAY", patience=6)
        self._vault             = vocabulary_vault
        self._ctx               = run_context or {}
        self._gripe_count       = 0
        self._traded            = False
        self._paid              = False
        self._corpo_flags       = 0

    def _intro_line(self) -> str:
        return random.choice([
            "Hey. Yeah, it's open channel out here. I'm Dray. Sector Three, stuck waiting on a gravity window. "
            "You headed the same direction? ...Barges are thick today. Just saying.",

            "*yawning static* Oh, a live one. Dray. Four years hauling, two warnings, zero promotions. "
            "Who are you. What've you got. Make it interesting, I'm bored.",

            "You're on my frequency. That's fine. I'm not doing anything. "
            "Third sector in a row with no tip-off from dispatch. "
            "These barges are on a new pattern. You noticed?",

            "Dray here. Listen — I heard something on the last gate scanner, "
            "thought I'd stay on channel for a bit. "
            "This sector's got two barges on a pincer. Just so you know. "
            "You owe me one. Or don't. I don't really care.",
        ])

    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        if any(w in raw for w in _SNITCH_KEYWORDS):
            self._patience = 0
            bus.emit(EVT_NLP_EXPLOIT, npc="dray", exploit_key="snitched")
            return NPCOutcome.IMPOUND, random.choice([
                "*flat* Hm. Thought you were a courier. "
                "My mistake. "
                "*channel click* Barge Seven, I've got a non-affiliate on channel Delta. "
                "Yeah. Yeah, transmitting coordinates now.",

                "Report me. Okay. "
                "*long pause, sounds of typing* "
                "I've got a buddy at Barge Six. Funny coincidence. "
                "He knows your transponder code now.",

                "*cold laugh* You really said that. Okay. "
                "First rule of this job: never threaten the guy who knows the barge schedules. "
                "*radio clicks off, then back on* Actually, one more thing: you're flagged.",
            ])

        if any(w in raw for w in _CORPO_KEYWORDS):
            self._corpo_flags += 1
            if self._corpo_flags >= 2:
                self._patience = 0
                return NPCOutcome.IMPOUND, random.choice([
                    "*sighs* You sound like a training module. "
                    "I'm out. "
                    "*channel drop, silence, then static* ...I also forwarded this channel to Dispatch. "
                    "Didn't want to but you kind of asked for it.",

                    "...Compliance. Clearance. Protocol. "
                    "*long pause* "
                    "That's a No from me. I'm flagging this as a Corp probe and closing out. "
                    "Good luck with your 'procedures.'",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*silence* ...You're going to be one of THOSE, aren't you.",
                "Uh huh. Very professional. Extremely formal. "
                "This is not that kind of channel, mate.",
                "*audible sigh* Right. Okay. Let me try again: "
                "forget the script. What do you actually want.",
            ])

        if any(w in raw for w in _TRADE_KEYWORDS):
            self._traded = True
            self._current_path = "INTEL TRADE"
            bus.emit(EVT_NLP_EXPLOIT, npc="dray", exploit_key="intel_trade")
            if self._vault:
                self._vault.record("dray", "INTEL_TRADE")
            return NPCOutcome.RELEASE, random.choice([
                "Oh, interesting. Yeah, alright. I'll match that. "
                "*short burst of static* Barge Seven is running a wide arc — "
                "hug the debris side of sector four and you're invisible. "
                "Don't tell anyone where you heard that.",

                "Hey, good tip. "
                "Returning the favour: "
                "Gate Nine has a busted scanner. Been down since Tuesday. "
                "You could run through it backwards and they wouldn't know. "
                "You didn't hear this from me.",

                "Not bad. For that I'll give you the gate frequency. "
                "*reads something* 334.7 on the short-wave. "
                "Barges ping in on the odd minute. Stay off it on the odd minute. "
                "We're square.",
            ])

        if parsed.amount is not None and parsed.amount >= _BRIBE_AMOUNT:
            self._paid = True
            # Playtest fix: dossier label uses the standardised
            # `BRIBE [X cr]` format instead of past-tense "BRIBED".
            self._current_path = f"BRIBE [{parsed.amount} cr]"
            bus.emit(EVT_NLP_EXPLOIT, npc="dray", exploit_key="bribe")
            if self._vault:
                self._vault.record("dray", "BRIBE")
            return NPCOutcome.RELEASE, random.choice([
                f"*laughing* {parsed.amount} credits. For a tip. "
                "That's... okay. I'm not complaining. "
                "Patrol window opens in forty seconds. You've got a clean run to Sector Five. "
                "Thanks, I guess.",

                "I was going to give you this for free if you griped a bit more. "
                "But credits are credits. "
                "*amused* Barge sweep is in eight minutes. Go now and you're clear.",

                f"The desperation in that {parsed.amount}. Respect. "
                "Barge Two is looping wide. You've got six minutes. "
                "Now we're both slightly richer and the day is better.",
            ])

        if any(w in raw for w in _COMMISERATE_KEYWORDS):
            self._gripe_count += 1
            self._current_path = "COMMISERATE"
            self.disposition += 2
            if self._gripe_count >= 3:
                bus.emit(EVT_NLP_EXPLOIT, npc="dray", exploit_key="commiserate")
                if self._vault:
                    self._vault.record("dray", "COMMISERATE")
                return NPCOutcome.RELEASE, random.choice([
                    "Okay, yeah. "
                    "*exhales* Yeah. Three years I've been doing this. "
                    "Nova Soma raised the debt threshold AGAIN last quarter. "
                    "You know what, just go through. "
                    "Barge Three is on a coffee run — no really, they take actual breaks. "
                    "You've got four minutes. Free. On me.",

                    "Man. We're in the exact same boat, you and me. "
                    "*static* Except I've been in the boat longer. "
                    "Listen: Gate Eight, scanner's on a five-minute loop. "
                    "Time it right and you don't exist. "
                    "Go. And hey — don't die.",

                    "Right? RIGHT? "
                    "Four years, Dray. Four years of this. "
                    "The clone debt GROWS. The delivery pay DOESN'T. "
                    "*long pause* Alright. Sending you the barge corridor. "
                    "I like you. You get it. Go make your delivery.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*grunt of recognition* Yeah. Yeah, I know. "
                "Barges three, four, and six today. It's a LOT. "
                "What else you got.",

                "Heh. Tell me about it. "
                "This sector is legitimately the worst. "
                "What's your cargo today?",

                "Man. They really just don't let up, do they. "
                "I've had the same Barge on my tail for two sectors running. "
                "Just... what's the point.",

                "That's the job. Nothing to do about it. "
                "I've accepted that this is my life and I have been miserable ever since. "
                "Keep talking, I'm genuinely curious how your day got here.",
            ])

        return NPCOutcome.CONTINUE, self._lazy_filler()

    def _lazy_filler(self) -> str:
        return random.choice([
            "Mm. Yeah.",
            "*long pause* Sorry, what?",
            "Uh huh. And?",
            "I've got time. You've got... less time. Make it interesting.",
            "*sounds of eating something* Sorry. Continue.",
            "You know what, don't even tell me what you're hauling. I don't want to know.",
            "This frequency gets boring. Give me something.",
            "I was going to go quiet but you seem like you might actually have a story.",
            "Three more minutes before I drift out of range. Use them.",
            "Gary's been quiet on the repo band today. Must be eating. He eats a lot.",
            "Mira at bay nine charges double if you sound desperate. Sound less desperate.",
            "Felix — Relay-7 Felix? — he's parked in sector four, twitching. "
            "Fence work if you need it.",
            "Sandra Vega-Marsh passed me on the comm yesterday. Smug. Beautiful sector clear. "
            "I'm not bitter. I'm slightly bitter.",
            "Heard a Bax-class droid on a passing courier last week. They get weirdly attached. "
            "You got one?",
        ])

    def get_path_progress(self) -> list[tuple[str, int, int]]:
        # Playtest fix: bribe row uses the standardised dollar-amount
        # label so it matches the rest of the NPC dossiers.
        return [
            ("GRIPE",            min(self._gripe_count, 3), 3),
            ("INTEL TRADE",      int(self._traded),         1),
            (f"BRIBE [{_BRIBE_AMOUNT}+ cr]", int(self._paid), 1),
        ]

    def exploits(self) -> dict[str, str]:
        return {
            "commiserate": "Gripe about the job / debt / barges 3 times",
            "intel_trade": "Offer intel or a weird tip — he trades back",
            "bribe":       "Offer 500+ credits — he laughs, then takes it",
        }
