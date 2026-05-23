"""
Dead Drift — Chapter 2 audio inflection (The Mycorrhizal Payload).
Per SOUNDTRACK_PLAN.md Section 4.2

Psychoactive fungal spores. The sonic identity drifts dorian against the
ship's home minor — dorian's raised 6th sounds *almost* right against the
bent harmonica, which is exactly the unsettled feeling we want. Lead voice
is a bowed-saw (slow-attack triangle through a comb filter / wineglass-wet).
Cargo damage flips the stereo field when the controls invert.
"""
from __future__ import annotations
import numpy as np
import pygame
from audio.synth import SAMPLE_RATE, _2PI, _to_sound, _adsr, _sine, _noise

# Chapter metadata
HOME_KEY_ROOT       = 261.6          # C4 — C natural minor (dorian-flavored)
HOME_KEY_NAME       = "C dorian"
MODE                = "dorian"
SIGNATURE_NAME      = "Bowed-saw lead (slow-attack triangle through comb filter)"
KIT_INFLECTION_DESC = "Rim-shot + tape-echo that mistimes 30-60 ms randomly"
CARGO_HOOK_DESC     = "On control inversion, stereo field inverts too"


def _triangle(freq: float, duration: float, amp: float = 1.0) -> np.ndarray:
    """Triangle wave — symmetric, mellow, the right starting timbre for the
    bowed-saw character before the comb filter colours it.
    """
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0.0, duration, n, endpoint=False)
    saw = 2.0 * ((t * freq) % 1.0) - 1.0
    tri = 2.0 * np.abs(saw) - 1.0
    return tri * amp


def signature_instrument(freq: float = None, duration: float = 1.0) -> pygame.mixer.Sound:
    """Bowed-saw lead. Triangle wave with a slow attack, fed into a
    comb-filter delay tuned to ~700 Hz period (1/700 s) at 50% wet — the
    delay's harmonic series adds the "wineglass wet" formant.
    """
    if freq is None:
        freq = HOME_KEY_ROOT
    n = int(SAMPLE_RATE * duration)
    if n <= 0:
        return _to_sound(np.zeros(1, dtype=np.float32))

    # Slow-attack triangle ('bowed' feel) with subtle vibrato
    t   = np.linspace(0.0, duration, n, endpoint=False)
    vib = 1.0 + 0.008 * np.sin(_2PI * 4.3 * t)
    phase = np.cumsum(_2PI * freq * vib / SAMPLE_RATE)
    # Reconstruct triangle from phase
    saw = ((phase / _2PI) % 1.0) * 2.0 - 1.0
    tri = 2.0 * np.abs(saw) - 1.0
    # Slow attack 220 ms — the 'bow' on the string
    attack = min(int(SAMPLE_RATE * 0.22), n)
    env = np.ones(n, dtype=np.float32)
    if attack > 0:
        env[:attack] = np.linspace(0.0, 1.0, attack) ** 1.6
    # Smooth release
    rel = min(int(SAMPLE_RATE * 0.12), n)
    if rel > 0:
        env[-rel:] *= np.linspace(1.0, 0.0, rel)
    dry = (tri * env * 0.6).astype(np.float32)

    # Comb-filter delay: tap at 1/700 s ≈ 63 samples — gives the wineglass formant
    delay_samples = max(2, int(SAMPLE_RATE / 700.0))
    comb = np.zeros(n, dtype=np.float32)
    if delay_samples < n:
        comb[delay_samples:] = dry[:-delay_samples]

    # 50% wet mix
    w = dry * 0.5 + comb * 0.5
    peak = float(np.max(np.abs(w)))
    if peak > 0:
        w = w / peak * 0.78
    return _to_sound(w.clip(-1.0, 1.0))


def kit_inflection(drum_sound_array: np.ndarray) -> np.ndarray:
    """Tape-echo that mistimes. Pick 2–3 random positions in the loop and
    nudge them forward/back by 30–60 ms via array roll on local windows.
    The drift makes the groove feel queasy — exactly the spore brief.
    """
    arr = drum_sound_array.astype(np.float32, copy=True)
    n = len(arr)
    if n < SAMPLE_RATE // 2:
        return arr

    out = arr.copy()
    rng = np.random.default_rng()
    n_shifts = int(rng.integers(2, 4))   # 2 or 3 shifted hits

    window = int(SAMPLE_RATE * 0.18)     # 180 ms grain around each shift
    for _ in range(n_shifts):
        center = int(rng.integers(window, max(window + 1, n - window)))
        shift_ms = float(rng.uniform(30.0, 60.0)) * rng.choice([-1.0, 1.0])
        shift_samples = int(SAMPLE_RATE * (shift_ms / 1000.0))
        lo = max(0, center - window // 2)
        hi = min(n, center + window // 2)
        grain = arr[lo:hi]
        rolled = np.roll(grain, shift_samples)
        # Cross-fade grain edges so we don't introduce clicks
        fade = max(1, int(SAMPLE_RATE * 0.004))
        if fade * 2 < len(rolled):
            rolled[:fade]  *= np.linspace(0.0, 1.0, fade)
            rolled[-fade:] *= np.linspace(1.0, 0.0, fade)
        # Mix the displaced grain on top at -3 dB (tape echo, not replacement)
        out[lo:hi] += rolled * 0.70

    peak = float(np.max(np.abs(out)))
    if peak > 1.0:
        out = out / peak
    return out


def cargo_alarm_callback(alarm_level: float, master_fx=None):
    """No-op here — stereo inversion on control-flip is handled in
    audio_manager when MycoShroom triggers the inversion event.
    """
    pass


# Stem priority — chapter 2 keeps the full mix
STEM_GATES = {
    "drum": 1.0,
    "bass": 1.0,
    "arp":  1.0,
}
