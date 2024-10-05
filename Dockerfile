# syntax=docker/dockerfile:1

# Initialize device type args
ARG USE_CUDA=false
ARG USE_OLLAMA=false
ARG USE_CUDA_VER=cu121
ARG USE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ARG USE_RERANKING_MODEL=""
ARG BUILD_HASH=dev-build
ARG UID=0
ARG GID=0

######## WebUI frontend ########
FROM --platform=$BUILDPLATFORM node:21-alpine3.19 as build
ARG BUILD_HASH

WORKDIR /app

COPY package.json package-lock.json ./

# Install dependencies with memory limit increased
RUN NODE_OPTIONS="--max-old-space-size=4096" npm ci

COPY . .
ENV APP_BUILD_HASH=${BUILD_HASH}
RUN NODE_OPTIONS="--max-old-space-size=4096" npm run build

######## WebUI backend ########
FROM python:3.11-slim-bookworm as base

# Use args
ARG USE_CUDA
ARG USE_OLLAMA
ARG USE_CUDA_VER
ARG USE_EMBEDDING_MODEL
ARG USE_RERANKING_MODEL
ARG UID
ARG GID

# Environment variables
ENV ENV=prod \
    PORT=8080 \
    USE_OLLAMA_DOCKER=${USE_OLLAMA} \
    USE_CUDA_DOCKER=${USE_CUDA} \
    USE_CUDA_DOCKER_VER=${USE_CUDA_VER} \
    USE_EMBEDDING_MODEL_DOCKER=${USE_EMBEDDING_MODEL} \
    USE_RERANKING_MODEL_DOCKER=${USE_RERANKING_MODEL}

# API and security keys (use secure handling in production)
ENV OLLAMA_BASE_URL="/ollama" \
    OPENAI_API_BASE_URL="" \
    OPENAI_API_KEY="" \
    WEBUI_SECRET_KEY="" \
    SCARF_NO_ANALYTICS=true \
    DO_NOT_TRACK=true \
    ANONYMIZED_TELEMETRY=false

# Model settings
ENV WHISPER_MODEL="base" \
    WHISPER_MODEL_DIR="/app/backend/data/cache/whisper/models" \
    RAG_EMBEDDING_MODEL="$USE_EMBEDDING_MODEL_DOCKER" \
    RAG_RERANKING_MODEL="$USE_RERANKING_MODEL_DOCKER" \
    SENTENCE_TRANSFORMERS_HOME="/app/backend/data/cache/embedding/models" \
    HF_HOME="/app/backend/data/cache/embedding/models"

WORKDIR /app/backend
ENV HOME /root

# Create user if not root
RUN if [ $UID -ne 0 ]; then \
    if [ $GID -ne 0 ]; then \
        addgroup --gid $GID app; \
    fi; \
    adduser --uid $UID --gid $GID --home $HOME --disabled-password --no-create-home app; \
    fi

# Setup directories and ownership
RUN mkdir -p $HOME/.cache/chroma && \
    echo -n 00000000-0000-0000-0000-000000000000 > $HOME/.cache/chroma/telemetry_user_id && \
    chown -R $UID:$GID /app $HOME

# Install dependencies based on USE_OLLAMA flag
RUN if [ "$USE_OLLAMA" = "true" ]; then \
    apt-get update && \
    apt-get install -y --no-install-recommends git build-essential pandoc netcat-openbsd curl gcc python3-dev ffmpeg libsm6 libxext6 && \
    curl -fsSL https://ollama.com/install.sh | sh && \
    rm -rf /var/lib/apt/lists/*; \
    else \
    apt-get update && \
    apt-get install -y --no-install-recommends git build-essential pandoc gcc netcat-openbsd curl jq ffmpeg libsm6 libxext6 && \
    rm -rf /var/lib/apt/lists/*; \
    fi

# Install Python dependencies and download models
COPY --chown=$UID:$GID ./backend/requirements.txt ./requirements.txt
RUN pip3 install uv && \
    if [ "$USE_CUDA" = "true" ]; then \
        pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/$USE_CUDA_DOCKER_VER --no-cache-dir && \
        uv pip install --system -r requirements.txt --no-cache-dir && \
        python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['RAG_EMBEDDING_MODEL'], device='cpu')" && \
        python -c "from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type='int8', download_root=os.environ['WHISPER_MODEL_DIR'])"; \
    else \
        pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --no-cache-dir && \
        uv pip install --system -r requirements.txt --no-cache-dir && \
        python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['RAG_EMBEDDING_MODEL'], device='cpu')" && \
        python -c "from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type='int8', download_root=os.environ['WHISPER_MODEL_DIR'])"; \
    fi && \
    chown -R $UID:$GID /app/backend/data/

# Copy frontend build and backend files
COPY --chown=$UID:$GID --from=build /app/build /app/build
COPY --chown=$UID:$GID --from=build /app/CHANGELOG.md /app/CHANGELOG.md
COPY --chown=$UID:$GID --from=build /app/package.json /app/package.json
COPY --chown=$UID:$GID ./backend .

EXPOSE 8080

# Healthcheck
HEALTHCHECK CMD curl --silent --fail http://localhost:${PORT:-8080}/health | jq -ne 'input.status == true' || exit 1

# Set user
USER $UID:$GID

# Build version
ARG BUILD_HASH
ENV WEBUI_BUILD_VERSION=${BUILD_HASH}
ENV DOCKER true

CMD [ "bash", "start.sh" ]
