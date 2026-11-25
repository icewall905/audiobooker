"""Command line interface: ``audiobook``."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional, Sequence

from . import __version__
from .config import cli_defaults
from .engine import ChatterboxEngine, EngineError
from .pipeline import AudiobookPipeline, PipelineConfig, PipelineError
from .report import ConsoleReporter
from .text import DEFAULT_MAX_CHUNK_LENGTH, MAX_CHUNK_LENGTH_LIMIT, MIN_CHUNK_LENGTH, Section

DEFAULT_DOCUMENT = "sample_document.txt"
DEFAULT_OUTPUT = "my_audiobook.wav"


def _unit_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a number")
    if not 0.0 <= number <= 1.0:
        raise argparse.ArgumentTypeError(f"must be between 0.0 and 1.0, got {number}")
    return number


def _non_negative_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a number")
    if number < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {number}")
    return number


def _non_negative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not an integer")
    if number < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {number}")
    return number


def _speech_rate(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a number")
    if not 0.25 <= number <= 4.0:
        raise argparse.ArgumentTypeError(f"must be between 0.25 and 4.0, got {number}")
    return number


def _chunk_length(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not an integer")
    if not MIN_CHUNK_LENGTH <= number <= MAX_CHUNK_LENGTH_LIMIT:
        raise argparse.ArgumentTypeError(
            f"must be between {MIN_CHUNK_LENGTH} and {MAX_CHUNK_LENGTH_LIMIT}, got {number}"
        )
    return number


def _wav_path(value: str) -> str:
    if os.path.splitext(value)[1].lower() not in (".wav", ""):
        raise argparse.ArgumentTypeError(
            "the streaming writer produces WAV output; use a .wav output path"
        )
    return value


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Arguments shared by the local and remote entry points."""
    parser.add_argument("--document", "-d", default=DEFAULT_DOCUMENT,
                        help="path to the text document")
    parser.add_argument("--voice", "-v", default=None,
                        help="path to a voice reference audio file (optional)")
    parser.add_argument("--no-voice", action="store_true",
                        help="ignore --voice/example.wav and use the default voice")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT, type=_wav_path,
                        help="path for the output audiobook (.wav)")
    parser.add_argument("--exaggeration", "-e", type=_unit_float, default=0.5,
                        help="emotion exaggeration, 0.0-1.0")
    parser.add_argument("--cfg-weight", "-c", type=_unit_float, default=0.5,
                        help="CFG weight, 0.0-1.0")
    parser.add_argument("--chapter-pause", type=_non_negative_float, default=1.0,
                        help="silence around chapter titles, in seconds")
    parser.add_argument("--paragraph-pause", type=_non_negative_float, default=1.0,
                        help="silence between paragraphs, in seconds (0 disables)")
    parser.add_argument("--speech-rate", type=_speech_rate, default=1.0,
                        help="speaking rate, 1.0 is unchanged (pitch is preserved "
                             "when torchaudio is installed)")
    parser.add_argument("--max-chunk-length", type=_chunk_length,
                        default=DEFAULT_MAX_CHUNK_LENGTH,
                        help="maximum characters sent to the model per call")
    parser.add_argument("--chapter-pattern", default=None,
                        help="regex for chapter headings (overrides the built-in rules)")
    parser.add_argument("--retries", type=_non_negative_int, default=2,
                        help="retries per chunk after the first failure")
    parser.add_argument("--retry-delay", type=_non_negative_float, default=1.0,
                        help="base delay between retries, in seconds")
    parser.add_argument("--strict", action="store_true",
                        help="abort on the first chunk that fails after retries")
    parser.add_argument("--no-resume", action="store_true",
                        help="ignore existing checkpoints and render from scratch")
    parser.add_argument("--keep-parts", action="store_true",
                        help="keep the per-section WAV parts after a successful run")
    parser.add_argument("--split-chapters", action="store_true",
                        help="write one file per chapter instead of a single audiobook")
    parser.add_argument("--no-split-chapters", dest="split_chapters", action="store_false",
                        help="write a single audiobook file (default)")
    parser.add_argument("--mp3", dest="mp3", action="store_true",
                        help="encode the result to MP3 with ffmpeg (removes the WAV)")
    parser.add_argument("--no-mp3", dest="mp3", action="store_false",
                        help="keep WAV output (default)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the detected structure and exit (no model load)")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="only print the final summary")
    parser.add_argument("--version", action="version", version=f"audiobook {__version__}")


def resolve_voice(args: argparse.Namespace) -> Optional[str]:
    """Apply --no-voice and the example.wav auto-detection."""
    if args.no_voice:
        return None
    if args.voice:
        return args.voice
    if os.path.exists("example.wav"):
        print("🎤 Automatically detected and using example.wav as voice reference")
        return "example.wav"
    return None


def print_plan(sections: Sequence[Section], counts: Sequence[int], max_rows: int = 200) -> None:
    total_chunks = sum(counts)
    total_chars = sum(len(section.text) for section in sections)
    print(f"{'#':>4}  {'kind':<8} {'chars':>7} {'chunks':>6}  preview")
    for index, (section, count) in enumerate(zip(sections, counts), 1):
        if index > max_rows:
            print(f"     ... {len(sections) - max_rows} more section(s)")
            break
        kind = "heading" if section.is_chapter_title else "body"
        preview = " ".join(section.text.split())[:60]
        print(f"{index:>4}  {kind:<8} {len(section.text):>7} {count:>6}  {preview}")
    print(f"\nTotal: {len(sections)} sections, {total_chunks} chunks, {total_chars:,} characters")


CONFIG_KEYS = {
    "document", "voice", "output", "device", "exaggeration", "cfg_weight",
    "chapter_pause", "paragraph_pause", "max_chunk_length", "speech_rate",
    "retries", "split_chapters", "mp3",
}


def apply_config_defaults(parser: argparse.ArgumentParser) -> None:
    """Let audiobooker.conf [defaults] provide defaults, flags still win."""
    values = {key: value for key, value in cli_defaults().items() if key in CONFIG_KEYS}
    if values:
        parser.set_defaults(**values)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="audiobook",
        description="Create an audiobook from a text document using Chatterbox TTS",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_common_arguments(parser)
    parser.add_argument("--device", default=None,
                        help="torch device, e.g. cuda or cpu (default: auto-detect)")
    parser.add_argument("-s", dest="speech_rate", type=_speech_rate,
                        default=argparse.SUPPRESS, help="alias for --speech-rate")
    apply_config_defaults(parser)
    args = parser.parse_args(argv)

    voice_path = resolve_voice(args)
    config = PipelineConfig(
        document_path=args.document,
        output_path=args.output,
        voice_prompt_path=voice_path,
        exaggeration=args.exaggeration,
        cfg_weight=args.cfg_weight,
        chapter_pause=args.chapter_pause,
        paragraph_pause=args.paragraph_pause,
        speech_rate=args.speech_rate,
        split_chapters=args.split_chapters,
        mp3=args.mp3,
        max_chunk_length=args.max_chunk_length,
        chapter_pattern=args.chapter_pattern,
        retries=args.retries,
        retry_delay=args.retry_delay,
        resume=not args.no_resume,
        keep_parts=args.keep_parts,
        strict=args.strict,
    )

    reporter = ConsoleReporter(quiet=args.quiet)
    reporter.header(
        f"Chatterbox Audiobook Creator v{__version__}",
        {
            "Document": args.document,
            "Voice reference": voice_path or "Default voice",
            "Output": args.output,
            "Exaggeration": args.exaggeration,
            "CFG weight": args.cfg_weight,
            "Chapter pause": f"{args.chapter_pause}s",
            "Paragraph pause": f"{args.paragraph_pause}s",
            "Speech rate": f"{args.speech_rate}x",
            "Output mode": (
                f"{'per chapter' if args.split_chapters else 'single file'}, "
                f"{'MP3' if args.mp3 else 'WAV'}"
            ),
            "Max chunk length": args.max_chunk_length,
        },
    )

    if args.dry_run:
        return run_dry(config)

    engine = ChatterboxEngine(device=args.device, voice_prompt_path=voice_path)
    return run_pipeline(config, engine, reporter)


def run_dry(config: PipelineConfig) -> int:
    """Print the detected structure without loading a model."""
    try:
        sections, counts = AudiobookPipeline(config).plan()
    except PipelineError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    if not sections:
        print("❌ No readable text found", file=sys.stderr)
        return 1
    print_plan(sections, counts)
    return 0


def run_pipeline(config: PipelineConfig, engine, reporter: ConsoleReporter) -> int:
    """Run a job with any engine and report the outcome. Returns an exit code."""
    pipeline = AudiobookPipeline(
        config, engine=engine, log=reporter.log, progress=reporter.progress
    )
    try:
        result = pipeline.run()
    except KeyboardInterrupt:
        print("\n⏹  Interrupted. Checkpoints are kept: re-run the same command to continue.")
        return 130
    except (PipelineError, EngineError) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # unexpected engine/library failure
        print(f"❌ Unexpected error: {exc}", file=sys.stderr)
        return 1

    reporter.result(result)
    return 0 if result.complete else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
