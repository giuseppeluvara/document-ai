#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
model_path="${DOCUMENT_AI_MODEL_PATH:-${project_dir}/models/qwen2.5-1.5b-instruct-q4_k_m.gguf}"
model_binary="${LLAMA_SERVER_BIN:-llama-server}"

if [[ ! -f "$model_path" ]]; then
    echo "Modello non trovato. Eseguire prima: python scripts/download_model.py" >&2
    exit 1
fi
if ! command -v "$model_binary" >/dev/null 2>&1; then
    echo "llama-server non trovato. Installare llama.cpp o impostare LLAMA_SERVER_BIN." >&2
    exit 1
fi

export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
exec "$model_binary" \
    --model "$model_path" \
    --alias local \
    --host 127.0.0.1 \
    --port 8081 \
    --threads 2 \
    --threads-batch 2 \
    --ctx-size 8192 \
    --parallel 1 \
    --n-gpu-layers 0
