"""Tests for the HTTP engine's WAV decoding (the old hardcoded 24 kHz bug)."""

import io
import wave

import numpy as np
import pytest

from audiobooker.engine import Engine, RemoteEngine, _decode_wav


def make_wav(samples: np.ndarray, sample_rate: int, channels: int = 1, width: int = 2) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(width)
        handle.setframerate(sample_rate)
        handle.writeframes(samples.tobytes())
    return buffer.getvalue()


def test_decode_wav_reads_the_real_sample_rate():
    payload = make_wav(np.zeros(100, dtype="<i2"), 32000)

    samples, sample_rate = _decode_wav(payload)

    assert sample_rate == 32000
    assert samples.shape == (100,)


def test_decode_wav_downsamples_stereo_to_mono():
    stereo = np.zeros((80, 2), dtype="<i2")
    payload = make_wav(stereo, 44100, channels=2)

    samples, sample_rate = _decode_wav(payload)

    assert sample_rate == 44100
    assert samples.shape == (80,)


def test_decode_wav_handles_8_bit():
    payload = make_wav(np.full(10, 128, dtype=np.uint8), 8000, width=1)

    samples, _ = _decode_wav(payload)

    assert samples.shape == (10,)
    assert np.allclose(samples, 0.0)


def test_decode_wav_handles_float32():
    floats = np.linspace(-0.5, 0.5, 16, dtype="<f4")
    payload = make_wav(floats, 24000, width=4)

    samples, _ = _decode_wav(payload)

    assert samples.shape == (16,)
    assert pytest.approx(samples[0], abs=1e-6) == -0.5


def test_remote_engine_rejects_sample_rate_mismatch(monkeypatch):
    engine = RemoteEngine("http://example.invalid", sample_rate=24000)

    def fake_request(text, exaggeration=0.5, cfg_weight=0.5):
        return np.zeros(10, dtype=np.float32), 32000

    monkeypatch.setattr(engine, "_request", fake_request)

    with pytest.raises(Exception, match="32000 Hz"):
        engine.generate("hello", exaggeration=0.5, cfg_weight=0.5)


def test_engine_base_class_is_abstract():
    with pytest.raises(TypeError):
        Engine()  # type: ignore[abstract]
