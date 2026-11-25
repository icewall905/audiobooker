"""Configuration file and environment support.

Resolution order for every setting is: command line flag > environment
variable > ``audiobooker.conf`` > built-in default.

``audiobooker.conf`` is looked up in this order:

1. ``$AUDIOBOOKER_CONF``
2. ``./audiobooker.conf``
3. ``~/.config/audiobooker/audiobooker.conf``
4. ``/etc/audiobooker/audiobooker.conf``

``[server]``

================  ==========================================================
``url``           Chatterbox server used by ``audiobook-remote``.
                  ``CHATTERBOX_SERVER_URL`` overrides it.
================  ==========================================================

``[defaults]`` accepts any of ``document``, ``voice``, ``output``, ``device``,
``exaggeration``, ``cfg_weight``, ``chapter_pause``, ``paragraph_pause``,
``max_chunk_length``, ``speech_rate``, ``retries``, ``split_chapters``,
``mp3``.  They are only defaults: an explicit flag always wins.
"""

from __future__ import annotations

import configparser
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_SERVER_URL = "http://127.0.0.1:7860"
ENV_CONF = "AUDIOBOOKER_CONF"
ENV_SERVER = "CHATTERBOX_SERVER_URL"

_FLOAT_KEYS = {
    "exaggeration",
    "cfg_weight",
    "chapter_pause",
    "paragraph_pause",
    "speech_rate",
}
_INT_KEYS = {"max_chunk_length", "retries"}
_BOOL_KEYS = {"split_chapters", "mp3"}
_STR_KEYS = {"document", "voice", "output", "device"}


def config_paths(cwd: Optional[Path] = None) -> List[Path]:
    """Candidate configuration files, highest priority first."""
    cwd = Path(cwd) if cwd is not None else Path.cwd()
    candidates: List[Path] = []
    override = os.environ.get(ENV_CONF)
    if override:
        candidates.append(Path(override).expanduser())
    candidates.extend(
        [
            cwd / "audiobooker.conf",
            Path.home() / ".config" / "audiobooker" / "audiobooker.conf",
            Path("/etc/audiobooker/audiobooker.conf"),
        ]
    )
    return candidates


def load_config(paths: Optional[Iterable[Path]] = None) -> configparser.ConfigParser:
    """Read the first readable configuration file; ignore malformed ones."""
    parser = configparser.ConfigParser()
    candidates = list(paths) if paths is not None else config_paths()
    for candidate in candidates:
        try:
            if candidate.is_file():
                parser.read(candidate, encoding="utf-8")
                break
        except (OSError, configparser.Error):
            # A broken config must never stop the CLI: fall through to defaults.
            continue
    return parser


def resolve_server_url(
    cli_value: Optional[str] = None, config: Optional[configparser.ConfigParser] = None
) -> str:
    """CLI > ``CHATTERBOX_SERVER_URL`` > ``[server] url`` > localhost default."""
    if cli_value:
        return cli_value
    env_value = os.environ.get(ENV_SERVER)
    if env_value:
        return env_value
    parser = config if config is not None else load_config()
    try:
        url = parser.get("server", "url", fallback="").strip()
    except configparser.Error:
        url = ""
    return url or DEFAULT_SERVER_URL


def _as_bool(value: str) -> Optional[bool]:
    lowered = value.strip().lower()
    if lowered in ("1", "true", "yes", "on"):
        return True
    if lowered in ("0", "false", "no", "off"):
        return False
    return None


def cli_defaults(
    config: Optional[configparser.ConfigParser] = None,
) -> Dict[str, Any]:
    """Values from the ``[defaults]`` section, as argparse defaults."""
    parser = config if config is not None else load_config()
    if not parser.has_section("defaults"):
        return {}

    values: Dict[str, Any] = {}
    for key, raw in parser.items("defaults"):
        key = key.strip().lower()
        text = (raw or "").strip()
        if not text:
            continue
        try:
            if key in _FLOAT_KEYS:
                values[key] = float(text)
            elif key in _INT_KEYS:
                values[key] = int(text)
            elif key in _BOOL_KEYS:
                parsed = _as_bool(text)
                if parsed is not None:
                    values[key] = parsed
            elif key in _STR_KEYS:
                values[key] = text
        except ValueError:
            continue
    return values
