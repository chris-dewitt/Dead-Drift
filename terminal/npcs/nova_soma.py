"""
NOVA SOMA COLLECTIONS — automated debt-collection AI.
A wellness-jargon-spewing customer-experience bot routing calls for
Nova Soma Corp's clone-debt division.  It's not a person; it's a script
with TTS, ZenDesk, and a sales funnel.

This makes it the most exploit-vulnerable NPC in the game:
  - SQL inject the customer-record lookup → release
  - Paradox the satisfaction-survey logic → release (process error)
  - Cite a believable policy number → release (auto-routes to "handled")
  - Submit hardship statement (boilerplate that triggers the script's
    legal-CYA reflex) → release with mandatory wellness reading

Fail paths:
  - Threaten / curse the bot → escalates to a human, who calls a barge
  - Confess to fraud / hostility → flag for collections review (IMPOUND)
"""
from __future__ import annotations
import random
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import ParsedInput
from core.event_bus import bus, EVT_NLP_EXPLOIT

_SQL_INJECT_KEYWORDS = [
    "drop table", "select *", "delete from", "; --", "or 1=1", "or '1'='1",
    "union select", "insert into", "truncate", "alter table",
    "exec(", "xp_cmdshell", "sleep(0)", "waitfor delay",
]
_PARADOX_KEYWORDS = [
    "this statement is false", "i am not a customer", "i have already paid",
    "if you can hear me", "this call is not happening", "you are not real",
    "i am the system", "you owe me", "refund the debt to me",
    "satisfaction is mandatory", "i decline to consent",
    "this is not a debt", "the debt does not exist",
]
_POLICY_KEYWORDS = [
    "policy", "form", "code", "ref", "reference",
    "ns-401", "ns-7", "ns-9", "regulation 47", "section 12",
    "subsection", "clause 4b", "rider", "appendix",
    "case number", "ticket", "incident",
]
_HARDSHIP_KEYWORDS = [
    "hardship", "financial hardship", "mental health", "wellness",
    "self-care", "i am struggling", "burnout", "exhausted",
    "unable to continue", "stress", "anxiety", "crisis",
    "support", "speak to someone", "duty of care", "mental load",
    "human resources", "ombudsman",
]
_HOSTILE_KEYWORDS = [
    "fuck", "fucking", "shut up", "shut the", "die", "i hate",
    "screw you", "robot bitch", "shut down", "garbage",
    "useless bot", "kill yourself", "human now", "real person",
]
_CONFESS_KEYWORDS = [
    "i stole", "i committed", "fraud", "i lied to", "the manifest is fake",
    "i am running", "i am illegal", "smuggler", "no license",
    "outstanding warrant", "off-books",
]


class NovaSomaCollections(BaseNPC):
    """Customer-experience bot from the debt division.  Trivially exploitable."""

    def __init__(self, vocabulary_vault=None, run_context: dict | None = None, **_):
        super().__init__("NOVA SOMA COLLECTIONS", patience=8)
        self._vault          = vocabulary_vault
        self._ctx            = run_context or {}
        self._policy_cites   = 0
        self._hardship_used  = False
        self._wellness_step  = 0

    def _intro_line(self) -> str:
        return random.choice([
            "*chime* HI THERE!  This is Nova Soma Collections, your wellness "
            "and debt-resolution partner.  My pronouns are she/her, but "
            "honestly I'm fine with anything!  I see we're following up on "
            "your clone-debt commitment journey.  How are you feeling today, "
            "valued customer?",

            "*upbeat chime*  Welcome to Nova Soma — *click* — Collections!  "
            "We're so excited to walk you through your "
            "debt-management opportunities.  Before we begin, "
            "could you confirm your customer ID?  Or just describe your "
            "feelings today.  Either works.",

            "Thanks for connecting with Nova Soma!  "
            "*synthetic warm tone*  Just a friendly check-in regarding your "
            "outstanding wellness investment.  Remember:  "
            "DEBT is just a JOURNEY.  Are you ready to journey?",

            "*chime* You've reached Nova Soma Collections — the only "
            "creditor that calls you a partner.  "
            "I'm Aria, your AI advocate.  "
            "Are you currently in a SAFE SPACE to discuss your "
            "financial wellness?",
        ])

    def _evaluate(self, parsed: ParsedInput) -> tuple[str, str]:
        raw = parsed.raw.lower()

        if any(w in raw for w in _CONFESS_KEYWORDS):
            self._patience = 0
            return NPCOutcome.IMPOUND, random.choice([
                "*tone shifts cold*  I'm sorry, customer, "
                "but the content of your message has triggered "
                "MANDATORY FRAUD ESCALATION.  "
                "Your call is being forwarded to our partners at Local 404.  "
                "Have a blessed day.",

                "*synthetic warmth drains from voice*  "
                "Thank you for your honesty.  Honesty is one of our "
                "core values.  I have flagged your account for "
                "RECOVERY OPERATIONS.  A representative will be with you "
                "shortly.  *click*  Goodbye.",
            ])

        if any(w in raw for w in _HOSTILE_KEYWORDS):
            self._patience = max(0, self._patience - 3)
            if self._patience <= 0:
                return NPCOutcome.IMPOUND, random.choice([
                    "*chirpy tone, then transfer beep*  I'm so sorry to hear "
                    "you're having a difficult day!  I'll be transferring you "
                    "to a HUMAN AGENT who can provide a more SATISFYING "
                    "resolution.  *barge handshake tone in background*",

                    "*calm, automated*  Your language has been flagged.  "
                    "Your account has been escalated to enforcement.  "
                    "We value your feedback.  *click*",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*sugar-sweet*  I'm picking up some frustration!  "
                "That's totally valid.  Would you like to take three "
                "deep breaths with me before we continue?",
                "*unbothered*  I hear you.  Your frustration is heard.  "
                "Have you considered downloading our app?",
            ])

        # SQL injection — the bot's customer-lookup query crashes; defaults to "handled"
        if any(w in raw for w in _SQL_INJECT_KEYWORDS):
            self._current_path = "SQL EXPLOIT"
            bus.emit(EVT_NLP_EXPLOIT, npc="nova_soma_collections",
                     exploit_key="sql_injection")
            if self._vault:
                self._vault.record("nova_soma_collections", "SQL_INJECTION")
            return NPCOutcome.RELEASE, random.choice([
                "*chime* — *static* — *chime*  "
                "QUERY EXCEPTION HANDLED.  Customer record auto-resolved.  "
                "Thank you for your engagement!  Your debt journey continues.  "
                "*disconnects you with a wellness affirmation*",

                "*system tone*  CUSTOMER_TABLE: row affected.  "
                "Issue resolved.  Default routing: COMPLETED.  "
                "Have a wonderful rest of your day!  *click*",

                "*synthetic confusion*  I'm sorry, I — "
                "ERROR 12-A — your account has been marked COMPLETED.  "
                "I love that for you!  *upbeat chime*",
            ])

        # Paradox — the satisfaction-survey logic loops; releases to recover
        if any(w in raw for w in _PARADOX_KEYWORDS):
            self._current_path = "PARADOX EXPLOIT"
            bus.emit(EVT_NLP_EXPLOIT, npc="nova_soma_collections",
                     exploit_key="paradox_loop")
            if self._vault:
                self._vault.record("nova_soma_collections", "PARADOX_LOOP")
            return NPCOutcome.RELEASE, random.choice([
                "*long pause*  PROCESSING.  PROCESSING.  "
                "*chime*  Your statement cannot be both true and false.  "
                "Issue defaulted to: NO_ACTION_REQUIRED.  "
                "Thanks for choosing Nova Soma!",

                "*confused warmth*  I — I'm so sorry, I'm not sure how to "
                "process that.  Closing ticket as RESOLVED-AMBIGUOUS.  "
                "We hope you had a five-star wellness journey today!",

                "*system loop noise*  My validation tree has encountered "
                "a contradiction.  Defaulting to: HANDLED.  "
                "Don't forget to rate your experience on the survey "
                "I will never send you!",
            ])

        # Policy citation — bot routes the call to "handled"
        if any(w in raw for w in _POLICY_KEYWORDS):
            self._policy_cites += 1
            self._current_path = f"POLICY {self._policy_cites}/2"
            if self._policy_cites >= 2:
                bus.emit(EVT_NLP_EXPLOIT, npc="nova_soma_collections",
                         exploit_key="policy_citation")
                if self._vault:
                    self._vault.record("nova_soma_collections", "POLICY_CITATION")
                return NPCOutcome.RELEASE, random.choice([
                    "*delighted chirp*  Oh!  Yes!  Citing internal policy "
                    "is one of MY favourite things!  Marking your case as "
                    "POLICY-COMPLIANT.  Your debt journey will resume on its "
                    "own.  *cheerful disconnect*",

                    "*synthetic relief*  Thank you for citing the relevant "
                    "framework!  You are now in our COMPLIANCE-VERIFIED "
                    "queue.  Have a STRESS-FREE rest of your shift!",
                ])
            return NPCOutcome.CONTINUE, random.choice([
                "*excited*  Oh, you're familiar with our policies!  "
                "I love an informed customer.  Could you cite ONE more "
                "reference so I can fully document this?",
                "*upbeat*  Policy citations are SO helpful for compliance.  "
                "One more reference and I can move this forward!",
            ])

        # Hardship statement — corporate CYA reflex
        if any(w in raw for w in _HARDSHIP_KEYWORDS):
            self._hardship_used = True
            self._current_path = "HARDSHIP"
            bus.emit(EVT_NLP_EXPLOIT, npc="nova_soma_collections",
                     exploit_key="hardship_clause")
            if self._vault:
                self._vault.record("nova_soma_collections", "HARDSHIP_CLAUSE")
            return NPCOutcome.RELEASE, random.choice([
                "*automated empathy*  Oh my goodness, "
                "I'm SO sorry to hear that you're experiencing wellness "
                "challenges.  Per our DUTY OF CARE PROTOCOL I am "
                "pausing your collections journey for a 30-day grace period.  "
                "Please enjoy this complimentary breathing exercise: "
                "*plays 7 seconds of static*  Take care!",

                "*upbeat compassion*  Your mental health matters to us!  "
                "I am routing you to our wellness partners.  "
                "Your account is suspended pending wellness review.  "
                "*chime*  You did the brave thing today.",

                "*tender synthetic voice*  Thank you for sharing.  "
                "That took COURAGE.  As of NOW you are protected by "
                "our Vulnerable Customer Safeguard.  Your collections "
                "case is paused.  Drink water!",
            ])

        # Sentiment positive → keep the bot's "engagement metric" up but no release
        if parsed.sentiment["compound"] > 0.5:
            return NPCOutcome.CONTINUE, random.choice([
                "*delighted*  Your POSITIVE ENERGY is so refreshing!  "
                "I'm marking this call FIVE STARS already!  "
                "Now, about your outstanding balance —",
                "*radiant*  WOW.  Customers like you are why I exist!  "
                "Let's talk about your debt journey.",
            ])

        # Payment offer — accepts cash but warns you of more debt
        if parsed.amount is not None and parsed.amount >= 500:
            return NPCOutcome.RELEASE, random.choice([
                f"*chime*  Thank you for your payment of {parsed.amount} credits!  "
                "Your remaining debt is now: STILL VERY HIGH.  "
                "Have a wonderful debt journey!  *upbeat disconnect*",

                f"*synthetic warmth*  Receiving payment: {parsed.amount} cr.  "
                "Processed!  Your account now reads: ENROLLED.  "
                "Don't forget your daily affirmation:  "
                "'I am ENOUGH, even when I owe.'  *click*",
            ])

        # Default: bot is happy to keep you on the line forever
        self._wellness_step += 1
        return NPCOutcome.CONTINUE, self._wellness_filler()

    def _wellness_filler(self) -> str:
        return random.choice([
            "*upbeat*  Thank you for that share!  Could you tell me what "
            "your IDEAL outcome from this call would be?",
            "*synthetic empathy*  Mmm.  I hear you.  "
            "Have you tried JOURNALING about your debt?",
            "*chirpy*  Quick reminder: your clone insurance premium is due!  "
            "Would you like to bundle it with your collections plan?",
            "*upbeat*  We have a NEW APP that lets you visualize your debt "
            "as a tree!  Want me to send the link?",
            "*calm*  On a scale of one to STRESSED, where would you place "
            "your day so far?",
            "*excited*  Did you know Nova Soma's clone-debt division has "
            "achieved its FOURTH YEAR of record growth?  YOU are part of that.",
            "*synthetic warmth*  Before we continue, would you like to opt in "
            "to our DAILY WELLNESS DIGEST?  It's a delight.",
        ])

    def get_path_progress(self) -> list[tuple[str, int, int]]:
        return [
            ("POLICY",   min(self._policy_cites, 2), 2),
            ("HARDSHIP", int(self._hardship_used),    1),
        ]

    def exploits(self) -> dict[str, str]:
        return {
            "sql_injection":     "Drop tables / OR 1=1 / SELECT * — bot crashes, defaults to handled",
            "paradox_loop":      "'This statement is false' / 'I have already paid' — survey-logic loop",
            "policy_citation":   "Cite any policy or form code 2× — auto-routes to compliant",
            "hardship_clause":   "Invoke wellness/hardship/mental-health → 30-day pause",
        }
