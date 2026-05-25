"""
Procedural character voice blips — formant synthesis, numpy only.

Each character has a distinct voice built from harmonics, bandpass formants,
optional vibrato, formant sweeps, and comm-radio degradation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import pygame

from audio.synth import SAMPLE_RATE, _2PI, _to_sound, _adsr


# ---------------------------------------------------------------------------
# Speaker name → profile key (aliases for terminal / comms labels)

_SPEAKER_ALIASES: dict[str, str] = {
    "bax": "bax",
    "gary": "gary",
    "tk-9": "tk-9",
    "tk9": "tk-9",
    "synthetic_droid": "tk-9",
    "dispatcher": "union_dispatcher",
    "union dispatcher": "union_dispatcher",
    "union_dispatcher": "union_dispatcher",
    "kress": "kress",
    "morwenna": "insurance_adjuster",
    "insurance_adjuster": "insurance_adjuster",
    "insurance adjuster": "insurance_adjuster",
    "rep. legal": "union_dispatcher",
    "rep legal": "union_dispatcher",
    "sandra": "sandra",
    "krellborn": "pirate",
    "pirate": "pirate",
    "marrow": "underground_dj",
    "underground_dj": "underground_dj",
    "underground dj": "underground_dj",
    "toll authority": "toll_authority",
    "toll_authority": "toll_authority",
    "medi-corp": "medi_corp",
    "medi corp": "medi_corp",
    "medi_corp": "medi_corp",
    "dock-7": "dock_7",
    "dock 7": "dock_7",
    "dock_7": "dock_7",
    "galactic infra.": "union_dispatcher",
    "galactic infra": "union_dispatcher",
    "unknown": "default",
    "system": "default",
    "you": "default",
}


def resolve_voice_key(speaker: str) -> str:
    """Map display speaker label to a voice profile key."""
    raw = speaker.strip().lower()
    raw = raw.lstrip("[").rstrip("]").strip()
    if raw in _SPEAKER_ALIASES:
        return _SPEAKER_ALIASES[raw]
    compact = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    if compact in _VOICES:
        return compact
    if raw in _VOICES:
        return raw
    return "default"


@dataclass(frozen=True)
class VoiceProfile:
    dur_ms: float
    fund_hz: float
    bp_lo: float
    bp_hi: float
    noise_ratio: float
    harmonics: tuple[float, ...]
    env: tuple[float, float, float, float]  # attack, decay_frac, sustain, release_frac
    bp_lo_end: float | None = None
    bp_hi_end: float | None = None
    vibrato_hz: float = 0.0
    vibrato_depth: float = 0.0
    wobble_hz: float = 0.0
    wobble_depth: float = 0.0
    comm_static: bool = False
    comm_crush: bool = False


def _bandpass(wave: np.ndarray, low: float, high: float) -> np.ndarray:
    n = len(wave)
    if n < 8:
        return wave
    lo = max(20.0, low)
    hi = min(SAMPLE_RATE * 0.45, max(lo + 40.0, high))
    spec = np.fft.rfft(wave)
    freqs = np.fft.rfftfreq(n, 1.0 / SAMPLE_RATE)
    spec[(freqs < lo) | (freqs > hi)] = 0.0
    return np.fft.irfft(spec, n)


def _apply_comm_fx(wave: np.ndarray, static: bool, crush: bool) -> np.ndarray:
    if not static and not crush:
        return wave
    out = wave.copy()
    if crush:
        steps = 8
        crushed = np.repeat(out[::steps], steps)[: len(out)]
        out = crushed
    if static:
        rng = np.random.default_rng(7)
        for i in range(0, len(out), 120):
            if rng.random() < 0.35:
                end = min(len(out), i + rng.integers(8, 28))
                out[i:end] *= rng.uniform(0.0, 0.25)
        out += rng.uniform(-0.15, 0.15, len(out))
    peak = np.max(np.abs(out))
    if peak > 0.001:
        out = out / peak * 0.7
    return out


def _make_one(profile: VoiceProfile, rng: np.random.Generator,
              pitch_mult: float = 1.0) -> np.ndarray:
    pitch_mul = (1.0 + rng.uniform(-0.11, 0.11)) * pitch_mult
    f0 = profile.fund_hz * pitch_mul
    dur = profile.dur_ms / 1000.0
    n = max(8, int(SAMPLE_RATE * dur))
    t = np.linspace(0.0, dur, n, endpoint=False)

    phase = _2PI * f0 * t
    if profile.vibrato_hz > 0:
        phase += profile.vibrato_depth * np.sin(_2PI * profile.vibrato_hz * t)
    if profile.wobble_hz > 0:
        phase += profile.wobble_depth * np.sin(_2PI * profile.wobble_hz * t + 0.7)

    wave = np.zeros(n)
    for idx, amp in enumerate(profile.harmonics, 1):
        wave += np.sin(phase * idx) * amp

    wave += rng.uniform(-1.0, 1.0, n) * profile.noise_ratio

    if profile.bp_lo_end is not None and profile.bp_hi_end is not None:
        lo_track = np.linspace(profile.bp_lo, profile.bp_lo_end, n)
        hi_track = np.linspace(profile.bp_hi, profile.bp_hi_end, n)
        chunks = 4
        chunk_n = max(1, n // chunks)
        filtered = np.zeros(n)
        for c in range(chunks):
            i0 = c * chunk_n
            i1 = n if c == chunks - 1 else (c + 1) * chunk_n
            filtered[i0:i1] = _bandpass(wave[i0:i1], lo_track[i0], hi_track[i0])
        wave = filtered
    else:
        wave = _bandpass(wave, profile.bp_lo, profile.bp_hi)

    a, d_frac, s, r_frac = profile.env
    wave = _adsr(wave, a, d_frac * dur, s, r_frac * dur)
    wave = _apply_comm_fx(wave, profile.comm_static, profile.comm_crush)

    peak = np.max(np.abs(wave))
    if peak > 0.001:
        wave = wave / peak * 0.65
    return wave


_VOICES: dict[str, VoiceProfile] = {
    "bax": VoiceProfile(
        68, 410, 260, 920, 0.06,
        (1.0, 0.58, 0.30, 0.12, 0.05),
        (0.004, 0.20, 0.48, 0.36),
        vibrato_hz=5.5, vibrato_depth=0.04,
        wobble_hz=2.2, wobble_depth=0.03,
    ),
    "gary": VoiceProfile(
        88, 245, 200, 1350, 0.34,
        (1.0, 0.64, 0.36, 0.14),
        (0.014, 0.32, 0.52, 0.40),
        bp_lo_end=280, bp_hi_end=1100,
        vibrato_hz=3.0, vibrato_depth=0.025,
    ),
    "tk-9": VoiceProfile(
        28, 1650, 950, 3800, 0.01,
        (1.0, 0.82, 0.64, 0.42, 0.24),
        (0.001, 0.08, 0.06, 0.82),
    ),
    "union_dispatcher": VoiceProfile(
        82, 205, 150, 500, 0.03,
        (1.0, 0.32, 0.10, 0.03),
        (0.004, 0.16, 0.70, 0.26),
    ),
    "kress": VoiceProfile(
        98, 125, 65, 340, 0.44,
        (1.0, 0.38, 0.14, 0.05),
        (0.012, 0.12, 0.45, 0.46),
        comm_static=True, comm_crush=True,
    ),
    "medi_corp": VoiceProfile(
        76, 310, 180, 720, 0.38,
        (1.0, 0.40, 0.12),
        (0.008, 0.14, 0.42, 0.44),
        comm_static=True,
    ),
    "dock_7": VoiceProfile(
        90, 175, 120, 480, 0.28,
        (1.0, 0.45, 0.18),
        (0.010, 0.22, 0.55, 0.38),
        bp_lo_end=140, bp_hi_end=420,
    ),
    "insurance_adjuster": VoiceProfile(
        74, 280, 220, 880, 0.12,
        (1.0, 0.50, 0.22, 0.08),
        (0.006, 0.24, 0.50, 0.34),
        vibrato_hz=4.0, vibrato_depth=0.02,
    ),
    "sandra": VoiceProfile(
        70, 520, 380, 1400, 0.08,
        (1.0, 0.48, 0.20),
        (0.005, 0.18, 0.55, 0.30),
        vibrato_hz=6.0, vibrato_depth=0.035,
    ),
    "pirate": VoiceProfile(
        85, 195, 140, 620, 0.22,
        (1.0, 0.55, 0.24, 0.10),
        (0.010, 0.28, 0.48, 0.38),
        bp_lo_end=180, bp_hi_end=750,
    ),
    "underground_dj": VoiceProfile(
        64, 360, 200, 1200, 0.18,
        (1.0, 0.60, 0.28, 0.12),
        (0.003, 0.20, 0.42, 0.42),
        vibrato_hz=7.0, vibrato_depth=0.05,
        wobble_hz=1.5, wobble_depth=0.04,
    ),
    "toll_authority": VoiceProfile(
        80, 230, 170, 560, 0.10,
        (1.0, 0.35, 0.12, 0.04),
        (0.005, 0.20, 0.62, 0.30),
    ),
    "default": VoiceProfile(
        62, 430, 290, 1050, 0.16,
        (1.0, 0.50, 0.22),
        (0.006, 0.24, 0.44, 0.38),
    ),
}


def make_voice_blips(character: str, n_vars: int = 10,
                     pitch_mult: float = 1.0) -> list[pygame.mixer.Sound]:
    key = resolve_voice_key(character)
    profile = _VOICES.get(key, _VOICES["default"])
    rng = np.random.default_rng(abs(hash(key)) % (2 ** 31))
    return [_to_sound(_make_one(profile, rng, pitch_mult)) for _ in range(n_vars)]


def prebuild_voices() -> dict[str, list[pygame.mixer.Sound]]:
    """Pre-generate blip sets for every profile key."""
    return {key: make_voice_blips(key) for key in _VOICES}


# Epic 7.4 — Bax hull-tier pitch variants (voice goes higher under damage).
# Three tiers: 1.0 (healthy / ≥30% hull), 1.05 (<30%), 1.12 (<10%).
BAX_PITCH_TIERS: tuple[float, ...] = (1.0, 1.05, 1.12)


def prebuild_bax_pitch_tiers(n_vars: int = 10) -> list[list[pygame.mixer.Sound]]:
    """Pre-generate the three Bax pitch tiers used by AudioManager."""
    return [make_voice_blips("bax", n_vars=n_vars, pitch_mult=m)
            for m in BAX_PITCH_TIERS]
