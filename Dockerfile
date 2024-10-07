# syntax=docker/dockerfile:1

# Initialize device type args
ARG USE_CUDA=false
ARG USE_OLLAMA=false
ARG USE_CUDA_VER=cu121
ARG USE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ARG USE_RERANKING_MODEL=""
ARG BUILD_HASH=dev-build
ARG UID=1000
ARG GID=1000

######## WebUI frontend ########

# Use specific node version for consistency (alpine for smaller image size)
FROM --platform=$BUILDPLATFORM node:21-alpine3.19 AS build
WORKDIR /app

# Install dependencies early to leverage Docker cache
COPY package.json package-lock.json ./
RUN npm ci

# Copy remaining source code
COPY . .

ENV APP_BUILD_HASH=${BUILD_HASH}

# Build static assets
## NODE_OPTIONS helps prevent OOM issues for large builds
RUN NODE_OPTIONS="--max-old-space-size=4096" npm run build

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

ENV ENV=prod \
    PORT=8080 \
    USE_OLLAMA_DOCKER=${USE_OLLAMA} \
    USE_CUDA_DOCKER=${USE_CUDA} \
    USE_CUDA_DOCKER_VER=${USE_CUDA_VER} \
    USE_EMBEDDING_MODEL_DOCKER=${USE_EMBEDDING_MODEL} \
    USE_RERANKING_MODEL_DOCKER=${USE_RERANKING_MODEL} \
    OLLAMA_BASE_URL="/ollama" \
    OPENAI_API_BASE_URL="" \
    OPENAI_API_KEY="" \
    WEBUI_SECRET_KEY="" \
    SCARF_NO_ANALYTICS=true \
    DO_NOT_TRACK=true \
    ANONYMIZED_TELEMETRY=false \
    WHISPER_MODEL="base" \
    WHISPER_MODEL_DIR="/app/backend/data/cache/whisper/models" \
    RAG_EMBEDDING_MODEL="$USE_EMBEDDING_MODEL_DOCKER" \
    RAG_RERANKING_MODEL="$USE_RERANKING_MODEL_DOCKER" \
    SENTENCE_TRANSFORMERS_HOME="/app/backend/data/cache/embedding/models" \
    HF_HOME="/app/backend/data/cache/embedding/models"

## Define working directory
WORKDIR /app/backend

# Optimization: creation of user and setting permissions
RUN if [ $UID -ne 0 ]; then \
    if [ $GID -ne 0 ]; then \
    addgroup --gid $GID app; \
    fi; \
    adduser --uid $UID --gid $GID --home /home/app --disabled-password --no-create-home app; \
    fi

# Pre-create directories for cache
RUN mkdir -p /home/app/.cache/chroma && \
    mkdir -p /app/backend/data/cache/embedding/models && \
    echo -n 00000000-0000-0000-0000-000000000000 > /home/app/.cache/chroma/telemetry_user_id

# Install apt dependencies based on USE_OLLAMA arg
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    pandoc \
    curl \
    jq \
    gcc \
    netcat-openbsd \
    python3-dev \
    && \
    if [ "$USE_OLLAMA" = "true" ]; then \
    apt-get install -y --no-install-recommends ffmpeg libsm6 libxext6 && \
    curl -fsSL https://ollama.com/install.sh | sh; \
    fi && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies directly (replace with actual packages you need)
RUN pip install --upgrade pip && \
    pip install \
    uvicorn \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install \
    sentence-transformers faster-whisper

# Copy built frontend files from the build stage
COPY --chown=$UID:$GID --from=build /app/build /app/build
COPY --chown=$UID:$GID --from=build /app/CHANGELOG.md /app/CHANGELOG.md
COPY --chown=$UID:$GID --from=build /app/package.json /app/package.json

# Copy backend files
COPY --chown=$UID:$GID ./backend .

# Expose the application port
EXPOSE 8080

# Set up health check
HEALTHCHECK CMD curl --silent --fail http://localhost:${PORT:-8080}/health | jq -ne 'input.status == true' || exit 1

# Set the user and command
USER $UID:$GID
ARG BUILD_HASH
ENV WEBUI_BUILD_VERSION=${BUILD_HASH}
ENV DOCKER=true

# Start application
CMD ["bash", "start.sh"]
