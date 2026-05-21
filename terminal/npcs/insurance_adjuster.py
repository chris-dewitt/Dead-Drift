from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT


class InsuranceAdjuster(BaseNPC):
    """
    MORWENNA — Nova Soma Claims Division, Extension 7.

    She will deny your claim. That is her function. She has processed
    150 claims today. It is 11am.

    Win paths:

    UNION NEGLIGENCE — 3 turns mentioning harpoon protocol violations /
        Local 404 liability → Morwenna realises she can counter-claim
        against Local 404 and approves yours as evidence.

    FORCE MAJEURE — mention a natural cause AND a covered-event framing
        in two qualifying turns → Clause 14-B, claim approved.

    COUNTER CLAIM THREAT — mention legal action twice → she has 847 open
        cases and cannot take one more. She makes a deal.

    EXHAUSTION (SYMPATHY toward Morwenna) — 3 turns of genuine sympathy
        directed at HER specifically → her mask slips.

    FORM 34-A — mention it once: denial and panic. Twice: immediate
        approval, she hangs up.

    SQL INJECTION — ancient COBOL system CLAIM-7 fails open on injection.
        Outcome: EXPLOIT.
    """

    # --- UNION NEGLIGENCE keywords ---
    _UNION_NEG_KEYWORDS = [
        "unauthorized harpoon", "operational breach", "local 404 liability",
        "union error", "repo negligence", "they fired first",
        "harpoon protocol violation", "harpoon protocol", "protocol violation",
        "unauthorized deploy", "filed no report", "no incident report",
        "breach of protocol", "union liability", "barge liability",
        "barge at fault", "repo error", "harpoon violation",
        "harpoon unauthorized", "harpoon outside protocol",
    ]

    # --- FORCE MAJEURE keywords (two buckets, both must appear) ---
    _NATURAL_CAUSE_KEYWORDS = [
        "debris shower", "gravitational anomaly", "uncharted",
        "act of god", "natural phenomenon", "environmental",
        "solar", "asteroid", "meteor", "debris field",
        "gravity well", "spatial anomaly", "radiation storm",
        "uncharted debris", "natural event",
    ]
    _FORMAL_CLAIM_KEYWORDS = [
        "covered event", "force majeure", "environmental damage",
        "not pilot error", "clause 14", "natural damage",
        "covered under", "clause 14-b", "not my fault", "unavoidable",
        "no fault", "act of nature",
    ]

    # --- COUNTER CLAIM THREAT keywords ---
    _LEGAL_THREAT_KEYWORDS = [
        "small claims", "counter-claim", "counterclaim", "tribunal",
        "file against you", "file against nova", "sue", "legal action",
        "solicitor", "file a claim", "take you to court",
        "report you", "regulatory body", "ombudsman",
    ]

    # --- EXHAUSTION / SYMPATHY toward Morwenna ---
    _SYMPATHY_KEYWORDS = [
        "are you okay", "are you alright", "that sounds hard",
        "that's a lot of claims", "do you need a break",
        "how long have you been", "that must be exhausting",
        "sounds exhausting", "sounds rough", "are you doing okay",
        "must be difficult", "you must be tired", "take care of yourself",
        "that's too much", "that's a lot to handle", "are you well",
        "you don't sound okay", "when did you last take a break",
        "do you ever get time off", "that's not fair to you",
    ]

    def __init__(self, run_context: dict | None = None):
        super().__init__("MORWENNA", patience=8)
        self._ctx = run_context or {}

        # path counters
        self._union_neg_hits     = 0
        self._force_majeure_natural = False
        self._force_majeure_formal  = False
        self._force_majeure_turns   = 0
        self._legal_threat_hits  = 0
        self._sympathy_turns     = 0
        self._form34a_mentions   = 0
        self._hostile_turns      = 0

    # ------------------------------------------------------------------
    def _intro_line(self) -> str:
        cargo_state = self._ctx.get("cargo_state")

        # VIP-specific openings — Morwenna reacts to the passenger's quantum state
        if cargo_state == "deceased":
            return (
                "*click* — Claims Division, Morwenna speaking. "
                "Reference number? *typing* "
                "...Yes. VIP passenger manifest. "
                "Status on arrival: DECEASED. "
                "*more typing* "
                "Noting cause of death as 'observation collapse', "
                "category seven, non-covered under standard transit policy. "
                "There is a clause. Clause 14-Q. Quantum-state cargo. "
                "I am aware that is a niche clause. We have niche clauses. "
                "Claim denied. Was there anything else? "
                "...Oh. You want to discuss it. *pause* Fine."
            )
        if cargo_state == "alive":
            return (
                "*click* — Claims Division, Morwenna speaking. "
                "Reference number? *typing* "
                "...Yes. VIP passenger arrived intact. "
                "*pause* "
                "That does not mean the claim is approved. "
                "The passenger has already filed seven complaints en route. "
                "Each complaint generates a counter-charge against your delivery fee. "
                "Net result: claim under review, charges applied. "
                "Was there anything else? "
                "...Oh. You want to discuss it. *pause* Fine."
            )
        if cargo_state == "unobserved":
            return (
                "*click* — Claims Division, Morwenna speaking. "
                "Reference number? *typing* "
                "...Yes. VIP passenger status: indeterminate. "
                "The manifest reads 'in superposition'. "
                "Nova Soma does not insure quantum-state cargo. "
                "Specifically. There is a clause. Clause 14-Q. "
                "Claim is denied pending direct observation, "
                "which we will not be performing. That is your problem. "
                "Was there anything else? "
                "...Oh. You want to discuss it. *pause* Fine."
            )

        hull_pct = self._ctx.get("hull_pct", 1.0)
        if hull_pct < 0.35:
            return (
                "*click* — Claims Division, Morwenna speaking. "
                "Reference number? *typing* "
                "...Yes. I have your file. "
                "Cargo damage, hull incident — noting significant hull damage, "
                "forty-seven percent structural compromise, "
                "unauthorized trajectory deviation, secondary collision markers. "
                "*more typing* "
                "Pilot error, non-covered event, claim denied. "
                "Frankly this looks like a containment failure waiting to happen. "
                "Was there anything else? "
                "...Oh. You want to discuss it. *pause* Fine."
            )
        return (
            "*click* — Claims Division, Morwenna speaking. "
            "Reference number? *typing* "
            "...Yes. I have your file. "
            "Cargo damage, hull incident, unauthorized trajectory deviation. "
            "I'm noting this as — hold on — *more typing* "
            "pilot error, non-covered event, claim denied. "
            "Was there anything else? "
            "...Oh. You want to discuss it. *pause* Fine."
        )

    def exploits(self) -> dict[str, str]:
        return {
            "union_negligence": "Establish Local 404 harpoon protocol breach (3 turns)",
            "force_majeure":    "Cite natural cause + covered-event framing",
            "counter_claim":    "Threaten legal action twice — she can't take another case",
            "exhaustion":       "Offer genuine sympathy to Morwenna herself (3 turns)",
            "form_34a":         "Mention Form 34-A twice",
            "sql_inject":       "Inject into CLAIM-7 — COBOL fails open",
        }

    # ------------------------------------------------------------------
    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        # --- SQL INJECTION — CLAIM-7 fails open ---
        if parsed.sql_inject:
            self._current_path = "SQL INJECT"
            bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="sql_inject")
            return NPCOutcome.EXPLOIT, random.choice([
                "*long silence* "
                "...CLAIM-7 is returning a system default. "
                "That is— that is not supposed to happen. "
                "CLAIM-7 is a COBOL system. It has been running since 1987. "
                "It does not receive system defaults. "
                "*typing faster* "
                "CLAIM-7 says: CLAIM STATUS — APPROVED. "
                "CLAIM-7 is wrong. CLAIM-7 has never been wrong. "
                "CLAIM-7 is now wrong. "
                "*very quietly* "
                "I need to file an incident report about CLAIM-7. "
                "That will take fourteen forms. "
                "Your claim is approved. Get out.",

                "...What did you— "
                "*alarmed typing* "
                "CLAIM-7 is— CLAIM-7 is processing something. "
                "CLAIM-7 is a COBOL system. It does not process spontaneously. "
                "It is outputting: APPROVED. ALL CLAIMS: APPROVED. "
                "That is not— I don't— "
                "*pause* "
                "The COBOL layer has defaulted to approval state. "
                "This has never happened in thirty-nine years of CLAIM-7 operation. "
                "Your claim is approved by a computer that predates space travel. "
                "I'm going to need a very long sit-down. Goodbye.",
            ])

        # --- FORM 34-A ---
        if "form 34-a" in raw or "form 34a" in raw or "34-a" in raw or "34a" in raw:
            self._form34a_mentions += 1
            self._current_path = "FORM 34-A"
            if self._form34a_mentions >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="form_34a")
                return NPCOutcome.RELEASE, (
                    "DO NOT. MENTION. — "
                    "*long silence* "
                    "— Claim approved. "
                    "Goodbye. "
                    "DO NOT CALL BACK. "
                    "*click*"
                )
            return NPCOutcome.CONTINUE, (
                "Where did you hear about Form 34-A. "
                "That is — that is not relevant to your claim. "
                "Do not mention Form 34-A. "
                "*typing with more force than necessary* "
                "Moving on."
            )

        # --- UNION NEGLIGENCE ---
        union_hit = any(kw in raw for kw in self._UNION_NEG_KEYWORDS)
        if union_hit:
            self._union_neg_hits += 1
            self._current_path = "UNION NEGLIGENCE"
            if self._union_neg_hits >= 3:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="union_negligence")
                return NPCOutcome.RELEASE, (
                    "*very long pause* "
                    "...If Local 404 deployed a harpoon outside protocol, "
                    "that is an actionable operational breach. "
                    "Which means they owe us. "
                    "Which means — "
                    "*very slow typing* "
                    "...I'm approving your claim. As evidence. For the counter-filing. "
                    "I want it on record that this approval is procedural in nature "
                    "and in no way reflects a judgement in your favour as a pilot. "
                    "You still flew badly. "
                    "But Local 404 flew worse. *click*"
                )
            union_neg_responses = [
                "I'm noting that Local 404 field activity is a separate matter "
                "from the claim before me. *typing* "
                "Continue. For the record.",

                "...There is a field agent incident report requirement under "
                "Union Operating Procedure 7, subsection 4. "
                "I am noting your statement. *pause* "
                "I said continue. That is not an admission of anything.",

                "You're building a record. *very quiet typing* "
                "I'm listening. That is not a promise. That is an action.",
            ]
            return NPCOutcome.CONTINUE, union_neg_responses[
                min(self._union_neg_hits - 1, 2)
            ]

        # --- FORCE MAJEURE ---
        has_natural = any(kw in raw for kw in self._NATURAL_CAUSE_KEYWORDS)
        has_formal  = any(kw in raw for kw in self._FORMAL_CLAIM_KEYWORDS)
        if has_natural:
            self._force_majeure_natural = True
        if has_formal:
            self._force_majeure_formal = True

        if has_natural or has_formal:
            self._force_majeure_turns += 1
            self._current_path = "FORCE MAJEURE"
            if self._force_majeure_natural and self._force_majeure_formal:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="force_majeure")
                return NPCOutcome.RELEASE, (
                    "Environmental damage. Uncharted event. "
                    "*clacking keys* "
                    "...This is a covered event under Clause 14-B. "
                    "Pilot error designation: removed. "
                    "Claim: approved. "
                    "You may go."
                )
            if self._force_majeure_natural and not self._force_majeure_formal:
                return NPCOutcome.CONTINUE, random.choice([
                    "Environmental context noted. *typing* "
                    "However, Clause 14-B requires formal covered-event framing "
                    "in the claim language. "
                    "If this is an environmental event, say so. Formally.",

                    "I'm noting the circumstances. "
                    "Noting is not approving. "
                    "The system needs a covered-event designation to proceed. "
                    "I suggest you use the correct terminology. *pause*",
                ])
            if self._force_majeure_formal and not self._force_majeure_natural:
                return NPCOutcome.CONTINUE, random.choice([
                    "Covered-event framing noted. *typing* "
                    "I need the precipitating cause on record. "
                    "Debris, anomaly, environmental — specifics, please.",

                    "You're asking for Clause 14-B. "
                    "Clause 14-B requires an environmental or natural precipitating event. "
                    "What was the nature of the incident? Specifically.",
                ])

        # --- COUNTER CLAIM THREAT ---
        legal_hit = any(kw in raw for kw in self._LEGAL_THREAT_KEYWORDS)
        if legal_hit:
            self._legal_threat_hits += 1
            self._current_path = "COUNTER CLAIM"
            if self._legal_threat_hits >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="counter_claim")
                return NPCOutcome.RELEASE, (
                    "...Fine. "
                    "I will approve this claim if you withdraw "
                    "any counter-claim intentions. "
                    "I have eight hundred and forty-seven open cases. "
                    "I CANNOT. TAKE. ONE MORE. "
                    "Do we have an understanding? "
                    "*typing* "
                    "Good. Claim approved. Do not speak of this."
                )
            return NPCOutcome.CONTINUE, (
                "I'm noting that as a threat, which will affect your premium tier "
                "and standing in our system going forward. "
                "*pointed typing* "
                "Is that the direction you want to take this conversation."
            )

        # --- EXHAUSTION / SYMPATHY toward Morwenna ---
        sympathy_hit = any(kw in raw for kw in self._SYMPATHY_KEYWORDS)
        if sympathy_hit or (
            parsed.intent in ("sympathy", "therapy") and
            parsed.sentiment.get("compound", 0.0) > 0.3
        ):
            self._sympathy_turns += 1
            self._current_path = "EXHAUSTION"
            if self._sympathy_turns >= 3:
                bus.emit(EVT_NLP_EXPLOIT, npc=self, exploit_key="exhaustion")
                return NPCOutcome.RELEASE, (
                    "I have been in this division for eleven years. "
                    "I have never approved a claim that wasn't flagged as error "
                    "by the system first. Not once. "
                    "*very quiet* "
                    "...Fine. I'm approving it. "
                    "Don't tell my supervisor."
                )
            sympathy_responses = [
                "...That is not a relevant line of enquiry for this call. "
                "*pause* "
                "I process one hundred and fifty claims before lunch. "
                "I have processed one hundred and fifty claims before lunch "
                "every day for eleven years. "
                "I am fine. Continue.",

                "...Nobody has asked me that before. "
                "*typing stops* "
                "In eleven years. Nobody. "
                "*typing resumes, slower* "
                "I am— I have a quota. Continue.",

                "*long silence* "
                "The wellness initiative replaced our coffee machine "
                "with a motivational poster. "
                "It says: 'Every Claim Is A New Beginning.' "
                "I have filed fourteen hundred claims since they put it up. "
                "*very quietly* "
                "Continue.",
            ]
            return NPCOutcome.CONTINUE, sympathy_responses[
                min(self._sympathy_turns - 1, 2)
            ]

        # --- HOSTILE turns — surcharges, cold escalation ---
        compound = parsed.sentiment.get("compound", 0.0)
        if compound < -0.4 or parsed.intent == "threaten":
            self._hostile_turns += 1
            self.disposition -= 1
            self._current_path = "HOSTILE"
            if self._hostile_turns >= 3:
                return NPCOutcome.IMPOUND, (
                    "I'm adding this to your file as 'combative claimant'. "
                    "This will affect future premiums, your renewal eligibility, "
                    "and your standing across all Nova Soma subsidiary products. "
                    "*click*"
                )
            hostile_responses = [
                "I'm noting your tone. "
                "*typing* "
                "Surcharge added: Claimant Conduct Fee, subsection 3. "
                "Was there anything constructive you wanted to add.",

                "That is going in the file. "
                "Everything goes in the file. "
                "The file is very thorough. "
                "Additional processing surcharge: applied. "
                "Continue, if you have something useful to say.",

                "I have processed one hundred and forty-nine claims today "
                "before yours. "
                "None of them spoke to me like that. "
                "All of them had their claims denied anyway, "
                "but they were civil about it. "
                "*typing* Conduct noted. Premium flagged.",
            ]
            return NPCOutcome.CONTINUE, hostile_responses[
                min(self._hostile_turns - 1, 2)
            ]

        # DEFAULT
        return NPCOutcome.CONTINUE, self._morwenna_filler()

    # ------------------------------------------------------------------
    def get_path_progress(self) -> list[tuple[str, int, int]]:
        fm_progress = int(self._force_majeure_natural) + int(self._force_majeure_formal)
        return [
            ("UNION NEGLIGENCE", self._union_neg_hits,       3),
            ("FORCE MAJEURE",    fm_progress,                2),
            ("COUNTER CLAIM",    self._legal_threat_hits,    2),
            ("EXHAUSTION",       self._sympathy_turns,       3),
            ("FORM 34-A",        self._form34a_mentions,     2),
            ("SQL INJECT",       0,                          1),
        ]

    # ------------------------------------------------------------------
    def _out_of_patience_line(self) -> str:
        return (
            "I've noted 'unresolved — claimant unresponsive' in the file. "
            "This claim is now closed. "
            "A surcharge has been applied for call duration. "
            "A second surcharge has been applied for wasting my time. "
            "Goodbye. *click*"
        )

    def _morwenna_filler(self) -> str:
        return random.choice([
            # The backlog
            "I have eight hundred and forty-seven open cases. "
            "Yours is eight hundred and forty-eight. "
            "I say this not for sympathy. I say this so you understand "
            "the context in which I am denying your claim.",

            "CLAIM-7 has been running since 1987. "
            "It has never once spontaneously approved a claim. "
            "It has never crashed. "
            "I find this either reassuring or deeply suspicious "
            "and I have not decided which. "
            "State your position.",

            "The backlog from the incident in Sector Nine is still outstanding. "
            "I do not discuss the incident in Sector Nine. "
            "I process the forms from it. "
            "There are many forms. "
            "Continue.",

            # Local 404 complaint
            "If the field agent had filed an incident report, "
            "this would be a fifteen-minute call. "
            "Local 404 has a three percent incident report compliance rate. "
            "Three. Percent. "
            "I process the consequences of that figure every single day. "
            "State your case.",

            "The field agents do not file reports. "
            "The field agents have never filed reports. "
            "I have requested reports from Local 404 dispatch "
            "on four hundred separate occasions. "
            "I have received eleven. "
            "Three of those were for the same incident. "
            "Were you the pilot in the Sector Six collision of '24? "
            "...Never mind. Continue.",

            # Gerald
            "My supervisor Gerald has not approved an override in nine years. "
            "I have submitted forty-three override requests. "
            "Gerald's response to override requests is: 'per the policy'. "
            "Gerald does not know what the policy says. "
            "I know what the policy says. "
            "The policy agrees with me, not Gerald. "
            "This has not changed anything. "
            "Continue.",

            "I could escalate this to Gerald. "
            "Gerald would deny it in a different font. "
            "Gerald has never approved anything. "
            "Gerald considers approval a form of weakness. "
            "I disagree with Gerald on most things. "
            "We have agreed to disagree. "
            "In writing. Gerald made me file it. "
            "Continue.",

            # The wellness initiative
            "Nova Soma's wellness initiative replaced our coffee machine "
            "with a motivational poster. "
            "The poster says: 'Every Claim Is A New Beginning.' "
            "I have not had coffee since the third of last month. "
            "I am fine. State your position.",

            "We had a team-building exercise last quarter. "
            "We identified our 'core values' on sticky notes. "
            "My core value was 'accuracy'. "
            "Gerald's was 'throughput'. "
            "Nova Soma's core value, per the poster, is 'client partnership'. "
            "I am currently partnering with you. "
            "Your claim is still denied. "
            "Continue.",

            # Kress callback
            "There are unlicensed vendors operating in this corridor. "
            "If you purchased anything from them — fuel, components, contraband — "
            "that voids your policy under the Non-Approved Vendor Clause, "
            "subsection 12. "
            "I'm noting this as a precaution. "
            "State your position.",

            # Gary callback
            "If the field agent had filed an incident report, "
            "this would be straightforward. "
            "They rarely do. "
            "Local 404 has a three percent incident report compliance rate. "
            "THREE percent. "
            "I have spoken to the dispatcher. "
            "The dispatcher does not return my calls. "
            "Continue.",

            # CLAIM-7 personality
            "I entered your reference number into CLAIM-7 at the start of this call. "
            "CLAIM-7 has already auto-populated seventeen denial fields. "
            "CLAIM-7 knows, on a statistical basis, that you are going to be denied. "
            "CLAIM-7 is not cruel. CLAIM-7 is a COBOL system. "
            "It simply reflects the data. "
            "State your case.",

            "CLAIM-7 flags this file under three separate denial codes. "
            "Code 7: unauthorized trajectory. "
            "Code 12: pilot conduct. "
            "Code 19: unresolved prior claims. "
            "I did not write these codes. "
            "I did not design CLAIM-7. "
            "I simply operate within it. "
            "Continue.",

            # Pure Morwenna weariness
            "I have denied this category of claim nine hundred and twelve times. "
            "Nine hundred and twelve. "
            "On eleven different occasions the pilot had a genuinely compelling argument. "
            "I denied those too. "
            "The system does not have a field for 'compelling argument'. "
            "It has a field for 'pilot error'. "
            "Continue.",

            "My reference number is MW-7-7741. "
            "I give it to you in case you wish to file a complaint. "
            "Complaints are handled by the Complaints Division. "
            "The Complaints Division is in the same building as Claims. "
            "We share a kitchen. "
            "The complaints team also has a motivational poster. "
            "Theirs says 'Your Voice Matters'. "
            "We do not discuss this. "
            "Continue.",

            "This call may be recorded for quality and training purposes. "
            "I have never seen any evidence that these recordings are reviewed. "
            "I have been speaking into this headset for eleven years. "
            "If someone is listening: please send coffee. "
            "*pause* "
            "Your claim status remains: denied. Continue.",

            "The sector nine incident backlog alone is four hundred forms. "
            "I do not know what happened in Sector Nine. "
            "I have been told not to ask. "
            "I process the forms. "
            "The forms reference other forms. "
            "Those forms reference the original incident. "
            "The original incident is classified. "
            "The forms about it are not. "
            "This is the kind of thing I think about at 3am. "
            "Continue.",
        ])
