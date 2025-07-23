# Production Docker Setup with OpenRouter Filtering

Now that OpenRouter scripts are included in the Docker image, deployment is straightforward.

## Building for Production

```bash
# Build the image with your customizations
docker build -t mai-production:latest .

# Tag for your registry (example with Docker Hub)
docker tag mai-production:latest yourusername/mai:latest

# Push to registry
docker push yourusername/mai:latest
```

## Production docker-compose.yaml

```yaml
services:
  mai:
    image: yourusername/mai:latest
    container_name: mai-production
    volumes:
      - mai-data:/app/backend/data
    ports:
      - "3000:8080"
    environment:
      - WEBUI_NAME=mAI
      - WEBUI_URL=https://mai.yourdomain.com
      - OLLAMA_BASE_URL=http://ollama:11434
      # Add your other environment variables
    restart: unless-stopped

volumes:
  mai-data:
    name: mai_production_data
```

## First Run Initialization

On first deployment, initialize OpenRouter filtering:

```bash
# After container starts, run once:
docker exec mai-production python /app/scripts/openrouter/production_fix.py init

# Verify configuration
docker exec mai-production python /app/scripts/openrouter/verify_config.py
```

## Managing Models

```bash
# List current models
docker exec mai-production python /app/scripts/openrouter/manage_models.py list

# Add a model
docker exec mai-production python /app/scripts/openrouter/manage_models.py add "model-id"

# Remove a model
docker exec mai-production python /app/scripts/openrouter/manage_models.py remove "model-id"
```

## Important Notes

1. The scripts are now part of the Docker image - no manual copying needed
2. The initialization only needs to run once per deployment
3. Configuration persists in the database volume
4. Changes survive container restarts

This setup is production-ready for deployment to Hetzner or any Docker host.