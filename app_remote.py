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
    "create_audiobook",
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


def create_audiobook(
    document_path: str = "sample_document.txt",
    voice_prompt_path: Optional[str] = None,
    output_path: str = "my_audiobook.wav",
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
    server_url: Optional[str] = None,
    chapter_pause: float = 1.0,
    paragraph_pause: float = 1.0,
    speech_rate: float = 1.0,
    max_chunk_length: int = MAX_CHUNK_LENGTH,
) -> bool:
    """Legacy 0.0.x entry point, backed by the streaming pipeline."""
    from audiobooker.config import resolve_server_url
    from audiobooker.engine import RemoteEngine
    from audiobooker.pipeline import AudiobookPipeline, PipelineConfig, PipelineError

    url = resolve_server_url(server_url)
    config = PipelineConfig(
        document_path=document_path,
        output_path=output_path,
        voice_prompt_path=voice_prompt_path,
        exaggeration=exaggeration,
        cfg_weight=cfg_weight,
        chapter_pause=chapter_pause,
        paragraph_pause=paragraph_pause,
        speech_rate=speech_rate,
        max_chunk_length=max_chunk_length,
    )
    engine = RemoteEngine(server_url=url, voice_prompt_path=voice_prompt_path)
    try:
        result = AudiobookPipeline(config, engine=engine, log=print).run()
    except PipelineError as exc:
        print(f"Error: {exc}")
        return False
    for line in result.summary_lines():
        print(line)
    return result.complete


if __name__ == "__main__":
    raise SystemExit(main())
