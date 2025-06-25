# Remote Audiobook Creator with Chatterbox TTS

This script creates natural-sounding audiobooks from text documents using a remote Chatterbox TTS server (running on a GPU-enabled system).

## Architecture

- **Local Machine**: Runs the audiobook creation script (minimal resources required)
- **Remote Server**: Hosts Chatterbox TTS with GPU acceleration (IP: 10.0.10.23:7860)
- **Communication**: HTTP API calls between local script and remote server

## Features

- **Remote Processing**: Leverages powerful GPU server for TTS generation
- **Smart Text Splitting**: Intelligently splits text at sentence boundaries
- **Voice Consistency**: Maintains consistent voice throughout the audiobook
- **Configurable Parameters**: Adjust exaggeration and CFG weight
- **Robust Error Handling**: Graceful recovery from network issues
- **Progress Tracking**: Real-time progress updates during generation
- **Minimal Dependencies**: Only requires `requests` and `numpy`

## Prerequisites

### Remote Server (10.0.10.23)
- Chatterbox TTS running in Docker container
- Accessible on port 7860
- GPU-enabled for fast processing

### Local Machine
- Python 3.7+
- Network access to remote server
- Minimal system requirements

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements_remote.txt
```

2. Verify server connectivity:
```bash
python test_remote.py
```

## Usage

### Basic Usage

```bash
python app_remote.py
```

This will use the default configuration:
- Server: `http://10.0.10.23:7860`
- Input: `sample_document.txt`
- Output: `my_audiobook.wav`
- Default voice (no voice cloning)

### Advanced Usage

```bash
python app_remote.py --document "path/to/your/book.txt" --voice "path/to/voice.wav" --output "my_audiobook.wav"
```

### Command Line Options

- `--document, -d`: Path to the text document to convert
- `--voice, -v`: Path to voice reference audio file (optional)
- `--output, -o`: Path for the output audiobook file
- `--exaggeration, -e`: Emotion exaggeration level (0.0-1.0, default: 0.5)
- `--cfg-weight, -c`: CFG weight for generation quality (0.0-1.0, default: 0.5)
- `--server, -s`: Chatterbox server URL (default: http://10.0.10.23:7860)
- `--no-voice`: Use default voice instead of voice reference

### Examples

1. **Basic audiobook with custom voice:**
```bash
python app_remote.py --document "novel.txt" --voice "narrator.wav"
```

2. **Expressive narration:**
```bash
python app_remote.py --document "drama.txt" --exaggeration 0.7 --cfg-weight 0.3
```

3. **Using default voice:**
```bash
python app_remote.py --document "book.txt" --no-voice
```

4. **Custom server:**
```bash
python app_remote.py --server "http://192.168.1.100:7860" --document "book.txt"
```

## API Communication

The script communicates with the remote Chatterbox server using HTTP API calls:

1. **Health Check**: Verifies server accessibility
2. **Audio Generation**: Sends text chunks and receives audio data
3. **Error Handling**: Retries and graceful degradation

### API Endpoints Used

- `GET /`: Health check
- `POST /api/predict`: Gradio API endpoint (primary)
- `POST /api/tts`: Direct TTS API (fallback)

## Voice Reference

For best results with voice cloning:
- Use a high-quality audio file (WAV format recommended)
- 10-30 seconds of clear speech
- Single speaker, minimal background noise
- Upload the voice file to your local machine (not the server)

## Performance

- **Network**: Minimal bandwidth required (text up, audio down)
- **Local CPU**: Very low usage (just API calls and file operations)
- **Remote GPU**: Handles all TTS processing
- **Latency**: Depends on network speed and server load

## Troubleshooting

### Connection Issues
```bash
# Test server connectivity
python test_remote.py

# Check if server is running
curl http://10.0.10.23:7860/

# Test with different server
python app_remote.py --server "http://your-server:port"
```

### Common Problems

1. **Server Not Accessible**
   - Check if Docker container is running
   - Verify network connectivity
   - Confirm port forwarding (7860)

2. **API Errors**
   - Server might be overloaded
   - Check server logs for errors
   - Try reducing chunk size

3. **Audio Quality Issues**
   - Experiment with different exaggeration values
   - Adjust cfg_weight for your voice style
   - Ensure voice reference file is high quality

4. **Memory Issues on Server**
   - Restart Docker container
   - Reduce concurrent requests
   - Check GPU memory usage

## Server Setup Reference

Your remote server setup:
```yaml
# docker-compose.yml
services:
  chatterbox:
    build: ./chatterbox
    ports:
      - "7860:7860"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## File Processing

- **Input**: Any UTF-8 text file
- **Output**: WAV format, 24kHz sample rate
- **Chunks**: Automatically split at sentence boundaries
- **Max Chunk Size**: 500 characters (configurable)

## Security Notes

- Server runs on local network (10.0.10.23)
- No authentication required for internal network
- Voice files are sent over HTTP (consider HTTPS for production)
- Generated audio includes watermarking for responsible AI use

## Testing

Run the test suite to verify everything works:
```bash
python test_remote.py
```

This will test:
- Server connectivity
- Text processing
- Single audio generation
- File validation
- All dependencies
