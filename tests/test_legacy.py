"""Tests that the 0.0.x entry points still import and behave."""

import app
import app_remote
import web_interface


def test_app_reexports_legacy_helpers():
    assert app.VERSION
    sections = app.detect_chapters("Chapter 1\n\nBody.")
    assert sections[0]["is_chapter_title"] is True
    assert sections[0]["text"] == "Chapter 1"
    assert app.smart_text_split("one. two.", 100) == ["one. two."]
    assert app.validate_inputs(__file__) is True


def test_app_remote_reexports_legacy_client(tmp_path):
    document = tmp_path / "doc.txt"
    document.write_text("hello", encoding="utf-8")

    assert app_remote.validate_inputs(str(document)) is True
    assert app_remote.smart_text_split("a b c", 100) == ["a b c"]  # noqa: E501
    client = app_remote.ChatterboxAPIClient("http://example.invalid:7860")
    assert hasattr(client, "generate_audio")


def test_web_interface_reexports_runner():
    assert web_interface.VERSION
    assert callable(web_interface.generate_audiobook)
    assert callable(web_interface.build_interface)
