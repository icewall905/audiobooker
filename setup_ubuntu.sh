#!/bin/bash
#
# Ubuntu setup for the audiobook creator.
#
#   ./setup_ubuntu.sh                 # install into ./audiobooker
#   ./setup_ubuntu.sh --dir ~/tools   # install into ~/tools/audiobooker
#   ./setup_ubuntu.sh --cpu           # skip CUDA, install CPU torch
#   ./setup_ubuntu.sh --skip-apt      # do not touch apt
#
# The script installs the package (see pyproject.toml) instead of copying a
# second copy of app.py around, so the installed program and the repository can
# no longer drift apart.
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${BLUE}==>${NC} $*"; }
ok()    { echo -e "${GREEN}✔${NC} $*"; }
warn()  { echo -e "${YELLOW}!${NC} $*"; }
fail()  { echo -e "${RED}✘${NC} $*" >&2; exit 1; }

REPO_URL="https://github.com/icewall905/audiobooker.git"
REF="main"
INSTALL_ROOT="$(pwd)"
USE_CPU=0
SKIP_APT=0

while [ $# -gt 0 ]; do
    case "$1" in
        --dir)      INSTALL_ROOT="${2:?--dir needs a value}"; shift 2 ;;
        --repo)     REPO_URL="${2:?--repo needs a value}"; shift 2 ;;
        --ref)      REF="${2:?--ref needs a value}"; shift 2 ;;
        --cpu)      USE_CPU=1; shift ;;
        --skip-apt) SKIP_APT=1; shift ;;
        -h|--help)  sed -n '2,10p' "$0"; exit 0 ;;
        *)          fail "unknown option: $1" ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------- source tree
if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
    info "Using the existing checkout at $PROJECT_DIR"
else
    PROJECT_DIR="$INSTALL_ROOT/audiobooker"
    if [ -f "$PROJECT_DIR/pyproject.toml" ]; then
        info "Reusing the existing install at $PROJECT_DIR"
    else
        info "Cloning $REPO_URL into $PROJECT_DIR"
        command -v git >/dev/null || fail "git is required to clone the repository"
        mkdir -p "$INSTALL_ROOT"
        git clone --depth 1 --branch "$REF" "$REPO_URL" "$PROJECT_DIR"
    fi
fi
cd "$PROJECT_DIR"

# ------------------------------------------------------------------- apt deps
if [ "$SKIP_APT" -eq 0 ]; then
    info "Installing system packages (needs sudo)"
    sudo apt-get update
    sudo apt-get install -y \
        python3 python3-venv python3-pip python3-dev \
        git curl ffmpeg build-essential libsndfile1
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' \
    || fail "python 3.9 or newer is required"

# ------------------------------------------------------------------ venv + pip
VENV_DIR="$PROJECT_DIR/audiobooker-env"
if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtual environment at $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip setuptools wheel >/dev/null

if [ "$USE_CPU" -eq 1 ]; then
    info "Installing CPU builds of torch/torchaudio"
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
elif command -v nvidia-smi >/dev/null; then
    info "NVIDIA GPU detected - installing CUDA builds of torch/torchaudio"
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
else
    warn "No NVIDIA GPU detected - installing CPU builds (slower)"
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

info "Installing the package (pip install -e .)"
pip install -e .

info "Installing runtime dependencies"
# argparse/pathlib are NOT installed: the PyPI versions shadow the stdlib.
pip install chatterbox-tts gradio requests

# ------------------------------------------------------------------- launcher
BIN_DIR="$VENV_DIR/bin"
if ! grep -qs "$BIN_DIR" "$HOME/.bashrc"; then
    printf '\n# audiobooker\nexport PATH="%s:$PATH"\n' "$BIN_DIR" >> "$HOME/.bashrc"
    ok "Added $BIN_DIR to PATH in ~/.bashrc (run: source ~/.bashrc)"
fi

# --------------------------------------------------------------------- verify
info "Verifying the installation"
if ! "$BIN_DIR/audiobook" --version >/dev/null; then
    fail "installation check failed: $BIN_DIR/audiobook --version"
fi
ok "Installed $("$BIN_DIR/audiobook" --version | head -1)"
"$BIN_DIR/audiobook" --dry-run --document sample_document.txt >/dev/null \
    && ok "Text pipeline OK (sample_document.txt parses)"

cat <<EOF

$(ok "Setup complete")

Commands (open a new shell first, or: source ~/.bashrc):
  audiobook --document book.txt                  # create an audiobook
  audiobook --document book.txt --dry-run        # inspect chapters/chunks only
  audiobook --document book.txt                 # re-run to resume a stopped job
  audiobook-remote --server http://gpu:7860 ...  # use a remote Chatterbox server
  audiobook-web                                  # Gradio interface on :7860

Install directory: $PROJECT_DIR
Python environment: $VENV_DIR

Long books stream to disk part by part: an interrupted run resumes where it
stopped, and re-running after a failure only re-renders the missing sections.
EOF
