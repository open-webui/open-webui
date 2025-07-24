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

## Deployment Models

### Single-Client Instance (Production - Hetzner Cloud)
Each client gets a dedicated mAI instance with isolated database and usage tracking.

```yaml
# docker-compose.yml for individual client deployment
version: '3.8'
services:
  mai-client:
    image: mai-production:latest
    container_name: mai-${CLIENT_NAME}
    volumes:
      - ./data:/app/backend/data
      - ./backups:/app/backups
    ports:
      - "80:8080"     # Direct HTTP access
      - "443:8080"    # HTTPS if SSL termination handled
    environment:
      - WEBUI_NAME=mAI - ${CLIENT_NAME}
      - ENABLE_SIGNUP=false
      - ENV=prod
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  client-data:
    name: mai_${CLIENT_NAME}_data
```

### Development Environment
```yaml
services:
  mai-dev:
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

## Client-Specific Deployment (Hetzner Cloud)

### Server Setup for Each Client
```bash
# SSH into client's Hetzner server
ssh root@[client-server-ip]

# Create deployment directory
mkdir /opt/mai-client
cd /opt/mai-client

# Environment-specific deployment
export CLIENT_NAME="companyabc"
envsubst < docker-compose.template.yml > docker-compose.yml

# Start client instance
docker-compose up -d
```

### Per-Client Usage Tracking

Each client instance includes isolated usage tracking:

#### Automated Features (Per Instance)
- **Single-Tenant Database**: Each client has isolated SQLite database
- **API Key Auto-Sync**: Admin enters OpenRouter key → automatic database configuration
- **External User Learning**: System learns user mappings on first API call
- **Real-time Tracking**: Live usage monitoring with 30-second updates

#### Client Admin Experience
1. **Initial Setup**: Admin creates account (first user becomes admin)
2. **API Configuration**: Settings → Connections → Enter OpenRouter API key
3. **User Management**: Admin creates accounts for 5-20 company employees
4. **Usage Monitoring**: Settings → Usage tab shows organization usage

#### Service Provider View
- **20 Separate Instances**: Each client has dedicated Hetzner server
- **Isolated Databases**: No data sharing between client organizations
- **Aggregate Monitoring**: OpenRouter dashboard shows all client API key usage
- **Per-Client Billing**: Individual usage tracking for accurate invoicing