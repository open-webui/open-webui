#!/usr/bin/env python3
"""
Docker initialization script for ComfyUI Agent Plugin.
This script handles Docker-specific setup and configuration.
"""

import os
import sys
import json
import shutil
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('comfyui_agent_docker')

class DockerEnvironment:
    def __init__(self):
        self.config = self._load_config()
        self.env_vars = self._load_environment_variables()
        
    def _load_config(self):
        """Load Docker configuration"""
        config_path = Path(__file__).parent / "docker_config.json"
        try:
            with open(config_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading Docker config: {e}")
            return {}
            
    def _load_environment_variables(self):
        """Load environment variables with defaults from config"""
        env_vars = {}
        
        # Load from config defaults
        if 'docker' in self.config and 'environment_variables' in self.config['docker']:
            for var, desc in self.config['docker']['environment_variables'].items():
                env_vars[var] = os.getenv(var, self.config['docker'].get(var.lower()))
        
        return env_vars
        
    def setup_directories(self):
        """Create and verify required directories"""
        directories = {
            'outputs': self.env_vars.get('COMFYUI_OUTPUT_DIR', '/app/data/outputs'),
            'cache': self.env_vars.get('PLUGIN_CACHE_DIR', '/app/data/cache'),
            'models': self.env_vars.get('COMFYUI_MODEL_DIR', '/app/comfyui/models'),
            'logs': '/app/data/logs'
        }
        
        for name, path in directories.items():
            try:
                Path(path).mkdir(parents=True, exist_ok=True)
                logger.info(f"Created/verified directory: {path}")
            except Exception as e:
                logger.error(f"Error creating directory {path}: {e}")
                
    def verify_permissions(self):
        """Verify and fix permissions if needed"""
        paths = [
            self.env_vars.get('COMFYUI_OUTPUT_DIR', '/app/data/outputs'),
            self.env_vars.get('PLUGIN_CACHE_DIR', '/app/data/cache'),
            '/app/extensions/plugins/comfyui-agent'
        ]
        
        for path in paths:
            try:
                if os.path.exists(path):
                    # Fix permissions (assuming UID 1000 is the Open WebUI user)
                    os.system(f"chown -R 1000:1000 {path}")
                    os.system(f"chmod -R 755 {path}")
                    logger.info(f"Fixed permissions for: {path}")
            except Exception as e:
                logger.error(f"Error fixing permissions for {path}: {e}")
                
    def verify_gpu(self):
        """Verify GPU availability in Docker"""
        try:
            import torch
            if torch.cuda.is_available():
                device_name = torch.cuda.get_device_name(0)
                logger.info(f"GPU available: {device_name}")
                return True
            else:
                logger.warning("No GPU available, will use CPU")
                return False
        except Exception as e:
            logger.error(f"Error checking GPU: {e}")
            return False
            
    def verify_comfyui(self):
        """Verify ComfyUI connection"""
        import requests
        url = self.env_vars.get('COMFYUI_API_URL', 'http://comfyui:8188')
        
        try:
            response = requests.get(f"{url}/history")
            if response.status_code == 200:
                logger.info("ComfyUI connection successful")
                return True
            else:
                logger.error(f"ComfyUI returned status code: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error connecting to ComfyUI: {e}")
            return False
            
    def initialize(self):
        """Run all initialization steps"""
        logger.info("Starting Docker environment initialization...")
        
        # Setup directories
        self.setup_directories()
        
        # Fix permissions
        self.verify_permissions()
        
        # Check GPU
        has_gpu = self.verify_gpu()
        
        # Check ComfyUI
        has_comfyui = self.verify_comfyui()
        
        # Return status
        return {
            'success': has_comfyui,
            'gpu_available': has_gpu,
            'environment': self.env_vars,
            'directories': {
                'outputs': self.env_vars.get('COMFYUI_OUTPUT_DIR'),
                'cache': self.env_vars.get('PLUGIN_CACHE_DIR'),
                'models': self.env_vars.get('COMFYUI_MODEL_DIR')
            }
        }

def initialize_docker():
    """Initialize Docker environment"""
    env = DockerEnvironment()
    return env.initialize()

if __name__ == "__main__":
    # When run directly, perform initialization and exit with status
    result = initialize_docker()
    if result['success']:
        logger.info("Docker initialization successful")
        sys.exit(0)
    else:
        logger.error("Docker initialization failed")
        sys.exit(1)