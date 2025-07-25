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

### Multi-Client Deployment (Production - Single Hetzner Server)
Single Hetzner server running multiple Docker instances (one per client) with isolated databases.

```yaml
# docker-compose.yml for individual client deployment
# Location: /opt/clients/mai-companyabc/docker-compose.yml
version: '3.8'
services:
  mai-companyabc:
    image: mai-production:latest
    container_name: mai-companyabc
    volumes:
      - ./data:/app/backend/data
      - ./backups:/app/backups
    ports:
      - "8001:8080"   # Unique port per client (8001-8020)
    environment:
      - WEBUI_NAME=mAI - Company ABC
      - ENABLE_SIGNUP=false
      - ENV=prod
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

networks:
  default:
    name: mai-network
    external: true
```

### Server Architecture
```
Hetzner Server (16-32 vCPU, 64-128GB RAM)
├── mai-client1:8001 → Company A (5 users)
├── mai-client2:8002 → Company B (12 users)  
├── mai-client3:8003 → Company C (8 users)
├── ...
└── mai-client20:8020 → Company T (15 users)

Total: 20 Docker instances, ~200 users
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

## Multi-Client Deployment (Single Hetzner Server)

### Server Setup for All Clients
```bash
# SSH into your main Hetzner server
ssh root@mai-production.hetzner-server.com

# Create Docker network for all clients
docker network create mai-network

# Setup client deployment function
setup_client() {
    local CLIENT_NAME=$1
    local PORT=$2
    
    # Create client directory
    mkdir -p /opt/clients/mai-${CLIENT_NAME}
    cd /opt/clients/mai-${CLIENT_NAME}
    
    # Generate docker-compose.yml
    cat > docker-compose.yml << EOF
version: '3.8'
services:
  mai-${CLIENT_NAME}:
    image: mai-production:latest
    container_name: mai-${CLIENT_NAME}
    ports:
      - "${PORT}:8080"
    environment:
      - WEBUI_NAME=mAI - ${CLIENT_NAME}
      - ENABLE_SIGNUP=false
      - ENV=prod
    volumes:
      - ./data:/app/backend/data
      - ./backups:/app/backups
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
networks:
  default:
    name: mai-network
    external: true
EOF
    
    # Start client instance
    docker-compose up -d
    echo "Client ${CLIENT_NAME} deployed on port ${PORT}"
}

# Deploy multiple clients
setup_client "companyabc" 8001
setup_client "companyxyz" 8002
# ... continue for all 20 clients
```

### Reverse Proxy Configuration (Nginx)
```nginx
# /etc/nginx/sites-available/mai-clients
upstream mai_companyabc {
    server localhost:8001;
}

upstream mai_companyxyz {
    server localhost:8002;
}

server {
    listen 80;
    server_name companyabc.mai-production.com;
    location / {
        proxy_pass http://mai_companyabc;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 80;
    server_name companyxyz.mai-production.com;
    location / {
        proxy_pass http://mai_companyxyz;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Per-Client Usage Tracking

Each client instance includes isolated usage tracking:

#### Automated Features (Per Instance) ✅ PRODUCTION READY
- **Single-Tenant Database**: Each client has isolated SQLite database
- **API Key Auto-Sync**: Admin enters OpenRouter key → automatic database configuration
- **External User Learning**: System learns user mappings on first API call
- **Real-time Tracking**: Live usage monitoring with 30-second updates
- **Background Usage Sync**: Automatic OpenRouter API polling every 10 minutes
- **Currency Display Fix**: Proper formatting for all cost amounts (including small values)
- **Production Database Tools**: Safe cleanup and initialization scripts included

#### Admin User Workflow (Per Client)
1. **Admin Registration**: First user to register automatically becomes admin
2. **Signup Auto-Disable**: System disables public signup after first user
3. **API Key Configuration**: Admin enters OpenRouter key in Settings → Connections
4. **User Account Creation**: Admin creates employee accounts via Admin → Users panel
   - Navigate to **Admin** (sidebar) → **Users** tab
   - **Add User** for each employee (name, email, password, role: "user")
   - Distribute credentials to 4-19 company employees
5. **Usage Monitoring**: Admin monitors combined usage in Settings → Usage

#### Employee User Experience
- **Login Access**: Use credentials provided by admin
- **Standard Permissions**: Regular user role (no admin access)
- **Individual Tracking**: Each user gets unique external_user from OpenRouter
- **Shared API Key**: All users share organization's OpenRouter API key

#### Open WebUI User Management
```
mAI Instance Structure (per client):
├── Admin User (1)
│   ├── Full system control
│   ├── Manages OpenRouter API key
│   ├── Creates/manages employee accounts
│   ├── Monitors usage dashboard
│   └── Configures instance settings
└── Regular Users (4-19)
    ├── Standard chat access
    ├── Individual usage tracking
    ├── No admin panel access
    └── Cannot create/manage users
```

#### Service Provider Benefits
- **Centralized Infrastructure**: Single server hosting all 20 client instances
- **Resource Efficiency**: Optimized resource utilization across clients
- **Simplified Management**: All containers managed from one server
- **Cost Optimization**: Single server costs vs 20 separate servers
- **Minimal Client Management**: Clients manage their own users internally
- **Automated User Tracking**: Each user gets unique external_user automatically
- **OpenRouter Dashboard**: Aggregate view of all client API key usage
- **Production Ready**: Clean codebase with debugging files removed
- **Reliable Usage Tracking**: Background sync ensures accurate billing data
- **1.3x Markup Pricing**: Automated profit calculation and tracking

### Management Commands
```bash
# View all client containers
docker ps --filter "name=mai-"

# Monitor specific client
docker logs mai-companyabc --follow

# Restart client instance
cd /opt/clients/mai-companyabc && docker-compose restart

# Update all clients
for client in /opt/clients/mai-*; do
    cd "$client" && docker-compose pull && docker-compose up -d
done

# Backup all client data
for client in /opt/clients/mai-*; do
    tar -czf "${client##*/}-backup-$(date +%Y%m%d).tar.gz" -C "$client" data
done
```