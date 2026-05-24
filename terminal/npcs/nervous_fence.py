"""
Nervous Fence — shady mid-route contact. Runs a grey-market relay station.
Sells intel on barge patrol routes in exchange for cargo manifests or credits.
Desperately wants to be legitimate one day. Isn't.

Outcomes:
  DEAL      : offer cargo manifest or "partial contents" → intel package, no barge
  CREDIT    : credits >= 800 → takes the money, gives patrol route
  SYMPATHY  : shared outsider status (debt/clone/owe) → 50% gives free intel
  DISTRACT  : ask about his side business, his "plans," his "real work"
              → he talks too long, forgets to flag you (3 turns)
  HOSTILE   : threaten or expose → calls barge, destroys channel
"""
from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT

_DEAL_KEYWORDS = [
    "manifest", "contents", "partial contents", "cargo list",
    "what's inside", "show you", "tell you what", "give you",
    "trade", "exchange", "deal", "swap", "offer you",
]
_CREDIT_AMOUNT = 800
_SYMPATHY_KEYWORDS = [
    "debt", "clone", "owe", "broke", "same boat", "one of us",
    "just trying", "trying to survive", "trying to get by",
    "not that different", "we're the same", "understand",
    "struggling", "system", "corpo", "corporation", "nova soma",
]
_DISTRACT_KEYWORDS = [
    "plan", "plans", "legitimate", "real work", "business",
    "what do you do", "tell me about", "your operation",
    "side hustle", "when you're done", "getting out",
    "one day", "dream", "future", "retire",
]
_HOSTILE_KEYWORDS = [
    "report", "expose", "authority", "turn you in", "rat",
    "illegal", "arrest", "warrant", "snitch", "grass you up",
    "not your friend", "who are you", "prove it", "scan",
]


class NervousFence(BaseNPC):
    """Grey-market relay contact. Will trade intel for discretion."""

    def __init__(self, vocabulary_vault=None, run_context: dict | None = None, **_):
        super().__init__("RELAY-7 FELIX", patience=7)
        self._vault         = vocabulary_vault
        self._ctx           = run_context or {}
        self._deal_offered  = False
        self._paid          = False
        self._distract_t    = 0
        self._sympathy_t    = 0
        self._spooked       = False

    def _intro_line(self) -> str:
        return random.choice([
            "*whispering* Hey. Hey. You're on the relay channel. "
            "I'm — look, I'm not official, alright? I run a... logistics node. "
            "Heard your transponder. I can make the next gate easier. "
            "We just need to come to an arrangement. Quickly. Please quickly.",

            "Relay-7. Felix. Don't file that name anywhere. "
            "*nervous laugh* I have patrol schedules. Full barge routes. "
            "I'm willing to share. All I need is... goodwill. Some goodwill. "
            "And possibly some information about what you're carrying.",

            "*static burst* Oh good you're there. Okay. Okay. "
            "I can clear the next checkpoint. I know people. "
            "By 'people' I mean I have their schedules and they don't know I have them. "
            "Can we just... let's just come to an arrangement. Fast. Please.",

            "You've picked up a private relay channel. That's me. Felix. "
            "I'm not supposed to be operating here but who is these days. "
            "I know where the barges are going to be. "
            "You want that? I want something small in return. Very small.",
        ])

    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        if any(w in raw for w in _HOSTILE_KEYWORDS):
            self._spooked = True
            self._patience = 0
            return NPCOutcome.IMPOUND, random.choice([
                "*static* Okay. Okay no. If you're going to be like that — "
                "*channel activity* I'm flagging this channel. I'm sorry. "
                "I have to protect the relay. I'm sorry.",

                "Expose me? I — *pause* "
                "I've already sent a proximity ping to the nearest barge. "
                "I didn't want to. You made me. I'm really sorry.",

                "*genuine distress* You don't have to threaten me. "
                "I'm just a guy. I'm just trying to get by. "
                "*barge dispatch tone in background* They're on their way.",
            ])

        if any(w in raw for w in _DEAL_KEYWORDS):
            self._deal_offered = True
            self._current_path = "DEAL"
            bus.emit(EVT_NLP_EXPLOIT, npc="nervous_fence", exploit_key="cargo_manifest")
            if self._vault:
                self._vault.record("nervous_fence", "MANIFEST_DEAL")
            return NPCOutcome.RELEASE, random.choice([
                "*relieved exhale* Yes. Yes that works. Perfect. "
                "Sending you the barge corridor map now. "
                "Three checkpoints cleared for the next forty minutes. "
                "You didn't get this from me. Obviously. Thank you. Okay. Bye.",

                "That's — yes. That's exactly what I needed. "
                "Gate Seven, Nine, and Eleven: cleared. "
                "This channel never existed. "
                "*hurried* Good luck out there. You'll be fine.",

                "*typing sounds* Uploading patrol schedule. "
                "It's not the most current but it's real. "
                "You're clear for the next sector. Don't tell anyone about Felix.",
            ])

        if parsed.amount is not None and parsed.amount >= _CREDIT_AMOUNT:
            self._paid = True
            self._current_path = "CREDIT DEAL"
            bus.emit(EVT_NLP_EXPLOIT, npc="nervous_fence", exploit_key="credit_deal")
            if self._vault:
                self._vault.record("nervous_fence", "CREDIT_DEAL")
            return NPCOutcome.RELEASE, random.choice([
                f"*quietly* {parsed.amount} credits. That's... generous for what I'm giving you. "
                "Route clear. Three sectors. Thank you. "
                "*warmly* You're a decent person. Probably.",

                "Credits received. Very good. Very professional. "
                "Patrol schedules uploaded. Gate operators notified. "
                "*pause* Well. 'Notified' is strong. They've been distracted. "
                "Same thing. Go on through.",
            ])

        if any(w in raw for w in _SYMPATHY_KEYWORDS):
            self._sympathy_t += 1
            self._current_path = "SYMPATHY"
            self.disposition += 2
            if random.random() < 0.5:
                bus.emit(EVT_NLP_EXPLOIT, npc="nervous_fence", exploit_key="shared_outsider")
                if self._vault:
                    self._vault.record("nervous_fence", "SHARED_OUTSIDER")
                return NPCOutcome.RELEASE, random.choice([
                    "*long pause* ...Yeah. Yeah, I know. "
                    "I've got clone debt too. Three payments behind. "
                    "*quietly* Go through. Gate's open. "
                    "Don't make me regret being soft about this.",

                    "Clone debt. Nova Soma. They've got us all. "
                    "*sighs* You know what, just go. "
                    "Sector's clear. We never spoke. "
                    "I hope your delivery lands.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*softening* I hear you. I really do. "
                "Give me something I can work with on my end though.",
                "We're not so different, you and me. ...What are you carrying though.",
                "That's... that's real. *pause* I still need something from you though.",
            ])

        if any(w in raw for w in _DISTRACT_KEYWORDS):
            self._distract_t += 1
            self._current_path = "DISTRACT"
            self.disposition += 1
            if self._distract_t >= 3:
                bus.emit(EVT_NLP_EXPLOIT, npc="nervous_fence", exploit_key="distraction")
                if self._vault:
                    self._vault.record("nervous_fence", "DISTRACTION")
                return NPCOutcome.RELEASE, random.choice([
                    "*embarrassed* Oh I've been talking for — "
                    "I do this. I talk too much about the plan. Bax always said — "
                    "I mean, someone always said — "
                    "*flustered* Just go. Gate's open. I'll file the form retroactively.",

                    "...and that's why I think with enough capital and the right permits "
                    "I could run a legitimate — *pause* "
                    "Wait. How long have we been talking. "
                    "I've... I've missed the checkpoint window. Go. "
                    "You did that on purpose, didn't you. I respect that.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*brightening* Oh, the plan! The plan is — "
                "well, it starts with capital accumulation, which is where the relay comes in.",
                "The legitimate business? It's a transit consultancy. "
                "Not unlike what I do now but with a license and a better chair.",
                "I've got a whole roadmap. Five years, maybe six. "
                "Phase One is already underway technically.",
            ])

        return NPCOutcome.CONTINUE, self._nervous_filler()

    def _nervous_filler(self) -> str:
        return random.choice([
            "*anxious* Come on. Come on. I don't have a lot of time here.",
            "The barge ping window is closing. Work with me.",
            "I'm not trying to scam you. This is a genuine arrangement.",
            "*checks something* You've got maybe ninety seconds before the gate auto-flags.",
            "I have a system. It works. You just need to engage with it.",
            "Nobody has to know about this. That's the whole beauty of relay comms.",
            "*whispers* I'm good at what I do. I'm just also technically unlicensed.",
            "Look, I've cleared forty-two couriers through my sector this quarter. "
            "Forty. Two. Zero complaints.",
        ])

    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [
            ("CARGO DEAL",   int(self._deal_offered), 1),
            ("CREDIT DEAL",  int(self._paid),          1),
            ("SYMPATHY",     min(self._sympathy_t, 1), 1),
            ("DISTRACT",     min(self._distract_t, 3), 3),
        ]

    def exploits(self) -> dict[str, str]:
        return {
            "cargo_manifest": "Offer cargo manifest / contents as trade",
            "credit_deal":    "Offer 800+ credits directly",
            "shared_outsider":"Bond over debt/clone status — 50% free pass",
            "distraction":    "Ask about his 'plan' 3 times — he forgets to flag you",
        }
