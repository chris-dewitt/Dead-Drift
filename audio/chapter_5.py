"""
Dead Drift — Chapter 5 audio inflection (The Edge).
Per SOUNDTRACK_PLAN.md Section 4 (extension — the Remnants chapters).

The first place in Dead Drift that feels like home. Chapter 5 is the warm
exhale after four chapters of corporate cold. Where Chapter 1's harmonica is
distorted through a tube amp, here the same voice plays *clean* — a lived-in
acoustic blues, slightly detuned, breathed rather than driven. D Dorian: a
minor mode with a raised sixth, so it leans hopeful without ever resolving
bright. The Remnants are still in debt; they just stopped pretending it hurts.

Cargo here is the empty hold / Chen's drive — inert in the void — so cargo
damage barely touches the mix. The warmth is the point.
"""
from __future__ import annotations
import numpy as np
import pygame
from audio.synth import SAMPLE_RATE, _2PI, _to_sound, _adsr, _sine, _noise
from audio.blues_licks import _harp_note

# Chapter metadata
HOME_KEY_ROOT       = 146.83         # D3 — D Dorian, warm minor
HOME_KEY_NAME       = "D Dorian"
MODE                = "dorian"
SIGNATURE_NAME      = "Clean acoustic harmonica — breathed, not driven"
KIT_INFLECTION_DESC = "Loose brushed kit, warm room tail, swing behind the beat"
CARGO_HOOK_DESC     = "Drive is inert in the void — cargo damage barely colours the mix"


def signature_instrument(freq: float = None, duration: float = 1.0) -> pygame.mixer.Sound:
    """One clean-harmonica phrase — the human counterpoint to Chapter 1.

    Same harp voice as ch.1, but with the tube drive removed and a second
    voice detuned a few cents underneath for that lived-in, two-reeds-at-once
    warmth. The result reads as *home* instead of *contraband*.
    """
    if freq is None:
        freq = HOME_KEY_ROOT
    clean = _harp_note(freq, duration, amp=0.80)
    # A second reed a touch flat — chorus the warmth, don't drive it.
    under = _harp_note(freq * 0.997, duration, amp=0.34)
    w = clean + under
    # Gentle soft-knee — round the peaks without the ch.1 grind.
    w = np.tanh(w * 1.1) * 0.9
    peak = float(np.max(np.abs(w)))
    if peak > 0:
        w = w / peak * 0.80
    return _to_sound(w.astype(np.float32))


def kit_inflection(drum_sound_array: np.ndarray) -> np.ndarray:
    """Brushed-kit warmth: a short, low-gain room tail (40 ms behind) plus a
    gentle pull to 0.78 amplitude so the kit sits behind the harmonica like
    brushes on a snare. The opposite of Chapter 6's quantised clock.
    """
    arr = drum_sound_array.astype(np.float32, copy=True)
    n = len(arr)
    if n == 0:
        return arr
    arr *= 0.78
    delay_samples = int(SAMPLE_RATE * 0.040)
    if 0 < delay_samples < n:
        tail = np.zeros_like(arr)
        tail[delay_samples:] = arr[:-delay_samples] * 0.45
        arr = arr + tail
    peak = float(np.max(np.abs(arr)))
    if peak > 1.0:
        arr = arr / peak
    return arr


def cargo_alarm_callback(alarm_level: float, master_fx=None):
    """The encrypted drive is inert in the void — it does not degrade the
    signal the way the Acoustic Archive does. We pass through only a faint
    fraction of the alarm so a battered hull still adds the barest grit.
    """
    if master_fx is not None:
        try:
            master_fx.cargo_degradation = float(max(0.0, min(1.0, alarm_level * 0.25)))
        except (AttributeError, TypeError):
            pass


# Stem priority — chapter 5 plays an intimate, slightly pulled-back full mix.
STEM_GATES = {
    "drum": 0.90,
    "bass": 1.0,
    "arp":  0.85,
}
