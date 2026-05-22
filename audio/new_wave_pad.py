"""
Long-form new-wave pad with chord progression and arpeggiated top voice.
Procedural — Tangerine Dream / Vangelis with bluesier minor-7 voicings.
"""
from __future__ import annotations
import numpy as np
import pygame
from audio.synth import (
    SAMPLE_RATE, _2PI, _to_sound, _CHORD_RATIOS,
)


def _saw_voice(freq: float, n: int) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    return 2.0 * ((t * freq) % 1.0) - 1.0


def _tri_voice(freq: float, n: int) -> np.ndarray:
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    return 2.0 * np.abs(2.0 * ((t * freq) % 1.0) - 1.0) - 1.0


def _chord_block(root: float, duration: float,
                 mode: str = "minor") -> np.ndarray:
    """Build a sustained chord block with attack/release ramp. No tail cut."""
    ratios = _CHORD_RATIOS.get(mode, _CHORD_RATIOS["minor"])
    n      = int(SAMPLE_RATE * duration)
    w      = np.zeros(n, dtype=np.float32)
    for i, r in enumerate(ratios):
        f    = root * r
        det  = 1.0 + 0.004 * ((i * 7) % 5 - 2)
        saw1 = _saw_voice(f, n) * 0.16
        saw2 = _saw_voice(f * det, n) * 0.13
        tri  = _tri_voice(f, n) * 0.18
        amp  = 0.32 if i in (0, 2) else 0.22
        w   += (saw1 + saw2 + tri) * amp
    # Lowpass: cumulative averaging twice
    for _ in range(2):
        w = (w + np.roll(w, 1) + np.roll(w, 2)) / 3.0
    # Slow LFO breath
    t   = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    lfo = 0.78 + 0.22 * np.sin(_2PI * 0.18 * t)
    w   = w * lfo
    return w


def _arpeggio_layer(roots: list[float], duration_per_chord: float,
                    mode: str = "minor", octave_mul: float = 4.0) -> np.ndarray:
    """High-octave triangle arpeggio over the chord progression. 8th notes."""
    from audio.synth import acoustic_guitar_note
    ratios = _CHORD_RATIOS.get(mode, _CHORD_RATIOS["minor"])
    notes_per_chord = 8   # 8 eighth notes per chord
    note_dur = duration_per_chord / notes_per_chord
    total_dur = duration_per_chord * len(roots)
    n         = int(SAMPLE_RATE * total_dur)
    buf       = np.zeros(n, dtype=np.float32)

    for ci, root in enumerate(roots):
        # Cycle through chord tones an octave up
        pattern = [ratios[i % len(ratios)] for i in range(notes_per_chord)]
        # Add a passing-tone variation per chord
        if ci % 2 == 1:
            pattern = pattern[::-1]
        for ni, r in enumerate(pattern):
            f = root * r * octave_mul
            # Use simple triangle synth, not full Karplus (faster, cleaner pad voice)
            note_n = int(SAMPLE_RATE * note_dur * 0.95)
            t      = np.arange(note_n, dtype=np.float32) / SAMPLE_RATE
            tri    = 2.0 * np.abs(2.0 * ((t * f) % 1.0) - 1.0) - 1.0
            # Plucky attack envelope
            env    = np.exp(-t * 6.5)
            tone   = tri * env * 0.22
            pos    = int(SAMPLE_RATE * (ci * duration_per_chord + ni * note_dur))
            end    = min(pos + note_n, n)
            buf[pos:end] += tone[: end - pos]

    return buf


def build_new_wave_pad(progression: list[float],
                       duration_per_chord: float = 4.0,
                       mode: str = "minor",
                       with_arpeggio: bool = True) -> pygame.mixer.Sound:
    """
    Build a looping chord progression as a single pad. Chords crossfade.
    progression: list of root frequencies (Hz). e.g. [220, 174.61, 196, 164.81]
                 → Am, F, G, Em
    Adds an arpeggiated triangle top voice when with_arpeggio=True.
    """
    if not progression:
        progression = [220.0]
    total_dur = duration_per_chord * len(progression)
    n         = int(SAMPLE_RATE * total_dur)
    out       = np.zeros(n, dtype=np.float32)

    # Crossfade time between chords — ~0.6s
    xfade_s = min(0.7, duration_per_chord * 0.18)
    xfade_n = int(SAMPLE_RATE * xfade_s)
    chord_n = int(SAMPLE_RATE * duration_per_chord)

    for ci, root in enumerate(progression):
        # Build chord with crossfade tails on both ends
        block_dur = duration_per_chord + xfade_s
        block     = _chord_block(root, block_dur, mode=mode)
        # Crossfade envelope: ramp-in at start, hold, ramp-out at end
        env       = np.ones(len(block), dtype=np.float32)
        if xfade_n > 0 and xfade_n < len(block):
            env[:xfade_n]  = np.linspace(0.0, 1.0, xfade_n)
            env[-xfade_n:] = np.linspace(1.0, 0.0, xfade_n)
        block = block * env
        # Position: start so that the ramp-in overlaps the previous chord's ramp-out
        start = ci * chord_n - xfade_n // 2
        end   = start + len(block)
        # Wrap-around for seamless loop on the last chord's tail
        if start < 0:
            # First chord — clip the pre-roll
            block = block[-start:]
            start = 0
        if end > n:
            # Tail wraps to the beginning for seamless loop
            tail_n = end - n
            out[start:n]    += block[: n - start]
            out[: tail_n]   += block[n - start :]
        else:
            out[start:end] += block

    # Add arpeggio layer
    if with_arpeggio:
        arp = _arpeggio_layer(progression, duration_per_chord, mode=mode)
        # Match length
        if len(arp) < n:
            arp = np.pad(arp, (0, n - len(arp)))
        elif len(arp) > n:
            arp = arp[:n]
        out = out + arp * 0.55

    # Sub-bass under the progression — root only, slow
    sub = np.zeros(n, dtype=np.float32)
    for ci, root in enumerate(progression):
        start = ci * chord_n
        end   = start + chord_n
        if start >= n:
            break
        seg_n = min(chord_n, n - start)
        t     = np.arange(seg_n, dtype=np.float32) / SAMPLE_RATE
        sub_f = root * 0.5
        sub[start:start + seg_n] = np.sin(_2PI * sub_f * t) * 0.18
    # Apply a slow attack to the sub for smoothness
    fa = int(SAMPLE_RATE * 0.3)
    if fa < n:
        sub[:fa] *= np.linspace(0.0, 1.0, fa)
    out = out + sub

    # Loop-boundary crossfade — fade the very last 0.3s into the head
    boundary = int(SAMPLE_RATE * 0.3)
    if boundary > 4 and boundary * 2 < n:
        env_h = np.linspace(0.0, 1.0, boundary)
        env_t = np.linspace(1.0, 0.0, boundary)
        head_blend = out[:boundary] * env_h + out[-boundary:] * env_t
        out[:boundary]   = head_blend
        out[-boundary:] *= env_t

    peak = float(np.max(np.abs(out))) if n else 0.0
    if peak > 0.95:
        out = out / peak * 0.85
    return _to_sound(out.clip(-1.0, 1.0))
