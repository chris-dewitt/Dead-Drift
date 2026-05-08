"""
Procedural sound generation — numpy only, no audio files required.
All sounds returned as pygame.mixer.Sound objects ready to play.
"""
from __future__ import annotations
import numpy as np
import pygame

SAMPLE_RATE = 44100
_2PI = 2.0 * np.pi


def _to_sound(wave: np.ndarray) -> pygame.mixer.Sound:
    clipped = wave.clip(-1.0, 1.0)
    scaled  = (clipped * 32767).astype(np.int16)
    stereo  = np.column_stack([scaled, scaled])
    return pygame.sndarray.make_sound(stereo)


def _t(duration: float) -> np.ndarray:
    return np.linspace(0.0, duration, int(SAMPLE_RATE * duration), endpoint=False)


def _sine(freq: float, duration: float, amp: float = 1.0) -> np.ndarray:
    return np.sin(_2PI * freq * _t(duration)) * amp


def _saw(freq: float, duration: float, amp: float = 1.0) -> np.ndarray:
    t = _t(duration)
    return (2.0 * ((t * freq) % 1.0) - 1.0) * amp


def _noise(duration: float, amp: float = 1.0) -> np.ndarray:
    return np.random.uniform(-1.0, 1.0, int(SAMPLE_RATE * duration)) * amp


def _adsr(wave: np.ndarray, attack: float, decay: float,
          sustain: float, release: float) -> np.ndarray:
    n  = len(wave)
    a  = min(int(attack  * SAMPLE_RATE), n)
    d  = min(int(decay   * SAMPLE_RATE), n - a)
    r  = min(int(release * SAMPLE_RATE), n)
    r0 = max(0, n - r)
    env = np.empty(n)
    env[:a]     = np.linspace(0.0, 1.0, a)
    env[a:a+d]  = np.linspace(1.0, sustain, d)
    env[a+d:r0] = sustain
    env[r0:]    = np.linspace(sustain, 0.0, n - r0)
    return wave * env


# ---------------------------------------------------------------------------
# Engine drones — 5 speed tiers, space-blues character

def engine_drone(tier: int, duration: float = 3.0) -> pygame.mixer.Sound:
    """
    Sawtooth fundamental + harmonic stack + slow LFO wail.
    tier 0 = idle drift, tier 4 = redline.
    """
    base = [52.0, 64.0, 78.0, 96.0, 118.0][tier]
    t    = _t(duration)
    lfo  = 0.65 + 0.35 * np.sin(_2PI * 0.38 * t)   # 0.38 Hz blues moan

    w  = _saw(base, duration, amp=0.28)
    w += _sine(base * 2,    duration, amp=[0.06, 0.09, 0.13, 0.17, 0.20][tier])
    w += _sine(base * 1.78, duration, amp=[0.00, 0.03, 0.06, 0.10, 0.14][tier]) * lfo
    w += _sine(base * 3,    duration, amp=[0.02, 0.04, 0.07, 0.10, 0.13][tier]) * (0.8 + 0.2 * lfo)
    w += _sine(base * 0.5,  duration, amp=0.12)   # sub-bass thump

    peak = np.max(np.abs(w))
    if peak > 0:
        w = w / peak * 0.70
    return _to_sound(w)


def ambient_static(duration: float = 4.0) -> pygame.mixer.Sound:
    """Deep space hiss — slow-swelling broadband noise + infra-bass rumble."""
    w  = _noise(duration, amp=0.06)
    w += _sine(28.0, duration, amp=0.05)
    w += _sine(41.0, duration, amp=0.03)
    n     = len(w)
    swell = 0.70 + 0.30 * np.sin(_2PI * 0.06 * np.linspace(0.0, duration, n))
    return _to_sound(w * swell)


# ---------------------------------------------------------------------------
# One-shot SFX

def gun_shot() -> pygame.mixer.Sound:
    dur = 0.09
    w = _noise(dur, amp=0.88) + _saw(260.0, dur, amp=0.32)
    return _to_sound(_adsr(w, 0.001, 0.045, 0.08, 0.04))


def hull_impact() -> pygame.mixer.Sound:
    dur = 0.40
    # Downward frequency chirp 190 → 40 Hz
    inst = np.linspace(190.0, 40.0, int(SAMPLE_RATE * dur))
    phase = np.cumsum(_2PI * inst / SAMPLE_RATE)
    w = np.sin(phase) * 0.65 + _noise(dur, amp=0.18)
    return _to_sound(_adsr(w, 0.001, 0.08, 0.30, 0.20))


def tether_clang() -> pygame.mixer.Sound:
    dur = 0.65
    w  = _sine(880.0,  dur, amp=0.48)
    w += _sine(1340.0, dur, amp=0.26)
    w += _sine(2080.0, dur, amp=0.11)
    w += _noise(dur, amp=0.04)
    return _to_sound(_adsr(w, 0.001, 0.05, 0.18, 0.55))


def tether_snap() -> pygame.mixer.Sound:
    dur = 0.14
    return _to_sound(_adsr(_noise(dur, amp=1.0), 0.001, 0.03, 0.30, 0.10))


def terminal_beep() -> pygame.mixer.Sound:
    dur = 0.055
    w = _sine(1100.0, dur, amp=0.33) + _sine(1650.0, dur, amp=0.13)
    return _to_sound(_adsr(w, 0.003, 0.018, 0.5, 0.025))


def spore_sting() -> pygame.mixer.Sound:
    """Psychedelic warble played when controls invert."""
    dur = 0.55
    t   = _t(dur)
    # Two detuned sines with LFO pitch drift
    lfo = np.sin(_2PI * 3.5 * t)
    w   = np.sin(_2PI * (220.0 + 40.0 * lfo) * t) * 0.35
    w  += np.sin(_2PI * (330.0 - 30.0 * lfo) * t) * 0.25
    w  += _noise(dur, amp=0.06)
    return _to_sound(_adsr(w, 0.01, 0.10, 0.6, 0.30))
