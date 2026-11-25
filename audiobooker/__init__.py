"""Audiobook generation on top of Resemble AI's Chatterbox TTS.

Layout (each module is importable on its own):

``text``      chapter detection, chunking, input validation (stdlib only)
``audio``     streaming WAV writer and part concatenation
``engine``    TTS backends: local Chatterbox, remote HTTP
``pipeline``  orchestration: checkpoints, retries, failure reporting
``cli``       ``audiobook`` entry point
``remote_cli````audiobook-remote`` entry point
``web``       ``audiobook-web`` (Gradio)
"""

from .text import (
    DEFAULT_MAX_CHUNK_LENGTH,
    Section,
    count_chapters,
    detect_sections,
    input_problems,
    read_document,
    split_into_chunks,
    validate_inputs,
)

__version__ = "0.2.0"
VERSION = __version__

__all__ = [
    "DEFAULT_MAX_CHUNK_LENGTH",
    "Section",
    "VERSION",
    "__version__",
    "count_chapters",
    "detect_sections",
    "input_problems",
    "read_document",
    "split_into_chunks",
    "validate_inputs",
]
