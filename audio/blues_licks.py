"""
Procedural blues licks and harmonica ditties for mid-flight ambience.
Synthesized with numpy — no audio files required.
"""
from __future__ import annotations
import random
import numpy as np
import pygame
from audio.synth import SAMPLE_RATE, _2PI, _to_sound, _adsr, _t

# ---------------------------------------------------------------------------
# A blues / minor-pentatonic note frequencies (Hz)
_NOTES = {
    'A1': 55.0,  'C2': 65.4,  'D2': 73.4,  'Eb2': 77.8,  'E2': 82.4,  'G2': 98.0,
    'A2': 110.0, 'C3': 130.8, 'D3': 146.8, 'Eb3': 155.6, 'E3': 164.8, 'G3': 196.0,
    'A3': 220.0, 'C4': 261.6, 'D4': 293.7, 'Eb4': 311.1, 'E4': 329.6, 'G4': 392.0,
}


def _harp_note(freq: float, duration: float, amp: float = 0.82,
               bend: float = 0.0) -> np.ndarray:
    """Single harmonica note — reedy timbre, slight vibrato, breathiness."""
    tv = _t(duration)
    vibrato = 1.0 + 0.016 * np.sin(_2PI * 5.6 * tv)
    pitch   = freq * (1.0 + bend) * vibrato
    phase   = np.cumsum(_2PI * pitch / SAMPLE_RATE)

    w  = np.sin(phase) * 0.48
    w += np.sin(phase * 2) * 0.20
    w += np.sin(phase * 3) * 0.09
    w += np.sin(phase * 4) * 0.04
    w += np.random.uniform(-1.0, 1.0, len(tv)) * 0.018   # breathiness

    return _adsr(w, 0.018, 0.04, 0.88, 0.14) * amp


# ---------------------------------------------------------------------------
# Lick patterns: list of (note_name, duration_s, gap_after_s, bend_ratio)
#   bend_ratio > 0 → pitch-bend up midway (blues "push")

_LICK_PATTERNS = [
    # 0 — Classic turnaround — ascending run up the blue note
    [('A2', 0.14, 0.02, 0.0), ('C3', 0.11, 0.02, 0.0),
     ('D3', 0.11, 0.0,  0.0), ('Eb3', 0.07, 0.0, 0.0),
     ('E3', 0.22, 0.08, 0.0), ('D3', 0.18, 0.0, 0.0)],

    # 1 — High wail and fall
    [('A3', 0.16, 0.02, 0.03), ('G3', 0.12, 0.0, 0.0),
     ('E3', 0.22, 0.10, 0.0),  ('D3', 0.14, 0.04, 0.0),
     ('C3', 0.32, 0.0,  0.0)],

    # 2 — Call and response
    [('E3', 0.10, 0.0,  0.0), ('D3', 0.10, 0.04, 0.0), ('C3', 0.18, 0.18, 0.0),
     ('A3', 0.09, 0.0,  0.0), ('G3', 0.09, 0.0,  0.0), ('E3', 0.26, 0.0,  0.0)],

    # 3 — Low delta growl
    [('A1', 0.20, 0.04, 0.0), ('C2', 0.14, 0.0, 0.0),
     ('D2', 0.14, 0.0,  0.0), ('E2', 0.28, 0.08, 0.0),
     ('G2', 0.12, 0.0,  0.0), ('A2', 0.30, 0.0,  0.0)],

    # 4 — Bent-note cry
    [('D3', 0.08, 0.0, 0.0),  ('E3', 0.18, 0.06, 0.04),
     ('Eb3', 0.12, 0.0, 0.0), ('D3', 0.14, 0.08, 0.0),
     ('C3', 0.12, 0.0, 0.0),  ('A2', 0.28, 0.0,  0.0)],

    # 5 — Syncopated groove
    [('A2', 0.08, 0.04, 0.0), ('A2', 0.08, 0.02, 0.0),
     ('C3', 0.12, 0.0,  0.0), ('D3', 0.08, 0.0,  0.0),
     ('Eb3', 0.06, 0.0, 0.0), ('D3', 0.16, 0.06, 0.0),
     ('A2', 0.24, 0.0,  0.0)],

    # 6 — Chicago shuffle — syncopated up-tempo bounce
    [('A2', 0.07, 0.02, 0.0), ('C3', 0.07, 0.01, 0.0), ('D3', 0.07, 0.02, 0.0),
     ('A2', 0.07, 0.01, 0.0), ('C3', 0.07, 0.01, 0.0), ('E3', 0.11, 0.04, 0.0),
     ('D3', 0.07, 0.01, 0.0), ('C3', 0.07, 0.0,  0.0), ('A2', 0.22, 0.0,  0.0)],

    # 7 — Slow lonesome wail — long breathy bends
    [('A2', 0.36, 0.06, 0.03), ('G2', 0.26, 0.04, 0.0),
     ('A2', 0.44, 0.08, 0.05), ('E2', 0.54, 0.0,  0.0)],

    # 8 — Minor-3rd hammers — quick punch pairs
    [('C3', 0.05, 0.0,  0.0), ('Eb3', 0.14, 0.06, 0.0),
     ('D3', 0.05, 0.0,  0.0), ('E3',  0.18, 0.04, 0.0),
     ('D3', 0.05, 0.0,  0.0), ('C3',  0.22, 0.06, 0.0),
     ('A2', 0.30, 0.0,  0.0)],

    # 9 — High register sundown run — quick descending from A3
    [('A3', 0.09, 0.01, 0.0), ('G3', 0.09, 0.01, 0.0), ('E3', 0.09, 0.01, 0.0),
     ('D3', 0.14, 0.04, 0.0), ('C3', 0.09, 0.01, 0.0), ('A2', 0.28, 0.0,  0.0)],

    # --- NEW PATTERNS ---

    # 10 — cocky: punchy ascending strut, quick notes, confident landing
    [('A2', 0.07, 0.01, 0.0), ('C3', 0.07, 0.01, 0.0),
     ('E3', 0.07, 0.01, 0.0), ('G3', 0.07, 0.01, 0.0),
     ('A3', 0.18, 0.04, 0.02), ('A3', 0.12, 0.0,  0.0)],

    # 11 — cocky: brash short run with a bent top note swagger
    [('C3', 0.06, 0.01, 0.0), ('D3', 0.06, 0.01, 0.0),
     ('E3', 0.06, 0.01, 0.0), ('G3', 0.14, 0.02, 0.04),
     ('E3', 0.10, 0.0,  0.0), ('G3', 0.20, 0.0,  0.0)],

    # 12 — cocky: quick ascending triplet stomp, lands hard on high A
    [('A2', 0.05, 0.01, 0.0), ('D3', 0.05, 0.01, 0.0), ('G3', 0.05, 0.01, 0.0),
     ('A3', 0.05, 0.01, 0.0), ('G3', 0.05, 0.01, 0.0), ('A3', 0.22, 0.0, 0.03)],

    # 13 — weary: slow descending sigh, long low notes
    [('E3', 0.38, 0.10, 0.0), ('D3', 0.32, 0.08, 0.0),
     ('C3', 0.36, 0.12, 0.0), ('A2', 0.54, 0.0,  0.0)],

    # 14 — weary: trudging low register, barely moving
    [('A2', 0.44, 0.12, 0.02), ('G2', 0.38, 0.10, 0.0),
     ('E2', 0.52, 0.14, 0.0),  ('D2', 0.60, 0.0,  0.0)],

    # 15 — weary: slow fall through mid-range, exhausted bends
    [('G3', 0.30, 0.08, 0.0),  ('E3', 0.36, 0.10, 0.03),
     ('C3', 0.40, 0.12, 0.0),  ('A2', 0.48, 0.0,  0.0)],

    # 16 — weary: dragging single-note lament, three long tones
    [('D3', 0.50, 0.14, 0.02), ('C3', 0.46, 0.12, 0.0),
     ('A2', 0.58, 0.0,  0.0)],

    # 17 — panic: fast chaotic scramble up into high register
    [('A2', 0.05, 0.01, 0.0), ('C3', 0.05, 0.01, 0.0), ('E3', 0.05, 0.0,  0.0),
     ('G3', 0.05, 0.01, 0.0), ('A3', 0.05, 0.0,  0.0), ('G4', 0.05, 0.01, 0.0),
     ('E4', 0.05, 0.0,  0.0), ('G4', 0.08, 0.02, 0.04), ('E4', 0.12, 0.0, 0.0)],

    # 18 — panic: frantic high-register flutter, no resolution
    [('E4', 0.05, 0.01, 0.0), ('G4', 0.05, 0.0,  0.0), ('E4', 0.05, 0.01, 0.0),
     ('G4', 0.05, 0.0,  0.0), ('Eb4', 0.05, 0.01, 0.0), ('E4', 0.05, 0.0, 0.0),
     ('G4', 0.10, 0.02, 0.05), ('E4', 0.08, 0.0,  0.0)],

    # 19 — panic: wild ascending then crashing descent
    [('A2', 0.04, 0.0,  0.0), ('E3', 0.04, 0.0,  0.0), ('A3', 0.04, 0.0, 0.0),
     ('E4', 0.04, 0.0,  0.0), ('G4', 0.06, 0.01, 0.03), ('E4', 0.04, 0.0, 0.0),
     ('C4', 0.04, 0.0,  0.0), ('A3', 0.04, 0.0,  0.0), ('E3', 0.14, 0.0, 0.0)],

    # 20 — delighted: bright quick ascending arpeggio, high and playful
    [('A3', 0.07, 0.01, 0.0), ('C4', 0.07, 0.01, 0.0),
     ('E4', 0.07, 0.01, 0.0), ('G4', 0.14, 0.02, 0.0),
     ('E4', 0.07, 0.01, 0.0), ('G4', 0.18, 0.0,  0.0)],

    # 21 — delighted: skipping high notes, buoyant feel
    [('E4', 0.06, 0.02, 0.0), ('G4', 0.06, 0.01, 0.0),
     ('E4', 0.06, 0.02, 0.0), ('C4', 0.06, 0.01, 0.0),
     ('E4', 0.06, 0.01, 0.0), ('G4', 0.20, 0.0,  0.01)],

    # 22 — delighted: playful trill-like bounce in upper mid
    [('C4', 0.05, 0.01, 0.0), ('D4', 0.05, 0.01, 0.0), ('E4', 0.05, 0.01, 0.0),
     ('D4', 0.05, 0.01, 0.0), ('E4', 0.05, 0.01, 0.0), ('G4', 0.16, 0.02, 0.02),
     ('E4', 0.18, 0.0,  0.0)],

    # 23 — lonely: very slow, single long low note then silence
    [('A1', 0.70, 0.30, 0.01), ('G2', 0.60, 0.40, 0.0),
     ('A2', 0.80, 0.0,  0.0)],

    # 24 — lonely: two low tones with a wide empty gap between
    [('D2', 0.55, 0.50, 0.02), ('A2', 0.65, 0.0,  0.0)],

    # 25 — lonely: three notes, all low, enormous space around them
    [('A1', 0.60, 0.45, 0.0), ('E2', 0.55, 0.50, 0.0),
     ('A2', 0.72, 0.0,  0.0)],

    # 26 — lonely: one long sustained low note, slow fade
    [('G2', 0.42, 0.35, 0.0), ('E2', 0.50, 0.40, 0.0),
     ('D2', 0.62, 0.0,  0.0)],

    # 27 — sarcastic: starts high and bright, then drags down flat
    [('G3', 0.08, 0.01, 0.0), ('A3', 0.08, 0.01, 0.02),
     ('G3', 0.10, 0.02, 0.0), ('E3', 0.14, 0.04, 0.0),
     ('C3', 0.30, 0.08, 0.0), ('A2', 0.38, 0.0,  0.0)],

    # 28 — sarcastic: bright opener, implied question hang, falls flat
    [('E3', 0.07, 0.01, 0.0), ('G3', 0.07, 0.01, 0.0), ('A3', 0.10, 0.04, 0.02),
     ('G3', 0.08, 0.02, 0.0), ('E3', 0.12, 0.04, 0.0), ('D3', 0.34, 0.0,  0.0)],

    # 29 — sarcastic: confident ascent to high note, then deflates slowly
    [('A2', 0.06, 0.01, 0.0), ('E3', 0.06, 0.01, 0.0), ('A3', 0.12, 0.02, 0.03),
     ('G3', 0.14, 0.04, 0.0), ('E3', 0.20, 0.06, 0.0), ('C3', 0.40, 0.0,  0.0)],
]

# ---------------------------------------------------------------------------
# Mood label for each pattern (one per entry, parallel to _LICK_PATTERNS)
# Existing patterns 0-9 assigned their most fitting mood.
_LICK_MOODS: list[str] = [
    'neutral',    # 0  — classic turnaround ascending run
    'weary',      # 1  — high wail and fall
    'sarcastic',  # 2  — call and response (question/answer structure)
    'lonely',     # 3  — low delta growl, dark and low
    'weary',      # 4  — bent-note cry, descending lament
    'cocky',      # 5  — syncopated groove, bouncy and assured
    'cocky',      # 6  — Chicago shuffle, up-tempo bounce
    'lonely',     # 7  — slow lonesome wail, long breathy bends
    'neutral',    # 8  — minor-3rd hammers, punchy but neutral
    'weary',      # 9  — high sundown run, descends to rest
    'cocky',      # 10 — punchy ascending strut
    'cocky',      # 11 — brash bent top-note swagger
    'cocky',      # 12 — quick ascending triplet stomp
    'weary',      # 13 — slow descending sigh
    'weary',      # 14 — trudging low register
    'weary',      # 15 — slow fall, exhausted bends
    'weary',      # 16 — dragging single-note lament
    'panic',      # 17 — fast chaotic scramble
    'panic',      # 18 — frantic high-register flutter
    'panic',      # 19 — wild ascending crash descent
    'delighted',  # 20 — bright quick ascending arpeggio
    'delighted',  # 21 — skipping high notes, buoyant
    'delighted',  # 22 — playful trill-like bounce
    'lonely',     # 23 — very slow, single long low note
    'lonely',     # 24 — two low tones, wide empty gap
    'lonely',     # 25 — three low notes, enormous space
    'lonely',     # 26 — one long sustained low note
    'sarcastic',  # 27 — starts high, drags down flat
    'sarcastic',  # 28 — bright opener, falls flat
    'sarcastic',  # 29 — confident ascent, deflates slowly
]

assert len(_LICK_PATTERNS) == 30, "Expected 30 lick patterns"
assert len(_LICK_MOODS) == 30, "Expected 30 mood labels"


def generate_lick(pattern_idx: int | None = None,
                  mood: str | None = None) -> pygame.mixer.Sound:
    """Synthesize one blues lick.

    Args:
        pattern_idx: If given, play this specific pattern (ignores mood).
        mood: If given (and pattern_idx is None), filter to patterns with
              matching mood label before picking randomly.  Falls back to the
              full pool if no pattern has that mood.
    """
    if pattern_idx is not None:
        pattern = _LICK_PATTERNS[pattern_idx]
    else:
        if mood is not None:
            indices = [i for i, m in enumerate(_LICK_MOODS) if m == mood]
            if not indices:
                indices = list(range(len(_LICK_PATTERNS)))  # fallback
        else:
            indices = list(range(len(_LICK_PATTERNS)))
        pattern = _LICK_PATTERNS[random.choice(indices)]

    segs = []
    for note, dur, gap, bend in pattern:
        segs.append(_harp_note(_NOTES[note], dur, bend=bend))
        if gap > 0:
            segs.append(np.zeros(int(SAMPLE_RATE * gap)))

    wave = np.concatenate(segs) if segs else np.zeros(SAMPLE_RATE)

    # Gentle master fade in / out
    n    = len(wave)
    fade = min(int(SAMPLE_RATE * 0.06), n // 6)
    wave[:fade]  *= np.linspace(0.0, 1.0, fade)
    wave[-fade:] *= np.linspace(1.0, 0.0, fade)

    return _to_sound(wave.clip(-1.0, 1.0))


def prebuild_all() -> list[pygame.mixer.Sound]:
    """Pre-generate one Sound per lick pattern (all 30)."""
    return [generate_lick(i) for i in range(len(_LICK_PATTERNS))]
