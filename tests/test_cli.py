"""Tests for the CLI surface and argument validation (issue #4)."""

import subprocess
import sys
from pathlib import Path

import pytest
from fake_engine import FakeEngine

from audiobooker.cli import main, run_pipeline
from audiobooker.pipeline import PipelineConfig
from audiobooker.report import ConsoleReporter

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "sample_document.txt"


def test_dry_run_accepts_max_chunk_length(capsys):
    code = main(["--dry-run", "--document", str(SAMPLE), "--max-chunk-length", "100"])

    assert code == 0
    output = capsys.readouterr().out
    assert "Total:" in output
    assert "chunks" in output


def test_production_validator_contract_is_supported(capsys):
    """validate_production.py calls: app.py ... --max-chunk-length 100"""
    code = main(
        [
            "--dry-run",
            "--document",
            str(SAMPLE),
            "--output",
            "/tmp/validator-output.wav",
            "--max-chunk-length",
            "100",
        ]
    )

    assert code == 0


@pytest.mark.parametrize(
    "argv",
    [
        ["--exaggeration", "3"],
        ["--exaggeration", "-0.2"],
        ["--cfg-weight", "1.5"],
        ["--chapter-pause", "-1"],
        ["--max-chunk-length", "5"],
        ["--max-chunk-length", "9000"],
        ["--output", "book.mp3"],
        ["--retries", "-1"],
    ],
)
def test_invalid_values_are_rejected(argv):
    with pytest.raises(SystemExit) as excinfo:
        main(["--dry-run", "--document", str(SAMPLE)] + argv)

    assert excinfo.value.code == 2


def test_version_flag():
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])

    assert excinfo.value.code == 0


def test_missing_document_exits_non_zero(tmp_path, capsys):
    code = main(["--dry-run", "--document", str(tmp_path / "missing.txt")])

    assert code == 1
    assert "not found" in capsys.readouterr().err


def test_run_pipeline_with_engine_writes_file(tmp_path, capsys):
    config = PipelineConfig(
        document_text="Chapter 1: Hello\n\nSome body text.",
        output_path=str(tmp_path / "out.wav"),
        retries=0,
    )

    code = run_pipeline(config, FakeEngine(), ConsoleReporter(quiet=True))

    assert code == 0
    assert (tmp_path / "out.wav").exists()


def test_run_pipeline_returns_non_zero_for_partial_output(tmp_path, capsys):
    config = PipelineConfig(
        document_text="Chapter 1: Hello\n\nSome body text.",
        output_path=str(tmp_path / "out.wav"),
        retries=0,
    )
    failing = FakeEngine(fail_on=lambda text: "body" in text, fail_times=-1
    )

    code = run_pipeline(config, failing, ConsoleReporter(quiet=True))

    assert code == 1
    assert (tmp_path / "out.wav").exists()
    output = capsys.readouterr().out
    assert "missing" in output.lower()


def test_wrapper_script_runs_the_package_cli():
    process = subprocess.run(
        [sys.executable, "app.py", "--dry-run", "--max-chunk-length", "100"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert process.returncode == 0, process.stderr
    assert "Total:" in process.stdout


def test_remote_wrapper_exposes_legacy_client():
    import app_remote

    assert callable(app_remote.ChatterboxAPIClient)
    assert app_remote.smart_text_split("one. two.", 100) == ["one. two."]


# --- upstream feature flags ------------------------------------------------
def test_new_feature_flags_are_accepted(capsys):
    code = main(
        [
            "--dry-run",
            "--document",
            str(SAMPLE),
            "--paragraph-pause",
            "0",
            "--speech-rate",
            "1.5",
            "--split-chapters",
            "--mp3",
        ]
    )

    assert code == 0
    output = capsys.readouterr().out
    assert "Paragraph pause: 0.0s" in output
    assert "Speech rate: 1.5x" in output
    assert "per chapter" in output and "MP3" in output


def test_upstream_compatibility_flags_still_work():
    assert main(["--dry-run", "--document", str(SAMPLE), "--no-split-chapters", "--no-mp3"]) == 0


@pytest.mark.parametrize(
    "argv",
    [["--speech-rate", "0"], ["--speech-rate", "9"], ["--paragraph-pause", "-1"]],
)
def test_invalid_speech_settings_are_rejected(argv):
    with pytest.raises(SystemExit) as excinfo:
        main(["--dry-run", "--document", str(SAMPLE)] + argv)

    assert excinfo.value.code == 2


def test_config_file_defaults_are_applied(tmp_path, monkeypatch, capsys):
    (tmp_path / "audiobooker.conf").write_text(
        "[defaults]\nmax_chunk_length = 120\nparagraph_pause = 0\nspeech_rate = 1.25\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    code = main(["--dry-run", "--document", str(SAMPLE)])

    assert code == 0
    output = capsys.readouterr().out
    assert "Max chunk length: 120" in output
    assert "Paragraph pause: 0.0s" in output
    assert "Speech rate: 1.25x" in output


def test_command_line_beats_the_config_file(tmp_path, monkeypatch, capsys):
    (tmp_path / "audiobooker.conf").write_text(
        "[defaults]\nmax_chunk_length = 120\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    code = main(["--dry-run", "--document", str(SAMPLE), "--max-chunk-length", "150"])

    assert code == 0
    assert "Max chunk length: 150" in capsys.readouterr().out


def test_remote_cli_uses_the_configured_server(tmp_path, monkeypatch, capsys):
    from audiobooker.remote_cli import main as remote_main

    (tmp_path / "audiobooker.conf").write_text(
        "[server]\nurl = http://gpu-box:9999\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CHATTERBOX_SERVER_URL", raising=False)

    code = remote_main(["--dry-run", "--document", str(SAMPLE)])

    assert code == 0
    assert "http://gpu-box:9999" in capsys.readouterr().out
