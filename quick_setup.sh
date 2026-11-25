#!/bin/bash
# Quick setup for an existing checkout: ./quick_setup.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/audiobooker-env"

echo "=== Quick Audiobook Creator Setup ==="

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip setuptools wheel

if command -v nvidia-smi >/dev/null; then
    echo "Installing PyTorch with CUDA support..."
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
else
    echo "Installing PyTorch (CPU)..."
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# The package itself, plus the optional runtime dependencies.  Note that
# argparse/pathlib from PyPI are deliberately not installed: they shadow the
# standard library modules.
pip install -e "$PROJECT_DIR"
pip install chatterbox-tts gradio requests

echo ""
echo "✅ Setup complete!"
echo ""
echo "Use:"
echo "  source $VENV_DIR/bin/activate"
echo "  audiobook --document your_book.txt"
echo "  audiobook --dry-run --document your_book.txt   # inspect chapters first"
