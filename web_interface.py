#!/usr/bin/env python3
"""
Gradio Web Interface for Chatterbox Audiobook Creator
Simple web UI for creating audiobooks from text with optional voice cloning.
"""

import gradio as gr
import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS
import re
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
import time

# Import our audiobook creation functions
from app import detect_chapters, smart_text_split, create_audiobook, VERSION

# Global model instance for efficiency
model = None
model_device = "cuda" if torch.cuda.is_available() else "cpu"

def load_model():
    """Load the TTS model once at startup."""
    global model
    if model is None:
        print("Loading ChatterboxTTS model...")
        try:
            model = ChatterboxTTS.from_pretrained(device=model_device)
            print(f"Model loaded successfully on {model_device}")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise e
    return model

def process_audiobook(
    text_input: str,
    text_file,
    voice_file,
    exaggeration: float,
    cfg_weight: float,
    chapter_pause: float,
    output_filename: str
) -> Tuple[str, str]:
    """
    Main function to process audiobook creation from web interface.
    Returns (audio_file_path, status_message)
    """
    try:
        # Load model
        tts_model = load_model()
        
        # Determine text source
        if text_file is not None:
            # Read uploaded file
            try:
                with open(text_file.name, 'r', encoding='utf-8') as f:
                    full_text = f.read().strip()
                text_source = f"Uploaded file: {text_file.name}"
            except Exception as e:
                return None, f"❌ Error reading uploaded file: {str(e)}"
        elif text_input.strip():
            # Use typed text
            full_text = text_input.strip()
            text_source = "Text input"
        else:
            return None, "❌ Please provide either text input or upload a text file."
        
        if not full_text:
            return None, "❌ No text content found."
        
        # Process voice file
        voice_path = None
        if voice_file is not None:
            voice_path = voice_file.name
            voice_source = f"Voice file: {os.path.basename(voice_path)}"
        else:
            voice_source = "Default voice"
        
        # Create output filename
        if not output_filename.strip():
            output_filename = "audiobook"
        
        # Ensure .wav extension
        if not output_filename.endswith('.wav'):
            output_filename += '.wav'
        
        # Create temporary output path
        output_path = os.path.join(tempfile.gettempdir(), output_filename)
        
        # Status message
        status_msg = f"🎬 **Processing Audiobook**\n\n"
        status_msg += f"📖 **Text source:** {text_source}\n"
        status_msg += f"🎤 **Voice:** {voice_source}\n"
        status_msg += f"📊 **Settings:** Exaggeration={exaggeration}, CFG Weight={cfg_weight}, Chapter Pause={chapter_pause}s\n"
        status_msg += f"💾 **Output:** {output_filename}\n\n"
        
        # Detect chapters for preview
        sections = detect_chapters(full_text)
        chapter_count = sum(1 for section in sections if section['is_chapter_title'])
        
        status_msg += f"📚 **Detected:** {len(sections)} sections ({chapter_count} chapter titles)\n"
        status_msg += f"📝 **Total characters:** {len(full_text):,}\n\n"
        
        # Process each section
        all_audio_chunks = []
        total_chunks = 0
        processing_log = []
        
        for section_idx, section_data in enumerate(sections):
            section_text = section_data['text']
            is_chapter_title = section_data['is_chapter_title']
            
            if is_chapter_title:
                processing_log.append(f"🎯 Processing Chapter Title: '{section_text[:50]}...'")
                
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
                    processing_log.append(f"  ✅ Generated chapter title audio ({len(section_text)} chars)")
                    
                except Exception as e:
                    processing_log.append(f"  ❌ Error generating chapter title: {str(e)}")
                    continue
                
                # Add pause AFTER chapter title
                if chapter_pause > 0:
                    pause_samples = int(chapter_pause * tts_model.sr)
                    pause_audio = torch.zeros(pause_samples)
                    all_audio_chunks.append(pause_audio)
                    
            else:
                # Regular content section
                processing_log.append(f"📄 Processing Content Section {section_idx + 1}/{len(sections)}")
                
                # Split section into chunks
                text_chunks = smart_text_split(section_text, max_length=300)
                total_chunks += len(text_chunks)
                processing_log.append(f"  Split into {len(text_chunks)} chunks")
                
                if not text_chunks:
                    continue

                # Synthesize each chunk
                section_audio_chunks = []
                
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
                        
                        section_audio_chunks.append(wav.squeeze(0).cpu())
                        
                    except Exception as e:
                        processing_log.append(f"    ❌ Error in chunk {i}: {str(e)}")
                        continue

                if section_audio_chunks:
                    # Concatenate section audio
                    section_audio = torch.cat(section_audio_chunks)
                    all_audio_chunks.append(section_audio)
                    
                    section_duration = len(section_audio) / tts_model.sr
                    processing_log.append(f"  ✅ Section complete: {section_duration:.1f}s")

        # Final concatenation and save
        if not all_audio_chunks:
            return None, "❌ No audio was generated."

        processing_log.append("🔗 Concatenating all audio...")
        full_audio = torch.cat(all_audio_chunks)
        
        processing_log.append(f"💾 Saving to {output_filename}...")
        ta.save(output_path, full_audio.unsqueeze(0), tts_model.sr)
        
        # Calculate final statistics
        total_duration = len(full_audio) / tts_model.sr
        total_minutes = total_duration / 60
        
        # Update status with results
        status_msg += "🎉 **Generation Complete!**\n\n"
        status_msg += f"⏱️  **Duration:** {total_minutes:.1f} minutes ({total_duration:.1f} seconds)\n"
        status_msg += f"📊 **Processing:** {total_chunks} total chunks\n"
        status_msg += f"🚀 **Speed:** {len(full_text) / total_duration:.1f} chars/second\n"
        status_msg += f"🎯 **Device:** {model_device.upper()}\n\n"
        
        # Add processing log
        status_msg += "📋 **Processing Log:**\n"
        for log_entry in processing_log[-10:]:  # Show last 10 entries
            status_msg += f"• {log_entry}\n"
        
        return output_path, status_msg
        
    except Exception as e:
        error_msg = f"❌ **Error during processing:**\n\n{str(e)}"
        return None, error_msg

def create_interface():
    """Create and configure the Gradio interface."""
    
    # Custom CSS for better styling
    css = """
    .container {
        max-width: 1200px;
        margin: auto;
    }
    .header {
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-box {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    """
    
    with gr.Blocks(css=css, title=f"Audiobook Creator v{VERSION}") as interface:
        
        # Header
        gr.Markdown(f"""
        # 🎧 Chatterbox Audiobook Creator v{VERSION}
        
        Create professional audiobooks from text with optional voice cloning.
        
        **Features:**
        • Automatic chapter detection with pauses
        • Voice cloning from audio samples
        • Smart text chunking and processing
        • Professional audio output
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## 📝 Text Input")
                
                # Text input options
                text_input = gr.Textbox(
                    label="Type or paste your text here",
                    placeholder="Enter your book text, or upload a file below...",
                    lines=10,
                    max_lines=20
                )
                
                text_file = gr.File(
                    label="Or upload a text file (.txt)",
                    file_types=[".txt"],
                    type="filepath"
                )
                
                gr.Markdown("## 🎤 Voice Settings")
                
                voice_file = gr.File(
                    label="Upload voice sample (optional)",
                    file_types=[".wav", ".mp3", ".m4a", ".flac"],
                    type="filepath"
                )
                
                gr.Markdown("*Upload a 5-30 second clear voice sample for voice cloning*")
                
            with gr.Column(scale=1):
                gr.Markdown("## ⚙️ Generation Settings")
                
                exaggeration = gr.Slider(
                    minimum=0.0,
                    maximum=1.0,
                    value=0.5,
                    step=0.1,
                    label="Emotion Exaggeration",
                    info="Higher values = more expressive narration"
                )
                
                cfg_weight = gr.Slider(
                    minimum=0.0,
                    maximum=1.0,
                    value=0.5,
                    step=0.1,
                    label="CFG Weight",
                    info="Lower values = faster speech, higher = more careful"
                )
                
                chapter_pause = gr.Slider(
                    minimum=0.0,
                    maximum=5.0,
                    value=1.0,
                    step=0.5,
                    label="Chapter Pause (seconds)",
                    info="Pause duration before and after chapter titles"
                )
                
                output_filename = gr.Textbox(
                    label="Output filename",
                    value="my_audiobook",
                    placeholder="my_audiobook",
                    info="Filename for the generated audiobook (.wav will be added)"
                )
                
                # Generate button
                generate_btn = gr.Button(
                    "🎬 Generate Audiobook",
                    variant="primary",
                    size="lg"
                )
        
        # Output section
        gr.Markdown("## 📊 Results")
        
        with gr.Row():
            with gr.Column(scale=1):
                audio_output = gr.Audio(
                    label="Generated Audiobook",
                    type="filepath"
                )
                
            with gr.Column(scale=1):
                status_output = gr.Markdown(
                    value="Ready to generate audiobook...",
                    elem_classes=["status-box"]
                )
        
        # Examples
        gr.Markdown("""
        ## 📚 Example Usage
        
        1. **Quick Start:** Paste some text and click "Generate Audiobook"
        2. **With Voice Cloning:** Upload a clear voice sample (5-30 seconds) and your text
        3. **From File:** Upload a .txt file instead of typing
        4. **Custom Settings:** Adjust emotion, speed, and chapter pauses to your liking
        
        **Tips:**
        • Chapter titles like "Chapter 1", "Part 1", etc. are automatically detected
        • Voice samples should be clear, single speaker, 5-30 seconds long
        • Longer texts will take more time to process
        """)
        
        # Connect the generate button
        generate_btn.click(
            fn=process_audiobook,
            inputs=[
                text_input,
                text_file,
                voice_file,
                exaggeration,
                cfg_weight,
                chapter_pause,
                output_filename
            ],
            outputs=[audio_output, status_output]
        )
    
    return interface

def main():
    """Main function to launch the web interface."""
    print(f"🚀 Starting Audiobook Creator Web Interface v{VERSION}")
    print(f"🎯 Device: {model_device}")
    
    # Pre-load the model
    try:
        load_model()
        print("✅ Model loaded successfully")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        print("The interface will start but may fail when generating audio.")
    
    # Create and launch interface
    interface = create_interface()
    
    print("\n🌐 Launching web interface...")
    print("📱 The interface will open in your browser automatically")
    print("🔗 If not, check the URL printed below")
    
    interface.launch(
        server_name="0.0.0.0",  # Allow external connections
        server_port=7860,
        share=False,  # Set to True to create a public link
        show_error=True,
        show_tips=True,
        enable_queue=True  # Handle multiple requests
    )

if __name__ == "__main__":
    main()
