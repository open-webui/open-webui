# ComfyUI Agent Plugin Files

## Core Files
- `comfyui_agent/__init__.py` - Plugin initialization
- `comfyui_agent/plugin.py` - Main plugin functionality
- `comfyui_agent/config.json` - Standard configuration
- `comfyui_agent/docker_config.json` - Docker configuration
- `comfyui_agent/manifest.json` - Plugin manifest

## Docker Support
- `comfyui_agent/docker_init.py` - Docker initialization
- `comfyui_agent/docker_test.py` - Docker environment tests
- `comfyui_agent/docker_test.sh` - Docker test script
- `comfyui_agent/docker_package.sh` - Docker packaging script
- `comfyui_agent/switch_environment.sh` - Environment switcher

## Testing
- `comfyui_agent/test_plugin.py` - Standard environment tests
- `comfyui_agent/test_docker.py` - Docker-specific tests
- `comfyui_agent/run_tests.sh` - Test runner script

## Documentation
- `README.md` - Main documentation
- `QUICKSTART.md` - Quick start guide
- `DOCKER_SETUP.md` - Docker setup guide
- `comfyui_agent/README.md` - Plugin-specific documentation

## Installation
- `comfyui_agent/requirements.txt` - Python dependencies
- `comfyui_agent/setup.py` - Installation script
- `comfyui_agent/install.sh` - Installation script
- `comfyui_agent/dev_install.sh` - Development installation

## Required Directories
- `outputs/` - Generated images
- `cache/` - Plugin cache
- `example_images/` - Example generations
