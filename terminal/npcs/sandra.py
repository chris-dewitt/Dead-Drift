from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT


class Sandra(BaseNPC):
    """
    Sandra Vega-Marsh — the "perfect courier."

    Local 404 holds her up as the gold standard. Never impounded.
    Perfect quotas. Twelve years with no damage report. Gary mentions
    her constantly. So does Blevins. So do you, internally, in your
    worst moments.

    She intercepts you on the gate channel because she can. Because
    she's curious who the system flagged as "RUNNER-CHRONIC". Because
    she's bored.

    Paths to release:
    - INTEL TRADE      : offer something she doesn't know (Blevins gossip,
                         exploit hints from your vault) → trade for safe passage
    - SOLIDARITY       : frame couriers as workers, not rivals (3 turns)
    - OUTPERFORM CLAIM : convincingly boast about run stats (snaps/slingshots)
    - CONFESSION       : make HER admit she's the system's favourite tool
                         → she short-circuits and lets you go
    - APOLOGY          : grovel for 3 turns. She HATES it but it works
    """

    _SOLIDARITY_KEYWORDS = [
        "worker", "workers", "union", "labour", "labor", "exploited", "exploit",
        "same boat", "same side", "we both", "fellow", "courier",
        "we all", "system", "rigged", "unfair", "underpaid",
        # extended solidarity vocabulary
        "solidarity", "together", "united", "we're the same", "not so different",
        "all workers", "fellow workers", "we struggle", "shared struggle",
        "same struggle", "we're tools", "they use us", "disposable",
        "all of us", "work the same", "both of us", "both couriers",
        "we both run", "same routes", "quota system",
    ]
    _INTEL_KEYWORDS = [
        "blevins", "supervisor", "tip", "intel", "gossip", "heard",
        "rumour", "rumor", "know something", "let me tell you",
        "between us", "off the record", "off record",
        # extended intel vocabulary
        "secret", "whisper", "confidential", "exclusive", "don't tell",
        "heard something", "pass this on", "keep this quiet",
        "just between us", "something you should know",
    ]
    _BOAST_KEYWORDS = [
        "snap", "snaps", "slingshot", "sling", "drift", "harpoon",
        "tether", "outran", "beat", "faster", "better", "outperformed",
        "outflew", "logged",
        # extended boast vocabulary
        "escaped", "evaded", "dodged", "clean run", "no hits",
        "pulled off", "zero hits", "outpaced", "lost them",
        "shook them", "ran the sector", "perfect run", "record time",
        "did it clean", "no damage", "snapped it",
    ]
    _CONFESSION_KEYWORDS = [
        "favourite", "favorite", "pet", "show pony", "trophy",
        "puppet", "tool", "used", "complicit", "their property",
        "their courier", "their poster", "they own", "owned",
        # extended confession vocabulary
        "poster child", "mascot", "golden", "role model",
        "model courier", "propaganda", "they use you", "showcase you",
        "golden girl", "golden boy", "their golden", "their darling",
        "their example", "held up as", "used as", "you're their",
        "made an example", "the example", "proof of concept",
    ]
    _APOLOGY_KEYWORDS = [
        "sorry", "apologise", "apologize", "my fault", "my bad",
        "wrong", "shouldn't have", "regret", "forgive", "humble",
    ]
    _GARY_KEYWORDS = [
        "gary", "pruitt", "partner", "partners", "meridian",
        "old route", "worked together", "local 404 field agent",
    ]

    def __init__(self, run_context: dict | None = None, **_):
        super().__init__("Sandra", patience=8)
        self._intel_offered    = 0
        self._solidarity_turns = 0
        self._boast_turns      = 0
        self._confession_score = 0
        self._apology_turns    = 0
        self._gary_turns       = 0
        self._ctx              = run_context or {}

    # ------------------------------------------------------------------
    def _intro_line(self) -> str:
        snaps = self._ctx.get("run_snaps", 0)
        if snaps >= 2:
            return random.choice([
                "Sandra Vega-Marsh. Local 404 courier ledger, top of the page. "
                f"I see you've snapped {snaps} of our harpoons this run. "
                "Bold. Bordering on rude. Care to explain?",
                "Sandra. Sandra Vega-Marsh. You don't know me. "
                "But the gate system DOES, and it just flagged your manifest. "
                f"Twelve years of perfect quotas, and you've snapped {snaps} cables this run alone. "
                "I want to know why.",
            ])
        return random.choice([
            "Sandra Vega-Marsh. I'm the courier they compare you to. "
            "Or rather — that they compare you UNFAVOURABLY to. "
            "Just wanted to put a voice to the name. Hi.",
            "This is Sandra. You've probably heard about me from Gary. "
            "Or Blevins. Or the entire dispatch board. "
            "Twelve years, no impounds. I was curious. Hello.",
            "Sandra Vega-Marsh, gate authority — secondary courier line. "
            "I'm clearing you through but I wanted to say hello first. "
            "We're in the same job. Sort of. Not really. Hello.",
        ])

    def exploits(self) -> dict[str, str]:
        return {
            "rival_intel":  "Trade something she doesn't know",
            "solidarity":   "Frame couriers as fellow workers",
            "outperform":   "Out-boast her with actual run stats",
            "confession":   "Make her admit she's the system's tool",
            "apology":      "Grovel sincerely for three turns",
            "gary_history":  "Ask what happened with Gary Pruitt",
        }

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        # GARY HISTORY -- hidden texture path shared with Gary's Sandra branch.
        if any(w in raw for w in self._GARY_KEYWORDS):
            self._gary_turns += 1
            self._current_path = "GARY HISTORY"
            self.disposition += 1
            if self._gary_turns >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="gary_history")
                return NPCOutcome.RELEASE, random.choice([
                    "*long pause* Gary was my partner before the Meridian incident. "
                    "He froze; I filed the report that protected him because I thought "
                    "the Union protected people. They promoted me into propaganda and "
                    "left him holding the shame. I owe him an apology. You get passage.",
                    "Gary Pruitt is not a punchline. He was a good partner on a bad night. "
                    "I let them turn my survival into his failure. That is on me. "
                    "*quieter* Gate's open. Go before I make this official.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*tight inhale* Gary told you something, didn't he.",
                "Pruitt and I worked Meridian together. If you know that name, keep talking carefully.",
            ])

        # INTEL TRADE — fastest path, one good piece of gossip + a follow-up
        if any(w in raw for w in self._INTEL_KEYWORDS):
            self._intel_offered  += 1
            self._current_path    = "INTEL TRADE"
            self.disposition     += 2
            blevins_specific = "blevins" in raw and ("affair" in raw or
                                                     "audit" in raw or
                                                     "bonus" in raw or
                                                     "skim" in raw or
                                                     "fudge" in raw)
            if blevins_specific or self._intel_offered >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="rival_intel")
                return NPCOutcome.RELEASE, random.choice([
                    "*long pause* ...That's actually new to me. "
                    "And I make a point of knowing everything. "
                    "Fine. Gate's open. Don't get used to this.",
                    "Hmh. I'll cross-reference that. "
                    "You're cleared. For now. Don't make me regret it. "
                    "And don't bring it up again.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "...Go on.",
                "Specifics, please. I deal in facts, not implications.",
                "That's the appetiser. I want the rest of it. Now.",
            ])

        # SOLIDARITY — needs accumulation
        if any(w in raw for w in self._SOLIDARITY_KEYWORDS):
            self._solidarity_turns += 1
            self._current_path      = "SOLIDARITY"
            self.disposition       += 1
            if self._solidarity_turns >= 3:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="solidarity")
                return NPCOutcome.RELEASE, (
                    "*long silence* ...You're not entirely wrong. "
                    "I file the same forms. I bleed when I scrape a hull. "
                    "I just don't talk about it. "
                    "*quietly* Go on through. I'll mark you 'verified compliant'. "
                    "We didn't have this conversation."
                )
            return NPCOutcome.CONTINUE, random.choice([
                "*pause* ...I don't think of myself as a worker. "
                "I think of myself as a courier. There's a difference. "
                "...Isn't there?",
                "We are NOT on the same side. I have a SPOTLESS record. "
                "Yours reads like a true-crime podcast. "
                "...Keep going though.",
                "I'm aware the system is what it is. "
                "I just decided not to lose to it. That's all.",
            ])

        # BOAST — outperform via run stats
        if any(w in raw for w in self._BOAST_KEYWORDS):
            self._boast_turns += 1
            self._current_path = "OUTPERFORM"
            # Verify with actual run stats — boasts only land if backed by ctx
            run_snaps      = self._ctx.get("run_snaps", 0)
            run_slingshots = self._ctx.get("run_slingshots", 0)
            credible = run_snaps >= 2 or run_slingshots >= 2
            if credible and self._boast_turns >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="outperform")
                return NPCOutcome.RELEASE, random.choice([
                    f"*checks scanner* ...You've actually snapped {run_snaps} cables. "
                    f"And the gravity assists log... {run_slingshots}. "
                    "Damn it. Pass. *quieter* I'll need to reread the manual. "
                    "Don't tell Blevins.",
                    "*long pause* You know what — congratulations. "
                    "That's actual flying. I'm letting you through. "
                    "Don't make a habit of it.",
                ])
            if not credible:
                self.disposition -= 1
                return NPCOutcome.CONTINUE, random.choice([
                    "Big words. Records don't agree. Try again, sober this time.",
                    "Talk is cheap. I'm pulling your run log. "
                    "Nothing flashy on it. Care to amend the claim?",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "Mm. Numbers? Specifics? Or vibes?",
                "Continue. I'm taking notes.",
            ])

        # CONFESSION — turn her own pride against her
        if any(w in raw for w in self._CONFESSION_KEYWORDS):
            self._confession_score += 2
            self._current_path      = "CONFESSION"
            self.disposition       += 0   # this isn't about being liked
            if self._confession_score >= 4:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="confession")
                return NPCOutcome.EXPLOIT, (
                    "*very long pause* "
                    "...I'm their poster, aren't I. "
                    "I'm the picture they show new recruits. "
                    "I'm — *click* — I need to take this conversation offline. "
                    "Gate's open. Walk through. Forget my name. "
                    "*the channel cuts*"
                )
            return NPCOutcome.CONTINUE, random.choice([
                "*tight* ...That's a strange thing to say to me.",
                "I'm not their tool. I'm their best CONTRACTOR. "
                "There's a difference. There is.",
                "*pause* Keep talking. I'm... interested in your angle.",
            ])

        # APOLOGY — she hates it but it cumulatively works
        if any(w in raw for w in self._APOLOGY_KEYWORDS):
            self._apology_turns += 1
            self._current_path   = "APOLOGY"
            self.disposition    += 1
            if self._apology_turns >= 3:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="apology")
                return NPCOutcome.RELEASE, (
                    "*sighs heavily* You sound genuinely pathetic. "
                    "That's the only reason I'm doing this. "
                    "Go. Quietly. I'm filing this as 'self-corrected behaviour'."
                )
            return NPCOutcome.CONTINUE, random.choice([
                "*dry* Mm. Keep going.",
                "An apology. Novel. From you. Continue.",
                "I'm not impressed but I'm not stopping you. Yet.",
            ])

        # Hostile
        compound = parsed.sentiment.get("compound", 0.0)
        if compound < -0.4 or parsed.intent == "threaten":
            self.disposition -= 2
            return NPCOutcome.CONTINUE, random.choice([
                "Charming. Adding 'courier hostility' to your already substantial file.",
                "Threaten me again. I dare you. I have a SPOTLESS record "
                "to weaponize against you.",
                "*coolly* You will not impress me with anger. Try competence.",
            ])

        return NPCOutcome.CONTINUE, self._sandra_filler()

    # ------------------------------------------------------------------
    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [
            ("INTEL TRADE",  min(self._intel_offered, 2),     2),
            ("SOLIDARITY",   min(self._solidarity_turns, 3),  3),
            ("OUTPERFORM",   min(self._boast_turns, 2),       2),
            ("CONFESSION",   min(self._confession_score, 4),  4),
            ("APOLOGY",      min(self._apology_turns, 3),     3),
            ("GARY HISTORY",  min(self._gary_turns, 2),        2),
        ]

    def _sandra_filler(self) -> str:
        return random.choice([
            "I've been doing this for twelve years. "
            "I haven't lost a cable. Not one. Not even when the harpoon "
            "calibration went sideways in '38. I just landed it manually. "
            "Did Gary tell you that? He should have.",
            "You know what they call my record at dispatch? "
            "'The Vega Curve.' Look it up. It's a quota baseline now. "
            "Couriers train against MY numbers. Just so you know who you're talking to.",
            "I've been monitoring your radio for three sectors. "
            "Your droid's funny. Crude, but funny. "
            "You should listen to him more.",
            "I genuinely don't dislike you. I just think you're sloppy. "
            "Those are different things. Most pilots can't tell.",
            "Blevins offered me a supervisor position last quarter. "
            "I turned it down. I prefer the field. Less paperwork. "
            "Tell Gary that, next time you see him. He'll lose his mind.",
            "Your ship's mass-to-thrust ratio is bizarrely inefficient. "
            "I'm not insulting you. I'm just observing. Out loud. "
            "While you can hear me.",
            "I bought a flat last year. In the Solis arcology. "
            "Three rooms. A balcony. I don't bring it up to brag. "
            "I bring it up because you don't have one. And I want you to know I know.",
            "The Union runs a yearly courier ranking. I've been first place "
            "every quarter since '36. Your highest rank was 'unranked — "
            "incident pending'. Just thought you should know your standing.",
            "Your run history reads like a structural-failure case study. "
            "I've read it. Twice. For research.",
            "I'm not going to impound you. I just wanted to talk. "
            "Honestly. ...Mostly honestly.",

            "Courier Dray operates on the same sector band. "
            "I've reviewed his run logs. Creative is the word I'd use. "
            "'Creative' meaning wrong. "
            "He also hasn't been impounded in fourteen runs. "
            "I find that statistically offensive.",

            "An unlicensed relay broker offered to clear my last checkpoint. "
            "Three hundred credits. For me. "
            "I reported him immediately. His name is Felix. "
            "I want him to know I reported him. "
            "I'm noting it here in case you know him.",

            "I encountered a TK-9 compliance unit last sector. "
            "Pre-filed everything. Correct codes. Both forms. "
            "It still cross-referenced my clone iteration. "
            "I cited Exemption 12-C. It paused for four seconds. "
            "That's the nearest I've come to an apology from a machine.",

            "There's a field medic out of Bay 9. Doctor Voss, off the books. "
            "Apparently very good with hull repairs. "
            "I don't use Bay 9. I also don't take hull damage. "
            "Those two facts are directly related.",

            "An information broker has been selling my route data. "
            "'Competitive intelligence.' His name rhymes with stress. "
            "I've filed three complaints. They're all pending. "
            "Kress is still selling my data. I'm told this is legal.",
        ])
