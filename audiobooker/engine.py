"""TTS backends.

Importing this module stays cheap: torch, chatterbox and requests are imported
inside the engines, so the pipeline can be driven by a fake engine (tests, CI)
on a machine without any ML dependencies.
"""

from __future__ import annotations

import base64
import io
import json
import time
import wave
from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

from .audio import flatten_mono

DEFAULT_SAMPLE_RATE = 24000


class EngineError(RuntimeError):
    """Raised when an engine cannot produce audio."""


class Engine(ABC):
    """Minimal interface the pipeline needs from a TTS backend."""

    name: str = "engine"
    sample_rate: int = DEFAULT_SAMPLE_RATE

    def prepare(self) -> None:
        """Load models / handshake. Must set :attr:`sample_rate`."""

    @abstractmethod
    def generate(self, text: str, *, exaggeration: float, cfg_weight: float) -> np.ndarray:
        """Return mono float32 samples in [-1, 1] for ``text``."""

    def close(self) -> None:  # pragma: no cover - backends hold no handles
        pass


def default_device() -> str:
    try:
        import torch
    except ImportError:  # pragma: no cover - exercised only without torch
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"


class ChatterboxEngine(Engine):
    """Local Chatterbox TTS model."""

    name = "chatterbox-local"

    def __init__(self, device: Optional[str] = None, voice_prompt_path: Optional[str] = None):
        self.device = device or default_device()
        self.voice_prompt_path = voice_prompt_path
        self.sample_rate = 0
        self._model = None

    def prepare(self) -> None:
        if self._model is not None:
            return
        try:
            from chatterbox.tts import ChatterboxTTS
        except ImportError as exc:  # pragma: no cover - depends on install
            raise EngineError(
                "chatterbox-tts is not installed. Install the local extras with "
                "`pip install -e '.[local]'` (or `pip install chatterbox-tts`)."
            ) from exc
        self._model = ChatterboxTTS.from_pretrained(device=self.device)
        self.sample_rate = int(getattr(self._model, "sr", DEFAULT_SAMPLE_RATE))

    def generate(self, text: str, *, exaggeration: float, cfg_weight: float) -> np.ndarray:
        if self._model is None:
            self.prepare()
        kwargs = {
            "exaggeration": float(exaggeration),
            "cfg_weight": float(cfg_weight),
        }
        # Only pass the prompt when we have one; keeps the default voice path.
        if self.voice_prompt_path:
            kwargs["audio_prompt_path"] = self.voice_prompt_path

        wav = self._model.generate(text, **kwargs)
        if hasattr(wav, "detach"):  # torch tensor
            wav = wav.detach().cpu().numpy()
        audio = flatten_mono(np.asarray(wav, dtype=np.float32))
        if audio.size == 0:
            raise EngineError("chatterbox returned no audio samples")
        return audio


def _decode_wav(data: bytes) -> tuple[np.ndarray, int]:
    """Decode WAV bytes to (mono float32 samples, sample rate)."""
    with wave.open(io.BytesIO(data), "rb") as handle:
        sample_rate = handle.getframerate()
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        frames = handle.readframes(handle.getnframes())

    if width == 1:
        samples = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif width == 2:
        samples = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 3:
        raw = np.frombuffer(frames, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        values = raw[:, 0] | (raw[:, 1] << 8) | (raw[:, 2] << 16)
        values = np.where(values >= 1 << 23, values - (1 << 24), values)
        samples = values.astype(np.float32) / float(1 << 23)
    elif width == 4:
        as_float = np.frombuffer(frames, dtype="<f4")
        if as_float.size and float(np.abs(as_float).max()) <= 1.5:
            samples = as_float.astype(np.float32)
        else:
            samples = np.frombuffer(frames, dtype="<i4").astype(np.float32) / 2147483648.0
    else:  # pragma: no cover - unknown width
        raise EngineError(f"unsupported WAV sample width: {width * 8} bit")

    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return flatten_mono(samples), sample_rate


class RemoteEngine(Engine):
    """Chatterbox served over Gradio's HTTP API.

    Results are read from the server's ``text/event-stream`` response (the way
    Gradio actually delivers them); JSON polling remains as a fallback for older
    or proxied servers.  Audio may come back as a file reference, a URL, raw WAV
    bytes or a ``data:audio/...;base64,`` URI.
    """

    name = "chatterbox-remote"

    def __init__(
        self,
        server_url: str,
        voice_prompt_path: Optional[str] = None,
        temperature: float = 0.8,
        seed: int = 0,
        timeout: float = 180.0,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        probe: bool = True,
        log=None,
    ):
        self.server_url = server_url.rstrip("/")
        self.voice_prompt_path = voice_prompt_path
        self.temperature = float(temperature)
        self.seed = int(seed)
        self.timeout = float(timeout)
        self.sample_rate = int(sample_rate)
        self.probe = probe
        self._log = log or (lambda message: None)

    # -- HTTP helpers ------------------------------------------------------
    def _session(self):
        try:
            import requests
        except ImportError as exc:  # pragma: no cover - depends on install
            raise EngineError(
                "requests is not installed. Install the remote extras with "
                "`pip install -e '.[remote]'`."
            ) from exc
        session = requests.Session()
        session.headers.update({"User-Agent": "audiobooker"})
        return session

    def check_health(self) -> bool:
        session = self._session()
        try:
            response = session.get(f"{self.server_url}/", timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def prepare(self) -> None:
        if not self.check_health():
            raise EngineError(f"cannot reach Chatterbox server at {self.server_url}")
        if not self.probe:
            return
        # A one-word synthesis tells us the real sample rate of the server, so a
        # 32 kHz server can no longer silently produce pitch-shifted audiobooks.
        try:
            _, sample_rate = self._request("Hello.")
        except Exception as exc:  # pragma: no cover - network dependent
            self._log(
                f"Could not probe server sample rate ({exc}); assuming {self.sample_rate} Hz."
            )
            return
        if sample_rate and sample_rate != self.sample_rate:
            self._log(f"Server reports {sample_rate} Hz; using that for output.")
            self.sample_rate = int(sample_rate)

    # -- request/response --------------------------------------------------
    def _request(
        self, text: str, exaggeration: float = 0.5, cfg_weight: float = 0.5
    ) -> tuple[np.ndarray, int]:
        session = self._session()
        payload = {
            "data": [
                None,  # gradio state slot
                text,
                self.voice_prompt_path,
                float(exaggeration),
                self.temperature,
                self.seed,
                float(cfg_weight),
            ]
        }
        response = session.post(
            f"{self.server_url}/gradio_api/call/generate", json=payload, timeout=self.timeout
        )
        response.raise_for_status()
        event_id = (response.json() or {}).get("event_id")
        if not event_id:
            raise EngineError("server did not return an event id")

        status_url = f"{self.server_url}/gradio_api/call/generate/{event_id}"
        result = self._read_result(session, status_url)
        return self._decode_payload(session, result)

    def _read_result(self, session, status_url: str):
        """Prefer Gradio's SSE stream, fall back to polling the status endpoint."""
        try:
            response = session.get(
                status_url,
                stream=True,
                timeout=self.timeout,
                headers={"Accept": "text/event-stream"},
            )
        except Exception as exc:  # network hiccup: polling may still work
            self._log(f"SSE request failed ({exc}); falling back to polling")
            return self._poll(session, status_url)

        with response:
            content_type = response.headers.get("content-type", "")
            if response.status_code != 200 or "event-stream" not in content_type:
                return self._poll(session, status_url)
            try:
                return self._parse_stream(response)
            except EngineError:
                raise
            except Exception as exc:
                self._log(f"SSE stream broke ({exc}); falling back to polling")
                return self._poll(session, status_url)

    @staticmethod
    def _parse_stream(response):
        """Return the final ``data:`` payload of a Gradio event stream."""
        event = None
        last_payload = None
        for raw in response.iter_lines(decode_unicode=True):
            if raw is None:
                continue
            line = raw.strip()
            if not line:
                continue
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
                continue
            if not line.startswith("data:"):
                continue
            body = line.split(":", 1)[1].strip()
            if not body or body == "null":
                continue
            try:
                payload = json.loads(body)
            except ValueError:
                continue
            if isinstance(payload, dict) and payload.get("error"):
                raise EngineError(f"server error: {payload['error']}")
            last_payload = payload
            if event in ("complete", "process_completed"):
                return payload
        if last_payload is not None:
            return last_payload
        raise EngineError("event stream ended without a result")

    def _poll(self, session, status_url: str):
        """JSON polling fallback for servers that do not stream."""
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            time.sleep(1.0)
            status = session.get(status_url, timeout=30)
            if status.status_code != 200:
                continue
            payload = status.json() or {}
            message = payload.get("msg")
            if message == "process_completed":
                return payload
            if message == "process_failed":
                raise EngineError(f"server failed to synthesise: {payload.get('output')}")
            if payload.get("error"):
                raise EngineError(f"server error: {payload['error']}")
        raise EngineError("timed out waiting for the server to synthesise audio")

    # -- payload decoding --------------------------------------------------
    def _audio_reference(self, data) -> tuple[str, str]:
        """Find the audio location in a Gradio result payload."""
        for item in data or []:
            if isinstance(item, dict):
                path = item.get("path") or item.get("name")
                if path and str(path).endswith((".wav", ".mp3", ".flac", ".ogg")):
                    return "url", f"{self.server_url}/file={path}"
                if item.get("url"):
                    return "url", item["url"]
            if isinstance(item, str):
                if item.startswith("data:audio"):
                    return "base64", item
                if item.startswith("http"):
                    return "url", item
                if item.endswith((".wav", ".mp3", ".flac", ".ogg")):
                    return "url", f"{self.server_url}/file={item}"
        raise EngineError(f"no audio in server response: {str(data)[:200]}")

    def _decode_payload(self, session, payload) -> tuple[np.ndarray, int]:
        data = payload
        if isinstance(payload, dict):
            data = payload.get("data")
            if data is None:
                data = (payload.get("output") or {}).get("data") or []
        kind, value = self._audio_reference(data)

        if kind == "base64":
            encoded = value.split(",", 1)[1] if "," in value else value
            return _decode_wav(base64.b64decode(encoded))

        response = session.get(value, timeout=self.timeout)
        response.raise_for_status()
        content = response.content
        if content[:4] == b"RIFF":
            return _decode_wav(content)
        # Some servers answer with a JSON document holding a data URI.
        try:
            inner = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise EngineError("server returned audio that is not a WAV file")
        if isinstance(inner, str) and inner.startswith("data:audio"):
            return _decode_wav(base64.b64decode(inner.split(",", 1)[1]))
        raise EngineError("could not decode the audio returned by the server")

    def generate(self, text: str, *, exaggeration: float, cfg_weight: float) -> np.ndarray:
        samples, sample_rate = self._request(
            text, exaggeration=exaggeration, cfg_weight=cfg_weight
        )
        if sample_rate and self.sample_rate and sample_rate != self.sample_rate:
            raise EngineError(
                f"server returned {sample_rate} Hz but the job expects {self.sample_rate} Hz; "
                "pass --sample-rate to match the server"
            )
        if samples.size == 0:
            raise EngineError("server returned no audio samples")
        return samples
