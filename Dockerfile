# Initialize device type args
# use build args in the docker build command with --build-arg="BUILDARG=true"
ARG USE_CUDA=false
ARG USE_OLLAMA=false
# Tested with cu117 for CUDA 11 and cu121 for CUDA 12 (default)
ARG USE_CUDA_VER=cu121
# any sentence transformer model; models to use can be found at https://huggingface.co/models?library=sentence-transformers
# Leaderboard: https://huggingface.co/spaces/mteb/leaderboard
# for better performance and multilangauge support use "intfloat/multilingual-e5-large" (~2.5GB) or "intfloat/multilingual-e5-base" (~1.5GB)
# IMPORTANT: If you change the embedding model (sentence-transformers/all-MiniLM-L6-v2) and vice versa, you aren't able to use RAG Chat with your previous documents loaded in the WebUI! You need to re-embed them.
ARG USE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ARG USE_RERANKING_MODEL=""

# Tiktoken encoding name; models to use can be found at https://huggingface.co/models?library=tiktoken
ARG USE_TIKTOKEN_ENCODING_NAME="cl100k_base"

ARG BUILD_HASH=dev-build
# Override at your own risk - non-root configurations are untested
ARG UID=0
ARG GID=0

######## WebUI frontend ########
FROM --platform=$BUILDPLATFORM node:22-alpine3.20 AS build
# for local docker test runs, enable alpine below
# FROM node:22-alpine3.20 AS build
ARG BUILD_HASH

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci && npm cache clean --force

COPY . .
ENV APP_BUILD_HASH=${BUILD_HASH}
RUN npm run build && \
    # Cleanup node_modules and other build artifacts to reduce layer size
    rm -rf node_modules .svelte-kit src static/pyodide package-lock.json

######## Model download stage (parallel and cacheable) ########
FROM python:3.11-slim-bookworm AS models

# Use args for model downloading
ARG USE_CUDA
ARG USE_CUDA_VER
ARG USE_EMBEDDING_MODEL
ARG USE_RERANKING_MODEL

# Environment variables for model downloads
ENV USE_CUDA_DOCKER=${USE_CUDA} \
    USE_CUDA_DOCKER_VER=${USE_CUDA_VER} \
    USE_EMBEDDING_MODEL_DOCKER=${USE_EMBEDDING_MODEL} \
    USE_RERANKING_MODEL_DOCKER=${USE_RERANKING_MODEL}

## Model cache directories ##
ENV RAG_EMBEDDING_MODEL="$USE_EMBEDDING_MODEL_DOCKER" \
    RAG_RERANKING_MODEL="$USE_RERANKING_MODEL_DOCKER" \
    SENTENCE_TRANSFORMERS_HOME="/models/embedding" \
    WHISPER_MODEL="base" \
    WHISPER_MODEL_DIR="/models/whisper" \
    TXTAI_WIKIPEDIA_MODEL="neuml/txtai-wikipedia" \
    TXTAI_CACHE_DIR="/models/txtai" \
    TRANSFORMERS_CACHE="/models/transformers" \
    TIKTOKEN_ENCODING_NAME="cl100k_base" \
    TIKTOKEN_CACHE_DIR="/models/tiktoken" \
    HF_HOME="/models/embedding"

# Install system dependencies for model downloads
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev curl && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# Create model directories
RUN mkdir -p /models/embedding /models/whisper /models/txtai /models/transformers /models/tiktoken

# Copy only requirements for model downloads
COPY ./backend/requirements.txt /tmp/requirements.txt

# Install dependencies and download all models in parallel-friendly layers
RUN pip3 install --no-cache-dir uv && \
    if [ "$USE_CUDA" = "true" ]; then \
    pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/$USE_CUDA_DOCKER_VER; \
    else \
    pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; \
    fi && \
    uv pip install --system --no-cache-dir -r /tmp/requirements.txt && \
    rm -rf /tmp/requirements.txt /root/.cache /tmp/* /var/tmp/*

# Download models in separate RUN commands for better caching and cleanup
RUN python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['RAG_EMBEDDING_MODEL'], device='cpu')" && \
    python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type='int8', download_root=os.environ['WHISPER_MODEL_DIR'])" && \
    python -c "import os; import tiktoken; tiktoken.get_encoding(os.environ['TIKTOKEN_ENCODING_NAME'])" && \
    HF_HOME="/models/txtai" python -c "import os; from txtai.embeddings import Embeddings; e = Embeddings(); e.load(provider='huggingface-hub', container='neuml/txtai-wikipedia')" && \
    python -c "import os; from transformers import pipeline; pipeline('translation', model='Helsinki-NLP/opus-mt-fr-en', device='cpu')" && \
    # Cleanup after model downloads
    pip3 cache purge && \
    rm -rf /root/.cache /tmp/* /var/tmp/* && \
    # Remove build dependencies to reduce size
    apt-get remove -y gcc python3-dev && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/*

######## WebUI backend ########
FROM python:3.11-slim-bookworm AS base

# Use args
ARG USE_CUDA
ARG USE_OLLAMA
ARG USE_CUDA_VER
ARG USE_EMBEDDING_MODEL
ARG USE_RERANKING_MODEL
ARG UID
ARG GID

## Basis ##
ENV ENV=prod \
    PORT=8080 \
    # pass build args to the build
    USE_OLLAMA_DOCKER=${USE_OLLAMA} \
    USE_CUDA_DOCKER=${USE_CUDA} \
    USE_CUDA_DOCKER_VER=${USE_CUDA_VER} \
    USE_EMBEDDING_MODEL_DOCKER=${USE_EMBEDDING_MODEL} \
    USE_RERANKING_MODEL_DOCKER=${USE_RERANKING_MODEL}

## Basis URL Config ##
ENV OLLAMA_BASE_URL="/ollama" \
    OPENAI_API_BASE_URL=""

## API Key and Security Config ##
ENV OPENAI_API_KEY="" \
    WEBUI_SECRET_KEY="" \
    SCARF_NO_ANALYTICS=true \
    DO_NOT_TRACK=true \
    ANONYMIZED_TELEMETRY=false

#### Other models #########################################################
## whisper TTS model settings ##
ENV WHISPER_MODEL="base" \
    WHISPER_MODEL_DIR="/app/backend/data/cache/whisper/models"

## RAG Embedding model settings ##
ENV RAG_EMBEDDING_MODEL="$USE_EMBEDDING_MODEL_DOCKER" \
    RAG_RERANKING_MODEL="$USE_RERANKING_MODEL_DOCKER" \
    SENTENCE_TRANSFORMERS_HOME="/app/backend/data/cache/embedding/models"

## txtai-wikipedia Wiki Grounding settings ##
ENV TXTAI_WIKIPEDIA_MODEL="neuml/txtai-wikipedia" \
    TXTAI_CACHE_DIR="/app/backend/data/cache/txtai/models" \
    TRANSFORMERS_CACHE="/app/backend/data/cache/transformers"

## Tiktoken model settings ##
ENV TIKTOKEN_ENCODING_NAME="cl100k_base" \
    TIKTOKEN_CACHE_DIR="/app/backend/data/cache/tiktoken"

## Hugging Face download cache ##
ENV HF_HOME="/app/backend/data/cache/embedding/models"

## Torch Extensions ##
# ENV TORCH_EXTENSIONS_DIR="/.cache/torch_extensions"

#### Other models ##########################################################

WORKDIR /app/backend

ENV HOME=/root
# Create user and group if not root
RUN if [ $UID -ne 0 ]; then \
    if [ $GID -ne 0 ]; then \
    addgroup --gid $GID app; \
    fi; \
    adduser --uid $UID --gid $GID --home $HOME --disabled-password --no-create-home app; \
    fi

RUN mkdir -p $HOME/.cache/chroma
RUN echo -n 00000000-0000-0000-0000-000000000000 > $HOME/.cache/chroma/telemetry_user_id

# Make sure the user has access to the app and root directory
RUN chown -R $UID:$GID /app $HOME && \
    chmod -R g=u $HOME

RUN if [ "$USE_OLLAMA" = "true" ]; then \
    apt-get update && \
    # Install pandoc and netcat
    apt-get install -y --no-install-recommends git build-essential pandoc netcat-openbsd curl && \
    # for RAG OCR
    apt-get install -y --no-install-recommends ffmpeg libsm6 libxext6 && \
    # install helper tools
    apt-get install -y --no-install-recommends curl jq && \
    # install ollama
    curl -fsSL https://ollama.com/install.sh | sh && \
    # Aggressive cleanup: remove build deps, clean all caches, remove docs/man pages
    apt-get remove -y --purge build-essential && \
    apt-get autoremove -y --purge && \
    apt-get autoclean && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* /tmp/* /var/tmp/* && \
    rm -rf /usr/share/doc /usr/share/man /usr/share/locale && \
    rm -rf /root/.cache /root/.npm /root/.pip; \
    else \
    apt-get update && \
    # Install pandoc, netcat and minimal dependencies
    apt-get install -y --no-install-recommends git build-essential pandoc netcat-openbsd curl jq && \
    # for RAG OCR
    apt-get install -y --no-install-recommends ffmpeg libsm6 libxext6 && \
    # Remove build dependencies after installation
    apt-get remove -y --purge build-essential && \
    apt-get autoremove -y --purge && \
    apt-get autoclean && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* /tmp/* /var/tmp/* && \
    rm -rf /usr/share/doc /usr/share/man /usr/share/locale && \
    rm -rf /root/.cache /root/.npm /root/.pip; \
    fi

# Copy Python packages from models stage to avoid duplicate installation (saves ~1.4GB)
COPY --from=models /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=models /usr/local/bin/ /usr/local/bin/

# Aggressive system cleanup for additional space savings (~300MB)
RUN apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* /var/cache/debconf/* && \
    rm -rf /usr/share/doc /usr/share/man /usr/share/locale /usr/share/info && \
    rm -rf /root/.cache /tmp/* /var/tmp/* /root/.npm /root/.pip && \
    find /usr/local -name "*.pyc" -delete && \
    find /usr/local -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Copy pre-downloaded models from parallel build stage and set permissions in single layer
COPY --from=models --chown=$UID:$GID --chmod=g=u /models/ /app/backend/data/cache/
# Remove any .git directories from model downloads to reduce size
RUN find /app/backend/data/cache -name ".git" -type d -exec rm -rf {} + 2>/dev/null || true && \
    # Remove any __pycache__ directories
    find /app/backend/data/cache -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true && \
    # Remove any temporary files
    find /app/backend/data/cache -name "*.tmp" -delete 2>/dev/null || true

# copy embedding weight from build
# RUN mkdir -p /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2
# COPY --from=build /app/onnx /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx

# copy built frontend files
COPY --chown=$UID:$GID --chmod=g=u --from=build /app/build /app/build
COPY --chown=$UID:$GID --chmod=g=u --from=build /app/CHANGELOG.md /app/CHANGELOG.md
COPY --chown=$UID:$GID --chmod=g=u --from=build /app/package.json /app/package.json

# copy backend files
COPY --chown=$UID:$GID --chmod=g=u ./backend .

EXPOSE 8080

HEALTHCHECK CMD curl --silent --fail http://localhost:${PORT:-8080}/health | jq -ne 'input.status == true' || exit 1

USER $UID:$GID

ARG BUILD_HASH
ENV WEBUI_BUILD_VERSION=${BUILD_HASH}
ENV DOCKER=true

CMD [ "bash", "start.sh"]
