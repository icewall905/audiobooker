# Web Interface Guide

## 🌐 Chatterbox Audiobook Creator Web Interface

The web interface provides an easy-to-use browser-based way to create audiobooks without using the command line.

### Features

- 📝 **Text Input**: Type or paste text directly into the interface
- 📄 **File Upload**: Upload `.txt` documents 
- 🎤 **Voice Cloning**: Upload voice samples for personalized narration
- 📖 **Auto Chapter Detection**: Automatically detects and adds pauses around chapters
- ⚙️ **Adjustable Settings**: Control speech expressiveness and timing
- 📊 **Real-time Progress**: See detailed progress and statistics
- 🎧 **Instant Playback**: Listen to your audiobook immediately

### Quick Start

1. **Launch the web interface:**
   ```bash
   ./start_web.sh
   ```

2. **Open your browser and go to:**
   - Local: http://localhost:7860
   - Network: http://YOUR_SERVER_IP:7860

3. **Create your audiobook:**
   - Enter text or upload a `.txt` file
   - Optionally upload a voice sample
   - Adjust settings if desired
   - Click "Generate Audiobook"

### Settings Explained

#### Audio Settings

- **Emotion Exaggeration (0.0-1.0)**
  - `0.0-0.3`: Calm, neutral delivery
  - `0.4-0.6`: Balanced expression (recommended)
  - `0.7-1.0`: Very expressive, dramatic delivery

- **CFG Weight (0.0-1.0)**
  - `0.0-0.3`: Faster, more fluid speech
  - `0.4-0.6`: Natural pacing (recommended)
  - `0.7-1.0`: Slower, more deliberate speech

- **Chapter Pause (0.0-5.0 seconds)**
  - `0.0`: No pauses between chapters
  - `1.0-2.0`: Natural chapter breaks (recommended)
  - `3.0-5.0`: Long dramatic pauses

### Voice Cloning

The web interface supports voice cloning with uploaded audio samples:

- **Supported formats**: `.wav`, `.mp3`, `.m4a`, `.flac`
- **Recommended**: 10-30 seconds of clear speech
- **Quality tips**:
  - Use high-quality recordings
  - Minimize background noise
  - Single speaker only
  - Clear, natural speech

### Chapter Detection

The system automatically detects common chapter patterns:

- `Chapter 1`, `Chapter 2`, etc.
- `CHAPTER 1`, `CHAPTER 2`, etc.
- `Ch. 1`, `Ch. 2`, etc.
- `Part 1`, `Part 2`, etc.
- `Section 1`, `Section 2`, etc.
- `Book 1`, `Book 2`, etc.

**Chapter Processing:**
1. Text before chapter title → [pause] → Chapter title → [pause] → Chapter content
2. Pauses are added both before and after chapter titles
3. Configurable pause duration

### Example Usage

#### Basic Text Input
```
Chapter 1: The Beginning

Once upon a time, in a land far away, there lived a young adventurer named Alex.

Chapter 2: The Journey

Alex set out on a quest to find the legendary crystal of power.
```

#### With Voice Sample
1. Upload your text or document
2. Upload a voice sample (e.g., `my_voice.wav`)
3. The system will clone your voice for narration

### Performance Tips

#### GPU vs CPU
- **GPU (CUDA)**: Much faster generation, recommended for longer texts
- **CPU**: Slower but works on any system

#### Text Length Guidelines
- **Short texts** (< 1,000 words): Fast generation
- **Medium texts** (1,000-10,000 words): 5-15 minutes
- **Long texts** (> 10,000 words): 15+ minutes

#### Optimization
- Use shorter paragraphs for better chunking
- Clear chapter markers improve structure
- High-quality voice samples improve cloning

### Troubleshooting

#### Common Issues

**"Model loading failed"**
- Ensure you have enough GPU memory (4GB+ recommended)
- Try restarting the interface
- Check if CUDA is properly installed

**"No audio generated"**
- Verify your text isn't empty
- Check for special characters that might cause issues
- Try with simpler test text first

**"File upload failed"**
- Ensure file is plain text (.txt)
- Check file encoding (UTF-8 recommended)
- Verify file size isn't too large (< 10MB recommended)

**Web interface won't start**
- Run `./setup_ubuntu.sh` to ensure all dependencies are installed
- Check if port 7860 is already in use
- Activate the virtual environment manually and try again

### Advanced Usage

#### Network Access
To allow access from other computers on your network:

1. Note your server's IP address:
   ```bash
   hostname -I
   ```

2. Access from other devices:
   ```
   http://YOUR_SERVER_IP:7860
   ```

#### Custom Port
To use a different port, edit `web_interface.py`:
```python
interface.launch(server_port=8080)  # Change 7860 to desired port
```

### API Integration

The web interface runs on Gradio, which automatically provides API endpoints:

- **API docs**: http://localhost:7860/docs
- **Direct API calls**: Available for automation

### Support

If you encounter issues:

1. Check the terminal output for error messages
2. Ensure all dependencies are properly installed
3. Verify your system meets the requirements
4. Try with simpler test cases first

For hardware requirements and installation, see the main [README.md](README.md) and [UBUNTU_SETUP.md](UBUNTU_SETUP.md).
