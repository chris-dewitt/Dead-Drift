"""
Diegetic cockpit radio stations — see SOUNDTRACK_PLAN.md Section 7.1.

Four procedurally-generated 30-second numpy-mixed pygame.mixer.Sound
buffers, intended to be cycled through by the SCENE_RADIO toggle (R key).
Each station is a self-contained 30s loop that sits inside the ship and
plays "alongside" the rest of the audio stack — they are the only place
in the game where the player can choose what they hear.

Stations:
    1. pirate_blues       — harmonica + acoustic guitar duet, no drums
    2. propaganda         — voice blips over a forbidden major-key pad
    3. union_solidarity   — kick/snare/bass workers' march, no melody
    4. dead_air           — wide-band static with a subliminal heartbeat
"""
from __future__ import annotations

import numpy as np
import pygame

from audio.synth import (
    SAMPLE_RATE,
    _2PI,
    _to_sound,
    _adsr,
    _sine,
    _saw,
    _noise,
    _t,
    acoustic_guitar_note,
    slide_blues_note,
    drum_kick,
    drum_snare_gated,
    drum_hihat,
    drum_clap,
    synth_bass_note,
    new_wave_chord,
)
from audio.blues_licks import _harp_note, _NOTES
from audio.voices import make_voice_blips


# ---------------------------------------------------------------------------
# Public registry

RADIO_STATIONS = [
    "pirate_blues",
    "propaganda",
    "union_solidarity",
    "dead_air",
]


# ---------------------------------------------------------------------------
# Internal helpers

_STATION_SECONDS = 30.0
_STATION_SAMPLES = int(_STATION_SECONDS * SAMPLE_RATE)


def _sound_to_np(snd: pygame.mixer.Sound) -> np.ndarray:
    """Pull a Sound back out as a float32 mono numpy array in [-1, 1]."""
    arr = pygame.sndarray.array(snd)
    if arr.ndim == 2:
        arr = arr[:, 0]
    return arr.astype(np.float32) / 32767.0


def _mix_at(buf: np.ndarray, hit: np.ndarray, sample_pos: int,
            gain: float = 1.0) -> None:
    """Additively mix `hit` into `buf` at `sample_pos`, clipped to buffer."""
    if sample_pos >= len(buf) or sample_pos < 0:
        return
    end = sample_pos + len(hit)
    if end > len(buf):
        hit = hit[: len(buf) - sample_pos]
        end = len(buf)
    buf[sample_pos:end] += hit.astype(np.float32) * float(gain)


def _seamless_edges(buf: np.ndarray, fade_s: float = 0.5) -> np.ndarray:
    """Fade in/out at the edges so the 30s clip loops without a click."""
    fade = int(SAMPLE_RATE * fade_s)
    n    = len(buf)
    if fade > 0 and fade * 2 < n:
        buf[:fade]  *= np.linspace(0.0, 1.0, fade).astype(np.float32)
        buf[-fade:] *= np.linspace(1.0, 0.0, fade).astype(np.float32)
    return buf


def _peak_normalise(buf: np.ndarray, target: float = 0.70) -> np.ndarray:
    peak = float(np.max(np.abs(buf)))
    if peak > 1e-6:
        buf = buf / peak * target
    return buf.clip(-1.0, 1.0)


# ---------------------------------------------------------------------------
# 1. Pirate Blues — harmonica + acoustic guitar duet, no drums
# ---------------------------------------------------------------------------

def station_pirate_blues() -> pygame.mixer.Sound:
    """
    Slow blues duet in A minor: fingerpicked acoustic guitar arpeggios with
    sparse harmonica licks drifting over the top. No drums. The kind of
    thing that makes the silence after it feel worse than no music at all.
    """
    rng = np.random.default_rng(0xB1EE51)
    buf = np.zeros(_STATION_SAMPLES, dtype=np.float32)

    # ---- Guitar: looping fingerpicked arpeggio A-min pattern ---------------
    # A2, E3, A3, C4 — root, 5th, octave, b3. Eight-beat pattern at 60 BPM.
    arpeggio = [
        (110.0, 0.00, 1.10, 0.65),   # A2 — root
        (164.8, 0.50, 1.00, 0.55),   # E3 — fifth
        (220.0, 1.00, 0.95, 0.55),   # A3 — octave
        (261.6, 1.50, 0.95, 0.50),   # C4 — minor third up high
        (164.8, 2.00, 0.95, 0.50),   # E3
        (220.0, 2.50, 0.90, 0.50),   # A3
        (130.8, 3.00, 1.05, 0.55),   # C3 — pivot to bring it home
        (110.0, 3.50, 1.20, 0.65),   # A2 — resolve
    ]
    pattern_len_s = 4.0
    n_patterns    = int(np.ceil(_STATION_SECONDS / pattern_len_s)) + 1

    for p in range(n_patterns):
        base_t = p * pattern_len_s
        # Gentle dynamic shape across the 30s — louder middle, quieter ends.
        progress = base_t / _STATION_SECONDS
        macro_amp = 0.55 + 0.45 * np.sin(np.pi * np.clip(progress, 0.0, 1.0))
        for freq, t_offset, dur, amp in arpeggio:
            # Tiny humanisation of timing + amplitude per pluck.
            jitter_t = float(rng.uniform(-0.020, 0.020))
            jitter_a = float(rng.uniform(0.88, 1.10))
            start    = base_t + t_offset + jitter_t
            sample_i = int(start * SAMPLE_RATE)
            note_snd = acoustic_guitar_note(freq, duration=dur)
            note_np  = _sound_to_np(note_snd)
            _mix_at(buf, note_np, sample_i,
                    gain=amp * macro_amp * jitter_a * 0.62)

    # ---- Harmonica: 6-8 sparse phrases drifting over the guitar ------------
    # Each phrase is 2-4 notes of A-minor pentatonic with a little bend.
    harp_phrases = [
        # (start_s, [(note, dur, gap, bend, amp), ...])
        ( 2.4,  [('E3', 0.55, 0.10, 0.02, 0.55),
                 ('D3', 0.45, 0.00, 0.00, 0.48),
                 ('C3', 0.65, 0.00, 0.00, 0.50)]),
        ( 6.8,  [('A3', 0.40, 0.10, 0.03, 0.55),
                 ('G3', 0.35, 0.05, 0.00, 0.50),
                 ('E3', 0.85, 0.00, 0.00, 0.55)]),
        (10.2,  [('C3', 0.50, 0.15, 0.00, 0.45),
                 ('A2', 1.20, 0.00, 0.02, 0.55)]),
        (13.7,  [('E3', 0.30, 0.05, 0.00, 0.45),
                 ('G3', 0.30, 0.05, 0.00, 0.50),
                 ('A3', 0.70, 0.00, 0.04, 0.60),
                 ('G3', 0.45, 0.00, 0.00, 0.45)]),
        (18.1,  [('D3', 0.60, 0.20, 0.02, 0.50),
                 ('C3', 0.50, 0.00, 0.00, 0.45),
                 ('A2', 1.10, 0.00, 0.00, 0.55)]),
        (22.0,  [('A3', 0.32, 0.04, 0.03, 0.50),
                 ('E3', 0.55, 0.00, 0.00, 0.50)]),
        (25.3,  [('C3', 0.40, 0.10, 0.00, 0.45),
                 ('D3', 0.40, 0.10, 0.02, 0.45),
                 ('E3', 0.70, 0.00, 0.00, 0.50),
                 ('A2', 1.00, 0.00, 0.00, 0.55)]),
    ]

    for start_s, phrase in harp_phrases:
        cursor_s = start_s
        for note, dur, gap, bend, amp in phrase:
            freq = _NOTES[note]
            note_np = _harp_note(freq, dur, amp=amp, bend=bend)
            sample_i = int(cursor_s * SAMPLE_RATE)
            _mix_at(buf, note_np, sample_i, gain=0.60)
            cursor_s += dur + gap

    # ---- Tape-hum bed underneath -------------------------------------------
    # Low-amplitude continuous noise to suggest a worn cassette.
    hum = _noise(_STATION_SECONDS, amp=0.05).astype(np.float32)
    # Crude lowpass smear to roll off the brightest hiss.
    hum = (hum + np.roll(hum, 1) + np.roll(hum, 2)) / 3.0
    # 60 Hz mains-style hum on top of the hiss.
    hum += _sine(60.0, _STATION_SECONDS, amp=0.012).astype(np.float32)
    buf += hum.astype(np.float32)

    buf = _seamless_edges(buf, fade_s=0.5)
    buf = _peak_normalise(buf, target=0.70)
    return _to_sound(buf)


# ---------------------------------------------------------------------------
# 2. Propaganda — voice blips over a forbidden major-key pad
# ---------------------------------------------------------------------------

def station_propaganda() -> pygame.mixer.Sound:
    """
    Spoken-word dispatcher blips over a sustained C-major triad. The major
    key is unique to this station — everything else in the game is minor —
    so the brightness lands as wrong rather than uplifting.
    """
    rng = np.random.default_rng(0xC0DE15)
    buf = np.zeros(_STATION_SAMPLES, dtype=np.float32)

    # ---- C-major pad (C E G), drawn directly with _sine, not new_wave -----
    # C4 = 261.63, E4 = 329.63, G4 = 392.00. Add an octave-below C for body.
    pad_freqs_amp = [
        (130.81, 0.16),   # C3 (octave below)
        (261.63, 0.18),   # C4
        (329.63, 0.14),   # E4
        (392.00, 0.13),   # G4
        (523.25, 0.06),   # C5 air on top
    ]
    t = _t(_STATION_SECONDS).astype(np.float32)
    pad = np.zeros(_STATION_SAMPLES, dtype=np.float32)
    # Slow breathing LFO so the chord isn't perfectly static.
    lfo = (0.78 + 0.22 * np.sin(_2PI * 0.08 * t)).astype(np.float32)
    for freq, amp in pad_freqs_amp:
        # Tiny detune per voice for organic shimmer.
        det = 1.0 + 0.0022 * float(rng.uniform(-1.0, 1.0))
        pad += np.sin(_2PI * freq * det * t).astype(np.float32) * amp
    pad *= lfo
    # Slight smoothing to soften the top end.
    pad = ((pad + np.roll(pad, 1) + np.roll(pad, 2)) / 3.0).astype(np.float32)
    buf += pad * 0.55

    # ---- Voice blip stream -------------------------------------------------
    voice_blips = make_voice_blips("dispatcher", n_vars=12)
    blip_nps    = [_sound_to_np(s) for s in voice_blips]

    # Roughly 30 blips across 30s, clustered into "phrases" of 3-6 blips
    # separated by longer pauses — mimics bureaucratic speech cadence.
    placements: list[tuple[float, int]] = []
    cursor_s = 0.6
    while cursor_s < _STATION_SECONDS - 0.4:
        phrase_len = int(rng.integers(3, 7))
        for _ in range(phrase_len):
            if cursor_s >= _STATION_SECONDS - 0.2:
                break
            placements.append((cursor_s, int(rng.integers(0, len(blip_nps)))))
            # Tight inter-blip gap inside a phrase.
            cursor_s += float(rng.uniform(0.09, 0.18))
        # Longer breath between phrases.
        cursor_s += float(rng.uniform(0.55, 1.25))

    for start_s, blip_idx in placements:
        sample_i = int(start_s * SAMPLE_RATE)
        _mix_at(buf, blip_nps[blip_idx], sample_i, gain=0.55)

    # ---- AM-radio static crackle ------------------------------------------
    static = _noise(_STATION_SECONDS, amp=0.04).astype(np.float32)
    # Modulate the static with a slow swell so it feels like a tuned-in signal.
    swell  = (0.55 + 0.45 * np.sin(_2PI * 0.12 * t + 0.7)).astype(np.float32)
    buf   += static * swell

    buf = _seamless_edges(buf, fade_s=0.5)
    buf = _peak_normalise(buf, target=0.70)
    return _to_sound(buf)


# ---------------------------------------------------------------------------
# 3. Union Solidarity — drum + bass workers' march, no melody
# ---------------------------------------------------------------------------

def station_union_solidarity() -> pygame.mixer.Sound:
    """
    A 4/4 workers' march at 92 BPM. Kick on beats 1 and 3, snare on 2 and 4,
    walking bass on root/4th/5th (A1, D2, E2). No melody — just rhythm and
    the implication of a crowd outside.
    """
    rng = np.random.default_rng(0xA110CA7E)
    buf = np.zeros(_STATION_SAMPLES, dtype=np.float32)

    bpm           = 92.0
    beat_s        = 60.0 / bpm                  # one quarter note
    beats_per_bar = 4
    bar_s         = beat_s * beats_per_bar
    n_bars        = int(np.ceil(_STATION_SECONDS / bar_s)) + 1

    # Pre-render the drum hits once each.
    kick_np  = _sound_to_np(drum_kick(duration=0.40))
    snare_np = _sound_to_np(drum_snare_gated(duration=0.45))

    # Walking bass: two-bar phrase — A1, A1, D2, A1 | A1, E2, D2, A1
    bass_pattern_two_bars = [
        # (beat_index, freq, dur_beats)
        (0, 55.0, 1.0),   # A1
        (1, 55.0, 1.0),   # A1
        (2, 73.4, 1.0),   # D2
        (3, 55.0, 1.0),   # A1
        (4, 55.0, 1.0),   # A1
        (5, 82.4, 1.0),   # E2
        (6, 73.4, 1.0),   # D2
        (7, 55.0, 1.0),   # A1
    ]

    bar = 0
    while bar < n_bars:
        bar_t = bar * bar_s
        if bar_t >= _STATION_SECONDS:
            break

        # Kick on beats 1 and 3 (zero-indexed: 0 and 2).
        for k_beat in (0, 2):
            t_s = bar_t + k_beat * beat_s
            _mix_at(buf, kick_np, int(t_s * SAMPLE_RATE), gain=0.85)

        # Snare on beats 2 and 4 (zero-indexed: 1 and 3).
        for s_beat in (1, 3):
            t_s = bar_t + s_beat * beat_s
            _mix_at(buf, snare_np, int(t_s * SAMPLE_RATE), gain=0.55)

        bar += 1

    # Walking bass — render across two-bar cycles, baked across the full 30s.
    two_bar_s = bar_s * 2
    n_cycles  = int(np.ceil(_STATION_SECONDS / two_bar_s)) + 1
    for cyc in range(n_cycles):
        cyc_t = cyc * two_bar_s
        if cyc_t >= _STATION_SECONDS:
            break
        for beat_idx, freq, dur_beats in bass_pattern_two_bars:
            t_s = cyc_t + beat_idx * beat_s
            if t_s >= _STATION_SECONDS:
                break
            dur_s   = dur_beats * beat_s * 0.92   # tiny gap before next note
            note_snd = synth_bass_note(freq, duration=dur_s)
            note_np  = _sound_to_np(note_snd)
            _mix_at(buf, note_np, int(t_s * SAMPLE_RATE), gain=0.55)

    # ---- Crowd murmur — filtered noise at a low amp ------------------------
    murmur = _noise(_STATION_SECONDS, amp=0.025).astype(np.float32)
    # Several lowpass passes => muffled crowd character.
    for _ in range(5):
        murmur = (murmur + np.roll(murmur, 1) + np.roll(murmur, 2)) / 3.0
    # Slow amplitude swell as if the crowd surges and ebbs.
    t = _t(_STATION_SECONDS).astype(np.float32)
    swell = (0.6 + 0.4 * np.sin(_2PI * 0.09 * t)).astype(np.float32)
    buf  += murmur.astype(np.float32) * swell

    buf = _seamless_edges(buf, fade_s=0.5)
    buf = _peak_normalise(buf, target=0.70)
    return _to_sound(buf)


# ---------------------------------------------------------------------------
# 4. Dead Air — wide-band static + subliminal heartbeat
# ---------------------------------------------------------------------------

def station_dead_air() -> pygame.mixer.Sound:
    """
    Empty band: wide-band static at low amplitude with a slow heartbeat
    pulsing underneath at 56 BPM. Nothing musical, nothing to grab onto —
    just a tuned-in nothing that the player notices only when they stop
    moving long enough to listen.
    """
    buf = np.zeros(_STATION_SAMPLES, dtype=np.float32)
    t   = _t(_STATION_SECONDS).astype(np.float32)

    # ---- Wide-band static with a very slow swell --------------------------
    static = _noise(_STATION_SECONDS, amp=0.18).astype(np.float32)
    swell  = (0.65 + 0.35 * np.sin(_2PI * 0.05 * t)).astype(np.float32)
    buf   += static * swell

    # A faint sub-rumble underneath, ~30 Hz, so the static has a floor.
    buf += _sine(30.0, _STATION_SECONDS, amp=0.04).astype(np.float32)

    # ---- Subliminal heartbeat at 56 BPM (0.9333 Hz, ~1.071s period) -------
    heartbeat_bpm    = 56.0
    period_s         = 60.0 / heartbeat_bpm     # ~1.0714 s
    # Build one heartbeat pulse: short soft sine around 65 Hz.
    pulse_dur        = 0.16
    pulse_n          = int(pulse_dur * SAMPLE_RATE)
    pt               = np.linspace(0.0, pulse_dur, pulse_n,
                                   endpoint=False).astype(np.float32)
    pulse_env        = (np.exp(-pt * 22.0)).astype(np.float32)
    pulse            = (np.sin(_2PI * 65.0 * pt).astype(np.float32)
                        * pulse_env * 0.55)
    # Slightly higher-frequency "second tap" of the heart — softer, just after.
    tap_offset_s     = 0.18
    tap_env          = (np.exp(-pt * 28.0)).astype(np.float32)
    second_tap       = (np.sin(_2PI * 78.0 * pt).astype(np.float32)
                        * tap_env * 0.32)

    n_beats = int(np.floor(_STATION_SECONDS / period_s)) + 1
    for i in range(n_beats):
        beat_t = i * period_s
        sample_i = int(beat_t * SAMPLE_RATE)
        if sample_i >= len(buf):
            break
        _mix_at(buf, pulse, sample_i, gain=0.55)
        tap_i = int((beat_t + tap_offset_s) * SAMPLE_RATE)
        _mix_at(buf, second_tap, tap_i, gain=0.45)

    buf = _seamless_edges(buf, fade_s=0.5)
    buf = _peak_normalise(buf, target=0.70)
    return _to_sound(buf)


# ---------------------------------------------------------------------------
# Public batch builder

def build_all_stations() -> dict[str, pygame.mixer.Sound]:
    return {
        "pirate_blues":      station_pirate_blues(),
        "propaganda":        station_propaganda(),
        "union_solidarity":  station_union_solidarity(),
        "dead_air":          station_dead_air(),
    }
