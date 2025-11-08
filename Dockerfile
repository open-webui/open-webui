# syntax=docker/dockerfile:1
# Initialize device type args
ARG USE_CUDA=false
ARG USE_OLLAMA=false
ARG USE_SLIM=false
ARG USE_PERMISSION_HARDENING=false
ARG USE_CUDA_VER=cu128
ARG USE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ARG USE_RERANKING_MODEL=""
ARG USE_TIKTOKEN_ENCODING_NAME="cl100k_base"
ARG BUILD_HASH=dev-build
ARG UID=0
ARG GID=0

######## WebUI frontend ########
FROM --platform=$BUILDPLATFORM node:20-alpine3.20 AS build
ARG BUILD_HASH

# ========== 配置 Alpine 镜像源 ==========
RUN echo "https://mirrors.aliyun.com/alpine/v3.20/main" > /etc/apk/repositories && \
    echo "https://mirrors.aliyun.com/alpine/v3.20/community" >> /etc/apk/repositories && \
    apk update

# ========== 配置 npm 镜像源（只保留有效选项）==========
RUN npm config set registry https://registry.npmmirror.com && \
    npm config set fetch-timeout 600000 && \
    npm config set fetch-retries 10 && \
    npm config set fetch-retry-mintimeout 30000 && \
    npm config set fetch-retry-maxtimeout 180000

# ========== 配置二进制包镜像（通过环境变量）==========
ENV ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/ \
    SASS_BINARY_SITE=https://npmmirror.com/mirrors/node-sass/ \
    PHANTOMJS_CDNURL=https://npmmirror.com/mirrors/phantomjs/ \
    CHROMEDRIVER_CDNURL=https://npmmirror.com/mirrors/chromedriver/ \
    OPERADRIVER_CDNURL=https://npmmirror.com/mirrors/operadriver/ \
    PYTHON_MIRROR=https://npmmirror.com/mirrors/python/

# ========== 配置代理（可选，作为备用方案）==========
ARG HTTP_PROXY
ARG HTTPS_PROXY
ENV HTTP_PROXY=${HTTP_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}
ENV NO_PROXY=localhost,127.0.0.1,mirrors.aliyun.com,registry.nppmirror.com,npmmirror.com

# ========== 安装 git 并配置 ==========
RUN apk add --no-cache git && \
    if [ -n "$HTTP_PROXY" ]; then \
        git config --global http.proxy ${HTTP_PROXY} && \
        git config --global https.proxy ${HTTPS_PROXY} && \
        git config --global http.sslVerify false; \
    fi

WORKDIR /app

# ========== 安装依赖 ==========
COPY package.json package-lock.json ./
RUN npm install --legacy-peer-deps --ignore-scripts || \
    (echo "First npm install failed, retrying..." && npm install --legacy-peer-deps --ignore-scripts)

# ========== 构建前端 ==========
COPY . .
ENV APP_BUILD_HASH=${BUILD_HASH}
RUN npm run build

######## WebUI backend ########
FROM python:3.11-slim-bookworm AS base

# Use args
ARG USE_CUDA
ARG USE_OLLAMA
ARG USE_CUDA_VER
ARG USE_SLIM
ARG USE_PERMISSION_HARDENING
ARG USE_EMBEDDING_MODEL
ARG USE_RERANKING_MODEL
ARG UID
ARG GID

## Basis ##
ENV ENV=prod \
    PORT=8080 \
    USE_OLLAMA_DOCKER=${USE_OLLAMA} \
    USE_CUDA_DOCKER=${USE_CUDA} \
    USE_SLIM_DOCKER=${USE_SLIM} \
    USE_CUDA_DOCKER_VER=${USE_CUDA_VER} \
    USE_EMBEDDING_MODEL_DOCKER=${USE_EMBEDDING_MODEL} \
    USE_RERANKING_MODEL_DOCKER=${USE_RERANKING_MODEL}

## Basis URL Config ##
ENV OLLAMA_BASE_URL="/ollama" \
    OPENAI_API_BASE_URL=""

## API Key and Security Config ##
# 注意：这些应该在运行时注入，不要在构建时写入
ENV OPENAI_API_KEY="" \
    WEBUI_SECRET_KEY="" \
    SCARF_NO_ANALYTICS=true \
    DO_NOT_TRACK=true \
    ANONYMIZED_TELEMETRY=false

#### Other models #########################################################
ENV WHISPER_MODEL="base" \
    WHISPER_MODEL_DIR="/app/backend/data/cache/whisper/models" \
    RAG_EMBEDDING_MODEL="$USE_EMBEDDING_MODEL_DOCKER" \
    RAG_RERANKING_MODEL="$USE_RERANKING_MODEL_DOCKER" \
    SENTENCE_TRANSFORMERS_HOME="/app/backend/data/cache/embedding/models" \
    TIKTOKEN_ENCODING_NAME="cl100k_base" \
    TIKTOKEN_CACHE_DIR="/app/backend/data/cache/tiktoken" \
    HF_HOME="/app/backend/data/cache/embedding/models"

# ========== 配置 Hugging Face 镜像（关键！）==========
ENV HF_ENDPOINT=https://hf-mirror.com

WORKDIR /app/backend

ENV HOME=/root

# ========== 创建用户和组 ==========
RUN if [ $UID -ne 0 ]; then \
    if [ $GID -ne 0 ]; then \
    addgroup --gid $GID app; \
    fi; \
    adduser --uid $UID --gid $GID --home $HOME --disabled-password --no-create-home app; \
    fi

RUN mkdir -p $HOME/.cache/chroma && \
    echo -n 00000000-0000-0000-0000-000000000000 > $HOME/.cache/chroma/telemetry_user_id && \
    chown -R $UID:$GID /app $HOME

# ========== 配置 Debian 镜像源 ==========
RUN sed -i 's@deb.debian.org@mirrors.aliyun.com@g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's@security.debian.org@mirrors.aliyun.com@g' /etc/apt/sources.list.d/debian.sources

# ========== 安装系统依赖 ==========
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git build-essential pandoc gcc netcat-openbsd curl jq \
    python3-dev \
    ffmpeg libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# ========== 配置 pip 镜像源 ==========
RUN pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip3 config set install.trusted-host mirrors.aliyun.com && \
    pip3 config set global.timeout 600

# ========== 安装 Python 依赖 ==========
COPY --chown=$UID:$GID ./backend/requirements.txt ./requirements.txt

RUN pip3 install --no-cache-dir uv && \
    if [ "$USE_CUDA" = "true" ]; then \
    # CUDA 版本：使用清华镜像加速 PyTorch 下载
    pip3 install torch torchvision torchaudio \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
        --extra-index-url https://download.pytorch.org/whl/$USE_CUDA_DOCKER_VER \
        --no-cache-dir && \
    uv pip install --system -r requirements.txt --no-cache-dir && \
    python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['RAG_EMBEDDING_MODEL'], device='cpu')" && \
    python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type='int8', download_root=os.environ['WHISPER_MODEL_DIR'])" && \
    python -c "import os; import tiktoken; tiktoken.get_encoding(os.environ['TIKTOKEN_ENCODING_NAME'])"; \
    else \
    # CPU 版本：使用清华镜像加速 PyTorch 下载
    pip3 install torch torchvision torchaudio \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        --no-cache-dir && \
    uv pip install --system -r requirements.txt --no-cache-dir && \
    if [ "$USE_SLIM" != "true" ]; then \
    python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['RAG_EMBEDDING_MODEL'], device='cpu')" && \
    python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type='int8', download_root=os.environ['WHISPER_MODEL_DIR'])" && \
    python -c "import os; import tiktoken; tiktoken.get_encoding(os.environ['TIKTOKEN_ENCODING_NAME'])"; \
    fi; \
    fi && \
    mkdir -p /app/backend/data && chown -R $UID:$GID /app/backend/data/ && \
    rm -rf /var/lib/apt/lists/*

# ========== 安装 Ollama（使用国内镜像）==========
RUN if [ "$USE_OLLAMA" = "true" ]; then \
    date +%s > /tmp/ollama_build_hash && \
    echo "Cache broken at timestamp: `cat /tmp/ollama_build_hash`" && \
    export HF_ENDPOINT=https://hf-mirror.com && \
    curl -fsSL https://ollama.com/install.sh | sh || \
    (echo "Ollama installation failed, trying with proxy..." && \
     export http_proxy=http://host.docker.internal:7897 && \
     export https_proxy=http://host.docker.internal:7897 && \
     curl -fsSL https://ollama.com/install.sh | sh) && \
    rm -rf /var/lib/apt/lists/*; \
    fi

# ========== 复制构建文件 ==========
COPY --chown=$UID:$GID --from=build /app/build /app/build
COPY --chown=$UID:$GID --from=build /app/CHANGELOG.md /app/CHANGELOG.md
COPY --chown=$UID:$GID --from=build /app/package.json /app/package.json
COPY --chown=$UID:$GID ./backend .

EXPOSE 8080

HEALTHCHECK CMD curl --silent --fail http://localhost:${PORT:-8080}/health | jq -ne 'input.status == true' || exit 1

# ========== 权限加固 ==========
RUN if [ "$USE_PERMISSION_HARDENING" = "true" ]; then \
    set -eux; \
    chgrp -R 0 /app /root || true; \
    chmod -R g+rwX /app /root || true; \
    find /app -type d -exec chmod g+s {} + || true; \
    find /root -type d -exec chmod g+s {} + || true; \
    fi

USER $UID:$GID

ARG BUILD_HASH
ENV WEBUI_BUILD_VERSION=${BUILD_HASH}
ENV DOCKER=true

CMD [ "bash", "start.sh"]