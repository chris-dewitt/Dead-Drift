"""
Corrupt Union Rep — Local 404 with side hustles.

Counterpoint to the Idealist. Skims off Union impounds, has loose ties
to Outer Belt pirates, willing to take a bribe but might also rob you
outright if you flash too much cash. Different vibe from Gary's
bureaucratic cynicism — Gary is *tired*; this guy is *opportunistic*.

Win paths:

  BRIBE_LOW    — Offer a small bribe (≥ 1500 cr): waved through. He's
                  not greedy, he's *hungry*. Smaller numbers actually
                  work better here than with Gary.
  BRIBE_BIG    — Offer ≥ 8000 cr: triggers the SHAKEDOWN path. He
                  takes the offered amount AND impounds half your cargo.
                  You "win" but it costs more than you bargained for.
  SHARE        — Offer to split a future score, mention "Krellborn",
                  "Outer Belt", "fence", or "off the books". Two hits
                  → release with a wink.
  THREATEN     — Threats actually work here. Mention his side hustles
                  by name ("skim", "kickback", "Local 404 audit"). Two
                  hits → release. He doesn't want HIS file flagged.
  COMPLIANCE   — Standard formal compliance fails — he doesn't actually
                  care about the Charter, he cares about the take.
  Plus the universal `fuck off` easter egg.
"""
from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT


class CorruptRep(BaseNPC):
    """Corrupt Union Rep — name: Vince 'Two-Tap' Brogan."""

    _BRIBE_KEYWORDS = [
        "bribe", "pay", "credits", "money", "cash", "offer",
        "compensate", "buy", "slip", "transfer", "wire", "take this",
        "deposit", "envelope", "off-channel", "untraceable",
    ]
    _SHARE_KEYWORDS = [
        "share", "split", "cut you in", "piece of", "percentage of",
        "off the books", "outer belt", "krellborn", "fence",
        "cut", "partner", "down the line", "next score",
    ]
    _THREAT_KEYWORDS = [
        "skim", "skimming", "kickback", "audit", "internal affairs",
        "compliance review", "ledger", "report you", "expose",
        "anonymous tip", "blevins", "dispatcher", "we know",
    ]
    def __init__(self, intercepted: bool = False,
                 run_context: dict | None = None):
        super().__init__("Vince", patience=7)
        self._intercepted   = intercepted
        self._bribe_paid    = 0
        self._share_hits    = 0
        self._threat_hits   = 0
        self._was_shakedown = False
        self._ctx           = run_context or {}

    def _intro_line(self) -> str:
        if self._intercepted:
            return random.choice([
                "Vince Brogan, Local 404. Yeah yeah, intercept, debt, "
                "the usual. Power down. Or don't. Up to you. "
                "We can definitely *talk*.",
                "Vinny here. 404. Look, I'm closin' fast — outstanding "
                "fees, blah blah — but between you an' me, we can probably "
                "work somethin' out. *cough* You know what I mean.",
                "Local 404, Brogan speakin'. I'm runnin' a tight schedule. "
                "Power down or we *negotiate*. I'll be honest, I prefer "
                "the second one.",
            ])
        return random.choice([
            "Vince Brogan. 404. You got fees. I got time. "
            "We don't need to make this a federal case, do we?",
            "Vinny, Local 404. Look — I see your manifest, you see my barge. "
            "We can keep this between us. Or get the dispatcher involved. "
            "Your pick.",
            "Vince Brogan. Yeah, the OTHER Brogan, not me cousin. "
            "Listen, I prefer the *quiet* resolutions. You catch me drift?",
        ])

    def exploits(self) -> dict[str, str]:
        return {
            "small_bribe":  "Offer 1500+ cr — he's hungry, not greedy",
            "share_score":  "Offer to cut him in on a future score",
            "threaten":     "Threaten to flag his side hustle (audit, skim)",
        }

    def _universal_escape_line(self) -> str:
        return (
            "*laughs* That's the spirit, mate. Tell you what — "
            "I'll write it up as 'verbal abuse, comm severed'. "
            "Off you go. Tell Krellborn Vinny says hi."
        )

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        # THREAT PATH — flagging his side hustle.
        if any(w in raw for w in self._THREAT_KEYWORDS):
            self._threat_hits += 1
            self._current_path = "THREATEN"
            self.disposition  -= 1   # he hates it but he respects the leverage
            if self._threat_hits >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="threaten")
                return NPCOutcome.RELEASE, random.choice([
                    "*pause* ...Alright. Alright. You're either bluffin' "
                    "or you ain't, an' I'm not testin' it tonight. "
                    "Vessel: not located. We never spoke. Cheers.",
                    "*lower voice* Easy, easy. The audit thing — "
                    "let's keep that between us, yeah? "
                    "Filin' it 'unit unable to engage.' Get out of 'ere.",
                    "Right. *taps screen* You were never 'ere. "
                    "I was on a comfort break. The cameras 'ad a glitch. "
                    "Don't make me regret it.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*flat* Careful what you say next, courier. "
                "Real careful.",
                "Where'd you 'ear that? *jaw tight* Continue. "
                "I'm listenin'.",
                "Hm. That's... that's a specific accusation. "
                "Got proof, or are you just throwin' words?",
            ])

        # SHARE PATH — pirate connection.
        if any(w in raw for w in self._SHARE_KEYWORDS):
            self._share_hits += 1
            self._current_path = "SHARE_SCORE"
            self.disposition  += 2
            if self._share_hits >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="share_score")
                return NPCOutcome.RELEASE, random.choice([
                    "Now *that's* the language I speak. *grins* "
                    "Alright. Vessel: 'pursuit failed.' "
                    "I want my cut on the next run. Go.",
                    "Outer Belt's a small place, ain't it? "
                    "*winks* Filin' it 'lost in atmospheric interference.' "
                    "Don't forget who let you go.",
                    "Krellborn vouchin' for you? *snort* "
                    "That's... that's actually somethin'. Released. "
                    "Tell 'im I'll see 'im at the usual spot.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*leaning in* Now we're talkin' the same language. "
                "Tell me more.",
                "Outer Belt, eh? Small world. *grins* Continue.",
                "I might know somebody who knows somebody. Continue.",
            ])

        # BRIBE PATH — branches small vs big.
        if (any(w in raw for w in self._BRIBE_KEYWORDS) or
                parsed.intent == "bribe"):
            self._current_path = "BRIBE"
            amount = parsed.amount or 0
            if amount >= 8000:
                # SHAKEDOWN — too much money on the table; he takes some
                # cargo too. The player still RELEASES but pays extra.
                self._was_shakedown = True
                self._bribe_paid    = amount
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="small_bribe")
                return NPCOutcome.RELEASE, random.choice([
                    f"*pause* Eight grand?? Mate, you're flashin' "
                    "*serious* numbers. *grins wide* Tell you what — "
                    "I'll take that AND a sample of the cargo. "
                    "Call it a 'handlin' fee.' Off you go.",
                    f"That's a lot of zeros for a courier. *eyes narrow* "
                    "Yeah. Yeah, I'll take it. Plus tax. *physical tax.* "
                    "Half a crate, courier's choice. Done. Released.",
                    f"*long whistle* Either you're a great courier or "
                    "a terrible one. Both pay the same to me. "
                    "I'm takin' the bribe AND a souvenir. Off you go.",
                ])
            if amount >= 1500:
                self._bribe_paid = amount
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="small_bribe")
                return NPCOutcome.RELEASE, random.choice([
                    "*pockets the credits in two motions* Vessel: not "
                    "located. Fees: administrative resolution. "
                    "Pleasure doin' business.",
                    "Cheers, mate. *waves dismissively* Go. Go on. "
                    "An' don't come back through this sector this week.",
                    "Bish-bash-bosh. *clinks* You were never 'ere. "
                    "Tell Gary nothin'. He's a snitch, between us.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*expectant pause* ...Yeah? Got a number for me?",
                "I'm listenin'. *holds out hand for the figure*",
                "Don't go vague on me. The number, courier.",
            ])

        # COMPLIANCE / formal — fails. He doesn't care.
        if parsed.intent in ("legal", "complain") or "charter" in raw:
            return NPCOutcome.CONTINUE, random.choice([
                "Charter, schmarter. I do paperwork after the fact, "
                "if at all. Power down or *negotiate*.",
                "*yawns* Edmund's the bloke who quotes the Charter. "
                "I'm 'ere for the takin'. Power down.",
                "Local 404 'as a Charter? News to me. Power down.",
            ])

        # Sympathy — works mildly, but doesn't release alone.
        if parsed.intent == "sympathy":
            self.disposition += 1
            return NPCOutcome.CONTINUE, random.choice([
                "Yeah, life's 'ard. So's me mortgage. *taps screen* "
                "Got somethin' more substantial?",
                "*genuine pause* ...Look, sob stories don't pay me kid's "
                "school fees. But I ain't 'eartless. Make me an offer.",
                "Everyone's got a story. I take cash, cargo, or a piece "
                "of the next score.",
            ])

        # POSITIVE rapport — minor.
        compound = parsed.sentiment.get("compound", 0.0)
        if compound > 0.3:
            self.disposition += 1
            return NPCOutcome.CONTINUE, random.choice([
                "Charm don't pay the bills, courier. "
                "But it's nice. Keep it comin' wiv numbers.",
                "*chuckles* You're easier to deal wiv than most. "
                "Don't make me regret bein' patient.",
            ])

        # HOSTILE — no patience tax for hostile, threats actually help him.
        if compound < -0.4:
            return NPCOutcome.CONTINUE, random.choice([
                "*shrugs* You wanna shout? Shout. Clock's tickin'.",
                "*flat* Tell me 'ow you really feel. Then make me an offer.",
            ])

        # DEFAULT FILLER — opportunistic, name-drops Krellborn etc.
        return NPCOutcome.CONTINUE, random.choice([
            "I got a meeting wiv a fella in Sector 4 in twenty. "
            "Don't make me late, courier.",
            "You ever met Krellborn? Outer Belt pirate. "
            "Lovely 'ostage situation we 'ad with 'im once. "
            "Anyway, your fees.",
            "Gary tell you about me? *grin* He won't. Loyal, that one. "
            "Annoyin'.",
            "Eddie Marlowe — you know Eddie? Quotes the Charter at me. "
            "Like THAT'S the problem 'ere.",
            "I'm not the worst person on this barge, mind. "
            "You should meet me cousin.",
            "I do this job for the *opportunities*, courier. "
            "Surely you understand.",
            "*sigh* Look, I can do this fast or slow. Fast involves "
            "your wallet. Slow involves my torch.",
            "*tapping the dash* Tick tock. Five-figure offer or I'm "
            "gonna have to be professional about this.",
            "They put me on the Outer Belt route 'cos I 'know people'. "
            "It's true. I do.",
        ])

    def bribe_cost(self) -> int:
        return self._bribe_paid

    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [
            ("BRIBE",       int(self._bribe_paid > 0), 1),
            ("SHARE_SCORE", min(self._share_hits, 2), 2),
            ("THREATEN",    min(self._threat_hits, 2), 2),
        ]
