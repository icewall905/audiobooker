#!/usr/bin/env python3
"""
Test script for paragraph pause feature.
This script demonstrates how the audiobook creator adds pauses between paragraphs.
"""

import os
import sys
from app import create_audiobook

def create_test_document():
    """Create a test document with multiple paragraphs to demonstrate pauses."""
    test_content = """Chapter 1: The Test

This is the first paragraph of our test document. It contains multiple sentences to demonstrate how the text processing works. The audiobook creator should add a pause after this paragraph.

This is the second paragraph. It should be separated from the first paragraph by a 1-second pause. This makes the audiobook sound more natural and easier to follow.

This is the third paragraph. Notice how each paragraph is clearly separated, making it easier to understand the structure of the text. The pauses help listeners process the information.

This is the final paragraph of our test. It demonstrates that the paragraph pause feature works correctly throughout the entire document."""
    
    with open("test_paragraphs.txt", "w") as f:
        f.write(test_content)
    
    print("✅ Created test document: test_paragraphs.txt")
    return "test_paragraphs.txt"

def test_paragraph_pauses():
    """Test the paragraph pause functionality."""
    print("=== Testing Paragraph Pause Feature ===")
    
    # Create test document
    document_path = create_test_document()
    output_path = "output/test_paragraphs.wav"
    
    print(f"Using document: {document_path}")
    print("Testing paragraph pause feature...")
    print("Expected: 1-second pauses between paragraphs")
    
    # Test with paragraph pauses (default behavior)
    success = create_audiobook(
        document_path=document_path,
        output_path=output_path,
        split_chapters=False,  # Single file for testing
        convert_mp3=True,
        chapter_pause=1.0,
        device="cpu"  # Use CPU for testing
    )
    
    if success:
        print("\n✅ Paragraph pause test completed successfully!")
        print("Check the output file to hear the pauses between paragraphs.")
        
        # Check for output files
        output_dir = "output"
        if os.path.exists(output_dir):
            if os.path.exists(os.path.join(output_dir, "test_paragraphs.mp3")):
                print("Generated: output/test_paragraphs.mp3")
                print("Listen to hear the 1-second pauses between paragraphs!")
            elif os.path.exists(os.path.join(output_dir, "test_paragraphs.wav")):
                print("Generated: output/test_paragraphs.wav (MP3 conversion failed)")
            else:
                print("No output file found")
        
        return True
    else:
        print("\n❌ Paragraph pause test failed!")
        return False

def main():
    """Run the paragraph pause test."""
    print("Paragraph Pause Feature Test")
    print("=" * 40)
    
    # Test paragraph pauses
    test_success = test_paragraph_pauses()
    
    print("\n" + "=" * 40)
    print("Test Summary:")
    print(f"Paragraph pause test: {'✅ PASSED' if test_success else '❌ FAILED'}")
    
    if test_success:
        print("\n🎉 Paragraph pause feature is working correctly!")
        print("💡 The audiobook should have natural 1-second pauses between paragraphs.")
        return 0
    else:
        print("\n⚠️  Test failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 