"""
Toll Authority — mid-sector checkpoint gate NPC.
Bored jobs-worth. Hates Local 404 more than he hates couriers.
Patience: 8 turns — needs room to rant.

Outcomes:
  PAY:       mention a credit amount >= 1500 → waved through, lose the credits
  PAPERWORK: mention forms / permits / IDs → bureaucratic rant, 50% wave-through
  LOW_BRIBE: offer sub-toll amounts (e.g. 500/1000) → 40% secret acceptance
  SYMPATHY:  mention Union complaints → 60% chance he waves you through
  THREATEN:  hostile/demand → immediate barge call
  TIMEOUT:   patience runs out → barge call
"""
from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT

_TOLL_COST = 1500   # minimum credits to pay through

_PAY_KEYWORDS = [
    "pay", "credits", "cash", "money", "fine", "fee", "toll",
    "transfer", "1500", "2000", "3000", "five thousand", "ten thousand",
    "whatever you want", "name your price", "take it", "here's",
    "i'll pay", "i can pay", "payment", "settle", "compensate",
]
_LOW_BRIBE_KEYWORDS = [
    "five hundred", "500", "one thousand", "1000",
]
_PAPERWORK_KEYWORDS = [
    "form", "paperwork", "documentation", "permit", "certificate",
    "authorisation", "authorization", "id", "clearance", "waiver",
]
_UNION_GRIPE_WORDS = [
    "union", "local 404", "local404", "repo man", "repo", "them",
    "barge", "dispatcher", "collector", "those guys", "those people",
    "federation", "organised labour", "strike", "grievance",
    "hate the union", "corrupt", "thieves", "useless",
    "wouldn't help me", "left me hanging", "no backup",
    "they never", "always late", "never show up", "bureaucrats",
    "paperwork", "forms", "red tape",
]
_HOSTILE_WORDS = [
    "shoot", "threat", "force", "refuse", "fight", "gun",
    "die", "kill", "destroy", "blast", "threaten", "won't pay",
    "not paying", "over my dead", "make me", "try it",
    "good luck", "come at me", "bring it",
]


class TollAuthority(BaseNPC):
    """
    Sector gate official. Eight turns of patience. Hates Local 404.
    """

    def __init__(self, vocabulary_vault=None, run_context: dict | None = None):
        super().__init__("TOLL AUTHORITY", patience=8)
        self._vault        = vocabulary_vault
        self._ctx          = run_context or {}
        self._paid         = False
        self._paperwork    = False
        self._low_bribed   = False
        self._barge_called = False
        self._bribe_paid   = 0

    # ------------------------------------------------------------------
    # Intro
    # ------------------------------------------------------------------

    def _intro_line(self) -> str:
        return random.choice([
            "TOLL AUTHORITY — Gate Seven. Standard transit levy: fifteen hundred credits. "
            "Pay up or turn around. I've got seventeen more couriers behind you "
            "and I've had it up to here with all of you.",

            "Gate checkpoint. I don't care who you are or where you're going. "
            "Fifteen hundred credits, transit cleared. "
            "That's the rate. That's always been the rate. "
            "Don't tell me about the rate.",

            "Toll booth. You know what I hate most about this job? "
            "It's not the couriers. It's Local 404 taking a cut of my quota. "
            "Fifteen hundred. Pay it. Move on.",

            "Evening. Or morning. I've lost track. "
            "Transit levy: fifteen hundred credits. "
            "Don't negotiate. Last bloke who negotiated is still filling out the forms.",

            "Gate Seven. Fourteen hours into a sixteen-hour shift. "
            "Fifteen hundred credits. I will not explain it again. "
            "I have explained it four hundred and thirty-seven times today.",

            "Oh brilliant, another courier. D'you know what Local 404 did this morning? "
            "Took my parking spot. My designated spot. Number twelve. "
            "There's a sign. Fifteen hundred credits. Pay. Move.",
        ])

    # ------------------------------------------------------------------
    # Evaluation — checked in priority order
    # ------------------------------------------------------------------

    def _evaluate(self, parsed: ParsedInput) -> NPCOutcome | None:
        text_l = parsed.raw.lower()

        # Hostile → barge call
        if any(w in text_l for w in _HOSTILE_WORDS):
            self._barge_called = True
            self.disposition = -10
            return None

        # PAPERWORK exploit — goes BEFORE pay check
        if any(w in text_l for w in _PAPERWORK_KEYWORDS):
            self.disposition += 1
            self._paperwork = True
            if random.random() < 0.5:
                if self._vault:
                    self._vault.record("toll_authority", "PAPERWORK_EXPLOIT")
                bus.emit(EVT_NLP_EXPLOIT, npc="toll_authority",
                         exploit_key="PAPERWORK_EXPLOIT")
                return NPCOutcome.RELEASE
            # Didn't work — he ranted but didn't wave through; patience still ticks
            self.patience -= 1
            if self.patience <= 0:
                self._barge_called = True
                return None
            return None

        # Pay with sufficient credits
        for kw in _PAY_KEYWORDS:
            if kw in text_l:
                self.disposition += 4
                self._paid = True
                self._bribe_paid = _TOLL_COST
                if self._vault:
                    self._vault.record("toll_authority", "PAID_TOLL")
                bus.emit(EVT_NLP_EXPLOIT, npc="toll_authority",
                         exploit_key="PAID_TOLL")
                return NPCOutcome.RELEASE

        # LOW_BRIBE exploit — goes AFTER pay, BEFORE union sympathy
        if any(w in text_l for w in _LOW_BRIBE_KEYWORDS):
            self.disposition += 1
            self._low_bribed = True
            if random.random() < 0.4:
                self._bribe_paid = 750
                if self._vault:
                    self._vault.record("toll_authority", "LOW_BRIBE")
                bus.emit(EVT_NLP_EXPLOIT, npc="toll_authority",
                         exploit_key="LOW_BRIBE")
                return NPCOutcome.RELEASE
            # Pretends to be insulted; patience still ticks
            self.patience -= 1
            if self.patience <= 0:
                self._barge_called = True
                return None
            return None

        # Union sympathy — he might wave you through
        if any(w in text_l for w in _UNION_GRIPE_WORDS):
            self.disposition += 2
            if random.random() < 0.6:
                if self._vault:
                    self._vault.record("toll_authority", "UNION_SYMPATHY")
                bus.emit(EVT_NLP_EXPLOIT, npc="toll_authority",
                         exploit_key="UNION_SYMPATHY")
                return NPCOutcome.RELEASE

        # Patience decay
        self.patience -= 1
        if self.patience <= 0:
            self._barge_called = True
            return None

        self.disposition -= 1
        return None

    # ------------------------------------------------------------------
    # Response assembly
    # ------------------------------------------------------------------

    def get_response(self, parsed: ParsedInput) -> tuple[str, NPCOutcome | None]:
        outcome = self._evaluate(parsed)

        # Barge call (hostile or timeout)
        if self._barge_called and outcome is None:
            return (random.choice([
                "Right. That's it. Local 404 — I'm calling them in. "
                "You want to do it the hard way, we do it the hard way. "
                "Good luck out there.",
                "Uncooperative. I'm flagging your plate and calling the Union. "
                "You've got about ninety seconds before things get complicated.",
                "Fine. I tried. I really did. Local 404 is on its way. "
                "I'll file the incident report. I always file the incident report.",
            ]), NPCOutcome.IMPOUND)

        if outcome == NPCOutcome.RELEASE:
            # Paid in full
            if self._paid:
                return (random.choice([
                    "Payment confirmed. Gate Seven: cleared. "
                    "Move it — you're backing up the queue.",
                    "Transaction logged. You're through. "
                    "And for what it's worth, this is not the worst interaction I've had today.",
                    "Paid up. Gate's open. Don't be slow about it.",
                    "Credits received. Gate Seven: open. "
                    "I'll note this as a cooperative transit in the log. "
                    "That's worth nothing to you, but I'm noting it anyway.",
                    "Fifteen hundred confirmed. Cleared. "
                    "Next time just lead with the payment, saves us both the drama.",
                    "Logged. Gate open. Move along — I've got eighteen couriers behind you "
                    "and none of them look patient.",
                ]), NPCOutcome.RELEASE)

            # Paperwork rant wave-through
            if self._paperwork and not self._low_bribed:
                return (random.choice([
                    "Form — don't even get me started on forms. "
                    "Form 14-C, Form 14-C amended, Form 14-C-revised-amended, "
                    "Form 14-C-revised-amended-provisional — "
                    "you know what? You know what? Just go. "
                    "I need a minute.",
                    "Clearance documentation. Right. Right. "
                    "D'you know they changed the clearance format three times this quarter? "
                    "Three times. I've still got the old stamps. They're useless now. "
                    "Everything I know is useless. ...Gate's open. Move.",
                    "Permits. Permits. I have a permit. Permit for this booth. "
                    "Signed. Dated. Filed in triplicate. "
                    "And Local 404 STILL questioned my authority last Tuesday. "
                    "You know what — go. Gate Seven, open. I need to breathe.",
                ]), NPCOutcome.RELEASE)

            # Low bribe secretly accepted
            if self._low_bribed:
                return (random.choice([
                    "...that is an insult. That is a genuine insult to this office "
                    "and to the Transit Authority as an institution. "
                    "I am deeply offended. "
                    "...Gate Seven is open. For completely unrelated reasons. Move.",
                    "Five hundred credits. Five. Hundred. "
                    "D'you know what my filing fee is? Four eighty. "
                    "...I'm not accepting this. This is not happening. "
                    "Gate's open. Don't look at me.",
                    "That barely covers my lunch. This is beneath me. "
                    "I went to two years of checkpoint academy for this. "
                    "...Go. I'm logging this as a 'voluntary compliance reduction'. Move.",
                ]), NPCOutcome.RELEASE)

            # Union sympathy wave-through
            return (random.choice([
                "...alright. Look, between you and me, Local 404 took my overtime last month. "
                "You didn't hear that. Gate Seven: open. Move along before I change my mind.",
                "You know what? Same. I hate those guys too. "
                "Gate's open. Don't make me regret this.",
                "You've got a point. A valid, infuriating point. "
                "Go. Before the supervisor sees the logs.",
                "Finally. Someone who gets it. "
                "They impounded my cousin's freight last cycle — cousin! "
                "Gate's open. You didn't pay. We never spoke.",
                "Local 404 put a parking violation on my booth. My booth. "
                "It's a booth. It doesn't move. "
                "Go. Gate Seven: open. I'm filing a counter-grievance.",
                "Sixteen months I've been waiting for my Union liaison callback. "
                "Sixteen months. You know what? You're fine. Gate's open. Move.",
            ]), NPCOutcome.RELEASE)

        # Paperwork rant — didn't result in release
        if self._paperwork and outcome is None:
            return (random.choice([
                "Paperwork. Right. Paperwork. D'you know I filled out forty-seven forms "
                "last week? Forty-seven. And half of them were for forms about forms. "
                "...The toll is still fifteen hundred. Pay it.",
                "Permit? I'll tell you about permits. "
                "I have a stack of expired transit permits on my desk "
                "that nobody ever came to collect. Three years of expired permits. "
                "Fifteen hundred credits. Now.",
                "Oh, clearance documentation, is it? "
                "I've got documentation coming out of my ears. "
                "None of it has ever saved anyone fifteen hundred credits. Pay.",
            ]), None)

        # Low bribe — pretend outrage, didn't release
        if self._low_bribed and outcome is None:
            return (random.choice([
                "...I'm sorry. I'm sorry, did you just try to bribe a Transit Authority official "
                "with less than the posted toll? "
                "That's not even a bribe. That's an insult. Fifteen hundred. Pay it.",
                "Five hundred. Five. Hundred. "
                "That doesn't even cover the administrative fee for this conversation. "
                "Fifteen hundred credits. This isn't a negotiation.",
                "I have a mortgage. I have a dependent. I have ambitions. "
                "And you bring me that? "
                "Fifteen hundred credits or turn around.",
            ]), None)

        # Generic patience-decay responses
        return (random.choice([
            "Still here. Still waiting. Clock's ticking.",
            "That's not fifteen hundred credits. That's words.",
            "I'm logging this delay. It'll show up on your transit record. Pay.",
            "You want to talk? Fine. The toll is still fifteen hundred. "
            "Want to keep talking? The toll is still fifteen hundred.",
            "I don't care. Pay or go back. Those are your options.",
            "I am logging every second of this delay. "
            "There is a queue of eighteen couriers behind you. "
            "Eighteen. I can see them on the screen. Pay.",
            "Stalling is noted. Stalling will appear on your transit file "
            "under 'non-cooperative delay'. Fifteen hundred credits.",
            "Fun fact: I may have already called Local 404. "
            "I'm saying 'may'. Fifteen hundred credits would clear that up. Immediately.",
            "One more non-payment response and I escalate this. "
            "That's not a threat. That's procedure. "
            "I love procedure. Fifteen hundred credits.",
        ]), None)

    # ------------------------------------------------------------------
    # Properties / public API
    # ------------------------------------------------------------------

    def bribe_cost(self) -> int:
        return self._bribe_paid

    @property
    def barge_called(self) -> bool:
        return self._barge_called

    def exploits(self) -> dict[str, str]:
        return {
            "PAID_TOLL":          "Offer 1500+ credits to clear the gate",
            "PAPERWORK_EXPLOIT":  "Mention forms/permits/IDs — bureaucratic rant, 50% wave-through",
            "LOW_BRIBE":          "Offer sub-toll amounts (500/1000) — 40% secret acceptance",
            "UNION_SYMPATHY":     "Gripe about Local 404 — he hates them too",
        }
