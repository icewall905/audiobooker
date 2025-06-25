# Audiobook Creator with Chatterbox TTS

A robust, production-ready Python application for generating high-quality audiobooks from text documents using Resemble AI's Chatterbox TTS model. Optimized for Ubuntu servers with NVIDIA GPU acceleration.

## Quick Start

### Ubuntu Server Setup (Recommended)

```bash
# One-command setup - creates everything you need
curl -sSL https://raw.githubusercontent.com/icewall905/audiobooker/main/setup_ubuntu.sh | bash

# After setup, use anywhere:
audiobook --document my_book.txt --voice narrator.wav
```

### Manual Setup

```bash
# Clone the repository
git clone https://github.com/icewall905/audiobooker.git
cd audiobooker

# Run quick setup
./quick_setup.sh

# Activate environment and use
source audiobooker-env/bin/activate
python app.py --document my_book.txt
```

## Features

- 🎯 **Smart Text Processing**: Intelligent sentence-boundary splitting
- 🎤 **Voice Consistency**: Maintains natural voice throughout entire audiobooks
- 🚀 **GPU Acceleration**: CUDA optimization for faster generation
- 🔧 **Configurable**: Adjustable voice parameters and quality settings
- 📊 **Progress Tracking**: Real-time generation progress updates
- 🛠️ **Production Ready**: Comprehensive error handling and logging
- 📖 **Multiple Workflows**: Both local and remote API support

## Documentation

- [Ubuntu Setup Guide](UBUNTU_SETUP.md) - Complete installation instructions
- [Usage Guide](README_USAGE.md) - Detailed usage examples and options
- [Remote API Guide](README_REMOTE.md) - Using with remote TTS services
- [Project Summary](PROJECT_SUMMARY.md) - Technical overview and architecture

## Quick Examples

```bash
# Basic audiobook generation
python app.py --document book.txt

# With custom voice and settings
python app.py --document novel.txt --voice speaker.wav --exaggeration 1.2 --cfg-weight 1.0

# Auto voice detection (place 'example.wav' in project directory)
python app.py --document story.txt  # Automatically uses example.wav if found

# Using global launcher (after Ubuntu setup)
audiobook --document story.txt --voice narrator.wav --output my_audiobook.wav
```

## Requirements

- Ubuntu 18.04+ (recommended)
- Python 3.8+
- NVIDIA GPU with CUDA support (recommended)
- 8GB+ RAM
- 10GB+ free disk space

## License

MIT License - see [LICENSE](LICENSE) for details.

## Repository

**GitHub**: https://github.com/icewall905/audiobooker