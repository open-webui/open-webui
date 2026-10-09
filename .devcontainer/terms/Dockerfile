FROM node:22-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip git curl build-essential ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspaces/canchat-v2
