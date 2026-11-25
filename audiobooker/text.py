"""Text handling: chapter detection and TTS-safe chunking.

This module deliberately imports nothing heavier than the standard library so
that the parsing rules can be unit-tested without torch, numpy or a GPU.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import List, Optional, Sequence

DEFAULT_MAX_CHUNK_LENGTH = 300
MIN_CHUNK_LENGTH = 20
MAX_CHUNK_LENGTH_LIMIT = 4000

#: A heading has to fit on one short line; longer lines are prose.
MAX_HEADING_LENGTH = 80

_NUMBER_WORDS = (
    "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|"
    "fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty"
)

# "Chapter 12", "CHAPTER IV", "Part two", "Ch. 3: The Return", "Book 1"
_KEYWORD_HEADING = re.compile(
    r"^(?:chapter|chap\.?|ch\.?|part|section|book|volume|vol\.?)\s*#?\s*"
    rf"(?:\d{{1,4}}|[ivxlcdm]{{1,7}}|(?:{_NUMBER_WORDS}))\b",
    re.IGNORECASE,
)

# "Prologue", "Introduction", "Preface to the Second Edition"
_BARE_HEADING = re.compile(
    r"^(?:prologue|epilogue|introduction|preface|foreword|afterword|interlude|appendix)\b",
    re.IGNORECASE,
)

# "# Chapter One", "## The Return"
_MARKDOWN_PREFIX = re.compile(r"^#{1,4}\s+")
_MARKDOWN_HEADING = re.compile(r"^#{1,4}\s+\S")

_SENTENCE_BOUNDARY = re.compile(r'(?<=[.!?])["\'”’»)\]]*\s+')

_BREAK_CHARS = " \t\u00a0,;:\u2013\u2014-"

_ABBREVIATIONS = {
    "mr.", "mrs.", "ms.", "dr.", "prof.", "sr.", "jr.", "st.", "vs.", "etc.",
    "e.g.", "i.e.", "cf.", "al.", "no.", "nos.", "fig.", "figs.", "vol.",
    "vols.", "ch.", "chap.", "p.", "pp.", "ed.", "eds.", "approx.", "dept.",
    "inc.", "ltd.", "co.", "corp.", "gen.", "col.", "capt.", "lt.", "sgt.",
    "rev.", "hon.", "pres.", "gov.", "sen.", "rep.", "jan.", "feb.", "mar.",
    "apr.", "jun.", "jul.", "aug.", "sep.", "sept.", "oct.", "nov.", "dec.",
}


@dataclass(frozen=True)
class Section:
    """One unit of the document: either a chapter heading or body text."""

    text: str
    is_chapter_title: bool = False


def count_chapters(sections: Sequence[Section]) -> int:
    """Number of detected chapter heading sections."""
    return sum(1 for section in sections if section.is_chapter_title)


def _clean_heading(line: str) -> str:
    """Normalise a heading line into the text that will be spoken."""
    title = _MARKDOWN_PREFIX.sub("", line.strip())
    title = title.strip().strip(":=-\u2013\u2014 \t")
    return title.strip()


def _looks_like_heading(line: str, custom_pattern: Optional[re.Pattern]) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > MAX_HEADING_LENGTH:
        return False
    if custom_pattern is not None:
        return bool(custom_pattern.match(stripped))
    # Headings do not end the way sentences do, and they are not clauses.
    if stripped[-1] in ".,;":
        return False
    if _MARKDOWN_HEADING.match(stripped):
        return True
    if _KEYWORD_HEADING.match(stripped):
        # Guard against prose that merely starts with the keyword, e.g.
        # "Chapter one was the hardest part of the whole book for her".
        return len(stripped.split()) <= 12
    if _BARE_HEADING.match(stripped):
        return len(stripped.split()) <= 5
    return False


def detect_sections(text: str, chapter_pattern: Optional[str] = None) -> List[Section]:
    """Split ``text`` into heading and body :class:`Section` objects.

    ''   -> no sections.
    Text is never dropped or duplicated: every non-heading line ends up in
    exactly one body section, in document order.

    ``chapter_pattern`` overrides the built-in heuristics with a regex matched
    against each stripped line (e.g. ``r'^\\d+\\.\\s+[A-Z]'`` for books that use
    "1. The Return" headings).
    """
    custom = re.compile(chapter_pattern, re.IGNORECASE) if chapter_pattern else None

    lines = text.splitlines()
    heading_indexes = [i for i, line in enumerate(lines) if _looks_like_heading(line, custom)]

    if not heading_indexes:
        body = text.strip()
        return [Section(body)] if body else []

    sections: List[Section] = []
    cursor = 0
    for position, line_index in enumerate(heading_indexes):
        body = "\n".join(lines[cursor:line_index]).strip()
        if body and _has_words(body):
            sections.append(Section(body, False))

        title = _clean_heading(lines[line_index])
        if title and _has_words(title):
            sections.append(Section(title, True))

        cursor = line_index + 1
        is_last = position == len(heading_indexes) - 1
        if is_last:
            tail = "\n".join(lines[cursor:]).strip()
            if tail and _has_words(tail):
                sections.append(Section(tail, False))

    return sections


def _has_words(text: str) -> bool:
    return bool(re.search(r"[^\W_]", text, re.UNICODE))


def _is_false_boundary(prefix: str) -> bool:
    """True when the token ending at this match is not a sentence end."""
    token = prefix.rstrip().split()[-1] if prefix.strip() else ""
    if not token:
        return True
    lowered = token.lower()
    if lowered in _ABBREVIATIONS:
        return True
    # Initials ("J. R. R. Tolkien") and enumerated fragments ("No 4.").
    if re.fullmatch(r"(?:[A-Z]|[0-9]{1,3})\.", token):
        return True
    return False


def split_sentences(paragraph: str) -> List[str]:
    """Split a paragraph on sentence boundaries, ignoring abbreviations."""
    sentences: List[str] = []
    start = 0
    for match in _SENTENCE_BOUNDARY.finditer(paragraph):
        end = match.start()
        if end <= start:
            continue
        if _is_false_boundary(paragraph[start:end]):
            continue
        candidate = paragraph[start:end].strip()
        if candidate:
            sentences.append(candidate)
        start = match.end()
    tail = paragraph[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def hard_split(text: str, max_length: int) -> List[str]:
    """Break text that has no usable punctuation so no part exceeds max_length."""
    parts: List[str] = []
    rest = text.strip()
    while len(rest) > max_length:
        window = rest[:max_length]
        cut = max(window.rfind(char) for char in _BREAK_CHARS)
        if cut < max_length // 3:
            cut = max_length
        piece = rest[:cut].strip()
        if piece:
            parts.append(piece)
        rest = rest[cut:].strip()
    if rest:
        parts.append(rest)
    return parts


def split_paragraphs(text: str) -> List[str]:
    """Normalised, non-empty paragraphs (blank-line separated)."""
    paragraphs: List[str] = []
    for block in re.split(r"\n\s*\n", text):
        normalised = re.sub(r"\s+", " ", block).strip()
        if normalised and _has_words(normalised):
            paragraphs.append(normalised)
    return paragraphs


def split_into_chunks(text: str, max_length: int = DEFAULT_MAX_CHUNK_LENGTH) -> List[str]:
    """Split text into chunks that never exceed ``max_length`` characters.

    Paragraphs are kept when they fit, otherwise they are packed by sentence,
    and any sentence that is still too long is hard-split at a space or comma.
    The invariant ``len(chunk) <= max_length`` always holds, which keeps the TTS
    prompt inside the range Chatterbox is stable at.
    """
    if max_length < MIN_CHUNK_LENGTH:
        raise ValueError(f"max_length must be >= {MIN_CHUNK_LENGTH}, got {max_length}")

    chunks: List[str] = []
    for normalised in split_paragraphs(text):
        if len(normalised) <= max_length:
            chunks.append(normalised)
            continue

        current = ""
        for sentence in split_sentences(normalised) or [normalised]:
            if len(sentence) > max_length:
                if current:
                    chunks.append(current.strip())
                    current = ""
                chunks.extend(hard_split(sentence, max_length))
                continue
            if current and len(current) + 1 + len(sentence) > max_length:
                chunks.append(current.strip())
                current = sentence
            else:
                current = f"{current} {sentence}" if current else sentence
        if current.strip():
            chunks.append(current.strip())

    return [chunk for chunk in chunks if chunk]


def input_problems(
    document_path: str,
    voice_prompt_path: Optional[str] = None,
    text: Optional[str] = None,
) -> List[str]:
    """Return a list of human readable problems with the requested inputs."""
    problems: List[str] = []
    if text is None:
        if not os.path.exists(document_path):
            problems.append(f"Document file '{document_path}' not found.")
        elif not os.path.isfile(document_path):
            problems.append(f"Document path '{document_path}' is not a file.")
    if voice_prompt_path and not os.path.exists(voice_prompt_path):
        problems.append(f"Voice reference file '{voice_prompt_path}' not found.")
    return problems


def validate_inputs(document_path: str, voice_prompt_path: Optional[str] = None) -> bool:
    """Backwards compatible boolean input check."""
    return not input_problems(document_path, voice_prompt_path)


def read_document(path: str) -> str:
    """Read a UTF-8 text file, tolerating stray undecodable bytes."""
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()
