# Docker Setup Guide for ComfyUI Agent Plugin

This guide explains how to install and use the ComfyUI Agent plugin with Docker-based Open WebUI installations.

## Option 1: Using Docker Volume

1. **Create a plugins directory in your Open WebUI data volume:**
```bash
mkdir -p /path/to/open-webui/data/plugins
cd /path/to/open-webui/data/plugins
git clone https://github.com/yourusername/comfyui-agent.git
```

2. **Update your docker-compose.yml:**
```yaml
services:
  open-webui:
    image: openweb/open-webui:latest
    volumes:
      - ./data:/app/data
      - ./data/plugins:/app/extensions/plugins
      # Add ComfyUI volume
      - ./comfyui:/app/comfyui
    environment:
      - COMFYUI_API_URL=http://comfyui:8188
    depends_on:
      - comfyui

  comfyui:
    image: comfyanonymous/comfyui:latest
    ports:
      - "8188:8188"
    volumes:
      - ./comfyui:/app/comfyui
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

3. **Install plugin dependencies:**
```bash
# Enter the Open WebUI container
docker-compose exec open-webui bash

# Install plugin dependencies
cd /app/extensions/plugins/comfyui-agent
pip install -r requirements.txt
```

## Option 2: Building Custom Docker Image

1. **Create a custom Dockerfile:**
```bash
mkdir -p custom-open-webui
cd custom-open-webui
```

2. **Create Dockerfile:**
```dockerfile
FROM openweb/open-webui:latest

# Install plugin
COPY comfyui-agent /app/extensions/plugins/comfyui-agent
RUN cd /app/extensions/plugins/comfyui-agent && \
    pip install -r requirements.txt

# Set ComfyUI URL environment variable
ENV COMFYUI_API_URL=http://comfyui:8188
```

3. **Create docker-compose.yml:**
```yaml
version: '3.8'

services:
  open-webui:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
    environment:
      - COMFYUI_API_URL=http://comfyui:8188
    depends_on:
      - comfyui

  comfyui:
    image: comfyanonymous/comfyui:latest
    ports:
      - "8188:8188"
    volumes:
      - ./comfyui:/app/comfyui
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  comfyui:
```

4. **Build and run:**
```bash
docker-compose up --build -d
```

## Verifying Installation

1. **Check plugin installation:**
```bash
# Enter the Open WebUI container
docker-compose exec open-webui bash

# Run plugin tests
cd /app/extensions/plugins/comfyui-agent
python3 test_plugin.py
```

2. **Test in Python console:**
```bash
docker-compose exec open-webui python3
```
```python
from comfyui_agent import generate_image

# Test image generation
result = generate_image(
    description="A beautiful sunset over mountains",
    max_attempts=5
)
print(result)
```

## Environment Variables

The plugin looks for these environment variables:
- `COMFYUI_API_URL`: URL of the ComfyUI API (default: http://comfyui:8188)
- `COMFYUI_OUTPUT_DIR`: Directory for generated images (default: /app/data/outputs)
- `PLUGIN_CACHE_DIR`: Directory for plugin cache (default: /app/data/cache)

## Troubleshooting

1. **ComfyUI Connection Issues**
```bash
# Check ComfyUI logs
docker-compose logs comfyui

# Test ComfyUI connection
docker-compose exec open-webui curl http://comfyui:8188/history
```

2. **Plugin Import Issues**
```bash
# Check plugin installation
docker-compose exec open-webui ls -la /app/extensions/plugins/comfyui-agent

# Check Python path
docker-compose exec open-webui python3 -c "import sys; print(sys.path)"
```

3. **Permission Issues**
```bash
# Fix permissions if needed
docker-compose exec open-webui chown -R 1000:1000 /app/extensions/plugins/comfyui-agent
```

## Development Setup

For development, you can mount the plugin directory directly:

```yaml
services:
  open-webui:
    volumes:
      - ./comfyui-agent:/app/extensions/plugins/comfyui-agent
```

This allows you to edit the plugin files on your host machine and see changes immediately in the container.

## Plugin Updates

To update the plugin in a Docker environment:

1. **Using volumes:**
```bash
cd /path/to/open-webui/data/plugins/comfyui-agent
git pull
docker-compose restart open-webui
```

2. **Using custom image:**
```bash
cd custom-open-webui
git pull
docker-compose build
docker-compose up -d
```

## Security Notes

1. The plugin container needs access to:
   - ComfyUI API (port 8188)
   - GPU (for CUDA support)
   - Volume for image storage

2. Consider setting these permissions in production:
```yaml
services:
  open-webui:
    security_opt:
      - no-new-privileges:true
    read_only: true
    volumes:
      - ./data:/app/data:rw
```