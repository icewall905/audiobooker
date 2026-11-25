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


# --- SSE transport and payload variants ------------------------------------
class FakeStreamResponse:
    """Minimal stand-in for a requests streaming response."""

    def __init__(self, lines, status_code=200, content_type="text/event-stream"):
        self._lines = lines
        self.status_code = status_code
        self.headers = {"content-type": content_type}

    def iter_lines(self, decode_unicode=False):
        return iter(self._lines)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def test_parse_stream_returns_the_complete_payload():
    stream = FakeStreamResponse(
        [
            "event: generating",
            'data: [{"status": "halfway"}]',
            "",
            "event: complete",
            'data: [{"path": "/tmp/out.wav"}]',
            "",
        ]
    )

    assert RemoteEngine._parse_stream(stream) == [{"path": "/tmp/out.wav"}]


def test_parse_stream_surfaces_server_errors():
    stream = FakeStreamResponse(["event: error", 'data: {"error": "model exploded"}'])

    with pytest.raises(Exception, match="model exploded"):
        RemoteEngine._parse_stream(stream)


def test_parse_stream_falls_back_to_the_last_payload():
    stream = FakeStreamResponse(['data: [{"path": "/tmp/out.wav"}]'])

    assert RemoteEngine._parse_stream(stream) == [{"path": "/tmp/out.wav"}]


def test_parse_stream_without_data_raises():
    with pytest.raises(Exception, match="without a result"):
        RemoteEngine._parse_stream(FakeStreamResponse(["event: generating"]))


def test_audio_reference_variants():
    engine = RemoteEngine("http://server:7860")

    assert engine._audio_reference([{"path": "/tmp/a.wav"}]) == (
        "url",
        "http://server:7860/file=/tmp/a.wav",
    )
    assert engine._audio_reference([{"url": "http://cdn/a.wav"}]) == ("url", "http://cdn/a.wav")
    kind, value = engine._audio_reference(["data:audio/wav;base64,AAAA"])
    assert kind == "base64" and value.startswith("data:audio")
    assert engine._audio_reference(["clip.wav"]) == ("url", "http://server:7860/file=clip.wav")


def test_audio_reference_without_audio_raises():
    engine = RemoteEngine("http://server:7860")

    with pytest.raises(Exception, match="no audio"):
        engine._audio_reference([{"status": "queued"}])


def test_decode_payload_accepts_a_base64_data_uri():
    import base64

    payload_wav = make_wav(np.zeros(50, dtype="<i2"), 16000)
    encoded = "data:audio/wav;base64," + base64.b64encode(payload_wav).decode()
    engine = RemoteEngine("http://server:7860")

    class NoFetch:
        def get(self, *args, **kwargs):
            raise AssertionError("should not fetch a URL for inline audio")

    samples, sample_rate = engine._decode_payload(NoFetch(), [encoded])

    assert sample_rate == 16000
    assert samples.shape == (50,)


def test_read_result_prefers_sse(monkeypatch):
    engine = RemoteEngine("http://server:7860")
    stream = FakeStreamResponse(["event: complete", 'data: [{"path": "/tmp/a.wav"}]'])

    class Session:
        def get(self, *args, **kwargs):
            return stream

    assert engine._read_result(Session(), "http://server/status") == [{"path": "/tmp/a.wav"}]


def test_read_result_falls_back_to_polling(monkeypatch):
    engine = RemoteEngine("http://server:7860")
    plain = FakeStreamResponse([], content_type="application/json")
    monkeypatch.setattr(engine, "_poll", lambda session, url: ["polled"])

    class Session:
        def get(self, *args, **kwargs):
            return plain

    assert engine._read_result(Session(), "http://server/status") == ["polled"]
