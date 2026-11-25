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

__all__ = [
    "VERSION",
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


if __name__ == "__main__":
    raise SystemExit(main())
