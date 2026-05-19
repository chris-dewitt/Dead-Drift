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


# ---------------------------------------------------------------------------
# New SFX — event-driven one-shots

def death_sting() -> pygame.mixer.Sound:
    """Descending synth chord on ship destroyed — two-octave fall over 3s."""
    dur = 3.0
    t   = _t(dur)
    # Three-voice descending chord — exponential frequency fall
    freqs = [440.0, 554.4, 659.3]   # A4, C#5, E5 — minor third + fifth
    w = np.zeros(int(SAMPLE_RATE * dur))
    for f0 in freqs:
        inst_f = f0 * np.exp(-t * 1.3)   # drops ~2 octaves over 3s
        phase  = np.cumsum(_2PI * inst_f / SAMPLE_RATE)
        w     += np.sin(phase) * 0.28
    w += _noise(dur, amp=0.03)
    env = np.exp(-t * 0.6) * 0.80   # smooth long decay
    return _to_sound((w * env).clip(-1.0, 1.0))


def slingshot_whoosh() -> pygame.mixer.Sound:
    """Rising speed rush on successful slingshot."""
    dur = 0.65
    t   = _t(dur)
    inst_f = np.linspace(70.0, 1400.0, len(t)) * (0.92 + 0.08 * np.sin(_2PI * 18 * t))
    phase  = np.cumsum(_2PI * inst_f / SAMPLE_RATE)
    w  = np.sin(phase) * 0.55
    w += _noise(dur, amp=0.10)
    return _to_sound(_adsr(w, 0.008, 0.18, 0.48, 0.35))


def canister_chime() -> pygame.mixer.Sound:
    """Bright C-major arpeggio on fuel pickup."""
    notes = [523.25, 659.25, 783.99, 1046.5]   # C5 E5 G5 C6
    segs  = []
    for freq in notes:
        dur  = 0.10
        t    = _t(dur)
        blip = np.sin(_2PI * freq * t) * 0.55
        blip += np.sin(_2PI * freq * 2 * t) * 0.16
        blip  = _adsr(blip, 0.002, 0.025, 0.65, 0.06)
        segs.append(blip)
        segs.append(np.zeros(int(SAMPLE_RATE * 0.028)))
    wave = np.concatenate(segs)
    return _to_sound(wave.clip(-1.0, 1.0))


def barge_alert() -> pygame.mixer.Sound:
    """Sharp descending chirp when barge enters proximity range."""
    dur  = 0.38
    t    = _t(dur)
    f    = np.linspace(1100.0, 380.0, len(t))
    phase = np.cumsum(_2PI * f / SAMPLE_RATE)
    w     = np.sin(phase) * 0.65
    w    += np.sin(phase * 2) * 0.20
    w    += _noise(dur, amp=0.05)
    return _to_sound(_adsr(w, 0.001, 0.05, 0.42, 0.20))


def delivery_footstep() -> pygame.mixer.Sound:
    """Soft metallic tap — courier boots on deck plate."""
    dur = 0.048
    n   = int(SAMPLE_RATE * dur)
    t   = np.linspace(0.0, dur, n, endpoint=False)
    env = np.exp(-t * 70.0)
    w   = np.random.uniform(-1.0, 1.0, n) * 0.45 * env
    w  += np.sin(_2PI * 260.0 * t) * 0.18 * env
    return _to_sound(w)


def delivery_hit_sting() -> pygame.mixer.Sound:
    """Sharp dissonant shock on obstacle contact."""
    dur = 0.20
    t   = _t(dur)
    f   = np.linspace(900.0, 140.0, len(t))
    phase = np.cumsum(_2PI * f / SAMPLE_RATE)
    w   = np.sin(phase) * 0.50
    w  += _noise(dur, amp=0.38)
    w  += _sine(55.0, dur, amp=0.28)
    return _to_sound(_adsr(w, 0.001, 0.04, 0.18, 0.12))


def delivery_door_chime() -> pygame.mixer.Sound:
    """Rising triumphant chord — reached the drop-off."""
    notes = [523.25, 659.25, 783.99, 1046.5, 1318.51]   # C5 E5 G5 C6 E6
    segs  = []
    for i, freq in enumerate(notes):
        dur  = 0.10 + i * 0.018
        t    = _t(dur)
        blip = np.sin(_2PI * freq * t) * 0.52
        blip += np.sin(_2PI * freq * 2 * t) * 0.14
        blip  = _adsr(blip, 0.001, 0.02, 0.72, 0.08)
        segs.append(blip)
        segs.append(np.zeros(int(SAMPLE_RATE * max(0.005, 0.022 - i * 0.003))))
    return _to_sound(np.concatenate(segs).clip(-1.0, 1.0))


def jump_ready_charge() -> pygame.mixer.Sound:
    """Rising capacitor charge — signals the jump window is open."""
    dur = 1.10
    t   = _t(dur)
    # Sweeping tone: starts low, accelerates up
    freq = np.linspace(55.0, 880.0, len(t)) ** 0.95
    phase = np.cumsum(_2PI * freq / SAMPLE_RATE)
    w  = np.sin(phase) * 0.45
    w += np.sin(phase * 2) * 0.18
    w += np.sin(phase * 3) * 0.08
    w += _noise(dur, amp=0.04)
    # Swell: quiet → loud → hold
    env = np.zeros(len(t))
    sw  = int(SAMPLE_RATE * 0.72)
    env[:sw]  = np.linspace(0.0, 1.0, sw) ** 1.6
    env[sw:]  = 1.0
    w = w * env
    w += _sine(440.0, dur, amp=0.22) * (0.5 + 0.5 * np.sin(_2PI * 8.0 * t))
    return _to_sound(_adsr(w.clip(-1.0, 1.0), 0.01, 0.10, 0.80, 0.15))


def debt_ding() -> pygame.mixer.Sound:
    """Sharp descending two-tone sting — debt milestone reached."""
    dur = 0.38
    w  = _sine(660.0, dur, amp=0.45)
    w += _sine(440.0, dur, amp=0.32)
    w += _noise(dur, amp=0.03)
    return _to_sound(_adsr(w, 0.002, 0.05, 0.40, 0.28))


def terminal_drone(duration: float = 6.0) -> pygame.mixer.Sound:
    """Ominous Am-chord pad that loops during terminal interrogation."""
    t       = _t(duration)
    lfo_a   = 0.72 + 0.28 * np.sin(_2PI * 0.07 * t)
    lfo_b   = 0.86 + 0.14 * np.sin(_2PI * 0.13 * t + 1.2)

    w  = _sine(110.0, duration, amp=0.26) * lfo_a   # A2
    w += _sine(130.8, duration, amp=0.16) * lfo_b   # C3
    w += _sine(164.8, duration, amp=0.11) * lfo_a   # E3
    w += _sine(55.0,  duration, amp=0.20)            # A1 sub
    w += _noise(duration, amp=0.018) * lfo_b         # radio texture

    # Seamless loop fade at edges
    n    = len(w)
    fade = int(SAMPLE_RATE * 0.9)
    w[:fade]  *= np.linspace(0.0, 1.0, fade)
    w[-fade:] *= np.linspace(1.0, 0.0, fade)
    return _to_sound((w * 0.65).clip(-1.0, 1.0))
