"""Tests for the web job runner (no Gradio required)."""

import os

from fake_engine import FakeEngine

import audiobooker.web as web


def test_generate_audiobook_from_pasted_text(tmp_path, monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(web, "get_engine", lambda device=None: engine)

    path, status = web.generate_audiobook(
        "Chapter 1: Hi\n\nSome body text.",
        None,
        None,
        exaggeration=0.6,
        cfg_weight=0.4,
        chapter_pause=0.5,
        max_chunk_length=200,
    )

    assert path and os.path.exists(path)
    assert "complete" in status.lower()
    assert "Chapter 1: Hi" not in status  # status is a summary, not the book
    assert engine.calls


def test_generate_audiobook_uses_uploaded_files(tmp_path, monkeypatch):
    document = tmp_path / "doc.txt"
    document.write_text("Chapter 1\n\nBody.", encoding="utf-8")
    engine = FakeEngine()
    monkeypatch.setattr(web, "get_engine", lambda device=None: engine)

    path, status = web.generate_audiobook("", str(document), None)

    assert path and "Uploaded file: doc.txt" in status
    assert engine.voice_prompt_path is None


def test_generate_audiobook_requires_input():
    path, status = web.generate_audiobook("", None, None)

    assert path is None
    assert "provide" in status.lower()


def test_generate_audiobook_reports_failed_chunks(monkeypatch):
    engine = FakeEngine(fail_on=lambda text: True, fail_times=-1)
    monkeypatch.setattr(web, "get_engine", lambda device=None: engine)

    path, status = web.generate_audiobook("Chapter 1\n\nBody text.")

    assert path is None  # nothing was rendered at all
    assert "no audio" in status.lower() or "error" in status.lower()


def test_generate_audiobook_surfaces_missing_text(monkeypatch):
    engine = FakeEngine(fail_on=lambda text: "Body" in text, fail_times=-1)
    monkeypatch.setattr(web, "get_engine", lambda device=None: engine)

    path, status = web.generate_audiobook("Chapter 1\n\nBody text.")

    assert path and os.path.exists(path)
    assert "missing" in status.lower()
