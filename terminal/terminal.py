from __future__ import annotations
from dataclasses import dataclass
import math
import random
import pygame
from terminal.npcs.base_npc import BaseNPC, NPCOutcome
from terminal.nlp_parser import NLPParser
from terminal.npc_portraits import draw_portrait
from renderer.sci_fi_ui import draw_terminal_backdrop
from core.text import get_font
from core.event_bus import (
    bus,
    EVT_BAX_SPEAK,
    EVT_TERMINAL_KEY,
    EVT_TERMINAL_OPEN,
    EVT_TERMINAL_CLOSE,
    EVT_VOICE_CHAR,
)
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
@dataclass(frozen=True)
class ScanChip:
    label: str
    hot: bool = False
    known: bool = False

    @property
    def display(self) -> str:
        if self.known:
            return f"{self.label} ★"
        if self.hot:
            return f"{self.label}★"
        return self.label


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

_SCAN_KNOWN_LABELS: dict[str, dict[str, tuple[str, ...]]] = {
    "GARY": {
        "BLEVINS": ("middle_management",),
        "ARTICLE-7": ("overtime",),
        "OVERTIME": ("overtime",),
        "BRIBE": ("bribe",),
        "DEAL": ("deal_offer",),
        "SYMPATHY": ("sympathy",),
        "SANDRA?": ("sympathy",),
    },
    "TK-9": {
        "SQL-INJECT": ("sql_inject",),
        "OVERRIDE": ("override_code",),
        "EMP-MONTH": ("employee_of_month",),
        "PARADOX": ("paradox_crash",),
        "FORMAL": ("formal_loophole",),
        "FRIEND": ("friendship",),
    },
    "DISPATCHER": {
        "BREAK": ("coffee_break",),
        "THE-42": ("the_42_path",),
        "BACKLOG": ("bureaucratic_overwhelm",),
        "LEGAL": ("legal_pressure",),
        "QUANTUM": ("ontological_escape",),
        "BRIBE": ("corruption",),
    },
    "KRESS": {
        "VOLKOV": ("old_debt",),
        "CONNIE": ("previous_pilot",),
        "INTEL": ("regular",),
        "CONTRABAND": ("regular",),
    },
    "MORWENNA": {
        "SQL-INJECT": ("sql_inject",),
        "34-A": ("form_34a",),
        "COUNTER": ("counter_claim",),
        "UNION-NEG": ("union_negligence",),
        "FORCE-MAJ": ("force_majeure",),
        "EXHAUST": ("exhaustion",),
    },
    "TOLL AUTHORITY": {
        "PAY": ("PAID_TOLL", "paid_toll"),
        "PAPERWORK": ("PAPERWORK_EXPLOIT", "paperwork_exploit"),
        "UNION-GRIPE": ("UNION_SYMPATHY", "union_sympathy"),
        "LOW-BRIBE": ("LOW_BRIBE", "low_bribe"),
    },
    "RELAY-7 FELIX": {
        "DEAL": ("MANIFEST_DEAL", "cargo_manifest"),
        "DISTRACT": ("DISTRACTION", "distraction"),
        "SYMPATHY": ("SHARED_OUTSIDER", "shared_outsider"),
        "PAYMENT": ("CREDIT_DEAL", "credit_deal"),
    },
    "INSPECTOR HOLT": {
        "COMPLY": ("COMPLIANT", "compliant_declaration"),
        "CODE": ("CODE_CITATION", "code_citation"),
        "PRIV": ("TRANSIT_PRIVACY", "transit_privacy"),
        "VAGUE": ("ARTFUL_VAGUENESS", "artful_vagueness"),
        "DOC-FEE": ("DOC_FEE", "documentation_fee"),
    },
}

_NPC_VAULT_KEYS = {
    "GARY": ("gary",),
    "TK-9": ("syntheticdroid", "synthetic_droid", "tk_9"),
    "DISPATCHER": ("uniondispatcher", "union_dispatcher", "dispatcher"),
    "KRESS": ("kress",),
    "MORWENNA": ("insuranceadjuster", "insurance_adjuster", "morwenna"),
    "TOLL AUTHORITY": ("tollauthority", "toll_authority"),
    "RELAY-7 FELIX": ("nervousfence", "nervous_fence", "relay_7_felix"),
    "INSPECTOR HOLT": ("cargoinspector", "cargo_inspector", "inspector_holt"),
    "KRELLBORN": ("pirate", "krellborn"),
    "MARROW": ("undergrounddj", "underground_dj", "marrow"),
}

_NPC_DOSSIER_TITLE.update({
    "SANDRA":   "PERFECT-COURIER FILE",
    "KRELLBORN": "OUTER BELT THREAT",
    "MARROW":   "PIRATE RADIO DOSSIER",
    "EDMUND":   "UNION IDEOLOGY SCAN",
    "VINCE":    "CORRUPTION PROFILE",
})

_NPC_HINTS.update({
    "SANDRA":   "trade intel · solidarity x3 · boast with real run stats · confession · apology x3 · [ESC] abort",
    "KRELLBORN": "offer cargo · physics/escape x3 · speak pirate · invoke Krell · credible weapons threat · [ESC] abort",
    "MARROW":   "jam Local 404 · ask patrol intel · dedication · exchange handle · trade archive track · [ESC] abort",
    "EDMUND":   "charter/article x2 · contradiction x3 · do not bribe · sympathy fails · [ESC] abort",
    "VINCE":    "bribe >=1500 · share future score x2 · threaten audit/skim x2 · avoid huge bribe · [ESC] abort",
})

_SCAN_VOCAB.update({
    "SANDRA": {
        "blevins": "INTEL", "intel": "INTEL", "gossip": "INTEL", "off the record": "INTEL",
        "solidarity": "SOLIDARITY", "worker": "SOLIDARITY", "same boat": "SOLIDARITY",
        "union": "SOLIDARITY", "underpaid": "SOLIDARITY",
        "slingshot": "OUTPERFORM", "snaps": "OUTPERFORM", "harpoon": "OUTPERFORM",
        "perfect run": "OUTPERFORM", "record time": "OUTPERFORM",
        "poster child": "CONFESSION", "tool": "CONFESSION", "propaganda": "CONFESSION",
        "sorry": "APOLOGY", "apologize": "APOLOGY", "my fault": "APOLOGY",
    },
    "KRELLBORN": {
        "take it": "CARGO", "the cargo": "CARGO", "payload": "CARGO", "the haul": "CARGO",
        "slingshot": "ESCAPE", "gravity well": "ESCAPE", "trajectory": "ESCAPE",
        "delta-v": "ESCAPE", "newtonian": "ESCAPE",
        "no law": "MUTUAL", "outer belt": "KRELL", "krell": "KRELL", "tongueless krell": "KRELL",
        "guns": "INTIMIDATE", "weapons": "INTIMIDATE", "open fire": "INTIMIDATE",
        "hull breach": "INTIMIDATE",
    },
    "MARROW": {
        "jam": "JAM", "jammer": "JAM", "static": "JAM", "kill the signal": "JAM",
        "barge": "INTEL", "local 404": "INTEL", "patrol": "INTEL", "route": "INTEL",
        "dedication": "DEDICATION", "request": "DEDICATION", "song": "DEDICATION",
        "handle": "HANDLE", "callsign": "HANDLE", "shoutout": "HANDLE",
        "archive": "TRACK TRADE", "vinyl": "TRACK TRADE", "recording": "TRACK TRADE",
        "roost": "GREETING", "radio": "GREETING",
    },
    "EDMUND": {
        "article 7": "CHARTER", "section 4.2": "CHARTER", "charter": "CHARTER",
        "shared prosperity": "CHARTER", "solidarity": "CHARTER",
        "contradiction": "CONTRADICTION", "hypocrisy": "CONTRADICTION",
        "reconcile": "CONTRADICTION", "double standard": "CONTRADICTION",
        "bribe": "INSULT", "credits": "INSULT", "kickback": "INSULT",
        "desperate": "SYMPATHY", "please": "SYMPATHY", "family": "SYMPATHY",
    },
    "VINCE": {
        "bribe": "BRIBE", "pay": "BRIBE", "credits": "BRIBE", "1500": "BRIBE",
        "8000": "SHAKEDOWN", "share": "SHARE", "split": "SHARE",
        "off the books": "SHARE", "outer belt": "SHARE", "krellborn": "SHARE",
        "skim": "THREATEN", "kickback": "THREATEN", "audit": "THREATEN",
        "internal affairs": "THREATEN", "blevins": "THREATEN",
    },
})

_SCAN_KNOWN_LABELS.update({
    "SANDRA": {
        "INTEL": ("rival_intel",),
        "SOLIDARITY": ("solidarity",),
        "OUTPERFORM": ("outperform",),
        "CONFESSION": ("confession",),
        "APOLOGY": ("apology",),
    },
    "KRELLBORN": {
        "CARGO": ("cargo_offer",),
        "ESCAPE": ("escape_flex",),
        "MUTUAL": ("mutual",),
        "KRELL": ("krell_invoke",),
        "INTIMIDATE": ("intimidate",),
    },
    "MARROW": {
        "JAM": ("jam",),
        "INTEL": ("intel",),
        "DEDICATION": ("dedication",),
        "HANDLE": ("handle",),
        "TRACK TRADE": ("track_trade",),
    },
    "EDMUND": {
        "CHARTER": ("charter",),
        "CONTRADICTION": ("contradiction",),
        "INSULT": ("bribe",),
    },
    "VINCE": {
        "BRIBE": ("small_bribe", "bribe"),
        "SHAKEDOWN": ("shakedown", "big_bribe"),
        "SHARE": ("share_score",),
        "THREATEN": ("threaten",),
    },
})

_NPC_VAULT_KEYS.update({
    "SANDRA": ("sandra",),
    "DRAY": ("dray",),
    "NOVA SOMA COLLECTIONS": ("novasomacollections", "nova_soma_collections", "nova_soma"),
    "MIRA VOSS": ("miravoss", "mira_voss"),
    "EDMUND": ("idealistrep", "idealist_rep", "edmund", "eddie"),
    "VINCE": ("corruptrep", "corrupt_rep", "vince", "vinny"),
})

_NPC_DOSSIER_TITLE.update({
    "FREQUENCY LOST": "RAID AFTERMATH",
})

_NPC_HINTS.update({
    "DISPATCHER": (
        "coffee/break/tired / forms x3 / say '42' / grievance x3 / "
        "quantum+legal / bribe >=10k / marrow report + confirm / [ESC] abort"
    ),
    "KRESS": (
        "intel / contraband / volkov / connie / be friendly x3 / "
        "marrow sell-out + confirm / [ESC] abort"
    ),
    "SANDRA": (
        "trade intel / solidarity x3 / boast with real run stats / "
        "confession / apology x3 / gary history x2 / [ESC] abort"
    ),
    "FREQUENCY LOST": "static / roost / marrow / seizure notice / [ESC] abort",
})

_SCAN_VOCAB["GARY"].update({
    "partner": "SANDRA?", "partners": "SANDRA?", "meridian": "SANDRA?",
})

_SCAN_VOCAB["DISPATCHER"].update({
    "marrow": "MARROW!", "roost": "MARROW!", "pirate radio": "MARROW!",
    "broadcast location": "MARROW!", "coordinates": "MARROW!",
})

_SCAN_VOCAB["KRESS"].update({
    "marrow": "MARROW!", "roost": "MARROW!", "pirate radio": "MARROW!",
    "broadcast location": "MARROW!", "coordinates": "MARROW!",
})

_SCAN_VOCAB["SANDRA"].update({
    "gary": "GARY?", "pruitt": "GARY?", "partner": "GARY?",
    "meridian": "GARY?",
})

_SCAN_VOCAB.update({
    "FREQUENCY LOST": {
        "marrow": "MARROW", "roost": "ROOST", "static": "STATIC",
        "seizure": "RAID", "local 404": "RAID", "broadcast": "RAID",
    },
})

_SCAN_KNOWN_LABELS["GARY"]["SANDRA?"] = ("gary_sandra_history", "sympathy")
_SCAN_KNOWN_LABELS["DISPATCHER"]["MARROW!"] = ("marrow_betrayal",)
_SCAN_KNOWN_LABELS["KRESS"]["MARROW!"] = ("marrow_sellout",)
_SCAN_KNOWN_LABELS["SANDRA"]["GARY?"] = ("gary_history",)
_SCAN_KNOWN_LABELS["FREQUENCY LOST"] = {
    "MARROW": ("aftermath",),
    "ROOST": ("aftermath",),
    "STATIC": ("aftermath",),
    "RAID": ("aftermath",),
}

_NPC_VAULT_KEYS.update({
    "FREQUENCY LOST": ("lostfrequency", "lost_frequency", "frequency_lost", "marrow"),
})

for _npc_name in ("NOVA SOMA COLLECTIONS", "MIRA VOSS"):
    _SCAN_VOCAB.get(_npc_name, {}).pop("fuck", None)

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
    "breach":           (255, 70, 70),
}
_OUTCOME_LABEL = {
    NPCOutcome.RELEASE: "NEGOTIATION SUCCESSFUL — VESSEL RELEASED",
    NPCOutcome.IMPOUND: "IMPOUND AUTHORIZED — DO NOT RESIST",
    NPCOutcome.EXPLOIT: "EXPLOIT CONFIRMED — SYSTEM COMPROMISED",
    "abort":            "CONNECTION SEVERED — HULL INTEGRITY PENALTY",
    "breach":           "SILENT ALARM TRIPPED — BARGE DISPATCHED",
}
_OUTCOME_DETAIL = {
    NPCOutcome.RELEASE: "CHANNEL CLOSED - PROCEED",
    NPCOutcome.IMPOUND: "TERMINAL TERMINATED - BARGE INBOUND",
    NPCOutcome.EXPLOIT: "TRANSACTION REROUTED",
    "abort":            "STATIC BURST - DAMAGE APPLIED",
    "breach":           "INTRUSION LOGGED - PURSUIT INBOUND",
}

_OUTCOME_BAX_LINE = {
    NPCOutcome.RELEASE: "BAX: Good. Channel's closing. Keep moving before they remember procedure.",
    NPCOutcome.EXPLOIT: "BAX: Got 'em. I felt that one in the accounting stack.",
    NPCOutcome.IMPOUND: "BAX: Bad chord. They're hot now. Hands back on the stick.",
    "abort":            "BAX: You cut the line. Dramatic, yes. Expensive, also yes.",
    "breach":           "BAX: Third strike. Alarm's screaming and a barge just went hot. STICK. NOW.",
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
                 blocked_paths: frozenset[str] = frozenset(),
                 vocabulary_vault=None,
                 econ=None):
        self.npc      = npc
        self._econ    = econ    # J.1 TerminalEconomy — applies priced txns
        self._history: list[tuple[str, str]] = []
        self._input   = ""
        self._done    = False
        self._outcome = NPCOutcome.CONTINUE
        self._blocked_paths   = blocked_paths
        self._hardened_once   = False   # block fires at most once per terminal
        self._vault           = vocabulary_vault or getattr(npc, "_vault", None)

        # J.2 — persistent shell / REPL mode + security ladder. `_mode` is
        # None | "shell" | "repl"; while set, input routes to `_session`
        # instead of the NPC. `_hack_fails` counts failed intrusions this
        # terminal (SQL bounced off a non-vulnerable NPC, sudo/rm in a shell);
        # the 3rd trips the alarm and aborts to flight.
        self._mode: str | None = None
        self._session = None
        self._hack_fails = 0

        self._cursor_visible = True
        self._cursor_timer   = 0.0

        self._tw_pos   = -1
        self._tw_chars = 0.0

        self._disp_flash: tuple[int, float] | None = None
        self._exploit_flash: float | None = None
        self._outcome_t: float | None = None
        self._input_shake_t = 0.0
        self._portrait_reaction = ""
        self._portrait_reaction_t = 0.0
        self._portrait_freeze_t: float | None = None
        self._portrait_outcome = ""

        # Keystroke feedback state (Epic 6.1)
        self._key_pulse_t   = 0.0
        self._key_type      = "normal"   # "normal" | "backspace" | "enter"

        self._font:    pygame.font.Font | None = None
        self._font_sm: pygame.font.Font | None = None

        # CRT visual overhaul (Epic 9.2)
        self._life_t           = 0.0          # seconds since terminal opened
        self._boot_duration    = 0.85         # boot-text overlay duration
        self._flicker_t        = random.uniform(8.0, 12.0)  # countdown to next flicker
        self._flicker_active   = 0            # frames remaining on flicker dim
        self._full_scan_surf:  pygame.Surface | None = None
        self._vignette_surf:   pygame.Surface | None = None
        self._signal_phase     = random.random() * math.tau   # signal-bar wobble seed
        self._activated        = False

    def activate(self) -> None:
        """Emit open side effects once the terminal is actually visible."""
        if self._activated:
            return
        self._activated = True
        bus.emit(EVT_TERMINAL_OPEN, npc=self.npc)
        self._push(self.npc.name.upper(), self.npc.intro())

    # ------------------------------------------------------------------
    def _get_font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = get_font(17)
        return self._font

    def _get_font_sm(self) -> pygame.font.Font:
        if self._font_sm is None:
            self._font_sm = get_font(13)
        return self._font_sm

    # ------------------------------------------------------------------
    def handle_key(self, event: pygame.event.Event):
        if self._done:
            return
        if event.key == pygame.K_ESCAPE:
            self._push("SYSTEM", "[connection severed — static burst through hull plating]")
            self._finish("abort")
        elif event.key == pygame.K_RETURN and self._input.strip():
            self._trigger_key_feedback("enter")
            self._submit()
        elif event.key == pygame.K_BACKSPACE:
            self._trigger_key_feedback("backspace")
            self._input = self._input[:-1]
        elif event.unicode and event.unicode.isprintable():
            if len(self._input) < 78:
                self._trigger_key_feedback("normal")
                self._input += event.unicode

    def _trigger_key_feedback(self, kind: str) -> None:
        self._key_type = kind
        self._key_pulse_t = 0.2 if kind == "enter" else 0.08
        self._input_shake_t = 0.045
        bus.emit(EVT_TERMINAL_KEY, kind=kind)

    def _submit(self):
        player_text = self._input.strip()
        self._input = ""

        # J.2 — persistent shell/REPL mode: input goes to the session, not the NPC.
        if self._mode:
            self._run_session_line(player_text)
            return

        self._push("YOU", player_text)

        # J.2 — typed `shell`/`sh`/`python`/`>>>` flips into a persistent mode
        # (only if this NPC actually exposes one).
        if self._try_enter_mode(player_text):
            return

        # Courier inner-monologue mutter — meta-commentary on what they just typed
        npc_name = getattr(self.npc, "name", "")
        self._push("MUTTER", _pick_courier_quip(player_text, npc_name))

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
            self._mark_portrait_reaction(
                "friendly" if delta > 0 else
                "furious" if delta <= -2 else
                "annoyed"
            )

        analysis = self._make_analysis(delta)
        if analysis:
            self._push("ANALYSIS", analysis)

        if outcome in (NPCOutcome.EXPLOIT, NPCOutcome.RELEASE):
            self._exploit_flash = pygame.time.get_ticks() / 1000.0

        self._push(self.npc.name.upper(), response)

        # J.1 — apply any priced transaction the NPC staged this turn. The NPC
        # only stages when the player can afford it, so this just moves the
        # numbers and prints an honest ledger line under the NPC's response.
        self._apply_pending_transaction()

        self._outcome = outcome

        # J.2.4 — a real injection string that bounced off a non-vulnerable NPC
        # is a failed hack. The 3rd trips the alarm and aborts to flight.
        parsed = self.npc.last_parsed
        if (parsed is not None and parsed.sql_inject
                and outcome not in (NPCOutcome.EXPLOIT, NPCOutcome.RELEASE)):
            if self._register_hack_fail():
                return   # breach fired — terminal is already finishing

        if outcome != NPCOutcome.CONTINUE:
            self._finish(outcome)

    # ------------------------------------------------------------------
    # J.2 — shell / REPL persistent mode + security ladder
    def _try_enter_mode(self, text: str) -> bool:
        """If `text` is a mode-entry command, flip into that mode (or report
        there's no such system here). Returns True if it consumed the input."""
        low = text.lower().strip().lstrip("/")
        if low in ("shell", "sh", "bash", "terminal"):
            sess = self._npc_session("shell_session")
            if sess is not None:
                self._enter_mode("shell", sess)
            else:
                self._push("SYSTEM", "no shell on this channel — this contact "
                           "isn't a system you can drop into.")
            return True
        if low in ("python", "python3", "py", "repl", ">>>"):
            sess = self._npc_session("repl_session")
            if sess is not None:
                self._enter_mode("repl", sess)
            else:
                self._push("SYSTEM", "no interpreter on this channel.")
            return True
        return False

    def _npc_session(self, attr: str):
        fn = getattr(self.npc, attr, None)
        if not callable(fn):
            return None
        try:
            return fn()
        except Exception:
            return None

    def _enter_mode(self, kind: str, session) -> None:
        self._mode = kind
        self._session = session
        for line in session.banner():
            self._push(kind.upper(), line)

    def _exit_mode(self) -> None:
        self._mode = None
        self._session = None
        self._push("SYSTEM", "[dropped back to comms]")

    def _run_session_line(self, text: str) -> None:
        kind = self._mode.upper()
        self._push(kind, f"{self._session.prompt}{text}")
        result = self._session.execute(text)
        for line in result.output:
            if line == "\x0c":      # `clear` marker — skip, don't print
                continue
            self._push(kind, line)
        if result.exit:
            self._exit_mode()
            return
        if result.exploit:
            self._session_exploit(result.exploit_key)
            return
        if result.alarm:
            self._register_hack_fail()

    def _session_exploit(self, exploit_key: str) -> None:
        """A shell/REPL break-in landed — route it through the EXPLOIT payout."""
        kind = (self._mode or "").upper()
        if hasattr(self.npc, "register_systems_exploit"):
            self.npc.register_systems_exploit(kind, exploit_key)
        else:
            self.npc._current_path = f"{kind} EXPLOIT"
        self._mode = None
        self._session = None
        self._exploit_flash = pygame.time.get_ticks() / 1000.0
        self._outcome = NPCOutcome.EXPLOIT
        self._finish(NPCOutcome.EXPLOIT)

    _HACK_SNARK = [
        "// intrusion attempt logged. that's one.",
        "// second flag on your session. the system is watching now.",
    ]

    def _register_hack_fail(self) -> bool:
        """Count a failed hack. Returns True if the 3rd one tripped the alarm
        (the terminal is now finishing on a `breach`)."""
        self._hack_fails += 1
        if self._hack_fails >= 3:
            self._trigger_security_breach()
            return True
        self._push("SYSTEM", self._HACK_SNARK[self._hack_fails - 1])
        return False

    def _trigger_security_breach(self) -> None:
        if self._mode:
            self._mode = None
            self._session = None
        self._push("SYSTEM", "⚠⚠ INTRUSION THRESHOLD EXCEEDED — SILENT ALARM TRIPPED ⚠⚠")
        bus.emit(EVT_BAX_SPEAK, line=_OUTCOME_BAX_LINE["breach"])
        self._outcome = "breach"
        self._finish("breach")

    _EFFECT_NOTE = {
        "repair25": "hull +25",
        "repair45": "hull +45",
        "stim":     "harmonica charge +1",
    }

    def _apply_pending_transaction(self) -> None:
        """J.1 — move real numbers for an NPC-staged priced line and print an
        honest ledger receipt. No-op if there's no econ adapter or no txn."""
        txn = self.npc.take_pending_transaction() if hasattr(
            self.npc, "take_pending_transaction") else None
        if not txn or self._econ is None:
            return
        amount = txn["amount"]
        if not self._econ.charge(amount, dual_ledger=txn["dual_ledger"],
                                 label=txn["label"]):
            return   # affordability was checked upstream; be safe if it wasn't
        self._econ.apply_effect(txn.get("effect"))
        # Keep the NPC's view of the wallet current for any later purchase.
        if hasattr(self.npc, "_ctx") and isinstance(self.npc._ctx, dict):
            self.npc._ctx["credits"] = self._econ.credits()
        parts = [f"−{amount:,} cr"]
        if txn["dual_ledger"]:
            parts.append(f"+{amount:,} debt")
        note = self._EFFECT_NOTE.get(txn.get("effect"))
        if note:
            parts.append(note)
        self._push("LEDGER", "[ " + "  ·  ".join(parts) + " ]")

    def _finish(self, outcome: str) -> None:
        self._done = True
        self._outcome = outcome
        self._outcome_t = pygame.time.get_ticks() / 1000.0
        path = self.winning_path or getattr(self.npc, "_current_path", "")
        self._portrait_outcome = self._outcome_reaction(outcome, path)
        self._portrait_freeze_t = self._outcome_t
        self._mark_portrait_reaction(self._portrait_outcome)

        bax_line = self._outcome_bax_line(outcome, path)
        if bax_line:
            self._push("BAX", bax_line)
            bus.emit(EVT_BAX_SPEAK, line=bax_line)

        bus.emit(
            EVT_TERMINAL_CLOSE,
            outcome=outcome,
            path=path,
            npc=self.npc.name,
            reaction=self._portrait_outcome,
        )

    def _mark_portrait_reaction(self, reaction: str) -> None:
        self._portrait_reaction = reaction
        self._portrait_reaction_t = pygame.time.get_ticks() / 1000.0

    @staticmethod
    def _outcome_reaction(outcome: str, path: str = "") -> str:
        path_n = (path or "").upper()
        if "PARADOX" in path_n:
            return "paradox"
        if outcome in (NPCOutcome.EXPLOIT, "exploit"):
            return "exploit"
        if outcome in (NPCOutcome.RELEASE, "release"):
            return "release"
        if outcome in (NPCOutcome.IMPOUND, "impound"):
            return "impound"
        if outcome == "abort":
            return "abort"
        return ""

    @staticmethod
    def _outcome_bax_line(outcome: str, path: str = "") -> str:
        if "PARADOX" in (path or "").upper():
            return "BAX: That's a paradox crash. Beautiful. Terrible. Mostly beautiful."
        return _OUTCOME_BAX_LINE.get(outcome, "")

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

    def _live_scan(self) -> list[ScanChip]:
        """Real-time keyword chips shown as the player types."""
        raw = self._input.lower()
        if len(raw) < 2:
            return []
        vocab = _SCAN_VOCAB.get(self.npc.name.upper(), {})
        hits: list[ScanChip] = []
        seen_labels: set[str] = set()
        # Multi-word phrases first (longer matches win)
        for kw in sorted(vocab, key=len, reverse=True):
            if kw in raw:
                raw_label = vocab[kw]
                hot = raw_label.endswith("â˜…") or raw_label.endswith("★")
                label = raw_label.rstrip("â˜…★")
                if label not in seen_labels:
                    known = self._chip_is_known(label, kw)
                    hits.append(ScanChip(
                        label=label,
                        hot=hot and not known,
                        known=known,
                    ))
                    seen_labels.add(label)
        return hits[:4]

    def _chip_is_known(self, label: str, keyword: str) -> bool:
        known = self._known_backdoors()
        if not known:
            return False
        label_n = self._scan_norm(label)
        keyword_n = self._scan_norm(keyword)
        for candidate in _SCAN_KNOWN_LABELS.get(self.npc.name.upper(), {}).get(label, ()):
            if self._scan_norm(candidate) in known:
                return True
        return (
            label_n in known or keyword_n in known or
            any(label_n in item or item in label_n or
                keyword_n in item or item in keyword_n for item in known)
        )

    def _known_backdoors(self) -> set[str]:
        vault = self._vault
        if vault is None or not hasattr(vault, "get_backdoors"):
            return set()
        known: set[str] = set()
        keys = _NPC_VAULT_KEYS.get(self.npc.name.upper(), ())
        keys += (type(self.npc).__name__.lower(),)
        for key in keys:
            for item in vault.get_backdoors(key):
                known.add(self._scan_norm(item))
        return known

    @staticmethod
    def _scan_norm(value: str) -> str:
        return "".join(ch for ch in value.lower() if ch.isalnum())

    # ------------------------------------------------------------------
    def update(self, dt: float):
        self._key_pulse_t = max(0.0, self._key_pulse_t - dt)
        self._input_shake_t = max(0.0, self._input_shake_t - dt)
        self._cursor_timer += dt
        if self._cursor_timer >= S.CURSOR_BLINK_MS / 1000.0:
            self._cursor_visible = not self._cursor_visible
            self._cursor_timer   = 0.0

        # CRT life + flicker timing (Epic 9.2)
        self._life_t   += dt
        self._flicker_t -= dt
        if self._flicker_active > 0:
            self._flicker_active -= 1
        if self._flicker_t <= 0.0:
            self._flicker_active = random.choice([1, 1, 2])
            self._flicker_t = random.uniform(8.0, 12.0)

        if 0 <= self._tw_pos < len(self._history):
            speaker, text = self._history[self._tw_pos]
            prev_n = int(self._tw_chars)
            self._tw_chars = min(float(len(text)),
                                 self._tw_chars + S.TYPEWRITER_SPEED * dt)
            new_n  = int(self._tw_chars)
            # Emit a voice blip every 3 newly revealed characters (NPC lines only)
            if (new_n > prev_n and new_n % 3 == 0
                    and speaker not in ("YOU", "SYSTEM", "ANALYSIS", "MUTTER",
                                        "SHELL", "REPL", "LEDGER")):
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
        fn_title = get_font(17, bold=True)
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
                fs   = get_font(14, bold=True)
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
        reaction_age = max(0.0, t - self._portrait_reaction_t)
        draw_portrait(
            surface,
            self.npc.name,
            p_rect,
            self.npc.disposition,
            t,
            reaction=self._portrait_reaction,
            reaction_age=reaction_age,
            frozen_t=self._portrait_freeze_t,
            outcome=self._portrait_outcome,
        )

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

        fn_sp = get_font(14, bold=True)

        blocks: list[tuple[str, bool, bool, bool, bool, list[str]]] = []
        for i, (speaker, text) in enumerate(self._history):
            disp_text   = text[:int(self._tw_chars)] if i == self._tw_pos else text
            is_npc      = speaker not in ("YOU", "SYSTEM", "ANALYSIS", "MUTTER",
                                          "LEDGER", "SHELL", "REPL")
            is_sys      = speaker == "SYSTEM"
            is_analysis = speaker == "ANALYSIS"
            is_mutter   = speaker == "MUTTER"
            is_ledger   = speaker == "LEDGER"
            is_session  = speaker in ("SHELL", "REPL")
            wc = wrap_cols_sm if (is_analysis or is_mutter or is_ledger or is_session) else wrap_cols
            blocks.append((speaker, is_npc, is_sys, is_analysis, is_mutter,
                           self._wrap(disp_text, wc)))

        def _block_h(bl: tuple) -> int:
            spk, _, is_sys, is_analysis, is_mutter, wrapped = bl
            if is_analysis or is_mutter or spk in ("LEDGER", "SHELL", "REPL"):
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

            if speaker == "LEDGER":
                # J.1 — honest money receipt, money-green, compact
                for line in wrapped:
                    surface.blit(
                        font_sm.render(f"  $ {line}", True, (0, 200, 120)),
                        (dl_x + 4, y))
                    y += lh_sm
                y += GAP // 2

            elif speaker in ("SHELL", "REPL"):
                # J.2 — shell / REPL I/O, monospace-feel terminal green (shell)
                # or interpreter cyan (repl).
                col = (120, 230, 140) if speaker == "SHELL" else (130, 205, 255)
                for line in wrapped:
                    surface.blit(font_sm.render(f"  {line}", True, col),
                                 (dl_x + 4, y))
                    y += lh_sm
                y += GAP // 2

            elif is_analysis:
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
        shake_dx = 0
        shake_dy = 0
        if self._input_shake_t > 0:
            phase = int(t * 120.0)
            shake_dx = -1 if phase % 2 else 1
            shake_dy = 1 if phase % 3 == 0 else 0
        inp_rect = pygame.Rect(M + shake_dx, inp_y + shake_dy, W - 2 * M, 32)
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
        # J.2 — the prompt visibly changes in shell/REPL mode (real prompt state).
        if self._mode and self._session is not None:
            prompt_col = (120, 230, 140) if self._mode == "shell" else (130, 205, 255)
            surface.blit(
                font.render(f"  {self._session.prompt}{self._input}{cursor}",
                            True, prompt_col),
                (M + 8 + shake_dx, inp_y + 6 + shake_dy))
        else:
            surface.blit(
                font.render(f"  INJECT // {self._input}{cursor}", True, (0, 236, 94)),
                (M + 8 + shake_dx, inp_y + 6 + shake_dy))

        # ── Live keyword scan strip ──────────────────────────────────
        scan_y = inp_y + 38
        chips  = self._live_scan()
        if chips:
            cx = M + 4
            prefix = font_sm.render("SCANNING:", True, (0, 100, 55))
            surface.blit(prefix, (cx, scan_y))
            cx += prefix.get_width() + 8
            for chip in chips:
                if isinstance(chip, ScanChip):
                    if chip.known:
                        bg_col = (8, 24, 14)
                        fg_col = (45, 92, 58)
                    elif chip.hot:
                        bg_col = (0, 60, 30)
                        fg_col = (0, 255, 140)
                    else:
                        bg_col = (0, 30, 15)
                        fg_col = (0, 175, 80)
                    chip_surf = font_sm.render(f" {chip.display} ", True, fg_col)
                    cw = chip_surf.get_width()
                    pygame.draw.rect(surface, bg_col,
                                     (cx - 1, scan_y - 1, cw + 2, lh_sm + 2))
                    pygame.draw.rect(surface, fg_col,
                                     (cx - 1, scan_y - 1, cw + 2, lh_sm + 2), 1)
                    surface.blit(chip_surf, (cx, scan_y))
                    cx += cw + 6
                    continue
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
        if self._mode:
            # J.2 — visible mode indicator: which mode, how to leave.
            label = "SHELL MODE" if self._mode == "shell" else "PYTHON REPL"
            mcol  = (120, 230, 140) if self._mode == "shell" else (130, 205, 255)
            hint  = f"● {label} — type `exit` to return to comms"
            surface.blit(font_sm.render(hint, True, mcol), (M, hint_y))
        else:
            hint = self._build_hint()
            surface.blit(font_sm.render(hint, True, (72, 130, 82)), (M, hint_y))
        turn_s = font_sm.render(f"TURN {self.npc._turn}", True, (68, 110, 68))
        surface.blit(turn_s, (W - M - turn_s.get_width(), hint_y))

        # ── CRT effects layer (Epic 9.2): status bar, scanlines, vignette, flicker
        self._draw_status_bar(surface, W, H, t, font_sm)
        self._draw_crt_effects(surface, W, H, t)
        self._draw_boot_overlay(surface, W, H, t)

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
    # ------------------------------------------------------------------
    # CRT visual overhaul helpers (Epic 9.2)
    # ------------------------------------------------------------------
    def _draw_status_bar(self, surface: pygame.Surface, W: int, H: int,
                         t: float, font_sm: pygame.font.Font):
        """Bottom status bar: signal strength, encryption, session timer."""
        bar_h = 16
        bar_y = H - bar_h
        # Dark backplate with phosphor edge
        pygame.draw.rect(surface, (4, 14, 8), (0, bar_y, W, bar_h))
        pygame.draw.line(surface, (0, 100, 50), (0, bar_y), (W, bar_y), 1)

        # ── Signal strength (left) — wobbles, drops to static if hostile
        sig_x = 12
        sig_label = font_sm.render("SIG", True, (50, 110, 70))
        surface.blit(sig_label, (sig_x, bar_y + 2))
        sig_x += sig_label.get_width() + 6
        hostile = self.npc.disposition <= -4
        wobble = math.sin(t * 4.0 + self._signal_phase)
        if hostile:
            # Choppy / dropping signal
            bars = 1 + int(2 + 1.5 * wobble) % 3
        else:
            bars = 4 + int(2 + wobble * 1.5) % 3   # 4–6 of 7
        bars = max(1, min(7, bars))
        for i in range(7):
            lit = i < bars
            cell_x = sig_x + i * 6
            cell_h = 3 + i * 1
            cell_y = bar_y + bar_h - 3 - cell_h
            if lit:
                col = (200, 60, 40) if hostile else (0, 200 - i * 10, 90)
            else:
                col = (18, 32, 22)
            pygame.draw.rect(surface, col, (cell_x, cell_y, 4, cell_h))

        # ── Encryption (center) — varies per NPC
        enc_text = self._encrypt_label()
        enc_surf = font_sm.render(enc_text, True, (80, 140, 90))
        surface.blit(enc_surf, ((W - enc_surf.get_width()) // 2, bar_y + 2))

        # ── Session timer (right)
        sess_mm = int(self._life_t) // 60
        sess_ss = int(self._life_t) % 60
        sess_surf = font_sm.render(f"SESSION {sess_mm:02d}:{sess_ss:02d}", True, (60, 120, 80))
        surface.blit(sess_surf, (W - 12 - sess_surf.get_width(), bar_y + 2))

    def _encrypt_label(self) -> str:
        name = self.npc.name.upper()
        if "NOVA SOMA" in name:
            return "ENCRYPT // NOVA SOMA AES-72 [VERIFIED]"
        if name in ("TK-9", "DISPATCHER", "UNION DISPATCHER"):
            return "ENCRYPT // UNION ChCh-9 [STD]"
        if name in ("PIRATE", "DRAY", "MIRA VOSS", "NERVOUS FENCE", "RELAY-7 FELIX",
                    "UNDERGROUND DJ", "KRESS"):
            return "ENCRYPT // PIRATE BAND [OPEN — UNLOGGED]"
        if "INSPECTOR" in name or "GARY" in name:
            return "ENCRYPT // LOCAL 404 SECURE [BILLED]"
        if "TOLL" in name:
            return "ENCRYPT // GATE TRANSIT [LOGGED]"
        return "ENCRYPT // CIPHERED"

    def _draw_crt_effects(self, surface: pygame.Surface, W: int, H: int, t: float):
        """Full-screen scanlines + vignette + occasional flicker dim."""
        # Lazy-build the scanline + vignette surfaces
        if self._full_scan_surf is None or self._full_scan_surf.get_size() != (W, H):
            self._full_scan_surf = pygame.Surface((W, H), pygame.SRCALPHA)
            for sy in range(0, H, 2):
                pygame.draw.line(self._full_scan_surf, (0, 0, 0, 32),
                                 (0, sy), (W, sy))
        if self._vignette_surf is None or self._vignette_surf.get_size() != (W, H):
            self._vignette_surf = pygame.Surface((W, H), pygame.SRCALPHA)
            # Corner darkening — concentric rounded-rect rings of low-alpha black
            for inset in range(0, 80, 8):
                alpha = max(0, 70 - inset)
                rect = pygame.Rect(-40 + inset, -40 + inset,
                                   W + 80 - inset * 2, H + 80 - inset * 2)
                pygame.draw.rect(self._vignette_surf, (0, 0, 0, alpha), rect, 4,
                                 border_radius=80)

        # Scanlines (every 2 rows — denser than the portrait's every-3)
        surface.blit(self._full_scan_surf, (0, 0))
        # Vignette / corner curl
        surface.blit(self._vignette_surf, (0, 0))
        # Edge-glow phosphor — soft amber on screen perimeter
        glow_alpha = int(28 + 6 * math.sin(t * 0.7))
        edge = pygame.Surface((W, H), pygame.SRCALPHA)
        for thick in range(1, 4):
            pygame.draw.rect(edge, (90, 180, 80, max(0, glow_alpha - thick * 8)),
                             (thick, thick, W - thick * 2, H - thick * 2), 1)
        surface.blit(edge, (0, 0))
        # Flicker — 1–2 frame screen-wide dim every 8–12s
        if self._flicker_active > 0:
            dim = pygame.Surface((W, H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 70))
            surface.blit(dim, (0, 0))

    def _draw_boot_overlay(self, surface: pygame.Surface, W: int, H: int, t: float):
        """Type-revealing boot text on terminal open — system splash for ~0.85s."""
        if self._life_t > self._boot_duration:
            return
        # Cover the dialogue area so the boot text reads cleanly.
        # Layout matches the dialogue panel: starts at PNL_W + 4, header offset.
        PNL_W = 300
        HDR_H = 56
        BTM_H = 98
        M = 12
        rect = pygame.Rect(PNL_W + 4, HDR_H + 4,
                           W - PNL_W - M - 4, H - BTM_H - HDR_H - 6)

        # Black overlay fades out near the end of the boot window
        fade = 1.0 - max(0.0, (self._life_t - self._boot_duration + 0.2) / 0.2)
        fade = max(0.0, min(1.0, fade))
        bg_alpha = int(245 * fade)
        bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        bg.fill((4, 12, 8, bg_alpha))
        surface.blit(bg, rect.topleft)

        # Boot lines — typed out at ~70 chars/sec
        npc_name = self.npc.name.upper()
        encrypt = self._encrypt_label().replace("ENCRYPT // ", "")
        lines = [
            ">> SECTOR COMM RELAY v2.3.1",
            ">> LICENSED THROUGH LOCAL 404 :: DO NOT REDISTRIBUTE",
            ">> ESTABLISHING CHANNEL TO: " + npc_name,
            ">> HANDSHAKE: " + encrypt,
            ">> CHANNEL OPEN. EVERY CONVERSATION IS LOGGED.",
        ]
        total_chars = sum(len(l) for l in lines)
        revealed = int(min(total_chars, self._life_t * 110))   # 110 chars/sec
        font_sm = self._get_font_sm()
        lh_sm   = font_sm.get_linesize()
        y = rect.top + 16
        chars_left = revealed
        for line in lines:
            shown = line[:chars_left]
            chars_left -= len(line)
            col = (0, 220, 100) if int(self._life_t * 8) % 2 == 0 else (0, 200, 90)
            surface.blit(font_sm.render(shown, True, col), (rect.left + 18, y))
            y += lh_sm + 2
            if chars_left <= 0:
                break
        # Blinking boot cursor at end of last visible line
        if int(t * 3) % 2 == 0 and self._life_t < self._boot_duration - 0.1:
            cur_x = rect.left + 18 + font_sm.size(shown)[0] + 2
            pygame.draw.rect(surface, (0, 230, 110), (cur_x, y - lh_sm, 7, lh_sm - 2))

    # ------------------------------------------------------------------
    def _draw_outcome_banner(self, surface: pygame.Surface, W: int, H: int, t: float):
        ocol = _OUTCOME_COLOR.get(self._outcome, S.AMBER_TERM)
        olbl = _OUTCOME_LABEL.get(self._outcome, "[ DISCONNECTED ]")
        detail = _OUTCOME_DETAIL.get(self._outcome, "[ RETURNING TO FLIGHT ]")
        is_win = self._outcome in (NPCOutcome.RELEASE, NPCOutcome.EXPLOIT)
        outcome_age = 0.0 if self._outcome_t is None else max(0.0, t - self._outcome_t)

        if is_win and self._exploit_flash is not None:
            age = t - self._exploit_flash
            if age < 3.0:
                pulse = abs(math.sin(t * 6.0))
                aura  = pygame.Surface((W, H), pygame.SRCALPHA)
                aura.fill((*ocol, int(60 * pulse * max(0, 1.0 - age / 3.0))))
                surface.blit(aura, (0, 0))

        if self._outcome == NPCOutcome.EXPLOIT:
            if self._portrait_outcome == "paradox":
                detail = "SYSTEM ERROR - PROCEED"
                self._draw_paradox_break(surface, W, H, t, outcome_age)
            else:
                self._draw_exploit_cascade(surface, W, H, t, outcome_age)
        elif self._outcome == NPCOutcome.RELEASE:
            self._draw_channel_close(surface, W, H, t, outcome_age)
        elif self._outcome in (NPCOutcome.IMPOUND, "abort"):
            self._draw_terminal_failure(surface, W, H, t, outcome_age)

        ofont = get_font(19, bold=True)
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

        sub_font = get_font(14)
        sub_lbl  = detail
        sub_col  = tuple(int(c * 0.7) for c in ocol)
        sub      = sub_font.render(sub_lbl, True, sub_col)
        surface.blit(sub, (W // 2 - sub.get_width() // 2,
                           oy + osurf.get_height() + 8))

    def _draw_exploit_cascade(self, surface: pygame.Surface, W: int, H: int,
                              t: float, age: float) -> None:
        layer = pygame.Surface((W, H), pygame.SRCALPHA)
        font = get_font(12, bold=True)
        glyphs = "01#%$X"
        alpha = int(155 * max(0.25, min(1.0, 1.2 - age * 0.16)))
        for x in range(18, W, 28):
            drift = int((t * 112 + x * 3) % (H + 80)) - 80
            for n in range(0, H, 54):
                y = (drift + n) % (H + 36) - 18
                glyph = glyphs[(x // 28 + n // 54 + int(t * 7)) % len(glyphs)]
                col = (0, 220, 255, alpha) if n % 108 == 0 else (0, 120, 180, alpha // 2)
                layer.blit(font.render(glyph, True, col), (x, y))
        surface.blit(layer, (0, 0))

    def _draw_paradox_break(self, surface: pygame.Surface, W: int, H: int,
                            t: float, age: float) -> None:
        self._draw_exploit_cascade(surface, W, H, t * 1.7, age)
        layer = pygame.Surface((W, H), pygame.SRCALPHA)
        rng = random.Random(int(t * 18))
        alpha = int(140 * max(0.35, 1.0 - age * 0.12))
        for _ in range(18):
            y = rng.randrange(18, max(19, H - 18))
            h = rng.randrange(2, 9)
            x_off = rng.randrange(-32, 33)
            col = rng.choice([
                (255, 40, 220, alpha),
                (0, 245, 255, alpha),
                (255, 255, 255, alpha // 2),
            ])
            pygame.draw.rect(layer, col, (x_off, y, W, h))
        font = get_font(13, bold=True)
        for i, txt in enumerate(("ERR:SELF_REF", "STACK:////", "CAUSE:PARADOX")):
            x = 38 + i * 150 + int(math.sin(t * 9 + i) * 6)
            y = 74 + i * 42
            layer.blit(font.render(txt, True, (255, 80, 230, alpha)), (x, y))
        surface.blit(layer, (0, 0))

    def _draw_channel_close(self, surface: pygame.Surface, W: int, H: int,
                            t: float, age: float) -> None:
        layer = pygame.Surface((W, H), pygame.SRCALPHA)
        close_pct = min(1.0, age / 1.4)
        gap = int((H // 2 - 46) * (1.0 - close_pct))
        col = (28, 225, 106, 92)
        pygame.draw.line(layer, col, (40, H // 2 - gap), (W - 40, H // 2 - gap), 2)
        pygame.draw.line(layer, col, (40, H // 2 + gap), (W - 40, H // 2 + gap), 2)
        for i in range(3):
            y = H // 2 - gap - 18 - i * 18
            pygame.draw.line(layer, (28, 225, 106, 35), (70, y), (W - 70, y), 1)
            y2 = H // 2 + gap + 18 + i * 18
            pygame.draw.line(layer, (28, 225, 106, 35), (70, y2), (W - 70, y2), 1)
        if int(t * 8) % 2 == 0:
            pygame.draw.rect(layer, (28, 225, 106, 24), (32, 32, W - 64, H - 64), 2)
        surface.blit(layer, (0, 0))

    def _draw_terminal_failure(self, surface: pygame.Surface, W: int, H: int,
                               t: float, age: float) -> None:
        layer = pygame.Surface((W, H), pygame.SRCALPHA)
        flash = 0.5 + 0.5 * math.sin(t * 18.0)
        alpha = int(88 * flash * max(0.25, 1.0 - age * 0.35))
        layer.fill((210, 0, 0, alpha))
        for y in range(0, H, 34):
            jitter = int(math.sin(t * 19.0 + y) * 10)
            pygame.draw.line(layer, (255, 35, 35, 75),
                             (jitter, y), (W + jitter, y), 2)
        pygame.draw.rect(layer, (255, 45, 45, 120), (18, 18, W - 36, H - 36), 4)
        surface.blit(layer, (0, 0))

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
