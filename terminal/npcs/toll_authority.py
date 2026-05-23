"""
Toll Authority — mid-sector checkpoint gate NPC.
Bored jobs-worth. Hates Local 404 more than he hates couriers.
Short patience — 20-second negotiation max.

Outcomes:
  PAY:       mention a credit amount >= 1500 → waved through, lose the credits
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
    Sector gate official. Short fuse. Hates Local 404.
    """

    def __init__(self, vocabulary_vault=None, run_context: dict | None = None):
        super().__init__("TOLL AUTHORITY", patience=5)   # short patience
        self._vault       = vocabulary_vault
        self._ctx         = run_context or {}
        self._paid        = False
        self._barge_called = False

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
        ])

    def _evaluate(self, parsed: ParsedInput) -> NPCOutcome | None:
        text_l = parsed.raw.lower()

        # Hostile → barge call
        if any(w in text_l for w in _HOSTILE_WORDS):
            self._barge_called = True
            self.disposition = -10
            return None   # outcome handled via flag in _response_for_outcome

        # Pay with sufficient credits
        for kw in _PAY_KEYWORDS:
            if kw in text_l:
                # Check if they mentioned a plausible amount
                self.disposition += 4
                self._paid = True
                if self._vault:
                    self._vault.record("toll_authority", "PAID_TOLL")
                bus.emit(EVT_NLP_EXPLOIT, npc="toll_authority", exploit_key="PAID_TOLL")
                return NPCOutcome.RELEASE

        # Union sympathy — he might wave you through
        if any(w in text_l for w in _UNION_GRIPE_WORDS):
            self.disposition += 2
            if random.random() < 0.6:
                # 60% chance — Union-griping solidarity works
                if self._vault:
                    self._vault.record("toll_authority", "UNION_SYMPATHY")
                bus.emit(EVT_NLP_EXPLOIT, npc="toll_authority", exploit_key="UNION_SYMPATHY")
                return NPCOutcome.RELEASE

        # Patience decay
        self.patience -= 1
        if self.patience <= 0:
            self._barge_called = True
            return None

        self.disposition -= 1
        return None

    def get_response(self, parsed: ParsedInput) -> tuple[str, NPCOutcome | None]:
        outcome = self._evaluate(parsed)

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
            if self._paid:
                return (random.choice([
                    "Payment confirmed. Gate Seven: cleared. "
                    "Move it — you're backing up the queue.",
                    "Transaction logged. You're through. "
                    "And for what it's worth, this is not the worst interaction I've had today.",
                    "Paid up. Gate's open. Don't be slow about it.",
                ]), NPCOutcome.RELEASE)
            else:
                return (random.choice([
                    "...alright. Look, between you and me, Local 404 took my overtime last month. "
                    "You didn't hear that. Gate Seven: open. Move along before I change my mind.",
                    "You know what? Same. I hate those guys too. "
                    "Gate's open. Don't make me regret this.",
                    "You've got a point. A valid, infuriating point. "
                    "Go. Before the supervisor sees the logs.",
                ]), NPCOutcome.RELEASE)

        # Impatient non-outcome responses
        return (random.choice([
            "Still here. Still waiting. Clock's ticking.",
            "That's not fifteen hundred credits. That's words.",
            "I'm logging this delay. It'll show up on your transit record. Pay.",
            "You want to talk? Fine. The toll is still fifteen hundred. "
            "Want to keep talking? The toll is still fifteen hundred.",
            "I don't care. Pay or go back. Those are your options.",
        ]), None)

    @property
    def barge_called(self) -> bool:
        return self._barge_called
