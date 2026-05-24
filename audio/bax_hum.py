"""
Dead Drift — Bax hums.
Per SOUNDTRACK_PLAN §7.4.

Eight wordless hummed melodies, 4 bars each at 84 BPM, in A natural minor.
Triggered once per run on the first delivery success.  Hum 7 is reserved
for Chapter 4 deliveries (campaign-clear hum).

Voice = triangle wave + breath noise + slight vibrato, detuned -6 cents
to match the Bax-flat tuning of the harmonica (§2.2).  All melodies are
descending as their primary motion.
"""
from __future__ import annotations
import numpy as np
import pygame
from audio.synth import SAMPLE_RATE, _2PI, _to_sound, _adsr, _t

# --- Scale & timing --------------------------------------------------------
_ROOT_FREQ   = 220.0    # A3 — A natural minor root
_DETUNE_CENT = -6.0     # §2.2 — Bax-flat
_BPM         = 84.0
_BEAT_S      = 60.0 / _BPM
_BAR_S       = _BEAT_S * 4

# Scale-degree → semitones above the root (A natural minor: A B C D E F G)
_DEGREE_MAP: dict[str, int] = {
    "1": 0, "2": 2, "b3": 3, "4": 5, "5": 7, "b6": 8, "b7": 10, "8": 12,
}


def _semitone_freq(degree: str) -> float:
    """Hz for a scale degree in A natural minor, detuned -6 cents."""
    n = _DEGREE_MAP[degree] + _DETUNE_CENT / 100.0
    return _ROOT_FREQ * (2.0 ** (n / 12.0))


# --- Voice ------------------------------------------------------------------
def _hum_voice(freq: float, duration: float, amp: float = 0.30) -> np.ndarray:
    """
    Triangle wave (lips-closed timbre) + faint breath noise + 4 Hz vibrato.
    120 ms attack, 600 ms release — never staccato; this is a *hum*.
    """
    t = _t(duration)
    # 4 Hz vibrato, ±10 cents
    vib   = 1.0 + 0.006 * np.sin(_2PI * 4.0 * t)
    phase = np.cumsum(_2PI * freq * vib / SAMPLE_RATE)

    # Triangle from a saw (cheap, no aliasing concerns at A4 and below)
    saw = 2.0 * (phase / _2PI - np.floor(0.5 + phase / _2PI))
    tri = 1.0 - 2.0 * np.abs(saw)

    # Faint breath layer — gives the hum a "through closed lips" body
    breath = np.random.uniform(-1.0, 1.0, len(t)).astype(np.float32) * 0.05

    wave = (tri * 0.92 + breath) * amp
    return _adsr(wave, attack=0.12, decay=0.10, sustain=0.85, release=0.6)


# --- Melody assembly --------------------------------------------------------
def _render_melody(notes: list[tuple[str, float]]) -> pygame.mixer.Sound:
    """
    notes — list of (scale_degree, beats).  Each note's audible duration is
    its beats × 1.08 (slight legato bleed into the next), and there's a 0.6 s
    tail to let the final note's release breathe.
    """
    total_beats = sum(n[1] for n in notes)
    total_dur   = max(11.0, total_beats * _BEAT_S + 0.6)
    out         = np.zeros(int(SAMPLE_RATE * total_dur), dtype=np.float32)
    pos_s       = 0.0
    for deg, beats in notes:
        freq = _semitone_freq(deg)
        # 8% legato bleed → connected, not staccato
        dur  = beats * _BEAT_S * 1.08
        v    = _hum_voice(freq, dur)
        start = int(pos_s * SAMPLE_RATE)
        end   = min(start + len(v), len(out))
        out[start:end] += v[:end - start]
        pos_s += beats * _BEAT_S
    return _to_sound(out.clip(-1.0, 1.0))


# --- The 8 hums -------------------------------------------------------------
# Format: list of (scale_degree, beats).  Beats sum near 16 (4 bars at 4/4).
_HUMS: list[list[tuple[str, float]]] = [
    # 0 — Standard Issue: the canonical descending A-G-E-D-C-A (plan example)
    [("1", 2), ("b7", 2), ("5", 2), ("4", 2), ("b3", 2), ("1", 6)],
    # 1 — Long Way Home: descending through b6
    [("1", 2), ("b7", 1.5), ("b6", 1.5), ("5", 2), ("4", 3), ("1", 6)],
    # 2 — Two Step Drift: low-energy pairs
    [("1", 1), ("5", 1), ("b3", 1), ("2", 1), ("1", 2),
     ("1", 1), ("5", 1), ("b3", 1), ("b7", 1), ("1", 5)],
    # 3 — Quarter to Three: arch that loops back
    [("1", 2), ("b3", 2), ("2", 2), ("1", 2), ("b7", 2), ("1", 6)],
    # 4 — Receipt Tape: paired notes — matches the decanting printer rhythm
    [("1", 1), ("1", 1), ("b7", 1), ("b7", 1),
     ("5", 1), ("5", 1), ("4", 2), ("1", 8)],
    # 5 — Empty Cab: slow climb and slow fall
    [("1", 3), ("b3", 3), ("5", 4), ("b3", 3), ("1", 3)],
    # 6 — Last Lap: modal descending
    [("b3", 2), ("2", 2), ("1", 2), ("b7", 2), ("b6", 2), ("5", 6)],
    # 7 — Sign Here Please: campaign-clear hum, settles content
    [("1", 1), ("2", 1), ("b3", 2), ("2", 1), ("1", 3),
     ("1", 1), ("2", 1), ("b3", 2), ("1", 4)],
]

_HUM_TITLES: list[str] = [
    "STANDARD ISSUE",
    "LONG WAY HOME",
    "TWO STEP DRIFT",
    "QUARTER TO THREE",
    "RECEIPT TAPE",
    "EMPTY CAB",
    "LAST LAP",
    "SIGN HERE PLEASE",
]

# Hum 7 is reserved as the campaign-clear (Chapter 4 delivery) hum.
CAMPAIGN_CLEAR_HUM_IDX: int = 7


def build_hum(idx: int) -> pygame.mixer.Sound:
    if not 0 <= idx < len(_HUMS):
        raise IndexError(f"hum index {idx} out of range 0..{len(_HUMS) - 1}")
    return _render_melody(_HUMS[idx])


def prebuild_all_hums() -> list[pygame.mixer.Sound]:
    return [build_hum(i) for i in range(len(_HUMS))]


def hum_count() -> int:
    return len(_HUMS)


def hum_title(idx: int) -> str:
    return _HUM_TITLES[idx]
