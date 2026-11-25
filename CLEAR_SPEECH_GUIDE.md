# Clear Speech Guide

This guide provides tips and techniques for achieving clearer, more understandable speech without making it sound robotic.

## 🎯 **Best Practices for Clear Speech**

### 1. **Text Preparation (Most Important)**

**Format your text properly:**
```
Chapter 1: Introduction

This is the first paragraph. It should be well-formatted with proper punctuation.

This is the second paragraph. Notice the empty line between paragraphs.

This is the third paragraph. Each paragraph should be clearly separated.
```

**Tips:**
- Use proper punctuation (periods, commas, question marks)
- Add empty lines between paragraphs
- Break long sentences into shorter ones
- Use clear, simple language
- Avoid run-on sentences

### 2. **Speech Rate Control (New Feature)**

Use the new `--speech-rate` parameter to slow down speech without affecting quality:

```bash
# Slightly slower (recommended)
./audiobook_run.sh --document book.txt --speech-rate 0.8

# Much slower
./audiobook_run.sh --document book.txt --speech-rate 0.6

# Very slow
./audiobook_run.sh --document book.txt --speech-rate 0.5
```

**Speech Rate Guidelines:**
- **1.0**: Normal speed (default)
- **0.9**: Slightly slower
- **0.8**: Slower, good for clarity ⭐ **Recommended**
- **0.7**: Much slower
- **0.6**: Very slow
- **0.5**: Slowest (may affect quality)

### 3. **Voice Quality Settings**

**For maximum clarity:**
```bash
./audiobook_run.sh --document book.txt \
  --speech-rate 0.8 \
  --exaggeration 0.3 \
  --cfg-weight 0.5
```

**Parameter explanations:**
- `--speech-rate 0.8`: Slower speech
- `--exaggeration 0.3`: Less emotional variation (more consistent)
- `--cfg-weight 0.5`: Keep default (avoid robotic sound)

### 4. **Voice Cloning for Consistency**

**Use a clear voice reference:**
```bash
# Record a clear voice sample (5-10 seconds)
# Save as example.wav or use a specific file
./audiobook_run.sh --document book.txt --voice clear_voice.wav --speech-rate 0.8
```

**Voice recording tips:**
- Speak clearly and slowly
- Use a quiet environment
- Record 5-10 seconds of clear speech
- Avoid background noise

### 5. **Text Processing Tips**

**Before processing, clean your text:**
- Remove extra spaces
- Fix punctuation
- Break up long paragraphs
- Add proper chapter markers

**Example of good formatting:**
```
Chapter 1: The Beginning

The story begins on a quiet morning. The sun was just rising over the horizon. Birds were singing in the trees.

Sarah walked down the path. She carried a small bag in her hand. Her footsteps made soft sounds on the gravel.

She stopped to look at the flowers. They were beautiful in the morning light. The colors seemed to glow.
```

### 6. **Advanced Techniques**

**For technical content:**
```bash
./audiobook_run.sh --document technical_book.txt \
  --speech-rate 0.7 \
  --exaggeration 0.2 \
  --chapter-pause 2.0
```

**For educational content:**
```bash
./audiobook_run.sh --document educational_book.txt \
  --speech-rate 0.8 \
  --exaggeration 0.1 \
  --chapter-pause 1.5
```

**For fiction:**
```bash
./audiobook_run.sh --document fiction_book.txt \
  --speech-rate 0.9 \
  --exaggeration 0.4 \
  --chapter-pause 1.0
```

## 🚀 **Quick Start for Clear Speech**

### **Step 1: Prepare Your Text**
- Format with proper paragraphs
- Add punctuation
- Break up long sentences

### **Step 2: Choose Your Settings**
```bash
# For most content (recommended)
./audiobook_run.sh --document book.txt --speech-rate 0.8

# For technical/educational content
./audiobook_run.sh --document book.txt --speech-rate 0.7 --exaggeration 0.2

# For fiction
./audiobook_run.sh --document book.txt --speech-rate 0.9 --exaggeration 0.4
```

### **Step 3: Test and Adjust**
- Start with a small sample
- Listen to the output
- Adjust speech rate if needed
- Try different exaggeration values

## 🎵 **Audio Quality Tips**

### **Post-Processing (Optional)**
If you need even more clarity, you can post-process the audio:

1. **Use audio editing software** (Audacity, etc.)
2. **Apply gentle compression** to even out volume
3. **Add slight reverb** for warmth
4. **Normalize** the audio levels

### **File Format Considerations**
- **MP3**: Good for compatibility, smaller files
- **WAV**: Better quality, larger files
- **Use `--no-mp3`** for WAV output if you plan to post-process

## 🔧 **Troubleshooting**

### **Speech Still Not Clear Enough**
1. **Check your text formatting**
2. **Try lower speech rate** (0.6-0.7)
3. **Use voice cloning** with a clear reference
4. **Reduce exaggeration** to 0.2-0.3

### **Sounds Robotic**
1. **Avoid high CFG weights** (keep at 0.5)
2. **Use moderate exaggeration** (0.3-0.4)
3. **Don't go too slow** (avoid speech-rate below 0.5)

### **Inconsistent Quality**
1. **Use voice cloning** for consistency
2. **Check text formatting** for consistency
3. **Use consistent settings** throughout

## 💡 **Pro Tips**

1. **Text quality matters most** - well-formatted text produces better audio
2. **Start with speech-rate 0.8** - it's usually the sweet spot
3. **Use voice cloning** for professional results
4. **Test with small samples** before processing large documents
5. **Keep CFG weight at default** (0.5) to avoid robotic sound
6. **Paragraph pauses help** - they're added automatically
7. **Chapter splitting** makes it easier to navigate and process

## 🎯 **Recommended Settings by Content Type**

| Content Type | Speech Rate | Exaggeration | Chapter Pause | Notes |
|--------------|-------------|--------------|---------------|-------|
| **General** | 0.8 | 0.3 | 1.0 | Good all-around settings |
| **Technical** | 0.7 | 0.2 | 1.5 | Slower for complex concepts |
| **Educational** | 0.8 | 0.1 | 1.5 | Clear and consistent |
| **Fiction** | 0.9 | 0.4 | 1.0 | More expressive |
| **Children's** | 0.8 | 0.5 | 1.0 | Clear and engaging |

Remember: **Text preparation is 80% of the battle for clear speech!** 