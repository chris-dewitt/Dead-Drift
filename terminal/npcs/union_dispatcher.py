from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT


class UnionDispatcher(BaseNPC):
    """
    Union Dispatcher — Final Collections Authority. Local 404, District 7.
    Has been 47 forms behind since the incident of '42. It is never not '42.

    Paths to release:
    - COFFEE BREAK: mention coffee/lunch/break/tired → mandatory break clause
    - BUREAUCRATIC OVERWHELM: mention forms/paperwork/backlog 3 times → drowns
    - THE 42 PATH: say "42" → existential crisis, Hitchhiker's Guide energy
    - ONTOLOGICAL ESCAPE: quantum argument (4 unique concepts + 1 legal point)
    - LEGAL PRESSURE: 3 turns citing union violations / grievances
    - BRIBERY: large bribe (10k+) — they are corrupt, but dignified about it
    - PHILOSOPHICAL EROSION: keep making existential points → certainty breaks
    """

    _QUANTUM_TERMS = {
        "schrodinger", "observer", "collapse", "superposition",
        "vessel", "exist", "manifest", "quantum", "undefined", "null",
        "unregistered", "wave", "function", "probability", "uncertainty",
        "eigenstate", "entangled", "decoherence",
    }
    _LEGAL_KEYWORDS = ["grievance", "violation", "lawyer", "lawsuit", "sue",
                       "charter", "clause", "article", "rights", "illegal",
                       "union rules", "arbitration", "injunction", "appeal"]
    _BRIBE_KEYWORDS = ["credits", "pay", "money", "bribe", "offer", "deal",
                       "cash", "transfer", "compensate", "buy"]
    _BIG_BRIBES     = ["10k", "ten thousand", "20k", "twenty", "fifty", "50k",
                       "hundred thousand", "a lot", "everything i have",
                       "15k", "fifteen thousand", "25k", "30k", "thirty"]
    _COFFEE_WORDS   = ["coffee", "lunch", "break", "tired", "hungry", "food",
                       "eat", "rest", "shift", "hours", "overtime", "exhausted",
                       "long day", "been here", "working late"]
    _FORMS_WORDS    = ["forms", "paperwork", "backlog",
                       "bureaucracy", "procedure", "stack", "pile", "admin",
                       "in-tray", "intray", "in tray", "47 forms", "the forms"]

    def __init__(self, vocabulary_vault=None):
        super().__init__("DISPATCHER", patience=9)
        self._vault              = vocabulary_vault
        self._concepts_used: set[str] = set()
        self._legal_points       = 0
        self._bribe_attempts     = 0
        self._certainty          = 10
        self._forms_mentions     = 0
        self._forty_two_hit      = False

    def _intro_line(self) -> str:
        return random.choice([
            "Union Dispatch. Final collections notice. "
            "You have outstanding debt across seventeen jurisdictions. "
            "I have seventeen forms about it. I have seventeen more forms about those forms. "
            "I am forty-seven forms behind. This is, I assure you, not your fault. "
            "Surrender your vessel.",

            "This is Union Dispatch. I'm going to need you to hold. "
            "No, don't hold. You can't hold. I said hold by accident. "
            "Outstanding debt. Seventeen jurisdictions. "
            "I need to find the form. I know it's here somewhere. "
            "It's always here. Everything is always here. "
            "Power down.",

            "Dispatch. Final notice. "
            "Outstanding fees, compound interest, accrual clause seven-B, surcharge. "
            "I have been forty-seven forms behind since the incident of '42. "
            "Every call makes it forty-eight. Don't make it forty-eight. "
            "Surrender the vessel.",
        ])

    def exploits(self) -> dict[str, str]:
        return {
            "coffee_break":          "Mention coffee / lunch / break / tired",
            "bureaucratic_overwhelm": "Mention forms/paperwork until they can't cope",
            "the_42_path":           "Say '42' and watch what happens",
            "ontological_escape":    "Build a quantum argument that the ship doesn't legally exist",
            "legal_pressure":        "File a grievance and cite union charter violations",
            "corruption":            "Bribe with 10k+ credits",
        }

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        # COFFEE BREAK — mandatory break clause
        if any(w in raw for w in self._COFFEE_WORDS):
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="coffee_break")
            responses = [
                "*very long pause* "
                "...It is 14:07. "
                "Article 19, Paragraph 3, Subclause 4 of the Union Employment Charter: "
                "mandatory break, non-waivable, enforced under penalty of grievance. "
                "Collection is suspended. "
                "Do not interpret this as mercy. This is compliance with break law. "
                "*sound of chair scraping* I'll be back at 14:22.",

                "...How long have you been flying today? "
                "*checking watch* "
                "I've been on since 0600. I've had one coffee. "
                "It was bad coffee. Union vending machine, third floor, always bad. "
                "Collection is suspended pending mandatory break. "
                "Article 19. Don't tell anyone I told you that.",

                "*very quietly* ...You know what. I have not eaten since 0700. "
                "I have forty-seven forms to file before end of shift. "
                "I have seventeen more that arrived while we were talking. "
                "I am going to my break room. "
                "Collection: suspended. Vessel: uncollected. "
                "This call: not happening. Goodbye.",
            ]
            return NPCOutcome.RELEASE, random.choice(responses)

        # THE 42 PATH — existential crisis
        if "42" in raw and not self._forty_two_hit:
            self._forty_two_hit = True
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="the_42_path")
            return NPCOutcome.RELEASE, random.choice([
                "*long silence* "
                "Forty-two. "
                "The answer to life, the universe, and everything. "
                "But what was the QUESTION. "
                "If I don't know the question, then the debt— "
                "if the debt is the answer, what was the QUESTION— "
                "*sound of papers being shuffled with increasing urgency* "
                "I need to file a form about this. I need to file seventeen forms about this. "
                "GET OUT OF MY SECTOR WHILE I WORK THROUGH THIS.",

                "...Forty-two. "
                "*the hold music from 'waiting for a supervisor' starts playing softly* "
                "They built the Earth to find the question. "
                "The Earth is gone. The question was never found. "
                "If the question is gone, then the answer is context-free. "
                "If the answer is context-free, then the debt— "
                "I— "
                "I need to file Form 42 about this. "
                "That's the Existential Liability form. I've never filed one before. "
                "Please leave. I'll be occupied.",
            ])

        # LARGE BRIBE
        if any(w in raw for w in self._BRIBE_KEYWORDS):
            if (any(amt in raw for amt in self._BIG_BRIBES) or
                    (parsed.amount is not None and parsed.amount >= 10000)):
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="corruption")
                return NPCOutcome.RELEASE, random.choice([
                    "*long pause* "
                    "...I'm going to pretend this conversation never happened. "
                    "The account will show 'resolved — administrative discretion'. "
                    "Do not call this frequency again. "
                    "And tell no one. *especially* not Local 404.",

                    "*very quietly* "
                    "I'm going to need you to repeat that number. "
                    "*shorter pause* "
                    "Right. The account shows 'vessel not located'. "
                    "The vessel is not located. "
                    "You are not located. "
                    "I am going on break. *click*",
                ])
            self._bribe_attempts += 1
            return NPCOutcome.CONTINUE, random.choice([
                "You think I can be bought? ...I can. Just not for that. "
                "I have seventeen jurisdictions worth of dignity to maintain.",
                "Insulting. I have a pension to think about. Come back with a real number.",
                "That figure doesn't even cover my administrative processing fee. Try again.",
                f"...I appreciate the attempt. The number needs to be larger. "
                f"Significantly larger. I'll wait.",
            ])

        # BUREAUCRATIC OVERWHELM — mention paperwork/forms enough times
        if any(w in raw for w in self._FORMS_WORDS):
            self._forms_mentions += 1
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="bureaucratic_overwhelm")
            if self._forms_mentions >= 3:
                return NPCOutcome.RELEASE, random.choice([
                    "I am forty-seven forms behind. "
                    "I have been forty-seven forms behind since the incident of '42. "
                    "This call has generated nine new forms. "
                    "If I file Form 27-B before 1700 hours Blevins doesn't get the quarterly bonus. "
                    "I need to go. YOU NEED TO GO. "
                    "COLLECTION SUSPENDED. BLEVINS CANNOT GET THAT BONUS. GOODBYE.",

                    "*muffled sound of papers falling* "
                    "I have— I just— there's— "
                    "Every conversation generates a Form 17-A, a Form 17-B, "
                    "a Form 17-B subsection 4, and a Form confirming receipt of Form 17-B subsection 4. "
                    "I cannot— I physically cannot— "
                    "Vessel: released pending paperwork. "
                    "The paperwork will never be complete. "
                    "I have accepted this. GOODBYE.",
                ])
            forms_responses = [
                "Yes. Forms. I am aware of forms. "
                "I am the forms. I have become the forms. "
                "Form 17-A: outstanding debt. Form 17-B: vessel details. "
                "Form 17-B subsection 4: your tone of voice. All outstanding. "
                "Power down.",

                "I have forty-seven forms behind me right now. "
                "FORTY-SEVEN. This call is generating three more. "
                "If you have a point about paperwork, make it fast. "
                "My in-tray is a physical danger.",
            ]
            return NPCOutcome.CONTINUE, forms_responses[min(self._forms_mentions - 1, 1)]

        # LEGAL PRESSURE
        if (parsed.intent == "legal" or
                any(w in raw for w in self._LEGAL_KEYWORDS)):
            self._legal_points += 1
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="legal_pressure")
            if self._legal_points >= 3:
                return NPCOutcome.RELEASE, (
                    "...Fine. If you file that grievance, the collection freeze "
                    "kicks in automatically under Article 9. "
                    "I cannot legally proceed while a grievance is pending. "
                    "You have 48 hours. Use them. "
                    "And for the record, I knew you were going to do that. "
                    "I have a form for people who do that. "
                    "I am forty-seven forms behind."
                )
            legal_responses = [
                "You know your charter. I'll give you that. Keep talking.",
                "That's... technically an arguable point. It doesn't make you debt-free. Yet.",
                "I've flagged your grievance argument. One more citation and you've got something.",
            ]
            return NPCOutcome.CONTINUE, legal_responses[min(self._legal_points - 1, 2)]

        # ONTOLOGICAL ESCAPE — quantum/existence argument
        new_hits = self._QUANTUM_TERMS & set(parsed.tokens)
        if self._vault:
            new_hits |= self._QUANTUM_TERMS & set(self._vault.get_all_terms())
        self._concepts_used.update(new_hits)

        if len(self._concepts_used) >= 4 and self._legal_points >= 1:
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="ontological_escape")
            return NPCOutcome.RELEASE, self._debt_deleted_monologue()

        if new_hits:
            self._certainty -= len(new_hits)
            if self._certainty <= 2:
                return NPCOutcome.RELEASE, (
                    "*very long silence* "
                    "I've been doing this job for twenty-two years. "
                    "I have never once questioned whether the ships exist. "
                    "The ships exist. The debt exists. That's the foundation. "
                    "If the foundation is— "
                    "I need to sit down. "
                    "I need to file a form about sitting down. "
                    "VESSEL: RELEASED. REASON: UNSPECIFIED. GET OUT OF MY SECTOR."
                )
            missing = list(self._QUANTUM_TERMS - self._concepts_used)[:2]
            return NPCOutcome.CONTINUE, random.choice([
                f"That's... an interesting argument. But you haven't addressed "
                f"{' or '.join(missing) if missing else 'the core question'}. "
                f"The debt is mathematically real until you prove the vessel isn't.",

                "You're making me think. Stop doing that. I have forms to file. "
                f"The {'and '.join(missing[:1]) if missing else 'ontological status'} "
                f"is still unresolved.",

                "I've been doing this job for twenty-two years. "
                "Nobody has ever made it this far. Keep going. "
                "Not because I want you to. Because I'm professionally curious.",
            ])

        # POSITIVE SENTIMENT — philosophical erosion
        compound = parsed.sentiment.get("compound", 0.0)
        if compound > 0.3 or parsed.intent == "philosophical":
            self._certainty -= 1
            self.disposition += 1
            return NPCOutcome.CONTINUE, random.choice([
                "You make an interesting point. It doesn't change the debt. "
                "The debt is very patient.",
                "I haven't had this conversation before. In twenty-two years. "
                "I'm not sure what to do with that. Keep talking.",
                "...You're making me think. Stop doing that. "
                "...Actually don't stop. I'm just saying it makes me uncomfortable.",
                "There's a form for existential uncertainty. Form 42. "
                "I've never filed one. I might need to today.",
            ])

        # HOSTILE
        if compound < -0.4 or parsed.intent == "threaten":
            self.disposition -= 1
            return NPCOutcome.CONTINUE, random.choice([
                "Threatening a Union Dispatcher is Article 12, Paragraph 3. "
                "I'm adding it to your tab. I have a form for it. Form 99-B. "
                "I love filing Form 99-B.",
                "I've authorized repo barges for less. Watch your tone. "
                "I'm already forty-seven forms behind. Don't make it forty-eight.",
                "Seventeen jurisdictions. Your anger is noted. It changes nothing. "
                "I've noted it in Form 17-C. That's the Hostility Notation form.",
            ])

        # DEFAULT — the 47-forms-behind running gag
        return NPCOutcome.CONTINUE, self._dispatcher_filler()

    def _dispatcher_filler(self) -> str:
        return random.choice([
            "I am forty-seven forms behind. This conversation is making it forty-eight. "
            "Please surrender your vessel so I can get back to the forms.",

            "The debt is real. The tow barge is real. The seventeen jurisdictions are real. "
            "The forty-seven forms are also real. One of these things is taking up most of my afternoon.",

            "We have a saying in Dispatch: 'everyone runs, everyone pays'. "
            "We have it on a mug. The mug is also in the forms system. Asset register. "
            "Mug. Outstanding.",

            "Your debt has accrued interest while we've been talking. "
            "My paperwork has also accrued. We are both, in different ways, drowning.",

            "Do you know what the collection rate is for clone-debt over 100,000 credits? "
            "One hundred percent. Eventually. "
            "I have time. The interest rate has more time than I do.",

            "I have been forty-seven forms behind since the incident of '42. "
            "I do not speak about the incident of '42. "
            "I do file forms about it. Forty-seven of them.",

            "The notice was sent. Form 17-B was filed in the appropriate depot. "
            "Copies were available for inspection at the relevant office. "
            "You were given the standard notice period. "
            "I cannot help it if you were difficult to reach.",

            "I'm a patient person. The interest rate is not. "
            "The interest rate has no feelings about you. I have a few.",

            "I once had a pilot argue his vessel didn't exist for forty minutes. "
            "It didn't work. But I remember it fondly. "
            "Mostly because it delayed the forms.",

            "Nova Soma sends us productivity metrics every quarter. "
            "Last quarter I processed 312 collections. "
            "Blevins processed 318. "
            "I don't want to talk about Blevins. "
            "I have a form about Blevins. I file it monthly.",
        ])

    def _debt_deleted_monologue(self) -> str:
        return random.choice([
            "*long silence* "
            "You're right. If the vessel's wave function never collapsed "
            "into a defined ownership state, it was never legally registered. "
            "If it was never registered, the debt instrument is null. "
            "If the debt is null... "
            "*sound of a keyboard being filed under 'existential concerns'* "
            "I'm going to need a personal day. "
            "DEBT RECORD: MATHEMATICALLY DELETED. "
            "Get out of my sector.",

            "*even longer silence* "
            "...The thing is, I knew this day would come. "
            "I have a form for it. Form 42. Existential Liability. "
            "I've never filed Form 42. I've thought about filing Form 42. "
            "If the vessel exists in superposition, the debt is in superposition. "
            "A superposition debt cannot be collected under Article 7, Section 3. "
            "COLLECTION: SUSPENDED PENDING QUANTUM RESOLUTION. "
            "QUANTUM RESOLUTION: NEVER. "
            "Get out. I need to call my supervisor. "
            "My supervisor also doesn't know what to do about this. "
            "That's why it's his job and not mine.",
        ])
