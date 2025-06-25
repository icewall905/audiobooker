# Ubuntu Server Setup Guide

## Overview

You can run the audiobook creator **anywhere** on your Ubuntu server. Here are two setup options:

## Option 1: Full Automated Setup (Recommended)

This creates a complete standalone installation:

```bash
# Download and run the setup script
curl -sSL https://raw.githubusercontent.com/icewall905/audiobooker/main/setup_ubuntu.sh | bash

# Or if you have the repo:
cd audiobooker
./setup_ubuntu.sh
```

### What this does:
- ✅ Updates Ubuntu packages
- ✅ Installs system dependencies (Python, FFmpeg, etc.)
- ✅ Detects and configures GPU support
- ✅ Creates virtual environment (in current directory if repo exists, otherwise in `./audiobooker/`)
- ✅ Installs all Python dependencies
- ✅ Creates ready-to-use scripts
- ✅ Adds global launcher command
- ✅ Tests the installation

### After setup:
```bash
# Use the convenient start script (recommended for beginners)
./start.sh

# Use the global launcher (audiobook command now available globally)
audiobook --document my_book.txt --voice narrator.wav

# Or activate and use directly
# If you ran setup from the cloned repo directory:
source audiobooker-env/bin/activate
python app.py --document my_book.txt

# If you ran setup from an empty directory:
cd audiobooker
source audiobooker-env/bin/activate
python app.py --document my_book.txt
```

## Option 2: Quick Setup (If you have the repo)

If you already cloned this repository:

```bash
cd /path/to/your/audiobooker/repo
./quick_setup.sh
```

This creates a virtual environment in the current directory.

## Manual Setup

If you prefer manual control:

```bash
# 1. Install system dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg libsndfile1

# 2. Create virtual environment
python3 -m venv audiobooker-env
source audiobooker-env/bin/activate

# 3. Install Python packages
pip install --upgrade pip

# For GPU servers:
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

# For CPU-only:
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install Chatterbox TTS
pip install chatterbox-tts

# 4. Copy the app.py script to your directory
```

## Usage Examples

### Basic Usage
```bash
# Activate environment
source audiobooker-env/bin/activate

# Create audiobook with default voice
python app.py --document "my_book.txt"

# Create audiobook with voice cloning
python app.py --document "my_book.txt" --voice "narrator_voice.wav"

# Auto voice detection (place 'example.wav' in project directory)
python app.py --document "my_book.txt"  # Will automatically use example.wav if found
```

### Advanced Usage
```bash
# Expressive narration
python app.py --document "drama.txt" --exaggeration 0.7 --cfg-weight 0.3

# Custom chapter pauses (default is 1 second)
python app.py --document "book.txt" --chapter-pause 3.0

# Custom output location
python app.py --document "book.txt" --output "/path/to/audiobooks/my_book.wav"

# Check all options
python app.py --help
```

## File Requirements

### Input Document
- **Format**: Plain text file (.txt)
- **Encoding**: UTF-8
- **Size**: Any size (automatically chunked)
- **Location**: Anywhere accessible to the script

### Voice Reference (Optional)
- **Format**: WAV, MP3, or other audio formats
- **Length**: 10-30 seconds recommended
- **Quality**: High quality, single speaker, minimal background noise
- **Location**: Anywhere accessible to the script
- **Auto-detection**: Place a file named `example.wav` in the project directory for automatic voice detection

### Output
- **Format**: WAV file (24kHz sample rate)
- **Location**: Specified by `--output` parameter

## Directory Structure

After full setup:
- **If run from cloned repo**: Virtual environment and scripts are in the current directory
- **If run from empty directory**: Creates `./audiobooker/` subdirectory

```
# From cloned repo:
./
├── audiobooker-env/          # Virtual environment
├── app.py                    # Main audiobook creator (existing)
├── sample_document.txt       # Test document (existing)
├── start.sh                  # Convenient startup script (new)
├── audiobook                # Global launcher script (new)
└── example.wav              # Optional: Auto-detected voice reference

# From empty directory:
./audiobooker/
├── audiobooker-env/          # Virtual environment
├── app.py                    # Main audiobook creator
├── sample_document.txt       # Test document
├── audiobook                # Global launcher script
└── example.wav              # Optional: Auto-detected voice reference
```

## GPU Requirements

### Supported GPUs
- NVIDIA GPUs with CUDA support
- Minimum 4GB VRAM recommended
- Your RTX 3060 (12GB) is perfect!

### GPU Detection
The setup script automatically detects GPU and installs appropriate PyTorch version:
- **GPU found**: Installs CUDA-enabled PyTorch
- **No GPU**: Installs CPU-only version (much slower)

## Performance Tips

### Optimal Settings
- **General use**: `--exaggeration 0.5 --cfg-weight 0.5` (default)
- **Expressive**: `--exaggeration 0.7 --cfg-weight 0.3`
- **Fast speakers**: Lower `--cfg-weight` to ~0.3

### Processing Time
- **With GPU**: ~1-2 minutes per minute of final audio
- **CPU only**: ~10-20 minutes per minute of final audio

## Troubleshooting

### Common Issues

1. **CUDA not found**
   ```bash
   # Check GPU status
   nvidia-smi
   
   # Reinstall PyTorch with CUDA
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

2. **Audio file errors**
   ```bash
   # Install additional audio libraries
   sudo apt install -y ffmpeg libsndfile1 portaudio19-dev
   ```

3. **Memory errors**
   - Reduce chunk size in the script
   - Use smaller documents for testing
   - Close other GPU applications

4. **Permission errors**
   ```bash
   # Make sure you own the installation directory
   sudo chown -R $USER:$USER ./audiobooker
   ```

### Testing Installation
```bash
cd audiobooker  # In the directory where you ran setup
source audiobooker-env/bin/activate
python test_setup.py
```

## Integration with Existing Workflow

### With your current Docker setup
Your existing Gradio server (`10.0.10.23:7860`) can run alongside this setup:
- **Gradio**: For quick tests and manual generation
- **Script**: For batch processing and full audiobooks

### Automation
```bash
# Process multiple books
for book in *.txt; do
    python app.py --document "$book" --output "audiobooks/${book%.txt}.wav"
done
```

### Using Auto Voice Detection
To enable automatic voice detection, simply place a file named `example.wav` in your project directory:

```bash
# Copy your voice sample to the project directory
cp /path/to/your/voice_sample.wav ./audiobooker/example.wav

# Now any audiobook creation without --voice will automatically use example.wav
cd audiobooker
source audiobooker-env/bin/activate
python app.py --document book.txt  # Will automatically use example.wav
```

## Next Steps

1. **Run the setup script** on your Ubuntu server
2. **Test with sample document** to verify everything works
3. **Upload your documents and voice references**
4. **Start creating audiobooks!**

The setup is completely self-contained and won't interfere with your existing Chatterbox Docker setup.
