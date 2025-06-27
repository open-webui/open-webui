# syntax=docker/dockerfile:1
# This Dockerfile builds a multi-stage container for the OpenWebUI application
# Stage 1: Frontend build
# Stage 2: Backend service with optional CUDA and Ollama support

# Build arguments
# Note: Build args can be set using --build-arg="BUILDARG=value" in docker build command
ARG USE_CUDA=false                  # Enable CUDA support for GPU acceleration
ARG USE_CUDA_VER=cu128             # CUDA version (tested with cu117 for CUDA 11, cu121 for CUDA 12, cu128 default)
ARG USE_OLLAMA=false               # Enable Ollama integration for local model support

# Sentence transformer model configuration
# Models available at: https://huggingface.co/models?library=sentence-transformers
# For better performance and multilingual support consider:
# - intfloat/multilingual-e5-large (~2.5GB)
# - intfloat/multilingual-e5-base (~1.5GB)
# Note: Changing the embedding model requires re-embedding previously loaded documents
# Performance impact: Larger models provide better accuracy but require more resources
ARG USE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ARG USE_RERANKING_MODEL=""         # Optional: Specify a reranking model for improved search results

# Token encoding configuration for text processing
# See: https://huggingface.co/models?library=tiktoken
ARG USE_TIKTOKEN_ENCODING_NAME="cl100k_base"  # Tiktoken encoding for token counting

ARG BUILD_HASH=dev-build           # Used for version tracking and cache busting

# User/Group configuration - non-root configurations are untested
# Default to root (0:0) for maximum compatibility
# For production, consider using non-root user for better security
ARG UID=0
ARG GID=0

# Frontend build stage
# Uses Node.js Alpine image for minimal size
FROM --platform=$BUILDPLATFORM node:22-alpine3.20 AS build
ARG BUILD_HASH
WORKDIR /app

RUN apk add --no-cache git  # Required for build version tracking and dependency management
COPY package.json package-lock.json ./
RUN npm ci                  # Clean install of dependencies

COPY . .
ENV APP_BUILD_HASH=${BUILD_HASH}
RUN npm run build          # Builds the production-ready frontend assets

# Backend stage
# Uses Python slim image as base to minimize size while maintaining compatibility
FROM python:3.11-slim-bookworm AS base

# Import build arguments
ARG USE_CUDA
ARG USE_OLLAMA
ARG USE_CUDA_VER
ARG USE_EMBEDDING_MODEL
ARG USE_RERANKING_MODEL
ARG UID
ARG GID
ARG BUILD_HASH

# Environment variables
# Core configuration
ENV ENV=prod \
    PORT=8080 \
    USE_OLLAMA_DOCKER=${USE_OLLAMA} \
    USE_CUDA_DOCKER=${USE_CUDA} \
    USE_CUDA_DOCKER_VER=${USE_CUDA_VER} \
    USE_EMBEDDING_MODEL_DOCKER=${USE_EMBEDDING_MODEL} \
    USE_RERANKING_MODEL_DOCKER=${USE_RERANKING_MODEL} \
    # API and Security Configuration
    # These can be overridden at runtime using docker -e flags
    OLLAMA_BASE_URL="/ollama" \
    OPENAI_API_BASE_URL="" \
    OPENAI_API_KEY="" \
    WEBUI_SECRET_KEY="" \
    # Privacy and Analytics Settings
    # Set to true to disable tracking and telemetry
    SCARF_NO_ANALYTICS=true \
    DO_NOT_TRACK=true \
    ANONYMIZED_TELEMETRY=false \
    # Model Configuration
    # Whisper settings for speech-to-text functionality
    WHISPER_MODEL="base" \
    WHISPER_MODEL_DIR="/app/backend/data/cache/whisper/models" \
    # RAG (Retrieval-Augmented Generation) settings
    RAG_EMBEDDING_MODEL="${USE_EMBEDDING_MODEL}" \
    RAG_RERANKING_MODEL="${USE_RERANKING_MODEL}" \
    SENTENCE_TRANSFORMERS_HOME="/app/backend/data/cache/embedding/models" \
    # Token encoding settings
    TIKTOKEN_ENCODING_NAME="cl100k_base" \
    TIKTOKEN_CACHE_DIR="/app/backend/data/cache/tiktoken" \
    # Cache and Build Configuration
    # Hugging Face cache location for model downloads
    HF_HOME="/app/backend/data/cache/embedding/models" \
    HOME=/root \
    WEBUI_BUILD_VERSION=${BUILD_HASH} \
    DOCKER=true

WORKDIR /app/backend

# Create non-root user if needed
# This is skipped if UID=0 (root)
RUN if [ $UID -ne 0 ]; then \
    [ $GID -ne 0 ] && addgroup --gid $GID app; \
    adduser --uid $UID --gid $GID --home $HOME --disabled-password --no-create-home app; \
    fi

# Setup directories and permissions
# Initialize Chroma DB with a default user ID to disable analytics
RUN mkdir -p $HOME/.cache/chroma && \
    echo -n 00000000-0000-0000-0000-000000000000 > $HOME/.cache/chroma/telemetry_user_id && \
    chown -R $UID:$GID /app $HOME

# Install common dependencies
# Note: These packages support various features including:
# - OCR and document processing (ffmpeg, libsm6, libxext6)
# - Build tools (gcc, python3-dev)
# - Network utilities (curl, netcat)
# - Document conversion (pandoc)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    build-essential \
    pandoc \
    gcc \
    python3-dev \
    netcat-openbsd \
    curl \
    jq \
    ffmpeg \
    libsm6 \
    libxext6 && \
    # Install Ollama if needed
    # Only installed when USE_OLLAMA=true
    if [ "$USE_OLLAMA" = "true" ]; then \
        curl -fsSL https://ollama.com/install.sh | sh; \
    fi && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY --chown=$UID:$GID ./backend/requirements.txt ./requirements.txt

# Install Python packages and initialize models
# Note: Models are initialized with CPU to ensure compatibility, they will use GPU if available
# The initialization ensures models are downloaded during build rather than at runtime
RUN pip3 install --no-cache-dir uv && \
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/$([ "$USE_CUDA" = "true" ] && echo "$USE_CUDA_DOCKER_VER" || echo "cpu") --no-cache-dir && \
    uv pip install --system -r requirements.txt --no-cache-dir && \
    python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['RAG_EMBEDDING_MODEL'], device='cpu')" && \
    python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type='int8', download_root=os.environ['WHISPER_MODEL_DIR'])" && \
    python -c "import os; import tiktoken; tiktoken.get_encoding(os.environ['TIKTOKEN_ENCODING_NAME'])" && \
    chown -R $UID:$GID /app/backend/data/

# Copy built frontend files
# These files come from the build stage
COPY --chown=$UID:$GID --from=build /app/build /app/build
COPY --chown=$UID:$GID --from=build /app/CHANGELOG.md /app/CHANGELOG.md
COPY --chown=$UID:$GID --from=build /app/package.json /app/package.json

# Copy backend files
COPY --chown=$UID:$GID ./backend .

# Expose the application port
EXPOSE 8080

# Health check to ensure the application is running
# Fails if the /health endpoint doesn't return status: true
HEALTHCHECK CMD curl --silent --fail http://localhost:${PORT:-8080}/health | jq -ne 'input.status == true' || exit 1

# Switch to non-root user if specified
USER $UID:$GID

# Start the application
CMD [ "bash", "start.sh"]

