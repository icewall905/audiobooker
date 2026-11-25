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
echo "  audiobook                                              # Uses sample_document.txt$AUTO_VOICE"
echo "  audiobook --document book.txt                          # Use specific document$AUTO_VOICE"
echo "  audiobook --document book.txt --dry-run                # Show chapters/chunks, no model load"
echo ""
echo -e "${GREEN}Voice Cloning:${NC}"
echo "  audiobook --document book.txt --voice narrator.wav     # Use specific voice"
echo "  audiobook --document book.txt --no-voice               # Force default voice (ignore example.wav)"
echo ""
echo -e "${GREEN}Advanced Settings:${NC}"
echo "  audiobook --document book.txt --exaggeration 0.7       # More expressive"
echo "  audiobook --document book.txt --cfg-weight 0.3         # Faster speech"
echo "  audiobook --document book.txt --max-chunk-length 200   # Smaller TTS prompts"
echo "  audiobook --document book.txt --output my_book.wav     # Custom output file"
echo ""
echo -e "${GREEN}Long Books & Failures:${NC}"
echo "  audiobook --document book.txt                          # re-run to resume a stopped job"
echo "  audiobook --document book.txt --no-resume              # start over from scratch"
echo "  audiobook --document book.txt --strict                 # stop on the first failed chunk"
echo ""
echo -e "${CYAN}📋 Quick Commands:${NC}"
echo "  audiobook --help                                      # Show all options"
echo "  deactivate                                             # Exit virtual environment"
echo ""
echo -e "${YELLOW}💡 Tip: Press Ctrl+C to stop generation if needed${NC}"
echo ""

# Keep the environment active for the user
echo -e "${GREEN}🎯 Environment is now active! You can run the commands above.${NC}"
echo -e "${BLUE}   Current directory: $CURRENT_DIR${NC}"
echo -e "${BLUE}   Virtual env: $VENV_DIR${NC}"
echo ""
