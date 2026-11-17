#!/usr/bin/env bash
# Regenerates the Dockerfile lock files; torch is overridden out because the Dockerfile installs it from the PyTorch index.
set -euo pipefail
cd "$(dirname "$0")"

flags=(--universal --python-version 3.12 --generate-hashes --no-header --quiet)
uv pip compile requirements-slim.txt "${flags[@]}" -o requirements-slim.lock
uv pip compile requirements.txt "${flags[@]}" --override <(echo "torch; python_version < '0'") -o requirements.lock
