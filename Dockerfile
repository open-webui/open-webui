# syntax=docker/dockerfile:1

FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Minimal OS deps for common Python wheels/builds
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      curl \
      git \
      build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install backend Python deps
COPY backend/requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt

RUN mkdir -p /app/backend

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /app/backend

EXPOSE 8503

ENTRYPOINT ["/entrypoint.sh"]
