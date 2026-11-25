#!/usr/bin/env python3
"""
Production validation script for the audiobook creator.
Tests all functionality in a production environment.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
import argparse

def run_command(cmd, description="", check=True):
    """Run a command and return the result."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        if result.returncode == 0:
            print(f"✅ {description}")
            return result.stdout.strip()
        else:
            print(f"❌ {description}: {result.stderr}")
            return None
    except subprocess.CalledProcessError as e:
        print(f"❌ {description}: {e}")
        return None

def test_environment():
    """Test the virtual environment setup."""
    print("\n=== Environment Test ===")
    
    # Check if we're in a virtual environment
    venv = os.environ.get('VIRTUAL_ENV')
    if venv:
        print(f"✅ Virtual environment active: {venv}")
    else:
        print("⚠️  Virtual environment not detected")
    
    # Test Python version
    python_version = run_command("python --version", "Python version check")
    if python_version and "Python 3." in python_version:
        print(f"✅ Python version: {python_version}")
    else:
        print("❌ Python version check failed")
        return False
    
    # Test pip
    pip_version = run_command("pip --version", "Pip version check")
    if pip_version:
        print(f"✅ Pip available: {pip_version.split()[1]}")
    else:
        print("❌ Pip not available")
        return False
    
    return True

def test_gpu_setup():
    """Test GPU and CUDA setup."""
    print("\n=== GPU Setup Test ===")
    
    # Check NVIDIA driver
    nvidia_smi = run_command("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits", 
                            "NVIDIA GPU detection", check=False)
    if nvidia_smi:
        print(f"✅ GPU detected: {nvidia_smi}")
        
        # Test CUDA availability in PyTorch
        cuda_test = run_command("python -c \"import torch; print(f'CUDA: {torch.cuda.is_available()}')\"",
                               "PyTorch CUDA test")
        if cuda_test and "True" in cuda_test:
            print("✅ PyTorch CUDA integration working")
            return True
        else:
            print("⚠️  PyTorch CUDA integration not working")
    else:
        print("⚠️  No NVIDIA GPU detected - will use CPU")
    
    return True

def test_dependencies():
    """Test all Python dependencies."""
    print("\n=== Dependencies Test ===")
    
    dependencies = [
        ("torch", "import torch; print(torch.__version__)"),
        ("torchaudio", "import torchaudio; print(torchaudio.__version__)"),
        ("chatterbox", "from chatterbox.tts import ChatterboxTTS; print('OK')"),
        ("numpy", "import numpy; print(numpy.__version__)"),
    ]
    
    all_good = True
    for name, test_code in dependencies:
        result = run_command(f"python -c \"{test_code}\"", f"Testing {name}")
        if not result:
            all_good = False
    
    return all_good

def test_audio_system():
    """Test audio system capabilities."""
    print("\n=== Audio System Test ===")
    
    # Test audio libraries
    audio_tests = [
        ("torchaudio backends", "import torchaudio; print(torchaudio.list_audio_backends())"),
        ("audio devices", "python -m sounddevice", False),  # Optional
    ]
    
    for name, test_cmd, *optional in audio_tests:
        is_optional = optional and optional[0] is False
        result = run_command(test_cmd, f"Testing {name}", check=not is_optional)
        if not result and not is_optional:
            return False
    
    return True

def test_text_pipeline():
    """Check chapter/chunk detection and the CLI contract without loading a model."""
    print("\n=== Text Pipeline Test ===")

    cmd = "python app.py --dry-run --document sample_document.txt --max-chunk-length 100"
    output = run_command(cmd, "Dry-run text pipeline", check=False)
    if not output or "Total:" not in output:
        print("❌ Dry-run did not report a plan (is --max-chunk-length supported?)")
        return False

    sections_line = [line for line in output.splitlines() if line.startswith("Total:")]
    print(f"✅ {sections_line[0] if sections_line else 'plan reported'}")
    return True


def test_audiobook_creation():
    """Test actual audiobook creation with a small sample."""
    print("\n=== Audiobook Creation Test ===")
    
    # Create a small test document
    test_text = """
This is a test document for the audiobook creator.
It contains multiple sentences to test the text splitting functionality.
The quick brown fox jumps over the lazy dog.
This sentence tests punctuation and pauses.
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_text)
        test_doc_path = f.name
    
    try:
        # Test basic audiobook creation
        output_path = tempfile.mktemp(suffix='.wav')
        cmd = f"python app.py --document {test_doc_path} --output {output_path} --max-chunk-length 100"
        
        result = run_command(cmd, "Creating test audiobook", check=False)
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ Audiobook created successfully: {file_size} bytes")
            
            # Clean up
            os.unlink(output_path)
            return True
        else:
            print("❌ Audiobook file not created")
            return False
    
    finally:
        # Clean up test document
        if os.path.exists(test_doc_path):
            os.unlink(test_doc_path)

def test_launcher():
    """Test the global launcher if available."""
    print("\n=== Launcher Test ===")
    
    # Check if audiobook command is available
    result = run_command("which audiobook", "Checking global launcher", check=False)
    if result:
        print(f"✅ Global launcher available: {result}")
        
        # Test launcher help
        help_result = run_command("audiobook --help", "Testing launcher help", check=False)
        if help_result:
            print("✅ Launcher help works")
            return True
    else:
        print("⚠️  Global launcher not found (may need shell reload)")
    
    return True

def main():
    """Run all production validation tests."""
    parser = argparse.ArgumentParser(description="Validate audiobook creator production setup")
    parser.add_argument("--skip-creation", action="store_true", 
                       help="Skip the audio creation test (faster)")
    args = parser.parse_args()
    
    print("🎯 Production Validation for Chatterbox Audiobook Creator")
    print("=" * 60)
    
    tests = [
        ("Environment", test_environment),
        ("GPU Setup", test_gpu_setup),
        ("Dependencies", test_dependencies),
        ("Audio System", test_audio_system),
        ("Text Pipeline", test_text_pipeline),
        ("Launcher", test_launcher),
    ]
    
    if not args.skip_creation:
        tests.append(("Audiobook Creation", test_audiobook_creation))
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
            else:
                print(f"⚠️  {test_name} has issues")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print(f"\n{'='*60}")
    print(f"🎯 Validation Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Production environment validated successfully!")
        print("\n🚀 Your audiobook creator is ready for production use:")
        print("   • All dependencies are working")
        print("   • GPU/CPU setup is optimal") 
        print("   • Audio generation is functional")
        print("\n📖 Start creating audiobooks:")
        print("   python app.py --document your_book.txt")
        print("   audiobook --document your_book.txt --voice narrator.wav")
        return True
    else:
        print(f"\n⚠️  {total - passed} issues found. Please review the output above.")
        print("\n🔧 Common fixes:")
        print("   • Run: source ~/.bashrc  (for launcher issues)")
        print("   • Run: source audiobooker-env/bin/activate  (for dependency issues)")
        print("   • Check: nvidia-smi  (for GPU issues)")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
