# Audiobook Creator with Chatterbox TTS

A robust, production-ready Python application for generating high-quality audiobooks from text documents using Resemble AI's Chatterbox TTS model. Optimized for Ubuntu servers with NVIDIA GPU acceleration.

## Quick Start

### All-in-One Setup (Recommended)

```bash
# One-command setup and activation - handles everything automatically
./start.sh

# After setup, you can run directly:
python app.py --document my_book.txt
```

### Ubuntu Server Setup (Alternative)

```bash
# One-command setup - creates everything you need in current directory
curl -sSL https://raw.githubusercontent.com/icewall905/audiobooker/main/setup_ubuntu.sh | bash

# After setup, use anywhere:
audiobook --document my_book.txt --voice narrator.wav
```

### Manual Setup

```bash
# Clone the repository
git clone https://github.com/icewall905/audiobooker.git
cd audiobooker

# Run all-in-one setup
./start.sh

# Or run quick setup
./quick_setup.sh

# Activate environment and use
source audiobooker-env/bin/activate
python app.py --document my_book.txt
```

## Features

- 🎯 **Smart Text Processing**: Intelligent sentence-boundary splitting with chapter detection
- 🎤 **Voice Consistency**: Maintains natural voice throughout entire audiobooks
- 🌐 **Web Interface**: Easy-to-use browser-based interface with drag-and-drop
- 🚀 **GPU Acceleration**: CUDA optimization for faster generation
- 📖 **Chapter Detection**: Automatic chapter detection with configurable pauses
- 🔧 **Configurable**: Adjustable voice parameters and quality settings
- 📊 **Progress Tracking**: Real-time generation progress updates
- 🛠️ **Production Ready**: Comprehensive error handling and logging
- 📖 **Multiple Workflows**: Both local and remote API support
- 📁 **Chapter Splitting**: Split each chapter into separate files for easier management
- 🎵 **MP3 Conversion**: Convert output to MP3 format for better compatibility
- ⏸️ **Paragraph Pauses**: Automatic 1-second pauses between paragraphs for natural flow

## Usage Options

### 🚀 All-in-One (Easiest)
```bash
./start.sh
# Then run: python app.py --document my_book.txt
```

### 🌐 Web Interface
```bash
./start_web.sh
# Open http://localhost:7860 in your browser
```

### 💻 Command Line
```bash
# After running ./start.sh, use:
python app.py --document my_book.txt --voice narrator.wav
```

## Documentation

- [Ubuntu Setup Guide](UBUNTU_SETUP.md) - Complete installation instructions
- [Usage Guide](README_USAGE.md) - Detailed usage examples and options
- [Web Interface Guide](README_WEB.md) - Browser-based interface documentation
- [Remote API Guide](README_REMOTE.md) - Using with remote TTS services
- [Chapter Splitting Guide](README_CHAPTER_SPLITTING.md) - Chapter splitting and MP3 conversion features
- [Project Summary](PROJECT_SUMMARY.md) - Technical overview and architecture

## Quick Examples

```bash
# Easy start with guided interface
./start.sh

# Basic audiobook generation (default: split chapters + MP3)
python app.py --document book.txt

# With custom voice and settings
python app.py --document novel.txt --voice speaker.wav --exaggeration 1.2 --cfg-weight 1.0

# Auto voice detection (place 'example.wav' in project directory)
python app.py --document story.txt  # Automatically uses example.wav if found

# Using global launcher (after Ubuntu setup)
audiobook --document story.txt --voice narrator.wav --output output/my_audiobook.wav

# Single file output (disable chapter splitting)
python app.py --document book.txt --no-split-chapters

# WAV format only (disable MP3 conversion)
python app.py --document book.txt --no-mp3

# Legacy behavior (single WAV file)
python app.py --document book.txt --no-split-chapters --no-mp3
```

## Requirements

- Ubuntu 18.04+ (recommended)
- Python 3.8+
- NVIDIA GPU with CUDA support (recommended)
- 8GB+ RAM
- 10GB+ free disk space
- ffmpeg (for MP3 conversion - optional)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Repository

**GitHub**: https://github.com/icewall905/audiobooker