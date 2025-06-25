#!/usr/bin/env python3
"""
Web interface for the Chatterbox Audiobook Creator using Gradio.
Allows users to input text directly or upload documents, and optionally upload voice samples.
"""

import gradio as gr
import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS
import re
import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
import traceback

# Import our audiobook creation functions
from app import detect_chapters, smart_text_split, validate_inputs, VERSION

# Configuration
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MAX_CHUNK_LENGTH = 300

# Global model variable to avoid reloading
model = None

def load_model():
    """Load the Chatterbox TTS model once and reuse it."""
    global model
    if model is None:
        try:
            print(f"Loading ChatterboxTTS model on {DEVICE}...")
            model = ChatterboxTTS.from_pretrained(device=DEVICE)
            print("Model loaded successfully!")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise e
    return model

def create_audiobook_web(
    text_input: str,
    document_file,
    voice_file,
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
    chapter_pause: float = 1.0,
    progress=gr.Progress()
) -> Tuple[str, str]:
    """
    Create audiobook from web interface inputs.
    Returns (audio_file_path, status_message)
    """
    try:
        # Progress tracking
        progress(0.1, desc="Initializing...")
        
        # Load model
        tts_model = load_model()
        
        # Determine text source
        if document_file is not None:
            progress(0.2, desc="Reading uploaded document...")
            try:
                with open(document_file.name, 'r', encoding='utf-8') as f:
                    full_text = f.read()
                text_source = f"Uploaded file: {os.path.basename(document_file.name)}"
            except Exception as e:
                return None, f"Error reading uploaded file: {str(e)}"
        elif text_input.strip():
            progress(0.2, desc="Processing text input...")
            full_text = text_input.strip()
            text_source = "Direct text input"
        else:
            return None, "Please provide either text input or upload a document file."
        
        if not full_text.strip():
            return None, "No text content found to convert."
        
        # Handle voice file
        voice_path = None
        if voice_file is not None:
            voice_path = voice_file.name
            voice_source = f"Uploaded voice: {os.path.basename(voice_file.name)}"
        else:
            voice_source = "Default voice"
        
        progress(0.3, desc="Analyzing text structure...")
        
        # Detect chapters and sections
        sections = detect_chapters(full_text)
        chapter_count = sum(1 for section in sections if section['is_chapter_title'])
        
        status_info = [
            f"📖 Text source: {text_source}",
            f"🎤 Voice: {voice_source}",
            f"📊 Detected {len(sections)} sections ({chapter_count} chapter titles)",
            f"⚙️ Settings: Exaggeration={exaggeration}, CFG Weight={cfg_weight}, Chapter Pause={chapter_pause}s",
            f"🖥️ Device: {DEVICE}",
            ""
        ]
        
        # Process sections
        all_audio_chunks = []
        total_chunks = 0
        current_chapter = 0
        
        for section_idx, section_data in enumerate(sections):
            section_text = section_data['text']
            is_chapter_title = section_data['is_chapter_title']
            
            progress(0.3 + (0.6 * section_idx / len(sections)), 
                    desc=f"Processing section {section_idx + 1}/{len(sections)}...")
            
            if is_chapter_title:
                current_chapter += 1
                status_info.append(f"🎯 Processing Chapter Title {current_chapter}: '{section_text[:50]}...'")
                
                # Add pause BEFORE chapter title (except for very first section)
                if section_idx > 0 and chapter_pause > 0:
                    pause_samples = int(chapter_pause * tts_model.sr)
                    pause_audio = torch.zeros(pause_samples)
                    all_audio_chunks.append(pause_audio)
                
                # Generate audio for chapter title
                try:
                    if voice_path:
                        wav = tts_model.generate(
                            section_text,
                            audio_prompt_path=voice_path,
                            exaggeration=exaggeration,
                            cfg_weight=cfg_weight
                        )
                    else:
                        wav = tts_model.generate(
                            section_text,
                            exaggeration=exaggeration,
                            cfg_weight=cfg_weight
                        )
                    
                    all_audio_chunks.append(wav.squeeze(0).cpu())
                    
                except Exception as e:
                    status_info.append(f"  ❌ Error generating audio for chapter title: {e}")
                    continue
                
                # Add pause AFTER chapter title
                if chapter_pause > 0:
                    pause_samples = int(chapter_pause * tts_model.sr)
                    pause_audio = torch.zeros(pause_samples)
                    all_audio_chunks.append(pause_audio)
                    
            else:
                # Regular content section
                status_info.append(f"📝 Processing content section {section_idx + 1}")
                
                # Split section into chunks
                text_chunks = smart_text_split(section_text, max_length=MAX_CHUNK_LENGTH)
                total_chunks += len(text_chunks)
                
                if not text_chunks:
                    continue

                # Synthesize each chunk
                for i, chunk in enumerate(text_chunks, 1):
                    try:
                        if voice_path:
                            wav = tts_model.generate(
                                chunk,
                                audio_prompt_path=voice_path,
                                exaggeration=exaggeration,
                                cfg_weight=cfg_weight
                            )
                        else:
                            wav = tts_model.generate(
                                chunk,
                                exaggeration=exaggeration,
                                cfg_weight=cfg_weight
                            )
                        
                        all_audio_chunks.append(wav.squeeze(0).cpu())
                        
                    except Exception as e:
                        status_info.append(f"  ❌ Error generating audio for chunk {i}: {e}")
                        continue

        progress(0.9, desc="Finalizing audiobook...")
        
        if not all_audio_chunks:
            return None, "No audio was generated. Please check your inputs."

        # Concatenate all audio
        full_audio = torch.cat(all_audio_chunks)
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        # Save the audiobook
        ta.save(output_path, full_audio.unsqueeze(0), tts_model.sr)
        
        # Calculate statistics
        total_duration = len(full_audio) / tts_model.sr
        total_minutes = total_duration / 60
        total_chars = len(full_text)
        
        status_info.extend([
            "",
            f"✅ Audiobook creation complete! (v{VERSION})",
            f"📊 Final Statistics:",
            f"   📝 Total characters: {total_chars:,}",
            f"   🔢 Total chunks: {total_chunks}",
            f"   ⏱️ Duration: {total_minutes:.1f} minutes ({total_duration:.1f} seconds)",
            f"   🚀 Speaking rate: {total_chars / total_duration:.1f} chars/second",
            f"   📂 Temporary file: {os.path.basename(output_path)}"
        ])
        
        progress(1.0, desc="Complete!")
        
        return output_path, "\n".join(status_info)
        
    except Exception as e:
        error_msg = f"❌ Error creating audiobook: {str(e)}\n\n" + traceback.format_exc()
        return None, error_msg

def create_interface():
    """Create and configure the Gradio interface."""
    
    with gr.Blocks(title=f"Chatterbox Audiobook Creator v{VERSION}", theme=gr.themes.Soft()) as interface:
        
        gr.Markdown(f"""
        # 🎧 Chatterbox Audiobook Creator v{VERSION}
        
        Convert your text into high-quality audiobooks using AI voice synthesis!
        
        **Features:**
        - 📖 Automatic chapter detection with pauses
        - 🎤 Voice cloning support (upload your own voice sample)
        - ⚙️ Adjustable speech parameters
        - 🖥️ GPU acceleration ({DEVICE} detected)
        """)
        
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("## 📝 Input Text")
                
                text_input = gr.Textbox(
                    label="Text Content",
                    placeholder="Type or paste your text here...\n\nExample:\nChapter 1: The Beginning\n\nOnce upon a time...",
                    lines=10,
                    max_lines=20
                )
                
                document_file = gr.File(
                    label="Or Upload Document (.txt file)",
                    file_types=[".txt"],
                    type="filepath"
                )
                
                gr.Markdown("*Note: Document upload will override text input*")
                
            with gr.Column(scale=1):
                gr.Markdown("## 🎤 Voice Settings")
                
                voice_file = gr.File(
                    label="Voice Sample (Optional)",
                    file_types=[".wav", ".mp3", ".m4a", ".flac"],
                    type="filepath"
                )
                
                gr.Markdown("## ⚙️ Audio Settings")
                
                exaggeration = gr.Slider(
                    minimum=0.0,
                    maximum=1.0,
                    value=0.5,
                    step=0.1,
                    label="Emotion Exaggeration",
                    info="Higher values = more expressive speech"
                )
                
                cfg_weight = gr.Slider(
                    minimum=0.0,
                    maximum=1.0,
                    value=0.5,
                    step=0.1,
                    label="CFG Weight",
                    info="Higher values = slower, more careful speech"
                )
                
                chapter_pause = gr.Slider(
                    minimum=0.0,
                    maximum=5.0,
                    value=1.0,
                    step=0.5,
                    label="Chapter Pause (seconds)",
                    info="Pause duration before and after chapter titles"
                )
        
        with gr.Row():
            generate_btn = gr.Button("🎧 Generate Audiobook", variant="primary", size="lg")
            clear_btn = gr.Button("🗑️ Clear All", variant="secondary")
        
        with gr.Row():
            with gr.Column():
                audio_output = gr.Audio(
                    label="🎧 Generated Audiobook",
                    type="filepath"
                )
                
                status_output = gr.Textbox(
                    label="📊 Status & Statistics",
                    lines=15,
                    max_lines=25,
                    show_copy_button=True
                )
        
        # Event handlers
        generate_btn.click(
            fn=create_audiobook_web,
            inputs=[text_input, document_file, voice_file, exaggeration, cfg_weight, chapter_pause],
            outputs=[audio_output, status_output],
            show_progress=True
        )
        
        clear_btn.click(
            fn=lambda: (None, None, None, 0.5, 0.5, 1.0, None, ""),
            outputs=[text_input, document_file, voice_file, exaggeration, cfg_weight, chapter_pause, audio_output, status_output]
        )
        
        # Examples
        gr.Markdown("## 📚 Example Texts")
        
        examples = [
            [
                """Chapter 1: The Digital Age

In the year 2024, artificial intelligence had become as common as smartphones once were. Sarah, a young researcher, discovered something extraordinary in her laboratory that would change everything.

Chapter 2: The Discovery

The algorithm she had been working on for months suddenly began to exhibit behavior that defied explanation. It wasn't just processing data—it was creating, imagining, dreaming.""",
                None, None, 0.6, 0.4, 1.5
            ],
            [
                """Part 1: Introduction

Welcome to the world of audio storytelling. This is a simple example of how chapter detection works.

Part 2: The Magic

With just a few clicks, your written words transform into spoken narratives, complete with natural pauses and expressive delivery.""",
                None, None, 0.4, 0.6, 2.0
            ]
        ]
        
        gr.Examples(
            examples=examples,
            inputs=[text_input, document_file, voice_file, exaggeration, cfg_weight, chapter_pause],
            label="Try these examples:"
        )
    
    return interface

def main():
    """Launch the web interface."""
    print(f"🎧 Starting Chatterbox Audiobook Creator Web Interface v{VERSION}")
    print(f"🖥️ Device: {DEVICE}")
    
    try:
        # Pre-load the model to show any errors early
        load_model()
        print("✅ Model loaded successfully!")
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        print("Please make sure you have installed the required dependencies:")
        print("  pip install chatterbox-tts torch torchaudio")
        return
    
    interface = create_interface()
    
    # Launch the interface
    interface.launch(
        server_name="0.0.0.0",  # Allow external connections
        server_port=7860,
        share=False,  # Set to True if you want a public link
        show_error=True,
        show_tips=True,
        inbrowser=True
    )

if __name__ == "__main__":
    main()
