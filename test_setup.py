#!/usr/bin/env python3
"""
Test script for the Chatterbox audiobook creator setup.
Validates all dependencies and functionality.
"""

import sys
import os
from pathlib import Path
import importlib.util

def test_imports():
    """Test if all required modules can be imported."""
    print("Testing imports...")
    
    required_modules = [
        'torch',
        'torchaudio',
        'chatterbox.tts',
        'numpy',
        'argparse',
        'pathlib',
        're',
    ]
    
    failed_imports = []
    
    for module in required_modules:
        try:
            if '.' in module:
                # Handle nested imports like chatterbox.tts
                parent_module = module.split('.')[0]
                __import__(parent_module)
                exec(f"import {module}")
            else:
                __import__(module)
            print(f"  ✅ {module}")
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
            failed_imports.append(module)
        except Exception as e:
            print(f"  ❌ {module}: Unexpected error: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
        return False
    
    print("✅ All imports successful!")
    return True

def test_torch_setup():
    """Test PyTorch setup and device availability."""
    print("\nTesting PyTorch setup...")
    
    try:
        import torch
        print(f"  ✅ PyTorch version: {torch.__version__}")
        
        # Test CUDA availability
        if torch.cuda.is_available():
            print(f"  ✅ CUDA available: {torch.cuda.get_device_name()}")
            print(f"  ✅ CUDA version: {torch.version.cuda}")
        else:
            print("  ⚠️  CUDA not available - will use CPU (slower)")
        
        # Test tensor creation
        test_tensor = torch.randn(2, 3)
        print(f"  ✅ Tensor creation successful: {test_tensor.shape}")
        
        return True
    except Exception as e:
        print(f"  ❌ PyTorch test failed: {e}")
        return False

def test_chatterbox():
    """Test Chatterbox TTS initialization."""
    print("\nTesting Chatterbox TTS...")
    
    try:
        from chatterbox.tts import ChatterboxTTS
        
        # Test initialization (this might download models)
        print("  🔄 Initializing ChatterboxTTS (may download models)...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tts = ChatterboxTTS(device=device)
        print(f"  ✅ ChatterboxTTS initialized on {device}")
        
        return True
    except Exception as e:
        print(f"  ❌ ChatterboxTTS test failed: {e}")
        print("  💡 This might be due to missing models - they will download on first use")
        return False

def test_files():
    """Test if required files exist."""
    print("\nTesting files...")
    
    required_files = [
        "app.py",
        "sample_document.txt"
    ]
    
    optional_files = [
        "requirements.txt",
        "test_setup.py"
    ]
    
    missing_required = []
    
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} missing")
            missing_required.append(file)
    
    for file in optional_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ⚠️  {file} missing (optional)")
    
    if missing_required:
        print(f"\n❌ Missing required files: {', '.join(missing_required)}")
        return False
    
    return True

def test_audio_generation():
    """Test basic audio generation capability."""
    print("\nTesting audio generation...")
    
    try:
        import torch
        from chatterbox.tts import ChatterboxTTS
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tts = ChatterboxTTS(device=device)
        
        # Test with a simple phrase
        test_text = "This is a test of the audiobook creator."
        print(f"  🔄 Generating audio for: '{test_text}'")
        
        audio = tts.generate(test_text)
        
        if audio is not None and len(audio) > 0:
            print(f"  ✅ Audio generated successfully: {len(audio)} samples")
            return True
        else:
            print("  ❌ Audio generation returned empty result")
            return False
            
    except Exception as e:
        print(f"  ❌ Audio generation test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=== Audiobook Creator Setup Validation ===\n")
    
    tests = [
        ("Import Test", test_imports),
        ("PyTorch Test", test_torch_setup),
        ("File Test", test_files),
        ("Chatterbox Test", test_chatterbox),
        ("Audio Generation Test", test_audio_generation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total} tests")
    
    if passed == total:
        print("\n🎉 All tests passed! Your audiobook creator is ready to use.")
        print("\nQuick start:")
        print("  python app.py                                    # Use sample document")
        print("  python app.py --document your_book.txt          # Use your document")
        print("  python app.py --voice narrator.wav              # Use voice cloning")
        return True
    else:
        print(f"\n❌ {total - passed} tests failed. Please check the setup.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
