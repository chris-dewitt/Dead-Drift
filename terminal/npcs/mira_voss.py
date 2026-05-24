"""
MIRA VOSS — back-alley hull medic.  Used to work auth maintenance for Local 404
before she got "professionally invited to leave."  Now she runs a docking-bay
repair stand out of a converted refueling pod.

She doesn't care who you are or what you're carrying.  She trades hull patches
for credits, intel, or cargo — whichever you've got.  Respects competence.
Hates time-wasters.

Outcomes:
  PAY        : ≥ 700 cr offered → patch job, hull repaired (RELEASE)
  INTEL      : offer patrol / barge / gate intel → patch (RELEASE)
  CARGO      : offer a slice of cargo (manifest/contents) → patch (RELEASE)
  TECHNICAL  : demonstrate hull/repair knowledge (any of 3 terms) → free patch
  HOSTILE    : threats or insults → snaps the comm, IMPOUND (she doesn't help)
  STALL      : vague replies for 4 turns → patience runs out, no patch
"""
from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT, EVT_HULL_DAMAGE


_PAY_AMOUNT = 700
_INTEL_KEYWORDS = [
    "patrol", "barge", "gate", "schedule", "frequency", "channel",
    "checkpoint", "patrol pattern", "barge route", "scanner",
    "patrol window", "blind spot", "gate timing", "intel",
    "tip", "heard something", "the route is", "i know where",
    "saw a", "spotted",
]
_CARGO_KEYWORDS = [
    "manifest", "contents", "cargo list", "what i'm hauling",
    "share the haul", "split the cargo", "take a cut", "piece of the cargo",
    "trade some cargo", "slice of cargo", "give you some",
]
_TECHNICAL_KEYWORDS = [
    # Things a real hull tech would say
    "compound", "patch compound", "polyseal", "ceramic plate",
    "hull integrity", "stress fracture", "micro-fracture", "weld line",
    "torch grade", "argon", "shield gradient", "vac-seal",
    "atmospheric pressure", "hairline crack", "hull plate",
    "graphene mesh", "reinforcement strip", "bonded layer",
    "decompression", "vacuum seal", "weld bead", "carbon braid",
]
_HOSTILE_KEYWORDS = [
    "shut up", "fuck", "i'll kill", "bitch", "hag", "old woman",
    "useless", "you're nothing", "rip you off", "scam",
    "threat", "make you", "you better", "or else",
]


class MiraVoss(BaseNPC):
    """Hull medic on a converted refueling pod.  Patches for cash, intel, or cargo."""

    def __init__(self, vocabulary_vault=None, run_context: dict | None = None,
                 ship=None, **_):
        super().__init__("MIRA VOSS", patience=7)
        self._vault     = vocabulary_vault
        self._ctx       = run_context or {}
        self._ship      = ship
        self._tech_hits = 0
        self._paid      = False
        self._intel_gave = False
        self._cargo_gave = False
        self._stall_turns = 0

    def _intro_line(self) -> str:
        return random.choice([
            "*coughs*  Yeah, comm's open.  Mira Voss, hull work, "
            "bay nine.  *sound of a torch igniting*  "
            "You're streaming atmosphere — I can see it from here.  "
            "I patch, you pay.  I take credits, intel, or a slice of "
            "whatever you're hauling.  What've you got.",

            "*static crackle*  Voss.  You're broadcasting hull damage "
            "louder than your transponder.  Bay nine.  "
            "I do clean welds, no questions, no manifest checks.  "
            "Price depends on what you can spare.  Talk.",

            "Mira here.  *muffled clang*  Saw your hull plates on the scope.  "
            "You're losing pressure.  I can fix that.  "
            "Not for free, mind — credits, intel, cargo, anything useful.  "
            "Insults are NOT on the list.",

            "*welding flash in background*  Look — I'm Voss, I run repairs, "
            "I don't care WHO you are.  But I'm busy and you're leaking.  "
            "Pay me, tip me off about a barge, or hand over something off the "
            "manifest.  Quick choice.",
        ])

    # ------------------------------------------------------------------
    def _do_repair(self):
        """Apply the hull patch to the ship if we have a reference."""
        if self._ship is None:
            return
        try:
            self._ship.repair(45.0)
        except Exception:
            pass

    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        if any(w in raw for w in _HOSTILE_KEYWORDS):
            self._patience = 0
            return NPCOutcome.IMPOUND, random.choice([
                "*comm slams off*  Right.  Fix yourself, then.  "
                "*static, then silence*",

                "Nope.  I don't fix mouth like yours.  "
                "*signal cuts*  Lose my channel.",

                "*flat*  We're done here.  "
                "Hope the next leak is fatal.  *click*",
            ])

        # Technical competence — counts hits, 3 → free repair
        tech_hits_this_turn = sum(1 for w in _TECHNICAL_KEYWORDS if w in raw)
        if tech_hits_this_turn > 0:
            self._tech_hits += tech_hits_this_turn
            if self._tech_hits >= 3:
                self._current_path = "TECHNICAL"
                bus.emit(EVT_NLP_EXPLOIT, npc="mira_voss",
                         exploit_key="technical_competence")
                if self._vault:
                    self._vault.record("mira_voss", "TECHNICAL_COMPETENCE")
                self._do_repair()
                return NPCOutcome.RELEASE, random.choice([
                    "*surprised laugh*  Huh.  You actually know hull work.  "
                    "Fine.  Patch is on the house.  "
                    "I respect a courier who can spell 'graphene.'  "
                    "Now go before I change my mind.",

                    "*satisfied grunt*  Okay.  You're not just guessing.  "
                    "That's worth a freebie.  Patch sealed, "
                    "pressure stable.  Stay alive, kid.  *signal off*",

                    "Alright, you're not playing.  "
                    "Free patch.  Don't make me regret it — "
                    "and don't come back unless you're paying or competent.  "
                    "*click*",
                ])
            # Partial — encourage more technical talk
            return NPCOutcome.CONTINUE, random.choice([
                "*intrigued*  Go on.  What grade?",
                "*half-listening*  Mm.  And the failure mode is?",
                "*evaluating*  Keep talking.  Convince me you've held a torch.",
            ])

        # Credits — ≥700 → solid patch
        if parsed.amount is not None and parsed.amount >= _PAY_AMOUNT:
            self._paid = True
            self._current_path = "PAID"
            bus.emit(EVT_NLP_EXPLOIT, npc="mira_voss", exploit_key="paid_repair")
            if self._vault:
                self._vault.record("mira_voss", "PAID_REPAIR")
            self._do_repair()
            return NPCOutcome.RELEASE, random.choice([
                f"{parsed.amount} credits.  Done.  Patch sealed, "
                "pressure back to nominal.  Pleasure doing business.  "
                "Don't fly into anything for the next ten minutes — "
                "the bond's still curing.",

                f"Cash.  My favourite language.  "
                f"Hull's patched, weld's good.  "
                f"{parsed.amount} cr in the box.  Off you go.",

                f"Right then.  {parsed.amount} cr accepted.  "
                "Drone's already on the hull.  Done in twenty seconds.  "
                "*welding sound*  ...Done.  Stay sharp out there.",
            ])

        # Intel offer — patrol/barge/gate info
        if any(w in raw for w in _INTEL_KEYWORDS):
            self._intel_gave = True
            self._current_path = "INTEL TRADE"
            bus.emit(EVT_NLP_EXPLOIT, npc="mira_voss", exploit_key="intel_trade")
            if self._vault:
                self._vault.record("mira_voss", "INTEL_TRADE")
            self._do_repair()
            return NPCOutcome.RELEASE, random.choice([
                "*considers*  Yeah, alright.  That's the kind of tip "
                "I can sell to the next courier through.  "
                "Patch is on.  We're square.",

                "Mm.  Useful.  I'll put that on the board.  "
                "Patch done, you're sealed.  Get gone before "
                "the comm log catches us trading.",

                "*chuckles*  Information.  Underrated.  "
                "Hull's fixed.  Don't tell anyone you got it from me — "
                "and I won't tell anyone you told me.",
            ])

        # Cargo offer
        if any(w in raw for w in _CARGO_KEYWORDS):
            self._cargo_gave = True
            self._current_path = "CARGO TRADE"
            bus.emit(EVT_NLP_EXPLOIT, npc="mira_voss", exploit_key="cargo_share")
            if self._vault:
                self._vault.record("mira_voss", "CARGO_SHARE")
            self._do_repair()
            return NPCOutcome.RELEASE, random.choice([
                "*pause*  You're offering me a piece of the haul?  "
                "Bold.  Risky for both of us.  ...Yeah, alright.  "
                "Patch's on.  Drop the package in tube three "
                "on your way past.",

                "Cargo it is.  I'll take whatever's small and untraceable.  "
                "Patch is sealed.  Tube three.  Don't be late.  "
                "And don't tell the inspector — he asks me weekly.",

                "*considers*  You're either desperate or generous.  "
                "Either way works for me.  Patch's done.  "
                "I'll take my cut from the dropoff.  Move.",
            ])

        # Stall — vague filler counts against patience
        self._stall_turns += 1
        if self._stall_turns >= 4:
            self._patience = 0
            return NPCOutcome.IMPOUND, random.choice([
                "*sighs*  Okay, I'm out.  Got actual customers.  "
                "Hope you find someone with more patience.  *click*",

                "Right, you're wasting both our shifts.  "
                "I'm closing the comm.  Bleed quietly.",

                "*dryly*  This isn't a chat line.  "
                "Get me an offer or get off my band.  "
                "*signal cuts*",
            ])

        return NPCOutcome.CONTINUE, self._impatient_filler()

    def _impatient_filler(self) -> str:
        return random.choice([
            "*tapping a wrench*  Offer.  Now.",
            "I do hull work, not therapy.  What's the trade?",
            "*welding sound*  You're paying for my attention with leaking atmosphere.  Talk.",
            "I'm not going to ask three times.  Credits, intel, or cargo?",
            "*flat*  Mm-hm.  Are we doing this or not?",
            "Other ships are queueing.  Decide.",
        ])

    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [
            ("TECHNICAL", min(self._tech_hits, 3), 3),
            ("PAID",      int(self._paid),         1),
            ("INTEL",     int(self._intel_gave),   1),
            ("CARGO",     int(self._cargo_gave),   1),
        ]

    def exploits(self) -> dict[str, str]:
        return {
            "technical_competence": "Use 3 real hull-repair terms (graphene, weld bead, vac-seal, ...)",
            "paid_repair":          "Offer ≥ 700 cr — straight cash patch",
            "intel_trade":          "Offer patrol / barge / gate intel — she resells it",
            "cargo_share":          "Offer a slice of cargo manifest — risky but accepted",
        }
