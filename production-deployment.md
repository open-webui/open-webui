# Production Deployment Strategy

## For Hetzner Cloud & Client Deployments

### 1. Docker Compose Production File

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  mai-db-migrate:
    build: 
      context: .
      dockerfile: Dockerfile.production
    command: |
      bash -c "
        cd /app/backend &&
        python -c 'from open_webui.config import run_migrations; run_migrations()' &&
        echo 'Migrations completed successfully'
      "
    volumes:
      - mai_data:/app/backend/data
    environment:
      - DATABASE_URL=sqlite:///app/backend/data/webui.db
    restart: "no"

  mai-app:
    build: 
      context: .
      dockerfile: Dockerfile.production
    ports:
      - "3002:8080"
    volumes:
      - mai_data:/app/backend/data
    environment:
      - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
      - OPENAI_API_KEYS=${OPENROUTER_API_KEY}
      - OPENAI_API_BASE_URLS=https://openrouter.ai/api/v1
    depends_on:
      - mai-db-migrate
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  mai_data:
```

### 2. Production Dockerfile

```dockerfile
# Dockerfile.production
FROM mai-open-webui-customization:latest

# Add migration safety check
RUN cd /app/backend && \
    python -c "
from alembic import command
from alembic.config import Config
import sys

try:
    alembic_cfg = Config('/app/backend/alembic.ini')
    command.check(alembic_cfg)
    print('✅ Migration configuration valid')
except Exception as e:
    print(f'❌ Migration configuration error: {e}')
    sys.exit(1)
"

# Add startup script with migration
COPY production_start.sh /app/production_start.sh
RUN chmod +x /app/production_start.sh

CMD ["/app/production_start.sh"]
```

### 3. Production Startup Script

```bash
#!/bin/bash
# production_start.sh

echo "🚀 Starting mAI Production Deployment..."

# Run migrations safely
cd /app/backend
echo "📊 Running database migrations..."
python -c "
from open_webui.config import run_migrations
try:
    run_migrations()
    print('✅ Migrations completed successfully')
except Exception as e:
    print(f'❌ Migration failed: {e}')
    exit(1)
"

# Start the application
echo "🌟 Starting mAI application..."
cd /app
exec bash start.sh
```

### 4. Client Deployment Commands

```bash
# 1. Clone repository
git clone https://github.com/your-org/mai.git
cd mai

# 2. Set environment variables
cp .env.example .env.production
# Edit .env.production with client-specific settings

# 3. Deploy
docker compose -f docker-compose.production.yml up -d

# 4. Verify deployment
docker compose -f docker-compose.production.yml ps
docker compose -f docker-compose.production.yml logs mai-app
```

### 5. Health Monitoring

```bash
# Add to monitoring script
curl -f http://localhost:3002/health || echo "mAI service down"
curl -f http://localhost:3002/api/v1/client-organizations/usage/my-organization/today \
  -H "Authorization: Bearer $ADMIN_TOKEN" || echo "Usage API down"
```

## Migration Safety Features

1. **Pre-flight Check**: Validates migration before deployment
2. **Rollback Support**: Each migration has proper downgrade
3. **Data Backup**: Volume-based persistence protects data
4. **Health Checks**: Ensures service is running correctly
5. **Graceful Failures**: Migration errors prevent startup

## For Multiple Client Deployments

Create client-specific configuration:
- Environment-based API keys
- Client-specific branding
- Usage limits per organization
- Automated backup schedules