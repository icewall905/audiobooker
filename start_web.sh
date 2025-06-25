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

echo -e "${BLUE}=== Audiobook Creator Web Interface Launcher ===${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo ""
    echo -e "${YELLOW}To set up the environment, run:${NC}"
    echo "  ./setup_ubuntu.sh"
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

# Check if required files exist
if [ ! -f "web_interface.py" ]; then
    echo -e "${RED}❌ web_interface.py not found in current directory${NC}"
    echo "Make sure you're in the correct directory with the audiobook creator files."
    exit 1
fi

if [ ! -f "app.py" ]; then
    echo -e "${RED}❌ app.py not found in current directory${NC}"
    echo "The web interface requires app.py to function."
    exit 1
fi

echo -e "${GREEN}✅ Required files found${NC}"

# Check if gradio is installed
echo -e "${CYAN}🔍 Checking for Gradio...${NC}"
python -c "import gradio" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Gradio not found. Installing...${NC}"
    pip install gradio>=4.0.0
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install Gradio${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Gradio installed successfully${NC}"
else
    echo -e "${GREEN}✅ Gradio is already installed${NC}"
fi

# Check GPU status
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✅ NVIDIA GPU detected${NC}"
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits | head -1)
    echo -e "${CYAN}   GPU: $GPU_INFO${NC}"
else
    echo -e "${YELLOW}⚠️  No NVIDIA GPU detected - will use CPU (slower)${NC}"
fi

echo ""
echo -e "${BLUE}=== Starting Web Interface ===${NC}"
echo ""
echo -e "${CYAN}🌐 Web interface will be available at:${NC}"
echo -e "${GREEN}   • Local:   http://localhost:7860${NC}"
echo -e "${GREEN}   • Network: http://$(hostname -I | cut -d' ' -f1):7860${NC}"
echo ""
echo -e "${YELLOW}💡 Tips:${NC}"
echo -e "${YELLOW}   • Upload .txt files or paste text directly${NC}"
echo -e "${YELLOW}   • Upload voice samples (.wav, .mp3, .m4a, .flac) for voice cloning${NC}"
echo -e "${YELLOW}   • Adjust settings for different speech styles${NC}"
echo -e "${YELLOW}   • Chapter detection works automatically${NC}"
echo -e "${YELLOW}   • Press Ctrl+C to stop the server${NC}"
echo ""

# Launch the web interface
python web_interface.py
