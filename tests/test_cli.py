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
