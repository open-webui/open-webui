# Docker Configuration

## Building mAI

### Production Build
```bash
docker build -t mai-production:latest .
```

### Development Build
```bash
docker build -t mai-dev:latest .
```

## Docker Compose Examples

### Production with External Ollama
```yaml
services:
  mai:
    image: mai-production:latest
    container_name: mai-production
    volumes:
      - mai-data:/app/backend/data
    ports:
      - "3000:8080"
    environment:
      - WEBUI_NAME=mAI
      - OLLAMA_BASE_URL=http://ollama-server:11434
      - ENABLE_SIGNUP=false
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  mai-data:
    name: mai_production_data
```

### Development with Local Ollama
```yaml
services:
  mai:
    image: mai-dev:latest
    container_name: mai-dev
    volumes:
      - mai-dev-data:/app/backend/data
    ports:
      - "3002:8080"
    environment:
      - WEBUI_NAME=mAI Development
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped

volumes:
  mai-dev-data:
    name: mai_dev_data
```

## Volume Management

### Backup
```bash
# Create backup
docker run --rm -v mai-data:/data -v $(pwd):/backup alpine tar czf /backup/mai-backup-$(date +%Y%m%d).tar.gz -C /data .
```

### Restore
```bash
# Restore from backup
docker run --rm -v mai-data:/data -v $(pwd):/backup alpine tar xzf /backup/mai-backup.tar.gz -C /data
```

## Container Management

### View Logs
```bash
docker logs -f mai-production
```

### Access Container Shell
```bash
docker exec -it mai-production bash
```

### Health Check
```bash
docker exec mai-production curl -s http://localhost:8080/health
```

## Resource Limits (Optional)

```yaml
services:
  mai:
    # ... other config ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## Networking

### With Reverse Proxy (Caddy/Nginx)
```yaml
services:
  mai:
    # ... other config ...
    networks:
      - web
    labels:
      - "caddy=mai.example.com"
      - "caddy.reverse_proxy={{upstreams 8080}}"

networks:
  web:
    external: true
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs mai-production

# Check health
docker ps -a | grep mai
```

### Reset Configuration
```bash
# Remove volume and start fresh
docker-compose down -v
docker-compose up -d
```

### Permission Issues
```bash
# Fix permissions
docker exec mai-production chown -R $UID:$GID /app/backend/data
```

## Multi-Tenant Usage Tracking

mAI includes automated usage tracking for OpenRouter API usage:

### Automated Features
- **API Key Sync**: OpenRouter keys entered in Settings automatically sync to database
- **External User Learning**: System learns OpenRouter user mappings automatically  
- **Real-time Tracking**: Usage recorded immediately with live dashboard updates
- **Multi-organization Support**: Single instance handles multiple client organizations

### Configuration
No manual configuration required! Simply:
1. Deploy container as shown above
2. Clients enter their OpenRouter API key in Settings → Connections
3. Usage tracking starts automatically

### Monitoring
- **Admin Dashboard**: Settings → Usage shows real-time usage statistics
- **Live Updates**: Dashboard refreshes every 30 seconds
- **Historical Data**: Daily and monthly usage summaries