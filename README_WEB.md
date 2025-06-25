# Web Interface Usage Guide

## 🌐 Audiobook Creator Web Interface

The web interface provides an easy-to-use browser-based interface for creating audiobooks without needing to use command line tools.

## 🚀 Quick Start

### 1. Start the Web Interface

```bash
# Using the convenient startup script
./start_web.sh

# Or manually
source audiobooker-env/bin/activate
python web_interface.py
```

### 2. Access the Interface

Open your browser and go to:
- **Local access:** http://localhost:7860
- **Network access:** http://YOUR_SERVER_IP:7860

## 📋 Features

### Text Input Options
- **Type directly:** Paste your text into the text box
- **Upload file:** Upload a .txt file containing your book

### Voice Cloning (Optional)
- Upload a 5-30 second clear voice sample
- Supports .wav, .mp3, .m4a, .flac formats
- Single speaker, clear audio works best

### Generation Settings
- **Emotion Exaggeration:** 0.0-1.0 (higher = more expressive)
- **CFG Weight:** 0.0-1.0 (lower = faster speech, higher = more careful)
- **Chapter Pause:** 0.0-5.0 seconds (pause around chapter titles)
- **Output Filename:** Name for your audiobook file

## 🎯 Usage Examples

### Basic Audiobook
1. Paste or upload your text
2. Click "Generate Audiobook"
3. Download the result

### With Voice Cloning
1. Upload a clear voice sample (5-30 seconds)
2. Add your text content
3. Adjust settings if needed
4. Generate and download

### Custom Settings
- **Expressive narration:** Set Exaggeration to 0.7-0.8
- **Fast reading:** Set CFG Weight to 0.3-0.4
- **Professional pause:** Set Chapter Pause to 1.5-2.0 seconds

## 📚 Chapter Detection

The interface automatically detects chapter titles like:
- Chapter 1: Title
- CHAPTER 2: Title
- Ch. 3 Title
- Part 1: Title
- Section 1: Title

**Pauses are automatically added:**
- Before chapter title (configurable)
- After chapter title (configurable)

## 🛠️ Technical Details

### System Requirements
- Same as command line version
- Additional: Gradio web framework
- Recommended: 8GB+ RAM for smooth operation

### Performance
- First generation may take longer (model loading)
- Subsequent generations are faster
- GPU acceleration automatically used if available

### File Handling
- Text files: Auto-detected encoding
- Audio files: Converted automatically
- Output: WAV format, 24kHz sample rate

## 🔧 Troubleshooting

### Interface Won't Start
```bash
# Check if Gradio is installed
pip list | grep gradio

# Install if missing
pip install gradio>=4.0.0

# Check for port conflicts
netstat -tlnp | grep 7860
```

### Generation Fails
- Check that the model loaded successfully in console output
- Ensure sufficient disk space for output files
- Verify text content is not empty
- Check voice file format if using voice cloning

### Slow Performance
- Use GPU if available (shows in interface)
- Reduce text length for testing
- Close other applications using GPU/RAM

### Network Access Issues
```bash
# Check firewall settings
sudo ufw status

# Allow port 7860 if needed
sudo ufw allow 7860

# Find your server IP
hostname -I
```

## 📱 Mobile Usage

The interface is responsive and works on:
- Tablets and phones
- Mobile browsers
- Touch-friendly controls
- File upload from mobile devices

## 🔒 Security Notes

- Interface runs on local network by default
- Set `share=True` in code for public links (use carefully)
- No authentication built-in (add if exposing publicly)
- Uploaded files are temporary and cleaned up

## 🎨 Customization

You can modify `web_interface.py` to:
- Change the interface theme
- Add new settings or controls
- Modify the layout
- Add authentication
- Change default values

## 📊 Monitoring

The interface provides real-time status including:
- Processing progress
- Chapter detection results
- Generation statistics
- Error messages and troubleshooting

## 🚀 Advanced Usage

### Running as a Service

Create a systemd service for automatic startup:

```bash
sudo nano /etc/systemd/system/audiobook-web.service
```

```ini
[Unit]
Description=Audiobook Creator Web Interface
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/audiobooker
Environment=PATH=/path/to/audiobooker/audiobooker-env/bin
ExecStart=/path/to/audiobooker/audiobooker-env/bin/python web_interface.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable audiobook-web
sudo systemctl start audiobook-web
```

### Reverse Proxy Setup

For production deployment behind nginx:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:7860;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 💡 Tips for Best Results

1. **Text Preparation:**
   - Use clear chapter headings
   - Remove excessive formatting
   - Check for typos and formatting issues

2. **Voice Samples:**
   - 10-20 seconds is optimal
   - Single speaker only
   - Clear, uncompressed audio
   - Consistent tone and pace

3. **Settings:**
   - Start with defaults
   - Adjust based on preview results
   - Save settings that work well for you

4. **Performance:**
   - Process shorter sections for testing
   - Use GPU for faster generation
   - Close unnecessary applications
