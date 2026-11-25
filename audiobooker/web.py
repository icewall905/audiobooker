"""Gradio front end: ``audiobook-web``.

The job runner below is plain Python (no Gradio import at module level), so it
can be unit-tested and reused by any other HTTP front end.
"""

from __future__ import annotations

import logging
import os
import tempfile
import traceback
from pathlib import Path
from typing import Callable, Optional, Tuple

from . import __version__
from .engine import ChatterboxEngine, EngineError
from .pipeline import AudiobookPipeline, PipelineConfig, PipelineError

LOGGER = logging.getLogger("audiobooker.web")
DEFAULT_MAX_CHUNK_LENGTH = 300

_ENGINE: Optional[ChatterboxEngine] = None


def get_engine(device: Optional[str] = None) -> ChatterboxEngine:
    """Load the model once per process and reuse it across requests."""
    global _ENGINE
    if _ENGINE is None:
        engine = ChatterboxEngine(device=device)
        engine.prepare()
        _ENGINE = engine
    return _ENGINE


def _path_of(upload) -> Optional[str]:
    """Gradio hands back either a path string or a tempfile-like object."""
    if upload is None:
        return None
    return getattr(upload, "name", None) or str(upload)


def _read_upload(upload) -> str:
    path = _path_of(upload)
    if not path:
        raise PipelineError("uploaded document could not be read")
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def generate_audiobook(
    text_input: str = "",
    document_file=None,
    voice_file=None,
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
    chapter_pause: float = 1.0,
    max_chunk_length: int = DEFAULT_MAX_CHUNK_LENGTH,
    progress: Optional[Callable] = None,
) -> Tuple[Optional[str], str]:
    """Render one job. Returns ``(audio_path, status_text)``.

    ``progress`` may be a Gradio ``gr.Progress`` instance; it is called with a
    fraction and a description.
    """
    status: list = []

    def report(message: str) -> None:
        status.append(message)
        LOGGER.info(message)

    try:
        if document_file is not None:
            document_text = _read_upload(document_file)
            source = f"Uploaded file: {os.path.basename(_path_of(document_file) or '')}"
        elif text_input and text_input.strip():
            document_text = text_input.strip()
            source = "Direct text input"
        else:
            return None, "Please provide either text input or upload a document file."

        if not document_text.strip():
            return None, "No text content found to convert."

        voice_path = _path_of(voice_file)
        voice_label = (
            f"Uploaded voice: {os.path.basename(voice_path)}" if voice_path else "Default voice"
        )

        engine = get_engine()
        # The model stays loaded; only the prompt changes per request.
        engine.voice_prompt_path = voice_path

        output_dir = Path(tempfile.mkdtemp(prefix="audiobooker-"))
        config = PipelineConfig(
            output_path=str(output_dir / "audiobook.wav"),
            document_text=document_text,
            voice_prompt_path=voice_path,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            chapter_pause=chapter_pause,
            max_chunk_length=int(max_chunk_length),
        )

        def on_progress(done: int, total: int, message: str) -> None:
            report(message)
            if progress is not None:
                fraction = 0.05 + 0.9 * min(done / max(total, 1), 1.0)
                progress(min(fraction, 0.99), desc=message)

        pipeline = AudiobookPipeline(
            config, engine=engine, log=report, progress=on_progress
        )
        result = pipeline.run()
        if progress is not None:
            progress(1.0, desc="Complete")

        header = [
            f"📖 Text source: {source}",
            f"🎤 Voice: {voice_label}",
            f"⚙️ Exaggeration={exaggeration}, CFG weight={cfg_weight}, "
            f"Chapter pause={chapter_pause}s, Chunk size={max_chunk_length}",
            f"🖥️ Device: {getattr(engine, 'device', engine.name)}",
            "",
        ]
        return result.output_path, "\n".join(header + result.summary_lines())

    except (PipelineError, EngineError) as exc:
        LOGGER.error("audiobook job failed: %s", exc)
        return None, f"❌ {exc}\n\n" + "\n".join(status[-20:])
    except Exception as exc:  # noqa: BLE001 - surface anything to the UI
        LOGGER.error("audiobook job crashed: %s\n%s", exc, traceback.format_exc())
        return None, f"❌ Unexpected error: {exc}\n\n" + "\n".join(status[-20:])


def build_interface():
    """Construct the Gradio Blocks UI (imports gradio here, not at module load)."""
    import gradio as gr
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"

    with gr.Blocks(title=f"Chatterbox Audiobook Creator v{__version__}") as interface:
        gr.Markdown(
            f"""
            # 🎧 Chatterbox Audiobook Creator v{__version__}

            Convert your text into high-quality audiobooks using AI voice synthesis!

            **Features:**
            - 📖 Automatic chapter detection with pauses
            - 🎤 Voice cloning support (upload your own voice sample)
            - ⚙️ Adjustable speech parameters
            - 💾 Resumable, streamed rendering (long books no longer need lots of RAM)
            - 🖥️ GPU acceleration ({device} detected)
            """
        )

        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("## 📝 Input Text")
                text_input = gr.Textbox(
                    label="Text Content",
                    placeholder=(
                        "Type or paste your text here...\n\nExample:\n"
                        "Chapter 1: The Beginning\n\nOnce upon a time..."
                    ),
                    lines=10,
                    max_lines=20,
                )
                document_file = gr.File(
                    label="Or Upload Document (.txt file)",
                    file_types=[".txt"],
                    type="filepath",
                )
                gr.Markdown("*Note: Document upload will override text input*")

            with gr.Column(scale=1):
                gr.Markdown("## 🎤 Voice Settings")
                voice_file = gr.File(
                    label="Voice Sample (Optional)",
                    file_types=[".wav", ".mp3", ".m4a", ".flac"],
                    type="filepath",
                )
                gr.Markdown("## ⚙️ Audio Settings")
                exaggeration = gr.Slider(0.0, 1.0, value=0.5, step=0.1,
                                         label="Emotion Exaggeration",
                                         info="Higher values = more expressive speech")
                cfg_weight = gr.Slider(0.0, 1.0, value=0.5, step=0.1,
                                       label="CFG Weight",
                                       info="Higher values = slower, more careful speech")
                chapter_pause = gr.Slider(0.0, 5.0, value=1.0, step=0.5,
                                          label="Chapter Pause (seconds)",
                                          info="Pause duration before and after chapter titles")
                max_chunk_length = gr.Slider(100, 600, value=DEFAULT_MAX_CHUNK_LENGTH, step=50,
                                             label="Max chunk length (characters)",
                                             info="Smaller = more stable, slower")

        with gr.Row():
            generate_btn = gr.Button("🎧 Generate Audiobook", variant="primary", size="lg")
            clear_btn = gr.Button("🗑️ Clear All", variant="secondary")

        with gr.Row():
            audio_output = gr.Audio(label="🎧 Generated Audiobook", type="filepath")
            status_output = gr.Textbox(label="📊 Status & Statistics", lines=15,
                                       max_lines=25, show_copy_button=True)

        inputs = [text_input, document_file, voice_file, exaggeration, cfg_weight,
                  chapter_pause, max_chunk_length]
        generate_btn.click(
            fn=generate_audiobook,
            inputs=inputs,
            outputs=[audio_output, status_output],
            show_progress=True,
        )
        clear_btn.click(
            fn=lambda: (None, None, None, 0.5, 0.5, 1.0, DEFAULT_MAX_CHUNK_LENGTH, None, ""),
            outputs=[text_input, document_file, voice_file, exaggeration, cfg_weight,
                     chapter_pause, max_chunk_length, audio_output, status_output],
        )

        gr.Markdown("## 📚 Example Texts")
        gr.Examples(
            examples=[
                [
                    "Chapter 1: The Digital Age\n\nIn the year 2024, artificial "
                    "intelligence had become as common as smartphones once were.\n\n"
                    "Chapter 2: The Discovery\n\nThe algorithm she had been working on "
                    "began to exhibit behaviour that defied explanation.",
                    None, None, 0.6, 0.4, 1.5, DEFAULT_MAX_CHUNK_LENGTH,
                ],
            ],
            inputs=inputs,
            label="Try this example:",
        )

    return interface


def main(argv=None) -> int:
    """Launch the web interface."""
    print(f"🎧 Starting Chatterbox Audiobook Creator Web Interface v{__version__}")
    try:
        engine = get_engine()
        print(f"✅ Model loaded on {engine.device} ({engine.sample_rate} Hz)")
    except Exception as exc:
        print(f"❌ Failed to load model: {exc}")
        print("Install the local extras with: pip install -e '.[local,web]'")
        return 1

    interface = build_interface()
    interface.launch(
        server_name="0.0.0.0",  # reachable from the LAN, as before
        server_port=7860,
        share=False,
        show_error=True,
        show_tips=True,
        inbrowser=True,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
