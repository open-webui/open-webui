# SQLite + Supabase Sync System - Docker Image
# Phase 1: High Availability Sync Container

FROM python:3.11-slim

# Metadata
LABEL maintainer="Open WebUI Sync System"
LABEL description="High availability database synchronization service"
LABEL version="1.0.0"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    curl \
    jq \
    docker.io \
    uuid-runtime \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy Python requirements and install
COPY python/requirements.txt /app/python/requirements.txt
RUN pip install --no-cache-dir -r /app/python/requirements.txt

# Copy application code
COPY python/ /app/python/
COPY scripts/ /app/scripts/
COPY config/ /app/config/

# Make scripts executable
RUN chmod +x /app/scripts/*.sh

# Create logs directory
RUN mkdir -p /app/logs

# Expose API port
EXPOSE 9443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:${API_PORT:-9443}/health || exit 1

# Copy and set entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
