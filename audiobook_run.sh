#!/bin/bash

# Simple wrapper to run audiobook commands with proper environment activation
# Usage: ./audiobook_run.sh --document book.txt

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "audiobooker-env" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo "Please run ./start.sh first to set up the environment."
    exit 1
fi

# Activate virtual environment
source audiobooker-env/bin/activate

# Check if app.py exists
if [ ! -f "app.py" ]; then
    echo -e "${RED}❌ app.py not found!${NC}"
    exit 1
fi

# Check if python command works
if ! command -v python &> /dev/null; then
    echo -e "${YELLOW}⚠️  Python command not found, trying python3...${NC}"
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    else
        echo -e "${RED}❌ No Python executable found!${NC}"
        exit 1
    fi
else
    PYTHON_CMD="python"
fi

echo -e "${GREEN}🚀 Running audiobook with: $PYTHON_CMD app.py $*${NC}"
echo ""

# Run the app with all arguments
exec "$PYTHON_CMD" app.py "$@" 