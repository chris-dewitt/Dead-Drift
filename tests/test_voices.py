"""Voice profile resolution (no mixer required)."""
from audio.voices import resolve_voice_key


def test_resolve_known_aliases():
    assert resolve_voice_key("Morwenna") == "insurance_adjuster"
    assert resolve_voice_key("[TK-9]") == "tk-9"
    assert resolve_voice_key("MEDI-CORP") == "medi_corp"


def test_resolve_unknown_uses_default():
    assert resolve_voice_key("Some Random NPC") == "default"
