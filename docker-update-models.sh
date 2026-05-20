#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# Pull the latest version of every model installed in the Ollama container.
# ---------------------------------------------------------------------------

readonly CONTAINER="${OLLAMA_CONTAINER:-ollama}"

echo "Fetching installed models from '${CONTAINER}' container..."
models=$(docker exec "$CONTAINER" ollama list | tail -n +2 | awk '{print $1}')

if [[ -z "$models" ]]; then
  echo "No models found."
  exit 0
fi

echo "Updating models..."
while IFS= read -r model; do
  echo "  Pulling ${model}..."
  docker exec "$CONTAINER" ollama pull "$model"
done <<< "$models"

echo "All models updated."
