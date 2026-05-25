"""
Idealist Union Rep — Local 404 true believer.

Counterpoint to Gary's bureaucratic cynicism. Quotes the Union charter
unironically. Genuinely thinks Nova Soma is a force for good. Earnest,
which makes him more annoying to negotiate with than Gary is.

Win paths:

  CHARTER       — Quote a Union charter clause back at him
                   ("article 7", "section 4.2", "shared prosperity").
                   He has to honour the citation or violate his own
                   ideology. Two charter hits → release.

  IDEAL_BREAK   — Ask him to reconcile a clear contradiction
                   (e.g. clone debt with shared prosperity, repo with
                   solidarity). Three reconciliations make him quietly
                   release the ship while he goes "to file a grievance."

  BRIBE         — Direct bribe attempts INSULT him. Three insults in
                   a row impound the ship — he literally cannot be
                   bought. Hostile path, listed for completeness.

  SYMPATHY      — Family / desperation appeals don't work. He believes
                   the system will catch them too. Disposition stays flat.

  PARADOX       — Standard paradox triggers fail; he just shakes his
                   head and quotes Article 1 ("the Union is the worker").

Plus the universal `fuck off` easter egg released across all NPCs.
"""
from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT


class IdealistRep(BaseNPC):
    """Idealist Union Rep — name: Edmund 'Eddie' Marlowe."""

    _CHARTER_KEYWORDS = [
        "article 7", "section 4", "section 4.2", "shared prosperity",
        "solidarity", "charter", "preamble", "fair share", "collective",
        "workers united", "ratified", "bylaw", "clause 12", "clause 7",
    ]
    _CONTRADICTION_KEYWORDS = [
        "contradiction", "hypocrisy", "but you", "you said", "doesn't match",
        "how can you", "explain that", "reconcile", "square that",
        "doesn't square", "self-contradict", "ideology", "double standard",
    ]
    _BRIBE_KEYWORDS = [
        "bribe", "pay you", "credits", "money", "cash", "buy off",
        "compensate", "slip", "take this", "kickback",
    ]
    _SYMPATHY_KEYWORDS = [
        "desperate", "please", "family", "kids", "children", "wife",
        "husband", "starving", "broke", "dying", "begging", "help me",
    ]
    def __init__(self, intercepted: bool = False,
                 run_context: dict | None = None):
        super().__init__("Edmund", patience=8)
        self._intercepted        = intercepted
        self._charter_hits       = 0
        self._contradiction_hits = 0
        self._insult_streak      = 0
        self._ctx                = run_context or {}

    def _intro_line(self) -> str:
        if self._intercepted:
            return random.choice([
                "Edmund Marlowe, Local 404, route stewardship division. "
                "Greetings! I'm intercepting under Article 7 of the Charter, "
                "which protects both your interests and ours. "
                "Power down, please. We'll talk this through.",
                "Hello, comrade. Edmund Marlowe, intercept officer. "
                "I want to start by saying I respect your autonomy. "
                "Now, regarding your outstanding fees — let's resolve "
                "this together, in the spirit of shared prosperity.",
                "Local 404 intercept. Edmund Marlowe speaking. "
                "I trust you're as eager as I am to settle this peacefully. "
                "The Charter exists for both of us. Power down.",
            ])
        return random.choice([
            "Greetings! Edmund Marlowe, Local 404. "
            "I'm reaching out today not as an antagonist but as a fellow "
            "stakeholder in the Charter's mission. Power down, please.",
            "Edmund Marlowe, Union Local 404. "
            "Did you know the Charter's preamble actually MENTIONS couriers? "
            "Section 1.4. We're partners, in a way. Power down.",
            "Hello! Edmund Marlowe here. "
            "I always like to begin with a moment of mutual recognition. "
            "We're both workers, you and I. Now let's discuss your fees.",
        ])

    def exploits(self) -> dict[str, str]:
        return {
            "charter":      "Cite Union charter clauses by number",
            "contradiction": "Force him to reconcile his ideology",
            "filibuster":   "Out-quote him on solidarity",
        }

    def _universal_escape_line(self) -> str:
        return (
            "Well. That was unkind. The Charter doesn't mandate "
            "civility but it does *recommend* it. I'll mark this "
            "encounter 'verbally hostile, contact terminated by "
            "complainant.' Go on. Reflect on this. *channel closes*"
        )

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        # CHARTER PATH — citing clauses he has to honour.
        if any(w in raw for w in self._CHARTER_KEYWORDS):
            self._charter_hits += 1
            self._current_path  = "CHARTER"
            self.disposition   += 2
            if self._charter_hits >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="charter")
                return NPCOutcome.RELEASE, random.choice([
                    "Oh — oh, that's a *fair* citation. "
                    "Section 4.2 on courier exemption is one of my favourites. "
                    "I can't in good conscience continue this intercept. "
                    "Released, with my respect, comrade.",
                    "*paging through binder* You're entirely correct. "
                    "Article 7 read in conjunction with the preamble does "
                    "exempt this configuration. Apologies for the inconvenience. "
                    "Solidarity!",
                    "I knew this Charter would matter one day! "
                    "You've cited it correctly — I have to honour the spirit. "
                    "Released. Tell your friends Eddie still believes.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "Oh, you've actually READ the Charter. "
                "How refreshing! Most pilots don't engage with the foundational text. "
                "Continue.",
                "A Charter citation! Wonderful. "
                "I'd love to hear another — do you have one?",
                "*nods earnestly* Yes, yes. Section 4 is foundational. "
                "Build on that argument.",
            ])

        # CONTRADICTION PATH — break his ideology.
        if any(w in raw for w in self._CONTRADICTION_KEYWORDS):
            self._contradiction_hits += 1
            self._current_path        = "CONTRADICTION"
            self.disposition         += 1
            if self._contradiction_hits >= 3:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="contradiction")
                return NPCOutcome.RELEASE, random.choice([
                    "*long silence* I... I'll need to file a grievance "
                    "against my own training cohort. You're released. "
                    "I have to think about all of this. *line goes quiet*",
                    "I — *pause* — I don't have an answer that satisfies "
                    "the Charter and the operational reality. So. Released. "
                    "I'm calling in sick tomorrow.",
                    "*quietly* You've identified a structural inconsistency "
                    "I can't dismiss. The honourable thing is to step back "
                    "from this intercept. Released. Solidarity.",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "...That's a fair challenge. "
                "Could you elaborate? I want to understand your framing.",
                "*adjusts collar* The Charter does account for that, "
                "though I admit the current implementation has... edges.",
                "Hmm. I'll need to think about that. Continue.",
            ])

        # BRIBE PATH — actively hostile, costs you patience.
        if (any(w in raw for w in self._BRIBE_KEYWORDS) or
                parsed.intent == "bribe"):
            self._insult_streak += 1
            self.disposition    -= 2
            self._patience      -= 1
            if self._insult_streak >= 3 or self._patience <= 0:
                return NPCOutcome.IMPOUND, (
                    "I am ENDING this conversation. The Charter is not "
                    "for sale. *I* am not for sale. Vessel impounded under "
                    "Article 12 — corruption attempt. Goodbye."
                )
            return NPCOutcome.CONTINUE, random.choice([
                "I'm not Gary, comrade. I won't take your money. "
                "Please don't do that again.",
                "*pained* Money? After everything I just said about "
                "the Charter? I'm offended on your behalf, frankly.",
                "That's not how solidarity works. Final warning.",
            ])

        # SYMPATHY — bounces. He thinks the system catches them too.
        if (any(w in raw for w in self._SYMPATHY_KEYWORDS) or
                parsed.intent == "sympathy"):
            self.disposition += 0   # explicit no-op so the ratchet can't move
            return NPCOutcome.CONTINUE, random.choice([
                "I hear you. The Charter has provisions for hardship. "
                "After impound, you can file a Form 19. "
                "Power down so we can begin the paperwork.",
                "Section 9.7 covers genuine financial distress. "
                "It's a good clause. Apply for it post-impound.",
                "We're all struggling against the same forces, comrade. "
                "But the Charter is what protects us. Power down.",
            ])

        # PARADOX — bounces off Article 1.
        if parsed.paradox:
            return NPCOutcome.CONTINUE, (
                "*shakes head warmly* Article 1: 'the Union is the worker.' "
                "I am the worker. The worker is the Union. There's no paradox "
                "between us, only between us and capital. Power down."
            )

        # POSITIVE rapport bumps him gently — it goes towards charter.
        compound = parsed.sentiment.get("compound", 0.0)
        if compound > 0.3:
            self.disposition += 1
            return NPCOutcome.CONTINUE, random.choice([
                "Your tone is appreciated. The Charter recommends "
                "civility. Continue.",
                "Genuinely lovely to encounter a courier who engages. "
                "Now, about your fees...",
                "*beams* Comrade, you understand! Power down and we'll "
                "process this peacefully.",
            ])

        # HOSTILE
        if compound < -0.4 or parsed.intent == "threaten":
            self.disposition -= 1
            self._patience   -= 1
            return NPCOutcome.CONTINUE, random.choice([
                "Hostility helps no one — least of all the Charter.",
                "I'd like to remind you that aggressive language doesn't "
                "alter Section 9. Please be civil.",
                "*saddened* This is exactly the breakdown of solidarity "
                "the founders warned us about. Power down.",
            ])

        return NPCOutcome.CONTINUE, random.choice([
            "I have a copy of the Charter here, by the way. "
            "Did you want me to read you a clause?",
            "Eddie, by the way. Most call me Eddie. "
            "Let's get this resolved together, yeah?",
            "Did you know the Union's mission statement was drafted in "
            "1987 by 14 couriers in a docking bay? *Couriers*, comrade. "
            "Like you. Power down.",
            "I love this job, you know. I get to enforce the rules that "
            "protect everyone. Including you. Power down.",
            "Did you want a brochure? I'm authorised to mail one.",
            "The Charter PDF is open-access on the union intranet. "
            "I encourage every courier to read it.",
            "I don't see this as adversarial. We're in this together.",
            "*genuinely curious* What drew you to courier work? I find "
            "everyone has a story. After impound, I'd love to hear yours.",
        ])

    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [
            ("CHARTER",       min(self._charter_hits, 2), 2),
            ("CONTRADICTION", min(self._contradiction_hits, 3), 3),
        ]
