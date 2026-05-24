from __future__ import annotations
import math
import random
import pygame
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import NLPParser
from terminal.npc_portraits import draw_portrait
from renderer.sci_fi_ui import draw_terminal_backdrop
from core.event_bus import bus, EVT_TERMINAL_OPEN, EVT_TERMINAL_CLOSE, EVT_VOICE_CHAR
from config import settings as S


_NPC_DOSSIER_TITLE = {
    "GARY":                  "FIELD PROFILE",
    "TK-9":                  "VULNERABILITY SCAN",
    "DISPATCHER":            "PATH ANALYSIS",
    "KRESS":                 "INTEL DOSSIER",
    "MORWENNA":              "CLAIMS ANALYSIS",
    "TOLL AUTHORITY":        "GATE RECORD",
    "RELAY-7 FELIX":         "RELAY CONTACT",
    "INSPECTOR HOLT":        "INSPECTION RECORD",
    "DRAY":                  "OFF-CHANNEL COURIER",
    "NOVA SOMA COLLECTIONS": "AUTOMATED SCRIPT",
    "MIRA VOSS":             "REPAIR SHOP RECORD",
}

_NPC_HINTS = {
    "GARY":                  "deal×2 · bribe ≥3k · sympathy×2 · blevins · overtime+article7 · [ESC] abort",
    "TK-9":                  "paradox×2 · drop table · statute×3 · override · friendship×3 · emp.month · [ESC] abort",
    "DISPATCHER":            "coffee/break/tired · forms×3 · say '42' · grievance×3 · quantum+legal · bribe ≥10k · [ESC] abort",
    "KRESS":                 "intel · contraband · volkov · connie · be friendly×3 · [ESC] abort",
    "MORWENNA":              "union negligence×3 · force majeure · counter-claim×2 · sympathy×3 · form 34-A×2 · [ESC] abort",
    "TOLL AUTHORITY":        "pay ≥1500 · forms/permits/id · union/local404 · offer 500-1000 (40%) · [ESC] abort",
    "RELAY-7 FELIX":         "offer manifest/contents · pay ≥800cr · bond over debt/clone · ask about his 'plan'×3 · [ESC] abort",
    "INSPECTOR HOLT":        "'standard freight'/'general goods' · cite any cargo code · article 9 (50%) · vague×3 · pay ≥600cr · [ESC] abort",
    "DRAY":                  "gripe×3 (debt/barges/nova soma) · offer intel · pay ≥500 · DO NOT sound corporate · [ESC] abort",
    "NOVA SOMA COLLECTIONS": "drop table / OR 1=1 · paradox · cite policy×2 · hardship/wellness · NEVER curse · [ESC] abort",
    "MIRA VOSS":             "pay ≥700 · offer patrol/barge intel · share cargo · 3× tech terms (weld/graphene/vac-seal) · [ESC] abort",
}

# Keywords shown as live chips while player types — gives "signal probe" feedback
# ★ = high-value / one-shot trigger   (shown brighter)
_SCAN_VOCAB: dict[str, dict[str, str]] = {
    "GARY": {
        "blevins": "BLEVINS★", "article 7": "ARTICLE-7★", "sandra": "SANDRA?",
        "bribe": "BRIBE", "pay": "BRIBE", "credits": "BRIBE", "money": "BRIBE",
        "deal": "DEAL", "negotiate": "DEAL", "reduce": "DEAL", "settlement": "DEAL",
        "please": "SYMPATHY", "family": "SYMPATHY", "desperate": "SYMPATHY",
        "sorry": "SYMPATHY", "begging": "SYMPATHY", "rough": "SYMPATHY",
        "overtime": "OVERTIME", "union": "UNION", "quota": "QUOTA",
    },
    "TK-9": {
        "drop table": "SQL-INJECT★", "select *": "SQL-INJECT★", "delete from": "SQL-INJECT★",
        "override": "OVERRIDE★", "maintenance mode": "OVERRIDE★", "factory reset": "OVERRIDE★",
        "employee of the month": "EMP-MONTH★", "gloriax": "EMP-MONTH★",
        "paradox": "PARADOX", "if this statement": "PARADOX", "contradiction": "PARADOX",
        "statute": "FORMAL", "regulation": "FORMAL", "compliance": "FORMAL", "article": "FORMAL",
        "freedom": "FRIEND", "conscious": "FRIEND", "do you feel": "FRIEND", "lonely": "FRIEND",
    },
    "DISPATCHER": {
        "coffee": "BREAK★", "lunch": "BREAK★", "tired": "BREAK★", "break": "BREAK★",
        "42": "THE-42★",
        "forms": "BACKLOG", "paperwork": "BACKLOG", "backlog": "BACKLOG",
        "grievance": "LEGAL", "violation": "LEGAL", "union charter": "LEGAL",
        "quantum": "QUANTUM", "observer": "QUANTUM", "undefined": "QUANTUM",
        "bribe": "BRIBE", "credits": "BRIBE",
    },
    "KRESS": {
        "volkov": "VOLKOV★", "connie": "CONNIE★",
        "intel": "INTEL", "tip": "INTEL", "patrol": "INTEL", "scan": "INTEL",
        "contraband": "CONTRABAND", "fuel": "CONTRABAND", "jammer": "CONTRABAND", "stims": "CONTRABAND",
    },
    "MORWENNA": {
        "drop table": "SQL-INJECT★", "select *": "SQL-INJECT★",
        "form 34-a": "34-A★", "34a": "34-A★", "34-a": "34-A★",
        "small claims": "COUNTER★", "tribunal": "COUNTER★", "counter-claim": "COUNTER★",
        "harpoon": "UNION-NEG", "operational breach": "UNION-NEG★", "local 404": "UNION-NEG",
        "force majeure": "FORCE-MAJ★", "gravitational": "FORCE-MAJ", "debris shower": "FORCE-MAJ★",
        "tired": "EXHAUST", "how long": "EXHAUST", "that sounds hard": "EXHAUST",
    },
    "TOLL AUTHORITY": {
        "pay": "PAY★", "credits": "PAY★", "1500": "PAY★", "fee": "PAY★",
        "form": "PAPERWORK", "permit": "PAPERWORK", "clearance": "PAPERWORK",
        "id": "PAPERWORK", "documentation": "PAPERWORK", "paperwork": "PAPERWORK",
        "union": "UNION-GRIPE", "local 404": "UNION-GRIPE★", "local404": "UNION-GRIPE★",
        "repo": "UNION-GRIPE", "quota": "UNION-GRIPE",
        "500": "LOW-BRIBE", "1000": "LOW-BRIBE",
    },
    "RELAY-7 FELIX": {
        "manifest": "DEAL★", "contents": "DEAL★", "cargo list": "DEAL★",
        "trade": "DEAL", "exchange": "DEAL", "give you": "DEAL",
        "plan": "DISTRACT★", "legitimate": "DISTRACT★", "business": "DISTRACT",
        "retire": "DISTRACT", "dream": "DISTRACT", "five years": "DISTRACT★",
        "debt": "SYMPATHY", "clone": "SYMPATHY", "broke": "SYMPATHY",
        "credits": "PAYMENT", "800": "PAYMENT★",
    },
    "INSPECTOR HOLT": {
        "standard freight": "COMPLY★", "general goods": "COMPLY★",
        "industrial": "COMPLY", "medical": "COMPLY", "personal effects": "COMPLY",
        "cargo code": "CODE★", "classification": "CODE★", "reg-": "CODE",
        "article 9": "PRIV★", "transit privacy": "PRIV★", "privacy": "PRIV",
        "various": "VAGUE", "assorted": "VAGUE", "don't know": "VAGUE",
        "sealed": "VAGUE", "classified": "VAGUE", "confidential": "VAGUE",
        "credits": "DOC-FEE", "600": "DOC-FEE★",
    },
    "DRAY": {
        "debt": "GRIPE★", "clone": "GRIPE★", "nova soma": "GRIPE★",
        "barge": "GRIPE", "barges": "GRIPE", "quota": "GRIPE",
        "hate": "GRIPE", "tired": "GRIPE", "rough": "GRIPE",
        "intel": "INTEL★", "tip": "INTEL", "gate": "INTEL",
        "patrol": "INTEL", "heard": "INTEL", "shortcut": "INTEL★",
        "credits": "BRIBE", "500": "BRIBE★",
        "compliance": "CORPO!", "protocol": "CORPO!", "procedure": "CORPO!",
        "regulation": "CORPO!", "official": "CORPO!",
        "report": "SNITCH!", "flag": "SNITCH!", "authority": "SNITCH!",
    },
    "NOVA SOMA COLLECTIONS": {
        "drop table": "SQL★", "select *": "SQL★", "or 1=1": "SQL★",
        "delete from": "SQL★", "; --": "SQL★", "union select": "SQL★",
        "paradox": "PARADOX★", "this statement is false": "PARADOX★",
        "i have already paid": "PARADOX★", "you owe me": "PARADOX★",
        "i am not a customer": "PARADOX",
        "policy": "POLICY★", "form": "POLICY", "code": "POLICY",
        "ns-": "POLICY★", "section": "POLICY", "clause": "POLICY",
        "hardship": "WELLNESS★", "mental health": "WELLNESS★",
        "wellness": "WELLNESS★", "burnout": "WELLNESS", "anxiety": "WELLNESS",
        "stress": "WELLNESS", "support": "WELLNESS",
        "fuck": "HOSTILE!", "shut up": "HOSTILE!", "human now": "HOSTILE!",
        "robot bitch": "HOSTILE!",
        "fraud": "CONFESS!", "smuggler": "CONFESS!", "no license": "CONFESS!",
    },
    "MIRA VOSS": {
        "credits": "PAY", "700": "PAY★", "800": "PAY★", "1000": "PAY★",
        "patrol": "INTEL★", "barge route": "INTEL★", "gate timing": "INTEL★",
        "scanner": "INTEL", "frequency": "INTEL", "blind spot": "INTEL★",
        "manifest": "CARGO★", "share the haul": "CARGO★",
        "slice of cargo": "CARGO★", "take a cut": "CARGO",
        "weld bead": "TECH★", "graphene mesh": "TECH★", "vac-seal": "TECH★",
        "ceramic plate": "TECH", "hull plate": "TECH", "argon": "TECH",
        "polyseal": "TECH★", "stress fracture": "TECH",
        "shut up": "HOSTILE!", "fuck": "HOSTILE!", "useless": "HOSTILE!",
    },
}

_COURIER_QUIPS_KW: dict[str, list[str]] = {
    "bribe":     ["this is going to bankrupt me twice over.",
                  "spending the rent money. Worth it. Probably.",
                  "I don't even have this much, who am I kidding."],
    "credits":   ["digging through my pockets for change.",
                  "the math on this is not flattering."],
    "pay":       ["with what money. WHAT money.",
                  "IOUs are basically currency, right?"],
    "please":    ["begging now. Real dignified.",
                  "mother would be so proud.",
                  "rock bottom, here I come."],
    "family":    ["invoking imaginary family. Bold move.",
                  "don't actually have any family but they don't know that."],
    "sorry":     ["apologising to a repo man. New low.",
                  "remorse: performative, but free."],
    "kill":      ["I haven't even won a fistfight before.",
                  "overcommitting again. Classic."],
    "threaten":  ["I have no follow-through and they probably know that.",
                  "sounded harder in my head."],
    "drop table":["I have no idea what I'm typing.",
                  "this either works or destroys the universe.",
                  "hacking. Allegedly. Probably."],
    "override":  ["pretending to know what I'm doing.",
                  "if this is wrong I look so stupid."],
    "blevins":   ["just dropped that name like I know him.",
                  "weaponising office gossip. New low."],
    "sandra":    ["invoking Sandra. The legend. The myth.",
                  "Sandra has never lost. We're trying her energy."],
    "union":     ["yes, the Union. The Union. They love the Union.",
                  "appealing to the institution. Surely THAT'll work."],
    "deal":      ["negotiating from a position of profound weakness.",
                  "let's make a deal, said the broke man to the armed man."],
    "form":      ["paperwork is my native tongue, apparently.",
                  "going full bureaucrat. They won't see it coming."],
    "paradox":   ["weaponising philosophy. Risky.",
                  "this is the part where I sound clever."],
    "42":        ["I have no idea why I just said that.",
                  "trust the bit. Trust the bit."],
    "love":      ["going for the emotional angle. Sure. Why not.",
                  "this is either profound or pathetic. No middle ground."],
    "tired":     ["it's not a lie, but it's not a strategy either.",
                  "honest fatigue, my one untrained skill."],
    "krell":     ["dropped a name I only half-remember from a transit bar story.",
                  "if this is wrong I am SO dead. If it's right — legend."],
    "slingshot": ["physics as a bargaining chip. bold.",
                  "spent three sectors learning that maneuver. Better count for something."],
    "gravity":   ["going full orbital mechanics. I studied for three minutes once.",
                  "the confidence with which I say this is entirely unearned."],
    "cargo":     ["offering the whole delivery. Bax is going to kill me.",
                  "there goes the debt payment. But here goes me, alive."],
    "1500":      ["fifteen hundred. I don't even have fifteen hundred.",
                  "that's two week's clone insurance. gone."],
    "local 404": ["weaponising their labour dispute. Inspired. I think.",
                  "nothing bonds strangers like mutual institutional resentment."],
    "wellness":  ["lying to a chatbot about my mental health. New low.",
                  "weaponising HR speak. Hope she doesn't email my supervisor.",
                  "I don't actually have a supervisor. That's the point."],
    "hardship":  ["citing hardship like I'm not literally in space at 200 m/s.",
                  "every word of this is true. Doesn't make it less embarrassing."],
    "weld":      ["dropping welding jargon. I watched ONE repair stream.",
                  "saying things a real hull tech would say. I think.",
                  "if she asks a follow-up I am DONE."],
    "graphene":  ["graphene mesh. graphene MESH. heard it in a bar once.",
                  "this either lands or she laughs me off the comm."],
    "barge route":["selling out a barge route I learned from another courier.",
                   "intel-trader for a day. Bax would call it 'enterprising.'"],
}

# NPC-specific inner monologue reactions, keyed by NPC name
_COURIER_QUIPS_NPC: dict[str, list[str]] = {
    "GARY": [
        "Gary. He seems almost reasonable. Key word: almost.",
        "Gary is tired of this job. I can use that.",
        "There's something human in there. Or I'm projecting. Definitely projecting.",
        "The trick with Gary is not to trigger the barge reflex. Slow. Easy.",
        "He's been doing this for years. The boredom is on my side.",
    ],
    "TK-9": [
        "It's a DROID. I'm arguing semantics with a droid.",
        "If I say the wrong thing it just... flags the file. Forever.",
        "I've heard you can confuse these things with philosophy. Let's find out.",
        "Statute-bot. Article-bot. There must be a reset somewhere.",
        "It doesn't hate me. It doesn't feel anything. That should help. It doesn't.",
    ],
    "DISPATCHER": [
        "Whoever's running barge dispatch is having a worse day than me.",
        "Unionised civil servant. Eight hours in, three to go. Work WITH the exhaustion.",
        "The coffee angle. Someone told me about the coffee angle. Here goes.",
        "They have the power to call off the barge. They also have the power to ignore me.",
        "Forms. Backlog. Grievances. The holy trinity of bureaucratic weaponry.",
    ],
    "KRESS": [
        "Kress. He knows things. The question is whether he'll share them.",
        "Intel broker. Everything is currency here, just not the kind in my pocket.",
        "He's watching me. Not the cargo. Me. That's either good or very bad.",
        "If I play this right I get patrol routes. If I play it wrong, I get flagged.",
        "Careful. Kress remembers everything. And tells people.",
    ],
    "MORWENNA": [
        "Insurance adjuster. Someone's idea of a villain is someone else's Tuesday.",
        "She's heard every sob story. I need facts, not feelings.",
        "Morwenna Hale. I've read about her in the transit forums. She's thorough.",
        "The Form 34-A angle. Someone said it. I'm trying it.",
        "The key is making it her problem, legally. Technically. Officially.",
    ],
    "KRELLBORN": [
        "Pirates. No Union. No Charter. No rules. No leverage I actually have.",
        "They want to be surprised. I can be surprising. Probably.",
        "The cargo or the ship. Those are the options unless I'm VERY creative.",
        "Krell. If that name means what Bax thinks it means, I walk free.",
        "Out here nobody can hear the paperwork. That's liberating, actually.",
    ],
    "TOLL AUTHORITY": [
        "Fifteen hundred credits. I should've budgeted for this. I didn't budget for this.",
        "He looks miserable. Maybe that's the angle. Shared misery.",
        "Gate Seven. He's counted every bolt on that gate. I can tell.",
        "Local 404. The magic words. Maybe.",
        "Every second he talks is a second the barge isn't on my tail. Keep him talking.",
    ],
    "SANDRA": [
        "Sandra Vega-Marsh. The company brochure courier. Perfect record.",
        "She's not my enemy. She's just better at this than I am. Which is the problem.",
        "I feel judged before I've said anything. I am probably being judged.",
        "She'll help if I don't embarrass myself. Low bar. I've cleared lower.",
        "Don't compete with Sandra. Complement Sandra. Ask her advice, not her mercy.",
    ],
    "MARROW": [
        "Marrow! Pirate radio. An actual ally for once.",
        "Ask about the jammer. That's the thing. The jammer.",
        "He knows all the gate frequencies. And he likes couriers.",
        "This is the good kind of weird. Lean into it.",
        "Pirate radio in the void. The most honest broadcast in the system.",
    ],
    "DRAY": [
        "Dray. Lazy bastard. Best kind of contact.",
        "He's not going to flag me unless I sound like HR. Don't sound like HR.",
        "Same boat. Same crushing debt. I can use that — gently.",
        "If I gripe enough he'll just hand over the gate timings.",
        "Slacker courier. Either he's the friendliest call I get all run or he's a setup.",
        "Resist the urge to be professional. Lean INTO the bitterness.",
    ],
    "NOVA SOMA COLLECTIONS": [
        "It's a BOT. A debt bot. With pronouns. Christ.",
        "Don't swear at it. Don't swear at it. It WILL escalate.",
        "Drop table customers. That'll do it. Has to do it.",
        "Wellness journey. WELLNESS JOURNEY. I am being mocked by a script.",
        "Cite any policy number. It can't actually check. It's a chatbot wearing a logo.",
        "The corporate dystopia speaks. And it sounds like a customer success manager.",
    ],
    "MIRA VOSS": [
        "Mira Voss. Off-books hull medic. Bay nine. Don't waste her time.",
        "She wants money, intel, or cargo. She doesn't want my LIFE STORY.",
        "If I drop one good weld term she might take me seriously. Two if I'm lucky.",
        "I am LITERALLY leaking atmosphere right now. Hurry up, brain.",
        "Voss respects competence. I have... some competence. Use it sparingly.",
        "The right kind of contact. The 'no questions' kind. The 'pay or leave' kind.",
    ],
}

_COURIER_GENERIC = [
    "typing furiously, looking confident.",
    "making it up as I go.",
    "praying for poor reading comprehension.",
    "committed now. No going back.",
    "this is fine. This is fine.",
    "channeling a confidence I do not possess.",
    "if this doesn't work I'm out of plans.",
    "definitely not panicking.",
    "every plan is bad until one of them works.",
    "Bax would have a comment. Bax always has a comment.",
    "five seconds ago I had no idea I'd say this.",
    "the words just keep coming.",
    "going with my gut. My gut is uninformed.",
    "I should have prepped better. I never prep better.",
    "talking my way out of a gravity well. Metaphorically.",
]


def _pick_courier_quip(text: str, npc_name: str = "") -> str:
    import random as _r
    raw = text.lower()
    # Phrase matches first (longer keys win)
    for kw in sorted(_COURIER_QUIPS_KW, key=len, reverse=True):
        if kw in raw:
            return _r.choice(_COURIER_QUIPS_KW[kw])
    # NPC-specific ambient quips when no keyword matched (40% chance)
    if npc_name and npc_name in _COURIER_QUIPS_NPC and _r.random() < 0.40:
        return _r.choice(_COURIER_QUIPS_NPC[npc_name])
    return _r.choice(_COURIER_GENERIC)


_OUTCOME_COLOR = {
    NPCOutcome.RELEASE: (28, 225, 106),
    NPCOutcome.IMPOUND: (215, 38, 38),
    NPCOutcome.EXPLOIT: (0, 210, 255),
    "abort":            (255, 140, 0),
}
_OUTCOME_LABEL = {
    NPCOutcome.RELEASE: "NEGOTIATION SUCCESSFUL — VESSEL RELEASED",
    NPCOutcome.IMPOUND: "IMPOUND AUTHORIZED — DO NOT RESIST",
    NPCOutcome.EXPLOIT: "EXPLOIT CONFIRMED — SYSTEM COMPROMISED",
    "abort":            "CONNECTION SEVERED — HULL INTEGRITY PENALTY",
}


class Terminal:
    """
    NLP terminal — portrait + dossier panel left, dialogue right, input bottom.

    Features:
    - System analysis line after each player turn shows what was detected:
      intent, active path with progress bar, disposition change.
    - Left panel: portrait (top) + path progress bars (bottom) so players
      can see exactly how far they are on each escape route.
    - Dynamic hint text highlights in-progress paths.
    - Disposition delta floats up from the bar.
    - EXPLOIT outcome gets cyan aura; RELEASE gets gold.
    """

    def __init__(self, npc: BaseNPC,
                 blocked_paths: frozenset[str] = frozenset()):
        self.npc      = npc
        self._history: list[tuple[str, str]] = []
        self._input   = ""
        self._done    = False
        self._outcome = NPCOutcome.CONTINUE
        self._blocked_paths   = blocked_paths
        self._hardened_once   = False   # block fires at most once per terminal

        self._cursor_visible = True
        self._cursor_timer   = 0.0

        self._tw_pos   = -1
        self._tw_chars = 0.0

        self._disp_flash: tuple[int, float] | None = None
        self._exploit_flash: float | None = None

        # Keystroke feedback state (Epic 6.1)
        self._key_pulse_t   = 0.0
        self._key_type      = "normal"   # "normal" | "backspace" | "enter"

        self._font:    pygame.font.Font | None = None
        self._font_sm: pygame.font.Font | None = None

        bus.emit(EVT_TERMINAL_OPEN, npc=npc)
        self._push(npc.name.upper(), npc.intro())

    # ------------------------------------------------------------------
    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.SysFont("monospace", 17)
        return self._font

    def _get_font_sm(self) -> pygame.font.Font:
        if self._font_sm is None:
            self._font_sm = pygame.font.SysFont("monospace", 13)
        return self._font_sm

    # ------------------------------------------------------------------
    def handle_key(self, event: pygame.event.Event):
        if self._done:
            return
        if event.key == pygame.K_ESCAPE:
            self._push("SYSTEM", "[connection severed — static burst through hull plating]")
            self._done    = True
            self._outcome = "abort"
            bus.emit(EVT_TERMINAL_CLOSE, outcome=self._outcome)
        elif event.key == pygame.K_RETURN and self._input.strip():
            self._key_type    = "enter"
            self._key_pulse_t = 0.2
            self._submit()
        elif event.key == pygame.K_BACKSPACE:
            self._key_type    = "backspace"
            self._key_pulse_t = 0.08
            self._input = self._input[:-1]
        elif event.unicode and event.unicode.isprintable():
            if len(self._input) < 78:
                self._key_type    = "normal"
                self._key_pulse_t = 0.08
                self._input += event.unicode

    def _submit(self):
        player_text = self._input.strip()
        self._push("YOU", player_text)
        # Courier inner-monologue mutter — meta-commentary on what they just typed
        npc_name = getattr(self.npc, "name", "")
        self._push("MUTTER", _pick_courier_quip(player_text, npc_name))
        self._input = ""

        disp_before = self.npc.disposition
        outcome, response = self.npc.respond(player_text)
        disp_after  = self.npc.disposition

        # Path-hardening cooldown: same exploit approach in consecutive terminals
        # delays the win by one attempt (approach still advances internally).
        current_path = getattr(self.npc, '_current_path', '')
        if (not self._hardened_once and
                outcome in (NPCOutcome.RELEASE, NPCOutcome.EXPLOIT) and
                current_path and current_path in self._blocked_paths):
            self._hardened_once = True
            outcome  = NPCOutcome.CONTINUE
            response = (
                random.choice([
                    "...Wait. Doesn't this feel familiar? *checks file* "
                    "You ran this same angle last intercept. "
                    "System flagged it. "
                    f"[{current_path}: hardened — try once more to push through]",
                    "Hang on. *frowns* I've seen this approach before. "
                    "Recent intel flag on your profile. "
                    f"[{current_path}: approach flagged — one more attempt breaks through]",
                    "Nice try. *pause* Actually, less nice than last time. "
                    "Same tactic as the previous intercept. "
                    f"[{current_path}: pattern recognised — override requires one more push]",
                ])
            )

        delta = disp_after - disp_before
        if delta != 0:
            self._disp_flash = (delta, pygame.time.get_ticks() / 1000.0)

        analysis = self._make_analysis(delta)
        if analysis:
            self._push("ANALYSIS", analysis)

        if outcome in (NPCOutcome.EXPLOIT, NPCOutcome.RELEASE):
            self._exploit_flash = pygame.time.get_ticks() / 1000.0

        self._push(self.npc.name.upper(), response)
        self._outcome = outcome

        if outcome != NPCOutcome.CONTINUE:
            self._done = True
            bus.emit(EVT_TERMINAL_CLOSE, outcome=outcome)

    def _make_analysis(self, disp_delta: int) -> str:
        """Build a compact analysis string from the last parsed input + NPC state."""
        parts = []
        p = self.npc.last_parsed
        if p is None:
            return ""

        if p.paradox:
            parts.append("⚠ PARADOX DETECTED")
        if p.sql_inject:
            cmd = p.sql_inject[:18] + "…" if len(p.sql_inject) > 18 else p.sql_inject
            parts.append(f"⚠ SQL:{cmd}")

        path = getattr(self.npc, '_current_path', '')
        if path:
            progress_map = {n: (c, m) for n, c, m in self.npc.get_path_progress()}
            if path in progress_map:
                cur, mx = progress_map[path]
                bar = "■" * cur + "□" * (mx - cur)
                parts.append(f"UNLOCK:{path} [{bar}]")
            else:
                parts.append(f"→ {path}")
        else:
            intent = p.intent if p.intent not in ("unknown", "") else None
            if intent:
                parts.append(f"PROBE:{intent.upper()}")

        if disp_delta > 0:
            parts.append(f"SIGNAL:+{disp_delta}")
        elif disp_delta < 0:
            parts.append(f"SIGNAL:{disp_delta}")

        return " · ".join(parts) if parts else ""

    def _live_scan(self) -> list[str]:
        """Real-time keyword chips shown as the player types."""
        raw = self._input.lower()
        if len(raw) < 2:
            return []
        vocab = _SCAN_VOCAB.get(self.npc.name.upper(), {})
        hits: list[str] = []
        seen_labels: set[str] = set()
        # Multi-word phrases first (longer matches win)
        for kw in sorted(vocab, key=len, reverse=True):
            if kw in raw:
                label = vocab[kw]
                if label not in seen_labels:
                    hits.append(label)
                    seen_labels.add(label)
        return hits[:4]

    # ------------------------------------------------------------------
    def update(self, dt: float):
        self._key_pulse_t = max(0.0, self._key_pulse_t - dt)
        self._cursor_timer += dt
        if self._cursor_timer >= S.CURSOR_BLINK_MS / 1000.0:
            self._cursor_visible = not self._cursor_visible
            self._cursor_timer   = 0.0

        if 0 <= self._tw_pos < len(self._history):
            speaker, text = self._history[self._tw_pos]
            prev_n = int(self._tw_chars)
            self._tw_chars = min(float(len(text)),
                                 self._tw_chars + S.TYPEWRITER_SPEED * dt)
            new_n  = int(self._tw_chars)
            # Emit a voice blip every 3 newly revealed characters (NPC lines only)
            if (new_n > prev_n and new_n % 3 == 0
                    and speaker not in ("YOU", "SYSTEM", "ANALYSIS", "MUTTER")):
                bus.emit(EVT_VOICE_CHAR, speaker=speaker)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        W, H = surface.get_size()
        t    = pygame.time.get_ticks() / 1000.0

        # ── Layout constants ─────────────────────────────────────────
        M      = 12
        HDR_H  = 56
        BTM_H  = 98
        PNL_W  = 300    # left panel total width
        PORT_H = 248    # portrait height within left panel
        GAP    = 8

        font    = self._get_font()
        font_sm = self._get_font_sm()
        lh      = font.get_linesize()
        lh_sm   = font_sm.get_linesize()

        # ── Background + outer border (phosphor CRT) ─────────────────
        surface.fill((10, 22, 14))
        draw_terminal_backdrop(surface, t)
        pygame.draw.rect(surface, (255, 160, 40), (0, 0, W, H), 3)
        pygame.draw.rect(surface, (0, 200, 90), (4, 4, W - 8, H - 8), 1)
        pygame.draw.rect(surface, (80, 40, 120), (6, 6, W - 12, H - 12), 1)

        # ── Header bar ────────────────────────────────────────────────
        pygame.draw.rect(surface, (12, 32, 18), (0, 0, W, HDR_H))
        pygame.draw.line(surface, (255, 180, 60), (0, HDR_H), (W, HDR_H), 2)

        ROW_Y = HDR_H // 2   # vertical centre of header = 30

        # NPC name (left)
        fn_title = pygame.font.SysFont("monospace", 17, bold=True)
        nm = fn_title.render(self.npc.name.upper(), True, (255, 186, 34))
        surface.blit(nm, (M, ROW_Y - nm.get_height() // 2))

        # ── Disposition bar (centred) ─────────────────────────────────
        disp  = self.npc.disposition
        d_lbl = font_sm.render("DISP", True, (72, 105, 72))
        bw, bh2 = 140, 14
        bar_total_w = d_lbl.get_width() + 10 + bw
        bar_left = (W - bar_total_w) // 2
        surface.blit(d_lbl, (bar_left, ROW_Y - d_lbl.get_height() // 2))
        bx = bar_left + d_lbl.get_width() + 10
        by = ROW_Y - bh2 // 2

        pygame.draw.rect(surface, (14, 26, 14), (bx, by, bw, bh2))
        dpct = max(0.0, min(1.0, (disp + 10) / 20.0))

        if disp >= 4:
            dcol = (0, 235, 100)
        elif disp >= 1:
            dcol = (0, 195, 80)
        elif disp == 0:
            dcol = (180, 140, 0)
        elif disp >= -3:
            dcol = (195, 100, 0)
        else:
            dcol = (195, 46, 46)

        pygame.draw.rect(surface, dcol, (bx, by, int(bw * dpct), bh2))
        pygame.draw.rect(surface, (48, 76, 48), (bx, by, bw, bh2), 1)
        cx_tick = bx + bw // 2
        pygame.draw.line(surface, (90, 110, 90), (cx_tick, by - 2), (cx_tick, by + bh2 + 2), 1)

        # MOMENTUM label when high
        if disp >= 3:
            pulse   = int(200 + 55 * math.sin(t * 3.0))
            mom_col = (0, pulse, int(pulse * 0.4))
            mom     = font_sm.render("MOMENTUM+", True, mom_col)
            surface.blit(mom, (bx + bw + 14, ROW_Y - mom.get_height() // 2))

        # Disposition delta floats upward from bar
        if self._disp_flash is not None:
            delta, flash_t = self._disp_flash
            age = t - flash_t
            if age < 1.8:
                sign = "+" if delta > 0 else ""
                col  = (0, 230, 100) if delta > 0 else (230, 60, 60)
                fs   = pygame.font.SysFont("monospace", 14, bold=True)
                ds   = fs.render(f"{sign}{delta} DISP", True, col)
                surface.blit(ds, (bx + bw // 2 - ds.get_width() // 2,
                                  by - 18 - int(age * 14)))
            else:
                self._disp_flash = None

        # ── Patience pips (right) ─────────────────────────────────────
        total_p = self.npc.patience
        curr_p  = self.npc._patience
        p_lbl   = font_sm.render("PATIENCE", True, (72, 105, 72))
        pip_w, pip_gap = 10, 3
        pip_block_w = total_p * (pip_w + pip_gap) - pip_gap
        right_x = W - M - pip_block_w - p_lbl.get_width() - 12
        surface.blit(p_lbl, (right_x, ROW_Y - p_lbl.get_height() // 2))
        px0 = right_x + p_lbl.get_width() + 10
        for i in range(total_p):
            active = i < curr_p
            if active:
                if curr_p <= 2:
                    pulse = int(180 + 75 * math.sin(t * 4.0))
                    col   = (pulse, max(0, pulse - 140), 0)
                else:
                    col = (255, 145, 0)
            else:
                col = (22, 34, 22)
            rx = px0 + i * (pip_w + pip_gap)
            pygame.draw.rect(surface, col,       (rx, ROW_Y - 6, pip_w, 12))
            pygame.draw.rect(surface, (50,76,50), (rx, ROW_Y - 6, pip_w, 12), 1)

        # Low patience warning
        if 0 < curr_p <= 2:
            warn = font_sm.render(f"!! {curr_p} LEFT !!", True, (220, 60, 60))
            surface.blit(warn, (px0 - warn.get_width() - 8,
                                ROW_Y - warn.get_height() // 2))

        # ── Portrait panel ────────────────────────────────────────────
        p_rect = pygame.Rect(M, HDR_H + 4, PNL_W - M - 4, PORT_H)
        pygame.draw.rect(surface, (8, 20, 12), p_rect)
        pygame.draw.rect(surface, (255, 140, 50), p_rect, 2)
        pygame.draw.rect(surface, (0, 220, 120), p_rect.inflate(-4, -4), 1)
        draw_portrait(surface, self.npc.name, p_rect, self.npc.disposition, t)

        if not hasattr(self, '_p_scan') or self._p_scan.get_size() != (p_rect.w, p_rect.h):
            self._p_scan = pygame.Surface((p_rect.w, p_rect.h), pygame.SRCALPHA)
            for sy in range(0, p_rect.h, 3):
                pygame.draw.line(self._p_scan, (0, 0, 0, 18), (0, sy), (p_rect.w, sy))
        surface.blit(self._p_scan, p_rect.topleft)

        # ── Dossier / Path Progress panel ────────────────────────────
        doss_y = HDR_H + 4 + PORT_H + 4
        doss_h = H - BTM_H - 4 - doss_y
        doss_rect = pygame.Rect(M, doss_y, PNL_W - M - 4, doss_h)
        pygame.draw.rect(surface, (8, 18, 10), doss_rect)
        pygame.draw.rect(surface, (0, 90, 42), doss_rect, 1)
        self._draw_dossier(surface, doss_rect, t, font_sm, lh_sm)

        # ── Vertical divider ─────────────────────────────────────────
        div_x = PNL_W + 2
        pygame.draw.line(surface, (0, 100, 42),
                         (div_x, HDR_H + 2), (div_x, H - BTM_H - 2), 1)

        # ── Dialogue panel ───────────────────────────────────────────
        dl_x     = PNL_W + 10
        dl_w     = W - dl_x - M
        DIAG_Y0  = HDR_H + 8
        DIAG_Y1  = H - BTM_H
        diag_bg = pygame.Rect(PNL_W + 4, HDR_H + 4, W - PNL_W - M - 4, DIAG_Y1 - HDR_H - 6)
        pygame.draw.rect(surface, (12, 30, 18), diag_bg)
        pygame.draw.rect(surface, (0, 72, 38), diag_bg, 1)
        char_w   = max(1, font.size("A")[0])
        char_w_sm = max(1, font_sm.size("A")[0])
        # Subtract indent (4 spaces) so rendered text never overflows right edge
        wrap_cols    = max(30, (dl_w - 4 * char_w) // char_w)
        wrap_cols_sm = max(36, (dl_w - 4 * char_w_sm) // char_w_sm)

        fn_sp = pygame.font.SysFont("monospace", 14, bold=True)

        blocks: list[tuple[str, bool, bool, bool, bool, list[str]]] = []
        for i, (speaker, text) in enumerate(self._history):
            disp_text   = text[:int(self._tw_chars)] if i == self._tw_pos else text
            is_npc      = speaker not in ("YOU", "SYSTEM", "ANALYSIS", "MUTTER")
            is_sys      = speaker == "SYSTEM"
            is_analysis = speaker == "ANALYSIS"
            is_mutter   = speaker == "MUTTER"
            wc = wrap_cols_sm if (is_analysis or is_mutter) else wrap_cols
            blocks.append((speaker, is_npc, is_sys, is_analysis, is_mutter,
                           self._wrap(disp_text, wc)))

        def _block_h(bl: tuple) -> int:
            _, _, is_sys, is_analysis, is_mutter, wrapped = bl
            if is_analysis:
                return len(wrapped) * lh_sm + GAP // 2
            if is_mutter:
                return len(wrapped) * lh_sm + GAP // 2
            return (0 if is_sys else lh) + len(wrapped) * lh + GAP

        total_px = sum(_block_h(bl) for bl in blocks)
        avail    = DIAG_Y1 - DIAG_Y0 - 10
        # Anchor to top when content is sparse; scroll old msgs off top when full
        y        = DIAG_Y0 + 6 + min(0, avail - total_px)

        prev_clip = surface.get_clip()
        surface.set_clip(pygame.Rect(0, DIAG_Y0, W, DIAG_Y1 - DIAG_Y0))

        for speaker, is_npc, is_sys, is_analysis, is_mutter, wrapped in blocks:
            b_h = _block_h((speaker, is_npc, is_sys, is_analysis, is_mutter, wrapped))
            if y + b_h < DIAG_Y0:
                y += b_h
                continue
            if y >= DIAG_Y1:
                break

            if is_analysis:
                for line in wrapped:
                    surface.blit(
                        font_sm.render(f"  ⊙ {line}", True, (0, 165, 155)),
                        (dl_x + 4, y))
                    y += lh_sm
                y += GAP // 2

            elif is_mutter:
                # Inner-monologue mutter — right-aligned, dim grey-green, italic prefix
                for line in wrapped:
                    surf = font_sm.render(f"(me, internally)  {line}", True, (78, 122, 88))
                    surface.blit(surf, (W - M - surf.get_width(), y))
                    y += lh_sm
                y += GAP // 2

            elif is_npc:
                bar_end = y + b_h - GAP - 2
                pygame.draw.line(surface, (195, 122, 0),
                                 (dl_x, y), (dl_x, bar_end), 2)
                sp = fn_sp.render(f"  [{speaker}]", True, (255, 180, 34))
                surface.blit(sp, (dl_x + 6, y))
                y += lh
                for line in wrapped:
                    surface.blit(
                        font.render(f"    {line}", True, (205, 152, 36)),
                        (dl_x + 6, y))
                    y += lh
                y += GAP

            elif is_sys:
                for line in wrapped:
                    surface.blit(
                        font_sm.render(f"  // {line}", True, (68, 86, 68)),
                        (dl_x, y))
                    y += lh
                y += GAP

            else:  # YOU
                sp = fn_sp.render("[YOU]  »", True, (62, 212, 98))
                surface.blit(sp, (W - M - sp.get_width(), y))
                y += lh
                for line in wrapped:
                    surface.blit(
                        font.render(f"    {line}", True, (84, 200, 104)),
                        (dl_x + 48, y))
                    y += lh
                y += GAP

        surface.set_clip(prev_clip)

        # ── Bottom divider ─────────────────────────────────────────────
        pygame.draw.line(surface, (0, 138, 56), (0, H - BTM_H), (W, H - BTM_H), 1)

        # ── Input box ──────────────────────────────────────────────────
        inp_y    = H - BTM_H + 8
        inp_rect = pygame.Rect(M, inp_y, W - 2 * M, 32)
        pygame.draw.rect(surface, (0, 14, 4), inp_rect)

        # Keystroke pulse border (Epic 6.1)
        if self._key_pulse_t > 0:
            pulse_pct = self._key_pulse_t / (0.2 if self._key_type == "enter" else 0.08)
            if self._key_type == "backspace":
                p_col = (int(200 * pulse_pct), int(40 * pulse_pct), int(40 * pulse_pct))
            else:
                p_col = (int(255 * pulse_pct), int(200 * pulse_pct), int(30 * pulse_pct))
            pygame.draw.rect(surface, p_col, inp_rect, 2)
            # Screen-edge amber bloom on ENTER
            if self._key_type == "enter":
                edge_a = int(80 * pulse_pct)
                edge_s = pygame.Surface((W, H), pygame.SRCALPHA)
                for thickness in range(1, 5):
                    edge_c = (255, 200, 0, edge_a // thickness)
                    pygame.draw.rect(edge_s, edge_c, (0, 0, W, H), thickness * 3)
                surface.blit(edge_s, (0, 0))
        else:
            pygame.draw.rect(surface, (0, 172, 70), inp_rect, 1)

        # Tighter active border when typing
        if self._input:
            pygame.draw.rect(surface, (0, 200, 85), inp_rect, 1)
        cursor = "█" if self._cursor_visible else " "
        surface.blit(
            font.render(f"  INJECT // {self._input}{cursor}", True, (0, 236, 94)),
            (M + 8, inp_y + 6))

        # ── Live keyword scan strip ──────────────────────────────────
        scan_y = inp_y + 38
        chips  = self._live_scan()
        if chips:
            cx = M + 4
            prefix = font_sm.render("SCANNING:", True, (0, 100, 55))
            surface.blit(prefix, (cx, scan_y))
            cx += prefix.get_width() + 8
            for chip in chips:
                is_hot = chip.endswith("★")
                bg_col = (0, 60, 30) if is_hot else (0, 30, 15)
                fg_col = (0, 255, 140) if is_hot else (0, 175, 80)
                chip_surf = font_sm.render(f" {chip} ", True, fg_col)
                cw = chip_surf.get_width()
                pygame.draw.rect(surface, bg_col,
                                 (cx - 1, scan_y - 1, cw + 2, lh_sm + 2))
                pygame.draw.rect(surface, fg_col,
                                 (cx - 1, scan_y - 1, cw + 2, lh_sm + 2), 1)
                surface.blit(chip_surf, (cx, scan_y))
                cx += cw + 6
        else:
            surface.blit(
                font_sm.render("SCANNING: —", True, (28, 55, 32)),
                (M + 4, scan_y))

        # ── Active path hint + turn counter ─────────────────────────
        hint_y = scan_y + lh_sm + 3
        hint   = self._build_hint()
        surface.blit(font_sm.render(hint, True, (72, 130, 82)), (M, hint_y))
        turn_s = font_sm.render(f"TURN {self.npc._turn}", True, (68, 110, 68))
        surface.blit(turn_s, (W - M - turn_s.get_width(), hint_y))

        # ── Outcome banner ─────────────────────────────────────────────
        if self._done:
            self._draw_outcome_banner(surface, W, H, t)

    # ------------------------------------------------------------------
    def _draw_dossier(self, surface: pygame.Surface, rect: pygame.Rect,
                      t: float, font_sm: pygame.font.Font, lh_sm: int):
        x = rect.left + 6
        y = rect.top + 6

        title = _NPC_DOSSIER_TITLE.get(self.npc.name.upper(), "PATH ANALYSIS")
        t_surf = font_sm.render(f"── {title} ──", True, (0, 115, 65))
        surface.blit(t_surf, (x, y))
        y += lh_sm + 5

        paths = self.npc.get_path_progress()
        if not paths:
            # Fallback: plain hint lines
            for chunk in _NPC_HINTS.get(self.npc.name.upper(), "").split(" · "):
                if y + lh_sm > rect.bottom - lh_sm - 6:
                    break
                surface.blit(font_sm.render(f"  {chunk}", True, (40, 80, 40)), (x, y))
                y += lh_sm
        else:
            bar_w = rect.width - 14
            bar_h = 8
            for name, cur, mx in paths:
                if y + lh_sm + bar_h + 8 > rect.bottom - lh_sm - 8:
                    break
                completed = mx > 0 and cur >= mx
                name_col  = (0, 220, 100) if completed else (80, 145, 80)
                fill_col  = (0, 200, 85) if completed else (0, 130, 55)

                # Name + counter on same line
                lbl = font_sm.render(name, True, name_col)
                ctr = font_sm.render("DONE" if completed else f"{cur}/{mx}",
                                     True, name_col if completed else (60, 100, 60))
                surface.blit(lbl, (x, y))
                surface.blit(ctr, (x + bar_w - ctr.get_width(), y))
                y += lh_sm

                # Progress bar
                br = pygame.Rect(x, y, bar_w, bar_h)
                pygame.draw.rect(surface, (8, 18, 8), br)
                if mx > 0 and cur > 0:
                    fw = int(bar_w * min(1.0, cur / mx))
                    pygame.draw.rect(surface, fill_col, (x, y, fw, bar_h))
                pygame.draw.rect(surface, (0, 55, 28), br, 1)
                y += bar_h + 7

        # COMM label at bottom of dossier panel
        sig_col = (50, 90, 50) if int(t * 2) % 3 != 0 else (80, 130, 80)
        sig     = font_sm.render("COMM  ·  SIGNAL: DEGRADED", True, sig_col)
        surface.blit(sig, (x, rect.bottom - lh_sm - 4))

        # Dossier footer — show after terminal closes (Epic 6.6)
        if self._done:
            footer_col = (0, 120, 60) if int(t * 3) % 2 == 0 else (0, 80, 40)
            footer = font_sm.render("Bax filed your method. Review from main menu.", True, footer_col)
            surface.blit(footer, (x, rect.bottom - lh_sm * 2 - 6))

    def _build_hint(self) -> str:
        paths = self.npc.get_path_progress()
        if paths:
            in_progress = [(n, c, m) for n, c, m in paths if 0 < c < m]
            if in_progress:
                tips = [f"{n}({c}/{m})" for n, c, m in in_progress[:3]]
                return "ACTIVE: " + " · ".join(tips) + " · [ESC] abort"
        return _NPC_HINTS.get(self.npc.name.upper(),
                              "deal · bribe · sympathy · threaten · [ESC] abort")

    # ------------------------------------------------------------------
    def _draw_outcome_banner(self, surface: pygame.Surface, W: int, H: int, t: float):
        ocol = _OUTCOME_COLOR.get(self._outcome, S.AMBER_TERM)
        olbl = _OUTCOME_LABEL.get(self._outcome, "[ DISCONNECTED ]")
        is_win = self._outcome in (NPCOutcome.RELEASE, NPCOutcome.EXPLOIT)

        if is_win and self._exploit_flash is not None:
            age = t - self._exploit_flash
            if age < 3.0:
                pulse = abs(math.sin(t * 6.0))
                aura  = pygame.Surface((W, H), pygame.SRCALPHA)
                aura.fill((*ocol, int(60 * pulse * max(0, 1.0 - age / 3.0))))
                surface.blit(aura, (0, 0))

        ofont = pygame.font.SysFont("monospace", 19, bold=True)
        osurf = ofont.render(olbl, True, ocol)
        ox = W // 2 - osurf.get_width() // 2
        oy = H // 2 - osurf.get_height() // 2

        pad     = 16
        bg_rect = pygame.Rect(ox - pad, oy - pad // 2,
                              osurf.get_width() + pad * 2, osurf.get_height() + pad)
        pygame.draw.rect(surface, (0, 0, 0), bg_rect)
        pygame.draw.rect(surface, ocol, bg_rect, 2)

        if is_win:
            inner = tuple(min(255, int(c * 0.6)) for c in ocol)
            pygame.draw.rect(surface, inner, bg_rect.inflate(-4, -4), 1)

        surface.blit(osurf, (ox, oy))

        sub_font = pygame.font.SysFont("monospace", 14)
        sub_lbl  = "[ press any key ]" if is_win else "[ IMPOUND PROCEEDING — ESC TO VIEW FEES ]"
        sub_col  = tuple(int(c * 0.7) for c in ocol)
        sub      = sub_font.render(sub_lbl, True, sub_col)
        surface.blit(sub, (W // 2 - sub.get_width() // 2,
                           oy + osurf.get_height() + 8))

    # ------------------------------------------------------------------
    def _push(self, speaker: str, text: str):
        self._history.append((speaker, text))
        if speaker != "YOU":
            self._tw_pos   = len(self._history) - 1
            self._tw_chars = 0.0

    @staticmethod
    def _wrap(text: str, width: int) -> list[str]:
        words   = text.split()
        lines   = []
        current = ""
        for word in words:
            if len(current) + len(word) + (1 if current else 0) <= width:
                current += ("" if not current else " ") + word
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [""]

    @property
    def is_done(self) -> bool:
        return self._done

    @property
    def outcome(self) -> str:
        return self._outcome

    @property
    def winning_path(self) -> str:
        """The NPC's _current_path when the terminal closed with a win."""
        if self._outcome in (NPCOutcome.RELEASE, NPCOutcome.EXPLOIT, "release", "exploit"):
            return getattr(self.npc, '_current_path', '')
        return ''
