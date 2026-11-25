# Ubuntu Server Setup Guide

## Overview

`setup_ubuntu.sh` installs the `audiobooker` package into a virtual environment and
puts the `audiobook` / `audiobook-remote` / `audiobook-web` commands on your `PATH`.
It no longer writes a second copy of `app.py`: it uses this repository (or clones it
when the script is piped from `curl`) and runs `pip install -e .`.

## One-command install

```bash
curl -sSL https://raw.githubusercontent.com/icewall905/audiobooker/main/setup_ubuntu.sh | bash
```

Then, in a new shell:

```bash
audiobook --document my_book.txt
```

## From a checkout

```bash
git clone https://github.com/icewall905/audiobooker.git
cd audiobooker
./setup_ubuntu.sh            # apt packages + venv + torch + chatterbox + this package
```

Options:

| Flag | Effect |
|---|---|
| `--dir PATH` | parent directory for the checkout (`./audiobooker` by default) |
| `--cpu` | install CPU-only torch even when a GPU is present |
| `--skip-apt` | skip `apt-get` (useful in containers) |
| `--repo URL` / `--ref BRANCH` | clone from somewhere else |
| `PYTHON_BIN=python3.11 ./setup_ubuntu.sh` | pick the interpreter |

The script installs: `python3`, `python3-venv`, `python3-pip`, `python3-dev`, `git`,
`curl`, `ffmpeg`, `build-essential`, `libsndfile1`.

## Manual install

```bash
python3 -m venv audiobooker-env
source audiobooker-env/bin/activate

# torch first, from the index that matches your hardware
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118   # GPU
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu     # CPU

pip install -e .                 # this package (numpy only, no torch pulled in)
pip install chatterbox-tts gradio requests
```

Do **not** `pip install argparse` or `pip install pathlib`: those PyPI packages shadow
the standard library modules and break unrelated imports.

## Verify the installation

```bash
audiobook --version
audiobook --dry-run --document sample_document.txt     # no model load, no GPU needed
python validate_production.py                          # full environment check
```

## Where things live

```
~/…/audiobooker/
├── audiobooker/            the package (all logic)
├── app.py                  thin wrapper, kept so `python app.py` still works
├── web_interface.py        thin wrapper for the Gradio UI
├── tests/                  pytest suite (no GPU required)
├── pyproject.toml          packaging + console scripts
└── audiobooker-env/        virtual environment created by the installer
```

## Remote server

`setup_ubuntu.sh` is only needed on the machine that runs the model. Other machines can
install the lightweight client:

```bash
pip install -e ".[remote]"
audiobook-remote --server http://10.0.10.23:7860 --document book.txt
```

An existing Gradio Chatterbox server can keep running alongside this setup.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `audiobook: command not found` | open a new shell or `source ~/.bashrc` |
| `chatterbox-tts is not installed` | `pip install -e ".[local]"` |
| CUDA not detected | check `nvidia-smi`, then re-run with `--cpu` to confirm the app itself works |
| `No module named encodings` | the venv was built with a Python that is gone; delete `audiobooker-env` and re-run the installer |
| job stopped halfway | re-run the same `audiobook` command; finished sections are reused |
