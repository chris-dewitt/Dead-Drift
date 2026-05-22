"""
Procedural sound generation — numpy only, no audio files required.
All sounds returned as pygame.mixer.Sound objects ready to play.
"""
from __future__ import annotations
import numpy as np
import pygame

SAMPLE_RATE = 44100
_2PI = 2.0 * np.pi


def _to_sound(wave: np.ndarray) -> pygame.mixer.Sound:
    clipped = wave.clip(-1.0, 1.0)
    scaled  = (clipped * 32767).astype(np.int16)
    stereo  = np.column_stack([scaled, scaled])
    return pygame.sndarray.make_sound(stereo)


def _t(duration: float) -> np.ndarray:
    return np.linspace(0.0, duration, int(SAMPLE_RATE * duration), endpoint=False)


def _sine(freq: float, duration: float, amp: float = 1.0) -> np.ndarray:
    return np.sin(_2PI * freq * _t(duration)) * amp


def _saw(freq: float, duration: float, amp: float = 1.0) -> np.ndarray:
    t = _t(duration)
    return (2.0 * ((t * freq) % 1.0) - 1.0) * amp


def _noise(duration: float, amp: float = 1.0) -> np.ndarray:
    return np.random.uniform(-1.0, 1.0, int(SAMPLE_RATE * duration)) * amp


def _adsr(wave: np.ndarray, attack: float, decay: float,
          sustain: float, release: float) -> np.ndarray:
    n  = len(wave)
    a  = min(int(attack  * SAMPLE_RATE), n)
    d  = min(int(decay   * SAMPLE_RATE), n - a)
    r  = min(int(release * SAMPLE_RATE), n)
    r0 = max(0, n - r)
    env = np.empty(n)
    env[:a]     = np.linspace(0.0, 1.0, a)
    env[a:a+d]  = np.linspace(1.0, sustain, d)
    env[a+d:r0] = sustain
    env[r0:]    = np.linspace(sustain, 0.0, n - r0)
    return wave * env


# ---------------------------------------------------------------------------
# Engine drones — 5 speed tiers, space-blues character

def engine_drone(tier: int, duration: float = 3.0) -> pygame.mixer.Sound:
    """
    Sawtooth fundamental + harmonic stack + slow LFO wail.
    tier 0 = idle drift, tier 4 = redline.
    """
    base = [52.0, 64.0, 78.0, 96.0, 118.0][tier]
    t    = _t(duration)
    lfo  = 0.65 + 0.35 * np.sin(_2PI * 0.38 * t)   # 0.38 Hz blues moan

    w  = _saw(base, duration, amp=0.28)
    w += _sine(base * 2,    duration, amp=[0.06, 0.09, 0.13, 0.17, 0.20][tier])
    w += _sine(base * 1.78, duration, amp=[0.00, 0.03, 0.06, 0.10, 0.14][tier]) * lfo
    w += _sine(base * 3,    duration, amp=[0.02, 0.04, 0.07, 0.10, 0.13][tier]) * (0.8 + 0.2 * lfo)
    w += _sine(base * 0.5,  duration, amp=0.12)   # sub-bass thump

    peak = np.max(np.abs(w))
    if peak > 0:
        w = w / peak * 0.70
    return _to_sound(w)


def ambient_static(duration: float = 4.0) -> pygame.mixer.Sound:
    """Deep space hiss — slow-swelling broadband noise + infra-bass rumble."""
    w  = _noise(duration, amp=0.06)
    w += _sine(28.0, duration, amp=0.05)
    w += _sine(41.0, duration, amp=0.03)
    n     = len(w)
    swell = 0.70 + 0.30 * np.sin(_2PI * 0.06 * np.linspace(0.0, duration, n))
    return _to_sound(w * swell)


def sector_pad(sector_idx: int, duration: float = 8.0) -> pygame.mixer.Sound:
    """
    Slow ambient music pad — one per sector. Each sector picks a different
    minor-key root + chord voicing for a fresh mood without changing genre.

    Loops cleanly. Designed to sit BEHIND the engine drone + blues licks.
    """
    # Minor-pentatonic-friendly roots, dropping by tritone every other sector
    roots = [65.4, 73.4, 87.3, 77.8, 82.4, 92.5, 98.0, 110.0, 87.3, 73.4]
    root  = roots[sector_idx % len(roots)]

    # Chord voicing — minor 7th adds blues tension
    voicings = [
        (1.0, 1.2, 1.5, 1.78),   # m7 voicing
        (1.0, 1.19, 1.5, 2.0),   # m + octave
        (1.0, 1.2, 1.78, 2.4),   # m7 + 9
        (1.0, 1.5, 1.78, 2.0),   # 5 + b7
    ]
    voicing = voicings[sector_idx % len(voicings)]

    t = _t(duration)
    # Slow LFO breathes the chord
    lfo = 0.55 + 0.45 * np.sin(_2PI * (0.07 + 0.01 * (sector_idx % 4)) * t)

    w = np.zeros_like(t)
    for i, mult in enumerate(voicing):
        # Detune slightly per voice for organic shimmer
        det = 1.0 + 0.0028 * ((i * 7) % 5 - 2)
        amp = 0.10 + 0.06 * ((sector_idx + i) % 3) / 2.0
        w += np.sin(_2PI * root * mult * det * t) * amp * (0.7 + 0.3 * lfo)

    # Add a sub-bass moan an octave below the root
    w += np.sin(_2PI * root * 0.5 * t) * 0.08 * lfo

    # Gentle low-pass-ish smoothing via cumulative mean (cheap & cheerful)
    w = (w + np.roll(w, 1) + np.roll(w, 2)) / 3.0

    # Cross-fade ends so the loop has no click
    n     = len(w)
    fade  = int(SAMPLE_RATE * 0.5)
    env   = np.ones(n)
    env[:fade]      = np.linspace(0.0, 1.0, fade)
    env[-fade:]     = np.linspace(1.0, 0.0, fade)
    w = w * env

    peak = np.max(np.abs(w))
    if peak > 0:
        w = w / peak * 0.55
    return _to_sound(w)


# ---------------------------------------------------------------------------
# One-shot SFX

def gun_shot() -> pygame.mixer.Sound:
    dur = 0.09
    w = _noise(dur, amp=0.88) + _saw(260.0, dur, amp=0.32)
    return _to_sound(_adsr(w, 0.001, 0.045, 0.08, 0.04))


def hull_impact() -> pygame.mixer.Sound:
    dur = 0.40
    # Downward frequency chirp 190 → 40 Hz
    inst = np.linspace(190.0, 40.0, int(SAMPLE_RATE * dur))
    phase = np.cumsum(_2PI * inst / SAMPLE_RATE)
    w = np.sin(phase) * 0.65 + _noise(dur, amp=0.18)
    return _to_sound(_adsr(w, 0.001, 0.08, 0.30, 0.20))


def tether_clang() -> pygame.mixer.Sound:
    dur = 0.65
    w  = _sine(880.0,  dur, amp=0.48)
    w += _sine(1340.0, dur, amp=0.26)
    w += _sine(2080.0, dur, amp=0.11)
    w += _noise(dur, amp=0.04)
    return _to_sound(_adsr(w, 0.001, 0.05, 0.18, 0.55))


def tether_snap() -> pygame.mixer.Sound:
    dur = 0.14
    return _to_sound(_adsr(_noise(dur, amp=1.0), 0.001, 0.03, 0.30, 0.10))


def terminal_beep() -> pygame.mixer.Sound:
    dur = 0.055
    w = _sine(1100.0, dur, amp=0.33) + _sine(1650.0, dur, amp=0.13)
    return _to_sound(_adsr(w, 0.003, 0.018, 0.5, 0.025))


def spore_sting() -> pygame.mixer.Sound:
    """Psychedelic warble played when controls invert."""
    dur = 0.55
    t   = _t(dur)
    # Two detuned sines with LFO pitch drift
    lfo = np.sin(_2PI * 3.5 * t)
    w   = np.sin(_2PI * (220.0 + 40.0 * lfo) * t) * 0.35
    w  += np.sin(_2PI * (330.0 - 30.0 * lfo) * t) * 0.25
    w  += _noise(dur, amp=0.06)
    return _to_sound(_adsr(w, 0.01, 0.10, 0.6, 0.30))


# ---------------------------------------------------------------------------
# New SFX — event-driven one-shots

def death_sting() -> pygame.mixer.Sound:
    """Descending synth chord on ship destroyed — two-octave fall over 3s."""
    dur = 3.0
    t   = _t(dur)
    # Three-voice descending chord — exponential frequency fall
    freqs = [440.0, 554.4, 659.3]   # A4, C#5, E5 — minor third + fifth
    w = np.zeros(int(SAMPLE_RATE * dur))
    for f0 in freqs:
        inst_f = f0 * np.exp(-t * 1.3)   # drops ~2 octaves over 3s
        phase  = np.cumsum(_2PI * inst_f / SAMPLE_RATE)
        w     += np.sin(phase) * 0.28
    w += _noise(dur, amp=0.03)
    env = np.exp(-t * 0.6) * 0.80   # smooth long decay
    return _to_sound((w * env).clip(-1.0, 1.0))


def slingshot_whoosh() -> pygame.mixer.Sound:
    """Rising speed rush on successful slingshot."""
    dur = 0.65
    t   = _t(dur)
    inst_f = np.linspace(70.0, 1400.0, len(t)) * (0.92 + 0.08 * np.sin(_2PI * 18 * t))
    phase  = np.cumsum(_2PI * inst_f / SAMPLE_RATE)
    w  = np.sin(phase) * 0.55
    w += _noise(dur, amp=0.10)
    return _to_sound(_adsr(w, 0.008, 0.18, 0.48, 0.35))


def canister_chime() -> pygame.mixer.Sound:
    """Bright C-major arpeggio on fuel pickup."""
    notes = [523.25, 659.25, 783.99, 1046.5]   # C5 E5 G5 C6
    segs  = []
    for freq in notes:
        dur  = 0.10
        t    = _t(dur)
        blip = np.sin(_2PI * freq * t) * 0.55
        blip += np.sin(_2PI * freq * 2 * t) * 0.16
        blip  = _adsr(blip, 0.002, 0.025, 0.65, 0.06)
        segs.append(blip)
        segs.append(np.zeros(int(SAMPLE_RATE * 0.028)))
    wave = np.concatenate(segs)
    return _to_sound(wave.clip(-1.0, 1.0))


def barge_alert() -> pygame.mixer.Sound:
    """Sharp descending chirp when barge enters proximity range."""
    dur  = 0.38
    t    = _t(dur)
    f    = np.linspace(1100.0, 380.0, len(t))
    phase = np.cumsum(_2PI * f / SAMPLE_RATE)
    w     = np.sin(phase) * 0.65
    w    += np.sin(phase * 2) * 0.20
    w    += _noise(dur, amp=0.05)
    return _to_sound(_adsr(w, 0.001, 0.05, 0.42, 0.20))


def delivery_footstep() -> pygame.mixer.Sound:
    """Soft metallic tap — courier boots on deck plate."""
    dur = 0.048
    n   = int(SAMPLE_RATE * dur)
    t   = np.linspace(0.0, dur, n, endpoint=False)
    env = np.exp(-t * 70.0)
    w   = np.random.uniform(-1.0, 1.0, n) * 0.45 * env
    w  += np.sin(_2PI * 260.0 * t) * 0.18 * env
    return _to_sound(w)


def delivery_hit_sting() -> pygame.mixer.Sound:
    """Sharp dissonant shock on obstacle contact."""
    dur = 0.20
    t   = _t(dur)
    f   = np.linspace(900.0, 140.0, len(t))
    phase = np.cumsum(_2PI * f / SAMPLE_RATE)
    w   = np.sin(phase) * 0.50
    w  += _noise(dur, amp=0.38)
    w  += _sine(55.0, dur, amp=0.28)
    return _to_sound(_adsr(w, 0.001, 0.04, 0.18, 0.12))


def delivery_door_chime() -> pygame.mixer.Sound:
    """Rising triumphant chord — reached the drop-off."""
    notes = [523.25, 659.25, 783.99, 1046.5, 1318.51]   # C5 E5 G5 C6 E6
    segs  = []
    for i, freq in enumerate(notes):
        dur  = 0.10 + i * 0.018
        t    = _t(dur)
        blip = np.sin(_2PI * freq * t) * 0.52
        blip += np.sin(_2PI * freq * 2 * t) * 0.14
        blip  = _adsr(blip, 0.001, 0.02, 0.72, 0.08)
        segs.append(blip)
        segs.append(np.zeros(int(SAMPLE_RATE * max(0.005, 0.022 - i * 0.003))))
    return _to_sound(np.concatenate(segs).clip(-1.0, 1.0))


def jump_ready_charge() -> pygame.mixer.Sound:
    """Rising capacitor charge — signals the jump window is open."""
    dur = 1.10
    t   = _t(dur)
    # Sweeping tone: starts low, accelerates up
    freq = np.linspace(55.0, 880.0, len(t)) ** 0.95
    phase = np.cumsum(_2PI * freq / SAMPLE_RATE)
    w  = np.sin(phase) * 0.45
    w += np.sin(phase * 2) * 0.18
    w += np.sin(phase * 3) * 0.08
    w += _noise(dur, amp=0.04)
    # Swell: quiet → loud → hold
    env = np.zeros(len(t))
    sw  = int(SAMPLE_RATE * 0.72)
    env[:sw]  = np.linspace(0.0, 1.0, sw) ** 1.6
    env[sw:]  = 1.0
    w = w * env
    w += _sine(440.0, dur, amp=0.22) * (0.5 + 0.5 * np.sin(_2PI * 8.0 * t))
    return _to_sound(_adsr(w.clip(-1.0, 1.0), 0.01, 0.10, 0.80, 0.15))


def debt_ding() -> pygame.mixer.Sound:
    """Sharp descending two-tone sting — debt milestone reached."""
    dur = 0.38
    w  = _sine(660.0, dur, amp=0.45)
    w += _sine(440.0, dur, amp=0.32)
    w += _noise(dur, amp=0.03)
    return _to_sound(_adsr(w, 0.002, 0.05, 0.40, 0.28))


# ---------------------------------------------------------------------------
# 80s new wave + delta blues palette — drums, bass, guitars, pads
# All sounds returned as pygame.mixer.Sound or numpy arrays as noted.

def drum_kick(duration: float = 0.4) -> pygame.mixer.Sound:
    """808-style boomy kick — sub sine pitch-drops 60→35Hz over ~80ms."""
    n      = int(SAMPLE_RATE * duration)
    t      = np.linspace(0.0, duration, n, endpoint=False)
    drop_n = int(SAMPLE_RATE * 0.08)
    f      = np.empty(n)
    f[:drop_n] = np.linspace(60.0, 35.0, drop_n)
    f[drop_n:] = 35.0
    phase = np.cumsum(_2PI * f / SAMPLE_RATE)
    w     = np.sin(phase) * 0.95
    # punchy click on the front
    click_n = int(SAMPLE_RATE * 0.004)
    if click_n > 0:
        w[:click_n] += np.linspace(1.0, 0.0, click_n) * 0.35
    # body envelope
    env = np.exp(-t * 7.5)
    return _to_sound((w * env).clip(-1.0, 1.0))


def drum_snare_gated(duration: float = 0.5) -> pygame.mixer.Sound:
    """LinnDrum-style snare — noise burst + 200Hz tone with abrupt 80s gated tail."""
    n  = int(SAMPLE_RATE * duration)
    t  = np.linspace(0.0, duration, n, endpoint=False)
    # Noise body + tonal element
    noise = np.random.uniform(-1.0, 1.0, n) * 0.75
    tone  = np.sin(_2PI * 200.0 * t) * 0.45
    tone += np.sin(_2PI * 330.0 * t) * 0.20
    w     = noise + tone
    # Tight attack, sustained noise, abrupt gate cut at ~0.35s
    env = np.empty(n)
    a = int(SAMPLE_RATE * 0.003)
    d = int(SAMPLE_RATE * 0.04)
    gate_t = min(0.35, duration * 0.7)
    g = int(SAMPLE_RATE * gate_t)
    env[:a]      = np.linspace(0.0, 1.0, a)
    env[a:a+d]   = np.linspace(1.0, 0.85, d)
    # sustained body up to gate
    body_end = min(g, n)
    env[a+d:body_end] = np.linspace(0.85, 0.55, max(0, body_end - (a+d)))
    if body_end < n:
        # Quick gated drop to silence — characteristic 80s sound
        cut_n = int(SAMPLE_RATE * 0.015)
        cut_end = min(body_end + cut_n, n)
        env[body_end:cut_end] = np.linspace(0.55, 0.0, cut_end - body_end)
        if cut_end < n:
            env[cut_end:] = 0.0
    return _to_sound((w * env).clip(-1.0, 1.0))


def drum_hihat(duration: float = 0.12) -> pygame.mixer.Sound:
    """Short bright noise burst with fast decay — high-pass feel via diff."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0.0, duration, n, endpoint=False)
    noise = np.random.uniform(-1.0, 1.0, n)
    # Crude high-pass via first-difference
    noise = np.diff(noise, prepend=noise[0])
    noise = np.diff(noise, prepend=noise[0])  # 2nd-order
    # Fast exponential decay
    env = np.exp(-t * 38.0)
    w   = noise * env * 0.55
    return _to_sound(w.clip(-1.0, 1.0))


def drum_clap(duration: float = 0.3) -> pygame.mixer.Sound:
    """Phil Collins / 80s — three short noise bursts ~25ms apart + reverb tail."""
    n = int(SAMPLE_RATE * duration)
    w = np.zeros(n)
    # Three bursts
    burst_dur = 0.012
    burst_n   = int(SAMPLE_RATE * burst_dur)
    burst_env = np.exp(-np.linspace(0.0, burst_dur, burst_n) * 220.0)
    for offset_s in (0.0, 0.018, 0.038):
        i = int(SAMPLE_RATE * offset_s)
        if i + burst_n <= n:
            noise = np.random.uniform(-1.0, 1.0, burst_n)
            # high-pass-ish via diff
            noise = np.diff(noise, prepend=noise[0])
            w[i:i+burst_n] += noise * burst_env * 0.65
    # Reverb tail — filtered noise that lingers
    tail_start = int(SAMPLE_RATE * 0.045)
    tail_n     = n - tail_start
    if tail_n > 0:
        tail_t    = np.linspace(0.0, duration - 0.045, tail_n)
        tail      = np.random.uniform(-1.0, 1.0, tail_n) * 0.18
        # crude low-pass moving avg to make it "verb-y"
        for _ in range(3):
            tail = (tail + np.roll(tail, 1) + np.roll(tail, 2)) / 3.0
        tail_env  = np.exp(-tail_t * 10.0)
        w[tail_start:] += tail * tail_env
    return _to_sound(w.clip(-1.0, 1.0))


def synth_bass_note(freq: float, duration: float = 0.5) -> pygame.mixer.Sound:
    """Moog-style synth bass — saw + sub sine + crude lowpass via mixed harmonics."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0.0, duration, n, endpoint=False)
    # Sawtooth fundamental
    saw = (2.0 * ((t * freq) % 1.0) - 1.0) * 0.55
    # Sub sine an octave down
    sub = np.sin(_2PI * freq * 0.5 * t) * 0.40
    # Mid-harmonic sine for body
    mid = np.sin(_2PI * freq * t) * 0.30
    w = saw + sub + mid
    # Crude lowpass via cumulative averaging — kills the sharpness of saw
    w = (w + np.roll(w, 1) + np.roll(w, 2) + np.roll(w, 3)) / 4.0
    # Tight ADSR — punchy
    w = _adsr(w, 0.006, 0.08, 0.65, max(0.05, duration * 0.30))
    peak = np.max(np.abs(w))
    if peak > 0:
        w = w / peak * 0.75
    return _to_sound(w)


def acoustic_guitar_note(freq: float, duration: float = 1.2) -> pygame.mixer.Sound:
    """Karplus-Strong plucked string with body resonance."""
    n          = int(SAMPLE_RATE * duration)
    buf_len    = max(2, int(SAMPLE_RATE / max(20.0, freq)))
    # Random excitation
    buf        = np.random.uniform(-1.0, 1.0, buf_len)
    out        = np.empty(n)
    decay      = 0.996  # string damping factor
    for i in range(n):
        out[i]            = buf[i % buf_len]
        # Average adjacent samples → string decay
        next_val          = 0.5 * (buf[i % buf_len] + buf[(i + 1) % buf_len]) * decay
        buf[i % buf_len]  = next_val
    # Body resonance — quiet low sine at 90Hz
    t        = np.linspace(0.0, duration, n, endpoint=False)
    body     = np.sin(_2PI * 90.0 * t) * 0.06 * np.exp(-t * 1.8)
    out      = out * 0.55 + body
    # Gentle fade-in to avoid pop, long natural decay
    fade_in  = int(SAMPLE_RATE * 0.005)
    if fade_in > 0:
        out[:fade_in] *= np.linspace(0.0, 1.0, fade_in)
    fade_out = int(SAMPLE_RATE * 0.08)
    if fade_out > 0 and fade_out < n:
        out[-fade_out:] *= np.linspace(1.0, 0.0, fade_out)
    peak = np.max(np.abs(out))
    if peak > 0:
        out = out / peak * 0.70
    return _to_sound(out.clip(-1.0, 1.0))


def slide_blues_note(start_freq: float, end_freq: float,
                     duration: float = 0.8) -> pygame.mixer.Sound:
    """Karplus-Strong with frequency-interpolated buffer length — delta slide."""
    n = int(SAMPLE_RATE * duration)
    # Build frequency curve
    freqs = np.linspace(start_freq, end_freq, n)
    # Start with longest buffer (lowest freq)
    init_len = max(2, int(SAMPLE_RATE / max(20.0, min(start_freq, end_freq))))
    buf      = np.random.uniform(-1.0, 1.0, init_len)
    out      = np.empty(n)
    decay    = 0.997
    # Per-sample buffer-step that varies with target freq
    for i in range(n):
        cur_len = max(2, int(SAMPLE_RATE / max(20.0, freqs[i])))
        idx     = i % cur_len
        nxt_idx = (i + 1) % cur_len
        # Bounds: keep within init_len
        idx     = idx     % init_len
        nxt_idx = nxt_idx % init_len
        out[i]  = buf[idx]
        buf[idx] = 0.5 * (buf[idx] + buf[nxt_idx]) * decay
    # Body resonance with subtle vibrato (slide character)
    t   = np.linspace(0.0, duration, n, endpoint=False)
    vib = 1.0 + 0.012 * np.sin(_2PI * 5.0 * t)
    body = np.sin(_2PI * 80.0 * t * vib) * 0.05 * np.exp(-t * 1.3)
    out  = out * 0.55 + body
    # Envelope — pluck attack, slow decay
    fade_in  = int(SAMPLE_RATE * 0.008)
    if fade_in > 0:
        out[:fade_in] *= np.linspace(0.0, 1.0, fade_in)
    fade_out = int(SAMPLE_RATE * 0.12)
    if fade_out > 0 and fade_out < n:
        out[-fade_out:] *= np.linspace(1.0, 0.0, fade_out)
    peak = np.max(np.abs(out))
    if peak > 0:
        out = out / peak * 0.68
    return _to_sound(out.clip(-1.0, 1.0))


# Chord interval ratios — minor 7 / minor 9
_CHORD_RATIOS = {
    "minor":  [1.0, 1.1892, 1.4983, 1.7818],            # 1, b3, 5, b7
    "minor9": [1.0, 1.1892, 1.4983, 1.7818, 2.2449],    # 1, b3, 5, b7, 9
    "minor7": [1.0, 1.1892, 1.4983, 1.7818],
}


def new_wave_chord(root_freq: float, mode: str = "minor",
                   duration: float = 2.0) -> pygame.mixer.Sound:
    """Layered saw/triangle 7th chord with chorus detune. Tangerine Dream-ish."""
    ratios = _CHORD_RATIOS.get(mode, _CHORD_RATIOS["minor"])
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0.0, duration, n, endpoint=False)
    w = np.zeros(n)
    for i, r in enumerate(ratios):
        f = root_freq * r
        # Saw voice
        saw = (2.0 * ((t * f) % 1.0) - 1.0)
        # Triangle voice via |saw|*2-1
        tri = 2.0 * np.abs(2.0 * ((t * f) % 1.0) - 1.0) - 1.0
        # Slight detune for chorus
        det = 1.0 + 0.004 * ((i * 7) % 5 - 2)
        saw2 = (2.0 * ((t * f * det) % 1.0) - 1.0)
        voice = saw * 0.18 + saw2 * 0.14 + tri * 0.20
        # Amplitude per chord tone — root and 5th louder
        amp = 0.32 if i in (0, 2) else 0.22
        w += voice * amp
    # Crude lowpass — saw/tri otherwise too harsh
    for _ in range(2):
        w = (w + np.roll(w, 1) + np.roll(w, 2)) / 3.0
    # Slow-attack pad envelope
    attack   = int(SAMPLE_RATE * 0.15)
    release  = int(SAMPLE_RATE * min(0.6, duration * 0.3))
    env = np.ones(n)
    if attack > 0:
        env[:attack] = np.linspace(0.0, 1.0, attack)
    if release > 0 and release < n:
        env[-release:] = np.linspace(1.0, 0.0, release)
    w = w * env
    peak = np.max(np.abs(w))
    if peak > 0:
        w = w / peak * 0.55
    return _to_sound(w.clip(-1.0, 1.0))


def gated_reverb_tail(duration: float = 0.4) -> pygame.mixer.Sound:
    """Standalone reverb burst — filtered noise + short envelope. For layering."""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0.0, duration, n, endpoint=False)
    noise = np.random.uniform(-1.0, 1.0, n) * 0.6
    # Multi-pass lowpass for "verby" texture
    for _ in range(4):
        noise = (noise + np.roll(noise, 1) + np.roll(noise, 2)) / 3.0
    # Quick attack, slow body, abrupt gate
    env = np.empty(n)
    a   = int(SAMPLE_RATE * 0.005)
    body = int(SAMPLE_RATE * min(duration * 0.7, 0.28))
    env[:a]          = np.linspace(0.0, 1.0, a)
    env[a:a+body]    = np.linspace(1.0, 0.5, max(0, body))
    if a + body < n:
        cut = int(SAMPLE_RATE * 0.015)
        cut_end = min(a + body + cut, n)
        env[a+body:cut_end] = np.linspace(0.5, 0.0, cut_end - (a+body))
        if cut_end < n:
            env[cut_end:] = 0.0
    return _to_sound((noise * env).clip(-1.0, 1.0))


def terminal_drone(duration: float = 6.0) -> pygame.mixer.Sound:
    """Ominous Am-chord pad that loops during terminal interrogation."""
    t       = _t(duration)
    lfo_a   = 0.72 + 0.28 * np.sin(_2PI * 0.07 * t)
    lfo_b   = 0.86 + 0.14 * np.sin(_2PI * 0.13 * t + 1.2)

    w  = _sine(110.0, duration, amp=0.26) * lfo_a   # A2
    w += _sine(130.8, duration, amp=0.16) * lfo_b   # C3
    w += _sine(164.8, duration, amp=0.11) * lfo_a   # E3
    w += _sine(55.0,  duration, amp=0.20)            # A1 sub
    w += _noise(duration, amp=0.018) * lfo_b         # radio texture

    # Seamless loop fade at edges
    n    = len(w)
    fade = int(SAMPLE_RATE * 0.9)
    w[:fade]  *= np.linspace(0.0, 1.0, fade)
    w[-fade:] *= np.linspace(1.0, 0.0, fade)
    return _to_sound((w * 0.65).clip(-1.0, 1.0))
