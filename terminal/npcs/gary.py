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
    - 15% deal: use deal/percent/discount keywords twice and Gary folds.
    """

    SUPERVISOR_NAME = "District Supervisor Blevins"

    _BRIBE_KEYWORDS  = ["bribe", "pay", "credits", "money", "cash", "offer",
                         "compensate", "deal", "buy"]
    _BIG_AMOUNTS     = ["five thousand", "10k", "ten thousand", "15k", "twenty",
                         "20k", "fifty", "50k", "hundred", "a lot"]
    _DEAL_KEYWORDS   = ["percent", "fifteen", "15%", "cut me", "how about",
                         "discount", "reduce", "knock off", "negotiate",
                         "percentage", "portion", "fraction", "split"]

    def __init__(self, cargo_ch1_active: bool = False, intercepted: bool = False):
        super().__init__("Gary", patience=7)
        self._therapy_mode    = cargo_ch1_active
        self._intercepted     = intercepted
        self._therapy_points  = 0
        self._bribe_attempts  = 0
        self._deal_attempts   = 0

    def _intro_line(self) -> str:
        if self._intercepted:
            return random.choice([
                "Oi! Gary Pruitt, Local 404. I am RIGHT BEHIND YOU. "
                "You've got outstanding fees on three vessels an' I've got "
                "a harpoon with your name on it. Power down or we do this the 'ard way.",
                "LOCAL 404 INTERCEPT. Gary Pruitt speakin'. "
                "I'm closin' to harpoon range as we speak, mate. "
                "Outstanding debt across seventeen jurisdictions. "
                "You gonna talk or am I gonna shoot?",
                "Gary Pruitt, repo an' recovery. I got you on radar an' I'm "
                "twenty seconds from your hull. "
                "Outstanding fees. Three vessels. Power down NOW "
                "or this gets a lot worse for both of us.",
            ])
        return (
            "Gary Pruitt, Local 404. You got outstanding fees on three "
            "registered vessels, mate. Gonna need you to power down "
            "an' submit to impound processin'. "
            "Don't make this weird, yeah?"
        )

    def exploits(self) -> dict[str, str]:
        return {
            "middle_management": "Complain about Blevins by name",
            "overtime":          "Cite Article 7 forced overtime clause",
            "therapy":           "Act as an amateur therapist (Ch.1 cargo active)",
            "bribe":             "Offer enough credits",
            "deal_offer":        "Negotiate a 15% reduction deal",
        }

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        # ARTICLE 7 EXPLOIT
        if "overtime" in raw and "article 7" in raw:
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="overtime")
            return NPCOutcome.RELEASE, (
                "Oh that's— blimey, that's an Article 7 violation if you file it right. "
                "They can't touch your impound if there's a grievance pending. "
                "You're free on a technicality, mate. Don't tell Blevins. "
                "I was never 'ere."
            )

        # 15% DEAL PATH — two deal/discount mentions and Gary folds
        if any(w in raw for w in self._DEAL_KEYWORDS):
            self._deal_attempts += 1
            if self._deal_attempts >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="deal_offer")
                return NPCOutcome.RELEASE, (
                    "*very long pause* ...Right. I'm not supposed to do this. "
                    "But I got seventeen more stops tonight an' me dogs are barkin'. "
                    "Fifteen percent off the fees, I mark it 'partial compliance', "
                    "we both go 'ome. Yeah? Yeah. Done. "
                    "Don't ring this number again. Cheers."
                )
            return NPCOutcome.CONTINUE, random.choice([
                "Fifteen percent? You fink I'm a market stall? I'm the Union, mate.",
                "A deal. *laughs* Mate, the fees ARE the deal. This is me bein' generous.",
                "Negotiate. Right. Bold. Still gonna need you to power down though.",
                "You've got a nerve, I'll give you that. Wrong number though, innit.",
            ])

        # BRIBE PATH
        if any(w in raw for w in self._BRIBE_KEYWORDS) or parsed.intent == "bribe":
            if any(amt in raw for amt in self._BIG_AMOUNTS):
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="bribe")
                return NPCOutcome.RELEASE, (
                    "*long pause* ...Right. I didn't see nuffin'. Drive safe, yeah. "
                    "An' tell your droid to stop broadcastin' on our frequency. "
                    "Cheers, mate."
                )
            self._bribe_attempts += 1
            if self._bribe_attempts >= 3:
                self.disposition += 2
                if self.disposition >= 3:
                    return NPCOutcome.RELEASE, (
                        "*long pause* You know what? Sod it. I got eleven more stops tonight "
                        "an' you ain't worth the paperwork. Get out of 'ere, go on."
                    )
            responses = [
                "You fink I do this for the credits? I do it for the pension, mate. Try 'arder.",
                "That's it? Me lunch costs more'n that. Come on, I'm not made of stone.",
                "Look, I'm not sayin' the right number is twenty fousand. "
                "I'm not NOT sayin' it either.",
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
                    "You know what? Blevins can tow it 'imself. "
                    "I'm on me break. Get out of 'ere, go on. Shoo."
                )
            return NPCOutcome.CONTINUE, random.choice([
                "...Yeah. The quotas are brutal, mate. Not that I'm agreein' wiv you. Power down.",
                "Union's been ridin' us 'ard lately. Doesn't mean you're off the 'ook though.",
                "I 'ear you, I do. Still got a job to do. You know 'ow it is.",
                "...Blevins changed our tow quotas again. Mid-quarter. What a muppet.",
                "Seventeen stops tonight. SEVENTEEN. An' 'e wonders why morale's in the bin.",
            ])

        # THERAPY (Chapter 1 cargo active)
        if self._therapy_mode and parsed.intent in ("therapy", "philosophical"):
            self._therapy_points += 1
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="therapy")
            if self._therapy_points >= 3:
                return NPCOutcome.RELEASE, (
                    "*long silence* ...I 'aven't talked to anyone like that in years. "
                    "You're free to go, mate. I'm gonna ring me sister. "
                    "She's been on at me for months."
                )
            return NPCOutcome.CONTINUE, [
                "I just... I dunno why I'm even out 'ere anymore. The routes never end.",
                "Nobody asks 'ow *I'm* doin', you know? I'm the one wiv the 'arpoon.",
                "Me therapist says I 'catastrophize.' I said Dave, I work in SPACE DEBT COLLECTION.",
            ][min(self._therapy_points - 1, 2)]

        # POSITIVE RAPPORT
        compound = parsed.sentiment.get("compound", 0.0)
        if compound > 0.25 or parsed.intent in ("negotiate", "legal"):
            self.disposition += 1
            if self.disposition >= 5:
                return NPCOutcome.RELEASE, (
                    "Alright, alright. You seem like a decent enough sort. "
                    "I'll mark it as 'unable to locate vessel'. "
                    "Don't make me regret it, yeah?"
                )
            return NPCOutcome.CONTINUE, random.choice([
                "...Look, I appreciate the tone. Doesn't change the fees though.",
                "You're bein' reasonable. I'll give you that. Still need you to power down.",
                "Nice try wiv the charm. I got feelings. They're just... professional feelings.",
                "You're alright, you know that? Shame about the seventeen jurisdictions.",
            ])

        # HOSTILE
        if compound < -0.4 or parsed.intent == "threaten":
            self.disposition -= 1
            if self.disposition <= -4:
                self._patience = max(0, self._patience - 1)
            return NPCOutcome.CONTINUE, random.choice([
                "You wanna add 'resistin' impound' to the charges? Keep it up, mate.",
                "I've dealt wiv worse'n you. A lot worse. Power down.",
                "That's real charmin'. I'm addin' a 'andlin' fee.",
                "Blimey. You kiss your mum wiv that mouth?",
                "Right. Addin' that to the file. You're welcome.",
            ])

        # DEFAULT FILLER
        return NPCOutcome.CONTINUE, self._gary_filler()

    def _gary_filler(self) -> str:
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
            "You ever just look at your life choices? Because I 'ave. Every Tuesday.",
            "Me 'arpoon calibration's a bit off. Don't make me test it on you.",
            "The union 'as a dental plan now. Still not worth it, if I'm 'onest.",
            "I got a bad knee from a tow-barge incident in Sector Four. "
            "I don't want to talk about it.",
            "Me ex-wife said I'd never amount to anyfing. "
            "I said Sandra, I am a LICENSED REPO AGENT. She still left.",
            "Fun fact: space debt never expires. It's actually written into the charter.",
            "You're stop number six of seventeen. I peaked at four. It's all downhill.",
            # the knife — Gary as victim of the same system
            "Me mum still owes on 'er fourth body. Clone fluid fees don't stop "
            "just cos you're seventy. Power down.",
            "Blevins gets a bonus for every successful impound. "
            "I get a flat rate. That's called incentive structure, apparently.",
            "I joined the union cos they said it'd protect us. "
            "That was... a different union. Power down.",
            "Nova Soma sends a card every Christmas. 'Thank you for your service.' "
            "To me. The repo man. Power down.",
            "You know what they call it in the charter? "
            "'Asset reclamation.' Not repo. Not debt collection. "
            "'Asset reclamation.' You're the asset. Power down.",
            "I asked 'R about early retirement once. "
            "She said the pension kicks in at 68. I said 68 what. "
            "She 'ung up. Power down.",
        ])
