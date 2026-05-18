"""
Procedural character voice blips — formant synthesis, numpy only.

Each character has a distinct voice 'texture' built from:
  - A harmonic stack at a characteristic fundamental frequency
  - Bandpass filtering to shape the formant envelope
  - A noise component (breathiness / static / grain)
  - A short ADSR envelope tuned to the character's speaking style

BAX         warm mid-range robot, slight wobble — Cockney android
GARY        breathy organic human, nasal, tired
TK-9        thin digital buzz, high-pitched, robotic precision
DISPATCHER  flat nasal monotone, bureaucratic droning
KRESS       deep crackly comm-link, heavy static
"""
from __future__ import annotations
import numpy as np
import pygame
from audio.synth import SAMPLE_RATE, _2PI, _to_sound, _adsr


# ---------------------------------------------------------------------------
# FFT bandpass — shapes the formant character of each voice

def _bandpass(wave: np.ndarray, low: float, high: float) -> np.ndarray:
    n = len(wave)
    if n < 8:
        return wave
    spec  = np.fft.rfft(wave)
    freqs = np.fft.rfftfreq(n, 1.0 / SAMPLE_RATE)
    spec[(freqs < low) | (freqs > high)] = 0.0
    return np.fft.irfft(spec, n)


# ---------------------------------------------------------------------------
# Voice profiles
#
# (dur_ms, fund_hz, bp_low, bp_high, noise_ratio, harmonics, env_ratios)
#   harmonics    — amplitude of each harmonic starting at fundamental
#   env_ratios   — (attack_s, decay_frac, sustain_lvl, release_frac)
#                  decay and release are fractions of total duration

_VOICES: dict[str, tuple] = {
    "bax": (
        52, 380, 260, 920, 0.07,
        [1.0, 0.48, 0.20, 0.07],
        (0.005, 0.28, 0.38, 0.42),
    ),
    "gary": (
        68, 310, 280, 1180, 0.18,
        [1.0, 0.55, 0.28, 0.10],
        (0.010, 0.32, 0.52, 0.38),
    ),
    "tk-9": (
        28, 1200, 680, 2800, 0.02,
        [1.0, 0.72, 0.52, 0.33, 0.18],
        (0.001, 0.14, 0.12, 0.72),
    ),
    "dispatcher": (
        62, 268, 195, 610, 0.04,
        [1.0, 0.38, 0.14, 0.04],
        (0.005, 0.22, 0.62, 0.34),
    ),
    "kress": (
        80, 168, 88, 445, 0.26,
        [1.0, 0.42, 0.18, 0.06],
        (0.008, 0.16, 0.52, 0.42),
    ),
}
_DEFAULT = (
    58, 440, 300, 1200, 0.12,
    [1.0, 0.50, 0.20],
    (0.006, 0.26, 0.42, 0.40),
)


def _make_one(profile: tuple, rng: np.random.Generator) -> np.ndarray:
    dur_ms, fund, bp_lo, bp_hi, noise_r, harmonics, env_r = profile

    # Pitch variation per blip — makes repeated blips feel natural, not robotic
    pitch_mul = 1.0 + rng.uniform(-0.09, 0.09)
    f   = fund * pitch_mul
    dur = dur_ms / 1000.0
    n   = int(SAMPLE_RATE * dur)
    t   = np.linspace(0.0, dur, n, endpoint=False)

    # Harmonic stack (voiced excitation)
    wave = np.zeros(n)
    for idx, amp in enumerate(harmonics, 1):
        wave += np.sin(_2PI * f * idx * t) * amp

    # Add breathiness / static layer
    wave += rng.uniform(-1.0, 1.0, n) * noise_r

    # Bandpass → formant shaping
    wave = _bandpass(wave, bp_lo, bp_hi)

    # ADSR envelope
    a, d_frac, s, r_frac = env_r
    wave = _adsr(wave, a, d_frac * dur, s, r_frac * dur)

    # Normalise to consistent amplitude
    peak = np.max(np.abs(wave))
    if peak > 0.001:
        wave = wave / peak * 0.65

    return wave


def make_voice_blips(character: str, n_vars: int = 5) -> list[pygame.mixer.Sound]:
    """Generate N pitch-varied blips for one character. Cache these at startup."""
    profile = _VOICES.get(character.lower(), _DEFAULT)
    # Deterministic seed per character so voices are reproducible across sessions
    rng     = np.random.default_rng(abs(hash(character)) % (2 ** 31))
    return [_to_sound(_make_one(profile, rng)) for _ in range(n_vars)]


def prebuild_voices() -> dict[str, list[pygame.mixer.Sound]]:
    """Pre-generate blip sets for every known character. Call once at startup."""
    return {char: make_voice_blips(char) for char in _VOICES}
