# syntax=docker/dockerfile:1

######## WebUI frontend ########
FROM node:21-alpine3.19 as build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

######## WebUI backend ########
ARG CUDA_VERSION=12.3.2
#FROM nvidia/cuda:$CUDA_VERSION-devel-ubuntu22.04 as base
FROM --platform=linux/amd64 nvidia/cuda:$CUDA_VERSION-devel-ubuntu22.04 AS cuda-build-amd64

# Set environment variables for NVIDIA Container Toolkit
ENV LD_LIBRARY_PATH=/usr/local/nvidia/lib:/usr/local/nvidia/lib64
ENV NVIDIA_DRIVER_CAPABILITIES=all
ENV NVIDIA_VISIBLE_DEVICES=all

# Install NVIDIA CUDA toolkit and libraries in the container
#RUN apt-get update && \
#    apt-get install -y --no-install-recommends nvidia-cuda-toolkit nvidia-cuda-dev nvidia-cudnn-dev

ENV ENV=prod
ENV PORT ""

ENV OLLAMA_BASE_URL "/ollama"

ENV OPENAI_API_BASE_URL ""
ENV OPENAI_API_KEY ""

ENV WEBUI_SECRET_KEY ""

ENV SCARF_NO_ANALYTICS true
ENV DO_NOT_TRACK true

######## Preloaded models ########
# whisper TTS Settings
ENV WHISPER_MODEL="base"
ENV WHISPER_MODEL_DIR="/app/backend/data/cache/whisper/models"

# RAG Embedding Model Settings
# any sentence transformer model; models to use can be found at https://huggingface.co/models?library=sentence-transformers
# Leaderboard: https://huggingface.co/spaces/mteb/leaderboard 
# for better performance and multilangauge support use "intfloat/multilingual-e5-large" (~2.5GB) or "intfloat/multilingual-e5-base" (~1.5GB)
# IMPORTANT: If you change the default model (all-MiniLM-L6-v2) and vice versa, you aren't able to use RAG Chat with your previous documents loaded in the WebUI! You need to re-embed them.
ENV RAG_EMBEDDING_MODEL="all-MiniLM-L6-v2"
# device type for whisper tts and embedding models - "cpu" (default), "cuda" (NVIDIA GPU and CUDA required), or "mps" (apple silicon) - choosing this right can lead to better performance
ENV RAG_EMBEDDING_MODEL_DEVICE_TYPE="cuda"
ENV RAG_EMBEDDING_MODEL_DIR="/app/backend/data/cache/embedding/models"
ENV SENTENCE_TRANSFORMERS_HOME $RAG_EMBEDDING_MODEL_DIR

######## Preloaded models ########
WORKDIR /app/backend

# Install Python & dependencies in the container
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3.11 python3-pip ffmpeg libsm6 libxext6 pandoc netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

COPY ./backend/requirements.txt ./requirements.txt
RUN pip3 install torch torchvision torchaudio --no-cache-dir
RUN pip3 install -r requirements.txt --no-cache-dir

# copy embedding weight from build
RUN mkdir -p /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2
COPY --from=build /app/onnx /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx

# copy built frontend files
COPY --from=build /app/build /app/build
COPY --from=build /app/CHANGELOG.md /app/CHANGELOG.md
COPY --from=build /app/package.json /app/package.json

# copy backend files
COPY ./backend .

CMD [ "bash", "start.sh"]
