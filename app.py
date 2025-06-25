import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS
import re # Using regex for simple paragraph splitting
import os
import sys
from pathlib import Path
import argparse
from typing import List, Optional

# --- Configuration ---
# Path to your document 
DOCUMENT_PATH = "sample_document.txt" 
# Path to a high-quality audio file to use as the voice prompt
# This is CRITICAL for voice consistency across the whole audiobook
VOICE_PROMPT_PATH = None  # Set to your voice reference file path if available
# Path for the final output audiobook
OUTPUT_PATH = "my_audiobook.wav" 
# Set the device, as shown in the project's examples
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Maximum characters per chunk to avoid memory issues
# The generate() function works best with shorter chunks (around 300 chars)
MAX_CHUNK_LENGTH = 300

def smart_text_split(text: str, max_length: int = MAX_CHUNK_LENGTH) -> List[dict]:
    """
    Intelligently split text into chunks, respecting sentence boundaries
    and keeping chunks under the specified length. Returns list of dicts
    with 'text' and 'is_chapter_start' keys.
    """
    # First split by paragraphs
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    
    # Pattern to detect chapter starts (case insensitive)
    chapter_pattern = re.compile(r'^\s*(chapter\s+\d+|chapter\s+[ivxlcdm]+)\s*[:.]?\s*', re.IGNORECASE)
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        
        # Check if this paragraph starts a new chapter
        is_chapter_start = bool(chapter_pattern.match(paragraph))
            
        # If paragraph is short enough, use it as-is
        if len(paragraph) <= max_length:
            chunks.append({
                'text': paragraph,
                'is_chapter_start': is_chapter_start
            })
        else:
            # Split long paragraphs by sentences
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            current_chunk = ""
            first_chunk = True
            
            for sentence in sentences:
                # If adding this sentence would exceed max_length, save current chunk
                if current_chunk and len(current_chunk + " " + sentence) > max_length:
                    chunks.append({
                        'text': current_chunk.strip(),
                        'is_chapter_start': is_chapter_start and first_chunk
                    })
                    current_chunk = sentence
                    first_chunk = False
                else:
                    current_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            # Add any remaining text
            if current_chunk.strip():
                chunks.append({
                    'text': current_chunk.strip(),
                    'is_chapter_start': is_chapter_start and first_chunk
                })
    
    return chunks

def create_silence(duration_seconds: float, sample_rate: int = 24000) -> torch.Tensor:
    """
    Create a tensor of silence with the specified duration.
    
    Args:
        duration_seconds: Duration of silence in seconds
        sample_rate: Sample rate in Hz (default: 24000 for ChatterboxTTS)
    
    Returns:
        Tensor of zeros representing silence
    """
    num_samples = int(duration_seconds * sample_rate)
    return torch.zeros(num_samples)

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
                   device: str = DEVICE,
                   chapter_pause_seconds: float = 2.0):
    """
    Loads a document, splits it into paragraphs, synthesizes each paragraph
    to audio using a consistent voice, and combines them into a single file.
    
    Args:
        document_path: Path to the text document
        voice_prompt_path: Path to reference audio for voice cloning (optional)
        output_path: Path for the final audiobook
        exaggeration: Emotion exaggeration control (0.0-1.0)
        cfg_weight: CFG weight for generation quality (0.0-1.0)
        device: Device to use for inference
        chapter_pause_seconds: Extra pause duration before new chapters (default: 2.0)
    """
    # Validate inputs
    if not validate_inputs(document_path, voice_prompt_path):
        return False
    
    print(f"Using device: {device}")
    print(f"Voice reference: {'Yes' if voice_prompt_path else 'No (using default voice)'}")

    # 1. Initialize the Chatterbox model
    print("Loading ChatterboxTTS model...")
    try:
        model = ChatterboxTTS.from_pretrained(device=device)
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")
        return False

    # 2. Load and chunk the document
    print(f"Loading document from {document_path}...")
    try:
        with open(document_path, 'r', encoding='utf-8') as f:
            full_text = f.read()
    except FileNotFoundError:
        print(f"Error: The file {document_path} was not found.")
        return False
    except Exception as e:
        print(f"Error reading file: {e}")
        return False

    # Use smart text splitting for better natural breaks
    text_chunks = smart_text_split(full_text, max_length=MAX_CHUNK_LENGTH)
    print(f"Document split into {len(text_chunks)} chunks.")
    
    # Count chapters for better progress reporting
    chapter_count = sum(1 for chunk in text_chunks if chunk['is_chapter_start'])
    if chapter_count > 0:
        print(f"Detected {chapter_count} chapters with {chapter_pause_seconds}s pauses between them.")
    
    if not text_chunks:
        print("No text found in document.")
        return False

    # 3. Synthesize each chunk and collect the audio
    audio_chunks = []
    print("Starting audio generation for each chunk...")
    
    for i, chunk_data in enumerate(text_chunks, 1):
        chunk_text = chunk_data['text']
        is_chapter_start = chunk_data['is_chapter_start']
        
        # Add chapter pause before new chapters (except the very first chunk)
        if is_chapter_start and i > 1:
            print(f"Adding {chapter_pause_seconds}s chapter pause...")
            chapter_silence = create_silence(chapter_pause_seconds, sample_rate=24000)
            audio_chunks.append(chapter_silence)
        
        print(f"Generating audio for chunk {i}/{len(text_chunks)} ({len(chunk_text)} chars){'[CHAPTER START]' if is_chapter_start else ''}...")
        try:
            # *** CRITICAL: Use the SAME voice_prompt_path for every chunk ***
            # This ensures voice consistency throughout the audiobook
            
            # The core API call - model.generate() returns a PyTorch tensor
            if voice_prompt_path:
                # With voice cloning
                wav = model.generate(
                    chunk_text,
                    audio_prompt_path=voice_prompt_path,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight
                )
            else:
                # With default voice
                wav = model.generate(
                    chunk_text,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight
                )
            
            # Collect the tensor (move to CPU and remove batch dimension)
            audio_chunks.append(wav.squeeze(0).cpu())
            
        except Exception as e:
            print(f"Error generating audio for chunk {i}: {e}")
            print(f"Chunk content preview: {chunk_text[:100]}...")
            # Continue with next chunk instead of failing completely
            continue

    # 4. Concatenate and save the final audiobook
    if not audio_chunks:
        print("No audio was generated. Exiting.")
        return False

    print("Concatenating audio chunks...")
    try:
        full_audio = torch.cat(audio_chunks)
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # The sample rate `model.sr` is defined in the ChatterboxTTS class
        # and confirmed to be 24000Hz from S3GEN_SR
        print(f"Saving final audiobook to {output_path} with sample rate {model.sr} Hz...")
        ta.save(output_path, full_audio.unsqueeze(0), model.sr)
        
        # Calculate and display duration
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
    parser.add_argument("--chapter-pause", "-p", type=float, default=2.0,
                       help="Extra pause in seconds before new chapters (default: 2.0)")
    parser.add_argument("--device", default=DEVICE,
                       help="Device to use (cuda/cpu)")
    parser.add_argument("--no-voice", action="store_true",
                       help="Don't use voice reference (use default voice)")
    
    args = parser.parse_args()
    
    # Handle no-voice flag
    voice_path = None if args.no_voice else args.voice
    
    print("=== Chatterbox Audiobook Creator ===")
    print(f"Document: {args.document}")
    print(f"Voice reference: {voice_path if voice_path else 'Default voice'}")
    print(f"Output: {args.output}")
    print(f"Exaggeration: {args.exaggeration}")
    print(f"CFG Weight: {args.cfg_weight}")
    print(f"Chapter pause: {args.chapter_pause}s")
    print(f"Device: {args.device}")
    print("=" * 35)
    
    success = create_audiobook(
        document_path=args.document,
        voice_prompt_path=voice_path,
        output_path=args.output,
        exaggeration=args.exaggeration,
        cfg_weight=args.cfg_weight,
        device=args.device,
        chapter_pause_seconds=args.chapter_pause
    )
    
    if success:
        print("\n✅ Audiobook creation completed successfully!")
    else:
        print("\n❌ Audiobook creation failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()