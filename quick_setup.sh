#!/bin/bash
# Quick setup for audiobook creator (if you already have the repo)

set -e

echo "=== Quick Audiobook Creator Setup ==="

# Create virtual environment
python3 -m venv audiobooker-env
source audiobooker-env/bin/activate

# Create python symlink if it doesn't exist
if [ ! -f "audiobooker-env/bin/python" ] && [ -f "audiobooker-env/bin/python3" ]; then
    echo "Creating python symlink..."
    ln -sf python3 audiobooker-env/bin/python
fi

# Install dependencies
pip install --upgrade pip

# Install PyTorch (with CUDA if available)
if command -v nvidia-smi &> /dev/null; then
    echo "Installing PyTorch with CUDA support..."
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
else
    echo "Installing PyTorch CPU version..."
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# Install Chatterbox TTS
pip install chatterbox-tts

echo ""
echo "✅ Setup complete!"
echo ""
echo "To use:"
echo "  source audiobooker-env/bin/activate"
echo "  python app.py --document your_book.txt"
echo ""
echo "Or use the startup script:"
echo "  ./start.sh"
echo ""
echo "Default behavior:"
echo "  • Splits chapters into separate files"
echo "  • Converts to MP3 format"
echo "  • Saves files in ./output/ directory"
