"""
Dead Drift — Chapter 6 audio inflection (THE UPLOAD).

Nova Soma Station — glass, chrome, fluorescent, polite, terrifying. The
building is a machine, and the machine does not want you here. B Phrygian:
the Phrygian mode's half-step opening interval is the most inherently tense
sound in Western music — everything wants to resolve, nothing does. The
signature instrument is a fluorescent-light buzz: 60 Hz power hum +
120 Hz tube ballast + slight beating from a mismatched second tube.
Pure institutional dread.

Cargo: THE UPLOAD — deploying the MERCY drive against Nova Soma's ledger.
Cargo alarm: during the 90-second upload countdown, all music above the
bass drone freezes. The building is holding its breath.
"""
from __future__ import annotations
import numpy as np
import pygame
from audio.synth import SAMPLE_RATE, _2PI, _to_sound, _adsr

# Chapter metadata
HOME_KEY_ROOT       = 246.94         # B3 — B Phrygian; the half-step open is maximum tension
HOME_KEY_NAME       = "B Phrygian"
MODE                = "phrygian"
SIGNATURE_NAME      = "Fluorescent-light buzz — 60 Hz hum + 120 Hz ballast + beating"
KIT_INFLECTION_DESC = "Clinical precision, no swing, metronome-locked; the building is the drummer"
CARGO_HOOK_DESC     = "Upload countdown freezes all stems above bass; machine holds its breath"


def signature_instrument(freq: float = None, duration: float = 1.5) -> pygame.mixer.Sound:
    """The fluorescent light hum. Three components:
      1. 60 Hz power-line fundamental — low, subliminal, always there.
      2. 120 Hz tube-ballast buzz — the dominant perceived pitch.
      3. 119.4 Hz second tube (slightly detuned) — beating at 0.6 Hz
         against the first, giving the slow oscillation of a failing tube.

    `freq` is ignored — fluorescent lights don't transpose.
    `duration` controls the buzz length.
    """
    n = max(1, int(SAMPLE_RATE * max(duration, 0.0)))
    t = np.linspace(0.0, duration, n, endpoint=False)

    # Power-line fundamental — felt more than heard
    f60  = np.sin(_2PI * 60.0  * t) * 0.30

    # Tube ballast — the audible buzz
    f120 = np.sin(_2PI * 120.0 * t) * 0.55

    # Second detuned tube — 0.6 Hz beating gives the "failing tube" oscillation
    f119 = np.sin(_2PI * 119.4 * t) * 0.40

    # Pink-ish noise floor — the hiss inside the fixture
    rng  = np.random.default_rng(seed=42)
    hiss = rng.uniform(-1.0, 1.0, n).astype(np.float32) * 0.06

    w = (f60 + f120 + f119 + hiss).astype(np.float32)

    # Short fade-in / fade-out so the buzz doesn't click at loop boundaries
    fade = min(int(SAMPLE_RATE * 0.025), n // 6)
    if fade > 0:
        w[:fade]  *= np.linspace(0.0, 1.0, fade)
        w[-fade:] *= np.linspace(1.0, 0.0, fade)

    peak = float(np.max(np.abs(w)))
    if peak > 0:
        w = w / peak * 0.70
    return _to_sound(w.clip(-1.0, 1.0))


def kit_inflection(drum_sound_array: np.ndarray) -> np.ndarray:
    """Clinical precision. No swing, no human warmth — sharpen the transients
    instead of softening them. Apply a slight transient boost at the very
    start of the array (kick hit) and leave everything else dead-flat.
    The building is the drummer. It does not miss the beat.
    """
    arr = drum_sound_array.astype(np.float32, copy=True)

    # Transient sharpener: boost the first 8 ms (kick attack region)
    attack_n = min(int(SAMPLE_RATE * 0.008), len(arr))
    if attack_n > 0:
        arr[:attack_n] *= 1.35

    # Overall level is controlled, not loud — the kit is in service of the tension
    arr *= 0.80

    # Hard clip to remove any stray peaks from the transient boost
    arr = arr.clip(-1.0, 1.0)
    return arr


def cargo_alarm_callback(alarm_level: float, master_fx=None):
    """Upload countdown active (alarm_level > 0) → freeze arp + drum stems.
    Implemented by audio_manager checking cargo_alarm > 0 and suppressing
    the signature_instrument channel. This callback is a hook for any
    per-frame master-bus work; the stem gating happens upstream.
    """
    pass


# Stem priority — chapter 6: bass is the building's heartbeat (full volume).
# Drums are present but subordinate. Arp stripped right back — the harmony
# is too tense to let the arp breathe freely.
STEM_GATES = {
    "drum": 0.70,
    "bass": 1.00,
    "arp":  0.45,
}
