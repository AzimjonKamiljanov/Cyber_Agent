#!/usr/bin/env bash
# scripts/manual/06-download-models.sh
# Cyber Agent — Stage S3 Local Models Download Helper
# Run by the owner: downloads Whisper models, pulls Ollama model, and caches TTS assets.
set -euo pipefail

echo "=== Cyber Agent: Stage S3 Local Model Downloader ==="
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$WORKSPACE_ROOT"

# Ensure venv exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment .venv not found. Run 'uv sync' first."
    exit 1
fi

PYTHON=".venv/bin/python"

echo "1. Checking Ollama status..."
if command -v ollama >/dev/null 2>&1; then
    echo "Ollama is installed. Pulling recommended local model..."
    ollama pull qwen2.5:7b-instruct-q4_K_M || echo "Warning: Ollama pull failed. Ensure ollama service is running."
else
    echo "Ollama binary not found on PATH. If needed, install via: curl -fsSL https://ollama.com/install.sh | sh"
fi

echo "2. Pre-caching local Uzbek Whisper STT models..."
$PYTHON -c "
import faster_whisper
models = ['Mannon/whisper-medium-uzbek', 'openai/whisper-large-v3-turbo']
for m in models:
    try:
        print(f'Caching {m}...')
        faster_whisper.WhisperModel(m, device='cpu', compute_type='int8', download_root='models/whisper')
        print(f'Successfully cached {m}')
    except Exception as e:
        print(f'Failed to cache {m}: {e}')
" || echo "Whisper pre-caching encountered an issue."

echo "=== Model pre-caching finished ==="
