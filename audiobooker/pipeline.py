"""Audiobook pipeline: text -> chunks -> engine -> streamed WAV.

Responsibilities kept here (and tested without a GPU):

* checkpointing/resume via a manifest next to the part files (fixes unbounded
  RAM growth and all-or-nothing runs);
* retries plus explicit failure reporting instead of silently dropping text;
* a single implementation shared by the CLI, the remote CLI and the web UI.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

from .audio import AudioSink
from .dsp import change_speed
from .engine import Engine
from .text import (
    DEFAULT_MAX_CHUNK_LENGTH,
    Section,
    count_chapters,
    detect_sections,
    input_problems,
    read_document,
    split_into_chunks,
    split_paragraphs,
)

MANIFEST_VERSION = 3

Log = Callable[[str], None]
Progress = Callable[[int, int, str], None]


class PipelineError(RuntimeError):
    """Fatal problem: bad input, no engine, nothing to save."""


@dataclass
class ChunkFailure:
    """A chunk that could not be synthesised (text that is missing from output)."""

    section: int
    chunk: int
    chars: int
    error: str
    preview: str

    def as_dict(self) -> dict:
        return {
            "section": self.section + 1,
            "chunk": self.chunk,
            "chars": self.chars,
            "error": self.error,
            "preview": self.preview,
        }

    def describe(self) -> str:
        return f"section {self.section + 1}, chunk {self.chunk} ({self.chars} chars): {self.error}"


@dataclass
class JobResult:
    output_path: Optional[str] = None
    output_paths: List[str] = field(default_factory=list)
    sections: int = 0
    chapters: int = 0
    chunks_total: int = 0
    chunks_synthesized: int = 0
    chunks_reused: int = 0
    chunks_missing_sections: int = 0
    failures: List[ChunkFailure] = field(default_factory=list)
    duration_seconds: float = 0.0
    elapsed_seconds: float = 0.0
    aborted: bool = False

    @property
    def chunks_failed(self) -> int:
        return len(self.failures)

    @property
    def complete(self) -> bool:
        return self.output_path is not None and not self.failures and not self.aborted

    def summary_lines(self) -> List[str]:
        lines = []
        if self.complete:
            lines.append("✅ Audiobook complete")
        elif self.aborted:
            lines.append("⛔ Aborted (strict mode); nothing was written")
        else:
            lines.append(
                f"⚠️  Audiobook written with {self.chunks_failed} chunk(s) of text missing"
            )
        if len(self.output_paths) > 1:
            lines.append(f"   Output: {len(self.output_paths)} files")
            for path in self.output_paths:
                lines.append(f"     {path}")
        elif self.output_path:
            lines.append(f"   Output: {self.output_path}")
        minutes = self.duration_seconds / 60
        lines.append(f"   Duration: {minutes:.1f} min ({self.duration_seconds:.0f} s)")
        lines.append(
            f"   Sections: {self.sections} ({self.chapters} chapter titles), "
            f"chunks: {self.chunks_total}"
        )
        lines.append(
            f"   Synthesised {self.chunks_synthesized} chunk(s), "
            f"reused {self.chunks_reused} from checkpoint(s)"
        )
        if self.chunks_missing_sections:
            lines.append(f"   Empty sections skipped: {self.chunks_missing_sections}")
        if self.failures:
            lines.append(f"   Missing chunks: {self.chunks_failed}")
        if self.elapsed_seconds:
            lines.append(f"   Wall clock: {self.elapsed_seconds / 60:.1f} min")
        return lines


@dataclass
class PipelineConfig:
    document_path: str = "sample_document.txt"
    output_path: str = "my_audiobook.wav"
    document_text: Optional[str] = None  # used by the web UI instead of a file
    voice_prompt_path: Optional[str] = None
    exaggeration: float = 0.5
    cfg_weight: float = 0.5
    chapter_pause: float = 1.0
    paragraph_pause: float = 1.0
    speech_rate: float = 1.0
    max_chunk_length: int = DEFAULT_MAX_CHUNK_LENGTH
    chapter_pattern: Optional[str] = None
    retries: int = 2
    retry_delay: float = 1.0
    resume: bool = True
    keep_parts: bool = False
    strict: bool = False
    split_chapters: bool = False
    mp3: bool = False


def voice_fingerprint(path: Optional[str]) -> Optional[str]:
    """Cheap identity for a voice prompt so checkpoints are only reused for it."""
    if not path:
        return None
    try:
        digest = sha256()
        with open(path, "rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
        return digest.hexdigest()[:16]
    except OSError:
        return f"path:{os.path.abspath(path)}"


class Manifest:
    """Checkpoint bookkeeping for one output file."""

    def __init__(self, path: Path, signature: dict):
        self.path = Path(path)
        self.signature = signature
        self.parts: dict = {}
        self.valid = False
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if data.get("manifest_version") != MANIFEST_VERSION:
            return
        if data.get("signature") != self.signature:
            return
        self.parts = dict(data.get("parts") or {})
        self.valid = True

    @staticmethod
    def key(index: int) -> str:
        return f"{index:05d}"

    @staticmethod
    def fingerprint(text: str) -> str:
        return sha256(text.encode("utf-8")).hexdigest()[:16]

    def reusable(self) -> int:
        return sum(1 for entry in self.parts.values() if entry.get("status") == "done")

    def is_reusable(self, index: int, text: str, part_path: Path) -> bool:
        entry = self.parts.get(self.key(index))
        if not entry or entry.get("status") != "done":
            return False
        if entry.get("fingerprint") != self.fingerprint(text):
            return False
        return part_path.exists() and part_path.stat().st_size > 44

    def mark(self, index: int, text: str, status: str, frames: int, error: Optional[str] = None) -> None:
        entry = {
            "status": status,
            "fingerprint": self.fingerprint(text),
            "frames": int(frames),
        }
        if error:
            entry["error"] = error[:300]
        self.parts[self.key(index)] = entry

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "manifest_version": MANIFEST_VERSION,
            "signature": self.signature,
            "parts": self.parts,
        }
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def reset(self) -> None:
        self.parts = {}
        self.save()


class AudiobookPipeline:
    """Runs one audiobook job, streaming sections to disk as they complete."""

    def __init__(
        self,
        config: PipelineConfig,
        engine: Optional[Engine] = None,
        log: Optional[Log] = None,
        progress: Optional[Progress] = None,
    ):
        self.config = config
        self.engine = engine
        self._log = log or (lambda message: None)
        self._progress = progress or (lambda done, total, message: None)
        self._done = 0
        self._total = 0
        self._sample_rate = 0
        self._speed_warned = False

    # -- layout ------------------------------------------------------------
    @property
    def output_path(self) -> Path:
        return Path(self.config.output_path)

    @property
    def parts_dir(self) -> Path:
        stem = self.output_path.stem or self.output_path.name or "audiobook"
        return self.output_path.parent / f"{stem}.parts"

    def plan(self) -> Tuple[List[Section], List[int]]:
        """Detected sections and the number of engine calls each needs."""
        text = self._document_text()
        sections = detect_sections(text, self.config.chapter_pattern)
        counts = [sum(len(group) for group in self._paragraph_chunks(section)) for section in sections]
        return sections, counts

    def _paragraph_chunks(self, section: Section) -> List[List[str]]:
        """Chunks for a section, grouped per paragraph (pauses go between groups)."""
        if section.is_chapter_title:
            return [[section.text]]
        groups = [
            split_into_chunks(paragraph, self.config.max_chunk_length)
            for paragraph in split_paragraphs(section.text)
        ]
        return [group for group in groups if group]

    # -- helpers -----------------------------------------------------------
    def _document_text(self) -> str:
        if self.config.document_text is not None:
            return self.config.document_text
        problems = input_problems(self.config.document_path, self.config.voice_prompt_path)
        if problems:
            raise PipelineError("; ".join(problems))
        return read_document(self.config.document_path)

    def _signature(self, sample_rate: int) -> dict:
        cfg = self.config
        return {
            "manifest_version": MANIFEST_VERSION,
            "sample_rate": int(sample_rate),
            "engine": getattr(self.engine, "name", "unknown"),
            "voice": voice_fingerprint(cfg.voice_prompt_path),
            "exaggeration": round(float(cfg.exaggeration), 6),
            "cfg_weight": round(float(cfg.cfg_weight), 6),
            "chapter_pause": round(float(cfg.chapter_pause), 6),
            "paragraph_pause": round(float(cfg.paragraph_pause), 6),
            "speech_rate": round(float(cfg.speech_rate), 6),
            "max_chunk_length": int(cfg.max_chunk_length),
        }

    def _apply_speed(self, samples):
        """Apply --speech-rate, warning only once if the fallback is used."""
        factor = float(self.config.speech_rate)
        if abs(factor - 1.0) < 1e-3:
            return samples
        warn = None
        if not self._speed_warned:
            warn = lambda message: self._log(f"  ! {message}")  # noqa: E731
            self._speed_warned = True
        return change_speed(samples, self._sample_rate, factor, warn=warn)

    def _synthesize(self, text: str):
        cfg = self.config
        attempts = max(1, int(cfg.retries) + 1)
        last_error: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            try:
                return self.engine.generate(
                    text, exaggeration=cfg.exaggeration, cfg_weight=cfg.cfg_weight
                )
            except Exception as exc:  # engine-specific, retry anything transient
                last_error = exc
                if attempt < attempts:
                    delay = float(cfg.retry_delay) * attempt
                    self._log(f"    retry {attempt}/{attempts - 1} after error: {exc}")
                    if delay > 0:
                        time.sleep(delay)
        raise last_error if last_error is not None else RuntimeError("engine failed")

    def _render_section(
        self,
        sink: AudioSink,
        index: int,
        section: Section,
        stop_on_failure: bool,
    ) -> Tuple[int, List[ChunkFailure]]:
        cfg = self.config
        failures: List[ChunkFailure] = []
        synthesised = 0

        paragraph_chunks = self._paragraph_chunks(section)
        pieces = [piece for group in paragraph_chunks for piece in group]
        if not pieces:
            return 0, []

        with sink.open_part(index) as writer:
            if section.is_chapter_title and cfg.chapter_pause > 0 and index > 0:
                writer.write_silence(cfg.chapter_pause)

            number = 0
            for paragraph_index, group in enumerate(paragraph_chunks):
                if paragraph_index and cfg.paragraph_pause > 0:
                    writer.write_silence(cfg.paragraph_pause)
                for piece in group:
                    number += 1
                    try:
                        writer.write(self._apply_speed(self._synthesize(piece)))
                        synthesised += 1
                    except Exception as exc:
                        failures.append(
                            ChunkFailure(
                                section=index,
                                chunk=number,
                                chars=len(piece),
                                error=str(exc) or exc.__class__.__name__,
                                preview=piece[:80],
                            )
                        )
                        self._log(
                            f"  ✗ section {index + 1} chunk {number}/{len(pieces)} failed: {exc}"
                        )
                        if stop_on_failure:
                            return synthesised, failures
                    finally:
                        self._advance(index, number, len(pieces))

            if section.is_chapter_title and cfg.chapter_pause > 0:
                writer.write_silence(cfg.chapter_pause)

        return synthesised, failures

    def _advance(self, index: int, number: int, total_in_section: int) -> None:
        self._done = min(self._total, self._done + 1)
        note = "chapter title" if total_in_section == 1 else f"chunk {number}/{total_in_section}"
        self._progress(self._done, max(self._total, 1), f"section {index + 1}: {note}")

    # -- output assembly ---------------------------------------------------
    def _chapter_groups(self, sections: Sequence[Section]) -> List[List[int]]:
        """Section indexes grouped per chapter; the preface joins chapter 1."""
        groups: List[List[int]] = []
        pending: List[int] = []
        current: Optional[List[int]] = None
        for index, section in enumerate(sections):
            if section.is_chapter_title:
                if current is not None:
                    groups.append(current)
                current = [*pending, index]
                pending = []
            elif current is None:
                pending.append(index)
            else:
                current.append(index)
        if current is not None:
            groups.append(current)
        elif pending:
            groups.append(pending)
        return [group for group in groups if group]

    def _assemble(
        self, sink: AudioSink, sections: Sequence[Section], available: Sequence[int]
    ) -> Tuple[List[Path], int]:
        """Write the final file(s), optionally one per chapter and/or as MP3."""
        cfg = self.config
        output = self.output_path
        if output.parent != Path(""):
            output.parent.mkdir(parents=True, exist_ok=True)

        groups = self._chapter_groups(sections)
        if not cfg.split_chapters or len(groups) <= 1:
            targets = [(output, list(available))]
        else:
            targets = []
            for number, group in enumerate(groups, 1):
                indexes = [index for index in group if index in available]
                if indexes:
                    targets.append((output.parent / f"chapter{number}.wav", indexes))

        outputs: List[Path] = []
        total_frames = 0
        for target, indexes in targets:
            # Concatenate next to the target, then rename: a crash during the
            # final copy must not leave a truncated file that looks finished.
            staging = target.with_suffix(target.suffix + ".tmp")
            frames = sink.concat(indexes, staging)
            if frames <= 0:
                staging.unlink(missing_ok=True)
                continue
            os.replace(staging, target)
            total_frames += frames
            outputs.append(self._encode_mp3(target) if cfg.mp3 else target)

        if not outputs:
            raise PipelineError("no audio was generated")
        return outputs, total_frames

    def _encode_mp3(self, wav_path: Path) -> Path:
        """Convert with ffmpeg; keep the WAV if that is not possible."""
        mp3_path = wav_path.with_suffix(".mp3")
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            self._log("  ! ffmpeg not found: keeping WAV output")
            return wav_path
        completed = subprocess.run(
            [
                ffmpeg, "-loglevel", "error", "-y", "-i", str(wav_path),
                "-codec:a", "libmp3lame", "-q:a", "2", str(mp3_path),
            ],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0 or not mp3_path.exists():
            detail = (completed.stderr or "").strip().splitlines()
            self._log(f"  ! MP3 conversion failed ({detail[-1] if detail else 'unknown'}); keeping WAV")
            return wav_path
        wav_path.unlink(missing_ok=True)
        return mp3_path

    # -- main entry point --------------------------------------------------
    def run(self) -> JobResult:
        started = time.monotonic()
        cfg = self.config

        sections, counts = self.plan()
        if not sections:
            raise PipelineError("document contains no readable text")

        result = JobResult(
            sections=len(sections),
            chapters=count_chapters(sections),
            chunks_total=sum(counts),
        )
        self._total = result.chunks_total
        self._done = 0
        self._log(
            f"Detected {len(sections)} sections ({result.chapters} chapter titles, "
            f"{result.chunks_total} chunks)"
        )

        if self.engine is None:
            raise PipelineError("no TTS engine configured")
        if cfg.speech_rate <= 0:
            raise PipelineError(f"--speech-rate must be positive, got {cfg.speech_rate}")
        if cfg.paragraph_pause < 0:
            raise PipelineError(f"--paragraph-pause must be >= 0, got {cfg.paragraph_pause}")
        self.engine.prepare()
        sample_rate = int(self.engine.sample_rate)
        if sample_rate <= 0:
            raise PipelineError(f"engine {self.engine.name} reports an invalid sample rate")
        self._sample_rate = sample_rate

        sink = AudioSink(self.parts_dir, sample_rate)
        manifest = Manifest(self.parts_dir / "manifest.json", self._signature(sample_rate))
        if not cfg.resume:
            manifest.reset()
            sink.clear()
            self._log("Resume disabled: rendering from scratch")
        elif manifest.reusable():
            self._log(f"Resuming: {manifest.reusable()} section(s) already rendered")

        for index, section in enumerate(sections):
            count = counts[index]
            if manifest.is_reusable(index, section.text, sink.part_path(index)):
                result.chunks_reused += count
                self._done += count
                self._progress(self._done, self._total, f"section {index + 1}: reused checkpoint")
                continue

            synthesised, failures = self._render_section(
                sink, index, section, stop_on_failure=cfg.strict
            )
            frames = sink.frames_in(index)
            if failures:
                result.failures.extend(failures)
                if synthesised:
                    manifest.mark(index, section.text, "partial", frames, failures[0].error)
                else:
                    # Only chapter pause silence was written: drop it rather than
                    # shipping a silent gap, and let the next run retry the section.
                    manifest.mark(index, section.text, "failed", 0, failures[0].error)
                    sink.part_path(index).unlink(missing_ok=True)
            else:
                manifest.mark(index, section.text, "done", frames)
            result.chunks_synthesized += synthesised
            manifest.save()

            if failures and cfg.strict:
                result.aborted = True
                self._log("Strict mode: stopping after the first failed chunk")
                break

        if result.aborted:
            result.elapsed_seconds = time.monotonic() - started
            return result

        available = [index for index in range(len(sections)) if sink.frames_in(index) > 0]
        result.chunks_missing_sections = len(sections) - len(available)
        if not available:
            raise PipelineError("no audio was generated")

        outputs, frames = self._assemble(sink, sections, available)
        result.output_paths = [str(path) for path in outputs]
        result.output_path = result.output_paths[0] if result.output_paths else None
        result.duration_seconds = frames / float(sample_rate)
        result.elapsed_seconds = time.monotonic() - started

        report = self.output_path.with_name(f"{self.output_path.stem}.failures.json")
        if result.failures:
            report.write_text(
                json.dumps([failure.as_dict() for failure in result.failures], indent=2),
                encoding="utf-8",
            )
            self._log(f"Failure report written to {report}")
        elif report.exists():
            # a previous partial run left a report behind; the text is complete now
            report.unlink(missing_ok=True)

        if not cfg.keep_parts and not result.failures:
            shutil.rmtree(self.parts_dir, ignore_errors=True)
        return result
