# Chapter Splitting and MP3 Conversion

This document explains the chapter splitting and MP3 conversion features of the audiobook creator.

## Default Behavior

**The audiobook creator now has the following defaults:**
- ✅ **Chapter splitting is ENABLED by default**
- ✅ **MP3 conversion is ENABLED by default**
- ✅ **Files are saved in `./output/` directory**

This means that by default, each chapter will be saved as a separate MP3 file in the output directory.

## Features

### 1. Chapter Splitting (Default: Enabled)

The audiobook creator splits each chapter into separate files while maintaining the pauses between chapters.

**Benefits:**
- Each chapter is saved as an individual file (e.g., `chapter1.mp3`, `chapter2.mp3`)
- Easier to navigate and manage large audiobooks
- Better compatibility with audio players and streaming services
- Reduced memory usage when processing large documents

**How it works:**
- Chapters are detected using common patterns (Chapter 1, CHAPTER 1, etc.)
- Each chapter's audio (including title, content, and pauses) is saved separately
- Pauses between chapters are preserved within each chapter file
- Files are named sequentially: `chapter1`, `chapter2`, etc.

### 2. MP3 Conversion (Default: Enabled)

The audiobook creator converts the final output to MP3 format for better compatibility and smaller file sizes.

**Benefits:**
- Smaller file sizes compared to WAV
- Better compatibility with most audio players and devices
- Easier to share and distribute
- Standard format for streaming services

**Requirements:**
- `ffmpeg` must be installed on your system
- The conversion uses high-quality settings (VBR quality 2)

## Usage Examples

### Default Behavior (Recommended)
```bash
python app.py --document book.txt
```

This will create separate MP3 files for each chapter in the `output/` directory.

### Single File Output
```bash
python app.py --document book.txt --no-split-chapters
```

This will create a single MP3 file containing the entire audiobook.

### WAV Format Only
```bash
python app.py --document book.txt --no-mp3
```

This will create separate WAV files for each chapter.

### Legacy Behavior (Single WAV File)
```bash
python app.py --document book.txt --no-split-chapters --no-mp3
```

This creates a single WAV file (original behavior).

### Custom Chapter Pause
```bash
python app.py --document book.txt --chapter-pause 2.0
```

This creates separate MP3 chapters with 2-second pauses between chapters.

### Using Voice Reference
```bash
python app.py --document book.txt --voice example.wav
```

This uses a voice reference file and creates separate MP3 chapters.

## Command Line Options

### Options to Disable Defaults

- `--no-split-chapters`: Don't split chapters (create single file)
- `--no-mp3`: Don't convert to MP3 (keep WAV format)

### Existing Options (still available)

- `--document` or `-d`: Path to the text document
- `--voice` or `-v`: Path to voice reference audio
- `--output` or `-o`: Path for the output audiobook
- `--exaggeration` or `-e`: Emotion exaggeration (0.0-1.0)
- `--cfg-weight` or `-c`: CFG weight (0.0-1.0)
- `--device`: Device to use (cuda/cpu)
- `--chapter-pause`: Pause duration between chapters in seconds
- `--no-voice`: Don't use voice reference

## Output Files

### Default Behavior (Chapter Splitting + MP3):

**Files in `output/` directory:**
- `chapter1.mp3`
- `chapter2.mp3`
- `chapter3.mp3`
- etc.

### When using `--no-split-chapters`:

**With MP3 (default):**
- `output/my_audiobook.mp3` (or custom output name)

**With `--no-mp3`:**
- `output/my_audiobook.wav` (or custom output name)

### When using `--no-mp3`:

**With chapter splitting (default):**
- `output/chapter1.wav`
- `output/chapter2.wav`
- `output/chapter3.wav`
- etc.

## Chapter Detection

The system automatically detects chapters using these patterns:
- `Chapter 1`, `CHAPTER 1`
- `Ch. 1`
- `1. Title`
- `Part 1`, `PART 1`
- `Section 1`
- `Book 1`

If no chapters are detected, the entire document is treated as a single chapter.

## Testing

Run the test script to verify the new features:

```bash
python test_chapter_splitting.py
```

This will test the default behavior and various options.

## System Requirements

### For MP3 Conversion:
- `ffmpeg` must be installed on your system
- On Ubuntu/Debian: `sudo apt install ffmpeg`
- On macOS: `brew install ffmpeg`
- On Windows: Download from https://ffmpeg.org/

### For Chapter Splitting:
- No additional requirements beyond the existing dependencies

## Troubleshooting

### MP3 Conversion Fails
If you see "Warning: ffmpeg not found. Skipping MP3 conversion":
1. Install ffmpeg on your system
2. Ensure ffmpeg is in your system PATH
3. The script will fall back to WAV format

### No Chapters Detected
If no chapters are found in your document:
1. Check that your document uses standard chapter formatting
2. The entire document will be treated as a single chapter
3. You can still use `--no-split-chapters` to create a single file

### Memory Issues with Large Documents
If you encounter memory issues:
1. Chapter splitting is enabled by default, which helps with memory usage
2. Use `--device cpu` if GPU memory is limited
3. Consider processing the document in smaller sections

## Performance Notes

- Chapter splitting may slightly increase processing time due to additional file I/O
- MP3 conversion adds minimal overhead
- The quality of MP3 output is high (VBR quality 2)
- WAV files are automatically cleaned up after successful MP3 conversion
- All output files are organized in the `output/` directory

## Version History

- **v0.0.3**: Added chapter splitting and MP3 conversion as default behavior
- **v0.0.2**: Original version with single file output 