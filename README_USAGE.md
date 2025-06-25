# Audiobook Creator with Chatterbox TTS

This script creates natural-sounding audiobooks from text documents using Resemble AI's Chatterbox TTS model.

## Features

- **Smart Text Splitting**: Intelligently splits text at sentence boundaries while respecting maximum chunk sizes
- **Voice Consistency**: Maintains consistent voice throughout the entire audiobook
- **Configurable Parameters**: Adjust exaggeration and CFG weight for different speaking styles
- **Error Handling**: Robust error handling with graceful recovery
- **Progress Tracking**: Real-time progress updates during generation
- **Command Line Interface**: Easy-to-use CLI with multiple options

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure you have a CUDA-compatible GPU for faster processing (optional but recommended)

## Usage

### Basic Usage

```bash
python app.py
```

This will use the default configuration:
- Input: `my_document.txt`
- Voice reference: `voice_reference.wav`
- Output: `my_audiobook.wav`

### Advanced Usage

```bash
python app.py --document "path/to/your/book.txt" --voice "path/to/voice.wav" --output "my_audiobook.wav"
```

### Command Line Options

- `--document, -d`: Path to the text document to convert
- `--voice, -v`: Path to voice reference audio file (optional)
- `--output, -o`: Path for the output audiobook file
- `--exaggeration, -e`: Emotion exaggeration level (0.0-1.0, default: 0.5)
- `--cfg-weight, -c`: CFG weight for generation quality (0.0-1.0, default: 0.5)
- `--chapter-pause, -p`: Extra pause in seconds before new chapters (default: 2.0)
- `--device`: Device to use (cuda/cpu, auto-detected by default)
- `--no-voice`: Use default voice instead of voice reference

### Examples

1. **Basic audiobook with custom voice:**
```bash
python app.py --document "novel.txt" --voice "narrator.wav"
```

2. **Expressive narration:**
```bash
python app.py --document "drama.txt" --exaggeration 0.7 --cfg-weight 0.3
```

3. **Custom chapter pauses:**
```bash
python app.py --document "book.txt" --chapter-pause 3.0
```

4. **Using default voice:**
```bash
python app.py --document "book.txt" --no-voice
```

## Voice Reference

For best results with voice cloning:
- Use a high-quality audio file (WAV format recommended)
- 10-30 seconds of clear speech
- Single speaker
- Minimal background noise
- Representative of the desired speaking style

## Tips for Different Content Types

### General Use (TTS and Voice Agents)
- Default settings work well: `exaggeration=0.5, cfg_weight=0.5`
- For fast-speaking reference voices, try `cfg_weight=0.3`

### Expressive or Dramatic Speech
- Use lower cfg_weight: `cfg_weight=0.3`
- Increase exaggeration: `exaggeration=0.7` or higher
- Higher exaggeration speeds up speech; lower cfg_weight compensates with slower pacing

## File Requirements

- **Text Document**: Any UTF-8 encoded text file
- **Voice Reference** (optional): WAV, MP3, or other audio formats supported by librosa
- **Output**: Will be saved as WAV format with 24kHz sample rate

## Performance Notes

- GPU recommended for faster processing
- Processing time depends on document length and hardware
- Memory usage scales with document size
- Each chunk is processed sequentially to maintain voice consistency

## Troubleshooting

1. **Model Loading Issues**: Ensure you have sufficient GPU memory or use CPU
2. **File Not Found**: Check file paths and permissions
3. **Memory Errors**: Try reducing `MAX_CHUNK_LENGTH` in the script
4. **Quality Issues**: Experiment with different exaggeration and cfg_weight values

## Watermarking

All generated audio includes Resemble AI's Perth watermarking for responsible AI use. The watermarks are imperceptible but can be detected using the provided extraction methods in the Chatterbox documentation.
