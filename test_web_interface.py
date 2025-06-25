#!/usr/bin/env python3
"""
Test script for the web interface - verifies imports and basic functionality
"""

import sys
import os

def test_web_interface():
    """Test that the web interface can be imported and basic functions work."""
    print("🧪 Testing Web Interface Components...")
    
    try:
        # Test basic imports
        import gradio as gr
        print(f"✅ Gradio {gr.__version__} imported successfully")
    except ImportError as e:
        print(f"❌ Gradio import failed: {e}")
        return False
    
    try:
        # Test our app imports
        from app import detect_chapters, smart_text_split, VERSION
        print(f"✅ App functions imported successfully (v{VERSION})")
    except ImportError as e:
        print(f"❌ App import failed: {e}")
        return False
    
    try:
        # Test web interface import
        from web_interface import create_interface, load_model
        print("✅ Web interface functions imported successfully")
    except ImportError as e:
        print(f"❌ Web interface import failed: {e}")
        return False
    
    # Test chapter detection with sample text
    try:
        sample_text = """Chapter 1: Test
        
        This is some sample content.
        
        Chapter 2: Another Test
        
        More content here."""
        
        sections = detect_chapters(sample_text)
        chapter_count = sum(1 for section in sections if section['is_chapter_title'])
        print(f"✅ Chapter detection test passed: {len(sections)} sections, {chapter_count} chapters")
    except Exception as e:
        print(f"❌ Chapter detection test failed: {e}")
        return False
    
    print("\n🎉 All web interface tests passed!")
    print("\n🚀 You can now start the web interface with:")
    print("   ./start_web.sh")
    print("\n🌐 Or manually with:")
    print("   python web_interface.py")
    
    return True

def main():
    print("=== Audiobook Creator Web Interface Test ===\n")
    
    if not test_web_interface():
        print("\n❌ Web interface tests failed.")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
