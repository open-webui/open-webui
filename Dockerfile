# 기존 WebUI Frontend 빌드
FROM --platform=$BUILDPLATFORM node:22-alpine3.20 AS build
ARG BUILD_HASH

WORKDIR /app

COPY package.json package-lock.json ./

ENV NODE_OPTIONS="--max-old-space-size=4096"

RUN npm ci

COPY . .
ENV APP_BUILD_HASH=${BUILD_HASH}
RUN npm run build

# 기존 WebUI Backend 설정
FROM python:3.11-slim-bookworm AS base

ARG USE_CUDA
ARG USE_OLLAMA
ARG USE_CUDA_VER
ARG USE_EMBEDDING_MODEL
ARG USE_RERANKING_MODEL
ARG UID
ARG GID

# 환경 변수 설정
ENV ENV=prod \
    PORT=8080 \
    USE_OLLAMA_DOCKER=${USE_OLLAMA} \
    USE_CUDA_DOCKER=${USE_CUDA} \
    USE_CUDA_DOCKER_VER=${USE_CUDA_VER} \
    USE_EMBEDDING_MODEL_DOCKER=${USE_EMBEDDING_MODEL} \
    USE_RERANKING_MODEL_DOCKER=${USE_RERANKING_MODEL}

WORKDIR /app/backend

RUN mkdir -p /app/backend/data/cache

# 기존 Python 패키지 설치 유지
COPY --chown=$UID:$GID ./backend/requirements.txt ./requirements.txt

RUN pip3 install uv && \
    if [ "$USE_CUDA" = "true" ]; then \
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/$USE_CUDA_DOCKER_VER --no-cache-dir && \
    uv pip install --system -r requirements.txt --no-cache-dir; \
    else \
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --no-cache-dir && \
    uv pip install --system -r requirements.txt --no-cache-dir; \
    fi

# IIS 서버 추가
FROM mcr.microsoft.com/windows/servercore/iis AS iis

# Git 설치
RUN powershell -Command \
    Invoke-WebRequest -Uri "https://github.com/git-for-windows/git/releases/latest/download/Git-64-bit.exe" -OutFile "C:\Git-64-bit.exe"; \
    Start-Process -FilePath "C:\Git-64-bit.exe" -ArgumentList "/VERYSILENT /NORESTART" -Wait; \
    Remove-Item -Path "C:\Git-64-bit.exe"

# GitHub 저장소에서 develop 브랜치 가져오기
WORKDIR C:\inetpub\wwwroot
RUN git clone --single-branch --branch develop https://github.com/Merge-Feat/hkust-open-webui.git .

# IIS 포트 개방
EXPOSE 80

# IIS 서비스 실행
CMD ["powershell", "Start-Service", "W3SVC", ";", "while ($true) { Start-Sleep -Seconds 100 }"]
