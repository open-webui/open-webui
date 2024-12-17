# syntax=docker/dockerfile:1.4

######## Base image ########
FROM --platform=$BUILDPLATFORM python:3.11-slim-bookworm as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create a non-root user
ARG UID=1000
ARG GID=0

# Environment variables for API configuration
ARG VITE_WEBUI_BASE_URL 
ARG VITE_WEBUI_API_BASE_URL
ARG WEBUI_BASE_URL
ARG WEBUI_API_BASE_URL
ARG OLLAMA_BASE_URL
ARG OPENAI_API_KEY
ARG OPENAI_API_BASE_URL
ARG BUILD_HASH

######## WebUI frontend ########
FROM --platform=$BUILDPLATFORM node:22-alpine3.20 AS build
ARG BUILD_HASH

ARG VITE_WEBUI_BASE_URL
ARG VITE_WEBUI_API_BASE_URL
ARG WEBUI_BASE_URL
ARG WEBUI_API_BASE_URL
ARG OLLAMA_BASE_URL
ARG OPENAI_API_KEY
ARG OPENAI_API_BASE_URL

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build frontend
RUN npm run build

######## WebUI backend ########
FROM base as backend

# Set working directory
WORKDIR /app/backend

# Copy backend requirements
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy backend source code
COPY backend/ .

# Create cache directory
RUN mkdir -p /app/backend/data/cache

######## Final image ########
FROM backend as final

# Copy frontend build
COPY --from=build /app/dist /app/backend/open_webui/web

# Set environment variables
ENV WEBUI_BASE_URL=${WEBUI_BASE_URL} \
    WEBUI_API_BASE_URL=${WEBUI_API_BASE_URL} \
    OLLAMA_BASE_URL=${OLLAMA_BASE_URL} \
    OPENAI_API_KEY=${OPENAI_API_KEY} \
    OPENAI_API_BASE_URL=${OPENAI_API_BASE_URL} \
    BUILD_HASH=${BUILD_HASH}

# Expose port
EXPOSE 8080

# Set working directory
WORKDIR /app/backend

# Start the application
CMD ["python", "-m", "open_webui.main"]
