#!/bin/bash
set -xeuo pipefail

PACKAGES="pandoc netcat-openbsd ffmpeg libsm6 libxext6"

if [ "$USE_OLLAMA" = "true" ]; then
	PACKAGES="$PACKAGES curl"
fi

apt-get update
# shellcheck disable=SC2086
apt-get install -y --no-install-recommends $PACKAGES

if [ "$USE_OLLAMA" = "true" ]; then
	curl -fsSL https://ollama.com/install.sh | bash
fi

rm -rf /var/lib/apt/lists/*

python -m pip install --no-cache uv

if [ "$USE_CUDA" = "true" ]; then
	PIP_INDEX_URL=https://download.pytorch.org/whl/$USE_CUDA_DOCKER_VER
else
	PIP_INDEX_URL=https://download.pytorch.org/whl/cpu
fi

uv pip install --system torch torchvision torchaudio --index-url "$PIP_INDEX_URL" --no-cache-dir
uv pip install --system -r requirements.txt --no-cache-dir

# Download models
python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['RAG_EMBEDDING_MODEL'], device='cpu')"
python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type='int8', download_root=os.environ['WHISPER_MODEL_DIR'])"

# Ensure model download directories now exist
ls "$SENTENCE_TRANSFORMERS_HOME" || exit 1
ls "$WHISPER_MODEL_DIR" || exit 1
