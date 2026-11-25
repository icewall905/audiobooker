# Chapter Splitting and MP3 Conversion

Two opt-in output modes are available: one file per chapter, and MP3 encoding.

> Both are **off by default**: `audiobook --document book.txt` writes a single
> `my_audiobook.wav`. The legacy `app.create_audiobook()` helper keeps the old
> `split_chapters=True` / `convert_mp3=True` defaults, so existing scripts behave
> as before.

## Enabling them

```bash
# one file per chapter: chapter1.wav, chapter2.wav, ...
audiobook --document book.txt --split-chapters

# single file, encoded to MP3 (ffmpeg required; the WAV is removed on success)
audiobook --document book.txt --mp3

# both
audiobook --document book.txt --split-chapters --mp3
```

`--no-split-chapters` and `--no-mp3` are accepted for compatibility with the
0.2-era scripts and simply keep the default behaviour.

## How chapter splitting works

* Chapters come from the usual heading detection (`Chapter 12`, `CHAPTER IV`,
  `Part two`, `Prologue`, markdown `#` headings, or `--chapter-pattern`).
* Text before the first heading (a preface) is kept with chapter 1 rather than
  being dropped.
* Each chapter is assembled from the already-rendered section parts, so
  checkpoints, resume and the per-section failure reporting all still apply.
* If the document has no headings, or only one chapter, the normal output file
  name is used instead of `chapter1.wav`.
* Chapter pauses (`--chapter-pause`) stay inside the file of the chapter they
  belong to.

## MP3 conversion

* Uses `ffmpeg -codec:a libmp3lame -q:a 2`.
* If `ffmpeg` is missing or conversion fails, the WAV is kept and a warning is
  printed; the job still succeeds.
* MP3 output is produced from the final WAV, so re-running with `--mp3` after a
  completed run re-encodes instead of re-synthesising.

## Practical notes

* With `--split-chapters`, `result.output_paths` (and the CLI summary) lists every
  file that was written.
* Splitting happens after rendering, so it does not change memory use: the
  streaming, per-section writer already keeps that flat.
* `--dry-run` shows the detected chapters and chunk counts before you commit to a
  long render:

```bash
audiobook --document book.txt --dry-run
```
