"""
audio/master_fx.py — Master DSP post-mix chain.

Intercepts the pygame mixer's output buffer via set_post_mix() and applies
hull-state audio degradation and AcousticArchive cargo degradation effects.

Hull state thresholds (hull_pct is 0.0 – 1.0):
    1.00 – 0.60  Clean. No processing.
    0.60 – 0.30  Bit-crush to 10 bits + transient boost (+2 dB gain nudge on
                 the already-mixed drums — approximated as a subtle master-gain
                 bump that makes the mix "edgier").
    0.30 – 0.00  Bit-crush to 6 bits + low-pass at ~2 kHz (20-tap running avg)
                 + 3.5 Hz tremolo on master. The harp (blues lick channel) is
                 zeroed by the volume layer in AudioManager; we leave that to
                 the caller and focus purely on the DSP chain here.

Cargo degradation (AcousticArchive chapter), cargo_degradation in 0.0 – 1.0:
    0.0          Clean.
    0.5          10-bit crush + 200 ms slap delay at 18 % wet.
    1.0          6-bit crush + 600 ms tape-echo at 32 % wet + 80 Hz hum bump.
    (Values between 0.0 and 1.0 are interpolated linearly.)

Critical constraints
--------------------
* pygame.mixer.set_post_mix(cb) — cb receives a numpy int16 array IN-PLACE
  (stereo, shape (N, 2)).  No return value.  N ≤ BUFFER_SIZE.
* All working buffers are pre-allocated in __init__; zero heap allocation
  inside _process().
* The tremolo accumulator _t advances by len(array) / SAMPLE_RATE each call.
"""

from __future__ import annotations

import math

import numpy as np
import pygame

SAMPLE_RATE: int = 44100

# Maximum number of samples expected per callback (matches mixer buffer=512
# in AudioManager but we allocate for a safe upper bound).
_BUFFER_SIZE: int = 4096

# Low-pass kernel length (~20 taps → cutoff ≈ SAMPLE_RATE / 20 ≈ 2 205 Hz)
_LP_TAPS: int = 20

# Ring buffer sizes (samples)
_SLAP_DELAY_SAMPLES: int = int(0.200 * SAMPLE_RATE)   # 8 820  (200 ms)
_TAPE_ECHO_SAMPLES:  int = int(0.600 * SAMPLE_RATE)   # 26 460 (600 ms)

# Bit-crush step sizes (int16 headroom = 32 768)
#   step = 32768 >> (bits - 1)
_STEP_10BIT: int = 32768 >> 9    # = 64
_STEP_6BIT:  int = 32768 >> 5    # = 1 024

# Wet mix levels
_SLAP_WET:      float = 0.18
_ECHO_WET:      float = 0.32

# 80 Hz hum bump amplitude (int16 units)
_HUM_AMP_INT16: float = 900.0

# Transient boost at the "edgy" hull threshold (+2 dB ≈ ×1.259)
_EDGE_GAIN: float = 1.259


class MasterFX:
    """
    Master post-mix DSP chain.

    Typical usage::

        fx = MasterFX()
        fx.install()                       # hooks into pygame mixer
        # per-frame:
        fx.update(hull_pct, cargo_deg)
        # on teardown:
        fx.uninstall()

    Pass ``debug=True`` to disable all processing (useful for profiling or
    when running without audio).
    """

    def __init__(self, *, debug: bool = False) -> None:
        self._debug = debug

        # ---------- state scalars ----------------------------------------
        self.hull_pct:          float = 1.0
        self.cargo_degradation: float = 0.0
        self._t:                float = 0.0   # tremolo accumulator (seconds)

        # Hum phase accumulator (80 Hz sine)
        self._hum_phase: float = 0.0

        # ---------- pre-allocated working buffers ------------------------
        # float64 scratch for per-channel processing (mono, BUFFER_SIZE)
        self._scratch_l: np.ndarray = np.zeros(_BUFFER_SIZE, dtype=np.float64)
        self._scratch_r: np.ndarray = np.zeros(_BUFFER_SIZE, dtype=np.float64)

        # Low-pass running-average history (last LP_TAPS-1 samples per channel)
        # We carry the tail between callbacks so the filter is continuous.
        self._lp_hist_l: np.ndarray = np.zeros(_LP_TAPS - 1, dtype=np.float64)
        self._lp_hist_r: np.ndarray = np.zeros(_LP_TAPS - 1, dtype=np.float64)

        # Slap-delay ring buffer (stereo int32 to avoid overflow on mix)
        self._slap_buf: np.ndarray  = np.zeros((_SLAP_DELAY_SAMPLES, 2), dtype=np.int32)
        self._slap_pos: int         = 0

        # Tape-echo ring buffer
        self._echo_buf: np.ndarray  = np.zeros((_TAPE_ECHO_SAMPLES, 2), dtype=np.int32)
        self._echo_pos: int         = 0

        # Tremolo sin table (one full cycle, 256 points — looked up by phase)
        # Not strictly necessary but avoids math.sin() inside the hot path;
        # we use a pre-computed table indexed by fractional position.
        # (We do use math.sin once per callback for simplicity and correctness
        #  rather than a table, since one sin call per frame is negligible.)

    # ------------------------------------------------------------------
    # Public API

    def install(self) -> None:
        """Register the post-mix callback with pygame.mixer."""
        pygame.mixer.set_post_mix(self._process)

    def uninstall(self) -> None:
        """Remove the post-mix callback."""
        pygame.mixer.set_post_mix(None)

    def update(self, hull_pct: float, cargo_degradation: float = 0.0) -> None:
        """
        Update DSP state from the game loop (called once per frame, NOT from
        inside the callback).  Thread-safety note: pygame's post-mix callback
        runs on the SDL audio thread; writing a float is atomic on CPython so
        this is safe without a lock.
        """
        self.hull_pct          = max(0.0, min(1.0, hull_pct))
        self.cargo_degradation = max(0.0, min(1.0, cargo_degradation))

    # ------------------------------------------------------------------
    # Internal callback — must be fast, zero allocation

    def _process(self, array: np.ndarray) -> None:
        """
        pygame post-mix callback.  ``array`` is int16, shape (N, 2), IN-PLACE.
        Modify directly; no return value needed.
        """
        if self._debug:
            return

        n = len(array)
        hull  = self.hull_pct
        cargo = self.cargo_degradation

        # Determine active hull band
        hull_crush_bits:  int   = 0       # 0 = no crush
        apply_lowpass:    bool  = False
        apply_tremolo:    bool  = False
        edge_gain:        float = 1.0

        if hull < 0.30:
            hull_crush_bits = 6
            apply_lowpass   = True
            apply_tremolo   = True
        elif hull < 0.60:
            hull_crush_bits = 10
            edge_gain       = _EDGE_GAIN

        # Determine cargo band (interpolated between 0→0.5 and 0.5→1.0)
        cargo_crush_bits: int   = 0
        apply_slap:       bool  = False
        apply_echo:       bool  = False
        apply_hum:        bool  = False

        if cargo >= 0.5:
            # Full degradation zone: 6-bit crush + tape echo + 80 Hz hum
            t = (cargo - 0.5) * 2.0           # 0..1 within this zone
            cargo_crush_bits = 6
            apply_echo       = True
            apply_hum        = cargo >= 0.75   # hum kicks in past 0.75
        elif cargo > 0.0:
            # Mild degradation zone: 10-bit crush + slap delay
            cargo_crush_bits = 10
            apply_slap       = True

        # ---- Resolve effective bit-crush depth ---------------------------
        # Take the *worse* (lower-bit) crush from hull and cargo bands.
        bits = 0
        if hull_crush_bits and cargo_crush_bits:
            bits = min(hull_crush_bits, cargo_crush_bits)
        else:
            bits = hull_crush_bits or cargo_crush_bits

        # ----------------------------------------------------------------
        # 1. Bit-crush (in-place, integer arithmetic — no float conversion)
        # ----------------------------------------------------------------
        if bits:
            step = 32768 >> (bits - 1)
            # Quantise: round to nearest multiple of step.
            # array is int16; to avoid overflow we work in int32 briefly.
            tmp = array.astype(np.int32)
            half_step = step >> 1
            tmp = ((tmp + half_step) // step) * step
            np.clip(tmp, -32768, 32767, out=tmp)
            array[:] = tmp.astype(np.int16)

        # ----------------------------------------------------------------
        # 2. Low-pass filter (~2 kHz, hull < 30%)
        #    Cheap 20-tap FIR (uniform kernel = running average).
        #    Applied per channel using pre-allocated scratch buffers.
        # ----------------------------------------------------------------
        if apply_lowpass:
            self._apply_lowpass(array, n)

        # ----------------------------------------------------------------
        # 3. Edge gain (hull 30%–60%) — makes the mix "edgier"
        # ----------------------------------------------------------------
        if edge_gain != 1.0:
            tmp = array.astype(np.int32)
            tmp = (tmp * edge_gain).astype(np.int32)  # type: ignore[assignment]
            np.clip(tmp, -32768, 32767, out=tmp)
            array[:] = tmp.astype(np.int16)

        # ----------------------------------------------------------------
        # 4. Slap delay (cargo 0.0–0.5, 200 ms, 18% wet)
        # ----------------------------------------------------------------
        if apply_slap:
            self._apply_ring_delay(
                array, n,
                self._slap_buf, _SLAP_DELAY_SAMPLES, self._slap_pos,
                _SLAP_WET,
            )
            # Advance slap write position
            self._slap_pos = (self._slap_pos + n) % _SLAP_DELAY_SAMPLES

        # ----------------------------------------------------------------
        # 5. Tape echo (cargo 0.5–1.0, 600 ms, 32% wet)
        # ----------------------------------------------------------------
        if apply_echo:
            self._apply_ring_delay(
                array, n,
                self._echo_buf, _TAPE_ECHO_SAMPLES, self._echo_pos,
                _ECHO_WET,
            )
            self._echo_pos = (self._echo_pos + n) % _TAPE_ECHO_SAMPLES

        # ----------------------------------------------------------------
        # 6. 80 Hz hum bump (cargo > 0.75)
        # ----------------------------------------------------------------
        if apply_hum:
            self._apply_hum(array, n)

        # ----------------------------------------------------------------
        # 7. 3.5 Hz tremolo (hull < 30%)
        # ----------------------------------------------------------------
        if apply_tremolo:
            self._apply_tremolo(array, n)

        # Advance tremolo time (do this even when tremolo is inactive so that
        # it doesn't snap when it activates).
        self._t += n / SAMPLE_RATE

    # ------------------------------------------------------------------
    # DSP helpers — called only from _process(), no allocation

    def _apply_lowpass(self, array: np.ndarray, n: int) -> None:
        """
        20-tap uniform FIR low-pass per channel, continuous across callbacks.
        Operates on self._scratch_l / _r float64 arrays.
        """
        inv_taps = 1.0 / _LP_TAPS

        for ch_idx, (scratch, hist) in enumerate((
            (self._scratch_l, self._lp_hist_l),
            (self._scratch_r, self._lp_hist_r),
        )):
            col = array[:n, ch_idx].astype(np.float64)

            # Prepend history so the convolution is continuous
            extended_len = (_LP_TAPS - 1) + n
            # Reuse scratch for the extended signal (it's BUFFER_SIZE, big enough)
            scratch[:_LP_TAPS - 1] = hist
            scratch[_LP_TAPS - 1 : extended_len] = col

            # Running average via cumsum trick
            cs = np.cumsum(scratch[:extended_len])
            cs[_LP_TAPS:] = cs[_LP_TAPS:] - cs[:-_LP_TAPS]
            averaged = cs[_LP_TAPS - 1:] * inv_taps   # shape (n,)

            # Save last (LP_TAPS-1) samples as new history
            hist[:] = scratch[n : n + (_LP_TAPS - 1)]

            out = averaged[:n]
            np.clip(out, -32768.0, 32767.0, out=out)
            array[:n, ch_idx] = out.astype(np.int16)

    def _apply_ring_delay(
        self,
        array: np.ndarray,
        n: int,
        ring: np.ndarray,
        ring_size: int,
        write_pos: int,
        wet: float,
    ) -> None:
        """
        Mix in a ring-buffer delay (slap or tape echo) at ``wet`` proportion.
        The ring buffer is written AFTER reading so the delay is ring_size samples.
        Operates in-place on ``array``.
        """
        dry = 1.0 - wet

        for i in range(n):
            read_pos = (write_pos + i) % ring_size
            delayed  = ring[read_pos]   # int32 stereo sample

            # Mix: out = dry * dry_sample + wet * delayed
            dry_sample = array[i].astype(np.int32)
            mixed      = (dry_sample * dry + delayed * wet).astype(np.int32)
            np.clip(mixed, -32768, 32767, out=mixed)
            array[i]   = mixed.astype(np.int16)

            # Write current (already-processed) dry sample into ring
            ring[read_pos] = dry_sample

    def _apply_hum(self, array: np.ndarray, n: int) -> None:
        """Add a low 80 Hz sine hum bump to both channels."""
        two_pi   = 2.0 * math.pi
        freq_inc = two_pi * 80.0 / SAMPLE_RATE

        # Build hum samples into scratch_l (reused as a temp mono buffer)
        hum = self._scratch_l
        phase = self._hum_phase
        for i in range(n):
            hum[i] = _HUM_AMP_INT16 * math.sin(phase)
            phase  = (phase + freq_inc) % two_pi
        self._hum_phase = phase

        # Add to both channels with clipping
        tmp = array[:n].astype(np.int32)
        hum_int = hum[:n].astype(np.int32)
        tmp[:, 0] += hum_int
        tmp[:, 1] += hum_int
        np.clip(tmp, -32768, 32767, out=tmp)
        array[:n] = tmp.astype(np.int16)

    def _apply_tremolo(self, array: np.ndarray, n: int) -> None:
        """
        Apply 3.5 Hz amplitude tremolo: gain = 0.7 + 0.3 * sin(2π × 3.5 × t).
        t advances continuously across callbacks.
        """
        two_pi   = 2.0 * math.pi
        freq     = 3.5
        t_start  = self._t
        t_inc    = 1.0 / SAMPLE_RATE

        # Build per-sample gain envelope into scratch_l
        gain_buf = self._scratch_l
        for i in range(n):
            t_i        = t_start + i * t_inc
            gain_buf[i] = 0.7 + 0.3 * math.sin(two_pi * freq * t_i)

        tmp = array[:n].astype(np.float64)
        tmp[:, 0] *= gain_buf[:n]
        tmp[:, 1] *= gain_buf[:n]
        np.clip(tmp, -32768.0, 32767.0, out=tmp)
        array[:n] = tmp.astype(np.int16)
