# mAI Installation Guide

This guide covers various installation methods for mAI, from simple Docker setups to Kubernetes deployments.

## Quick Start with Docker (Recommended)

### Prerequisites
- Docker Desktop (Mac/Windows) or Docker Engine (Linux)
- 4GB+ RAM
- 10GB+ free disk space

### One-Line Installation

```bash
docker run -d -p 3000:8080 -v mai_data:/app/backend/data -e OLLAMA_BASE_URL=http://host.docker.internal:11434 --name mai --restart always ghcr.io/open-webui/open-webui:main
```

Access mAI at: http://localhost:3000

## Installation Methods

### 1. Docker Compose (Recommended for Development)

#### With Host Ollama
If you already have Ollama installed:

```bash
# Clone repository
git clone https://github.com/yourusername/mAI.git
cd mAI

# Start with host Ollama
docker compose -f docker-compose-host-ollama.yaml up -d
```

#### Full Stack Installation
For a complete setup including Ollama:

```bash
# Start both mAI and Ollama
docker compose up -d

# Pull your first model
docker exec ollama ollama pull llama3.1:8b
```

### 2. Direct Docker Run

#### Basic Setup
```bash
docker run -d \
  -p 3000:8080 \
  -v mai_data:/app/backend/data \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -e WEBUI_NAME="mAI" \
  --name mai \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

#### With Ollama Container
```bash
# Start Ollama
docker run -d \
  -v ollama:/root/.ollama \
  -p 11434:11434 \
  --name ollama \
  ollama/ollama

# Start mAI
docker run -d \
  -p 3000:8080 \
  -v mai_data:/app/backend/data \
  -e OLLAMA_BASE_URL=http://ollama:11434 \
  --link ollama \
  --name mai \
  ghcr.io/open-webui/open-webui:main
```

### 3. Kubernetes Deployment

#### Using Kustomize

For CPU-only deployment:
```bash
kubectl apply -f ./kubernetes/manifest/base
```

For GPU-enabled deployment:
```bash
kubectl apply -k ./kubernetes/manifest
```

#### Using Helm

Package Helm chart:
```bash
helm package ./kubernetes/helm/
```

Install CPU-only:
```bash
helm install mai ./mai-*.tgz
```

Install with GPU support:
```bash
helm install mai ./mai-*.tgz \
  --set ollama.resources.limits.nvidia.com/gpu="1"
```

Check `kubernetes/helm/values.yaml` for customization options.

### 4. Manual Installation (Advanced)

#### Backend Setup
```bash
# Clone repository
git clone https://github.com/yourusername/mAI.git
cd mAI/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start backend
python -m open_webui.main
```

#### Frontend Setup
```bash
cd ../  # Back to project root

# Install dependencies
npm install

# Build frontend
npm run build

# Preview production build
npm run preview
```

## Post-Installation Setup

### 1. Create Admin Account
- Navigate to http://localhost:3000
- Click "Sign up"
- The first account created becomes the admin

### 2. Configure Ollama Connection
- Go to Settings → General
- Verify Ollama URL is correct
- Test connection with "Verify"

### 3. Pull AI Models
Via mAI interface:
- Settings → Models → Pull a model
- Enter model name (e.g., `llama3.1:8b`)
- Click download

Via command line:
```bash
# For Docker Ollama
docker exec ollama ollama pull llama3.1:8b

# For host Ollama
ollama pull llama3.1:8b
```

### 4. Configure User Settings
- Profile → Settings
- Set theme preference
- Configure language
- Adjust chat settings

## System Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 10GB
- **OS**: Linux, macOS, Windows

### Recommended Requirements
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 50GB+ (for models)
- **GPU**: Optional but recommended for better performance

## Environment Variables

Key configuration options:

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | Ollama API endpoint | `http://localhost:11434` |
| `WEBUI_NAME` | Application name | `mAI` |
| `WEBUI_AUTH` | Enable authentication | `true` |
| `WEBUI_SECRET_KEY` | JWT secret key | (auto-generated) |
| `PORT` | Backend port | `8080` |

## Updating mAI

### Docker Update
```bash
# Pull latest image
docker pull ghcr.io/open-webui/open-webui:main

# Recreate container
docker compose down
docker compose up -d
```

### Manual Update
```bash
# Pull latest code
git pull origin main

# Update backend
cd backend
pip install -r requirements.txt
alembic upgrade head

# Update frontend
cd ..
npm install
npm run build
```

## Troubleshooting Installation

### Port Already in Use
```bash
# Find process using port
lsof -i :3000  # Mac/Linux
netstat -ano | findstr :3000  # Windows

# Use different port
docker run -p 3001:8080 ...
```

### Permission Denied
```bash
# Fix volume permissions
docker exec mai chown -R 1000:1000 /app/backend/data
```

### Cannot Connect to Ollama
1. Verify Ollama is running: `curl http://localhost:11434/api/tags`
2. Check Docker network: `docker network ls`
3. Use correct URL:
   - Host Ollama: `http://host.docker.internal:11434`
   - Docker Ollama: `http://ollama:11434`

### Database Errors
```bash
# Reset database (WARNING: Deletes all data)
docker exec mai rm /app/backend/data/webui.db
docker restart mai
```

## Uninstallation

### Docker
```bash
# Stop and remove containers
docker compose down

# Remove volumes (WARNING: Deletes all data)
docker volume rm mai_data mai_ollama

# Remove images
docker rmi ghcr.io/open-webui/open-webui:main
```

### Manual
```bash
# Stop services
pkill -f "open_webui.main"

# Remove virtual environment
rm -rf backend/venv

# Remove node modules
rm -rf node_modules

# Remove data (optional)
rm -rf backend/data
```

## Next Steps

1. Check out the [Docker Setup Guide](./docker-setup.md) for advanced Docker configurations
2. Review [Troubleshooting Guide](./troubleshooting.md) for common issues
3. Set up [SSL/HTTPS](../deployment/hetzner-guide.md#5-ssl-setup) for production
4. Configure [backups](../deployment/hetzner-guide.md#7-backup-strategy)

For production deployments, see our [Deployment Guide](../deployment/hetzner-guide.md).