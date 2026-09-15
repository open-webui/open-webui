#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Pull and run the official Ollama container with optional GPU support.
# ---------------------------------------------------------------------------

readonly CONTAINER="ollama"
readonly HOST_PORT="${OLLAMA_PORT:-11434}"
readonly CONTAINER_PORT=11434
readonly OLLAMA_KEEP_ALIVE_VALUE="${OLLAMA_KEEP_ALIVE:--1}"
readonly OLLAMA_FLASH_ATTENTION_VALUE="${OLLAMA_FLASH_ATTENTION:-1}"
readonly OLLAMA_NUM_PARALLEL_VALUE="${OLLAMA_NUM_PARALLEL:-2}"

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
  -e "OLLAMA_KEEP_ALIVE=${OLLAMA_KEEP_ALIVE_VALUE}" \
  -e "OLLAMA_FLASH_ATTENTION=${OLLAMA_FLASH_ATTENTION_VALUE}" \
  -e "OLLAMA_NUM_PARALLEL=${OLLAMA_NUM_PARALLEL_VALUE}" \
  -v "ollama:/root/.ollama" \
  -p "${HOST_PORT}:${CONTAINER_PORT}" \
  --name "$CONTAINER" \
  ollama/ollama

echo "Cleaning up dangling images..."
docker image prune -f

echo "Ollama is running at http://localhost:${HOST_PORT}"
echo "Performance defaults: keep_alive=${OLLAMA_KEEP_ALIVE_VALUE}, flash_attention=${OLLAMA_FLASH_ATTENTION_VALUE}, num_parallel=${OLLAMA_NUM_PARALLEL_VALUE}"
