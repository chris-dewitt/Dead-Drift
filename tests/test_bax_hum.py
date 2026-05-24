"""Bax-hum synth tests (no audio device required).

We mock _to_sound so the synth's numpy pipeline can be exercised without
initialising a real audio backend.  Verifies count, titles, expected
buffer length per hum, finite samples, and amplitude within ±1.0.
"""
from __future__ import annotations
import numpy as np
import pytest

import audio.bax_hum as bh
import audio.synth as synth


@pytest.fixture(autouse=True)
def _mock_to_sound(monkeypatch):
    """Replace _to_sound so it returns the raw numpy buffer for inspection."""
    monkeypatch.setattr(synth, "_to_sound", lambda wave: wave)
    monkeypatch.setattr(bh,    "_to_sound", lambda wave: wave)


def test_hum_count_is_eight():
    assert bh.hum_count() == 8


def test_hum_titles_are_all_distinct_strings():
    titles = [bh.hum_title(i) for i in range(bh.hum_count())]
    assert all(isinstance(t, str) and t for t in titles)
    assert len(set(titles)) == bh.hum_count()


def test_campaign_clear_hum_index_is_seven():
    assert bh.CAMPAIGN_CLEAR_HUM_IDX == 7
    assert 0 <= bh.CAMPAIGN_CLEAR_HUM_IDX < bh.hum_count()


def test_build_hum_returns_finite_buffer_per_index():
    for i in range(bh.hum_count()):
        buf = bh.build_hum(i)
        assert isinstance(buf, np.ndarray), f"hum {i} not an array"
        assert buf.size > 0,                f"hum {i} is empty"
        assert np.all(np.isfinite(buf)),    f"hum {i} contains NaN / Inf"
        assert np.max(np.abs(buf)) <= 1.0,  f"hum {i} clips above 1.0"


def test_build_hum_duration_at_least_eleven_seconds():
    """Each hum is 4 bars at 84 BPM (~11.4 s).  Buffer length should reflect this."""
    sr = synth.SAMPLE_RATE
    for i in range(bh.hum_count()):
        buf = bh.build_hum(i)
        seconds = len(buf) / sr
        # Plan §7.4 — 4 bars at 84 BPM ≈ 11.4 s.  Allow 11.0–14.0 to absorb
        # legato bleed + release tail across variant melodies.
        assert 11.0 <= seconds <= 14.0, \
            f"hum {i} duration {seconds:.2f}s outside expected 11..14s window"


def test_prebuild_all_hums_yields_eight_buffers():
    hums = bh.prebuild_all_hums()
    assert len(hums) == bh.hum_count() == 8


def test_build_hum_raises_on_out_of_range():
    with pytest.raises(IndexError):
        bh.build_hum(8)
    with pytest.raises(IndexError):
        bh.build_hum(-1)
