# Multi-stage Dockerfile for Open WebUI KidsGPT
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (including dev dependencies for build)
RUN npm ci --legacy-peer-deps

# Copy source code
COPY src/ ./src/
COPY static/ ./static/
COPY scripts/ ./scripts/
COPY svelte.config.js ./
COPY tailwind.config.js ./
COPY postcss.config.js ./
COPY vite.config.ts ./
COPY tsconfig.json ./

# Build frontend
RUN npm run build

# Stage 2: Python backend
FROM python:3.11-slim AS backend

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/build ./build

# Copy other necessary files
COPY pyproject.toml ./
COPY .python-version ./
COPY CHANGELOG.md ./

# Create necessary directories
RUN mkdir -p backend/data/uploads backend/data/cache backend/data/vector_db

# Set environment variables
ENV PYTHONPATH=/app
ENV FRONTEND_BUILD_DIR=/app/build
ENV PORT=8000

# Expose port
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Run the application
CMD cd backend && uvicorn open_webui.main:app --host 0.0.0.0 --port $PORT