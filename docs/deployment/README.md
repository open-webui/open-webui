# Deployment Guide

This guide covers deploying mAI for production use.

## Overview

mAI is deployed using Docker and is designed to serve 20 small companies in Poland, each with 5-20 employees. Each deployment includes automated OpenRouter usage tracking with 1.3x markup pricing.

## Quick Start

1. **Build the Docker image:**
   ```bash
   docker build -t mai-production:latest .
   ```

2. **Create docker-compose.yaml:**
   ```yaml
   services:
     mai:
       image: mai-production:latest
       container_name: mai-company-name
       volumes:
         - mai-data:/app/backend/data
       ports:
         - "3000:8080"
       environment:
         - WEBUI_NAME=mAI - Company Name
         - OLLAMA_BASE_URL=http://ollama:11434
       restart: unless-stopped
   
   volumes:
     mai-data:
       name: mai_company_data
   ```

3. **Start the container:**
   ```bash
   docker-compose up -d
   ```

4. **Initialize Database** (first time only):
   ```bash
   # Initialize usage tracking database with sample data
   docker exec mai-company-name python /app/create_tables.py
   ```

5. **Configure OpenRouter Usage Tracking**:
   - Admin logs in and navigates to Settings → Connections
   - Enters OpenRouter API key
   - Background sync starts automatically (every 10 minutes)
   - Usage data appears in Settings → Usage dashboard

## Configuration

See specific guides:
- [Docker Setup](./docker.md) - Detailed Docker configuration
- [OpenRouter Setup](./openrouter.md) - AI model configuration

## Environment Variables

Essential variables for production:
- `WEBUI_NAME` - Display name (e.g., "mAI - Company X")
- `OLLAMA_BASE_URL` - Ollama server URL
- `WEBUI_SECRET_KEY` - Security key (auto-generated if not set)
- `ENABLE_SIGNUP` - Set to `false` for production
- `OPENROUTER_USAGE_SYNC_INTERVAL` - Background sync interval in seconds (default: 600)
- `LOG_LEVEL` - Logging level for monitoring (default: INFO)

## Multi-Company Deployment

Each company gets:
- Same Docker image with production-ready usage tracking
- Access to all OpenRouter models with transparent pricing
- Separate isolated database (SQLite per container)
- Custom display name and branding
- Automated usage monitoring with 1.3x markup
- Real-time usage dashboard for admin users
- Background sync service for accurate billing

Example for multiple companies:
```bash
# Company A
docker run -d --name mai-company-a -v mai-company-a:/app/backend/data mai-production:latest

# Company B
docker run -d --name mai-company-b -v mai-company-b:/app/backend/data mai-production:latest
```