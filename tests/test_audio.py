"""Tests for the streaming WAV writer (issue #1)."""

import wave

import numpy as np
import pytest

from audiobooker.audio import AudioSink, PartWriter, flatten_mono, to_pcm16


def test_to_pcm16_clips_out_of_range_samples():
    payload = to_pcm16(np.array([2.0, -2.0, 0.0], dtype=np.float32))

    assert np.frombuffer(payload, dtype="<i2").tolist() == [32767, -32767, 0]


def test_to_pcm16_passes_through_int16():
    payload = to_pcm16(np.array([1, -1, 300], dtype=np.int16))

    assert np.frombuffer(payload, dtype="<i2").tolist() == [1, -1, 300]


def test_flatten_mono_averages_stereo():
    stereo = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)

    mono = flatten_mono(stereo)

    assert mono.tolist() == [0.5, 0.5]


def test_part_writer_counts_speech_and_silence(tmp_path):
    path = tmp_path / "part.wav"

    with PartWriter(path, 8000) as writer:
        writer.write(np.zeros(800, dtype=np.float32))
        writer.write_silence(0.5)
        assert writer.frames == 4800

    with wave.open(str(path)) as handle:
        assert handle.getframerate() == 8000
        assert handle.getnchannels() == 1
        assert handle.getnframes() == 4800


def test_sink_concatenates_parts_in_order(tmp_path):
    sink = AudioSink(tmp_path / "parts", 8000)
    for index, size in enumerate((100, 200, 300)):
        with sink.open_part(index) as writer:
            writer.write(np.ones(size, dtype=np.float32))

    output = tmp_path / "book.wav"
    frames = sink.concat([0, 1, 2], output)

    assert frames == 600
    with wave.open(str(output)) as handle:
        assert handle.getnframes() == 600
        assert handle.getframerate() == 8000


def test_sink_reports_missing_or_empty_parts(tmp_path):
    sink = AudioSink(tmp_path / "parts", 8000)

    assert sink.frames_in(0) == 0
    assert sink.duration_in(0) == 0.0


def test_sink_rejects_sample_rate_mismatch(tmp_path):
    sink = AudioSink(tmp_path / "parts", 8000)
    with PartWriter(sink.part_path(0), 16000) as writer:
        writer.write(np.zeros(10, dtype=np.float32))

    with pytest.raises(ValueError, match="16000 Hz"):
        sink.concat([0], tmp_path / "out.wav")


def test_clear_removes_only_parts(tmp_path):
    sink = AudioSink(tmp_path / "parts", 8000)
    with sink.open_part(0) as writer:
        writer.write(np.zeros(10, dtype=np.float32))
    keep = sink.directory / "manifest.json"
    keep.write_text("{}", encoding="utf-8")

    sink.clear()

    assert not sink.part_path(0).exists()
    assert keep.exists()
