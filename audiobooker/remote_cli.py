"""Command line interface: ``audiobook-remote`` (Chatterbox over HTTP)."""

from __future__ import annotations

import argparse
from typing import Optional, Sequence

from . import __version__
from .cli import CONFIG_KEYS, add_common_arguments, resolve_voice, run_dry, run_pipeline
from .config import load_config, resolve_server_url
from .engine import DEFAULT_SAMPLE_RATE, RemoteEngine
from .pipeline import PipelineConfig
from .report import ConsoleReporter

#: Kept for backwards compatibility; the real default comes from
#: ``audiobooker.conf`` / ``CHATTERBOX_SERVER_URL`` (see audiobooker.config).
DEFAULT_SERVER = "http://127.0.0.1:7860"


def _config_values(config) -> list:
    from .config import cli_defaults

    return list(cli_defaults(config).items())


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="audiobook-remote",
        description="Create an audiobook using a remote Chatterbox TTS server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_common_arguments(parser)
    parser.add_argument("--server", "-s", default=None,
                        help="Chatterbox server URL (default: audiobooker.conf [server] url, "
                             "$CHATTERBOX_SERVER_URL, then 127.0.0.1:7860)")
    parser.add_argument("--temperature", type=float, default=0.8,
                        help="sampling temperature used by the server")
    parser.add_argument("--seed", type=int, default=0,
                        help="sampling seed passed to the server")
    parser.add_argument("--timeout", type=float, default=180.0,
                        help="per-request timeout, in seconds")
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE,
                        help="sample rate to assume if the server cannot be probed")
    parser.add_argument("--no-probe", action="store_true",
                        help="skip the probe synthesis used to detect the server sample rate")
    values = {}
    config = load_config()
    for key, value in _config_values(config):
        if key in CONFIG_KEYS:
            values[key] = value
    if values:
        parser.set_defaults(**values)
    args = parser.parse_args(argv)

    server_url = resolve_server_url(args.server, config)
    voice_path = resolve_voice(args)
    config = PipelineConfig(
        document_path=args.document,
        output_path=args.output,
        voice_prompt_path=voice_path,
        exaggeration=args.exaggeration,
        cfg_weight=args.cfg_weight,
        chapter_pause=args.chapter_pause,
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
        f"Remote Chatterbox Audiobook Creator v{__version__}",
        {
            "Server": server_url,
            "Document": args.document,
            "Voice reference": voice_path or "Default voice",
            "Output": args.output,
            "Exaggeration": args.exaggeration,
            "CFG weight": args.cfg_weight,
            "Chapter pause": f"{args.chapter_pause}s",
            "Max chunk length": args.max_chunk_length,
        },
    )

    if args.dry_run:
        return run_dry(config)

    engine = RemoteEngine(
        server_url=server_url,
        voice_prompt_path=voice_path,
        temperature=args.temperature,
        seed=args.seed,
        timeout=args.timeout,
        sample_rate=args.sample_rate,
        probe=not args.no_probe,
        log=reporter.log,
    )
    return run_pipeline(config, engine, reporter)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
