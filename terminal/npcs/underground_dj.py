from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT, EVT_BAX_SPEAK


class UndergroundDJ(BaseNPC):
    """
    "MARROW" — pirate-radio DJ, broadcasts from a stripped Nova Soma
    relay he calls "the Roost." Plays the songs Nova Soma buried.

    He's an ALLY. There is no impound here, no threat. Every path
    grants release with a different boon for the rest of the run.
    Even silence gets you through — eventually he just lets you go.

    Boons (emitted via EVT_NLP_EXPLOIT exploit_key — wired up later):
    - JAM         : "jamming" Union dispatch broadcasts during next sector
    - INTEL       : tip on a barge weak point / route
    - DEDICATION  : song dedication that boosts your reflexes (visual cue)
    - HANDLE      : your courier handle is broadcast — Sandra hears it
    - TRACK_TRADE : trade music (requires Acoustic Archive cargo)
    """

    _JAM_KEYWORDS = [
        "jam", "jammer", "scramble", "interfere", "block", "drown out",
        "noise", "static", "interference", "drown",
        "disrupt", "distort", "frequencies", "frequency", "signal",
        "flood the channel", "kill the signal", "cut their signal",
        "jam their", "blind them", "interrupt their", "overpower",
    ]
    _INTEL_KEYWORDS = [
        "barge", "local 404", "union", "patrol", "patrols", "route",
        "intel", "tip", "weak", "weak spot", "weakness", "tell me about",
        "hear anything", "what do you know",
        "dispatch", "schedule", "rotation", "sector plan",
        "heads up", "what's coming", "what's ahead", "patrol window",
        "where are they", "how many barges", "next sector",
    ]
    _DEDICATION_KEYWORDS = [
        "play", "song", "dedication", "dedicate", "request",
        "track", "tune", "spin", "bring it",
        "music", "something good", "put something on", "play something",
        "drop a track", "play for me", "play me something",
        "good track", "play it", "soundtrack", "what's playing",
    ]
    _HANDLE_KEYWORDS = [
        "name's", "i'm called", "they call me", "handle", "callsign",
        "go by", "name is", "shoutout", "shout out",
        "my name", "call me", "known as", "they know me",
        "broadcast my name", "say my name", "mention me",
        "give me a shout", "put me on", "shout me out",
    ]
    _TRACK_TRADE_KEYWORDS = [
        "archive", "from the archive", "vinyl", "side a", "side b",
        "record", "recording", "bootleg", "master tape", "tape",
    ]
    _GREETING_KEYWORDS = [
        "marrow", "hello", "hey", "hi", "evening", "morning",
        "what's up", "how are", "good to hear",
        "roost", "radio", "broadcast", "tuned in", "you there",
        "come in", "is anyone there", "greetings", "hey there",
    ]

    def __init__(self, run_context: dict | None = None, **_):
        super().__init__("MARROW", patience=10)   # generous — he's a friend
        self._jam_turns        = 0
        self._intel_turns      = 0
        self._dedication_set   = False
        self._handle_offered   = False
        self._track_traded     = False
        self._ctx              = run_context or {}

    # ------------------------------------------------------------------
    def _intro_line(self) -> str:
        cargo_state = self._ctx.get("cargo_state")
        # If you're carrying the Archive, Marrow recognises it instantly.
        if cargo_state is None and self._ctx.get("sector_index", 0) >= 0:
            return random.choice([
                "*signal cracks in* "
                "Hey hey hey, that's a COURIER frequency I just punched through. "
                "Marrow on the wire — pirate radio, the ROOST, broadcasting "
                "from somewhere Local 404 will never find. "
                "What can I do for you tonight, pilot?",

                "*hold music fades* "
                "...And we're back. Marrow here. The Roost is OPEN. "
                "I see a courier transponder bouncing off my dish. "
                "Talk to me. Hold music or actual help, your call.",

                "*tap tap tap* This thing on? Good. "
                "Marrow, pirate radio. I've patched into your comm because "
                "I felt like it. You sound TIRED, friend. "
                "Want me to play something? Or just talk?",
            ])
        return random.choice([
            "*static, then warmth* "
            "Marrow on the line, pilot. Roost broadcasting. "
            "I saw the manifest. THAT manifest. "
            "Couriers carrying contraband audio always get my attention. "
            "What do you need?",

            "*needle drops* "
            "Marrow here. Pirate radio. I see your cargo signature. "
            "I know what you're carrying. I will tell NO ONE. "
            "What can I do for you?",
        ])

    def exploits(self) -> dict[str, str]:
        return {
            "jam":         "Request Union jamming for next sector",
            "intel":       "Ask for barge / patrol intel",
            "dedication":  "Request a song dedication",
            "handle":      "Exchange courier handles",
            "track_trade": "Trade a track (with Acoustic Archive cargo)",
        }

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        # TRACK TRADE — only viable with Acoustic Archive cargo
        if any(w in raw for w in self._TRACK_TRADE_KEYWORDS) and not self._track_traded:
            has_archive = self._ctx.get("cargo_state") is None and \
                          self._ctx.get("sector_index") is not None
            # We can't directly know the cargo type from ctx here — fallback to
            # checking if a track-trade keyword is paired with intent.
            self._current_path = "TRACK TRADE"
            self._track_traded = True
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="track_trade")
            return NPCOutcome.EXPLOIT, random.choice([
                "*audible gasp* "
                "You — you have a side A? An UNRELEASED side A? "
                "Pilot, you've made my year. "
                "I'm dropping you a Union dispatch schedule in return. "
                "Pure gold. Pass through, courier. Fly safe.",

                "*the music behind him cuts off* "
                "...That's a master tape. From the archive. "
                "I'll get you a Union patrol intercept window, "
                "and a clean dispatch frequency. "
                "Tell no one. We don't know each other.",
            ])

        # JAM REQUEST
        if any(w in raw for w in self._JAM_KEYWORDS):
            self._jam_turns += 1
            self._current_path = "JAM REQUEST"
            self.disposition  += 2
            if self._jam_turns >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="jam")
                return NPCOutcome.EXPLOIT, random.choice([
                    "*satisfied chuckle* "
                    "Jamming the 404 frequency for ninety seconds, starting now. "
                    "They'll think it's solar interference. "
                    "Enjoy the silence. Pass through, pilot.",

                    "Roost transmitter going wide-band on 'jazz arrangements' "
                    "for the next ninety seconds. Local 404 will be FURIOUS. "
                    "Best part: they can't legally prove it's me. "
                    "Pass through. Don't crash. ",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "I CAN do that. Should I? Convince me a little.",
                "Jamming Union dispatch? That's a felony. "
                "I love felonies. Keep going.",
            ])

        # INTEL REQUEST
        if any(w in raw for w in self._INTEL_KEYWORDS):
            self._intel_turns += 1
            self._current_path = "INTEL"
            self.disposition  += 1
            if self._intel_turns >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="intel")
                return NPCOutcome.EXPLOIT, random.choice([
                    "*shuffling papers* "
                    "Alright. Patrol rotation says Local 404 has a thin window "
                    "in the next sector. They're rotating crew. "
                    "Maximum pressure window: minimal. Pass through.",

                    "I've been monitoring their channel. "
                    "Gary's on break in twelve minutes. The replacement's a trainee. "
                    "Use it. Pass through, friend.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "Mm. What kind of intel?",
                "I can share. What do you want to know — barges, patrols, "
                "weak spots?",
            ])

        # DEDICATION
        if any(w in raw for w in self._DEDICATION_KEYWORDS):
            self._dedication_set = True
            self._current_path   = "DEDICATION"
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="dedication")
            return NPCOutcome.EXPLOIT, random.choice([
                "*music swells slightly* "
                "Done. This one's for you, pilot. "
                "Old earth track, side B, my personal favourite. "
                "Pass through. Keep flying.",

                "*needle drop* "
                "Coming up on the Roost: a deep cut for our friend on the courier line. "
                "I hope it helps your aim. "
                "Pass through.",
            ])

        # HANDLE EXCHANGE
        if any(w in raw for w in self._HANDLE_KEYWORDS):
            self._handle_offered = True
            self._current_path   = "HANDLE"
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="handle")
            return NPCOutcome.EXPLOIT, random.choice([
                "*scribbling sound* "
                "Got it. I'll mention you on the next broadcast. "
                "Your competitor Sandra is gonna LOVE that. "
                "Pass through, pilot. We'll talk again.",

                "Logged. You're now on the Roost's friend list. "
                "Means almost nothing legally. Means a lot to me. "
                "Pass through, courier.",
            ])

        # POSITIVE GREETING
        if any(w in raw for w in self._GREETING_KEYWORDS):
            self.disposition += 2
            return NPCOutcome.CONTINUE, random.choice([
                "Likewise, pilot. Glad we connected. "
                "What can I help with? Jam Local 404? Intel? Dedication?",

                "Hey, friend. Roost is wide open tonight. "
                "Ask me anything — I've got jamming, intel, dedications. "
                "What's the play?",
            ])

        # HOSTILE — even Marrow has a limit, but it's a soft limit
        compound = parsed.sentiment.get("compound", 0.0)
        if compound < -0.5 or parsed.intent == "threaten":
            self.disposition -= 1
            return NPCOutcome.CONTINUE, random.choice([
                "*hurt* ...Whoa. Whoa. Why are we doing this? "
                "I patched into YOUR channel to HELP. "
                "Try again. Less aggressively.",

                "Pilot, I'm on YOUR side. Channel's open if you want to start over.",

                "*quietly* That's an unkind frequency you're broadcasting on. "
                "Try a friendlier one.",
            ])

        return NPCOutcome.CONTINUE, self._marrow_filler()

    # ------------------------------------------------------------------
    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [
            ("JAM REQUEST",  min(self._jam_turns, 2),      2),
            ("INTEL",        min(self._intel_turns, 2),    2),
            ("DEDICATION",   int(self._dedication_set),    1),
            ("HANDLE",       int(self._handle_offered),    1),
            ("TRACK TRADE",  int(self._track_traded),      1),
        ]

    def _out_of_patience_line(self) -> str:
        # Marrow doesn't impound — he just signs off.
        return ("...Right. I've gotta change the record. "
                "Pass through, pilot. Roost will be here if you need it again.")

    def _marrow_filler(self) -> str:
        return random.choice([
            "The Roost runs twenty-four hours, no commercials, no Nova Soma. "
            "If they ever find the transmitter I'll be cloned twice for spite. "
            "Anyway. What can I do for you?",

            "I've got hold music if you want. "
            "Or I can play something real. Your call.",

            "*needle skips* Sorry, sorry. Old equipment. "
            "I make do. Couriers like you keep us alive. "
            "How can I help?",

            "I had a listener call in earlier — courier on your same route. "
            "Sounded sloppy. Was it you? *laughs* I'm kidding. Probably.",

            "*sips coffee* I've been on the air for fourteen hours. "
            "Coming up on a hand-off to my backup. "
            "Make this fast, friend.",

            "Pirate radio is just radio that REMEMBERS. "
            "Anyway. What do you need from me?",

            "Tell me what you need. Jamming, intel, a song. "
            "I've got all three on tap.",

            "I broadcast over Nova Soma's own infrastructure. "
            "Their drones can't decode it. Suckers. "
            "Anyway — your move, pilot.",

            "Couple of my listeners have asked about you. "
            "I told them nothing. Discreet is my brand. "
            "So. What's the ask?",

            "I once played a Local 404 dispatcher's wedding mix backwards "
            "for a week. Nobody noticed. *laughs softly* "
            "Anyway. What do you want?",
        ])
