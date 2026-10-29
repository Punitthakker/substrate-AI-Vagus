#!/usr/bin/env bash
# Substrate - fully local Vagus Engine on macOS. No data leaves this machine.
# Detects the chip, pulls the right open-weight model via Ollama, installs Substrate, opens the console.
set -euo pipefail

say() { printf "\n\033[1;31m●\033[0m %s\n" "$1"; }
cd "$(dirname "$0")/.."

# ---------------------------------------------------------------- 1. pick a model for this hardware
ARCH="$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)"
RAM_GB=$(( $(sysctl -n hw.memsize) / 1073741824 ))
if [ "$ARCH" = "1" ]; then
  CHIP="Apple Silicon"
  if   [ "$RAM_GB" -ge 48 ]; then MODEL="${OLLAMA_MODEL:-qwen2.5:32b}"
  elif [ "$RAM_GB" -ge 24 ]; then MODEL="${OLLAMA_MODEL:-qwen2.5:14b}"
  else                            MODEL="${OLLAMA_MODEL:-llama3.1:8b}"; fi
else
  CHIP="Intel (CPU inference)"
  MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"
fi
say "Chip: $CHIP · RAM: ${RAM_GB}GB · brain: $MODEL"

# ---------------------------------------------------------------- 2. ollama
if ! command -v ollama >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    say "Installing Ollama via Homebrew"; brew install ollama
  else
    say "Ollama not found. Install it from https://ollama.com/download, then re-run this script."; exit 1
  fi
fi
if ! curl -sf http://localhost:11434/api/tags >/dev/null; then
  say "Starting Ollama"
  (open -a Ollama 2>/dev/null || nohup ollama serve >/tmp/ollama.log 2>&1 &)
  for _ in $(seq 1 30); do curl -sf http://localhost:11434/api/tags >/dev/null && break; sleep 1; done
fi
say "Pulling $MODEL (first time only - this can take a few minutes)"
ollama pull "$MODEL"

# ---------------------------------------------------------------- 3. substrate
if [ ! -d .venv ]; then
  say "Creating Python environment"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

say "Warming up the brain"
curl -s http://localhost:11434/api/generate -d "{\"model\":\"$MODEL\",\"prompt\":\"ok\",\"stream\":false}" >/dev/null || true

# ---------------------------------------------------------------- 4. launch
export SUBSTRATE_MODEL=ollama OLLAMA_MODEL="$MODEL" OLLAMA_URL=http://localhost:11434
export SUBSTRATE_DB="${SUBSTRATE_DB:-$HOME/.substrate/substrate.db}"
mkdir -p "$(dirname "$SUBSTRATE_DB")"
PORT="${PORT:-8080}"
say "Substrate is live on http://localhost:$PORT  (local brain: $MODEL - turn Wi-Fi off, it still works)"
(sleep 2 && open "http://localhost:$PORT") &
exec uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
