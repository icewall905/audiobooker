#!/bin/bash
set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
# If we're in a git repo with app.py, install directly here, otherwise create audiobooker subdirectory
if [ -f "app.py" ] && [ -d ".git" ]; then
    INSTALL_DIR="$(pwd)"
else
    INSTALL_DIR="$(pwd)/audiobooker"
fi
VENV_NAME="audiobooker-env"
PYTHON_VERSION="3.8"

echo -e "${BLUE}=== Chatterbox Audiobook Creator Setup ===${NC}"
echo "This script will set up the audiobook creator on your Ubuntu server."
echo "Installation directory: $INSTALL_DIR"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on Ubuntu
check_ubuntu() {
    if [[ ! -f /etc/lsb-release ]] || ! grep -q "Ubuntu" /etc/lsb-release; then
        print_warning "This script is designed for Ubuntu. Continuing anyway..."
    else
        print_status "Ubuntu detected ✓"
    fi
}

# Check for GPU
check_gpu() {
    if command -v nvidia-smi &> /dev/null; then
        print_status "NVIDIA GPU detected:"
        nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits | head -1
    else
        print_warning "NVIDIA GPU not detected. CPU mode will be used (much slower)."
    fi
}

# Update system packages
update_system() {
    print_status "Updating system packages..."
    sudo apt update
    sudo apt upgrade -y
}

# Install system dependencies
install_system_deps() {
    print_status "Installing system dependencies..."
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        curl \
        wget \
        build-essential \
        ffmpeg \
        libsndfile1 \
        portaudio19-dev \
        python3-pyaudio
}

# Install CUDA support (if GPU available)
install_cuda_support() {
    if command -v nvidia-smi &> /dev/null; then
        print_status "Installing CUDA support for PyTorch..."
        # This will be handled in the pip install step with the right PyTorch version
    else
        print_status "Skipping CUDA installation (no GPU detected)"
    fi
}

# Create installation directory
create_install_dir() {
    print_status "Creating installation directory..."
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
}

# Create virtual environment
create_venv() {
    print_status "Creating Python virtual environment..."
    python3 -m venv "$VENV_NAME"
    source "$VENV_NAME/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
}

# Install Python dependencies
install_python_deps() {
    print_status "Installing Python dependencies..."
    source "$VENV_NAME/bin/activate"
    
    # Install PyTorch with CUDA support if available
    if command -v nvidia-smi &> /dev/null; then
        print_status "Installing PyTorch with CUDA support..."
        pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
    else
        print_status "Installing PyTorch CPU version..."
        pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
    fi
    
    # Install Chatterbox TTS
    print_status "Installing Chatterbox TTS..."
    pip install chatterbox-tts
    
    # Install additional dependencies
    pip install numpy requests argparse pathlib
    
    # Install from requirements.txt if it exists
    if [ -f "requirements.txt" ]; then
        print_status "Installing from requirements.txt..."
        pip install -r requirements.txt
    fi
}

# Download audiobook creator scripts
download_scripts() {
    print_status "Setting up audiobook creator scripts..."
    
    # Check if we're in a git repository with existing files
    if [ -f "app.py" ] && [ -d ".git" ]; then
        print_status "Found existing app.py in git repository - using existing file ✓"
        print_status "This preserves any local customizations and latest features"
    else
        print_status "Creating app.py script..."
        # Create the main app.py script only if it doesn't exist or we're not in a git repo
        cat > app.py << 'EOF'
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
DOCUMENT_PATH = "sample_document.txt" 
VOICE_PROMPT_PATH = None  # Set to your voice reference file path if available
OUTPUT_PATH = "my_audiobook.wav" 
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MAX_CHUNK_LENGTH = 300

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
                   device: str = DEVICE):
    """Create audiobook from document using Chatterbox TTS."""
    
    if not validate_inputs(document_path, voice_prompt_path):
        return False
    
    print(f"Using device: {device}")
    print(f"Voice reference: {'Yes' if voice_prompt_path else 'No (using default voice)'}")

    # Initialize the Chatterbox model
    print("Loading ChatterboxTTS model...")
    try:
        model = ChatterboxTTS.from_pretrained(device=device)
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")
        return False

    # Load and chunk the document
    print(f"Loading document from {document_path}...")
    try:
        with open(document_path, 'r', encoding='utf-8') as f:
            full_text = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return False

    text_chunks = smart_text_split(full_text, max_length=MAX_CHUNK_LENGTH)
    print(f"Document split into {len(text_chunks)} chunks.")
    
    if not text_chunks:
        print("No text found in document.")
        return False

    # Synthesize each chunk
    audio_chunks = []
    print("Starting audio generation for each chunk...")
    
    for i, chunk in enumerate(text_chunks, 1):
        print(f"Generating audio for chunk {i}/{len(text_chunks)} ({len(chunk)} chars)...")
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
            
            audio_chunks.append(wav.squeeze(0).cpu())
            
        except Exception as e:
            print(f"Error generating audio for chunk {i}: {e}")
            continue

    # Concatenate and save
    if not audio_chunks:
        print("No audio was generated. Exiting.")
        return False

    print("Concatenating audio chunks...")
    try:
        full_audio = torch.cat(audio_chunks)
        
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        print(f"Saving final audiobook to {output_path} with sample rate {model.sr} Hz...")
        ta.save(output_path, full_audio.unsqueeze(0), model.sr)
        
        duration_seconds = len(full_audio) / model.sr
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
    
    args = parser.parse_args()
    
    # Auto-detect example.wav if no voice specified and file exists
    voice_path = args.voice
    if not args.no_voice and not voice_path and os.path.exists("example.wav"):
        voice_path = "example.wav"
        print("🎤 Automatically detected and using example.wav as voice reference")
    elif args.no_voice:
        voice_path = None
    
    print("=== Chatterbox Audiobook Creator ===")
    print(f"Document: {args.document}")
    print(f"Voice reference: {voice_path if voice_path else 'Default voice'}")
    print(f"Output: {args.output}")
    print(f"Exaggeration: {args.exaggeration}")
    print(f"CFG Weight: {args.cfg_weight}")
    print(f"Device: {args.device}")
    print("=" * 35)
    
    success = create_audiobook(
        document_path=args.document,
        voice_prompt_path=voice_path,
        output_path=args.output,
        exaggeration=args.exaggeration,
        cfg_weight=args.cfg_weight,
        device=args.device
    )
    
    if success:
        print("\n✅ Audiobook creation completed successfully!")
    else:
        print("\n❌ Audiobook creation failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF
    fi
    
    # Create sample document (only if it doesn't exist)
    if [ ! -f "sample_document.txt" ]; then
        print_status "Creating sample document..."
    cat > sample_document.txt << 'EOF'
Chapter 1: The Beginning

In the heart of a bustling city, where the sounds of traffic and life never ceased, there lived a young woman named Sarah. She had always been fascinated by the stories that surrounded her - the tales whispered in coffee shops, the legends passed down through generations, and the quiet moments of human connection that seemed to happen when she least expected them.

Every morning, Sarah would walk through the same streets, observing the world with the keen eye of someone who understood that every person she passed had their own story to tell. The elderly man feeding pigeons in the park, the mother rushing to catch the bus with her children, the artist sketching silently on a bench - each carried within them a universe of experiences.

Chapter 2: The Discovery

One particular Tuesday, something extraordinary happened. As Sarah made her usual route to work, she noticed a small, leather-bound book lying abandoned on a park bench. The cover was worn and weathered, suggesting it had been well-loved and frequently read. Without thinking, she picked it up and opened it to the first page.

The words that greeted her were unlike anything she had ever read before. They seemed to shimmer and dance across the page, telling a story that felt both completely foreign and intimately familiar. It was as if the book had been waiting specifically for her to find it.

Chapter 3: The Journey Begins

As days turned into weeks, Sarah found herself completely absorbed in the mysterious book. Each page revealed new wonders and challenged her understanding of what was possible in the world. The story spoke of places that existed between the spaces of reality, of people who could step from one world to another with nothing more than a thought and a wish.

The more she read, the more she began to notice strange coincidences in her daily life. People she had never met would smile at her as if they were old friends. Conversations would take unexpected turns that seemed to echo themes from the book. Even the weather seemed to respond to her moods in ways that defied explanation.

And so began Sarah's journey into a world where the boundaries between story and reality were far more fluid than she had ever imagined possible.
EOF
    else
        print_status "Found existing sample_document.txt - keeping existing file ✓"
    fi

    # Create test script (only if it doesn't exist)
    if [ ! -f "test_setup.py" ]; then
        print_status "Creating test script..."
    cat > test_setup.py << 'EOF'
#!/usr/bin/env python3
"""Test script to verify the audiobook creator setup."""

import sys
import os

def test_imports():
    """Test that all required imports work."""
    print("Testing imports...")
    
    try:
        import torch
        print(f"✅ PyTorch {torch.__version__} imported successfully")
        print(f"   CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"   GPU: {torch.cuda.get_device_name()}")
    except ImportError as e:
        print(f"❌ PyTorch import failed: {e}")
        return False
    
    try:
        import torchaudio
        print(f"✅ TorchAudio {torchaudio.__version__} imported successfully")
    except ImportError as e:
        print(f"❌ TorchAudio import failed: {e}")
        return False
    
    try:
        from chatterbox.tts import ChatterboxTTS
        print("✅ Chatterbox TTS imported successfully")
    except ImportError as e:
        print(f"❌ Chatterbox TTS import failed: {e}")
        return False
    
    return True

def test_files():
    """Test that required files exist."""
    files_to_check = ['app.py', 'sample_document.txt']
    
    for file in files_to_check:
        if os.path.exists(file):
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} missing")
            return False
    
    return True

def main():
    print("=== Audiobook Creator Setup Test ===\n")
    
    if not test_imports():
        print("\n❌ Import tests failed.")
        return False
    
    if not test_files():
        print("\n❌ File tests failed.")
        return False
    
    print("\n✅ All tests passed!")
    print("\nYou can now create audiobooks:")
    print("  python app.py                                    # Use sample document")
    print("  python app.py --document your_book.txt          # Use your document")
    print("  python app.py --voice narrator.wav              # Use voice cloning")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
EOF
        chmod +x test_setup.py
    else
        print_status "Found existing test_setup.py - keeping existing file ✓"
    fi

    # Create start script for easy usage (only if it doesn't exist)
    if [ ! -f "start.sh" ]; then
        print_status "Creating start script..."
    cat > start.sh << 'EOF'
#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
VENV_DIR="audiobooker-env"
CURRENT_DIR=$(pwd)

echo -e "${BLUE}=== Audiobook Creator Startup Script ===${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo ""
    echo -e "${YELLOW}To set up the environment, run one of:${NC}"
    echo "  • Full setup:    ./setup_ubuntu.sh"
    echo "  • Quick setup:   ./quick_setup.sh"
    echo "  • Manual setup: python3 -m venv $VENV_DIR && source $VENV_DIR/bin/activate && pip install -r requirements.txt"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Virtual environment found at: $VENV_DIR${NC}"

# Activate virtual environment
echo -e "${CYAN}🔄 Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Environment activated successfully!${NC}"
else
    echo -e "${RED}❌ Failed to activate environment${NC}"
    exit 1
fi

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo -e "${RED}❌ app.py not found in current directory${NC}"
    echo "Make sure you're in the correct directory with the audiobook creator files."
    exit 1
fi

echo -e "${GREEN}✅ app.py found${NC}"

# Check for example.wav
if [ -f "example.wav" ]; then
    echo -e "${GREEN}✅ example.wav found - will be auto-detected for voice cloning${NC}"
    AUTO_VOICE=" (auto-detects example.wav)"
else
    echo -e "${YELLOW}ℹ️  No example.wav found - place one here for automatic voice detection${NC}"
    AUTO_VOICE=""
fi

echo ""
echo -e "${BLUE}=== Ready to Create Audiobooks! ===${NC}"
echo ""
echo -e "${CYAN}📖 Available Documents:${NC}"
for file in *.txt; do
    if [ -f "$file" ]; then
        echo "  • $file"
    fi
done

echo ""
echo -e "${CYAN}🎤 Available Voice Files:${NC}"
voice_found=false
for file in *.wav *.mp3 *.m4a *.flac; do
    if [ -f "$file" ]; then
        echo "  • $file"
        voice_found=true
    fi
done
if [ "$voice_found" = false ]; then
    echo "  • No voice files found (will use default voice)"
fi

echo ""
echo -e "${CYAN}🚀 Usage Examples:${NC}"
echo ""
echo -e "${GREEN}Basic Usage:${NC}"
echo "  python app.py                                          # Uses sample_document.txt$AUTO_VOICE"
echo "  python app.py --document book.txt                      # Use specific document$AUTO_VOICE"
echo ""
echo -e "${GREEN}Voice Cloning:${NC}"
echo "  python app.py --document book.txt --voice narrator.wav # Use specific voice"
echo "  python app.py --document book.txt --no-voice          # Force default voice (ignore example.wav)"
echo ""
echo -e "${GREEN}Advanced Settings:${NC}"
echo "  python app.py --document book.txt --exaggeration 0.7  # More expressive"
echo "  python app.py --document book.txt --cfg-weight 0.3    # Faster speech"
echo "  python app.py --document book.txt --output my_book.wav # Custom output file"
echo ""
echo -e "${GREEN}Global Launcher (if available):${NC}"
echo "  audiobook --document book.txt --voice narrator.wav    # Use from anywhere"
echo ""
echo -e "${CYAN}📋 Quick Commands:${NC}"
echo "  python app.py --help                                  # Show all options"
echo "  deactivate                                             # Exit virtual environment"
echo ""
echo -e "${YELLOW}💡 Tip: Press Ctrl+C to stop generation if needed${NC}"
echo ""

# Keep the environment active for the user
echo -e "${GREEN}🎯 Environment is now active! You can run the commands above.${NC}"
echo -e "${BLUE}   Current directory: $CURRENT_DIR${NC}"
echo -e "${BLUE}   Virtual env: $VENV_DIR${NC}"
echo ""
EOF
        chmod +x start.sh
    else
        print_status "Found existing start.sh - keeping existing file ✓"
    fi
}

# Create launcher script
create_launcher() {
    print_status "Creating launcher script..."
    
    cat > "$INSTALL_DIR/audiobook" << EOF
#!/bin/bash
# Audiobook Creator Launcher
cd "$INSTALL_DIR"
source "$VENV_NAME/bin/activate"
python app.py "\$@"
EOF
    
    chmod +x "$INSTALL_DIR/audiobook"
    
    # Add to PATH
    if ! grep -q "$INSTALL_DIR" ~/.bashrc; then
        echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> ~/.bashrc
        print_status "Added launcher to PATH in ~/.bashrc"
    fi
}

# Test installation
test_installation() {
    print_status "Testing installation..."
    cd "$INSTALL_DIR"
    source "$VENV_NAME/bin/activate"
    
    if python test_setup.py; then
        print_status "Installation test passed! ✓"
    else
        print_error "Installation test failed!"
        return 1
    fi
}

# Print usage instructions
print_usage() {
    echo ""
    echo -e "${GREEN}=== Installation Complete! ===${NC}"
    echo ""
    echo "Installation directory: $INSTALL_DIR"
    echo ""
    echo -e "${BLUE}Quick Start:${NC}"
    echo "  # Use the convenient start script (recommended)"
    echo "  cd $INSTALL_DIR && ./start.sh"
    echo ""
    echo "  # Or manual activation"
    echo "  cd $INSTALL_DIR"
    echo "  source $VENV_NAME/bin/activate"
    echo "  python app.py"
    echo ""
    echo -e "${BLUE}Usage Examples:${NC}"
    echo "  # Basic usage with sample document"
    echo "  python app.py"
    echo ""
    echo "  # Use your own document"
    echo "  python app.py --document /path/to/your/book.txt"
    echo ""
    echo "  # Use voice cloning"
    echo "  python app.py --document book.txt --voice narrator.wav"
    echo ""
    echo "  # Auto voice detection (place 'example.wav' in project folder)"
    echo "  python app.py --document book.txt  # Will auto-use example.wav if found"
    echo ""
    echo "  # Expressive narration"
    echo "  python app.py --exaggeration 0.7 --cfg-weight 0.3"
    echo ""
    echo -e "${BLUE}Global launcher:${NC}"
    echo "  audiobook --document book.txt --voice narrator.wav"
    echo ""
    echo -e "${YELLOW}Reloading shell to enable global launcher...${NC}"
    # Reload bash configuration
    if [ -f ~/.bashrc ]; then
        source ~/.bashrc
        echo -e "${GREEN}✅ Shell reloaded! Global launcher is now available.${NC}"
    else
        echo -e "${YELLOW}Note: Restart your terminal or run 'source ~/.bashrc' to use the global launcher${NC}"
    fi
}

# Main execution
main() {
    check_ubuntu
    check_gpu
    update_system
    install_system_deps
    install_cuda_support
    create_install_dir
    create_venv
    install_python_deps
    download_scripts
    create_launcher
    test_installation
    print_usage
}

# Run main function
main
