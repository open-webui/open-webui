# Deployment Guide

This guide covers deploying mAI for production use.

## Overview

mAI is deployed using Docker and is designed to serve 20 small companies in Poland, each with 5-20 employees.

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

4. **Initialize OpenRouter** (first time only):
   ```bash
   docker exec mai-company-name python /app/scripts/openrouter/production_fix.py init
   ```

## Key Features

- **OpenRouter Filtering**: 12 curated AI models
- **Polish Localization**: Full Polish language support
- **Custom Branding**: mAI branding and themes
- **Background Patterns**: Customizable chat backgrounds
- **Multi-Company Ready**: Same image for all deployments

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

## Multi-Company Deployment

Each company gets:
- Same Docker image
- Same 12 OpenRouter models
- Separate data volume
- Custom display name

Example for multiple companies:
```bash
# Company A
docker run -d --name mai-company-a -v mai-company-a:/app/backend/data mai-production:latest

# Company B
docker run -d --name mai-company-b -v mai-company-b:/app/backend/data mai-production:latest
```