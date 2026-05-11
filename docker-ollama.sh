#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Pull and run the official Ollama container with optional GPU support.
# ---------------------------------------------------------------------------

readonly CONTAINER="ollama"
readonly HOST_PORT="${OLLAMA_PORT:-11434}"
readonly CONTAINER_PORT=11434

read -rp "Enable GPU passthrough? [y/N]: " use_gpu

echo "Pulling latest Ollama image..."
docker pull ollama/ollama:latest

echo "Stopping any existing ${CONTAINER} container..."
docker rm -f "$CONTAINER" 2>/dev/null || true

gpu_flags=()
if [[ "${use_gpu,,}" =~ ^y(es)?$ ]]; then
  gpu_flags=("--gpus=all")
  echo "GPU passthrough enabled."
fi

echo "Starting ${CONTAINER}..."
docker run -d \
  "${gpu_flags[@]}" \
  -v "ollama:/root/.ollama" \
  -p "${HOST_PORT}:${CONTAINER_PORT}" \
  --name "$CONTAINER" \
  ollama/ollama

echo "Cleaning up dangling images..."
docker image prune -f

echo "Ollama is running at http://localhost:${HOST_PORT}"
