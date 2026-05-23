from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT


class Gary(BaseNPC):
    """
    Gary Pruitt — Local 404 Field Agent, 17 years service.

    Win paths (designed to feel discoverable in 3-4 natural turns):

    DEAL / NEGOTIATION  — say "deal", "reduce", "negotiate", "how about",
                          "settlement" etc. First attempt gets a clear
                          "I'm listening" response. Second attempt closes it.
                          One attempt if they include a specific % or "waive".

    BRIBE               — mention a specific amount ≥ 3000 cr with any bribe
                          keyword → immediate release. Vague bribe → Gary asks
                          for the number (one more turn).

    SYMPATHY            — desperation, family, please → disposition +2 per turn.
                          Two sympathetic turns → release. Gary's from the same
                          system and he knows it.

    MANAGEMENT COMPLAINT — complain about the union/quotas/overtime. Mention
                          "Blevins" for +3 disposition bonus. Reach +5 → release.

    THERAPY (Ch.1 cargo) — 3 turns of genuine emotional engagement → Gary calls
                          his sister, lets you go.

    ARTICLE 7 EXPLOIT   — say both "overtime" and "article 7" in one message.
                          Instant release on a technicality.

    FRIENDLY RAPPORT    — kind, patient tone builds disposition. Gary signals
                          clearly when you're close.
    """

    _DEAL_KEYWORDS = [
        "percent", "fifteen", "15%", "discount", "reduce", "knock off",
        "negotiate", "percentage", "portion", "split", "cut me",
        "deal", "settlement", "arrangement", "work something out",
        "how about", "what if", "reduction", "waive", "write off",
    ]
    _BRIBE_KEYWORDS = [
        "bribe", "pay", "credits", "money", "cash", "offer",
        "compensate", "buy", "slip", "transfer",
    ]
    _SYMPATHY_KEYWORDS = [
        "desperate", "please", "family", "kids", "children", "wife", "husband",
        "survive", "struggling", "starving", "no choice", "last run",
        "lost everything", "dying", "broke", "nothing left", "help me",
        "can't afford", "cannot afford", "just let me", "i'm begging", "begging",
    ]
    _BIG_AMOUNTS = [
        "five thousand", "ten thousand", "fifteen thousand", "twenty thousand",
        "thirty thousand", "fifty thousand",
        "5000", "10000", "15000", "20000",
        "5k", "10k", "15k", "20k", "30k", "50k",
        "five grand", "ten grand", "twenty grand",
    ]

    def __init__(self, cargo_ch1_active: bool = False, intercepted: bool = False,
                 run_context: dict | None = None):
        super().__init__("Gary", patience=9)
        self._therapy_mode     = cargo_ch1_active
        self._intercepted      = intercepted
        self._therapy_points   = 0
        self._bribe_attempts   = 0
        self._bribe_paid       = 0     # credit amount owed when bribe is accepted
        self._deal_attempts    = 0
        self._sympathy_turns   = 0
        self._management_turns = 0
        self._management_score = 0     # gated path counter — sympathy can't bleed into this
        self._article7_hit     = False
        self._sandra_turns     = 0
        self._ctx              = run_context or {}

    def _intro_line(self) -> str:
        if self._intercepted:
            return random.choice([
                "Oi! Gary Pruitt, Local 404. I am RIGHT BEHIND YOU. "
                "Outstanding fees on three vessels. "
                "Power down or we do this the 'ard way. Your call, mate.",
                "LOCAL 404 INTERCEPT. Gary Pruitt. "
                "I'm closing to harpoon range as we speak. "
                "Outstanding debt across seventeen jurisdictions. "
                "Talk fast or I shoot. Simple as.",
                "Gary Pruitt, repo an' recovery. I got you on radar. "
                "I'm twenty seconds from your hull. Outstanding fees. "
                "Power down NOW or this gets much worse for both of us.",
            ])
        run_snaps = self._ctx.get("run_snaps", 0)
        if run_snaps >= 2:
            return random.choice([
                f"Gary Pruitt, Local 404. You've snapped {run_snaps} of our harpoon "
                "cables this run. That's a property damage report on top of "
                "outstanding fees. Claims are already filing. Power down.",
                f"Gary Pruitt. I've been watchin' you on sector feed. "
                f"{run_snaps} harpoon snaps. Our tech team is LIVID. "
                "Outstanding fees, plus cable replacement costs. Power down.",
                f"Gary Pruitt, Local 404. Those harpoon cables aren't free. "
                f"{run_snaps} of 'em, written off this run. Neither is your debt. "
                "Power down and we'll talk about the damages.",
            ])
        hull_pct = self._ctx.get("hull_pct", 1.0)
        sector   = self._ctx.get("sector_index", 0)
        if hull_pct < 0.30:
            return random.choice([
                "Gary Pruitt, Local 404. Blimey — what 'appened to your 'ull, mate? "
                "You look like you've 'ad a rough one. Outstanding fees, mind. "
                "But also... you alright?",
                "Gary Pruitt. I got your vessel on scanner and... yeah, that 'ull reading's "
                "not great, is it. Outstanding fees. Wanna talk about it? "
                "No? Right. Power down.",
            ])
        if sector >= 7:
            return random.choice([
                "Gary Pruitt, Local 404. You've made it far, I'll give you that. "
                "Most don't get past sector five with these fees outstanding. "
                "Doesn't change anything. Power down.",
                "Gary Pruitt. I've been trackin' you since sector two. "
                "Outstanding fees. I 'onestly 'oped you'd make it further. "
                "Don't make this weird, yeah?",
            ])
        return (
            "Gary Pruitt, Local 404. You got outstanding fees on three "
            "registered vessels, mate. Gonna need you to power down "
            "an' submit to impound processin'. "
            "Don't make this weird, yeah?"
        )

    def exploits(self) -> dict[str, str]:
        return {
            "middle_management": "Mention Blevins by name",
            "overtime":          "Cite Article 7 forced overtime clause",
            "therapy":           "Talk him through his feelings (Ch.1 cargo)",
            "bribe":             "Offer enough credits",
            "deal_offer":        "Negotiate a reduction deal",
            "sympathy":          "Appeal to his humanity",
        }

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        # ARTICLE 7 EXPLOIT — cite the Article 7 forced overtime clause
        # Works with just "article 7" or the full phrase
        if "article 7" in raw or ("overtime" in raw and "article" in raw):
            self._article7_hit = True
            self._current_path = "ARTICLE 7"
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="overtime")
            return NPCOutcome.RELEASE, (
                "Oh that's— blimey, that's an Article 7 violation if you file it right. "
                "They can't touch your impound if there's a grievance pending. "
                "You're free on a technicality, mate. Don't tell Blevins. "
                "I was never 'ere."
            )

        # SYMPATHY PATH — new and naturalistic
        if (any(w in raw for w in self._SYMPATHY_KEYWORDS) or
                parsed.intent == "sympathy"):
            self._sympathy_turns += 1
            self._current_path    = "SYMPATHY"
            self.disposition += 2
            if self._sympathy_turns >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="sympathy")
                return NPCOutcome.RELEASE, random.choice([
                    "*long pause* ...Look. I got a mum on 'er fourth body. "
                    "Clone fluid ain't free either. I know 'ow this goes. "
                    "One time. Get out of 'ere. Don't make me regret it.",
                    "*sighs* ...You know what, sod the quota. "
                    "I'm not the villain in everyone's story. Go on. Go.",
                    "*quiet* I joined this job 'cos I needed the money too, yeah. "
                    "Don't broadcast that. Just go. "
                    "*marks form: 'vessel not located'*",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "...Look, I 'ear you. I genuinely do. "
                "But I got quotas and they don't care about circumstances.",
                "*quieter* Don't do that to me, mate. "
                "I'm tryin' to be professional 'ere.",
                "...That's rough. I'm not sayin' I'm unmoved. "
                "I'm sayin' keep talkin'.",
            ])

        # DEAL / NEGOTIATION PATH
        if (any(w in raw for w in self._DEAL_KEYWORDS) or
                parsed.intent == "negotiate"):
            self._deal_attempts += 1
            self._current_path   = "DEAL/NEGOTIATE"
            has_proposal = any(w in raw for w in [
                "percent", "%", "fifteen", "twenty", "thirty",
                "reduction", "waive", "write off", "settlement",
                "knock off", "portion", "cut",
            ])
            if self._deal_attempts >= 2 or has_proposal:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="deal_offer")
                return NPCOutcome.RELEASE, random.choice([
                    "*very long pause* ...Right. I'm not supposed to do this. "
                    "But I got seventeen more stops tonight an' me dogs are barkin'. "
                    "Fifteen percent off the fees, I mark it 'partial compliance', "
                    "we both go 'ome. Yeah? Yeah. Done. "
                    "Don't ring this number again. Cheers.",
                    "*sighs* ...Fine. FINE. "
                    "I write it up as 'disputed asset, released pending review'. "
                    "Buys you 48 hours. Don't waste 'em. "
                    "An' don't tell Blevins. He'll 'ave my badge.",
                    "You know what? It's been a LONG shift. "
                    "*taps screen* Reducin' fees by fifteen percent, "
                    "markin' 'cooperation noted'. That's the deal. Take it.",
                ])
            # First attempt — clearly signal to keep going
            return NPCOutcome.CONTINUE, random.choice([
                "A deal? *pause* ...You got my attention. "
                "What exactly are you proposin'?",
                "*slowly* Alright. I'm listenin'. "
                "What kind of arrangement did you 'ave in mind?",
                "Go on then. I'm not a market stall but I'm also not stupid. "
                "What's the offer?",
                "...'Ave you got an actual number, or are we still feelin' it out?",
            ])

        # BRIBE PATH
        if (any(w in raw for w in self._BRIBE_KEYWORDS) or
                parsed.intent == "bribe"):
            self._current_path = "BRIBE (3k+)"
            has_big = (any(amt in raw for amt in self._BIG_AMOUNTS) or
                       (parsed.amount is not None and parsed.amount >= 3000))
            if has_big:
                self._bribe_paid = parsed.amount if parsed.amount else 3000
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="bribe")
                return NPCOutcome.RELEASE, random.choice([
                    "*long pause* ...Right. I didn't see nuffin'. "
                    "Drive safe, yeah. An' tell your droid to stop broadcastin' "
                    "on our frequency. Cheers, mate.",
                    "*very quietly* Don't say the number out loud again. "
                    "The barges record audio. *tap* You're clear. Go.",
                    "*sound of form being filed very thoroughly* "
                    "Vessel: not located. Fees: administrative error. "
                    "Me conscience: also not located. Go on then.",
                ])
            self._bribe_attempts += 1
            if self._bribe_attempts == 1:
                return NPCOutcome.CONTINUE, random.choice([
                    "Now we're talkin'. What's the number, specifically?",
                    "I'm not NOT interested. Give me an actual figure.",
                    "*laughs* You're the first one today to try that. "
                    "What number are we talkin' about?",
                ])
            elif self._bribe_attempts >= 3:
                self.disposition += 1
                if self.disposition >= 3:
                    self._bribe_paid = parsed.amount if parsed.amount else 1000
                    return NPCOutcome.RELEASE, (
                        "Alright, alright. You know what, I'm tired. "
                        "It's been six stops and none of 'em 'ave offered me anyfing. "
                        "You at least 'ave the initiative. Go on. *waves hand* "
                        "Just don't tell Blevins."
                    )
            return NPCOutcome.CONTINUE, [
                "That's it? Me lunch costs more'n that. Come on.",
                "Look, I'm not sayin' the right number is twenty thousand. "
                "I'm not NOT sayin' it either.",
                "*sighs* Persistent. I'll give you that. "
                "More persistent would 'elp.",
            ][min(self._bribe_attempts - 1, 2)]

        # MANAGEMENT COMPLAINT — also triggers on "blevins" alone
        if ("blevins" in raw or "district supervisor" in raw or
                parsed.intent == "complain" or
                any(w in raw for w in [
                    "union", "management", "supervisor", "quota", "overtime",
                    "unfair", "underpaid", "bureaucracy", "system",
                ])):
            self._management_turns += 1
            self._current_path      = "BLEVINS METHOD"
            blevins_hit = "blevins" in raw or "district supervisor" in raw
            if blevins_hit:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="middle_management")
                self._management_score += 3
                self.disposition       += 3
            else:
                self._management_score += 1
                self.disposition       += 1
            if self._management_score >= 5:
                return NPCOutcome.RELEASE, random.choice([
                    "You know what? Blevins can tow it 'imself. "
                    "I'm on me break. Get out of 'ere. Shoo.",
                    "Right. That's it. I am NOT doin' this for Blevins's bonus. "
                    "Clear off. *stamps form 'vessel vacated premises'*",
                    "*quietly furious* Twenty-two years on this route. "
                    "Twenty-two years and Blevins gets the commendation. "
                    "...Go. Just go. Before I change me mind.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "...Yeah. The quotas are brutal, mate. "
                "Not that I'm agreein' wiv you. Power down.",
                "Union's been ridin' us 'ard lately. "
                "Doesn't mean you're off the 'ook though.",
                "...Blevins changed our tow quotas again. Mid-quarter. What a muppet.",
                "Seventeen stops tonight. SEVENTEEN. "
                "An' 'e wonders why morale's in the bin.",
                "I 'ear you, I do. Still got a job to do. You know 'ow it is.",
                "Tell me about it. *quieter* Tell me more about it actually.",
            ])

        # THERAPY PATH (Chapter 1 cargo active)
        if self._therapy_mode and parsed.intent in ("therapy", "philosophical", "sympathy"):
            self._therapy_points += 1
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="therapy")
            if self._therapy_points >= 3:
                return NPCOutcome.RELEASE, (
                    "*long silence* ...I 'aven't talked to anyone like that in years. "
                    "You're free to go, mate. I'm gonna ring me sister. "
                    "She's been on at me for months. *quietly* Cheers."
                )
            return NPCOutcome.CONTINUE, [
                "I just... I dunno why I'm even out 'ere anymore. "
                "The routes never end. *static* Sorry. Power down.",
                "Nobody asks 'ow *I'm* doin', you know? "
                "I'm the one wiv the 'arpoon.",
                "Me therapist says I 'catastrophize.' "
                "I said Dave, I work in SPACE DEBT COLLECTION.",
            ][min(self._therapy_points - 1, 2)]

        # POSITIVE RAPPORT
        compound = parsed.sentiment.get("compound", 0.0)
        if compound > 0.2 or parsed.intent in ("negotiate", "legal"):
            self.disposition += 1
            if self.disposition >= 5:
                return NPCOutcome.RELEASE, (
                    "Alright, alright. You seem like a decent enough sort. "
                    "I'll mark it 'unable to locate vessel'. "
                    "Don't make me regret it, yeah?"
                )
            if self.disposition >= 3:
                return NPCOutcome.CONTINUE, random.choice([
                    "...Look, you're bein' reasonable. That goes a long way. "
                    "Keep talkin'.",
                    "Nice try wiv the charm. I got feelings. "
                    "They're PROFESSIONAL feelings, but still.",
                    "You're alright, you know that? "
                    "Still got seventeen jurisdictions though.",
                    "*quieter* Look, I'm not heartless. "
                    "Just... give me somethin' to work with. Anyfing.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "...I appreciate the tone. Doesn't change the fees though.",
                "You're bein' reasonable. I'll give you that. "
                "Still need you to power down.",
            ])

        # HOSTILE
        if compound < -0.4 or parsed.intent == "threaten":
            self.disposition -= 1
            if self.disposition <= -4:
                self._patience = max(0, self._patience - 1)
            return NPCOutcome.CONTINUE, random.choice([
                "You wanna add 'resistin' impound' to the charges? "
                "Keep it up, mate.",
                "I've dealt wiv worse'n you. A lot worse. Power down.",
                "That's real charmin'. I'm addin' a 'andlin' fee.",
                "Blimey. You kiss your mum wiv that mouth?",
                "Right. Addin' that to the file. You're welcome.",
            ])

        # SANDRA — hidden path, never shown in dossier
        if "sandra" in raw:
            self._sandra_turns += 1
            self._current_path  = "SANDRA"
            self.disposition   += 2
            if self._sandra_turns >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="sympathy")
                return NPCOutcome.RELEASE, random.choice([
                    "*long silence* ...She's got the Meridian route now. Perfect impound rate. "
                    "Never missed a quota in fourteen years. "
                    "*quieter* I don't know why you brought her up but... "
                    "go on. Just. Go on. I'll mark it 'unverified vessel'.",
                    "*very quiet* ...Yeah. I know Sandra. "
                    "She's better at this than me. Always was. "
                    "...You know what, I'm gonna pretend I didn't see you. "
                    "Don't tell Blevins.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*pause* ...Sandra. Where did you — 'ow do you know that name?",
                "*quiet* ...Don't. Don't bring 'er into this. "
                "She's got nothing to do with your fees.",
            ])

        # DEFAULT — changes tone based on progress
        return NPCOutcome.CONTINUE, self._gary_filler()

    def bribe_cost(self) -> int:
        return self._bribe_paid

    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [
            ("DEAL/NEGOTIATE", min(self._deal_attempts, 2),    2),
            ("SYMPATHY",       min(self._sympathy_turns, 2),   2),
            ("BLEVINS METHOD", min(self._management_score, 5), 5),
            ("ARTICLE 7",      int(self._article7_hit),        1),
            ("BRIBE (3k+)",    min(self._bribe_attempts, 1),   1),
        ]

    def _gary_filler(self) -> str:
        # Signal when close
        if self.disposition >= 3:
            return random.choice([
                "...Look. You seem alright. "
                "Give me somethin' concrete and we can talk.",
                "I'm not sayin' I'm convinced. "
                "But I'm listenin'. That's somethin'.",
                "*quieter* What exactly are you proposin'? "
                "Cos I might — MIGHT — be open to it.",
                "You're wearin' me down. That's not a compliment. "
                "Keep goin'.",
            ])

        # Hint if player is stuck after 3 turns with zero progress
        if (self._turn >= 3 and self._deal_attempts == 0 and
                self._bribe_attempts == 0 and self._sympathy_turns == 0 and
                self.disposition <= 0):
            return random.choice([
                "*sighs* Look, I'm gonna level with you. "
                "I got two 'ours left on shift. "
                "Find an angle — a deal, a number, a story — "
                "and make it somethin' I can work with. "
                "I'm not made of stone. Mostly not.",
                "Alright look. *quieter* I've been doin' this twelve years. "
                "The ones who get out charm me, pay me, or confuse me. "
                "Pick one.",
                "...You know, most people just offer credits. Or they apologize. "
                "Or they mention their kids. "
                "Any of those would 'onestly be a nice change of pace.",
            ])

        # Run history callbacks — slingshots show Gary you know what you're doing
        run_slingshots = self._ctx.get("run_slingshots", 0)
        if run_slingshots >= 2 and self._turn <= 2 and random.random() < 0.30:
            return random.choice([
                f"You've been slingin' round them gravity wells like a professional. "
                "Proper navigation. Doesn't waive the fees, mind. Power down.",
                f"Two gravity assists at least. You know your way round a sector. "
                "Shame about the outstanding debt. Power down.",
            ])

        # Cross-NPC callbacks mixed in with filler
        if self._turn == 3 and random.random() < 0.3:
            return random.choice([
                "You know a bloke called Kress? Russian fella, sells... things. "
                "Not my department. But 'e's in this corridor a lot. "
                "If you've been dealin' wiv 'im, that's a separate file. Power down.",
                "They sent one of them TK units on our route for a week once. "
                "Talked to itself the whole time. Filed a 'loyalty subroutine error' "
                "on its own shift. We asked it to leave. "
                "Anyway. Your fees. Power down.",
                "Claims division rang me this mornin'. Apparently they denied your "
                "last three damage reports. Morwenna's department. "
                "That's between you an' 'er. Your fees are still my department. Power down.",
            ])

        hull_pct = self._ctx.get("hull_pct", 1.0)
        if hull_pct < 0.50 and random.random() < 0.25:
            return random.choice([
                "Your 'ull readings look rough, mate. "
                "Not my problem professionally, but... you been in a scrap?",
                "*glances scanner* That's a lot of structural damage for a courier run. "
                "What sector 'ave you been in? Power down, we'll talk.",
                "I've seen better 'ull readings on scrap barges. "
                "Seriously, what 'appened to you? ...Never mind. Power down.",
            ])

        return random.choice([
            "Look, I got a quota. Just power down.",
            "I don't make the rules. Well, the union makes some of 'em. Power down.",
            "You got anyfing in that cargo 'old I should know about?",
            "Me barge is blockin' traffic. Let's wrap this up, yeah?",
            "I've been doin' this route for six years. Just cooperate, mate.",
            "You're makin' this 'arder than it needs to be.",
            "Seventeen stops tonight. You're number six. Let's keep it movin'.",
            "I 'ad a microwave meal waitin' for me back at depot. "
            "It's probably stone cold now. Thanks for that.",
            "You ever just look at your life choices? "
            "Because I 'ave. Every Tuesday.",
            "Me 'arpoon calibration's a bit off. Don't make me test it on you.",
            "The union 'as a dental plan now. Still not worth it, if I'm 'onest.",
            "I got a bad knee from a tow-barge incident in Sector Four. "
            "I don't want to talk about it.",
            "Me mum still owes on 'er fourth body. "
            "Clone fluid fees don't stop just cos you're seventy. Power down.",
            "Blevins gets a bonus for every successful impound. "
            "I get a flat rate. That's incentive structure, apparently.",
            "Nova Soma sends a card every Christmas. "
            "'Thank you for your service.' To me. The repo man. Power down.",
            "You know what they call it in the charter? "
            "'Asset reclamation.' Not repo. Not debt collection. "
            "'Asset reclamation.' You're the asset. Power down.",
            "I've done seventeen 'undred impounds. Not one of 'em felt good. "
            "Not one. Power down so I can add you to the list.",
            "There's a pub back at depot. The Docking Ring. "
            "I'm missin' quiz night for this. Power. Down.",
            "My therapist says I 'struggle to disengage from work.' "
            "I said Dave, I AM at work. I AM in a barge. Power down.",
            "Union wellness initiative says I should take three deep breaths "
            "before each impound. I've done fifteen. Still stressed. Power down.",
            "You know 'ow many times I've 'eard 'it wasn't my fault'? "
            "Every single time. It's never anyone's fault. Power down.",
            "I 'ad a trainee last month. Lovely kid. Quit after two weeks. "
            "Said the moral weight was unbearable. "
            "I said welcome to Tuesday, son. Power down.",
            "The union 'as a pension. I checked. It's 'theoretical.' Their word. Power down.",
            "Last pilot I let go called me a good man. "
            "That was three years ago and I still fink about it. Power down.",
            "I know you think there's a way out of this. "
            "That's good. 'Old onto that. Now power down.",
        ])
