#!/bin/bash

# Fix script for Python executable issues
# This script fixes common Python path issues in the audiobooker environment

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Python Executable Fix Script ===${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "audiobooker-env" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo "Please run the setup first:"
    echo "  ./quick_setup.sh"
    exit 1
fi

echo -e "${GREEN}✅ Virtual environment found${NC}"

# Check current Python executables
echo -e "${BLUE}🔍 Checking Python executables...${NC}"

# Check system Python
if command -v python &> /dev/null; then
    echo -e "${GREEN}✅ System python found${NC}"
    SYSTEM_PYTHON="python"
elif command -v python3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  Only system python3 found${NC}"
    SYSTEM_PYTHON="python3"
else
    echo -e "${RED}❌ No system Python found${NC}"
    exit 1
fi

# Check virtual environment Python
if [ -f "audiobooker-env/bin/python" ]; then
    echo -e "${GREEN}✅ Virtual env python found${NC}"
    VENV_PYTHON="python"
elif [ -f "audiobooker-env/bin/python3" ]; then
    echo -e "${YELLOW}⚠️  Only virtual env python3 found${NC}"
    VENV_PYTHON="python3"
else
    echo -e "${RED}❌ No Python in virtual environment${NC}"
    exit 1
fi

# Fix virtual environment python symlink
if [ "$VENV_PYTHON" = "python3" ] && [ ! -f "audiobooker-env/bin/python" ]; then
    echo -e "${YELLOW}🔧 Creating python symlink in virtual environment...${NC}"
    ln -sf python3 audiobooker-env/bin/python
    echo -e "${GREEN}✅ Created python symlink${NC}"
    VENV_PYTHON="python"
fi

# Test the fix
echo -e "${BLUE}🧪 Testing Python executable...${NC}"
source audiobooker-env/bin/activate

if command -v python &> /dev/null; then
    echo -e "${GREEN}✅ Python command now works!${NC}"
    PYTHON_VERSION=$(python --version 2>&1)
    echo -e "${GREEN}   Version: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python command still not working${NC}"
    echo "Trying alternative approach..."
    
    # Try creating a wrapper script
    cat > audiobooker-env/bin/python << 'EOF'
#!/bin/bash
exec "$(dirname "$0")/python3" "$@"
EOF
    chmod +x audiobooker-env/bin/python
    echo -e "${GREEN}✅ Created Python wrapper script${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Python executable fix completed!${NC}"
echo ""
echo -e "${BLUE}You can now use:${NC}"
echo "  python app.py --document sample_document.txt"
echo ""
echo -e "${BLUE}Or use the wrapper script:${NC}"
echo "  ./run_audiobook.sh --document sample_document.txt"
echo ""
echo -e "${BLUE}Or use the startup script:${NC}"
echo "  ./start.sh"
echo ""
echo -e "${YELLOW}💡 Remember to activate the environment first:${NC}"
echo "  source audiobooker-env/bin/activate" 