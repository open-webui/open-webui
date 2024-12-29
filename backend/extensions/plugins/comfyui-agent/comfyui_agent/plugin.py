"""
Plugin initialization for Open WebUI.
This script is called when the plugin is loaded by Open WebUI.
Supports both Docker and non-Docker environments.
"""

import os
import sys
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('comfyui_agent')

def is_docker() -> bool:
    """Check if running in a Docker container"""
    return os.path.exists('/.dockerenv')

def load_config(config_type: str = 'default') -> Dict[str, Any]:
    """Load configuration based on environment"""
    config_dir = Path(__file__).parent
    
    if config_type == 'docker':
        config_path = config_dir / 'docker_config.json'
    else:
        config_path = config_dir / 'config.json'
        
    try:
        with open(config_path) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {config_type} config: {e}")
        return {}

def setup_environment() -> Dict[str, Any]:
    """Setup environment based on context (Docker/non-Docker)"""
    if is_docker():
        logger.info("Docker environment detected")
        try:
            from . import docker_init
            return docker_init.initialize_docker()
        except Exception as e:
            logger.error(f"Docker initialization failed: {e}")
            return {'success': False, 'error': str(e)}
    else:
        logger.info("Standard environment detected")
        return setup_standard_environment()

def setup_standard_environment() -> Dict[str, Any]:
    """Setup standard (non-Docker) environment"""
    config = load_config('default')
    
    # Create required directories
    directories = {
        'outputs': config.get('paths', {}).get('outputs', 'outputs'),
        'cache': config.get('paths', {}).get('cache', 'cache'),
        'logs': config.get('paths', {}).get('logs', 'logs')
    }
    
    for name, path in directories.items():
        Path(path).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created/verified directory: {path}")
    
    return {
        'success': True,
        'environment': 'standard',
        'directories': directories
    }

class ComfyUIAgentPlugin:
    def __init__(self):
        self.name = "comfyui-agent"
        self.env = setup_environment()
        self.config = load_config('docker' if is_docker() else 'default')
        self._ensure_initialized()
        
    def _ensure_initialized(self):
        """Ensure plugin is properly initialized"""
        if not self.env['success']:
            logger.error("Plugin initialization failed")
            if 'error' in self.env:
                logger.error(f"Error: {self.env['error']}")
            return False
            
        # Set up API URL based on environment
        if is_docker():
            self.api_url = os.getenv('COMFYUI_API_URL', 'http://comfyui:8188')
        else:
            self.api_url = os.getenv('COMFYUI_API_URL', 'http://127.0.0.1:8188')
            
        return True
        
    def initialize(self) -> bool:
        """Initialize the plugin"""
        try:
            # Import core functionality
            from . import generate_image, analyze_image
            
            # Verify ComfyUI connection
            import requests
            response = requests.get(f"{self.api_url}/history")
            if response.status_code != 200:
                logger.warning(f"ComfyUI not accessible at {self.api_url}")
                logger.warning("Plugin will be available but may not function until ComfyUI is running")
                
            # Register functions with Open WebUI
            return True
            
        except Exception as e:
            logger.error(f"Error initializing plugin: {e}")
            return False
            
    def get_functions(self) -> Dict[str, Dict[str, Any]]:
        """Return available functions for LLM"""
        return {
            "generate_image": {
                "name": "generate_image",
                "description": "Generate an image using ComfyUI with CLIP-guided refinement",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Detailed description of the image to generate"
                        },
                        "max_attempts": {
                            "type": "integer",
                            "description": "Maximum number of generation attempts",
                            "default": 5
                        },
                        "cfg_scale": {
                            "type": "number",
                            "description": "Initial CFG scale",
                            "default": 7.0
                        },
                        "steps": {
                            "type": "integer",
                            "description": "Initial number of steps",
                            "default": 20
                        },
                        "width": {
                            "type": "integer",
                            "description": "Image width",
                            "default": 512
                        },
                        "height": {
                            "type": "integer",
                            "description": "Image height",
                            "default": 512
                        }
                    },
                    "required": ["description"]
                }
            },
            "analyze_image": {
                "name": "analyze_image",
                "description": "Analyze how well an image matches a description using CLIP",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "Path to the image file to analyze"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description to compare the image against"
                        }
                    },
                    "required": ["image_path", "description"]
                }
            }
        }
        
    def get_examples(self) -> list:
        """Return example conversations"""
        return [
            {
                "role": "user",
                "content": "Generate an image of a beautiful sunset over mountains."
            },
            {
                "role": "assistant",
                "content": "I'll help you generate that image using ComfyUI.",
                "function_call": {
                    "name": "generate_image",
                    "parameters": {
                        "description": "A beautiful sunset over mountains with warm golden light, majestic peaks, and a peaceful atmosphere",
                        "max_attempts": 5
                    }
                }
            }
        ]
        
    def cleanup(self):
        """Clean up resources when plugin is unloaded"""
        logger.info("Cleaning up ComfyUI Agent Plugin...")
        try:
            # Clean up any temporary files
            cache_dir = self.env['directories'].get('cache')
            if cache_dir and os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                logger.info(f"Cleaned up cache directory: {cache_dir}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Create plugin instance
plugin = ComfyUIAgentPlugin()

# Export functions
from . import generate_image, analyze_image

__all__ = ['plugin', 'generate_image', 'analyze_image']
