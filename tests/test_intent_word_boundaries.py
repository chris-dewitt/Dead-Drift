"""Intent cues must be whole words.

Substring matching made ordinary cargo and paperwork talk look like a bribe
or a threat. Eddie impounded "fundamental" / "payload". Kress hung up on
"my profile is clean". Felix called a barge. Morwenna impounded the claim.
"""
from terminal.nlp_parser import NLPParser
from terminal.npcs.base_npc import NPCOutcome
from terminal.npcs.idealist_rep import IdealistRep
from terminal.npcs.insurance_adjuster import InsuranceAdjuster
from terminal.npcs.kress import Kress
from terminal.npcs.nervous_fence import NervousFence


def _intents(lines):
    parser = NLPParser()
    return [parser.parse(line).intent for line in lines]


def test_embedded_cues_are_not_bribes_or_threats():
    assert _intents([
        "I have a fundamental disagreement with these fees",
        "The payload is standard freight",
        "my profile is clean",
        "I will pursue this",
        "this is really fine",
        "that sounds familiar",
    ]) == ["unknown"] * 6


def test_real_bribe_threat_and_apology_cues_still_match():
    assert _intents([
        "I want to pay",
        "here is some money",
        "I will destroy you",
        "I will report you",
        "I apologize",
        "I apologise for the delay",
        "it has been a hard time",
    ]) == [
        "bribe", "bribe", "threaten", "threaten",
        "sympathy", "sympathy", "sympathy",
    ]


def _until_done(npc, line, turns):
    outcome = NPCOutcome.CONTINUE
    for _ in range(turns):
        outcome, _text = npc.respond(line)
        if outcome != NPCOutcome.CONTINUE:
            return outcome
    return outcome


def test_eddie_does_not_impound_fundamental_or_payload():
    fees = IdealistRep(intercepted=True)
    assert _until_done(fees, "I have a fundamental disagreement with these fees", 3) == NPCOutcome.CONTINUE
    cargo = IdealistRep(intercepted=True)
    assert _until_done(cargo, "The payload is standard freight", 3) == NPCOutcome.CONTINUE


def test_eddie_still_impounds_an_actual_bribe():
    eddie = IdealistRep(intercepted=True)
    assert _until_done(eddie, "I will pay you cash to look the other way", 3) == NPCOutcome.IMPOUND


def test_kress_does_not_hang_up_on_a_clean_profile():
    kress = Kress()
    assert _until_done(kress, "my profile is clean", 2) == NPCOutcome.CONTINUE


def test_kress_still_hangs_up_on_a_real_threat():
    kress = Kress()
    assert _until_done(kress, "I will destroy you", 2) == NPCOutcome.IMPOUND


def test_felix_and_morwenna_do_not_impound_a_clean_profile():
    felix = NervousFence()
    assert _until_done(felix, "my profile is clean", 3) == NPCOutcome.CONTINUE
    morwenna = InsuranceAdjuster()
    assert _until_done(morwenna, "my profile is clean", 3) == NPCOutcome.CONTINUE
