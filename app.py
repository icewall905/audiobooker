#!/usr/bin/env python3
"""Backwards compatible entry point: ``python app.py`` == ``audiobook``.

The implementation lives in the :mod:`audiobooker` package.  The helpers below
are re-exported so scripts written against the 0.0.x single-file layout keep
working.
"""

from __future__ import annotations

from typing import List, Optional

from audiobooker import VERSION
from audiobooker.cli import main
from audiobooker.text import (
    DEFAULT_MAX_CHUNK_LENGTH,
    detect_sections,
    split_into_chunks,
    validate_inputs,
)

DEFAULT_DOCUMENT = "sample_document.txt"
DEFAULT_OUTPUT = "my_audiobook.wav"

__all__ = [
    "VERSION",
    "create_audiobook",
    "detect_chapters",
    "smart_text_split",
    "validate_inputs",
    "main",
]


def detect_chapters(text: str, chapter_pattern: Optional[str] = None) -> List[dict]:
    """Legacy wrapper: sections as ``{"text", "is_chapter_title"}`` dicts."""
    return [
        {"text": section.text, "is_chapter_title": section.is_chapter_title}
        for section in detect_sections(text, chapter_pattern)
    ]


def smart_text_split(text: str, max_length: int = DEFAULT_MAX_CHUNK_LENGTH) -> List[str]:
    """Legacy alias for :func:`audiobooker.text.split_into_chunks`."""
    return split_into_chunks(text, max_length)


def create_audiobook(
    document_path: str = DEFAULT_DOCUMENT,
    voice_prompt_path: Optional[str] = None,
    output_path: str = DEFAULT_OUTPUT,
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
    device: Optional[str] = None,
    chapter_pause: float = 1.0,
    split_chapters: bool = True,
    convert_mp3: bool = True,
    speech_rate: float = 1.0,
    paragraph_pause: float = 1.0,
    max_chunk_length: int = DEFAULT_MAX_CHUNK_LENGTH,
) -> bool:
    """Legacy 0.0.x entry point, backed by the streaming pipeline.

    ``split_chapters``/``convert_mp3`` keep their historical ``True`` defaults;
    the ``audiobook`` CLI writes a single WAV unless you pass ``--split-chapters``
    or ``--mp3``.
    """
    from audiobooker.engine import ChatterboxEngine
    from audiobooker.pipeline import AudiobookPipeline, PipelineConfig, PipelineError

    config = PipelineConfig(
        document_path=document_path,
        output_path=output_path,
        voice_prompt_path=voice_prompt_path,
        exaggeration=exaggeration,
        cfg_weight=cfg_weight,
        chapter_pause=chapter_pause,
        paragraph_pause=paragraph_pause,
        speech_rate=speech_rate,
        max_chunk_length=max_chunk_length,
        split_chapters=split_chapters,
        mp3=convert_mp3,
    )
    engine = ChatterboxEngine(device=device, voice_prompt_path=voice_prompt_path)
    try:
        result = AudiobookPipeline(config, engine=engine, log=print).run()
    except PipelineError as exc:
        print(f"Error: {exc}")
        return False
    for line in result.summary_lines():
        print(line)
    return result.complete


if __name__ == "__main__":
    raise SystemExit(main())
