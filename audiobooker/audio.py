"""Streaming audio output.

Instead of holding every generated tensor in RAM until the end (a 10 h book
needs ~3.5 GB plus a second copy for ``torch.cat``), audio is written to one
WAV file per document section as it is produced.  Part files double as
checkpoints: a failed or interrupted run can resume where it stopped, and the
final audiobook is a straight frame-level concatenation of the parts.
"""

from __future__ import annotations

import wave
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional, Sequence

import numpy as np

SAMPLE_WIDTH = 2  # bytes; 16-bit PCM is universally playable
CHANNELS = 1


def to_pcm16(samples: np.ndarray) -> bytes:
    """Convert float samples in [-1, 1] (or int16) to little endian PCM bytes."""
    array = np.asarray(samples)
    if array.dtype == np.int16:
        return np.ascontiguousarray(array).tobytes()

    flat = np.asarray(array, dtype=np.float32).reshape(-1)
    clipped = np.clip(flat, -1.0, 1.0)
    return (clipped * 32767.0).round().astype("<i2").tobytes()


def flatten_mono(array: np.ndarray) -> np.ndarray:
    """Return float32 mono samples, averaging channels when audio is stereo."""
    audio = np.asarray(array, dtype=np.float32)
    if audio.ndim == 2:
        # Accept both (frames, channels) and (channels, frames).
        axis = 1 if audio.shape[1] <= 8 else 0
        audio = audio.mean(axis=axis)
    return np.ascontiguousarray(audio.reshape(-1))


class PartWriter:
    """Append-only WAV writer for a single section."""

    def __init__(self, path: Path, sample_rate: int):
        self.path = Path(path)
        self.sample_rate = int(sample_rate)
        self.frames = 0
        self._handle: Optional[wave.Wave_write] = wave.open(str(self.path), "wb")
        self._handle.setnchannels(CHANNELS)
        self._handle.setsampwidth(SAMPLE_WIDTH)
        self._handle.setframerate(self.sample_rate)

    def write(self, samples: np.ndarray) -> int:
        payload = to_pcm16(samples)
        if not payload:
            return 0
        self._handle.writeframes(payload)
        written = len(payload) // SAMPLE_WIDTH
        self.frames += written
        return written

    def write_silence(self, seconds: float) -> int:
        if seconds <= 0:
            return 0
        total = int(round(seconds * self.sample_rate))
        written = 0
        # Write in 1 s blocks so a long pause never allocates a big buffer.
        block = np.zeros(self.sample_rate, dtype=np.float32)
        remaining = total
        while remaining > 0:
            take = min(remaining, self.sample_rate)
            written += self.write(block[:take])
            remaining -= take
        return written

    def close(self) -> int:
        if self._handle is not None:
            self._handle.close()
            self._handle = None
        return self.frames

    def __enter__(self) -> "PartWriter":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


class AudioSink:
    """Manages the part files for one job."""

    def __init__(self, directory: Path, sample_rate: int):
        self.directory = Path(directory)
        self.sample_rate = int(sample_rate)
        self.directory.mkdir(parents=True, exist_ok=True)

    def part_path(self, index: int) -> Path:
        return self.directory / f"part_{index:05d}.wav"

    @contextmanager
    def open_part(self, index: int) -> Iterator[PartWriter]:
        writer = PartWriter(self.part_path(index), self.sample_rate)
        try:
            yield writer
        finally:
            writer.close()

    def frames_in(self, index: int) -> int:
        path = self.part_path(index)
        if not path.exists() or path.stat().st_size <= 44:
            return 0
        try:
            with wave.open(str(path), "rb") as handle:
                return handle.getnframes()
        except (wave.Error, EOFError, OSError):
            return 0

    def duration_in(self, index: int) -> float:
        return self.frames_in(index) / float(self.sample_rate)

    def concat(self, indexes: Sequence[int], output_path: Path) -> int:
        """Write the parts, in order, into one WAV file. Returns total frames."""
        output_path = Path(output_path)
        if output_path.parent and not output_path.parent.exists():
            output_path.parent.mkdir(parents=True, exist_ok=True)

        total_frames = 0
        with wave.open(str(output_path), "wb") as out:
            out.setnchannels(CHANNELS)
            out.setsampwidth(SAMPLE_WIDTH)
            out.setframerate(self.sample_rate)
            for index in indexes:
                path = self.part_path(index)
                if not path.exists():
                    continue
                with wave.open(str(path), "rb") as part:
                    if part.getframerate() != self.sample_rate:
                        raise ValueError(
                            f"{path.name} is {part.getframerate()} Hz but the job is "
                            f"{self.sample_rate} Hz; delete {self.directory} and re-run"
                        )
                    while True:
                        block = part.readframes(1 << 18)
                        if not block:
                            break
                        out.writeframes(block)
                        total_frames += len(block) // (SAMPLE_WIDTH * CHANNELS)
        return total_frames

    def clear(self) -> None:
        for stale in self.directory.glob("part_*.wav"):
            try:
                stale.unlink()
            except OSError:
                pass
