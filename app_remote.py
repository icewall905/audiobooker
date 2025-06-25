import requests
import base64
import re
import os
import sys
import json
import time
from pathlib import Path
import argparse
from typing import List, Optional, Dict, Any
import tempfile
import wave
import numpy as np

# --- Configuration ---
# Remote Chatterbox server configuration
CHATTERBOX_SERVER_URL = "http://10.0.10.23:7860"
CHATTERBOX_API_ENDPOINT = f"{CHATTERBOX_SERVER_URL}/api/tts"

# Path to your document (using sample document by default)
DOCUMENT_PATH = "sample_document.txt" 
# Path to a high-quality audio file to use as the voice prompt
# This is optional - if not provided, will use the default Chatterbox voice
VOICE_PROMPT_PATH = None  # Set to your voice reference file path if available
# Path for the final output audiobook
OUTPUT_PATH = "my_audiobook.wav" 

# Maximum characters per chunk to avoid memory issues
MAX_CHUNK_LENGTH = 500

class ChatterboxAPIClient:
    """Client for communicating with remote Chatterbox TTS server."""
    
    def __init__(self, server_url: str = CHATTERBOX_SERVER_URL):
        self.server_url = server_url
        self.gradio_call_endpoint = f"{server_url}/gradio_api/call/generate"
        self.gradio_status_endpoint = f"{server_url}/gradio_api/call/generate"
        
    def check_server_health(self) -> bool:
        """Check if the Chatterbox server is accessible."""
        try:
            response = requests.get(f"{self.server_url}/", timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def generate_audio_gradio(self, text: str, voice_prompt_path: Optional[str] = None, 
                             exaggeration: float = 0.5, cfg_weight: float = 0.5,
                             temperature: float = 0.8, seed: int = 0) -> bytes:
        """
        Generate audio using Gradio API endpoint.
        This uses the standard Gradio prediction API.
        """
        # Prepare the data payload for Gradio - based on the config analysis
        # The generate function expects: [state, text, audio_file, exaggeration, temperature, seed, cfg_weight]
        data = {
            "data": [
                None,  # state (will be managed by server)
                text,  # Input text
                voice_prompt_path,  # Voice prompt file path (can be None)
                exaggeration,  # Exaggeration parameter
                temperature,  # Temperature parameter
                seed,  # Random seed
                cfg_weight  # CFG weight parameter
            ]
        }
        
        try:
            # Call the Gradio API
            response = requests.post(self.gradio_call_endpoint, json=data, timeout=120)
            response.raise_for_status()
            
            # Get the event_id from the response
            result = response.json()
            event_id = result.get('event_id')
            
            if not event_id:
                raise Exception("No event_id received from server")
            
            # Poll for completion
            status_url = f"{self.server_url}/gradio_api/call/generate/{event_id}"
            
            # Wait for completion
            for _ in range(180):  # Wait up to 3 minutes
                time.sleep(1)
                status_response = requests.get(status_url, timeout=10)
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    
                    if status_data.get('msg') == 'process_completed':
                        # Get the output data
                        output_data = status_data.get('output', {}).get('data', [])
                        if output_data and len(output_data) > 0:
                            # The output should be a file reference
                            audio_info = output_data[0]
                            if isinstance(audio_info, dict) and 'path' in audio_info:
                                # Download the file
                                file_path = audio_info['path']
                                file_url = f"{self.server_url}/file={file_path}"
                                
                                file_response = requests.get(file_url, timeout=30)
                                file_response.raise_for_status()
                                return file_response.content
                            elif isinstance(audio_info, dict) and 'url' in audio_info:
                                # Direct URL
                                file_response = requests.get(audio_info['url'], timeout=30)
                                file_response.raise_for_status()
                                return file_response.content
                        
                        break
                    elif status_data.get('msg') == 'process_failed':
                        raise Exception(f"Server processing failed: {status_data.get('output')}")
            
            raise Exception("Timeout waiting for audio generation")
            
        except requests.RequestException as e:
            raise Exception(f"API request failed: {e}")
    
    def generate_audio(self, text: str, voice_prompt_path: Optional[str] = None,
                      exaggeration: float = 0.5, cfg_weight: float = 0.5) -> bytes:
        """
        Generate audio using the available API method.
        """
        try:
            return self.generate_audio_gradio(text, voice_prompt_path, exaggeration, cfg_weight)
        except Exception as e:
            raise Exception(f"Audio generation failed: {e}")

def smart_text_split(text: str, max_length: int = MAX_CHUNK_LENGTH) -> List[str]:
    """
    Intelligently split text into chunks, respecting sentence boundaries
    and keeping chunks under the specified length.
    """
    # First split by paragraphs
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # If paragraph is short enough, use it as-is
        if len(paragraph) <= max_length:
            chunks.append(paragraph)
        else:
            # Split long paragraphs by sentences
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            current_chunk = ""
            
            for sentence in sentences:
                # If adding this sentence would exceed max_length, save current chunk
                if current_chunk and len(current_chunk + " " + sentence) > max_length:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            # Add any remaining text
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

def save_audio_chunks_as_wav(audio_chunks: List[bytes], output_path: str, sample_rate: int = 24000):
    """
    Combine multiple audio chunks (as bytes) into a single WAV file.
    """
    combined_audio = []
    
    # Convert each audio chunk to numpy array and combine
    for chunk_bytes in audio_chunks:
        # Save chunk to temporary file and read as audio
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(chunk_bytes)
            temp_path = temp_file.name
        
        try:
            # Read the temporary WAV file
            with wave.open(temp_path, 'rb') as wav_file:
                frames = wav_file.readframes(wav_file.getnframes())
                audio_data = np.frombuffer(frames, dtype=np.int16)
                combined_audio.append(audio_data)
        finally:
            # Clean up temporary file
            os.unlink(temp_path)
    
    # Concatenate all audio data
    if combined_audio:
        full_audio = np.concatenate(combined_audio)
        
        # Save as WAV file
        with wave.open(output_path, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(full_audio.tobytes())
        
        return len(full_audio) / sample_rate  # Return duration in seconds
    
    return 0

def create_audiobook(document_path: str = DOCUMENT_PATH, 
                   voice_prompt_path: Optional[str] = VOICE_PROMPT_PATH,
                   output_path: str = OUTPUT_PATH,
                   exaggeration: float = 0.5,
                   cfg_weight: float = 0.5,
                   server_url: str = CHATTERBOX_SERVER_URL):
    """
    Loads a document, splits it into paragraphs, synthesizes each paragraph
    to audio using a remote Chatterbox server, and combines them into a single file.
    
    Args:
        document_path: Path to the text document
        voice_prompt_path: Path to reference audio for voice cloning (optional)
        output_path: Path for the final audiobook
        exaggeration: Emotion exaggeration control (0.0-1.0)
        cfg_weight: CFG weight for generation quality (0.0-1.0)
        server_url: URL of the remote Chatterbox server
    """
    # Validate inputs
    if not validate_inputs(document_path, voice_prompt_path):
        return False
    
    # Initialize API client
    client = ChatterboxAPIClient(server_url)
    
    # Check server health
    print(f"Checking connection to Chatterbox server at {server_url}...")
    if not client.check_server_health():
        print(f"❌ Cannot connect to Chatterbox server at {server_url}")
        print("Please ensure:")
        print("1. The server is running")
        print("2. The IP address and port are correct")
        print("3. Network connectivity is available")
        return False
    
    print(f"✅ Connected to Chatterbox server successfully")
    print(f"Voice reference: {'Yes' if voice_prompt_path else 'No (using default voice)'}")

    # Load and chunk the document
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
    text_chunks = smart_text_split(full_text)
    print(f"Document split into {len(text_chunks)} chunks.")
    
    if not text_chunks:
        print("No text found in document.")
        return False

    # Synthesize each chunk and collect the audio
    audio_chunks = []
    print("Starting audio generation for each chunk...")
    
    for i, chunk in enumerate(text_chunks, 1):
        print(f"Generating audio for chunk {i}/{len(text_chunks)} ({len(chunk)} chars)...")
        print(f"Preview: {chunk[:100]}{'...' if len(chunk) > 100 else ''}")
        
        try:
            # Generate audio via API
            audio_bytes = client.generate_audio(
                text=chunk,
                voice_prompt_path=voice_prompt_path,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight
            )
            
            audio_chunks.append(audio_bytes)
            print(f"✅ Chunk {i} generated successfully ({len(audio_bytes)} bytes)")
            
            # Small delay to avoid overwhelming the server
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Error generating audio for chunk {i}: {e}")
            print(f"Chunk content preview: {chunk[:100]}...")
            # Continue with next chunk instead of failing completely
            continue

    # Concatenate and save the final audiobook
    if not audio_chunks:
        print("No audio was generated. Exiting.")
        return False

    print("Concatenating audio chunks...")
    try:
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Combine audio chunks into single file
        duration_seconds = save_audio_chunks_as_wav(audio_chunks, output_path)
        
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
    parser = argparse.ArgumentParser(description="Create an audiobook using remote Chatterbox TTS")
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
    parser.add_argument("--server", "-s", default=CHATTERBOX_SERVER_URL,
                       help="Chatterbox server URL (default: http://10.0.10.23:7860)")
    parser.add_argument("--no-voice", action="store_true",
                       help="Don't use voice reference (use default voice)")
    
    args = parser.parse_args()
    
    # Handle no-voice flag
    voice_path = None if args.no_voice else args.voice
    
    print("=== Remote Chatterbox Audiobook Creator ===")
    print(f"Server: {args.server}")
    print(f"Document: {args.document}")
    print(f"Voice reference: {voice_path if voice_path else 'Default voice'}")
    print(f"Output: {args.output}")
    print(f"Exaggeration: {args.exaggeration}")
    print(f"CFG Weight: {args.cfg_weight}")
    print("=" * 45)
    
    success = create_audiobook(
        document_path=args.document,
        voice_prompt_path=voice_path,
        output_path=args.output,
        exaggeration=args.exaggeration,
        cfg_weight=args.cfg_weight,
        server_url=args.server
    )
    
    if success:
        print("\n✅ Audiobook creation completed successfully!")
    else:
        print("\n❌ Audiobook creation failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
