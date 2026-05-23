"""
Dead Drift — Chapter 1 audio inflection (The Acoustic Archive).
Per SOUNDTRACK_PLAN.md Section 4.1

Smuggling an illegal music library. Sonic identity leans hard into the
"music store" register — A natural minor (aeolian), lush minor-7th pads,
and a distorted electric harmonica through a tube amp as the lead voice.
Cargo damage manifests as audio fidelity degradation (bit-crush gets worse).
"""
from __future__ import annotations
import numpy as np
import pygame
from audio.synth import SAMPLE_RATE, _2PI, _to_sound, _adsr, _sine, _noise
from audio.blues_licks import _harp_note

# Chapter metadata
HOME_KEY_ROOT       = 220.0          # A3 — A natural minor
HOME_KEY_NAME       = "A minor"
MODE                = "minor"        # aeolian
SIGNATURE_NAME      = "Distorted electric harmonica through tube amp"
KIT_INFLECTION_DESC = "Snare +20% reverb tail, hi-hat behind beat (swing 54%)"
CARGO_HOOK_DESC     = "Cargo damage drives literal bit-crush on master bus"


def signature_instrument(freq: float = None, duration: float = 1.0) -> pygame.mixer.Sound:
    """One distorted-harmonica phrase. A harp note overdriven through a soft
    clipper for that tube-amp grind. Default to A3 if no freq given.
    """
    if freq is None:
        freq = HOME_KEY_ROOT
    # Generate clean harp tone
    clean = _harp_note(freq, duration, amp=0.85)
    # Tube-amp soft clip: boost +9.5 dB (~x3) then clip to ±0.9
    driven = (clean * 3.0).clip(-0.9, 0.9)
    # Mix a little clean back in for body
    w = driven * 0.78 + clean * 0.18
    # Re-normalize gently
    peak = float(np.max(np.abs(w)))
    if peak > 0:
        w = w / peak * 0.82
    return _to_sound(w.astype(np.float32))


def kit_inflection(drum_sound_array: np.ndarray) -> np.ndarray:
    """Echo-chamber sheen: add a delayed copy at +20% gain, 80 ms behind.
    Sums into the same array length — extra tail past the loop is dropped,
    which gives the snare a short reverb impression without recursive feedback.
    """
    arr = drum_sound_array.astype(np.float32, copy=True)
    delay_samples = int(SAMPLE_RATE * 0.080)
    if delay_samples >= len(arr) or delay_samples <= 0:
        return arr
    # Add delayed copy at 1.20x (the "+20% reverb feel")
    delayed = np.zeros_like(arr)
    delayed[delay_samples:] = arr[:-delay_samples] * 1.20
    out = arr + delayed
    # Headroom safety — don't let the verb hot-clip
    peak = float(np.max(np.abs(out)))
    if peak > 1.0:
        out = out / peak
    return out


def cargo_alarm_callback(alarm_level: float, master_fx=None):
    """Cargo damage degrades audio fidelity literally — pipe the alarm level
    straight into master_fx.cargo_degradation so the bit-crush worsens as the
    Acoustic Archive's hull integrity falls.
    """
    if master_fx is not None:
        try:
            master_fx.cargo_degradation = float(max(0.0, min(1.0, alarm_level)))
        except (AttributeError, TypeError):
            pass


# Stem priority — chapter 1 plays the full mix
STEM_GATES = {
    "drum": 1.0,
    "bass": 1.0,
    "arp":  1.0,
}
