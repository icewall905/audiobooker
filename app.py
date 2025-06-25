import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS
import re
import os
import sys
from pathlib import Path
import argparse
from typing import List, Optional

# --- Configuration ---
DOCUMENT_PATH = "sample_document.txt" 
VOICE_PROMPT_PATH = None  # Set to your voice reference file path if available
OUTPUT_PATH = "my_audiobook.wav" 
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MAX_CHUNK_LENGTH = 300

def smart_text_split(text: str, max_length: int = MAX_CHUNK_LENGTH) -> List[str]:
    """Intelligently split text into chunks, respecting sentence boundaries."""
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        if len(paragraph) <= max_length:
            chunks.append(paragraph)
        else:
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            current_chunk = ""
            
            for sentence in sentences:
                if current_chunk and len(current_chunk + " " + sentence) > max_length:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
    
    return chunks

def validate_inputs(document_path: str, voice_prompt_path: Optional[str] = None) -> bool:
    """Validate that required input files exist."""
    if not os.path.exists(document_path):
        print(f"Error: Document file '{document_path}' not found.")
        return False
    
    if voice_prompt_path and not os.path.exists(voice_prompt_path):
        print(f"Error: Voice reference file '{voice_prompt_path}' not found.")
        return False
    
    return True

def create_audiobook(document_path: str = DOCUMENT_PATH, 
                   voice_prompt_path: Optional[str] = VOICE_PROMPT_PATH,
                   output_path: str = OUTPUT_PATH,
                   exaggeration: float = 0.5,
                   cfg_weight: float = 0.5,
                   device: str = DEVICE):
    """Create audiobook from document using Chatterbox TTS."""
    
    if not validate_inputs(document_path, voice_prompt_path):
        return False
    
    print(f"Using device: {device}")
    print(f"Voice reference: {'Yes' if voice_prompt_path else 'No (using default voice)'}")

    # Initialize the Chatterbox model
    print("Loading ChatterboxTTS model...")
    try:
        model = ChatterboxTTS.from_pretrained(device=device)
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")
        return False

    # Load and chunk the document
    print(f"Loading document from {document_path}...")
    try:
        with open(document_path, 'r', encoding='utf-8') as f:
            full_text = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return False

    text_chunks = smart_text_split(full_text, max_length=MAX_CHUNK_LENGTH)
    print(f"Document split into {len(text_chunks)} chunks.")
    
    if not text_chunks:
        print("No text found in document.")
        return False

    # Synthesize each chunk
    audio_chunks = []
    print("Starting audio generation for each chunk...")
    
    for i, chunk in enumerate(text_chunks, 1):
        print(f"Generating audio for chunk {i}/{len(text_chunks)} ({len(chunk)} chars)...")
        try:
            if voice_prompt_path:
                wav = model.generate(
                    chunk,
                    audio_prompt_path=voice_prompt_path,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight
                )
            else:
                wav = model.generate(
                    chunk,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight
                )
            
            audio_chunks.append(wav.squeeze(0).cpu())
            
        except Exception as e:
            print(f"Error generating audio for chunk {i}: {e}")
            continue

    # Concatenate and save
    if not audio_chunks:
        print("No audio was generated. Exiting.")
        return False

    print("Concatenating audio chunks...")
    try:
        full_audio = torch.cat(audio_chunks)
        
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        print(f"Saving final audiobook to {output_path} with sample rate {model.sr} Hz...")
        ta.save(output_path, full_audio.unsqueeze(0), model.sr)
        
        duration_seconds = len(full_audio) / model.sr
        duration_minutes = duration_seconds / 60
        print(f"Audiobook creation complete!")
        print(f"Duration: {duration_minutes:.1f} minutes ({duration_seconds:.1f} seconds)")
        print(f"Output saved to: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error saving audiobook: {e}")
        return False

def main():
    """Main function with command line argument support."""
    parser = argparse.ArgumentParser(description="Create an audiobook using Chatterbox TTS")
    parser.add_argument("--document", "-d", default=DOCUMENT_PATH,
                       help="Path to the text document")
    parser.add_argument("--voice", "-v", default=VOICE_PROMPT_PATH,
                       help="Path to voice reference audio (optional)")
    parser.add_argument("--output", "-o", default=OUTPUT_PATH,
                       help="Path for the output audiobook")
    parser.add_argument("--exaggeration", "-e", type=float, default=0.5,
                       help="Emotion exaggeration (0.0-1.0, default: 0.5)")
    parser.add_argument("--cfg-weight", "-c", type=float, default=0.5,
                       help="CFG weight (0.0-1.0, default: 0.5)")
    parser.add_argument("--device", default=DEVICE,
                       help="Device to use (cuda/cpu)")
    parser.add_argument("--no-voice", action="store_true",
                       help="Don't use voice reference (use default voice)")
    
    args = parser.parse_args()
    
    # Auto-detect example.wav if no voice specified and file exists
    voice_path = args.voice
    if not args.no_voice and not voice_path and os.path.exists("example.wav"):
        voice_path = "example.wav"
        print("🎤 Automatically detected and using example.wav as voice reference")
    elif args.no_voice:
        voice_path = None
    
    print("=== Chatterbox Audiobook Creator ===")
    print(f"Document: {args.document}")
    print(f"Voice reference: {voice_path if voice_path else 'Default voice'}")
    print(f"Output: {args.output}")
    print(f"Exaggeration: {args.exaggeration}")
    print(f"CFG Weight: {args.cfg_weight}")
    print(f"Device: {args.device}")
    print("=" * 35)
    
    success = create_audiobook(
        document_path=args.document,
        voice_prompt_path=voice_path,
        output_path=args.output,
        exaggeration=args.exaggeration,
        cfg_weight=args.cfg_weight,
        device=args.device
    )
    
    if success:
        print("\n✅ Audiobook creation completed successfully!")
    else:
        print("\n❌ Audiobook creation failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
