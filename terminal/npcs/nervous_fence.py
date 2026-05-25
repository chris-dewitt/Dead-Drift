"""
Nervous Fence — RELAY-7 FELIX. Off-the-books gate broker who's always
sixty seconds from getting caught and desperately wants to "go legit"
one day. Will trade barge patrol intel for almost anything.

Win paths:

DEAL                — offer cargo manifest / "show you what's inside" /
                      partial contents. One turn. Direct trade.

CREDIT              — pay >= 800 credits up front. One turn.

SYMPATHY            — share outsider status (debt / clone / nova soma).
                      50% chance of immediate release, otherwise 2 turns.

DISTRACT            — ask about his "plan" 3 times. He talks too long
                      and forgets to flag you.

LEGITIMACY MENTOR   — give him real business advice (LLC, incorporate,
                      tax ID, license, permit, lawyer, business plan).
                      2 turns. He sees you as a peer and lets you through.

PARANOIA / GOSSIP   — mention another NPC by name (Gary, Kress, Morwenna,
                      Marrow, Holt, Sandra). He gets distracted prying for
                      info. 2 turns of gossip → release.

VALIDATION / EGO    — compliment his operation ("the best", "famous",
                      "always use Felix", "you saved my last run"). Ego
                      boost. 2 turns → release.

TIME-PRESSURE STALL — stall repeatedly ("wait", "hold on", "give me a
                      second"). After 4 stalls he panics and opens the
                      gate just to close the channel.

HOSTILE             — overt threat (report / expose / arrest / snitch).
                      Immediate barge call. IMPOUND. Soft hostility
                      (insult / aggression) just costs patience.
"""
from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT

_DEAL_KEYWORDS = [
    "manifest", "contents", "partial contents", "cargo list",
    "what's inside", "show you", "tell you what", "give you",
    "trade", "exchange", "deal", "swap", "offer you", "barter",
]
_CREDIT_AMOUNT = 800
_SYMPATHY_KEYWORDS = [
    "debt", "clone", "owe", "broke", "same boat", "one of us",
    "just trying", "trying to survive", "trying to get by",
    "not that different", "we're the same", "understand",
    "struggling", "system", "corpo", "corporation", "nova soma",
    "behind on payments", "rent", "fees", "quota",
]
_DISTRACT_KEYWORDS = [
    "plan", "plans", "legitimate", "real work", "business",
    "what do you do", "tell me about", "your operation",
    "side hustle", "when you're done", "getting out",
    "one day", "dream", "future", "retire", "vision",
]
_HOSTILE_KEYWORDS = [
    "report you", "expose you", "authorities", "turn you in", "rat you out",
    "ratted you", "illegal operation", "arrest you", "warrant for",
    "snitch", "grass you up", "not your friend", "scan your channel",
    "transponder check", "log this channel", "file complaint",
    "trace your signal", "i'll tell", "going to tell",
]
# New: business/legal advice keywords — Felix wants to go legit
_LEGITIMACY_KEYWORDS = [
    "llc", "incorporate", "incorporated", "incorporation",
    "tax id", "ein", "license", "licensed", "permit",
    "business plan", "lawyer", "attorney", "accountant",
    "register your business", "trademark", "logo design",
    "domain name", "website", "branding", "marketing",
    "small business loan", "grant", "consultancy", "consult",
    "venture capital", "angel investor",
]
# New: ego/validation keywords
_VALIDATION_KEYWORDS = [
    "the best", "famous", "saved my", "always use", "regular client",
    "everyone says", "people talk about you", "reputation",
    "highly recommended", "heard great things", "your work",
    "you're good", "you're the best", "respect you",
    "you're a professional", "a pro", "talented",
]
# New: stall keywords
_STALL_KEYWORDS = [
    "wait", "hold on", "give me a second", "give me a sec",
    "one moment", "hang on", "hold up", "uh", "um", "umm",
    "let me check", "let me think", "thinking", "buffering",
    "lag", "frozen", "your connection",
]
# New: other NPCs Felix knows / fears
_OTHER_NPCS = {
    "gary":     ("Gary", "Local 404 - Repo. Hates him. Fears him."),
    "pruitt":   ("Gary", "Local 404 - Repo. Hates him. Fears him."),
    "kress":    ("Kress", "Russian fence. Felix's actual competitor."),
    "morwenna": ("Morwenna", "Nova Soma claims. Felix WILL NOT cross her."),
    "marrow":   ("Marrow", "Underground DJ. Felix listens, never admits."),
    "holt":     ("Inspector Holt", "STA checkpoint. Pure poison to Felix's operation."),
    "inspector":("Inspector Holt", "STA checkpoint. Pure poison to Felix's operation."),
    "sandra":   ("Sandra", "Repo. Better than Gary. Felix has heard the name."),
    "dispatcher":("the dispatcher", "Union. Probably knows Felix exists. Felix prays not."),
    "tk-9":     ("TK-9", "Compliance droid. Glitchy. Felix once almost sold one a freighter."),
    "tk9":      ("TK-9", "Compliance droid. Glitchy. Felix once almost sold one a freighter."),
    "dray":     ("Dray", "Other off-channel courier. Felix has wave-traded with him before."),
}


class NervousFence(BaseNPC):
    """Grey-market relay contact. Will trade intel for almost anything."""

    def __init__(self, vocabulary_vault=None, run_context: dict | None = None, **_):
        super().__init__("RELAY-7 FELIX", patience=8)
        self._vault         = vocabulary_vault
        self._ctx           = run_context or {}
        self._deal_offered  = False
        self._paid          = False
        # Aliveness B.1 — actual credit amount paid (drives standard label)
        self._bribe_paid    = 0
        self._distract_t    = 0
        self._sympathy_t    = 0
        self._legit_t       = 0
        self._gossip_t      = 0
        self._gossip_target = ""
        self._validation_t  = 0
        self._stall_t       = 0
        self._spooked       = False
        self._soft_hostile  = 0

    # ------------------------------------------------------------------
    def _intro_line(self) -> str:
        run_snaps     = self._ctx.get("run_snaps", 0)
        run_slingshots = self._ctx.get("run_slingshots", 0)
        hull_pct      = self._ctx.get("hull_pct", 1.0)
        sector        = self._ctx.get("sector_index", 0)

        if hull_pct < 0.30:
            return random.choice([
                "*static* Oh — oh god, your hull telemetry is leaking onto open band. "
                "You look terrible. Look — Felix. Relay-7. I can get you past the next "
                "gate FAST if you just... give me something. Anything. Quickly.",

                "Relay-7. Felix. I see your damage profile on the broker net — that's bad, "
                "that's really bad. *typing* I'm prepping a gate-clear package. "
                "I just need you to agree to give me something. We can negotiate AFTER. "
                "Just say yes first. Please.",

                "*whispering* You're broadcasting distress on six frequencies right now. "
                "The barges will find you in nine minutes. I can clear two gates ahead "
                "of you — I just need an offer. Move fast. Move FAST.",
            ])

        if run_snaps >= 2:
            return random.choice([
                f"*nervous laugh* Yeah I — I heard about the {run_snaps} cable snaps. "
                "The repo guys talk on a wider band than they think. "
                "Look — Felix. Relay-7. I can route you around the next barge entirely. "
                "But the price just went up. They're MAD at you. What've you got?",

                f"You're the one who snapped {run_snaps} harpoons? *quiet whistle* "
                "Okay. I respect that. I want NOTHING to do with that, but I respect it. "
                "Felix, Relay-7. Pay me and I clear your gate. "
                "Pay me MORE because the heat is on you specifically.",
            ])

        if run_slingshots >= 3:
            return random.choice([
                f"*surprised* Wait — are you the {run_slingshots}-slingshot pilot from "
                "Sector traffic? I heard about you. Felix, Relay-7. "
                "Look, talent like that, I want you ON my client list. "
                "What do you need? Patrol routes? Gate clears? Name it.",
            ])

        if sector >= 5:
            return random.choice([
                f"*static burst* Five sectors deep. You've been busy. Felix. Relay-7. "
                "Most pilots don't make it this far without a broker on retainer. "
                "I could BE that broker. Discount, first-time, just to prove value. "
                "What've you got for me.",
            ])

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

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        # ------------ HARD HOSTILE — overt threat ----------------------
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

                "*panic* No no no — I have a kill-switch protocol for this. "
                "Channel ping going out. Barge dispatch logging your bearing. "
                "Whatever happens next is on you. I — I really hoped you weren't like this.",
            ])

        # ------------ CARGO DEAL --------------------------------------
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

        # ------------ CREDIT BRIBE ------------------------------------
        # Aliveness B.8 — too-low bribe gets a specific counter-offer
        # naming the floor, not vague filler.
        if (parsed.amount is not None
                and 0 < parsed.amount < _CREDIT_AMOUNT):
            self._current_path = "BRIBE"
            return NPCOutcome.CONTINUE, random.choice([
                f"*nervous laugh* {parsed.amount}? Felix's floor is "
                f"{_CREDIT_AMOUNT}. *exact* It's not negotiable. Well — it IS, "
                "but it's not, and we'd both rather not have that conversation.",
                f"You said {parsed.amount} credits. The number is {_CREDIT_AMOUNT}. "
                "That's the broker rate. I have overheads. Power costs. "
                "Trauma costs. Round up.",
                f"{parsed.amount}? *pause* I'd love to. Genuinely. "
                "But the floor's {_CREDIT_AMOUNT} and the floor is the floor. "
                "*hopeful* Try {_CREDIT_AMOUNT}?".format(
                    _CREDIT_AMOUNT=_CREDIT_AMOUNT),
            ])

        if parsed.amount is not None and parsed.amount >= _CREDIT_AMOUNT:
            self._paid = True
            self._bribe_paid = parsed.amount
            # Aliveness B.1 — standardised dossier label
            self._current_path = f"BRIBE [{parsed.amount} cr]"
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

                f"*incredulous* {parsed.amount}? Up front? "
                "I'm — okay, you're a serious operator. I respect that. "
                "Sending the full broker package. Gates, patrol times, "
                "and one of my backup transponders for emergencies. Go.",
            ])

        # ------------ LEGITIMACY MENTOR (NEW) -------------------------
        if any(w in raw for w in _LEGITIMACY_KEYWORDS):
            self._legit_t += 1
            self._current_path = "LEGITIMACY"
            self.disposition += 3
            if self._legit_t >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc="nervous_fence", exploit_key="legitimacy_mentor")
                if self._vault:
                    self._vault.record("nervous_fence", "LEGITIMACY_MENTOR")
                return NPCOutcome.RELEASE, random.choice([
                    "*genuine emotion* You — you actually KNOW this stuff. "
                    "Nobody talks to me like a real businessperson. "
                    "Hold on — *typing furiously* I'm clearing your route and adding "
                    "you to my 'consultants' list. When I'm legit, you get a referral fee. "
                    "Promise. Go on through. Thank you.",

                    "*almost teary* That's the most useful advice anyone's given me in two years. "
                    "Tax ID. RIGHT. Why didn't I think of that. "
                    "Look — gates eleven through fifteen, all yours. "
                    "I'm taking notes. You're a good person. Don't tell anyone I said that.",

                    "*professional now* Understood. I'll start the paperwork tomorrow. "
                    "Today actually. Today. Look — patrol routes, full upload. "
                    "Three-sector clearance. This is what mentorship feels like, isn't it. "
                    "I've heard about this.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*excited* Wait — say more. Are you saying I should incorporate "
                "BEFORE I get the license, or after?",

                "*scribbling* Hold on, hold on, let me write that down. "
                "Domain name first or business plan first?",

                "Oh wow. Nobody's ever — most people just want the gate routes. "
                "You're actually trying to HELP. Keep going. Tell me everything.",

                "*frantic typing* This is gold. This is GOLD. "
                "And the lawyer thing — would I need one before or after the LLC? "
                "Tell me more. Then we'll talk about your route. Promise.",
            ])

        # ------------ PARANOIA / GOSSIP (NEW) --------------------------
        # Playtest fix: bare "gossip" / "rumor" used to fall through to
        # filler. It now arms the path and prompts Felix to ask whose
        # name we have. Patience still ticks, but the player gets clear
        # signal that they're on a real path.
        if (any(w in raw for w in ("gossip", "rumor", "rumors", "rumour",
                                    "rumours", "intel", "talk about",
                                    "word on", "chatter"))
                and self._gossip_t == 0):
            self._gossip_t += 1
            self._current_path = "GOSSIP"
            self.disposition += 1
            return NPCOutcome.CONTINUE, random.choice([
                "*sharp inhale* Gossip? About *whom*? Names, names. "
                "I don't trade in vague feelings.",
                "Rumour from where? Specifically. *paranoid* "
                "Is it about me?",
                "Word on the relay is great, but I need a NAME, courier. "
                "Drop one.",
            ])

        gossip_match = None
        for key, (display, _flavor) in _OTHER_NPCS.items():
            if key in raw:
                gossip_match = (key, display)
                break
        if gossip_match is not None:
            key, display = gossip_match
            self._gossip_t += 1
            self._gossip_target = display
            self._current_path = "GOSSIP"
            self.disposition += 1
            if self._gossip_t >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc="nervous_fence", exploit_key="gossip")
                if self._vault:
                    self._vault.record("nervous_fence", "GOSSIP")
                return NPCOutcome.RELEASE, random.choice([
                    f"*conspiratorial* Right — so what does {display} actually know "
                    "about me? Be honest. Be brutal. Okay you know what, "
                    "*sound of channel switching* I need to deal with this. "
                    "Your gate's open. We never spoke. GO.",

                    f"*spiraling* Oh god, if {display} is talking about me, "
                    "I need to relocate the whole relay rig. "
                    "*muttering* Tonight. Tonight tonight tonight. "
                    "Look, you — go. Gate's clear. I have to make calls.",

                    f"*scattered* {display}. Yes. {display}. "
                    "I knew this was coming. I — okay your route is uploaded, "
                    "I have to encrypt my contact list now, GO. PLEASE GO.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                f"*sharp inhale* {display}? You — you've talked to {display}? "
                "What did they say. Specifically. Word for word.",

                f"*nervous* {display} doesn't come up on this channel often. "
                "What's your connection? Are you — are you sent by them?",

                f"*paranoid* Did {display} send you? Be honest. "
                "I'm not mad. I just need to know. *checking five screens at once*",
            ])

        # ------------ VALIDATION / EGO (NEW) ---------------------------
        if any(p in raw for p in _VALIDATION_KEYWORDS):
            self._validation_t += 1
            self._current_path = "VALIDATION"
            self.disposition += 2
            if self._validation_t >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc="nervous_fence", exploit_key="validation")
                if self._vault:
                    self._vault.record("nervous_fence", "VALIDATION")
                return NPCOutcome.RELEASE, random.choice([
                    "*audibly preening* Well, I — yes, I do pride myself on quality service. "
                    "Look — for a valued client like you, the gate's on the house. "
                    "Just this once. Spread the word though. Quietly.",

                    "*overwhelmed* Nobody — nobody's ever said that to me on the relay. "
                    "Most clients just call me a discount Kress. Which I am NOT. "
                    "*sniffles* Go on through. Gate's clear. Tell your friends. "
                    "Quietly.",

                    "*professional cool* Of course. Reputation matters in this game. "
                    "I appreciate the recognition. *sound of forms being prepared* "
                    "VIP-tier clearance. Three sectors. You're an asset to the network.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*pleased* Oh. Oh really? People are saying that? "
                "...What ELSE are they saying? Specifically the good things.",

                "*chuffed* I mean, I do try. The relay is a labor of love. "
                "Tell me more about — uh — about the recognition.",

                "Reputation matters in this business. Keep going. "
                "I want to make sure I deserve it.",
            ])

        # ------------ SYMPATHY ----------------------------------------
        if any(w in raw for w in _SYMPATHY_KEYWORDS):
            self._sympathy_t += 1
            self._current_path = "SYMPATHY"
            self.disposition += 2
            if self._sympathy_t == 1 and random.random() < 0.5:
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
            if self._sympathy_t >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc="nervous_fence", exploit_key="shared_outsider")
                if self._vault:
                    self._vault.record("nervous_fence", "SHARED_OUTSIDER")
                return NPCOutcome.RELEASE, random.choice([
                    "*quiet resignation* Look. I keep telling myself I'm above this. "
                    "I'm not. We're all just trying to make rent. Gate's open. Go.",

                    "*sighs* You and me both, friend. "
                    "Route's clear. Don't make a habit of getting caught.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*softening* I hear you. I really do. "
                "Give me something I can work with on my end though.",
                "We're not so different, you and me. ...What are you carrying though.",
                "That's... that's real. *pause* I still need something from you though.",
                "*quiet* My fourth body's eight months from being repossessed too. "
                "...Doesn't change the gate fee though. Or does it. ...Keep talking.",
            ])

        # ------------ DISTRACT (his "plans") --------------------------
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

                    "*deep in monologue* — and the rebrand would obviously involve "
                    "ditching the Relay-7 designation, maybe something cleaner like — "
                    "*alarm beep* Oh that's the gate-flag countdown. "
                    "Go. Just go. I'll backdate the manifest. Cheers.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*brightening* Oh, the plan! The plan is — "
                "well, it starts with capital accumulation, which is where the relay comes in.",

                "The legitimate business? It's a transit consultancy. "
                "Not unlike what I do now but with a license and a better chair.",

                "I've got a whole roadmap. Five years, maybe six. "
                "Phase One is already underway technically.",

                "Phase Two involves a fresh ID and a small office above a noodle bar "
                "in Sector Two. I've already picked the noodle bar.",
            ])

        # ------------ TIME-PRESSURE STALL (NEW) ------------------------
        if any(w in raw for w in _STALL_KEYWORDS):
            self._stall_t += 1
            self._current_path = "TIME PRESSURE"
            if self._stall_t >= 4:
                bus.emit(EVT_NLP_EXPLOIT, npc="nervous_fence", exploit_key="time_pressure")
                if self._vault:
                    self._vault.record("nervous_fence", "TIME_PRESSURE")
                return NPCOutcome.RELEASE, random.choice([
                    "*hyperventilating* OKAY YOU KNOW WHAT JUST GO. "
                    "Gate's open. I can't hold this channel any longer. "
                    "The auto-flag is THIRTY SECONDS out. JUST GO.",

                    "*cracking* I cannot — I CANNOT keep this channel open. "
                    "Going through. You're clear. CHANNEL CLOSING. "
                    "I have to go relocate the rig now. Bye. BYE.",

                    "*screaming whisper* Just — just go. Gate's open. "
                    "I won't bill you. I'll forget this happened. "
                    "Please get off my channel. Please.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*increasingly anxious* Are you — are you frozen? "
                "Your transponder's still active. Please respond.",

                "*alarmed* The auto-flag timer doesn't pause for your buffering. "
                "Hello? HELLO?",

                f"*panicking quietly* That's the {self._stall_t}th time you've said "
                "that. The barges sweep this band every minute and a half. "
                "Hello? Please?",

                "I — okay if this is a tactic it's working and I hate it. "
                "Say something. ANYTHING.",
            ])

        # ------------ SOFT HOSTILITY — insult / aggression ------------
        compound = parsed.sentiment.get("compound", 0.0)
        if compound < -0.5 or parsed.intent == "threaten":
            self._soft_hostile += 1
            self._patience -= 1
            if self._soft_hostile >= 3:
                self._patience = 0
                return NPCOutcome.IMPOUND, random.choice([
                    "*hardening* You know what, I'm not paid enough for this. "
                    "*ping* Patrol notified. Enjoy the barge.",

                    "*finally angry* I have FEELINGS, you knob. "
                    "*sends coordinates* They'll be on you in two minutes.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*hurt* You don't have to be like that.",
                "*sniffing* I'm a person. I have a name. It's Felix.",
                "*quiet* That stings. I'm offering you a way out, mate.",
            ])

        # ------------ POSITIVE TONE — build disposition --------------
        if compound > 0.3:
            self.disposition += 1
            if self.disposition >= 5:
                bus.emit(EVT_NLP_EXPLOIT, npc="nervous_fence", exploit_key="rapport")
                return NPCOutcome.RELEASE, random.choice([
                    "*warmly* You know what, you've been nothing but nice to me. "
                    "Most clients won't even use my name. Gate's open. "
                    "Tell your friends about Felix. Quietly.",

                    "*surprised softness* I — yeah. Yeah, alright. "
                    "Free of charge. Patrol routes uploaded. "
                    "It's been a long week. You're a bright spot.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*pleased* That's — thank you. That's nice. "
                "Doesn't change my fee structure but I'm noting the tone.",

                "*relaxing slightly* You're a lot easier to talk to than most. "
                "Keep going. Maybe we can work something out.",
            ])

        return NPCOutcome.CONTINUE, self._nervous_filler()

    # ------------------------------------------------------------------
    def _nervous_filler(self) -> str:
        # Signal when close
        if self.disposition >= 3:
            return random.choice([
                "*almost there voice* You're doing great. Just — give me an offer. "
                "Or a name. Or a number. Anything. We're so close.",

                "*hopeful* I want to clear this gate. I really do. "
                "Throw me a bone. Manifest, credits, story — anything.",

                "*quieter* I'm in a good mood today. Use it. "
                "Make me an offer.",
            ])

        # Hint after 3 turns of zero progress
        if (self._turn >= 3 and not self._deal_offered and not self._paid and
                self._sympathy_t == 0 and self._distract_t == 0 and
                self._legit_t == 0 and self._gossip_t == 0 and
                self._validation_t == 0 and self.disposition <= 0):
            return random.choice([
                "*frustrated whisper* Look, I'll be straight with you. "
                "Most clients pay me. Some trade cargo. The clever ones distract me. "
                "The KIND ones share a story. Pick one and run with it.",

                "*coaching* I'm not your enemy here. "
                "Offer me credits. Offer me cargo info. Tell me about your debt. "
                "Help me retire. SOMETHING. The clock is ticking.",

                "*tutorial-voice* My exploits are an open secret. "
                "Cargo manifests open gates. Eight hundred credits opens gates. "
                "Compliments work on me more than they should. So does gossip. "
                "Pick a path. Please.",
            ])

        # Cross-NPC callbacks
        if self._turn == 3 and random.random() < 0.35:
            return random.choice([
                "*sidetracked* Hey have you ever dealt with Kress? "
                "He undercuts me. Constantly. Russian bastard. Power down — "
                "I mean — give me an offer. Sorry, that's Gary's line.",

                "Morwenna's claims department flagged three of my safe-houses last quarter. "
                "*paranoid* You haven't talked to her, have you? "
                "Wait — don't answer that. Make me an offer.",

                "Inspector Holt's been ramping up STA scans this week. "
                "I lost two good clients to his manifest checks. "
                "*sigh* You should be paying me extra just for the inflation. "
                "Make an offer.",
            ])

        # Hull-aware filler
        hull_pct = self._ctx.get("hull_pct", 1.0)
        if hull_pct < 0.50 and random.random() < 0.30:
            return random.choice([
                "*concerned* Your hull is in the red, by the way. "
                "Did you know about that? I have a medic contact. Mira. "
                "I take a 15% finder's fee. Just — focus, what's your offer.",

                "Look I'd sell you Mira Voss's contact info but you're not in "
                "shape for negotiations. Pay me FIRST then I'll route you to her.",
            ])

        # Stock filler
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
            "*muttering* My rent's due. Help me out.",
            "I have an espresso machine on layaway. Help me make my next payment.",
            "*frantically tidying papers off-channel* Don't mind the background noise.",
            "Once I'm legit I'll send you a referral discount. Help me get there.",
            "I'm a small business. I'm a SMALL BUSINESS. Treat me like one.",
            "Channel-Six is judging me. I can feel it. They have a wider client base. "
            "But I have HEART. Make an offer.",
        ])

    # ------------------------------------------------------------------
    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [
            ("CARGO DEAL",   int(self._deal_offered),         1),
            # Aliveness B.1 — standardised label, falls back to floor.
            ((f"BRIBE [{self._bribe_paid} cr]" if self._bribe_paid > 0
              else f"BRIBE [{_CREDIT_AMOUNT}+ cr]"),
             int(self._paid), 1),
            ("SYMPATHY",     min(self._sympathy_t, 2),         2),
            ("DISTRACT",     min(self._distract_t, 3),         3),
            ("LEGITIMACY",   min(self._legit_t, 2),            2),
            ("GOSSIP",       min(self._gossip_t, 2),           2),
            ("VALIDATION",   min(self._validation_t, 2),       2),
            ("TIME PRESSURE",min(self._stall_t, 4),            4),
        ]

    def exploits(self) -> dict[str, str]:
        return {
            "cargo_manifest":    "Offer cargo manifest / contents as trade",
            "credit_deal":       "Offer 800+ credits directly",
            "shared_outsider":   "Bond over debt / clone status",
            "distraction":       "Ask about his 'plan' 3 times — he forgets",
            "legitimacy_mentor": "Give him real business advice (LLC, license, tax ID)",
            "gossip":            "Mention another NPC by name — paranoia takes him",
            "validation":        "Compliment his work — ego unlocks the gate",
            "time_pressure":     "Stall 4 times — he panics, opens the gate",
            "rapport":           "Stay consistently kind — disposition wears him down",
        }
