"""Tests for streaming, checkpointing and failure reporting (issues #1 and #2)."""

import dataclasses
import json
import shutil
import wave
from pathlib import Path

import pytest
from fake_engine import CountingFailer, FakeEngine

from audiobooker.pipeline import AudiobookPipeline, PipelineConfig, PipelineError

DOCUMENT = """Chapter 1: The Start

Alpha beta gamma. Delta epsilon zeta.

Chapter 2: The End

Eta theta iota. Kappa lambda mu."""


def make_config(tmp_path, **overrides):
    values = dict(
        document_text=DOCUMENT,
        output_path=str(tmp_path / "book.wav"),
        retries=0,
        retry_delay=0.0,
        chapter_pause=0.5,
    )
    values.update(overrides)
    return PipelineConfig(**values)


def frames_of(path):
    with wave.open(str(path)) as handle:
        return handle.getnframes(), handle.getframerate()


def test_happy_path_streams_and_cleans_up(tmp_path):
    engine = FakeEngine()

    result = AudiobookPipeline(make_config(tmp_path), engine=engine).run()

    assert result.complete
    assert result.failures == []
    assert result.chunks_total == result.chunks_synthesized
    assert result.duration_seconds > 0
    assert result.output_path and (tmp_path / "book.wav").exists()
    frames, rate = frames_of(result.output_path)
    assert rate == engine.sample_rate
    assert frames == pytest.approx(result.duration_seconds * rate, abs=1)
    # parts are removed after a clean run
    assert not (tmp_path / "book.parts").exists()


def test_audio_is_written_per_section_not_buffered(tmp_path):
    cfg = make_config(tmp_path, keep_parts=True)

    AudiobookPipeline(cfg, engine=FakeEngine()).run()

    parts = sorted((tmp_path / "book.parts").glob("part_*.wav"))
    assert len(parts) == 4  # 2 headings + 2 bodies
    assert all(part.stat().st_size > 44 for part in parts)


def test_manifest_records_every_section(tmp_path):
    cfg = make_config(tmp_path, keep_parts=True)

    AudiobookPipeline(cfg, engine=FakeEngine()).run()

    manifest = json.loads((tmp_path / "book.parts" / "manifest.json").read_text())
    assert all(entry["status"] == "done" for entry in manifest["parts"].values())
    assert len(manifest["parts"]) == 4


def test_failed_chunk_is_reported_and_kept_for_resume(tmp_path):
    cfg = make_config(tmp_path)
    engine = FakeEngine(fail_on=CountingFailer(target=2), fail_times=1)

    result = AudiobookPipeline(cfg, engine=engine).run()

    assert not result.complete
    assert result.chunks_failed == 1
    assert result.output_path and (tmp_path / "book.wav").exists()
    report = tmp_path / "book.failures.json"
    assert report.exists()
    assert json.loads(report.read_text())[0]["section"] == 2
    # the partial run stays resumable
    assert (tmp_path / "book.parts").exists()


def test_resume_renders_only_the_missing_section(tmp_path):
    cfg = make_config(tmp_path)
    failing = FakeEngine(fail_on=CountingFailer(target=2), fail_times=1)
    AudiobookPipeline(cfg, engine=failing).run()
    first_duration = frames_of(tmp_path / "book.wav")[0]

    healthy = FakeEngine()
    result = AudiobookPipeline(cfg, engine=healthy).run()

    assert result.complete
    assert result.chunks_reused > 0
    assert len(healthy.calls) >= 1
    assert frames_of(tmp_path / "book.wav")[0] > first_duration
    assert not (tmp_path / "book.failures.json").exists()


def test_checkpoints_skip_work_on_a_second_run(tmp_path):
    cfg = make_config(tmp_path, keep_parts=True)
    AudiobookPipeline(cfg, engine=FakeEngine()).run()

    second = FakeEngine()
    result = AudiobookPipeline(cfg, engine=second).run()

    assert result.complete
    assert result.chunks_reused == result.chunks_total
    assert second.calls == []


def test_changed_parameters_invalidate_checkpoints(tmp_path):
    base = make_config(tmp_path, keep_parts=True)
    AudiobookPipeline(base, engine=FakeEngine()).run()

    changed = dataclasses.replace(base, exaggeration=0.9)
    result = AudiobookPipeline(changed, engine=FakeEngine()).run()

    assert result.chunks_synthesized == result.chunks_total


def test_no_resume_starts_from_scratch(tmp_path):
    first = make_config(tmp_path, keep_parts=True)
    AudiobookPipeline(first, engine=FakeEngine()).run()

    second = dataclasses.replace(first, resume=False)
    engine = FakeEngine()
    result = AudiobookPipeline(second, engine=engine).run()

    assert result.chunks_reused == 0
    assert len(engine.calls) == result.chunks_total


def test_strict_mode_aborts_without_output(tmp_path):
    cfg = make_config(tmp_path, strict=True)
    engine = FakeEngine(fail_on=lambda text: True, fail_times=-1)

    result = AudiobookPipeline(cfg, engine=engine).run()

    assert result.aborted
    assert result.output_path is None
    assert not (tmp_path / "book.wav").exists()


def test_retries_recover_a_transient_failure(tmp_path):
    cfg = make_config(tmp_path, retries=2)
    engine = FakeEngine(fail_on=CountingFailer(target=1), fail_times=1)

    result = AudiobookPipeline(cfg, engine=engine).run()

    assert result.complete
    assert result.chunks_failed == 0


def test_retries_are_exhausted_before_reporting(tmp_path):
    cfg = make_config(tmp_path, retries=2)
    engine = FakeEngine(fail_on=lambda text: "Delta" in text, fail_times=-1)

    result = AudiobookPipeline(cfg, engine=engine).run()

    assert result.chunks_failed == 1
    assert result.failures[0].section == 1
    # failing chunk attempted three times, and the run still covered every section
    assert len(engine.calls) == 6


def test_keep_parts_preserves_the_work_directory(tmp_path):
    cfg = make_config(tmp_path, keep_parts=True)

    result = AudiobookPipeline(cfg, engine=FakeEngine()).run()

    assert result.complete
    assert (tmp_path / "book.parts").exists()


def test_missing_document_raises(tmp_path):
    cfg = PipelineConfig(
        document_path=str(tmp_path / "nope.txt"),
        output_path=str(tmp_path / "book.wav"),
    )

    with pytest.raises(PipelineError, match="not found"):
        AudiobookPipeline(cfg, engine=FakeEngine()).plan()


def test_empty_document_raises(tmp_path):
    cfg = make_config(tmp_path, document_text="   \n\n\t ")

    with pytest.raises(PipelineError, match="no readable text"):
        AudiobookPipeline(cfg, engine=FakeEngine()).run()


def test_plan_reports_sections_and_chunk_counts(tmp_path):
    cfg = make_config(tmp_path)

    sections, counts = AudiobookPipeline(cfg).plan()

    assert len(sections) == 4
    assert counts[0] == 1  # heading
    assert sum(counts) == 4  # every body in this fixture fits in one chunk


def test_progress_is_monotonic_and_reaches_total(tmp_path):
    seen = []

    def progress(done, total, message):
        seen.append((done, total, message))

    AudiobookPipeline(make_config(tmp_path), engine=FakeEngine(), progress=progress).run()

    assert seen
    assert [entry[0] for entry in seen] == sorted(entry[0] for entry in seen)
    assert seen[-1][0] == seen[-1][1]


def test_engine_failure_during_prepare_is_not_swallowed(tmp_path):
    class Broken(FakeEngine):
        def prepare(self):
            raise RuntimeError("model failed to load")

    with pytest.raises(RuntimeError, match="model failed to load"):
        AudiobookPipeline(make_config(tmp_path), engine=Broken()).run()

def test_keyboard_interrupt_keeps_finished_sections(tmp_path):
    class Interrupting(FakeEngine):
        def generate(self, text, **kwargs):
            if len(self.calls) == 2:
                raise KeyboardInterrupt
            return super().generate(text, **kwargs)

    cfg = make_config(tmp_path)
    with pytest.raises(KeyboardInterrupt):
        AudiobookPipeline(cfg, engine=Interrupting()).run()

    # no half-written output, but the finished sections are on disk
    assert not (tmp_path / "book.wav").exists()
    manifest = json.loads((tmp_path / "book.parts" / "manifest.json").read_text())
    assert len(manifest["parts"]) == 2

    healthy = FakeEngine()
    result = AudiobookPipeline(cfg, engine=healthy).run()

    assert result.complete
    assert result.chunks_reused == 2
    assert not (tmp_path / "book.wav.tmp").exists()


# --- upstream features: paragraph pauses, speech rate, chapters, MP3 -------
PARAGRAPH_DOC = """Chapter 1: Pauses

First paragraph of the chapter.

Second paragraph follows.

Third paragraph closes it."""


def test_paragraph_pauses_add_silence_between_paragraphs(tmp_path):
    without = make_config(tmp_path, document_text=PARAGRAPH_DOC, paragraph_pause=0.0,
                          output_path=str(tmp_path / "none.wav"))
    with_pause = make_config(tmp_path, document_text=PARAGRAPH_DOC, paragraph_pause=0.5,
                             output_path=str(tmp_path / "pause.wav"))

    base = AudiobookPipeline(without, engine=FakeEngine()).run()
    paused = AudiobookPipeline(with_pause, engine=FakeEngine()).run()

    added = paused.duration_seconds - base.duration_seconds
    assert added == pytest.approx(2 * 0.5, abs=0.01)  # three paragraphs, two gaps


def test_paragraph_pause_does_not_change_the_chunk_count(tmp_path):
    plain = make_config(tmp_path, document_text=PARAGRAPH_DOC, paragraph_pause=0.0)
    paused = make_config(tmp_path, document_text=PARAGRAPH_DOC, paragraph_pause=2.0)

    assert AudiobookPipeline(plain).plan()[1] == AudiobookPipeline(paused).plan()[1]


def test_chunks_are_grouped_per_paragraph(tmp_path):
    cfg = make_config(tmp_path, document_text=PARAGRAPH_DOC)

    _, counts = AudiobookPipeline(cfg).plan()

    # 1 heading + 3 paragraph chunks
    assert counts == [1, 3]


def test_speech_rate_shortens_the_audio(tmp_path):
    # silence is not sped up, so measure with the pauses turned off
    normal = make_config(tmp_path, document_text=PARAGRAPH_DOC, paragraph_pause=0.0,
                         chapter_pause=0.0, output_path=str(tmp_path / "normal.wav"))
    fast = make_config(tmp_path, document_text=PARAGRAPH_DOC, paragraph_pause=0.0,
                       chapter_pause=0.0, speech_rate=2.0,
                       output_path=str(tmp_path / "fast.wav"))

    base = AudiobookPipeline(normal, engine=FakeEngine()).run()
    quicker = AudiobookPipeline(fast, engine=FakeEngine()).run()

    assert quicker.duration_seconds == pytest.approx(base.duration_seconds / 2, rel=0.05)


def test_speech_rate_is_part_of_the_checkpoint_signature(tmp_path):
    base = make_config(tmp_path, keep_parts=True)
    AudiobookPipeline(base, engine=FakeEngine()).run()

    changed = dataclasses.replace(base, speech_rate=1.5)
    result = AudiobookPipeline(changed, engine=FakeEngine()).run()

    assert result.chunks_synthesized == result.chunks_total


def test_split_chapters_writes_one_file_per_chapter(tmp_path):
    cfg = make_config(tmp_path, split_chapters=True)

    result = AudiobookPipeline(cfg, engine=FakeEngine()).run()

    assert result.complete
    assert [Path(path).name for path in result.output_paths] == ["chapter1.wav", "chapter2.wav"]
    for path in result.output_paths:
        assert Path(path).exists()
        assert Path(path).stat().st_size > 44
    assert not (tmp_path / "book.wav").exists()


def test_split_chapters_with_a_single_chapter_uses_the_output_name(tmp_path):
    single = "Chapter 1: Only\n\nOne body."
    cfg = make_config(tmp_path, document_text=single, split_chapters=True)

    result = AudiobookPipeline(cfg, engine=FakeEngine()).run()

    assert [Path(path).name for path in result.output_paths] == ["book.wav"]


def test_chapter_groups_merge_the_preface_into_chapter_one(tmp_path):
    document = "A short preface.\n\nChapter 1: One\n\nBody one.\n\nChapter 2: Two\n\nBody two."
    cfg = make_config(tmp_path, document_text=document, split_chapters=True, keep_parts=True)

    result = AudiobookPipeline(cfg, engine=FakeEngine()).run()
    sections, _ = AudiobookPipeline(cfg).plan()
    groups = AudiobookPipeline(cfg)._chapter_groups(sections)

    assert len(groups) == 2
    assert groups[0][0] == 0  # the preface body stays with chapter 1
    assert len(result.output_paths) == 2


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_mp3_output_replaces_the_wav(tmp_path):
    cfg = make_config(tmp_path, mp3=True)

    result = AudiobookPipeline(cfg, engine=FakeEngine()).run()

    assert result.complete
    assert result.output_path.endswith(".mp3")
    assert Path(result.output_path).stat().st_size > 0
    assert not (tmp_path / "book.wav").exists()


def test_mp3_is_part_of_the_output_mode_only_not_the_signature(tmp_path):
    base = make_config(tmp_path, keep_parts=True)
    AudiobookPipeline(base, engine=FakeEngine()).run()

    engine = FakeEngine()
    result = AudiobookPipeline(dataclasses.replace(base, mp3=False), engine=engine).run()

    assert engine.calls == []  # rendering was reused
    assert result.chunks_reused == result.chunks_total
