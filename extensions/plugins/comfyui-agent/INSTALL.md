# ComfyUI Agent Plugin Installation Guide

This guide will help you install and verify the ComfyUI Agent Plugin for Open WebUI.

## Prerequisites Checklist

### Standard Installation
- [ ] Python 3.8 or higher installed
- [ ] ComfyUI installed and running
- [ ] Open WebUI installed
- [ ] CUDA-capable GPU (recommended)
- [ ] Git installed

### Docker Installation
- [ ] Docker installed
- [ ] Docker Compose installed
- [ ] NVIDIA Container Toolkit installed (for GPU support)
- [ ] Open WebUI Docker container running
- [ ] ComfyUI Docker container running

## Installation Steps

### Option 1: Standard Installation

1. Clone the repository:
```bash
cd /path/to/open-webui/extensions
git clone https://github.com/yourusername/comfyui-agent.git
cd comfyui-agent
```

2. Run installation script:
```bash
./install.sh
```

3. Verify installation:
```bash
./test_plugin.py
```

### Option 2: Docker Installation

1. Clone the repository:
```bash
cd /path/to/open-webui/extensions
git clone https://github.com/yourusername/comfyui-agent.git
cd comfyui-agent
```

2. Switch to Docker environment:
```bash
./switch_environment.sh docker
```

3. Update docker-compose.yml:
```yaml
services:
  open-webui:
    volumes:
      - ./extensions/comfyui-agent:/app/extensions/plugins/comfyui-agent
    environment:
      - COMFYUI_API_URL=http://comfyui:8188

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

4. Restart containers:
```bash
docker-compose down
docker-compose up -d
```

5. Verify Docker installation:
```bash
./docker_test.sh
```

## Verification Steps

### 1. Check Dependencies
```bash
# Standard installation
pip list | grep -E "torch|transformers|Pillow"

# Docker installation
docker exec open-webui pip list | grep -E "torch|transformers|Pillow"
```

### 2. Check ComfyUI Connection
```bash
# Standard installation
curl http://127.0.0.1:8188/history

# Docker installation
curl http://localhost:8188/history
```

### 3. Test Image Generation
```python
from comfyui_agent import generate_image

result = generate_image(
    description="A test image of a red circle on white background",
    max_attempts=1
)
print(result)
```

### 4. Test CLIP Analysis
```python
from comfyui_agent import analyze_image

analysis = analyze_image(
    image_path=result["image_path"],
    description="A red circle on white background"
)
print(analysis)
```

## Common Issues

### 1. ComfyUI Connection Failed
- Check if ComfyUI is running
- Verify API URL configuration
- Check network connectivity

### 2. GPU Not Detected
- Verify NVIDIA drivers installed
- Check CUDA installation
- For Docker: verify NVIDIA Container Toolkit

### 3. Import Errors
- Verify Python path
- Check all dependencies installed
- For Docker: verify volume mounts

### 4. Permission Issues
- Check directory permissions
- For Docker: verify user permissions
- Check file ownership

## Environment Variables

### Standard Installation
```bash
export COMFYUI_API_URL=http://127.0.0.1:8188
export COMFYUI_OUTPUT_DIR=/path/to/outputs
export PLUGIN_CACHE_DIR=/path/to/cache
```

### Docker Installation
```bash
export COMFYUI_API_URL=http://comfyui:8188
export COMFYUI_OUTPUT_DIR=/app/data/outputs
export PLUGIN_CACHE_DIR=/app/data/cache
```

## Support

If you encounter any issues:
1. Run verification script:
   ```bash
   ./verify_installation.py
   ```
2. Check logs:
   ```bash
   cat logs/plugin.log
   ```
3. Open an issue on GitHub with the verification output

## Next Steps

After successful installation:
1. Try generating example images:
   ```bash
   ./run.sh --examples
   ```
2. Read the documentation:
   - [README.md](README.md) - Overview
   - [QUICKSTART.md](QUICKSTART.md) - Quick start guide
   - [DOCKER_SETUP.md](DOCKER_SETUP.md) - Docker guide
3. Explore the API in Python:
   ```python
   import comfyui_agent
   help(comfyui_agent)
   ```