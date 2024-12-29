# ComfyUI Agent Plugin - Available Commands

This document lists all available commands and scripts for managing the ComfyUI Agent Plugin.

## Quick Start Commands

### Installation
```bash
# Standard installation
./run.sh --setup

# Docker installation
./run.sh --docker --setup
```

### Basic Usage
```bash
# Generate image (standard)
./run.sh "your image description"

# Generate image (Docker)
./run.sh --docker "your image description"

# Generate example images
./run.sh --examples
```

## Setup and Verification

### Environment Setup
```bash
# Switch to Docker environment
./switch_environment.sh docker

# Switch to standard environment
./switch_environment.sh standard

# Verify setup
./verify_setup.sh
```

### Installation Scripts
```bash
# Standard installation
./install.sh

# Development installation
./dev_install.sh

# Docker installation
./docker_test.sh
```

## Testing Commands

### Standard Tests
```bash
# Run all tests
./run_tests.sh

# Run plugin tests
./test_plugin.py

# Run CLIP scorer tests
./test_clip_scorer.py
```

### Docker Tests
```bash
# Run Docker environment tests
./docker_test.sh

# Run specific Docker tests
./test_docker.py
```

## Development Commands

### Package Management
```bash
# Create Docker package
./docker_package.sh

# Clean environment
./cleanup.sh
```

### Python Usage
```python
# Generate image
from comfyui_agent import generate_image
result = generate_image(
    description="A beautiful sunset over mountains",
    max_attempts=5
)

# Analyze image
from comfyui_agent import analyze_image
analysis = analyze_image(
    image_path=result["image_path"],
    description="A beautiful sunset over mountains"
)
```

## Environment Variables

### Standard Environment
```bash
export COMFYUI_API_URL=http://127.0.0.1:8188
export COMFYUI_OUTPUT_DIR=outputs
export PLUGIN_CACHE_DIR=cache
```

### Docker Environment
```bash
export COMFYUI_API_URL=http://comfyui:8188
export COMFYUI_OUTPUT_DIR=/app/data/outputs
export PLUGIN_CACHE_DIR=/app/data/cache
```

## Plugin Functions

### generate_image
Generate an image using ComfyUI with CLIP-guided refinement.
```python
result = generate_image(
    description="Image description",
    max_attempts=5,
    cfg_scale=7.0,
    steps=20,
    width=512,
    height=512
)
```

### analyze_image
Analyze how well an image matches a description using CLIP.
```python
result = analyze_image(
    image_path="/path/to/image.png",
    description="Image description"
)
```

## Docker Compose Commands

### Start Services
```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d open-webui
docker-compose up -d comfyui
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop specific service
docker-compose stop open-webui
docker-compose stop comfyui
```

### Logs and Debugging
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs open-webui
docker-compose logs comfyui

# Follow logs
docker-compose logs -f
```

### Container Management
```bash
# Rebuild containers
docker-compose build

# Restart services
docker-compose restart

# Check status
docker-compose ps
```

## File Locations

### Configuration Files
- `config.json` - Standard configuration
- `docker_config.json` - Docker configuration
- `.env` - Environment variables

### Output Directories
- `outputs/` - Generated images
- `cache/` - Plugin cache
- `example_images/` - Example generations

### Log Files
- `logs/plugin.log` - Plugin logs
- `logs/comfyui.log` - ComfyUI logs

## Support Commands

### Get Help
```bash
# Show command help
./run.sh --help

# Show Docker test help
./docker_test.sh --help

# Show plugin version
python3 -c "import comfyui_agent; print(comfyui_agent.__version__)"
```

### Troubleshooting
```bash
# Check ComfyUI status
curl http://localhost:8188/history

# Check GPU status
nvidia-smi

# Verify plugin installation
./verify_setup.sh

# Clean and reinstall
./cleanup.sh && ./install.sh
```

For more detailed information, refer to:
- [README.md](README.md) - Main documentation
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [DOCKER_SETUP.md](DOCKER_SETUP.md) - Docker setup guide
- [INSTALL.md](INSTALL.md) - Installation troubleshooting