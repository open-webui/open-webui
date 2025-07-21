# mAI Docker Setup Guide

This guide covers setting up mAI using Docker for both development and production environments.

## Prerequisites

- Docker Desktop (Mac/Windows) or Docker Engine (Linux)
- Docker Compose v2.0+
- 4GB+ RAM available for Docker
- (Optional) Ollama installed on host machine

## Quick Start

### Option 1: Using Host Ollama (Recommended)

If you already have Ollama installed on your machine with models:

```bash
# Clone the repository
git clone https://github.com/yourusername/mAI.git
cd mAI

# Start mAI connected to your host Ollama
docker compose -f docker-compose-host-ollama.yaml up -d

# Access mAI at http://localhost:3000
```

### Option 2: Complete Docker Setup

For a fully containerized setup including Ollama:

```bash
# Start both mAI and Ollama
docker compose up -d

# Pull a model into the containerized Ollama
docker exec ollama ollama pull llama3.1:8b

# Access mAI at http://localhost:3000
```

## Docker Compose Configurations

### docker-compose-host-ollama.yaml (Recommended for Development)

```yaml
services:
  open-webui:
    build:
      context: .
      dockerfile: Dockerfile
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    volumes:
      - open-webui:/app/backend/data
    ports:
      - 3000:8080
    environment:
      - 'OLLAMA_BASE_URL=http://host.docker.internal:11434'
      - 'WEBUI_NAME=mAI'
      - 'WEBUI_URL=http://localhost:3000'
    extra_hosts:
      - host.docker.internal:host-gateway
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  open-webui:
    external: true
    name: mai_open-webui
```

### docker-compose.yaml (Full Stack)

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    restart: unless-stopped
    volumes:
      - ollama:/root/.ollama
    ports:
      - "11434:11434"
    environment:
      - OLLAMA_HOST=0.0.0.0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3

  open-webui:
    build:
      context: .
      dockerfile: Dockerfile
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    volumes:
      - open-webui:/app/backend/data
    depends_on:
      - ollama
    ports:
      - 3000:8080
    environment:
      - 'OLLAMA_BASE_URL=http://ollama:11434'
      - 'WEBUI_NAME=mAI'
    restart: unless-stopped

volumes:
  ollama:
    name: mai_ollama_data
  open-webui:
    name: mai_webui_data
```

## Important Volume Management

### Understanding Docker Volumes

Docker volumes persist your data (models, chat history, user accounts) between container restarts.

**Key Points:**
- Always use named volumes for data persistence
- Use `external: true` when referencing existing volumes
- Never delete volumes without backing up data first

### Managing Volumes

```bash
# List all volumes
docker volume ls

# Inspect a volume
docker volume inspect mai_open-webui

# Backup a volume
docker run --rm -v mai_open-webui:/source -v $(pwd):/backup alpine tar czf /backup/mai-backup.tar.gz -C /source .

# Restore a volume
docker run --rm -v mai_open-webui:/target -v $(pwd):/backup alpine tar xzf /backup/mai-backup.tar.gz -C /target
```

## Updating mAI

### Method 1: Quick Update (No Rebuild)

For quick updates to static files (favicons, logos, etc.):

```bash
# Copy updated files directly to running container
docker cp static/static/favicon.ico open-webui:/app/backend/static/
docker cp static/static/favicon.png open-webui:/app/backend/static/
docker cp static/manifest.json open-webui:/app/backend/static/

# Restart container
docker restart open-webui
```

### Method 2: Full Update (Rebuild)

For code changes or major updates:

```bash
# Pull latest changes
git pull origin customization

# Rebuild and restart
docker compose build --no-cache
docker compose up -d
```

## Environment Variables

### Essential Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | Ollama API endpoint | `http://ollama:11434` |
| `WEBUI_NAME` | Application name | `mAI` |
| `WEBUI_URL` | Public URL | `http://localhost:3000` |
| `WEBUI_SECRET_KEY` | JWT secret key | (auto-generated) |
| `AIOHTTP_CLIENT_TIMEOUT` | Request timeout (seconds) | `300` |
| `WORKERS` | Number of worker processes | `1` |

### Using .env File

Create a `.env` file in your project root:

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://host.docker.internal:11434

# mAI Configuration
WEBUI_NAME=mAI
WEBUI_URL=https://ai.yourdomain.com
WEBUI_SECRET_KEY=your-secret-key-here

# Performance
WORKERS=4
AIOHTTP_CLIENT_TIMEOUT=600
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs open-webui

# Common fixes:
# 1. Port conflict - change port mapping
# 2. Volume permissions - ensure proper ownership
# 3. Memory limits - increase Docker memory allocation
```

### Can't Connect to Ollama

```bash
# Test from container
docker exec open-webui curl http://ollama:11434/api/tags

# For host Ollama, ensure it's running:
ollama serve
```

### Lost Data After Update

This happens when volumes aren't properly configured:

1. Stop containers: `docker compose down`
2. Find your data volume: `docker volume ls | grep mai`
3. Update docker-compose.yaml to use existing volume with `external: true`
4. Start containers: `docker compose up -d`

## Best Practices

### Development

1. **Use Host Ollama**: Faster model switching and no duplicate storage
2. **Mount Source Code**: For live reloading during development
3. **Enable Debug Logs**: Set `LOG_LEVEL=debug` environment variable

### Production

1. **Use Named Volumes**: Ensure data persistence
2. **Set Resource Limits**: Prevent container from consuming all resources
3. **Enable Health Checks**: Monitor container health
4. **Regular Backups**: Automate volume backups

### Security

1. **Set Strong Secrets**: Always set `WEBUI_SECRET_KEY` in production
2. **Use HTTPS**: Deploy behind a reverse proxy with SSL
3. **Limit Exposed Ports**: Only expose necessary ports
4. **Regular Updates**: Keep images and dependencies updated

## Advanced Configuration

### GPU Support

For NVIDIA GPUs:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Custom Build Args

```yaml
build:
  context: .
  args:
    - OLLAMA_BASE_URL=/ollama
    - NODE_OPTIONS=--max-old-space-size=4096
```

### Multi-Container Networking

```yaml
networks:
  mai-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## Monitoring

### Container Stats

```bash
# Real-time stats
docker stats

# One-time snapshot
docker stats --no-stream
```

### Logs

```bash
# Follow logs
docker compose logs -f

# Last 100 lines
docker compose logs --tail=100

# Specific service
docker logs ollama
```

### Health Status

```bash
# Check health
docker ps --filter "name=open-webui" --format "table {{.Names}}\t{{.Status}}"
```

## Cleanup

### Remove Unused Resources

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes (CAREFUL!)
docker volume prune

# Complete cleanup
docker system prune -a --volumes
```

Remember: Always backup important data before cleanup operations!