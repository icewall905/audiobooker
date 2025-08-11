#!/bin/bash

# All-in-one startup script for audiobook creator
# This script handles everything: setup, environment activation, and Python fixes

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

# Check if we should run a command immediately
RUN_COMMAND=""
USE_REMOTE=0

# Parse arguments to determine mode and collect command
while [ $# -gt 0 ]; do
    case $1 in
        --run|-r)
            shift
            RUN_COMMAND="$*"
            break
            ;;
        --run-remote|-R)
            shift
            RUN_COMMAND="$*"
            USE_REMOTE=1
            break
            ;;
        *)
            # No run flag, exit loop
            break
            ;;
    esac
done

# If user passed a --server flag inside RUN_COMMAND, prefer remote runner
if [ -n "$RUN_COMMAND" ] && echo " $RUN_COMMAND " | grep -q " --server "; then
    USE_REMOTE=1
fi

echo -e "${BLUE}=== Audiobook Creator All-in-One Startup ===${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function to find Python executable
find_python() {
    if command_exists python; then
        echo "python"
    elif command_exists python3; then
        echo "python3"
    else
        echo ""
    fi
}

# Check if we have Python available
PYTHON_CMD=$(find_python)
if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}❌ No Python executable found!${NC}"
    echo "Please install Python 3.8+ first:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "  macOS: brew install python3"
    exit 1
fi

echo -e "${GREEN}✅ Found Python: $PYTHON_CMD${NC}"

# Check if virtual environment exists, create if not
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}📦 Virtual environment not found. Creating...${NC}"
    
    # Create virtual environment
    $PYTHON_CMD -m venv "$VENV_DIR"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to create virtual environment${NC}"
        echo "Make sure you have python3-venv installed:"
        echo "  sudo apt install python3-venv"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Virtual environment created${NC}"
    
    # Activate and install dependencies
    echo -e "${CYAN}📥 Installing dependencies...${NC}"
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install PyTorch (with CUDA if available)
    if command_exists nvidia-smi; then
        echo -e "${CYAN}🚀 Installing PyTorch with CUDA support...${NC}"
        pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
    else
        echo -e "${CYAN}💻 Installing PyTorch CPU version...${NC}"
        pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
    fi
    
    # Install Chatterbox TTS
    echo -e "${CYAN}🎤 Installing Chatterbox TTS...${NC}"
    pip install chatterbox-tts
    
    # Install other dependencies
    if [ -f "requirements.txt" ]; then
        echo -e "${CYAN}📋 Installing additional requirements...${NC}"
        pip install -r requirements.txt
    fi
    
    echo -e "${GREEN}✅ Dependencies installed successfully!${NC}"
else
    echo -e "${GREEN}✅ Virtual environment found at: $VENV_DIR${NC}"
fi

# Activate virtual environment
echo -e "${CYAN}🔄 Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Environment activated successfully!${NC}"
else
    echo -e "${RED}❌ Failed to activate environment${NC}"
    exit 1
fi

# Fix Python executable issues
echo -e "${CYAN}🔧 Checking Python executable...${NC}"
if command_exists python; then
    echo -e "${GREEN}✅ Python executable found${NC}"
    PYTHON_CMD="python"
elif command_exists python3; then
    echo -e "${YELLOW}⚠️  Only python3 found, creating python symlink...${NC}"
    # Create python symlink in virtual environment if it doesn't exist
    if [ ! -f "$VENV_DIR/bin/python" ] && [ -f "$VENV_DIR/bin/python3" ]; then
        ln -sf python3 "$VENV_DIR/bin/python"
        echo -e "${GREEN}✅ Created python symlink${NC}"
    fi
    PYTHON_CMD="python3"
else
    echo -e "${RED}❌ No Python executable found in virtual environment${NC}"
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

# Create output directory
if [ ! -d "output" ]; then
    echo -e "${CYAN}📁 Creating output directory...${NC}"
    mkdir -p output
    echo -e "${GREEN}✅ Output directory created${NC}"
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
echo -e "${GREEN}Default Behavior (Recommended):${NC}"
echo "  python app.py                                          # Uses sample_document.txt$AUTO_VOICE"
echo "  python app.py --document book.txt                      # Use specific document$AUTO_VOICE"
echo ""
echo -e "${GREEN}Voice Cloning:${NC}"
echo "  python app.py --document book.txt --voice narrator.wav # Use specific voice"
echo "  python app.py --document book.txt --no-voice          # Force default voice (ignore example.wav)"
echo ""
echo -e "${GREEN}Remote Server (Chatterbox API):${NC}"
echo "  python app_remote.py --document book.txt --server http://10.0.10.23:7860 [--voice narrator.wav]"
echo "  ./start.sh --run-remote --document book.txt [--voice narrator.wav] [--server http://10.0.10.23:7860]"
echo ""
echo -e "${GREEN}Advanced Settings:${NC}"
echo "  python app.py --document book.txt --exaggeration 0.7  # More expressive"
echo "  python app.py --document book.txt --cfg-weight 0.3    # Faster speech"
echo "  python app.py --document book.txt --output output/my_book.wav # Custom output file"
echo ""
echo -e "${GREEN}Chapter Splitting (Default):${NC}"
echo "  python app.py --document book.txt                      # Split chapters + MP3 (default)"
echo "  python app.py --document book.txt --no-split-chapters  # Single file"
echo "  python app.py --document book.txt --no-mp3             # WAV format only"
echo ""
echo -e "${GREEN}Alternative Methods:${NC}"
echo "  ./run_audiobook.sh --document book.txt                 # Use wrapper script"
echo "  audiobook --document book.txt --voice narrator.wav     # Global launcher (if available)"
echo ""
echo -e "${CYAN}📋 Quick Commands:${NC}"
echo "  python app.py --help                                   # Show all options"
echo "  deactivate                                             # Exit virtual environment"
echo ""
echo -e "${YELLOW}💡 Tip: Press Ctrl+C to stop generation if needed${NC}"
echo ""

# Set up environment for immediate use
echo -e "${GREEN}🎯 Environment is ready! You can now run:${NC}"
echo -e "${BLUE}   python app.py --document sample_document.txt${NC}"
echo ""
echo -e "${BLUE}   Current directory: $CURRENT_DIR${NC}"
echo -e "${BLUE}   Virtual env: $VENV_DIR${NC}"
echo -e "${BLUE}   Python command: $PYTHON_CMD${NC}"
echo -e "${BLUE}   Output directory: output/${NC}"
echo ""

# Test that python command works
echo -e "${CYAN}🧪 Testing Python command...${NC}"
if python --version &> /dev/null; then
    echo -e "${GREEN}✅ Python command is working!${NC}"
    PYTHON_VERSION=$(python --version 2>&1)
    echo -e "${GREEN}   Version: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python command not working, trying alternative...${NC}"
    if python3 --version &> /dev/null; then
        echo -e "${GREEN}✅ Python3 command is working!${NC}"
        echo -e "${YELLOW}   Use 'python3 app.py' instead of 'python app.py'${NC}"
    else
        echo -e "${RED}❌ No Python command is working${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}🎉 Everything is set up and ready!${NC}"

# If a command was specified, run it immediately
if [ -n "$RUN_COMMAND" ]; then
    echo -e "${CYAN}🚀 Running command: $RUN_COMMAND${NC}"
    echo ""
    if [ "$USE_REMOTE" -eq 1 ]; then
        exec python app_remote.py $RUN_COMMAND
    else
        exec python app.py $RUN_COMMAND
    fi
fi

# If no command specified, start an interactive shell with the environment
echo -e "${YELLOW}💡 Starting interactive shell with activated environment...${NC}"
echo -e "${YELLOW}💡 You can now run 'python app.py' directly${NC}"
echo -e "${YELLOW}💡 Type 'exit' to leave the environment${NC}"
echo ""

# Start a new shell with the environment activated
exec bash --rcfile <(echo "source $VENV_DIR/bin/activate; PS1='(audiobooker) \w\$ '")
