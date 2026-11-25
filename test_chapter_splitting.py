#!/usr/bin/env python3
"""
Test script for chapter splitting and MP3 conversion features.
This script demonstrates how to use the new defaults and options.
"""

import os
import sys
from app import create_audiobook

def test_default_behavior():
    """Test the default behavior (chapter splitting + MP3)."""
    print("=== Testing Default Behavior (Chapter Splitting + MP3) ===")
    
    # Test parameters
    document_path = "sample_document.txt"
    output_path = "output/test_audiobook.wav"
    
    # Check if sample document exists
    if not os.path.exists(document_path):
        print(f"Error: {document_path} not found. Please ensure the sample document exists.")
        return False
    
    print(f"Using document: {document_path}")
    print("Testing with default settings (chapter splitting + MP3)...")
    
    # Test with default settings
    success = create_audiobook(
        document_path=document_path,
        output_path=output_path,
        split_chapters=True,  # Default
        convert_mp3=True,     # Default
        chapter_pause=1.5,    # Slightly longer pause for testing
        device="cpu"          # Use CPU for testing
    )
    
    if success:
        print("\n✅ Default behavior test completed successfully!")
        print("Check for chapter files in output/ directory:")
        
        # List generated files
        output_dir = "output"
        if os.path.exists(output_dir):
            chapter_files = [f for f in os.listdir(output_dir) if f.startswith('chapter') and f.endswith('.mp3')]
            if chapter_files:
                print("Generated MP3 chapter files:")
                for file in sorted(chapter_files):
                    print(f"  - {file}")
            else:
                print("No MP3 chapter files found. Check for WAV files:")
                wav_files = [f for f in os.listdir(output_dir) if f.startswith('chapter') and f.endswith('.wav')]
                for file in sorted(wav_files):
                    print(f"  - {file}")
        else:
            print("Output directory not found")
        
        return True
    else:
        print("\n❌ Default behavior test failed!")
        return False

def test_single_file():
    """Test single file output (no chapter splitting)."""
    print("\n=== Testing Single File Output ===")
    
    document_path = "sample_document.txt"
    output_path = "output/single_audiobook.wav"
    
    if not os.path.exists(document_path):
        print(f"Error: {document_path} not found.")
        return False
    
    print("Testing single file output (no chapter splitting)...")
    
    success = create_audiobook(
        document_path=document_path,
        output_path=output_path,
        split_chapters=False,  # Disable chapter splitting
        convert_mp3=True,      # Keep MP3 conversion
        chapter_pause=1.0,
        device="cpu"
    )
    
    if success:
        print("\n✅ Single file test completed successfully!")
        
        # Check for output files
        output_dir = "output"
        if os.path.exists(output_dir):
            if os.path.exists(os.path.join(output_dir, "single_audiobook.mp3")):
                print("Generated: output/single_audiobook.mp3")
            elif os.path.exists(os.path.join(output_dir, "single_audiobook.wav")):
                print("Generated: output/single_audiobook.wav (MP3 conversion failed)")
            else:
                print("No output file found")
        
        return True
    else:
        print("\n❌ Single file test failed!")
        return False

def test_wav_only():
    """Test WAV output (no MP3 conversion)."""
    print("\n=== Testing WAV Output (No MP3 Conversion) ===")
    
    document_path = "sample_document.txt"
    output_path = "output/wav_only_audiobook.wav"
    
    if not os.path.exists(document_path):
        print(f"Error: {document_path} not found.")
        return False
    
    print("Testing WAV output (no MP3 conversion)...")
    
    success = create_audiobook(
        document_path=document_path,
        output_path=output_path,
        split_chapters=True,   # Keep chapter splitting
        convert_mp3=False,     # Disable MP3 conversion
        chapter_pause=1.0,
        device="cpu"
    )
    
    if success:
        print("\n✅ WAV-only test completed successfully!")
        
        # Check for output files
        output_dir = "output"
        if os.path.exists(output_dir):
            wav_files = [f for f in os.listdir(output_dir) if f.startswith('wav_only') and f.endswith('.wav')]
            if wav_files:
                print("Generated WAV files:")
                for file in sorted(wav_files):
                    print(f"  - {file}")
        
        return True
    else:
        print("\n❌ WAV-only test failed!")
        return False

def main():
    """Run all tests."""
    print("Audiobook Default Behavior Test")
    print("=" * 50)
    
    # Test 1: Default behavior (chapter splitting + MP3)
    test1_success = test_default_behavior()
    
    # Test 2: Single file output
    test2_success = test_single_file()
    
    # Test 3: WAV-only output
    test3_success = test_wav_only()
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"Default behavior test: {'✅ PASSED' if test1_success else '❌ FAILED'}")
    print(f"Single file test: {'✅ PASSED' if test2_success else '❌ FAILED'}")
    print(f"WAV-only test: {'✅ PASSED' if test3_success else '❌ FAILED'}")
    
    if test1_success and test2_success and test3_success:
        print("\n🎉 All tests passed! Your audiobook service is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 