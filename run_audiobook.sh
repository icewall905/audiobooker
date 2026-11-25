#!/bin/bash

# Simple wrapper script to run the audiobook app with the correct Python executable
# This script automatically detects whether to use 'python' or 'python3'

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to find the correct Python executable
find_python() {
    if command -v python &> /dev/null; then
        echo "python"
    elif command -v python3 &> /dev/null; then
        echo "python3"
    else
        echo ""
    fi
}

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo -e "${GREEN}✅ Virtual environment detected: $VIRTUAL_ENV${NC}"
    
    # In virtual environment, try to use python first, fallback to python3
    if [ -f "$VIRTUAL_ENV/bin/python" ]; then
        PYTHON_CMD="$VIRTUAL_ENV/bin/python"
    elif [ -f "$VIRTUAL_ENV/bin/python3" ]; then
        PYTHON_CMD="$VIRTUAL_ENV/bin/python3"
        # Create python symlink if it doesn't exist
        if [ ! -f "$VIRTUAL_ENV/bin/python" ]; then
            echo -e "${YELLOW}⚠️  Creating python symlink in virtual environment...${NC}"
            ln -sf python3 "$VIRTUAL_ENV/bin/python"
            PYTHON_CMD="$VIRTUAL_ENV/bin/python"
        fi
    else
        echo -e "${RED}❌ No Python executable found in virtual environment${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  No virtual environment detected${NC}"
    PYTHON_CMD=$(find_python)
    if [ -z "$PYTHON_CMD" ]; then
        echo -e "${RED}❌ No Python executable found${NC}"
        echo "Please activate the virtual environment first:"
        echo "  source audiobooker-env/bin/activate"
        exit 1
    fi
fi

echo -e "${GREEN}🚀 Running audiobook app with: $PYTHON_CMD${NC}"
echo ""

# Run the app with all arguments passed to this script
exec "$PYTHON_CMD" app.py "$@" 