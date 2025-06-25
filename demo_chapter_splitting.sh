#!/bin/bash

# Demo script for chapter splitting and MP3 conversion features
# This script demonstrates the new default behavior and options

echo "🎵 Audiobook Chapter Splitting and MP3 Conversion Demo"
echo "======================================================"
echo ""

# Check if sample document exists
if [ ! -f "sample_document.txt" ]; then
    echo "❌ Error: sample_document.txt not found!"
    echo "Please ensure you have the sample document in the current directory."
    exit 1
fi

# Check if ffmpeg is available
if command -v ffmpeg &> /dev/null; then
    echo "✅ ffmpeg found - MP3 conversion will be available"
    FFMPEG_AVAILABLE=true
else
    echo "⚠️  ffmpeg not found - MP3 conversion will be skipped"
    echo "   Install ffmpeg for MP3 support:"
    echo "   Ubuntu/Debian: sudo apt install ffmpeg"
    echo "   macOS: brew install ffmpeg"
    FFMPEG_AVAILABLE=false
fi

echo ""
echo "📖 Sample document contains 3 chapters:"
echo "   - Chapter 1: The Beginning"
echo "   - Chapter 2: The Discovery" 
echo "   - Chapter 3: The Journey Begins"
echo ""

# Function to run demo
run_demo() {
    local description="$1"
    local command="$2"
    
    echo "🔧 Demo: $description"
    echo "Command: $command"
    echo "---"
    
    eval "$command"
    
    if [ $? -eq 0 ]; then
        echo "✅ Success!"
    else
        echo "❌ Failed!"
    fi
    echo ""
}

# Demo 1: Default behavior (chapter splitting + MP3)
echo "🎯 Demo 1: Default Behavior (Chapter Splitting + MP3)"
run_demo "Default behavior - split chapters into MP3 files" \
    "python app.py --document sample_document.txt --device cpu"

# Demo 2: Single file output (no chapter splitting)
echo "🎯 Demo 2: Single File Output"
run_demo "Create single MP3 file (no chapter splitting)" \
    "python app.py --document sample_document.txt --no-split-chapters --output output/single_demo.wav --device cpu"

# Demo 3: WAV only (no MP3 conversion)
echo "🎯 Demo 3: WAV Only Output"
run_demo "Create WAV files (no MP3 conversion)" \
    "python app.py --document sample_document.txt --no-mp3 --output output/wav_demo.wav --device cpu"

# Demo 4: Legacy behavior (no splitting, no MP3)
echo "🎯 Demo 4: Legacy Behavior"
run_demo "Legacy behavior - single WAV file" \
    "python app.py --document sample_document.txt --no-split-chapters --no-mp3 --output output/legacy_demo.wav --device cpu"

# Demo 5: Custom chapter pause
echo "🎯 Demo 5: Custom Chapter Pause"
run_demo "Default behavior with 2-second pauses" \
    "python app.py --document sample_document.txt --chapter-pause 2.0 --device cpu"

echo "📁 Generated Files in output/ directory:"
echo "========================================"

# List generated files
if [ -d "output" ]; then
    echo "Chapter files:"
    for file in output/chapter*.mp3 output/chapter*.wav; do
        if [ -f "$file" ]; then
            size=$(du -h "$file" | cut -f1)
            echo "  📄 $(basename "$file") ($size)"
        fi
    done

    echo ""
    echo "Single files:"
    for file in output/*.mp3 output/*.wav; do
        if [ -f "$file" ] && [[ ! "$file" =~ chapter ]]; then
            size=$(du -h "$file" | cut -f1)
            echo "  📄 $(basename "$file") ($size)"
        fi
    done
else
    echo "No output directory found"
fi

echo ""
echo "🎉 Demo completed!"
echo ""
echo "💡 New Default Behavior:"
echo "  ✅ Chapter splitting is ENABLED by default"
echo "  ✅ MP3 conversion is ENABLED by default"
echo "  ✅ Files are saved in ./output/ directory"
echo ""
echo "💡 How to Disable Defaults:"
echo "  --no-split-chapters: Create single file instead of separate chapters"
echo "  --no-mp3: Keep WAV format instead of converting to MP3"
echo ""
echo "💡 Tips:"
echo "  - Use --device cpu for testing (slower but no GPU required)"
echo "  - Install ffmpeg for MP3 conversion support"
echo "  - All output files are now organized in the output/ directory"
echo ""
echo "📚 For more information, see README_CHAPTER_SPLITTING.md" 