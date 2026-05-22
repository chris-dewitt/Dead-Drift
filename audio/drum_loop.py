"""
80s drum-machine loop builder. Procedural — no asset files.

Pattern: kick on 1+3, snare on 2+4 (LinnDrum gated), closed hi-hats on every 8th,
clap doubling the snare at high intensity. Seamless loop.
"""
from __future__ import annotations
import numpy as np
import pygame
from audio.synth import (
    SAMPLE_RATE, _to_sound,
    drum_kick, drum_snare_gated, drum_hihat, drum_clap,
)


def _sound_to_np(snd: pygame.mixer.Sound) -> np.ndarray:
    """Pull a mono float array out of a stereo int16 Sound."""
    arr = pygame.sndarray.array(snd)
    if arr.ndim == 2:
        arr = arr[:, 0]
    return arr.astype(np.float32) / 32767.0


def _mix_at(buf: np.ndarray, hit: np.ndarray, sample_pos: int, gain: float = 1.0):
    """In-place additive mix at the given sample offset, clipping the tail."""
    end = sample_pos + len(hit)
    if sample_pos >= len(buf):
        return
    if end > len(buf):
        hit = hit[: len(buf) - sample_pos]
        end = len(buf)
    buf[sample_pos:end] += hit * gain


def build_drum_loop(bpm: float = 96.0, length_bars: int = 2,
                    intensity: float = 1.0) -> pygame.mixer.Sound:
    """
    Build a 2-bar 4/4 drum loop. 8th-note hi-hat grid, kick on 1+3, snare on 2+4.

    Returns a seamlessly-loopable Sound.
    """
    intensity = max(0.0, min(1.5, intensity))
    sec_per_beat   = 60.0 / bpm
    beats_per_bar  = 4
    total_beats    = beats_per_bar * length_bars
    loop_duration  = sec_per_beat * total_beats
    n              = int(SAMPLE_RATE * loop_duration)
    buf            = np.zeros(n, dtype=np.float32)

    # Pre-generate hits (fresh randomness each call keeps loops feeling natural)
    kick_np  = _sound_to_np(drum_kick())
    snare_np = _sound_to_np(drum_snare_gated())
    hat_np   = _sound_to_np(drum_hihat())
    clap_np  = _sound_to_np(drum_clap())

    # Hi-hats on every 8th — 8 per bar
    eighth = sec_per_beat / 2.0
    for i in range(total_beats * 2):
        pos = int(SAMPLE_RATE * i * eighth)
        # Accent on downbeats
        is_down = (i % 2 == 0)
        gain    = (0.45 if is_down else 0.32) * (0.7 + 0.3 * intensity)
        _mix_at(buf, hat_np, pos, gain=gain)

    # Kick: beats 1, 3 of every bar
    for bar in range(length_bars):
        for beat_in_bar in (0, 2):
            beat = bar * beats_per_bar + beat_in_bar
            pos  = int(SAMPLE_RATE * beat * sec_per_beat)
            _mix_at(buf, kick_np, pos, gain=0.95)

    # Snare: beats 2, 4 of every bar (with gated reverb already baked in)
    for bar in range(length_bars):
        for beat_in_bar in (1, 3):
            beat = bar * beats_per_bar + beat_in_bar
            pos  = int(SAMPLE_RATE * beat * sec_per_beat)
            _mix_at(buf, snare_np, pos, gain=0.78)
            # Clap doubles the snare when intensity is high
            if intensity > 0.65:
                clap_gain = 0.45 * min(1.0, (intensity - 0.65) / 0.5)
                _mix_at(buf, clap_np, pos, gain=clap_gain)

    # Optional ghost-snare on the 'and' of beat 4 every other bar — a bit of swing
    if intensity > 0.85 and length_bars >= 2:
        ghost_beat = (length_bars - 1) * beats_per_bar + 3 + 0.5
        pos        = int(SAMPLE_RATE * ghost_beat * sec_per_beat)
        _mix_at(buf, snare_np, pos, gain=0.22)

    # Headroom — make sure mix doesn't clip
    peak = float(np.max(np.abs(buf))) if len(buf) else 0.0
    if peak > 0.95:
        buf = buf / peak * 0.92

    # Tiny crossfade at the very loop boundary to avoid clicks
    xfade = min(int(SAMPLE_RATE * 0.005), n // 32)
    if xfade > 4:
        # Wrap the tail's last samples into the head with a gentle blend
        head_env = np.linspace(0.0, 1.0, xfade)
        buf[:xfade] = buf[:xfade] * head_env + buf[-xfade:] * (1.0 - head_env) * 0.0
        # (Leave tail intact — drum hits already decay)

    return _to_sound(buf.clip(-1.0, 1.0))


def build_bass_loop(progression: list[float], bpm: float = 96.0,
                    notes_per_chord: int = 4) -> pygame.mixer.Sound:
    """
    Walking sub-bass pattern that maps to the chord progression.

    Each chord gets `notes_per_chord` 8th-ish notes; the root + 5th alternate
    with a passing tone. Designed to lock to build_drum_loop at the same BPM.
    """
    from audio.synth import synth_bass_note
    sec_per_beat = 60.0 / bpm
    # one note per beat → 4 beats per chord = 1 bar per chord
    note_dur     = sec_per_beat
    total_notes  = len(progression) * notes_per_chord
    total_dur    = total_notes * note_dur
    n            = int(SAMPLE_RATE * total_dur)
    buf          = np.zeros(n, dtype=np.float32)

    for ci, root in enumerate(progression):
        # Walking pattern: root, root, 5th, root (classic riff)
        fifth = root * 1.4983
        seventh = root * 1.7818
        pattern = [root, root, fifth, root]
        # Drop everything an octave to sub-bass register if root is high
        if root >= 110.0:
            pattern = [f * 0.5 for f in pattern]
        for ni, freq in enumerate(pattern[:notes_per_chord]):
            idx     = ci * notes_per_chord + ni
            pos     = int(SAMPLE_RATE * idx * note_dur)
            note_np = _sound_to_np(synth_bass_note(freq, duration=note_dur * 0.95))
            _mix_at(buf, note_np, pos, gain=0.85)

    peak = float(np.max(np.abs(buf))) if len(buf) else 0.0
    if peak > 0.95:
        buf = buf / peak * 0.90

    return _to_sound(buf.clip(-1.0, 1.0))
