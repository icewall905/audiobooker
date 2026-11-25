#!/usr/bin/env python3
"""Backwards compatible entry point: ``python app_remote.py`` == ``audiobook-remote``.

Keeps :class:`ChatterboxAPIClient` and the text helpers importable for scripts
written against the 0.0.x layout; the real work happens in
:mod:`audiobooker.engine` and :mod:`audiobooker.pipeline`.
"""

from __future__ import annotations

import io
import wave
from typing import List, Optional

from audiobooker import VERSION
from audiobooker.audio import to_pcm16
from audiobooker.engine import DEFAULT_SAMPLE_RATE, RemoteEngine
from audiobooker.remote_cli import DEFAULT_SERVER, main
from audiobooker.text import (
    DEFAULT_MAX_CHUNK_LENGTH,
    split_into_chunks,
    validate_inputs,
)

CHATTERBOX_SERVER_URL = DEFAULT_SERVER
MAX_CHUNK_LENGTH = DEFAULT_MAX_CHUNK_LENGTH

__all__ = [
    "VERSION",
    "CHATTERBOX_SERVER_URL",
    "ChatterboxAPIClient",
    "smart_text_split",
    "validate_inputs",
    "main",
]


def _encode_wav(samples, sample_rate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(int(sample_rate))
        handle.writeframes(to_pcm16(samples))
    return buffer.getvalue()


class ChatterboxAPIClient:
    """Deprecated wrapper around :class:`audiobooker.engine.RemoteEngine`."""

    def __init__(
        self,
        server_url: str = DEFAULT_SERVER,
        voice_prompt_path: Optional[str] = None,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
    ):
        self.server_url = server_url
        self.voice_prompt_path = voice_prompt_path
        self._engine = RemoteEngine(
            server_url=server_url,
            voice_prompt_path=voice_prompt_path,
            sample_rate=sample_rate,
            probe=False,
        )

    def check_server_health(self) -> bool:
        return self._engine.check_health()

    def generate_audio_gradio(
        self,
        text: str,
        voice_prompt_path: Optional[str] = None,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
    ) -> bytes:
        self._engine.voice_prompt_path = voice_prompt_path or self.voice_prompt_path
        samples = self._engine.generate(
            text, exaggeration=exaggeration, cfg_weight=cfg_weight
        )
        return _encode_wav(samples, self._engine.sample_rate)

    def generate_audio(
        self,
        text: str,
        voice_prompt_path: Optional[str] = None,
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
    ) -> bytes:
        return self.generate_audio_gradio(
            text, voice_prompt_path, exaggeration, cfg_weight
        )


def smart_text_split(text: str, max_length: int = MAX_CHUNK_LENGTH) -> List[str]:
    return split_into_chunks(text, max_length)


if __name__ == "__main__":
    raise SystemExit(main())
