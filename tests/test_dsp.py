"""Tests for the speech-rate helper."""

import numpy as np
import pytest

from audiobooker.dsp import change_speed


def tone(frames=800, rate=8000):
    timeline = np.arange(frames, dtype=np.float32) / rate
    return (0.5 * np.sin(2 * np.pi * 440 * timeline)).astype(np.float32)


def test_factor_one_is_a_no_op():
    samples = tone()

    result = change_speed(samples, 8000, 1.0)

    assert result.shape == samples.shape
    assert np.allclose(result, samples)


def test_invalid_factor_is_rejected():
    with pytest.raises(ValueError):
        change_speed(tone(), 8000, 0)


def test_faster_speech_is_shorter():
    samples = tone(8000)
    warnings = []

    result = change_speed(samples, 8000, 2.0, warn=warnings.append)

    assert result.shape[0] == pytest.approx(4000, abs=50)
    assert result.dtype == np.float32
    # torchaudio is not installed in CI, so the documented fallback warns once
    if warnings:
        assert "pitch" in warnings[0]


def test_slower_speech_is_longer():
    samples = tone(4000)
    warnings = []

    result = change_speed(samples, 8000, 0.5, warn=warnings.append)

    assert result.shape[0] == pytest.approx(8000, abs=50)


def test_stereo_input_is_flattened():
    stereo = np.stack([tone(400), tone(400)], axis=1)

    result = change_speed(stereo, 8000, 1.0)

    assert result.ndim == 1
    assert result.shape[0] == 400
