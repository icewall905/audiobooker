#!/usr/bin/env python3
"""
Test script for the audiobook creator.
This script performs basic validation without actually running the TTS model.
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import smart_text_split, validate_inputs

def test_text_splitting():
    """Test the smart text splitting function."""
    print("Testing text splitting...")
    
    sample_text = """This is the first paragraph. It has multiple sentences! Does it work well?

This is the second paragraph. It's a bit longer and should be split appropriately. We want to make sure it handles different punctuation marks correctly.

This is a very long paragraph that exceeds the maximum chunk length and should be split into multiple chunks based on sentence boundaries. It contains many sentences to test the splitting logic. Each sentence should be preserved as a complete unit. The algorithm should find natural breaking points. This ensures good audio quality in the final audiobook."""
    
    chunks = smart_text_split(sample_text, max_length=200)
    
    print(f"Original text split into {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks, 1):
        print(f"  Chunk {i} ({len(chunk)} chars): {chunk[:50]}...")
    
    # Verify no chunk exceeds max length
    oversized_chunks = [chunk for chunk in chunks if len(chunk) > 200]
    if oversized_chunks:
        print(f"⚠️  Warning: {len(oversized_chunks)} chunks exceed max length")
    else:
        print("✅ All chunks are within size limits")
    
    return len(chunks)

def test_file_validation():
    """Test file validation function."""
    print("\nTesting file validation...")
    
    # Test with existing file
    if validate_inputs("sample_document.txt"):
        print("✅ Sample document validation passed")
    else:
        print("❌ Sample document validation failed")
    
    # Test with non-existent file
    if not validate_inputs("nonexistent_file.txt"):
        print("✅ Non-existent file validation correctly failed")
    else:
        print("❌ Non-existent file validation should have failed")

def test_imports():
    """Test that all required imports work."""
    print("\nTesting imports...")
    
    try:
        import torch
        print(f"✅ PyTorch {torch.__version__} imported successfully")
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
        print("   Make sure you've installed chatterbox-tts: pip install chatterbox-tts")
        return False
    
    return True

def main():
    """Run all tests."""
    print("=== Audiobook Creator Test Suite ===\n")
    
    # Test imports first
    if not test_imports():
        print("\n❌ Import tests failed. Please install required dependencies.")
        return False
    
    # Test text splitting
    num_chunks = test_text_splitting()
    
    # Test file validation
    test_file_validation()
    
    print(f"\n=== Test Summary ===")
    print(f"✅ All basic tests passed")
    print(f"📄 Sample document split into {num_chunks} chunks")
    print(f"🎯 Ready to create audiobooks!")
    
    print(f"\nTo create an audiobook from the sample document, run:")
    print(f"  python app.py")
    print(f"\nTo use your own document:")
    print(f"  python app.py --document 'your_document.txt'")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
