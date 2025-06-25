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
