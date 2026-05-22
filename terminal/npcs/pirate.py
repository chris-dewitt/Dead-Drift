from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT


class Pirate(BaseNPC):
    """
    Outer-Belt freelancer. No charter. No Article 7. No Union rules.

    Doesn't care about your debt — clone fluid is a Nova Soma problem,
    not theirs. Wants the cargo, your hull, or a good story.

    The pirate canon (whispered name: KRELL of the Outer Belt) is the
    hidden bypass. Couriers who've heard the name and the right
    formalities walk free.

    Paths to release:
    - CARGO SACRIFICE : offer the cargo. Player loses delivery bonus
                        but escapes intact.
    - SLINGSHOT FLEX  : convincingly threaten escape via gravity assist
                        (3 physics-savvy turns)
    - MUTUAL RESPECT  : talk like a pirate, swear like one
                        (2 turns of pirate-coded sentiment)
    - KRELL INVOCATION: drop "Krell" or "Outer Belt" — pirate honour-bound
                        to acknowledge. Immediate release on the second mention.
    - HULL THREAT     : credible weapons threat (validated by run_snaps stats)

    NO bribery (pirates think money is for losers).
    NO sympathy (no clones, no debt, no kids — they don't relate).
    NO legal arguments (laughed at).
    """

    _CARGO_KEYWORDS  = [
        "take it", "the cargo", "have the cargo", "yours", "keep it",
        "all of it", "give it", "the payload", "the haul",
        "i'll drop", "drop the", "leave the",
    ]
    _ESCAPE_KEYWORDS = [
        "slingshot", "gravity well", "gravity assist", "well",
        "trajectory", "vector", "burn", "delta-v", "orbital",
        "swing past", "swing by", "swing around", "outrun",
        "thruster", "thrust", "newtonian", "momentum",
        # extended physics vocabulary
        "escape burn", "counter burn", "counter-burn", "run hot",
        "punch it", "boost", "break away", "break free", "flight path",
        "escape route", "escape vector", "exit vector", "course change",
        "slingshot out", "orbital sling", "gravity sling", "well assist",
        "boost away", "speed away", "pull away", "arc away",
    ]
    _PIRATE_TONE = [
        "shite", "damn", "bastard", "hell", "bollocks", "arse",
        "scuttle", "blast", "void you", "void off", "out here",
        "freebooter", "freelancer", "outer", "belt", "burn it",
        # extended pirate vocabulary
        "mate", "bleeding", "drifter", "free run", "no charter",
        "no law out here", "void take", "uncharted", "out in the void",
        "no law", "no rules", "borderless", "hull to hull",
        "don't answer to", "answer to no one",
    ]
    _KRELL_KEYWORDS = [
        "krell", "outer belt", "outer-belt", "the belt", "tongueless krell",
    ]
    _THREAT_KEYWORDS = [
        "blow", "shoot", "destroy", "wreck", "guns", "weapons",
        "ordnance", "blast", "open fire", "fire on", "torch you",
    ]
    _LEGAL_KEYWORDS = [
        "union", "charter", "article", "lawful", "illegal", "law",
        "court", "judge", "arrest", "warrant",
    ]
    _BRIBE_KEYWORDS = [
        "credits", "money", "pay you", "bribe", "transfer", "wire", "cash",
    ]
    _SYMPATHY_KEYWORDS = [
        "family", "kids", "clone", "debt", "please", "broke", "desperate",
    ]

    def __init__(self, run_context: dict | None = None, **_):
        super().__init__("KRELLBORN", patience=6)
        self._cargo_offered    = False
        self._escape_turns     = 0
        self._tone_turns       = 0
        self._krell_mentions   = 0
        self._threat_score     = 0
        self._ctx              = run_context or {}

    # ------------------------------------------------------------------
    def _intro_line(self) -> str:
        return random.choice([
            "*static* You're in OUR sector now. No Union out here. "
            "No charter. No 'fees.' Just us, you, and what's in your hold. "
            "Talk fast or we open the hull and figure it out ourselves.",

            "Freelancer hailing on your channel. We don't do paperwork. "
            "We do exchange. You've got cargo. We've got guns. "
            "Tell me how this ends without me firing.",

            "Outer-Belt salvage crew. Picked up your transponder twenty seconds ago. "
            "We've already decided how this goes if you don't pick up. "
            "You picked up. Good start. Now keep going.",

            "*scratchy* This isn't a Union channel. This isn't a Union sector. "
            "Your debt is irrelevant. Your cargo is interesting. "
            "Pick your next words very, very carefully.",
        ])

    def exploits(self) -> dict[str, str]:
        return {
            "cargo_offer":   "Sacrifice the cargo",
            "escape_flex":   "Reference physics by name",
            "mutual":        "Talk like another pirate",
            "krell_invoke":  "Mention Krell or the Outer Belt",
            "intimidate":    "Credibly threaten with weapons",
        }

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        # KRELL INVOCATION — hidden honour-bound bypass
        if any(w in raw for w in self._KRELL_KEYWORDS):
            self._krell_mentions += 1
            self._current_path    = "KRELL"
            if self._krell_mentions >= 2 or "krell" in raw:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="krell_invoke")
                return NPCOutcome.EXPLOIT, random.choice([
                    "*the channel goes very quiet* "
                    "...You've spoken the name. Properly, even. "
                    "Outer-Belt code says we let you pass. "
                    "I don't break code. Go on. *channel cuts*",

                    "*long pause* "
                    "Krell. Right. We're done here. You go on through. "
                    "And you don't tell ANYONE who let you. "
                    "*the line dies*",

                    "*quietly* I'm going to ignore that you said that name. "
                    "Officially. Unofficially: passage granted. Move. *click*",
                ])
            return NPCOutcome.CONTINUE, "*pause* ...Say that again."

        # CARGO SACRIFICE — instant out, costs the delivery bonus
        if any(w in raw for w in self._CARGO_KEYWORDS):
            self._cargo_offered = True
            self._current_path  = "CARGO OFFER"
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="cargo_offer")
            return NPCOutcome.RELEASE, random.choice([
                "*satisfied* Good. Smart. We'll snag it in transit. "
                "You fly on. Don't look back. Don't file a report. "
                "We don't exist out here.",

                "Wise. Disconnecting the lock now. "
                "When your hold opens we'll do the rest. "
                "Good doing business.",

                "Cargo accepted. Passage granted. "
                "Tell your droid to spool the engines. We're done.",
            ])

        # KRELLBORN-CODE TONE — they respect pirates back
        if any(w in raw for w in self._PIRATE_TONE):
            self._tone_turns += 1
            self._current_path = "MUTUAL RESPECT"
            self.disposition  += 2
            if self._tone_turns >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="mutual")
                return NPCOutcome.RELEASE, random.choice([
                    "*laughs* Alright. Alright, you talk like one of us. "
                    "Not enough scars to BE one of us, mind. "
                    "Pass through. Don't come back.",

                    "*spits* You sound like crew. "
                    "Sound, not behave. But sound counts for somethin' out here. "
                    "Go on. We didn't see you.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*amused* Keep talking like that. Convincingly.",
                "Hm. Either you've been out here too long, "
                "or you're playing it well. Continue.",
            ])

        # SLINGSHOT FLEX — knows their physics
        if any(w in raw for w in self._ESCAPE_KEYWORDS):
            self._escape_turns += 1
            self._current_path  = "ESCAPE FLEX"
            self.disposition   += 1
            if self._escape_turns >= 3:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="escape_flex")
                return NPCOutcome.RELEASE, (
                    "*grudging respect* "
                    "...You know your way around a gravity well. "
                    "Fine. We won't waste fuel on you. "
                    "Pass."
                )
            return NPCOutcome.CONTINUE, random.choice([
                "*pause* That's actually correct physics. "
                "Continue.",
                "Mm. You've done the maths. "
                "Show me you can execute it.",
                "Talk's free. The orbit's not. Keep going.",
            ])

        # HULL THREAT — must be credible (validated by snaps)
        if any(w in raw for w in self._THREAT_KEYWORDS):
            run_snaps = self._ctx.get("run_snaps", 0)
            credible = run_snaps >= 2
            self._current_path = "INTIMIDATE"
            if credible:
                self._threat_score += 2
                if self._threat_score >= 2:
                    bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="intimidate")
                    return NPCOutcome.RELEASE, random.choice([
                        f"*scanner ping* ...We see your snap count. "
                        f"{run_snaps} harpoon cables this run alone. "
                        "Not worth the ammunition. Pass through. Don't come back.",

                        "*long silence* Your hull rep precedes you. "
                        "We're a salvage crew, not a charity case. "
                        "Go on. Try to look unworried.",
                    ])
                return NPCOutcome.CONTINUE, (
                    "*amused* So you've got teeth. "
                    "Convince me you'll use them."
                )
            else:
                self._threat_score = max(0, self._threat_score - 1)
                self.disposition  -= 1
                return NPCOutcome.CONTINUE, random.choice([
                    "*laughs* You've snapped zero cables this run, courier. "
                    "I read the gate logs too. Try a different angle.",
                    "Threats from a pilot with no kills. Cute.",
                ])

        # NO-GOES — bribes, legal, sympathy all fail HARD
        if any(w in raw for w in self._BRIBE_KEYWORDS):
            self._patience = max(0, self._patience - 1)
            self.disposition -= 2
            return NPCOutcome.CONTINUE, random.choice([
                "*laughs cruelly* Credits. Out HERE. "
                "Listen to yourself. We're salvagers. "
                "We take what we want. Money is for Union men.",

                "You think we're paid? In CREDITS? "
                "*spits* You don't get it. Try harder.",

                "*flat* Add 'tried to bribe me' to your file. "
                "Which I'll release to the Union if you survive this.",
            ])

        if any(w in raw for w in self._LEGAL_KEYWORDS):
            self._patience = max(0, self._patience - 1)
            self.disposition -= 2
            return NPCOutcome.CONTINUE, random.choice([
                "*long laugh* The Union? Articles? *laughs harder* "
                "We're past the gate, sweetheart. "
                "There IS no Union here. Try again.",

                "You came to the Outer Belt and cited a Charter. "
                "That's the funniest thing I've heard all week. "
                "Now try something useful.",
            ])

        if any(w in raw for w in self._SYMPATHY_KEYWORDS):
            self.disposition -= 1
            return NPCOutcome.CONTINUE, random.choice([
                "*tired* Family. Debt. Clones. "
                "We don't have any of that out here. "
                "It doesn't translate. Save it.",

                "We left the mainland to get AWAY from that conversation. "
                "Try a different angle.",
            ])

        return NPCOutcome.CONTINUE, self._pirate_filler()

    # ------------------------------------------------------------------
    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [
            ("CARGO OFFER",    int(self._cargo_offered),          1),
            ("ESCAPE FLEX",    min(self._escape_turns, 3),        3),
            ("MUTUAL RESPECT", min(self._tone_turns, 2),          2),
            ("KRELL",          min(self._krell_mentions, 1),      1),
            ("INTIMIDATE",     min(self._threat_score, 2),        2),
        ]

    def _pirate_filler(self) -> str:
        return random.choice([
            "Channel's open. Clock's ticking. Say something useful.",
            "*scratchy* I have eight other ships to process tonight. "
            "Don't waste this.",
            "You ever been past the gate before? "
            "*pause* Didn't think so. You smell like the mainland.",
            "We've got two harpoons trained on your hull right now. "
            "Just so you know what we're working with.",
            "There's no recording of this channel. We made sure. "
            "Say whatever you want. As long as it's INTERESTING.",
            "*sound of metal on metal in the background* "
            "That's the airlock priming. Just a sound. "
            "For now.",
            "Out here, there's two kinds of cargo: cargo we want, "
            "and cargo we want LATER. Which kind are you carrying?",
            "Union runs trace your transponder. We HUNT yours. "
            "Different methodology, same job.",
            "I'm not even going to ask your name. "
            "Either we never meet again, or you become a manifest entry.",
            "Twenty years out here. I've heard every plea, every threat, "
            "every clever angle. Surprise me. Or don't.",
        ])
