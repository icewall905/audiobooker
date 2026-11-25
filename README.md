# Audiobook Creator with Chatterbox TTS

Turn text documents into audiobooks with [Chatterbox TTS](https://github.com/resemble-ai/chatterbox).
Runs on an Ubuntu box with an NVIDIA GPU (CPU works too, just slower) or against a
remote Chatterbox server.

Version 0.2.0 replaced the duplicated single-file scripts with one package, so every
entry point shares the same text handling, checkpointing and error reporting.

## Quick start

```bash
# Ubuntu server, fresh machine (clones the repo, creates a venv, installs everything)
curl -sSL https://raw.githubusercontent.com/icewall905/audiobooker/main/setup_ubuntu.sh | bash

# or, from an existing checkout
./quick_setup.sh

audiobook --document my_book.txt --voice narrator.wav
```

## Install options

| Situation | Command |
|---|---|
| Repo checkout, full local stack | `pip install -e ".[local,web]"` |
| Remote server only (no torch) | `pip install -e ".[remote]"` |
| Web UI | `pip install -e ".[web]"` |
| Development / tests | `pip install -e ".[dev]"` |

The installer no longer copies `app.py` around: `setup_ubuntu.sh` clones the repo and
runs `pip install -e .`, so the installed program and the repository cannot drift apart
anymore.

## Usage

### Command line

```bash
audiobook --document book.txt                       # default voice
audiobook -d book.txt -v narrator.wav               # voice cloning
audiobook -d book.txt -e 0.7 -c 0.3                 # more expressive / faster speech
audiobook -d book.txt --chapter-pause 1.5           # longer pauses around chapter titles
audiobook -d book.txt --max-chunk-length 200        # smaller TTS prompts
audiobook -d book.txt --dry-run                     # show chapters/chunks, no model load
audiobook -d book.txt                               # re-run the same command to resume
```

`python app.py ...` keeps working and is equivalent to `audiobook ...`.

### Resume, parts and failures

* Each document section is synthesised straight to `my_audiobook.parts/part_000NN.wav`
  while the job runs. Memory use stays flat instead of growing with the book
  length (a 65 minute book needed 40 MB of RSS; buffering it as float32 tensors
  would have needed ~370 MB, ~740 MB at the concatenation peak).
* The parts directory holds a manifest. Re-running the same command skips
  everything that is already rendered, so an interrupted overnight job continues
  where it stopped. `--no-resume` starts over, `--keep-parts` keeps the parts
  after a clean run.
* A chunk that still fails after `--retries` (default 2) is **not** silently
  dropped anymore: it is printed, written to `my_audiobook.failures.json`, the
  process exits non-zero, and the partial section stays in the manifest so the
  next run re-renders only that section. `--strict` aborts instead.

### Web interface

```bash
audiobook-web            # or: ./start_web.sh, or: python web_interface.py
# open http://localhost:7860
```

Paste text or upload a `.txt`, optionally upload a voice sample, and the same
pipeline runs in the background with progress reporting and the same failure
summary.

### Remote server

```bash
audiobook-remote --server http://gpu-box:7860 -d book.txt -v narrator.wav
```

The client reads the sample rate from the server's response (previously it was
hardcoded to 24 kHz, which silently produced pitch-shifted audio from a 32 kHz
server) and retries transient HTTP failures the same way the local engine does.

## Text handling

* Chapters are detected from `Chapter 12`, `CHAPTER IV`, `Part two`, `Ch. 3:`,
  `Prologue`/`Epilogue`/`Introduction`, markdown `#` headings, or a custom
  `--chapter-pattern` regex. Numbered list items (`1. Buy milk`) are no longer
  mistaken for chapter titles.
* Chunks never exceed `--max-chunk-length` characters, even for text without
  punctuation. Sentences are packed whole, and an over-long sentence is split at
  a word or comma boundary.

## Architecture

```
audiobooker/
├── text.py       heading detection, chunking, input validation (stdlib only)
├── audio.py      streaming WAV writer, part concatenation
├── engine.py     ChatterboxEngine (local), RemoteEngine (HTTP)
├── pipeline.py   orchestration: checkpoints, retries, failure reports
├── cli.py        `audiobook`
├── remote_cli.py `audiobook-remote`
├── web.py        `audiobook-web` (Gradio)
└── report.py     console output

app.py, app_remote.py, web_interface.py   thin wrappers, kept for compatibility
```

## Tests

```bash
pip install -e ".[dev]"
pytest            # no GPU, no torch, no network required
```

The suite covers chunking and chapter-detection edge cases, the WAV writer,
checkpoint/resume behaviour, retry and failure reporting, CLI validation (including
`--max-chunk-length`, which `validate_production.py` depends on) and WAV decoding.

## Requirements

* Ubuntu 18.04+ (recommended), Python 3.9+
* NVIDIA GPU with CUDA for local generation (8 GB+ RAM; CPU works slowly)
* ~1 GB of disk per hour of 16-bit audio, plus scratch space for parts
* `ffmpeg` is only needed if you want to convert the WAV afterwards

## Troubleshooting

| Symptom | Fix |
|---|---|
| `chatterbox-tts is not installed` | `pip install -e ".[local]"` |
| `cannot reach Chatterbox server` | check `--server`, the port and the firewall |
| output sounds slow/fast | server sample rate differs; pass `--sample-rate` |
| job stopped halfway | re-run the same command (checkpoints are reused) |
| want to know what will be read | `audiobook --dry-run --document book.txt` |

## License

MIT - see [LICENSE](LICENSE).

## Repository

**GitHub**: https://github.com/icewall905/audiobooker
