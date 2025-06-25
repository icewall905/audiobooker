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
VERSION = "0.0.2"
DOCUMENT_PATH = "sample_document.txt" 
VOICE_PROMPT_PATH = None  # Set to your voice reference file path if available
OUTPUT_PATH = "my_audiobook.wav" 
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MAX_CHUNK_LENGTH = 300

def detect_chapters(text: str) -> List[dict]:
    """Detect chapters in text and return structured data with pause information."""
    # Common chapter patterns
    chapter_patterns = [
        r'^\s*Chapter\s+\d+',
        r'^\s*CHAPTER\s+\d+',
        r'^\s*Ch\.\s*\d+',
        r'^\s*\d+\.\s*[A-Z]',
        r'^\s*Part\s+\d+',
        r'^\s*PART\s+\d+',
        r'^\s*Section\s+\d+',
        r'^\s*Book\s+\d+'
    ]
    
    lines = text.split('\n')
    chapter_indices = []
    
    for i, line in enumerate(lines):
        for pattern in chapter_patterns:
            if re.match(pattern, line.strip(), re.IGNORECASE):
                chapter_indices.append(i)
                break
    
    # If no chapters found, return the whole text as one chapter
    if not chapter_indices:
        return [{'text': text, 'is_chapter_title': False}]
    
    # Split text into sections with chapter information
    sections = []
    current_start = 0
    
    for chapter_idx in chapter_indices:
        # Add content before chapter (if any)
        if chapter_idx > current_start:
            pre_chapter_text = '\n'.join(lines[current_start:chapter_idx]).strip()
            if pre_chapter_text:
                sections.append({'text': pre_chapter_text, 'is_chapter_title': False})
        
        # Add chapter title line
        chapter_title = lines[chapter_idx].strip()
        if chapter_title:
            sections.append({'text': chapter_title, 'is_chapter_title': True})
        
        # Find the end of this chapter's content
        next_chapter_idx = None
        for next_idx in chapter_indices:
            if next_idx > chapter_idx:
                next_chapter_idx = next_idx
                break
        
        # Add chapter content
        content_start = chapter_idx + 1
        content_end = next_chapter_idx if next_chapter_idx else len(lines)
        
        if content_start < content_end:
            chapter_content = '\n'.join(lines[content_start:content_end]).strip()
            if chapter_content:
                sections.append({'text': chapter_content, 'is_chapter_title': False})
        
        current_start = next_chapter_idx if next_chapter_idx else len(lines)
    
    return sections

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
                   device: str = DEVICE,
                   chapter_pause: float = 1.0):
    """Create audiobook from document using Chatterbox TTS."""
    
    if not validate_inputs(document_path, voice_prompt_path):
        return False
    
    print(f"Using device: {device}")
    print(f"Voice reference: {'Yes' if voice_prompt_path else 'No (using default voice)'}")
    print(f"Chapter pause: {chapter_pause}s")

    # Initialize the Chatterbox model
    print("Loading ChatterboxTTS model...")
    try:
        model = ChatterboxTTS.from_pretrained(device=device)
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")
        return False

    # Load and process the document
    print(f"Loading document from {document_path}...")
    try:
        with open(document_path, 'r', encoding='utf-8') as f:
            full_text = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return False

    # Detect chapters and sections
    sections = detect_chapters(full_text)
    chapter_count = sum(1 for section in sections if section['is_chapter_title'])
    print(f"Detected {len(sections)} sections ({chapter_count} chapter titles)")

    # Process each section
    all_audio_chunks = []
    total_chunks = 0
    chapter_stats = []
    current_chapter = 0
    
    for section_idx, section_data in enumerate(sections):
        section_text = section_data['text']
        is_chapter_title = section_data['is_chapter_title']
        
        if is_chapter_title:
            current_chapter += 1
            print(f"\n🎯 Processing Chapter Title {current_chapter}: '{section_text[:50]}...'")
            
            # Add pause BEFORE chapter title (except for very first section)
            if section_idx > 0 and chapter_pause > 0:
                pause_samples = int(chapter_pause * model.sr)
                pause_audio = torch.zeros(pause_samples)
                all_audio_chunks.append(pause_audio)
                print(f"  Added {chapter_pause}s pause before chapter title")
            
            # Generate audio for chapter title
            try:
                if voice_prompt_path:
                    wav = model.generate(
                        section_text,
                        audio_prompt_path=voice_prompt_path,
                        exaggeration=exaggeration,
                        cfg_weight=cfg_weight
                    )
                else:
                    wav = model.generate(
                        section_text,
                        exaggeration=exaggeration,
                        cfg_weight=cfg_weight
                    )
                
                all_audio_chunks.append(wav.squeeze(0).cpu())
                print(f"  Generated audio for chapter title ({len(section_text)} chars)")
                
            except Exception as e:
                print(f"  Error generating audio for chapter title: {e}")
                continue
            
            # Add pause AFTER chapter title
            if chapter_pause > 0:
                pause_samples = int(chapter_pause * model.sr)
                pause_audio = torch.zeros(pause_samples)
                all_audio_chunks.append(pause_audio)
                print(f"  Added {chapter_pause}s pause after chapter title")
                
        else:
            # Regular content section
            print(f"\n--- Processing Content Section {section_idx + 1}/{len(sections)} ---")
            
            # Split section into chunks
            text_chunks = smart_text_split(section_text, max_length=MAX_CHUNK_LENGTH)
            total_chunks += len(text_chunks)
            print(f"Section split into {len(text_chunks)} chunks.")
            
            if not text_chunks:
                print(f"No text found in section.")
                continue

            # Synthesize each chunk in the section
            section_audio_chunks = []
            
            for i, chunk in enumerate(text_chunks, 1):
                print(f"  Chunk {i}/{len(text_chunks)} ({len(chunk)} chars)...")
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
                    
                    section_audio_chunks.append(wav.squeeze(0).cpu())
                    
                except Exception as e:
                    print(f"  Error generating audio for chunk {i}: {e}")
                    continue

            if section_audio_chunks:
                # Concatenate section audio
                section_audio = torch.cat(section_audio_chunks)
                all_audio_chunks.append(section_audio)
                
                # Calculate section statistics
                section_duration = len(section_audio) / model.sr
                chapter_stats.append({
                    'section': section_idx + 1,
                    'is_chapter_title': is_chapter_title,
                    'chunks': len(text_chunks),
                    'duration': section_duration,
                    'chars': len(section_text)
                })
                
                print(f"Section complete: {section_duration:.1f}s")

    # Final concatenation and save
    if not all_audio_chunks:
        print("No audio was generated. Exiting.")
        return False

    print("\nConcatenating all audio...")
    try:
        full_audio = torch.cat(all_audio_chunks)
        
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        print(f"Saving final audiobook to {output_path} with sample rate {model.sr} Hz...")
        ta.save(output_path, full_audio.unsqueeze(0), model.sr)
        
        # Print detailed statistics
        total_duration = len(full_audio) / model.sr
        total_minutes = total_duration / 60
        total_chars = sum(stat['chars'] for stat in chapter_stats)
        
        print(f"\n✅ Audiobook creation complete! (v{VERSION})")
        print(f"📊 Statistics:")
        print(f"   Total sections: {len(sections)}")
        print(f"   Chapter titles: {chapter_count}")
        print(f"   Total chunks: {total_chunks}")
        print(f"   Total characters: {total_chars:,}")
        print(f"   Total duration: {total_minutes:.1f} minutes ({total_duration:.1f} seconds)")
        print(f"   Average speaking rate: {total_chars / total_duration:.1f} chars/second")
        print(f"   Output file: {output_path}")
        
        if chapter_count > 0:
            print(f"\n📖 Section breakdown:")
            for stat in chapter_stats:
                section_type = "Chapter Title" if stat['is_chapter_title'] else "Content"
                print(f"   Section {stat['section']} ({section_type}): {stat['duration']:.1f}s ({stat['chunks']} chunks, {stat['chars']:,} chars)")
        
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
    parser.add_argument("--chapter-pause", type=float, default=1.0,
                       help="Pause duration between chapters in seconds (default: 1.0)")
    
    args = parser.parse_args()
    
    # Auto-detect example.wav if no voice specified and file exists
    voice_path = args.voice
    if not args.no_voice and not voice_path and os.path.exists("example.wav"):
        voice_path = "example.wav"
        print("🎤 Automatically detected and using example.wav as voice reference")
    elif args.no_voice:
        voice_path = None
    
    print(f"=== Chatterbox Audiobook Creator v{VERSION} ===")
    print(f"Document: {args.document}")
    print(f"Voice reference: {voice_path if voice_path else 'Default voice'}")
    print(f"Output: {args.output}")
    print(f"Exaggeration: {args.exaggeration}")
    print(f"CFG Weight: {args.cfg_weight}")
    print(f"Device: {args.device}")
    print(f"Chapter pause: {args.chapter_pause}s")
    print("=" * 50)
    
    success = create_audiobook(
        document_path=args.document,
        voice_prompt_path=voice_path,
        output_path=args.output,
        exaggeration=args.exaggeration,
        cfg_weight=args.cfg_weight,
        device=args.device,
        chapter_pause=args.chapter_pause
    )
    
    if success:
        print("\n✅ Audiobook creation completed successfully!")
    else:
        print("\n❌ Audiobook creation failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
