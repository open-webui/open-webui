# Docker & Deployment

## Development with Docker (Recommended)

### Host Ollama Setup (Recommended)
```bash
# Use host Ollama for local development
docker compose -f docker-compose-host-ollama.yaml up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Docker Ollama Setup
```bash
# Creates isolated Ollama instance
docker compose up -d
```

## Docker Configuration Best Practices

### Local Development Configuration
Use `docker-compose-host-ollama.yaml` to connect to your host Ollama installation:

```yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    volumes:
      - open-webui:/app/backend/data
    environment:
      - 'OLLAMA_BASE_URL=http://host.docker.internal:11434'
      - 'WEBUI_NAME=mAI'
    ports:
      - 3000:8080
    extra_hosts:
      - host.docker.internal:host-gateway

volumes:
  open-webui:
    external: true
    name: mai_open-webui  # Use existing volume with data
```

### Critical Docker Notes
- **Always use named volumes** with `external: true` to preserve data
- **Never create new volumes** unless intentionally starting fresh
- **For updates**: Copy files directly to running container instead of rebuilding
- **Browser caching**: Always clear cache after favicon/asset updates

## Production Deployment

### Via Makefile
```bash
make install              # docker-compose up -d
make start               # docker-compose start
make stop                # docker-compose stop
make update              # Pull, rebuild, restart
```

### Manual Production Commands
```bash
# Build and start
docker compose -f docker-compose.prod.yaml up -d

# Update production
docker compose pull
docker compose up -d --force-recreate
```

## Volume Management

### Best Practices
1. **Named Volumes**: Always use explicitly named volumes
2. **External Volumes**: Use `external: true` to reference existing volumes
3. **Data Persistence**: Never delete volumes without backup
4. **Volume Inspection**: Use `docker volume ls` and `docker volume inspect`

### Volume Commands
```bash
# List volumes
docker volume ls | grep mai

# Inspect volume contents
docker run --rm -v volume_name:/data alpine ls -la /data/

# Backup volume
docker run --rm -v mai_open-webui:/data -v $(pwd):/backup alpine tar czf /backup/mai-backup.tar.gz -C /data .

# Restore volume
docker run --rm -v mai_open-webui:/data -v $(pwd):/backup alpine tar xzf /backup/mai-backup.tar.gz -C /data
```

### Common Issues & Solutions
- **Multiple volumes with same data**: Check timestamps to identify the active one
- **Lost data after rebuild**: Always use `external: true` for existing volumes
- **Ollama models missing**: Connect to host Ollama or mount host directory

## Quick Updates Without Rebuilding

### Asset Updates
```bash
# Copy updated files directly to running container
docker cp static/static/favicon.ico open-webui:/app/backend/static/
docker cp static/static/favicon.png open-webui:/app/backend/static/
docker cp static/manifest.json open-webui:/app/backend/static/
docker restart open-webui
```

### Code Updates
```bash
# Copy updated frontend build
docker cp build/. open-webui:/app/build/
docker restart open-webui

# Copy backend changes
docker cp backend/open_webui/. open-webui:/app/backend/open_webui/
docker restart open-webui
```

## Environment Variables

### Development
```bash
export PORT=8080
export OLLAMA_BASE_URL=http://localhost:11434
export ENV=dev
export WEBUI_NAME=mAI
```

### Production
```bash
export ENV=prod
export WEBUI_URL=https://yourdomain.com
export DATABASE_URL=postgresql://user:pass@host:port/db
export REDIS_URL=redis://localhost:6379
```

## Cleanup Commands

### Safe Cleanup
```bash
# Remove unused images (keep volumes)
docker image prune

# Remove stopped containers
docker container prune
```

### Dangerous Cleanup (USE WITH CAUTION)
```bash
# Remove ALL unused volumes (WILL DELETE DATA)
docker volume prune

# Complete system cleanup (WILL DELETE EVERYTHING)
docker system prune -a --volumes
```

## Monitoring & Logs

### Log Management
```bash
# Follow logs
docker compose logs -f

# Specific service logs
docker compose logs -f open-webui

# Log rotation
docker compose logs --tail=1000 open-webui
```

### Health Checks
```bash
# Check container status
docker ps

# Check volume usage
docker system df

# Check container health
docker inspect open-webui | grep Health -A 10
```