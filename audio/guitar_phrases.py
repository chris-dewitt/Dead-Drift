"""
Procedural acoustic guitar phrases — fingerpicked arpeggios + delta slide bends.
Minor pentatonic in A. Each phrase ~1.5-3.0s, with subtle reverb.
"""
from __future__ import annotations
import numpy as np
import pygame
from audio.synth import (
    SAMPLE_RATE, _to_sound,
    acoustic_guitar_note, slide_blues_note,
)

# A minor pentatonic — A C D E G across two octaves
_NOTES = {
    "A2": 110.0,  "C3": 130.8,  "D3": 146.8,  "E3": 164.8,  "G3": 196.0,
    "A3": 220.0,  "C4": 261.6,  "D4": 293.7,  "E4": 329.6,  "G4": 392.0,
    "A4": 440.0,
}


def _sound_to_np(snd: pygame.mixer.Sound) -> np.ndarray:
    arr = pygame.sndarray.array(snd)
    if arr.ndim == 2:
        arr = arr[:, 0]
    return arr.astype(np.float32) / 32767.0


def _mix_at(buf: np.ndarray, hit: np.ndarray, sample_pos: int, gain: float = 1.0):
    end = sample_pos + len(hit)
    if sample_pos >= len(buf):
        return
    if end > len(buf):
        hit = hit[: len(buf) - sample_pos]
        end = len(buf)
    buf[sample_pos:end] += hit * gain


def _add_subtle_reverb(buf: np.ndarray, delay_s: float = 0.085,
                       decay: float = 0.32) -> np.ndarray:
    """Amplitude-decayed copy mixed in — cheap reverb-ish texture."""
    delay_n = int(SAMPLE_RATE * delay_s)
    if delay_n >= len(buf):
        return buf
    wet = np.zeros_like(buf)
    wet[delay_n:] = buf[: len(buf) - delay_n] * decay
    # Second tap for body
    delay2 = int(delay_n * 1.7)
    if delay2 < len(buf):
        wet[delay2:] += buf[: len(buf) - delay2] * (decay * 0.55)
    out = buf + wet
    return out


def _fingerpicked_arpeggio(notes: list[str], spacing_s: float,
                           total_dur: float, note_dur: float = 1.0) -> np.ndarray:
    """Pluck a sequence of notes at fixed spacing; let them ring overlapping."""
    n   = int(SAMPLE_RATE * total_dur)
    buf = np.zeros(n, dtype=np.float32)
    for i, name in enumerate(notes):
        freq = _NOTES[name]
        # Vary note length slightly so high notes ring shorter
        nd   = note_dur * (1.0 if freq < 250 else 0.85)
        snd  = acoustic_guitar_note(freq, duration=nd)
        np_  = _sound_to_np(snd)
        pos  = int(SAMPLE_RATE * i * spacing_s)
        _mix_at(buf, np_, pos, gain=0.65)
    return buf


def _slide_phrase(slides: list[tuple[str, str, float]],
                  spacing_s: float, total_dur: float) -> np.ndarray:
    """Sequence of slide bends. Each tuple: (start_note, end_note, duration)."""
    n   = int(SAMPLE_RATE * total_dur)
    buf = np.zeros(n, dtype=np.float32)
    cursor = 0.0
    for start_name, end_name, dur in slides:
        f0 = _NOTES[start_name]
        f1 = _NOTES[end_name]
        snd = slide_blues_note(f0, f1, duration=dur)
        np_ = _sound_to_np(snd)
        pos = int(SAMPLE_RATE * cursor)
        _mix_at(buf, np_, pos, gain=0.72)
        cursor += spacing_s
    return buf


def _phrase_to_sound(buf: np.ndarray) -> pygame.mixer.Sound:
    # Add subtle reverb
    out = _add_subtle_reverb(buf, delay_s=0.085, decay=0.30)
    # Gentle master fade-in / out
    n    = len(out)
    fade = min(int(SAMPLE_RATE * 0.05), n // 8)
    if fade > 0:
        out[:fade]  *= np.linspace(0.0, 1.0, fade)
        out[-fade:] *= np.linspace(1.0, 0.0, fade)
    peak = float(np.max(np.abs(out))) if n else 0.0
    if peak > 0.95:
        out = out / peak * 0.90
    return _to_sound(out.clip(-1.0, 1.0))


# Phrase generators -----------------------------------------------------------

def _phrase_arp_ascending() -> pygame.mixer.Sound:
    notes = ["A2", "E3", "A3", "C4", "E4", "A4"]
    buf = _fingerpicked_arpeggio(notes, spacing_s=0.28, total_dur=2.4, note_dur=1.2)
    return _phrase_to_sound(buf)


def _phrase_arp_rolling() -> pygame.mixer.Sound:
    notes = ["A2", "C3", "E3", "C3", "A2", "G3", "E3", "C3"]
    buf = _fingerpicked_arpeggio(notes, spacing_s=0.21, total_dur=2.4, note_dur=1.0)
    return _phrase_to_sound(buf)


def _phrase_arp_descending() -> pygame.mixer.Sound:
    notes = ["E4", "D4", "C4", "A3", "G3", "E3", "A2"]
    buf = _fingerpicked_arpeggio(notes, spacing_s=0.24, total_dur=2.2, note_dur=1.0)
    return _phrase_to_sound(buf)


def _phrase_slide_cry() -> pygame.mixer.Sound:
    slides = [
        ("C3", "D3", 0.45),
        ("E3", "G3", 0.55),
        ("A3", "C4", 0.7),
    ]
    buf = _slide_phrase(slides, spacing_s=0.55, total_dur=2.4)
    return _phrase_to_sound(buf)


def _phrase_slide_lament() -> pygame.mixer.Sound:
    slides = [
        ("E3", "G3", 0.6),
        ("D3", "C3", 0.7),
        ("A2", "E3", 0.9),
    ]
    buf = _slide_phrase(slides, spacing_s=0.7, total_dur=2.8)
    return _phrase_to_sound(buf)


def _phrase_call() -> pygame.mixer.Sound:
    """Short 'call' phrase — to pair with answer."""
    notes = ["A3", "C4", "D4"]
    buf   = _fingerpicked_arpeggio(notes, spacing_s=0.22, total_dur=1.6, note_dur=0.9)
    return _phrase_to_sound(buf)


def _phrase_answer() -> pygame.mixer.Sound:
    """Short 'answer' phrase — slide resolution."""
    slides = [
        ("E3", "D3", 0.4),
        ("C3", "A2", 0.55),
    ]
    buf = _slide_phrase(slides, spacing_s=0.45, total_dur=1.6)
    return _phrase_to_sound(buf)


def _phrase_pentatonic_run() -> pygame.mixer.Sound:
    notes = ["A2", "C3", "D3", "E3", "G3", "A3", "G3", "E3"]
    buf   = _fingerpicked_arpeggio(notes, spacing_s=0.18, total_dur=2.0, note_dur=0.7)
    return _phrase_to_sound(buf)


_PHRASE_BUILDERS = [
    _phrase_arp_ascending,
    _phrase_arp_rolling,
    _phrase_arp_descending,
    _phrase_slide_cry,
    _phrase_slide_lament,
    _phrase_call,
    _phrase_answer,
    _phrase_pentatonic_run,
]


def prebuild_phrases() -> list[pygame.mixer.Sound]:
    """Pre-generate all guitar phrases. Cache at startup."""
    return [build() for build in _PHRASE_BUILDERS]
