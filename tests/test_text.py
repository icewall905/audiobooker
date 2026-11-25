"""Tests for chapter detection and chunking (issue #4)."""

import pytest

from audiobooker.text import (
    MAX_HEADING_LENGTH,
    count_chapters,
    detect_sections,
    hard_split,
    input_problems,
    split_into_chunks,
    split_sentences,
    validate_inputs,
)

WORDS_699 = " ".join(["word"] * 140)  # 699 characters, no sentence punctuation


def test_chunks_never_exceed_max_length_without_punctuation():
    chunks = split_into_chunks(WORDS_699, max_length=300)

    assert len(chunks) > 1
    assert max(len(chunk) for chunk in chunks) <= 300
    # no text is lost or duplicated
    assert "".join(chunks).replace(" ", "") == WORDS_699.replace(" ", "")


def test_single_giant_word_is_split():
    text = "x" * 5000

    chunks = split_into_chunks(text, max_length=100)

    assert all(len(chunk) <= 100 for chunk in chunks)
    assert "".join(chunks) == text


def test_sentences_are_packed_without_breaking_them():
    text = ("Alpha beta gamma. " * 40).strip()

    chunks = split_into_chunks(text, max_length=60)

    assert all(len(chunk) <= 60 for chunk in chunks)
    assert sum(chunk.count(".") for chunk in chunks) == 40
    for chunk in chunks:
        assert chunk.endswith(".")


def test_hard_split_prefers_word_boundaries():
    parts = hard_split("alpha beta gamma delta", max_length=12)

    assert all(len(part) <= 12 for part in parts)
    assert parts[0] == "alpha beta"


def test_abbreviations_do_not_end_sentences():
    sentences = split_sentences("Dr. Smith paid 3.50 dollars for it. Then he left.")

    assert sentences == ["Dr. Smith paid 3.50 dollars for it.", "Then he left."]


def test_initials_do_not_end_sentences():
    sentences = split_sentences("J. R. R. Tolkien wrote it. He was prolific.")

    assert sentences == ["J. R. R. Tolkien wrote it.", "He was prolific."]


def test_max_length_is_validated():
    with pytest.raises(ValueError):
        split_into_chunks("hello", max_length=5)


def test_chapter_headings_are_detected():
    document = (
        "Chapter 1: The Beginning\n\nFirst body.\n\n"
        "# Chapter Two\n\nSecond body."
    )

    sections = detect_sections(document)

    titles = [section.text for section in sections if section.is_chapter_title]
    assert titles == ["Chapter 1: The Beginning", "Chapter Two"]
    assert count_chapters(sections) == 2


@pytest.mark.parametrize(
    "heading",
    ["Part 2", "CHAPTER IV", "Book one", "Ch. 3: The Return", "Prologue", "## The End"],
)
def test_common_heading_styles(heading):
    sections = detect_sections(f"{heading}\n\nBody text.")

    assert [section.text for section in sections if section.is_chapter_title]


def test_numbered_lists_are_not_chapters():
    document = (
        "Chapter 1: Start\n\nIntro.\n\n"
        "1. Buy milk\n2. Call Bob\n3. Sell shares\n\nMore prose."
    )

    sections = detect_sections(document)

    titles = [section.text for section in sections if section.is_chapter_title]
    assert titles == ["Chapter 1: Start"]
    body = " ".join(section.text for section in sections if not section.is_chapter_title)
    assert "1. Buy milk" in body and "3. Sell shares" in body


def test_prose_starting_with_a_keyword_is_not_a_heading():
    sections = detect_sections("Book two of the trilogy was long. It took weeks.")

    assert count_chapters(sections) == 0
    assert sections[0].text.startswith("Book two")


def test_long_line_is_not_a_heading():
    document = "Chapter 1 " + "and the sentence keeps going for a while " * 3

    assert len(document.strip()) > MAX_HEADING_LENGTH
    assert count_chapters(detect_sections(document)) == 0


def test_custom_chapter_pattern():
    document = "1. The Return\n\nBody one.\n\n2. The Road\n\nBody two."

    sections = detect_sections(document, chapter_pattern=r"^\d+\.\s+[A-Z]")

    titles = [section.text for section in sections if section.is_chapter_title]
    assert titles == ["1. The Return", "2. The Road"]


def test_sections_preserve_every_word_in_order():
    document = (
        "Preface text.\n\nChapter 1: One\n\nBody one.\n\n"
        "Chapter 2: Two\n\nBody two."
    )

    sections = detect_sections(document)
    joined = " ".join(section.text for section in sections).split()

    assert joined == document.split()


def test_empty_document_has_no_sections():
    assert detect_sections("   \n\n  ") == []


def test_validate_inputs_matches_legacy_behaviour(tmp_path):
    document = tmp_path / "book.txt"
    document.write_text("hello", encoding="utf-8")

    missing = tmp_path / "missing.txt"
    assert validate_inputs(str(document)) is True
    assert validate_inputs(str(missing)) is False
    assert input_problems(str(missing)) == [f"Document file '{missing}' not found."]


def test_validate_inputs_checks_voice_file(tmp_path):
    document = tmp_path / "book.txt"
    document.write_text("hello", encoding="utf-8")

    assert validate_inputs(str(document), str(tmp_path / "voice.wav")) is False
