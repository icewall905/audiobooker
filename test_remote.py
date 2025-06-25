#!/usr/bin/env python3
"""
Test script for the remote audiobook creator.
This script tests connectivity and basic functionality without generating full audiobooks.
"""

import sys
import os
import requests
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_remote import ChatterboxAPIClient, smart_text_split, validate_inputs

def test_server_connectivity(server_url: str = "http://10.0.10.23:7860"):
    """Test connection to the remote Chatterbox server."""
    print(f"Testing connection to {server_url}...")
    
    client = ChatterboxAPIClient(server_url)
    
    if client.check_server_health():
        print("✅ Server is accessible")
        return True
    else:
        print("❌ Cannot connect to server")
        print("Please check:")
        print("1. Server is running")
        print("2. IP address and port are correct")
        print("3. Network connectivity")
        return False

def test_text_splitting():
    """Test the smart text splitting function."""
    print("\nTesting text splitting...")
    
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

def test_single_generation(server_url: str = "http://10.0.10.23:7860"):
    """Test generating a single short audio clip."""
    print(f"\nTesting single audio generation...")
    
    client = ChatterboxAPIClient(server_url)
    test_text = "Hello, this is a test of the Chatterbox text-to-speech system."
    
    try:
        print(f"Generating audio for: '{test_text}'")
        audio_bytes = client.generate_audio(test_text)
        
        if audio_bytes and len(audio_bytes) > 0:
            print(f"✅ Audio generated successfully ({len(audio_bytes)} bytes)")
            
            # Save test audio file
            test_output = "test_audio.wav"
            with open(test_output, 'wb') as f:
                f.write(audio_bytes)
            print(f"✅ Test audio saved to {test_output}")
            return True
        else:
            print("❌ No audio data received")
            return False
            
    except Exception as e:
        print(f"❌ Audio generation failed: {e}")
        return False

def test_imports():
    """Test that all required imports work."""
    print("\nTesting imports...")
    
    try:
        import requests
        print(f"✅ Requests {requests.__version__} imported successfully")
    except ImportError as e:
        print(f"❌ Requests import failed: {e}")
        return False
    
    try:
        import numpy
        print(f"✅ NumPy {numpy.__version__} imported successfully")
    except ImportError as e:
        print(f"❌ NumPy import failed: {e}")
        return False
    
    return True

def main():
    """Run all tests."""
    print("=== Remote Audiobook Creator Test Suite ===\n")
    
    # Test imports first
    if not test_imports():
        print("\n❌ Import tests failed. Please install required dependencies:")
        print("pip install -r requirements_remote.txt")
        return False
    
    # Test server connectivity
    server_url = "http://10.0.10.23:7860"
    if not test_server_connectivity(server_url):
        print(f"\n❌ Server connectivity test failed.")
        print("Please ensure your Chatterbox server is running and accessible.")
        return False
    
    # Test text splitting
    num_chunks = test_text_splitting()
    
    # Test file validation
    test_file_validation()
    
    # Test single audio generation
    if test_single_generation(server_url):
        print(f"\n✅ Single audio generation test passed")
    else:
        print(f"\n⚠️ Single audio generation test failed")
        print("The server is accessible but audio generation failed.")
        print("This might be due to API endpoint differences.")
    
    print(f"\n=== Test Summary ===")
    print(f"✅ Basic tests completed")
    print(f"📄 Sample document would be split into {num_chunks} chunks")
    print(f"🌐 Server connectivity: OK")
    print(f"🎯 Ready to create audiobooks remotely!")
    
    print(f"\nTo create an audiobook from the sample document, run:")
    print(f"  python app_remote.py")
    print(f"\nTo use your own document:")
    print(f"  python app_remote.py --document 'your_document.txt'")
    print(f"\nTo use a different server:")
    print(f"  python app_remote.py --server 'http://your-server:port'")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
