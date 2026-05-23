"""
Dead Drift — Chapter 4 audio inflection (The Schrödinger VIP).
Per SOUNDTRACK_PLAN.md Section 4.4

The passenger may or may not be alive. The chapter's sonic identity IS
its absence — stems get gated out, the kick drops every fourth measure,
brushes replace sticks. E Locrian is the only unstable mode in Western
music; nothing wants to rest on the tonic, which is exactly right.
Cargo damage makes the mix BLINK — observed alive = 1 s of warm pad chord,
observed dead = 1 s of complete silence. The box is not opened.
"""
from __future__ import annotations
import numpy as np
import pygame
from audio.synth import SAMPLE_RATE, _2PI, _to_sound, _adsr, _sine, _noise

# Chapter metadata
HOME_KEY_ROOT       = 164.81         # E3 — E Locrian, perpetually unstable
HOME_KEY_NAME       = "E Locrian"
MODE                = "locrian"
SIGNATURE_NAME      = "SILENCE — the chapter's signature is removal of stems"
KIT_INFLECTION_DESC = "Half-time brushes; every 4th measure the kick drops"
CARGO_HOOK_DESC     = "Mix blinks: alive = warm pad chord, dead = total silence"


def signature_instrument(freq: float = None, duration: float = 1.0) -> pygame.mixer.Sound:
    """The signature of chapter 4 is absence — there is no lead voice.
    Returns one second (or `duration` seconds) of pure silence. Plays through
    the same channels as other chapter signatures, but the player hears
    nothing. The void IS the instrument.
    """
    n = max(1, int(SAMPLE_RATE * max(duration, 0.0)))
    silence = np.zeros(n, dtype=np.float32)
    return _to_sound(silence)


def kit_inflection(drum_sound_array: np.ndarray) -> np.ndarray:
    """Half-time brushes feel. Every 4th measure the kick goes missing —
    we zero out small windows at measure boundaries to simulate the dropped
    kick. Overall amplitude scaled to 0.6 so the whole kit sits behind the
    pad like brushes instead of sticks.

    Assumes a typical 2-bar @ 90 BPM drum loop, so we conservatively zero
    a small ~80 ms window at the start of every fourth measure based on the
    array's length divided into 16 candidate slots.
    """
    arr = drum_sound_array.astype(np.float32, copy=True)
    n = len(arr)
    if n == 0:
        return arr

    # Brushes vibe — pull overall amplitude to 0.6
    arr *= 0.6

    # Subdivide the loop into 16 slots and zero a window at every 4th
    # (i.e. slots 0, 4, 8, 12) — the dropped kicks.
    n_slots = 16
    slot_len = n // n_slots
    if slot_len <= 0:
        return arr
    drop_window = min(slot_len, int(SAMPLE_RATE * 0.080))  # ~80 ms cut
    for slot_idx in range(0, n_slots, 4):
        start = slot_idx * slot_len
        end   = min(start + drop_window, n)
        if start < end:
            # Short fade ramps avoid clicks at the cut edges
            fade = max(1, int(SAMPLE_RATE * 0.003))
            if end - start > fade * 2:
                arr[start:start + fade]    *= np.linspace(1.0, 0.0, fade)
                arr[start + fade:end - fade] = 0.0
                arr[end - fade:end]        *= np.linspace(0.0, 1.0, fade)
            else:
                arr[start:end] = 0.0
    return arr


def cargo_alarm_callback(alarm_level: float, master_fx=None):
    """No-op — the alive/dead "blink" behaviour is implemented in
    audio_manager via STEM_GATES being toggled when SchrodingerVIP.update()
    collapses the wavefunction. Hook reserved for future per-frame work.
    """
    pass


# Stem priority — chapter 4 strips the mix down to a half-empty room.
# Bass is gone entirely; drums at half, arp pulled back to make space.
STEM_GATES = {
    "drum": 0.5,
    "bass": 0.0,
    "arp":  0.8,
}
