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
    # Classic turnaround — ascending run up the blue note
    [('A2', 0.14, 0.02, 0.0), ('C3', 0.11, 0.02, 0.0),
     ('D3', 0.11, 0.0,  0.0), ('Eb3', 0.07, 0.0, 0.0),
     ('E3', 0.22, 0.08, 0.0), ('D3', 0.18, 0.0, 0.0)],

    # High wail and fall
    [('A3', 0.16, 0.02, 0.03), ('G3', 0.12, 0.0, 0.0),
     ('E3', 0.22, 0.10, 0.0),  ('D3', 0.14, 0.04, 0.0),
     ('C3', 0.32, 0.0,  0.0)],

    # Call and response
    [('E3', 0.10, 0.0,  0.0), ('D3', 0.10, 0.04, 0.0), ('C3', 0.18, 0.18, 0.0),
     ('A3', 0.09, 0.0,  0.0), ('G3', 0.09, 0.0,  0.0), ('E3', 0.26, 0.0,  0.0)],

    # Low delta growl
    [('A1', 0.20, 0.04, 0.0), ('C2', 0.14, 0.0, 0.0),
     ('D2', 0.14, 0.0,  0.0), ('E2', 0.28, 0.08, 0.0),
     ('G2', 0.12, 0.0,  0.0), ('A2', 0.30, 0.0,  0.0)],

    # Bent-note cry
    [('D3', 0.08, 0.0, 0.0),  ('E3', 0.18, 0.06, 0.04),
     ('Eb3', 0.12, 0.0, 0.0), ('D3', 0.14, 0.08, 0.0),
     ('C3', 0.12, 0.0, 0.0),  ('A2', 0.28, 0.0,  0.0)],

    # Syncopated groove
    [('A2', 0.08, 0.04, 0.0), ('A2', 0.08, 0.02, 0.0),
     ('C3', 0.12, 0.0,  0.0), ('D3', 0.08, 0.0,  0.0),
     ('Eb3', 0.06, 0.0, 0.0), ('D3', 0.16, 0.06, 0.0),
     ('A2', 0.24, 0.0,  0.0)],
]


def generate_lick(pattern_idx: int | None = None) -> pygame.mixer.Sound:
    """Synthesize one blues lick. Picks randomly if pattern_idx is None."""
    pattern = _LICK_PATTERNS[
        pattern_idx if pattern_idx is not None
        else random.randrange(len(_LICK_PATTERNS))
    ]
    segs = []
    for note, dur, gap, bend in pattern:
        segs.append(_harp_note(_NOTES[note], dur, bend=bend))
        if gap > 0:
            segs.append(np.zeros(int(SAMPLE_RATE * gap)))

    wave = np.concatenate(segs) if segs else np.zeros(SAMPLE_RATE)

    # Gentle master fade in / out
    n      = len(wave)
    fade   = min(int(SAMPLE_RATE * 0.06), n // 6)
    wave[:fade]  *= np.linspace(0.0, 1.0, fade)
    wave[-fade:] *= np.linspace(1.0, 0.0, fade)

    return _to_sound(wave.clip(-1.0, 1.0))


def prebuild_all() -> list[pygame.mixer.Sound]:
    """Pre-generate one Sound per lick pattern."""
    return [generate_lick(i) for i in range(len(_LICK_PATTERNS))]
