"""Coverage for Aliveness Phase H — Audio & Soundtrack.

Headless: we mock _to_sound where the synth numpy pipeline is exercised, and
sniff source / data tables everywhere else, so no real audio device is needed.

  H.2 — Bax harmonica chain fires the blues-lick voice at critical hull.
  H.3 — Chapters 5 & 6 audio inflection modules + dock receivers + station
        themes + per-chapter music wiring.
  H.4 — Voice profiles for the two new union reps (and the ch5/6 receivers).
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path

import numpy as np
import pytest

import audio.synth as synth


# ---------------------------------------------------------------------------
# H.3 — chapter 5 & 6 audio inflection modules
# ---------------------------------------------------------------------------

@pytest.fixture
def _mock_to_sound(monkeypatch):
    """Return the raw numpy buffer instead of a pygame Sound."""
    monkeypatch.setattr(synth, "_to_sound", lambda wave: wave)
    import audio.chapter_5 as c5
    import audio.chapter_6 as c6
    monkeypatch.setattr(c5, "_to_sound", lambda wave: wave)
    monkeypatch.setattr(c6, "_to_sound", lambda wave: wave)
    return c5, c6


def test_new_chapter_modules_expose_the_standard_api():
    import audio.chapter_5 as c5
    import audio.chapter_6 as c6
    for mod in (c5, c6):
        assert callable(mod.signature_instrument)
        assert callable(mod.kit_inflection)
        assert callable(mod.cargo_alarm_callback)
        assert isinstance(mod.STEM_GATES, dict)
        assert set(mod.STEM_GATES) == {"drum", "bass", "arp"}
        assert isinstance(mod.MODE, str) and mod.MODE


def test_new_chapter_modes_are_registered():
    from audio.audio_manager import _CHAPTER_MODES
    assert _CHAPTER_MODES[5] == "dorian"
    assert _CHAPTER_MODES[6] == "minor"


def test_chapter_signatures_render_finite_audio(_mock_to_sound):
    c5, c6 = _mock_to_sound
    for mod in (c5, c6):
        buf = mod.signature_instrument()
        assert isinstance(buf, np.ndarray) and buf.size > 0
        assert np.all(np.isfinite(buf))
        assert np.max(np.abs(buf)) <= 1.0


def test_chapter_kit_inflection_preserves_length_and_headroom(_mock_to_sound):
    c5, c6 = _mock_to_sound
    rng = np.random.default_rng(1)
    drum = rng.uniform(-0.8, 0.8, synth.SAMPLE_RATE).astype(np.float32)
    for mod in (c5, c6):
        out = mod.kit_inflection(drum)
        assert out.shape == drum.shape
        assert np.all(np.isfinite(out))
        assert np.max(np.abs(out)) <= 1.0001


def test_cargo_callback_clamps_degradation():
    import audio.chapter_5 as c5
    import audio.chapter_6 as c6
    from types import SimpleNamespace
    fx = SimpleNamespace(cargo_degradation=0.0)
    c5.cargo_alarm_callback(2.0, master_fx=fx)   # over-range input
    assert 0.0 <= fx.cargo_degradation <= 1.0
    c6.cargo_alarm_callback(2.0, master_fx=fx)
    assert 0.0 <= fx.cargo_degradation <= 1.0
    # ch6 reacts hotter than ch5 for the same alarm (the building notices).
    fx5 = SimpleNamespace(cargo_degradation=0.0)
    fx6 = SimpleNamespace(cargo_degradation=0.0)
    c5.cargo_alarm_callback(0.5, master_fx=fx5)
    c6.cargo_alarm_callback(0.5, master_fx=fx6)
    assert fx6.cargo_degradation > fx5.cargo_degradation


def test_audio_manager_loads_all_six_chapter_modules():
    src = Path("audio/audio_manager.py").read_text(encoding="utf-8")
    assert "for ch_num in (1, 2, 3, 4, 5, 6):" in src


def test_corridor_signature_profiles_cover_chapters_five_and_six():
    src = Path("audio/audio_manager.py").read_text(encoding="utf-8")
    for ch in (5, 6):
        assert f"            {ch}: " in src, f"chapter {ch} missing corridor profile"


# ---------------------------------------------------------------------------
# H.3 — dock receivers, station themes, chapter names
# ---------------------------------------------------------------------------

def test_dock_receiver_leaves_the_union_loop_for_ch5_and_ch6():
    from delivery.delivery_sequence import (_DOCK_RECEIVER, _GARY_DOCK_LINES,
                                             _BAX_DOCK_WINDUP_DELIVERY)
    assert _DOCK_RECEIVER[5] == "FITZ"
    assert _DOCK_RECEIVER[6] == "BOWEN"
    for ch in (5, 6):
        assert _GARY_DOCK_LINES[ch], f"no dock lines for chapter {ch}"
        assert _BAX_DOCK_WINDUP_DELIVERY[ch], f"no Bax windup for chapter {ch}"
    # Gary must NOT be the receiver for the off-loop chapters.
    assert "GARY" not in _DOCK_RECEIVER[5]
    assert "GARY" not in _DOCK_RECEIVER[6]


def test_station_themes_defined_for_all_six_chapters():
    from delivery.delivery_sequence import _STATION_THEMES
    for ch in range(1, 7):
        assert ch in _STATION_THEMES
        hull, trim, name = _STATION_THEMES[ch]
        assert len(hull) == 3 and len(trim) == 3 and isinstance(name, str)


# ---------------------------------------------------------------------------
# H.4 — new voice profiles
# ---------------------------------------------------------------------------

def test_new_reps_resolve_to_distinct_voice_profiles():
    from audio.voices import resolve_voice_key, _VOICES
    assert resolve_voice_key("EDMUND") == "idealist_rep"
    assert resolve_voice_key("Eddie") == "idealist_rep"
    assert resolve_voice_key("VINCE") == "corrupt_rep"
    assert resolve_voice_key("Vinny") == "corrupt_rep"
    # Distinct from each other and from Gary.
    keys = {"idealist_rep", "corrupt_rep", "gary"}
    assert len(keys) == 3
    for k in ("idealist_rep", "corrupt_rep"):
        assert k in _VOICES


def test_ch5_ch6_dock_receivers_have_voices():
    from audio.voices import resolve_voice_key, _VOICES
    assert resolve_voice_key("FITZ") == "fitz"
    assert resolve_voice_key("BOWEN") == "bowen"
    assert "fitz" in _VOICES and "bowen" in _VOICES
    # The Union dock receiver emits Gary's full name — it must not fall
    # through to the default voice (G.1 / H.3 regression guard).
    assert resolve_voice_key("GARY PRUITT") == "gary"


def test_new_voice_profiles_generate_blips():
    """The full synth path must produce playable blips for each new voice."""
    import pygame
    pygame.mixer.quit()
    try:
        pygame.mixer.init()
    except pygame.error:
        pytest.skip("no audio backend available")
    from audio.voices import make_voice_blips
    for who in ("EDMUND", "VINCE", "FITZ", "BOWEN"):
        blips = make_voice_blips(who, n_vars=2)
        assert len(blips) == 2


# ---------------------------------------------------------------------------
# H.2 — harmonica chain
# ---------------------------------------------------------------------------

def test_harmonica_event_constant_exists_and_bax_emits_it():
    from core.event_bus import EVT_BAX_HARMONICA
    assert isinstance(EVT_BAX_HARMONICA, str)
    src = Path("bax/bax.py").read_text(encoding="utf-8")
    assert "bus.emit(EVT_BAX_HARMONICA)" in src


def test_audio_manager_plays_a_lick_on_harmonica_event():
    src = Path("audio/audio_manager.py").read_text(encoding="utf-8")
    assert "EVT_BAX_HARMONICA" in src
    assert "_on_bax_harmonica" in src
    assert "generate_lick" in src
