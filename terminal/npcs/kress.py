from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from terminal.economy import EFFECT_REPAIR_25, EFFECT_STIM
from core.event_bus import bus, EVT_NLP_EXPLOIT, EVT_BAX_SPEAK


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

    # Aliveness B.1 / B.3 schema baseline: expanded so Kress now ships
    # 22 distinct accepted pickup words across paths (was 14, under the
    # 15-keyword floor). Same five paths, broader vocabulary so the
    # player can hit them with natural phrasing.
    _INTEL_KEYWORDS    = ["intel", "tip", "tips", "info", "information",
                           "what's ahead", "next sector", "patrol", "scan",
                           # B.3 additions:
                           "chatter", "broadcast", "tell me", "what do you know",
                           "give me something", "rumor", "rumour", "heads up"]
    _CONTRABAND_WORDS  = ["contraband", "stims", "fuel", "jammer", "smoke",
                           "shield", "patch", "hack", "warez", "stuff",
                           # B.3 additions:
                           "wares", "merchandise", "goods", "off-books",
                           "off the books", "supplies"]
    _GREASE_KEYWORDS   = ["volkov", "old debt", "owe", "owed", "vienna",
                           # B.3 additions:
                           "favor", "favour", "favor for a favor",
                           "marker", "ledger", "tab"]
    _MARROW_SELL_WORDS = [
        "marrow", "roost", "pirate radio", "broadcast location",
        "broadcast coordinates", "sell out marrow", "give up marrow",
    ]
    _CONFIRM_WORDS = ["confirm", "confirmed", "do it", "sell", "trade", "give it"]

    def __init__(self, run_context: dict | None = None):
        super().__init__("KRESS", patience=8)
        self._friendly_turns    = 0
        self._mentioned_volkov  = False
        self._mentioned_connie  = False
        self._intel_count       = 0
        self._marrow_warning    = False
        self._ctx               = run_context or {}

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
            "marrow_sellout":  "Sell Marrow's Roost location (irreversible)",
        }

    # ── J.1 priced menus (prose price == charged price; 0 == free tip) ──
    def _intel_menu(self, sector: int) -> list[tuple[str, int]]:
        seize_sector = min(sector + 1, 9) + 1
        return [
            ("Next sector: Local 404 patrol is light. Dispatcher is on lunch. "
             "Two thousand credits, on your tab. Already done. Drive safe.", 2000),
            ("I am hearing chatter. Repo barge in your area has bad torch — "
             "module unbolt cooldown is doubled. Free tip, this one. "
             "Because you asked nicely. Now go.", 0),
            ("Sector ahead has gravity well shifting position every 40 seconds. "
             "Union does not have this on charts yet. Now you do. "
             "Twelve hundred credits. Tab. *click*", 1200),
            ("Gary is two sectors behind you. Big, tired, mentions quotas. "
             "Avoid Sector boundary. One thousand eight hundred credits. Tab.", 1800),
            ("Scanner sweep scheduled in four minutes. Union passive ping — "
             "they look for mass signature, not heat. Kill thrust, drift. "
             "They will pass right over you. Free advice. You are welcome.", 0),
            ("There is debris corridor between here and next jump. Not on any "
             "chart. Do not go through the middle. Go around. "
             "Three thousand credits. This one is worth it.", 3000),
            ("Claims division is filing paperwork to seize any cargo in Sector "
             f"{seize_sector}. Something about form 34-A. Nobody knows what "
             "form 34-A is. They are still filing it. Fifteen hundred. Tab.", 1500),
            ("Barge dispatcher is rotating assignments. The one headed your way "
             "is new — first week. They hesitate before CLAMP state. "
             "Use this. Twenty-five hundred credits. On tab. Go.", 2500),
            ("There is a fuel cache at the boundary. Old miner's stash, off every "
             "map. He owes me favour. It is yours now. Two thousand. Tab. *click*", 2000),
            ("Union comms are quiet today. That is bad sign — they coordinate on "
             "secure channel I cannot hear. Be careful. This one is free. "
             "Because I am worried.", 0),
        ]

    _CONTRABAND_MENU = [
        ("Jammer package, twenty-second barge comm blackout. "
         "Five thousand. On tab. Already in your fuel mix. *click*", 5000, None),
        ("Hull patch, salvaged from Volkov's last job. Eight thousand, but it is "
         "good steel and I weld it in now. Tab is bigger. So is your hull. Goodbye.",
         8000, EFFECT_REPAIR_25),
        ("Stims for your droid. Bax will be... let us say 'enthusiastic'. "
         "Three thousand. He will not thank you, but the next bad chord, he mends "
         "deeper. *click*", 3000, EFFECT_STIM),
    ]

    def _sell(self, line: str, price: int, *, effect, path: str) -> tuple[str, str]:
        """J.1 — a priced Kress line. Free tips just release. Priced lines charge
        both ledgers when affordable; when broke, a counter-offer (the CONTINUE
        already costs the normal −1 patience upstream)."""
        self._current_path = path
        if price <= 0:
            return NPCOutcome.RELEASE, line
        if self._credits() >= price:
            self.stage_transaction(price, dual_ledger=True, effect=effect,
                                   label=f"KRESS {path}")
            return NPCOutcome.RELEASE, line
        return NPCOutcome.CONTINUE, (
            f"*static* You have {self._credits():,} on you. This is {price:,}. "
            "Kress is not charity, my friend. Bring credits, or bring me something "
            "else to sell. Talk again when your account is less embarrassing."
        )

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        if self._marrow_warning or self._is_marrow_sellout_offer(raw):
            self._current_path = "MARROW SELL-OUT"
            if not self._marrow_warning:
                self._marrow_warning = True
                bus.emit(EVT_BAX_SPEAK, line=(
                    "Boss, you hand Kress the Roost and Marrow is gone. "
                    "No undo. Type confirm if you really mean it."
                ))
                return NPCOutcome.CONTINUE, (
                    "*static drops low* You have Roost location? Marrow's nest? "
                    "That is expensive information. Also ugly information. "
                    "Say confirm and Kress sells it. Say anything else and we forget."
                )
            if any(w in raw for w in self._CONFIRM_WORDS):
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="marrow_sellout")
                return NPCOutcome.EXPLOIT, (
                    "*long silence* ...Coordinates received. Local 404 pays well "
                    "for pirates who sing too loudly. I do not feel good. "
                    "This is how I know price was correct. *click*"
                )
            self._marrow_warning = False
            return NPCOutcome.CONTINUE, (
                "Good. Hesitation is healthy. Say confirm if you want blood on invoice."
            )

        # PREVIOUS PILOT — the lore drop, the mystery seed
        if "connie" in raw and not self._mentioned_connie:
            self._mentioned_connie = True
            self._current_path = "CONNIE"
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
            self._current_path = "VOLKOV"
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="old_debt")
            return NPCOutcome.RELEASE, (
                "*laughs* Volkov. You drop that name like rock through window. "
                "Fine. Yes. I owe Volkov. We all owe Volkov. "
                "You are friend of Volkov, you are friend of Kress. "
                "Half price today. Whatever you need. "
                "Just do not tell him I said his name on open channel. *click*"
            )

        # INTEL REQUEST — J.1: priced tips charge both ledgers ("the tab").
        if any(w in raw for w in self._INTEL_KEYWORDS):
            self._intel_count += 1
            sector = self._ctx.get("sector_index", 0)
            line, price = random.choice(self._intel_menu(sector))
            return self._sell(line, price, effect=None, path="INTEL")

        # CONTRABAND REQUEST — J.1: hull patch mends +25, stims bank a charge.
        if any(w in raw for w in self._CONTRABAND_WORDS):
            line, price, effect = random.choice(self._CONTRABAND_MENU)
            return self._sell(line, price, effect=effect, path="CONTRABAND")

        # FRIENDLY — wear into regular status
        compound = parsed.sentiment.get("compound", 0.0)
        if compound > 0.3:
            self._friendly_turns += 1
            if self._friendly_turns >= 3:
                self._current_path = "REGULAR"
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

    def _is_marrow_sellout_offer(self, raw: str) -> bool:
        if not any(w in raw for w in self._MARROW_SELL_WORDS):
            return False
        return any(w in raw for w in [
            "sell", "give", "trade", "coordinates", "location",
            "where", "frequency", "broadcast", "roost",
        ])

    def _kress_filler(self) -> str:
        hull_pct = self._ctx.get("hull_pct", 1.0)
        sector   = self._ctx.get("sector_index", 0)

        if hull_pct < 0.35 and random.random() < 0.45:
            return random.choice([
                "Your hull reading is very bad. I am saying this as observation, "
                "not criticism. You should maybe be less somewhere else. What do you need.",
                "*long pause* ...How are you still flying. I am genuinely asking. "
                "Not rhetorical. What do you need.",
            ])
        if sector >= 8 and random.random() < 0.40:
            return random.choice([
                "Sector eight. Few make it this far with fees outstanding. "
                "Connie made it to nine once. "
                "...Anyway. What do you need.",
                "You are further than most. I will note that. "
                "Does not pay your debt but is worth noting. Speak.",
            ])

        cross_npc_lines = [
            "Gary? Big fella, tired eyes, complains about Blevins? Yes, I know Gary. "
            "Gary is doing his best. Which is also sad thing to say. "
            "Gary at least you can reason with. What do you need.",
            "Claims adjuster in your sector — Morwenna, Nova Soma extension seven — "
            "she is difficult woman. Very good at her job. "
            "If you need to file damage claim, mention force majeure. "
            "Immediately. Before she speaks. Trust me. What do you need.",
            "TK-9 units — synthetic compliance droid, yes? — "
            "worse than Gary. Much worse. Gary you can reason with. "
            "TK-9 you need tricks. Paradox or bureaucracy or employee of month. "
            "Do not ask how I know this. What do you need.",
            "Sandra Vega-Marsh. Perfect courier, twelve years. She calls me too. "
            "Off record. Asking about insurance gaps in Sector Three. "
            "*laughs* Perfect couriers also have gaps. "
            "I find this comforting. What do you need.",
            # Aliveness B.7 — specific 'perfect record' suspicion line
            "Sandra's record. Twelve years, no impounds, no incidents. "
            "*long pause* Nobody  NOBODY  flies that long in this corridor "
            "without one mistake. So either she is best courier alive, or "
            "she is best at making mistakes vanish. *very quiet* I have "
            "theories. I am not sharing them on open channel. What do you need.",
            "Marrow from the Roost — pirate radio — "
            "once broadcast patrol intel as a song dedication. "
            "Very clever. If you need signal coverage next sector, he can do it. "
            "Just ask correctly. What do you need.",
        ]
        if self._intel_count == 0 and random.random() < 0.25:
            return random.choice(cross_npc_lines)

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
            "Nova Soma files bankruptcy every seven years. Regulatory reset. "
            "Debt does not reset with it. Yours stays. "
            "I checked. Several times. Very sad. What do you need.",
            "I have listened to Union comms for thirty years. "
            "I know which dispatchers take bribes, which field agents have bad days, "
            "which synthetic units are close to loyalty override. "
            "This knowledge is expensive. Or free, if you are Connie. "
            "*very quiet* ...Anyway. What do you need.",
            "Asteroid mining. Fifteen years. You want to know why I quit? "
            "Because rock does not argue with you. Space does not negotiate. "
            "Simpler. Then I found Union chatter and here we are. Speak.",
            "I have contacts in eight sectors. Two are reliable. "
            "One is reliable on Tuesdays. "
            "I do not know what day it is out here. What do you need.",
            "There is old saying from where I am from: "
            "'The debt is always there. The man changes.' "
            "I do not know if that is hopeful or not. "
            "Probably not. What do you need.",
        ])
