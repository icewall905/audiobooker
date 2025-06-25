#!/usr/bin/env python3
"""Simple test for web interface imports and basic functionality."""

import sys
import os

def test_web_interface():
    """Test that the web interface can be imported and basic functions work."""
    print("Testing web interface imports and functionality...")
    
    try:
        # Test basic imports
        import torch
        print(f"✅ PyTorch {torch.__version__} imported")
        
        import torchaudio
        print(f"✅ TorchAudio {torchaudio.__version__} imported")
        
        try:
            import gradio as gr
            print(f"✅ Gradio {gr.__version__} imported")
        except ImportError:
            print("❌ Gradio not found - install with: pip install gradio")
            return False
        
        # Test our app imports
        try:
            from app import detect_chapters, smart_text_split, VERSION
            print(f"✅ App functions imported (version {VERSION})")
        except ImportError as e:
            print(f"❌ Failed to import from app.py: {e}")
            return False
        
        # Test chapter detection function
        test_text = """Chapter 1: Test
        
        This is test content.
        
        Chapter 2: Another Test
        
        More content here."""
        
        sections = detect_chapters(test_text)
        print(f"✅ Chapter detection test: Found {len(sections)} sections")
        
        # Check if we can create a simple interface
        try:
            with gr.Blocks() as test_interface:
                gr.Markdown("# Test Interface")
                gr.Textbox(label="Test")
            print("✅ Gradio interface creation test passed")
        except Exception as e:
            print(f"❌ Gradio interface test failed: {e}")
            return False
        
        print("\n🎉 All web interface tests passed!")
        print("\nTo start the web interface:")
        print("  ./start_web.sh")
        print("  or")
        print("  python web_interface.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_web_interface()
    sys.exit(0 if success else 1)
