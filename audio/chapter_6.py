"""
Dead Drift — Chapter 6 audio inflection (Compliance).
Per SOUNDTRACK_PLAN.md Section 4 (extension — the Nova Soma climax).

Nova Soma Station. Glass, chrome, fluorescent, polite, terrifying. Where
Chapter 5 is the warm exhale, Chapter 6 is the held breath. The building is
the boss. The score's job is to make the player feel *processed*.

A cold A-minor (aeolian), but the signature voice is not blues — it is a
fluorescent compliance chime: a glassy bell, detuned a few cents sharp so it
sits slightly *wrong*, like a lift announcing a floor you don't want. The kit
is quantised and squeezed flat: no swing, no dynamics, a clock that does not
care. The drive pings Nova Soma the moment it's plugged in, so cargo "damage"
here reads as the building noticing you — the degradation rises with alarm.
"""
from __future__ import annotations
import numpy as np
import pygame
from audio.synth import SAMPLE_RATE, _2PI, _to_sound, _adsr, _sine, _noise

# Chapter metadata
HOME_KEY_ROOT       = 110.0          # A2 — low, institutional A minor
HOME_KEY_NAME       = "A minor (cold aeolian)"
MODE                = "minor"
SIGNATURE_NAME      = "Fluorescent compliance chime — glassy, a few cents sharp"
KIT_INFLECTION_DESC = "Quantised clock kit, squeezed flat — no swing, no mercy"
CARGO_HOOK_DESC     = "Drive pings Nova Soma — alarm rises as the building notices you"


def signature_instrument(freq: float = None, duration: float = 1.0) -> pygame.mixer.Sound:
    """A cold compliance bell. Sine fundamental plus inharmonic glassy
    partials, the whole thing tuned ~8 cents sharp so it never feels at rest.
    The institutional cousin of a lift chime — polite, and a little wrong.
    """
    if freq is None:
        freq = HOME_KEY_ROOT * 4.0      # ring it up an octave-ish, bell register
    sharp = freq * (2.0 ** (8.0 / 1200.0))   # +8 cents — deliberately uneasy
    t = np.linspace(0.0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # Glassy, slightly inharmonic partial stack (bell-like ratios).
    w = (
        np.sin(_2PI * sharp * 1.00 * t) * 1.00
        + np.sin(_2PI * sharp * 2.01 * t) * 0.45
        + np.sin(_2PI * sharp * 2.99 * t) * 0.30
        + np.sin(_2PI * sharp * 4.17 * t) * 0.18
    )
    # Bell envelope — fast attack, long ringing decay.
    w = _adsr(w, attack=0.002, decay=0.45 * duration, sustain=0.18, release=0.5 * duration)
    # A breath of fluorescent hiss underneath — the room tone of a server floor.
    w += _noise(duration, amp=0.015)
    peak = float(np.max(np.abs(w)))
    if peak > 0:
        w = w / peak * 0.74
    return _to_sound(w.astype(np.float32))


def kit_inflection(drum_sound_array: np.ndarray) -> np.ndarray:
    """The clock that does not care. Squeeze the kit flat — hard soft-clip to
    compress the dynamics toward a single sterile level, then trim the tail of
    every transient so nothing rings. Sterile, quantised, relentless.
    """
    arr = drum_sound_array.astype(np.float32, copy=True)
    n = len(arr)
    if n == 0:
        return arr
    # Flatten dynamics — compress toward a uniform level (institutional, airless).
    arr = np.tanh(arr * 2.4) * 0.62
    # Clip any residual ring tails into silence so the groove feels gated.
    gate = 0.06
    arr[np.abs(arr) < gate] = 0.0
    peak = float(np.max(np.abs(arr)))
    if peak > 1.0:
        arr = arr / peak
    return arr


def cargo_alarm_callback(alarm_level: float, master_fx=None):
    """The drive pings Nova Soma the instant it's live. Here, rising alarm IS
    the building noticing — pipe it straight (and a touch hotter than ch.1)
    into the master degradation so the mix curdles as Compliance closes in.
    """
    if master_fx is not None:
        try:
            master_fx.cargo_degradation = float(max(0.0, min(1.0, alarm_level * 1.15)))
        except (AttributeError, TypeError):
            pass


# Stem priority — chapter 6 is the clock and the low end. The clock never
# stops; the arp (the only "human" colour) is pulled almost out of the room.
STEM_GATES = {
    "drum": 1.0,
    "bass": 0.90,
    "arp":  0.30,
}
