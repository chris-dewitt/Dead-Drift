from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT


class Kress(BaseNPC):
    """
    KRESS — ex-asteroid miner turned smuggler/fixer. Russian accent, kept
    readable. Has been listening to Union comms for thirty years. Knows
    where the soft spots are. Knew the previous pilot.

    Not an enemy. The player CALLS him. He sells intel and contraband and
    runs his mouth about Nova Soma. Outcomes:
    - RELEASE: amicable hangup (any reasonable conversation ends here)
    - IMPOUND: comm cut after sustained hostility (Kress doesn't work
      with assholes — translates to "no deal" for this run)
    - EXPLOIT: discovered linguistic shortcut to a discount or to the
      lore (Volkov mention, previous pilot mention)

    Discovery paths:
    - "Volkov" — Kress owes a debt of his own to Volkov; mention his
      name and Kress softens up immediately (EXPLOIT: old_debt)
    - "Connie" — name of the previous pilot. Kress goes quiet. Asks
      if you knew her. Reveals lore. (EXPLOIT: previous_pilot)
    - Friendly tone (3 turns of positive sentiment) → discount
    - Asking for intel/tips/contraband → he sells you a service
    """

    _INTEL_KEYWORDS    = ["intel", "tip", "tips", "info", "information",
                           "what's ahead", "next sector", "patrol", "scan"]
    _CONTRABAND_WORDS  = ["contraband", "stims", "fuel", "jammer", "smoke",
                           "shield", "patch", "hack", "warez", "stuff"]
    _GREASE_KEYWORDS   = ["volkov", "old debt", "owe", "owed", "vienna"]

    def __init__(self):
        super().__init__("KRESS", patience=8)
        self._friendly_turns = 0
        self._mentioned_volkov  = False
        self._mentioned_connie  = False

    def _intro_line(self) -> str:
        return random.choice([
            "*static* ...Kress here. Channel is dirty, talk fast. "
            "You want intel, contraband, or you want me to hang up? "
            "I am busy man. Well. I am not. But say it like I am.",
            "*click* Kress. Yes. You found frequency. Good for you. "
            "Most people, they do not find frequency. "
            "Most people, they get clamped. So. What you need.",
            "*long static crackle* ...This is Kress. "
            "I have been listening to Union chatter since before you were "
            "decanted, my friend. I know things. Things have prices. "
            "Begin.",
        ])

    def exploits(self) -> dict[str, str]:
        return {
            "old_debt":       "Mention Volkov — Kress owes him, softens up",
            "previous_pilot": "Mention Connie — Kress knew her, reveals lore",
            "regular":        "Become a regular through friendly conversation",
        }

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        # PREVIOUS PILOT — the lore drop, the mystery seed
        if "connie" in raw and not self._mentioned_connie:
            self._mentioned_connie = True
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="previous_pilot")
            return NPCOutcome.RELEASE, (
                "*very long silence* "
                "...You knew Connie? *quiet* "
                "She used to fly this same route. Bax was hers, you know. "
                "Before. She came close — closer than anyone. "
                "Then Nova Soma flagged her file 'asset volatility risk' "
                "and that was that. *static* "
                "...You did not know Connie. You guessed. Smart. "
                "On the house this time. Do not waste it. *click*"
            )

        # OLD DEBT — Volkov is Kress's leverage, mention him for goodwill
        if any(w in raw for w in self._GREASE_KEYWORDS) and not self._mentioned_volkov:
            self._mentioned_volkov = True
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="old_debt")
            return NPCOutcome.RELEASE, (
                "*laughs* Volkov. You drop that name like rock through window. "
                "Fine. Yes. I owe Volkov. We all owe Volkov. "
                "You are friend of Volkov, you are friend of Kress. "
                "Half price today. Whatever you need. "
                "Just do not tell him I said his name on open channel. *click*"
            )

        # INTEL REQUEST
        if any(w in raw for w in self._INTEL_KEYWORDS):
            return NPCOutcome.RELEASE, random.choice([
                "Next sector: Local 404 patrol is light. Dispatcher is on lunch. "
                "Two thousand credits, on your tab. Already done. Drive safe.",
                "I am hearing chatter. Repo barge in your area has bad torch — "
                "module unbolt cooldown is doubled. Free tip, this one. "
                "Because you asked nicely. Now go.",
                "Sector ahead has gravity well shifting position every 40 seconds. "
                "Union does not have this on charts yet. Now you do. "
                "Twelve hundred credits. Tab. *click*",
            ])

        # CONTRABAND REQUEST
        if any(w in raw for w in self._CONTRABAND_WORDS):
            return NPCOutcome.RELEASE, random.choice([
                "Jammer package, twenty-second barge comm blackout. "
                "Five thousand. On tab. Already in your fuel mix. *click*",
                "Hull patch, salvaged from Volkov's last job. "
                "Eight thousand, but it is good steel. I throw it in. "
                "Tab is bigger now. So is your hull. Goodbye.",
                "Stims for your droid. Bax will be... let us say 'enthusiastic' "
                "for next ten minutes. Three thousand. "
                "He will not thank you. *click*",
            ])

        # FRIENDLY — wear into regular status
        compound = parsed.sentiment.get("compound", 0.0)
        if compound > 0.3:
            self._friendly_turns += 1
            if self._friendly_turns >= 3:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="regular")
                return NPCOutcome.RELEASE, (
                    "*laughs* Okay, okay. You are not Union spy. I can tell. "
                    "Spies do not make small talk. Spies do not have patience. "
                    "You are regular now. Next time you call, "
                    "I do not ask questions. Just say what you need. "
                    "*click*"
                )
            return NPCOutcome.CONTINUE, random.choice([
                "You are not in hurry, hm? Most pilots, very rushed. "
                "I appreciate. Talk more.",
                "Friendly. Suspicious. But friendly. Continue.",
                "You remind me of someone. Cannot place. Speak again.",
            ])

        # HOSTILE — Kress doesn't work with assholes
        if compound < -0.4 or parsed.intent == "threaten":
            self.disposition -= 2
            if self.disposition <= -4:
                return NPCOutcome.IMPOUND, (
                    "*static* ...No. I am hanging up. "
                    "I do not need this. I have been alive too long for this. "
                    "Do not call this frequency again. *click*"
                )
            return NPCOutcome.CONTINUE, random.choice([
                "Watch your mouth on open channel, my friend. "
                "Union listens. So do I.",
                "You are rude. I do not like rude. "
                "Try again, nicely. Or do not.",
            ])

        # DEFAULT — Kress runs his mouth
        return NPCOutcome.CONTINUE, self._kress_filler()

    def _kress_filler(self) -> str:
        return random.choice([
            "Speak plainly. I am not telepath. Telepaths charge more.",
            "You called me, remember? Was there reason, or just lonely?",
            "Nova Soma is hiring more enforcement this quarter. Record profits. "
            "Hiring more enforcement. You see pattern, yes?",
            "I knew man who paid off his clone debt once. "
            "Just one. He retired. Two weeks later, accident. "
            "Strange, that. Anyway. What do you need.",
            "Union charter just got amended again. Article 47, paragraph 12. "
            "You will not like it. I do not even like it. Continue.",
            "I am older than I look. Asteroid mining ages you. "
            "Also, I am quite old. So both things are true.",
            "There is rumor Local 404 dispatcher has started drinking on shift. "
            "Probably nothing. Probably opportunity. Same thing, often.",
            "Bax is good droid. Old model. They do not make like that anymore. "
            "Reason they do not make like that anymore. Think on it.",
        ])
