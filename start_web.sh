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

echo -e "${BLUE}=== Audiobook Creator Web Interface ===${NC}"
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

# Check if web_interface.py exists
if [ ! -f "web_interface.py" ]; then
    echo -e "${RED}❌ web_interface.py not found in current directory${NC}"
    echo "Make sure you're in the correct directory with the audiobook creator files."
    exit 1
fi

echo -e "${GREEN}✅ web_interface.py found${NC}"

# Check if gradio is installed
echo -e "${CYAN}🔄 Checking Gradio installation...${NC}"
python -c "import gradio" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Gradio is installed${NC}"
else
    echo -e "${YELLOW}⚠️  Gradio not found. Installing...${NC}"
    pip install gradio>=4.0.0
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Gradio installed successfully${NC}"
    else
        echo -e "${RED}❌ Failed to install Gradio${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${BLUE}🚀 Starting Web Interface...${NC}"
echo ""
echo -e "${CYAN}📱 The web interface will be available at:${NC}"
echo -e "${GREEN}   • Local:    http://localhost:7860${NC}"
echo -e "${GREEN}   • Network:  http://$(hostname -I | awk '{print $1}'):7860${NC}"
echo ""
echo -e "${YELLOW}💡 Tips:${NC}"
echo "   • Upload text files or paste text directly"
echo "   • Add voice samples for voice cloning"
echo "   • Adjust settings for different narration styles"
echo "   • Chapter titles are automatically detected"
echo ""
echo -e "${CYAN}🛑 Press Ctrl+C to stop the server${NC}"
echo ""

# Start the web interface
python web_interface.py
