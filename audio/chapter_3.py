"""
Dead Drift — Chapter 3 audio inflection (The Paperwork).
Per SOUNDTRACK_PLAN.md Section 4.3

Cursed bureaucratic forms. The tritone home key (F#m against the ship's
home C) is the most cursed interval in Western music — the diabolus in
musica. Suspended-2nd voicing never resolves; sus2 pads hang forever
waiting for a release that never comes. The signature is a mechanical
typewriter rhythm — pitched at kick frequency so it doubles as part of
the drum pattern. Dead straight, no swing. The Union demands precision.
Cargo damage freezes the music on one sustained chord until the form is filed.
"""
from __future__ import annotations
import numpy as np
import pygame
from audio.synth import SAMPLE_RATE, _2PI, _to_sound, _adsr, _sine, _noise

# Chapter metadata
HOME_KEY_ROOT       = 185.0          # F#3 — tritone from C, the cursed interval
HOME_KEY_NAME       = "F# minor"
MODE                = "sus2"         # never resolves — bureaucratic limbo
SIGNATURE_NAME      = "Mechanical typewriter rhythm (pitched at kick freq)"
KIT_INFLECTION_DESC = "Manila-folder snare, stapler-click hat. No swing."
CARGO_HOOK_DESC     = "Music freezes on a sustained chord until form filed"


def signature_instrument(freq: float = None, duration: float = 1.0) -> pygame.mixer.Sound:
    """A single typewriter clack — short noise burst plus the brief carriage
    thunk at ~120 Hz. The whole thing is ~12 ms of noise riding a ~50 ms
    sine, which sits perfectly in the kick frequency pocket.

    `freq` is ignored — the typewriter is fixed at carriage-thunk pitch.
    `duration` controls the carriage sine tail.
    """
    # Click body — 12 ms of high-mid noise burst
    click_dur = 0.012
    n_click   = int(SAMPLE_RATE * click_dur)
    if n_click > 0:
        click_t   = np.linspace(0.0, click_dur, n_click, endpoint=False)
        click_env = np.exp(-click_t * 320.0)
        click     = np.random.uniform(-1.0, 1.0, n_click) * 0.88 * click_env
    else:
        click = np.zeros(1, dtype=np.float32)

    # Carriage thunk — short 120 Hz sine, decays inside `duration`
    thunk_dur = max(0.04, min(duration, 0.18))
    n_thunk   = int(SAMPLE_RATE * thunk_dur)
    thunk_t   = np.linspace(0.0, thunk_dur, n_thunk, endpoint=False)
    thunk_env = np.exp(-thunk_t * 35.0)
    thunk     = np.sin(_2PI * 120.0 * thunk_t) * 0.55 * thunk_env

    # Total length = max(duration, click+thunk). Overlay click at start of thunk.
    total_n = max(n_thunk, n_click, int(SAMPLE_RATE * duration))
    w = np.zeros(total_n, dtype=np.float32)
    w[:n_thunk] += thunk.astype(np.float32)
    w[:n_click] += click.astype(np.float32)

    peak = float(np.max(np.abs(w)))
    if peak > 0:
        w = w / peak * 0.85
    return _to_sound(w.clip(-1.0, 1.0))


def kit_inflection(drum_sound_array: np.ndarray) -> np.ndarray:
    """Identity — drums play as written. The chapter's kit "replacement"
    (manila-folder snare, stapler hat) is implemented by the audio_manager
    overlaying typewriter clicks on top of the standard kit through the
    signature_instrument channel. Keeping this identity also ensures the
    dead-straight, no-swing groove the Union demands.
    """
    return drum_sound_array.astype(np.float32, copy=True)


def cargo_alarm_callback(alarm_level: float, master_fx=None):
    """No-op here — when the form-filing minigame is active, audio_manager
    holds the current chord and freezes pad progression. This callback is
    a hook for future per-frame behaviour.
    """
    pass


# Stem priority — chapter 3 retains the full mix
STEM_GATES = {
    "drum": 1.0,
    "bass": 1.0,
    "arp":  1.0,
}
