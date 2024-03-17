# syntax=docker/dockerfile:1
ARG CUDA_VERSION=12.3.2

######## WebUI frontend ########
FROM node:21-alpine3.19 as build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

######## CPU-only WebUI backend ########
# To support both CPU and GPU backend, we need to keep the ability to build the CPU-only image.
#FROM python:3.11-slim-bookworm as base
FROM --platform=linux/amd64 cgr.dev/chainguard/python:latest-dev AS cpu-build-amd64
#FROM --platform=linux/amd64 ubuntu:22.04 AS cpu-builder-amd64

#FROM --platform=linux/amd64 cpu-builder-amd64 AS cpu-build-amd64
#RUN OPENWEBUI_CPU_TARGET="cpu" sh gen_linux.sh

#FROM --platform=linux/amd64 cpu-builder-amd64 AS cpu_avx-build-amd64
#RUN OPENWEBUI_CPU_TARGET="cpu_avx" sh gen_linux.sh

#FROM --platform=linux/amd64 cpu-builder-amd64 AS cpu_avx2-build-amd64
#RUN OPENWEBUI_CPU_TARGET="cpu_avx2" sh gen_linux.sh

######## CUDA WebUI backend ########
#FROM --platform=linux/amd64 nvidia/cuda:"$CUDA_VERSION"-devel-ubuntu22.04 AS cuda-build-amd64
#FROM --platform=linux/amd64 cgr.dev/chainguard/pytorch-cuda12:latest AS cuda-build-amd64 # fails with python requirements conflicts

# Set environment variables for NVIDIA Container Toolkit
ENV LD_LIBRARY_PATH=/usr/local/nvidia/lib:/usr/local/nvidia/lib64 \
    NVIDIA_DRIVER_CAPABILITIES=all \
    NVIDIA_VISIBLE_DEVICES=all

ENV ENV=prod \
    PORT=8080

## Base URL Config ##
ENV OLLAMA_BASE_URL="/ollama" \
    OPENAI_API_BASE_URL=""

## API Key and Security Config ##
ENV OPENAI_API_KEY="" \
    WEBUI_SECRET_KEY="" \
    SCARF_NO_ANALYTICS=true \
    DO_NOT_TRACK=true

######## Preloaded models ########
# whisper TTS Settings
ENV WHISPER_MODEL="base" \
    WHISPER_MODEL_DIR="/app/backend/data/cache/whisper/models"

# RAG Embedding Model Settings
# any sentence transformer model; models to use can be found at https://huggingface.co/models?library=sentence-transformers
# Leaderboard: https://huggingface.co/spaces/mteb/leaderboard 
# for better performance and multilangauge support use "intfloat/multilingual-e5-large" (~2.5GB) or "intfloat/multilingual-e5-base" (~1.5GB)
# IMPORTANT: If you change the default model (all-MiniLM-L6-v2) and vice versa, you aren't able to use RAG Chat with your previous documents loaded in the WebUI! You need to re-embed them.
ENV RAG_EMBEDDING_MODEL="all-MiniLM-L6-v2" \
    # device type for whisper tts and embedding models - "cpu" (default), "cuda" (NVIDIA GPU and CUDA required), or "mps" (apple silicon) - choosing this right can lead to better performance
    RAG_EMBEDDING_MODEL_DEVICE_TYPE="cuda" \
    RAG_EMBEDDING_MODEL_DIR="/app/backend/data/cache/embedding/models" \
    SENTENCE_TRANSFORMERS_HOME=$RAG_EMBEDDING_MODEL_DIR

######## Preloaded models ########
WORKDIR /app/backend

# Install Python & dependencies in the container
# Used for Debian
#RUN apt-get update && \
#    apt-get install -y --no-install-recommends python3.11 python3-pip ffmpeg libsm6 libxext6 pandoc netcat-openbsd && \
#    rm -rf /var/lib/apt/lists/*

# Used for Redhat
#RUN apk update && \
#    apk add --no-install-recommends python3.11 python3-pip ffmpeg libsm6 libxext6 pandoc netcat-openbsd && \
#    apk del /var/cache/apk/*.tbz2

# Install only the dependencies in the container, python will come from the base image used
RUN apk update && \
    apk add --no-install-recommends ffmpeg libsm6 libxext6 pandoc netcat-openbsd && \
    apk del /var/cache/apk/*.tbz2

COPY ./backend/requirements.txt ./requirements.txt
RUN pip3 install torch torchvision torchaudio --no-cache-dir && \
    pip3 install -r requirements.txt --no-cache-dir

# copy built frontend files
COPY --from=build /app/build /app/build
COPY --from=build /app/CHANGELOG.md /app/CHANGELOG.md
COPY --from=build /app/package.json /app/package.json

# copy backend files
COPY ./backend .

EXPOSE 8080

CMD [ "bash", "start.sh"]
