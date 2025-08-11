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
import configparser

# --- Configuration ---
# Prefer config/env over hardcoded defaults
DEFAULT_SERVER_URL = "http://10.0.10.23:7860"
CONFIG_PATHS = [
    Path.cwd() / "audiobooker.conf",
    Path.home() / ".config/audiobooker/audiobooker.conf",
    Path("/etc/audiobooker/audiobooker.conf"),
]

def _load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    for p in CONFIG_PATHS:
        try:
            if p.exists():
                cfg.read(p)
                break
        except Exception:
            # Ignore malformed configs and fall through to defaults
            pass
    return cfg

CONFIG = _load_config()

def resolve_server_url(cli_server: Optional[str] = None) -> str:
    """Resolve server URL from CLI > env > config > default."""
    if cli_server:
        return cli_server
    env_val = os.getenv("CHATTERBOX_SERVER_URL")
    if env_val:
        return env_val
    cfg_val = CONFIG.get("server", "url", fallback=None)
    if cfg_val:
        return cfg_val
    return DEFAULT_SERVER_URL

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
    
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.gradio_predict_endpoint = f"{server_url}/api/predict"
        
    def check_server_health(self) -> bool:
        """Check if the Chatterbox server is accessible."""
        try:
            response = requests.get(f"{self.server_url}/", timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def discover_api_endpoints(self) -> Dict[str, Any]:
        """Try to discover available API endpoints on the server."""
        endpoints = {}
        
        # Common Gradio API endpoints to try
        test_endpoints = [
            "/api/predict",
            "/api/queue/join",
            "/queue/join", 
            "/run/predict",
            "/run/generate",
            "/call/generate",
            "/gradio_api",
            "/config"
        ]
        
        print(f"  Discovering API endpoints on {self.server_url}...")
        
        for endpoint in test_endpoints:
            try:
                url = f"{self.server_url}{endpoint}"
                response = requests.get(url, timeout=5)
                endpoints[endpoint] = {
                    "status": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                    "size": len(response.content)
                }
                if response.status_code == 200:
                    print(f"  ✅ {endpoint} - {response.status_code}")
                elif response.status_code in [404, 405]:
                    print(f"  ❌ {endpoint} - {response.status_code}")
                else:
                    print(f"  ⚠️  {endpoint} - {response.status_code}")
            except Exception as e:
                endpoints[endpoint] = {"error": str(e)}
                print(f"  ❌ {endpoint} - Error: {e}")
        
        # Try to get Gradio config which often reveals the correct API structure
        try:
            config_response = requests.get(f"{self.server_url}/config", timeout=10)
            if config_response.status_code == 200:
                config_data = config_response.json()
                endpoints["/config"] = config_data
                print(f"  📋 Config data available - {len(str(config_data))} chars")
                
                # Look for API info in config
                if "dependencies" in config_data:
                    print(f"  📋 Found {len(config_data['dependencies'])} dependencies in config")
                    for i, dep in enumerate(config_data["dependencies"]):
                        if "api_name" in dep:
                            api_name = dep.get('api_name')
                            targets = dep.get('targets', [])
                            print(f"    API {i}: {api_name} (targets: {targets})")
                            
                            # Store the generate API info for later use
                            if api_name == "generate":
                                endpoints["_generate_api"] = {
                                    "api_name": api_name,
                                    "targets": targets,
                                    "dependency_index": i
                                }
                                
                # Try to find the actual working endpoint patterns
                print(f"  🔍 Attempting to discover working endpoints...")
                test_post_endpoints = [
                    "/api/predict",
                    f"/api/predict/{endpoints.get('_generate_api', {}).get('dependency_index', 1)}",
                    "/run/predict", 
                    "/call/generate",
                    "/api/v1/predict",
                    "/gradio_api/call/generate",
                    "/predict"
                ]
                
                for endpoint in test_post_endpoints:
                    try:
                        # Use the correct 7-parameter format for testing
                        test_data = {
                            "data": [
                                None,  # State object
                                "test",  # Input text
                                None,  # Voice prompt file
                                0.5,   # Exaggeration parameter
                                0.8,   # Temperature parameter
                                0,     # Random seed
                                0.5    # CFG weight parameter
                            ],
                            "fn_index": endpoints.get('_generate_api', {}).get('dependency_index', 1)
                        }
                        url = f"{self.server_url}{endpoint}"
                        response = requests.post(url, json=test_data, timeout=10)
                        
                        if response.status_code != 404:
                            endpoints[f"POST_{endpoint}"] = {
                                "status": response.status_code,
                                "content_type": response.headers.get("content-type", ""),
                                "size": len(response.content)
                            }
                            if response.status_code in [200, 422]:  # 422 might mean wrong data format but endpoint exists
                                print(f"  🎯 POST {endpoint} - {response.status_code} (potential working endpoint!)")
                            else:
                                print(f"  ⚠️  POST {endpoint} - {response.status_code}")
                    except Exception as e:
                        continue
                        
        except Exception as e:
            print(f"  ❌ Config endpoint failed: {e}")
        
        return endpoints
    
    def generate_audio_gradio_v2(self, text: str, voice_prompt_path: Optional[str] = None, 
                                exaggeration: float = 0.5, cfg_weight: float = 0.5,
                                temperature: float = 0.8, seed: int = 0) -> bytes:
        """
        Generate audio using the correct Gradio API format discovered from /config.
        Uses the working /gradio_api/call/generate endpoint with proper data formatting.
        """
        # For now, skip voice cloning due to API complexity
        if voice_prompt_path:
            print(f"Note: Voice cloning not yet supported via remote API. Using default voice.")
        
        # Try the queue/join approach first for better compatibility
        try:
            return self._generate_with_queue_join(text, voice_prompt_path, exaggeration, cfg_weight, temperature, seed)
        except Exception as queue_error:
            print(f"  Queue join method failed: {queue_error}")
            print(f"  Trying direct call method...")
            
            # Fallback to direct call method
            return self._generate_with_direct_call(text, voice_prompt_path, exaggeration, cfg_weight, temperature, seed)
    
    def _generate_with_queue_join(self, text: str, voice_prompt_path: Optional[str] = None, 
                                 exaggeration: float = 0.5, cfg_weight: float = 0.5,
                                 temperature: float = 0.8, seed: int = 0) -> bytes:
        """Generate audio using Gradio's queue/join mechanism."""
        
        # Step 1: Join the queue
        join_url = f"{self.server_url}/queue/join"
        
        join_data = {
            "data": [
                None,  # State object
                text,  # Input text
                None,  # Voice prompt file
                exaggeration,  # Exaggeration parameter
                temperature,  # Temperature parameter
                seed,  # Random seed
                cfg_weight  # CFG weight parameter
            ],
            "event_data": None,
            "fn_index": 12,
            "trigger_id": None,
            "session_hash": None
        }
        
        print(f"  Joining queue at: {join_url}")
        join_response = requests.post(join_url, json=join_data, timeout=30)
        
        if join_response.status_code == 404:
            raise Exception("Queue join endpoint not available")
        
        join_response.raise_for_status()
        join_result = join_response.json()
        
        if 'event_id' not in join_result:
            raise Exception(f"No event_id in queue join response: {join_result}")
        
        event_id = join_result['event_id']
        print(f"  Joined queue with event_id: {event_id}")
        
        # Step 2: Stream results using the event_id
        return self._stream_queue_results(event_id)
    
    def _generate_with_direct_call(self, text: str, voice_prompt_path: Optional[str] = None, 
                                  exaggeration: float = 0.5, cfg_weight: float = 0.5,
                                  temperature: float = 0.8, seed: int = 0) -> bytes:
        """Generate audio using direct API call method."""
        
        api_endpoint = f"{self.server_url}/gradio_api/call/generate"
        
        # Prepare the data payload in the correct Gradio format
        data = {
            "data": [
                None,  # State object
                text,  # Input text
                None,  # Voice prompt file
                exaggeration,  # Exaggeration parameter
                temperature,  # Temperature parameter
                seed,  # Random seed
                cfg_weight  # CFG weight parameter
            ],
            "event_data": None,
            "fn_index": 12,
            "trigger_id": None
        }
        
        print(f"  Sending direct call to: {api_endpoint}")
        response = requests.post(api_endpoint, json=data, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        print(f"  Direct call response received")
        
        # Handle streaming response with event_id
        if 'event_id' in result:
            event_id = result['event_id']
            print(f"  Got event_id: {event_id}, streaming results...")
            return self._stream_queue_results(event_id)
        
        # Check if we got direct data
        elif 'data' in result and result['data']:
            return self._extract_audio_from_response(result['data'])
        
        raise Exception(f"No audio data or event_id found in response: {result}")
    
    def _stream_queue_results(self, event_id: str, max_wait: int = 180) -> bytes:
        """Stream results from Gradio queue using the correct event_id endpoint."""
        
        # Use the correct endpoint pattern we discovered
        event_url = f"{self.server_url}/gradio_api/call/generate/{event_id}"
        
        start_time = time.time()
        
        print(f"  🔄 Polling event endpoint: {event_url}")
        
        # Be much more patient with initial wait - TTS takes time
        print(f"  ⏳ Initial wait for TTS processing (15s)...")
        time.sleep(15)  # Give the server time to actually process before polling
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(event_url, timeout=15)
                
                if response.status_code == 200:
                    # This endpoint returns Server-Sent Events format
                    content = response.text
                    
                    # Look for the completion event
                    if 'event: complete' in content and 'data: [' in content:
                        print(f"  ✅ Got completion event")
                        
                        # Extract the JSON data from the SSE format
                        lines = content.split('\n')
                        for line in lines:
                            if line.startswith('data: ['):
                                try:
                                    # Parse the JSON data
                                    data_str = line[6:]  # Remove 'data: ' prefix
                                    data = json.loads(data_str)
                                    
                                    # Extract file URL from the response
                                    if data and len(data) > 0 and 'url' in data[0]:
                                        file_url = data[0]['url']
                                        print(f"  📥 Downloading audio from: {file_url}")
                                        
                                        # Download the audio file
                                        file_response = requests.get(file_url, timeout=30)
                                        file_response.raise_for_status()
                                        
                                        print(f"  ✅ Downloaded {len(file_response.content)} bytes")
                                        return file_response.content
                                    
                                except json.JSONDecodeError as e:
                                    print(f"  ❌ JSON decode error: {e}")
                                    continue
                    
                    # Look for progress or other status updates
                    elif 'event:' in content:
                        # Extract event type for progress reporting
                        lines = content.split('\n')
                        for line in lines:
                            if line.startswith('event: '):
                                event_type = line[7:].strip()
                                if event_type not in ['heartbeat', 'ping']:
                                    print(f"  ⏳ Event: {event_type}")
                
                elif response.status_code == 404:
                    # Event not ready yet, continue polling
                    pass
                else:
                    print(f"  ⚠️ Unexpected status {response.status_code}: {response.text}")
                    
            except Exception as e:
                print(f"  ❌ Polling error: {e}")
            
            # Be much less aggressive with polling to avoid overwhelming server
            elapsed = int(time.time() - start_time)
            if elapsed % 15 == 0 and elapsed > 0:  # Print every 15 seconds
                print(f"  ⏳ Still waiting... ({elapsed}s)")
            
            time.sleep(8)  # Wait 8 seconds between polls instead of 2
        
        raise Exception(f"Timeout waiting for result after {max_wait}s")
    
    def _poll_fallback(self, event_id: str, max_wait: int, start_time: float) -> bytes:
        """Fallback polling method when SSE streaming fails."""
        
        # Try the most common Gradio polling patterns
        polling_endpoints = [
            f"/queue/data?session_hash={event_id}",
            f"/api/predict/{event_id}",
            f"/call/generate/{event_id}",
            f"/queue/status/{event_id}",
            f"/api/v1/prediction/{event_id}",
            f"/predictions/{event_id}",
            f"/results/{event_id}"
        ]
        
        # Also try file-based result checking
        file_endpoints = [
            f"/file/tmp/gradio/{event_id}.wav",
            f"/file/outputs/{event_id}.wav", 
            f"/file/{event_id}",
            f"/files/{event_id}",
            f"/download/{event_id}"
        ]
        
        while time.time() - start_time < max_wait:
            # First try polling endpoints for JSON responses
            for endpoint in polling_endpoints:
                try:
                    poll_url = f"{self.server_url}{endpoint}"
                    poll_response = requests.get(poll_url, timeout=10)
                    
                    if poll_response.status_code == 200:
                        try:
                            poll_result = poll_response.json()
                            
                            # Check for completion
                            if 'data' in poll_result and poll_result['data']:
                                print(f"  ✅ Got result from {endpoint}")
                                return self._extract_audio_from_response(poll_result['data'])
                            
                            # Check for error status
                            if 'error' in poll_result:
                                raise Exception(f"Server error: {poll_result['error']}")
                                
                        except json.JSONDecodeError:
                            # Some endpoints might return non-JSON data
                            if len(poll_response.content) > 100:
                                print(f"  ✅ Got binary result from {endpoint}")
                                return poll_response.content
                                
                except Exception:
                    continue  # Try next endpoint
            
            # Try file endpoints for direct file downloads
            for endpoint in file_endpoints:
                try:
                    file_url = f"{self.server_url}{endpoint}"
                    file_response = requests.get(file_url, timeout=10)
                    
                    if file_response.status_code == 200:
                        # Check if it's actually audio content
                        content_type = file_response.headers.get('content-type', '')
                        if ('audio' in content_type or 
                            'wav' in content_type or 
                            len(file_response.content) > 1000):  # Reasonable audio file size
                            print(f"  ✅ Got audio file from {endpoint}")
                            return file_response.content
                            
                except Exception:
                    continue  # Try next endpoint
            
            # Wait before next poll
            time.sleep(3)
            print(f"  ⏳ Still polling... ({int(time.time() - start_time)}s)")
        
        raise Exception(f"Fallback polling timeout after {max_wait}s")
    
    def _extract_audio_from_response(self, output_data) -> bytes:
        """Extract audio data from various response formats."""
        
        # Look for audio data - could be various formats
        for item in output_data:
            if isinstance(item, dict):
                # Check for file reference
                if 'name' in item or 'path' in item:
                    file_path = item.get('name') or item.get('path')
                    file_url = f"{self.server_url}/file={file_path}"
                    
                    print(f"  Downloading audio from: {file_url}")
                    file_response = requests.get(file_url, timeout=30)
                    file_response.raise_for_status()
                    return file_response.content
                
                # Check for base64 data
                elif 'data' in item:
                    if item['data'].startswith('data:audio'):
                        # Base64 encoded audio
                        header, encoded = item['data'].split(',', 1)
                        return base64.b64decode(encoded)
            
            elif isinstance(item, str):
                # Direct file path or base64
                if item.startswith('data:audio'):
                    header, encoded = item.split(',', 1)
                    return base64.b64decode(encoded)
                elif item.startswith('/'):
                    # File path
                    file_url = f"{self.server_url}/file={item}"
                    print(f"  Downloading audio from: {file_url}")
                    file_response = requests.get(file_url, timeout=30)
                    file_response.raise_for_status()
                    return file_response.content
        
        raise Exception(f"No audio data found in response data: {output_data}")
    
    def generate_audio_gradio(self, text: str, voice_prompt_path: Optional[str] = None, 
                             exaggeration: float = 0.5, cfg_weight: float = 0.5,
                             temperature: float = 0.8, seed: int = 0) -> bytes:
        """
        Generate audio using simple Gradio API predict endpoint.
        This uses the basic prediction API that most Gradio apps support.
        """
        # For now, skip voice cloning due to API complexity
        if voice_prompt_path:
            print(f"Note: Voice cloning not yet supported via remote API. Using default voice.")
        
        # Prepare the data payload for basic Gradio predict
        # Most Gradio apps accept this simple format
        data = {
            "data": [
                text,  # Input text
                None,  # Voice prompt file (None for default voice)
                exaggeration,  # Exaggeration parameter
                temperature,  # Temperature parameter
                seed,  # Random seed
                cfg_weight  # CFG weight parameter
            ]
        }
        
        try:
            print(f"  Sending request to: {self.gradio_predict_endpoint}")
            
            # Call the simple predict API
            response = requests.post(self.gradio_predict_endpoint, json=data, timeout=120)
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            print(f"  Response status: success")
            
            # Check if we got direct data or need to download a file
            if 'data' in result and result['data']:
                output_data = result['data']
                
                # Look for audio data - could be various formats
                for item in output_data:
                    if isinstance(item, dict):
                        # Check for file reference
                        if 'name' in item or 'path' in item:
                            file_path = item.get('name') or item.get('path')
                            file_url = f"{self.server_url}/file={file_path}"
                            
                            print(f"  Downloading audio from: {file_url}")
                            file_response = requests.get(file_url, timeout=30)
                            file_response.raise_for_status()
                            return file_response.content
                        
                        # Check for base64 data
                        elif 'data' in item:
                            if item['data'].startswith('data:audio'):
                                # Base64 encoded audio
                                header, encoded = item['data'].split(',', 1)
                                return base64.b64decode(encoded)
                    
                    elif isinstance(item, str):
                        # Direct file path or base64
                        if item.startswith('data:audio'):
                            header, encoded = item.split(',', 1)
                            return base64.b64decode(encoded)
                        elif item.startswith('/'):
                            # File path
                            file_url = f"{self.server_url}/file={item}"
                            print(f"  Downloading audio from: {file_url}")
                            file_response = requests.get(file_url, timeout=30)
                            file_response.raise_for_status()
                            return file_response.content
            
            raise Exception(f"No audio data found in response: {result}")
            
        except requests.RequestException as e:
            raise Exception(f"API request failed: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {e}")
        except Exception as e:
            raise Exception(f"Unexpected error: {e}")
    
    def generate_audio(self, text: str, voice_prompt_path: Optional[str] = None,
                      exaggeration: float = 0.5, cfg_weight: float = 0.5) -> bytes:
        """
        Generate audio using the available API method.
        Tries the modern Gradio API format first, then falls back to legacy format.
        """
        try:
            # Try the v2 method first (uses correct endpoint from config)
            return self.generate_audio_gradio_v2(text, voice_prompt_path, exaggeration, cfg_weight)
        except Exception as e:
            print(f"  V2 API failed: {e}")
            print(f"  Falling back to legacy API...")
            
            try:
                # Fall back to the legacy method
                return self.generate_audio_gradio(text, voice_prompt_path, exaggeration, cfg_weight)
            except Exception as e2:
                raise Exception(f"Both API methods failed. V2: {e}, Legacy: {e2}")

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
                   server_url: Optional[str] = None):
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
    
    # Resolve server URL
    server_url = resolve_server_url(server_url)
    
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
    
    # Discover available API endpoints
    endpoints = client.discover_api_endpoints()
    
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
    parser.add_argument("--server", "-s", default=None,
                       help="Chatterbox server URL (overrides config/env)")
    parser.add_argument("--no-voice", action="store_true",
                       help="Don't use voice reference (use default voice)")
    
    args = parser.parse_args()
    
    # Handle no-voice flag
    voice_path = None if args.no_voice else args.voice
    effective_server = resolve_server_url(args.server)
    
    print("=== Remote Chatterbox Audiobook Creator ===")
    print(f"Server: {effective_server}")
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
        server_url=effective_server
    )
    
    if success:
        print("\n✅ Audiobook creation completed successfully!")
    else:
        print("\n❌ Audiobook creation failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
