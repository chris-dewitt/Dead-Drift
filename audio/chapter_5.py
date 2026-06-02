"""
Dead Drift — Chapter 5 audio inflection (MERCY).

The Remnants' station — warm, amber-lit, human. The first place in the
run that feels like home. Sonic identity pulls away from everything
corporate: G natural minor (Aeolian), soft brushes, acoustic guitar as
the lead. The score breathes. The machine is behind you, for now.

Cargo: MERCY drive — Chen's zero-write exploit. No alarm mechanic
(the drive is inert until deployed). Cargo alarm is silence.
"""
from __future__ import annotations
import numpy as np
import pygame
from audio.synth import SAMPLE_RATE, _2PI, _to_sound, _adsr, acoustic_guitar_note

# Chapter metadata
HOME_KEY_ROOT       = 196.0          # G3 — G natural minor, earthen, warmer than A
HOME_KEY_NAME       = "G minor"
MODE                = "minor"        # Aeolian — back to basics, this is where home is
SIGNATURE_NAME      = "Acoustic guitar fingerpicking — simple, human, battered-hopeful"
KIT_INFLECTION_DESC = "Soft brushes, loose swing, kit pulled way back — someone's living room"
CARGO_HOOK_DESC     = "No alarm mechanic — the drive is inert until deployed"


def signature_instrument(freq: float = None, duration: float = 1.5) -> pygame.mixer.Sound:
    """A simple fingerpicked arpeggio in G minor — three notes, open and human.
    Uses acoustic_guitar_note from synth.py. No tube amp, no distortion.
    Just the string and the room.
    """
    if freq is None:
        freq = HOME_KEY_ROOT

    # G minor arpeggio: root, minor-third, fifth
    # freq = G3 (196), minor-3rd = Bb3 (233.1), fifth = D4 (293.7)
    freqs = [freq, freq * (2 ** (3 / 12)), freq * (2 ** (7 / 12))]
    dur_per_note = 1.0
    spacing_s    = 0.26
    total_n      = max(1, int(SAMPLE_RATE * duration))
    buf          = np.zeros(total_n, dtype=np.float32)

    for i, f in enumerate(freqs):
        snd  = acoustic_guitar_note(f, duration=dur_per_note)
        arr  = pygame.sndarray.array(snd)
        if arr.ndim == 2:
            arr = arr[:, 0]
        arr  = arr.astype(np.float32) / 32767.0
        pos  = int(SAMPLE_RATE * i * spacing_s)
        end  = min(pos + len(arr), total_n)
        if pos < total_n:
            buf[pos:end] += arr[: end - pos] * 0.62

    # Gentle fade-in and fade-out
    fade = min(int(SAMPLE_RATE * 0.04), total_n // 8)
    if fade > 0:
        buf[:fade]  *= np.linspace(0.0, 1.0, fade)
        buf[-fade:] *= np.linspace(1.0, 0.0, fade)

    # Subtle reverb — one delay tap
    delay_n = int(SAMPLE_RATE * 0.09)
    if delay_n < total_n:
        wet = np.zeros_like(buf)
        wet[delay_n:] = buf[: total_n - delay_n] * 0.28
        buf = buf + wet

    peak = float(np.max(np.abs(buf)))
    if peak > 0:
        buf = buf / peak * 0.78
    return _to_sound(buf.clip(-1.0, 1.0))


def kit_inflection(drum_sound_array: np.ndarray) -> np.ndarray:
    """Soft brushes. Pull the whole kit back to 0.55 amplitude so it sits
    behind the guitar like a drummer playing in the corner of a small room.
    Add a gentle high-frequency rolloff to remove the hard stick attack and
    leave the brush sweep — a 5-sample running average does the trick.
    """
    arr = drum_sound_array.astype(np.float32, copy=True)
    # Volume way back — brushes are quiet
    arr *= 0.55
    # Low-pass rolloff: kill the crisp stick transient, keep the body
    if len(arr) > 5:
        kernel = np.ones(5, dtype=np.float32) / 5.0
        arr = np.convolve(arr, kernel, mode="same")
    # Gentle headroom safety
    peak = float(np.max(np.abs(arr)))
    if peak > 1.0:
        arr = arr / peak
    return arr


def cargo_alarm_callback(alarm_level: float, master_fx=None):
    """No-op — MERCY drive is inert cargo until chapter 6 deploys it.
    No cargo-state audio mechanic for this chapter.
    """
    pass


# Stem priority — chapter 5 is the quiet chapter: warm room, not war.
# Bass stays present (the groove keeps going), arp pulls back, drums very soft.
STEM_GATES = {
    "drum": 0.55,
    "bass": 0.90,
    "arp":  0.65,
}
