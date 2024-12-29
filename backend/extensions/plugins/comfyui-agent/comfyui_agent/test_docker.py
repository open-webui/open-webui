#!/usr/bin/env python3
"""
Docker-specific test script for ComfyUI Agent Plugin.
This script verifies the plugin works correctly in a Docker environment.
"""

import os
import sys
import json
import logging
import requests
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('comfyui_agent_docker_test')

class DockerTester:
    def __init__(self):
        self.tests = [
            self.test_docker_environment,
            self.test_directories,
            self.test_permissions,
            self.test_comfyui_connection,
            self.test_plugin_import,
            self.test_gpu,
            self.test_model_access
        ]
        
    def test_docker_environment(self):
        """Verify we're running in Docker"""
        logger.info("Testing Docker environment...")
        
        if not os.path.exists('/.dockerenv'):
            logger.error("Not running in Docker container")
            return False
            
        logger.info("✓ Running in Docker container")
        
        # Check environment variables
        required_vars = ['COMFYUI_API_URL', 'COMFYUI_OUTPUT_DIR', 'PLUGIN_CACHE_DIR']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
            logger.warning("Using default values")
        
        return True
        
    def test_directories(self):
        """Test required directories exist and are writable"""
        logger.info("Testing directories...")
        
        directories = {
            'outputs': os.getenv('COMFYUI_OUTPUT_DIR', '/app/data/outputs'),
            'cache': os.getenv('PLUGIN_CACHE_DIR', '/app/data/cache'),
            'models': os.getenv('COMFYUI_MODEL_DIR', '/app/comfyui/models'),
            'plugins': '/app/extensions/plugins'
        }
        
        success = True
        for name, path in directories.items():
            if not os.path.exists(path):
                logger.error(f"Directory not found: {path}")
                success = False
                continue
                
            # Test write permission
            test_file = os.path.join(path, '.test_write')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                logger.info(f"✓ Directory {name} exists and is writable: {path}")
            except Exception as e:
                logger.error(f"Cannot write to {path}: {e}")
                success = False
                
        return success
        
    def test_permissions(self):
        """Test file permissions"""
        logger.info("Testing permissions...")
        
        # Check plugin directory permissions
        plugin_dir = '/app/extensions/plugins/comfyui-agent'
        if not os.path.exists(plugin_dir):
            logger.error(f"Plugin directory not found: {plugin_dir}")
            return False
            
        # Check ownership (should be UID 1000 for Open WebUI)
        stat = os.stat(plugin_dir)
        if stat.st_uid != 1000:
            logger.warning(f"Plugin directory not owned by Open WebUI user (UID 1000)")
            
        logger.info("✓ Plugin directory permissions verified")
        return True
        
    def test_comfyui_connection(self):
        """Test connection to ComfyUI"""
        logger.info("Testing ComfyUI connection...")
        
        url = os.getenv('COMFYUI_API_URL', 'http://comfyui:8188')
        try:
            response = requests.get(f"{url}/history")
            if response.status_code == 200:
                logger.info(f"✓ ComfyUI accessible at {url}")
                return True
            else:
                logger.error(f"ComfyUI returned status code {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Cannot connect to ComfyUI: {e}")
            return False
            
    def test_plugin_import(self):
        """Test plugin import"""
        logger.info("Testing plugin import...")
        
        try:
            sys.path.append('/app/extensions/plugins')
            import comfyui_agent
            from comfyui_agent import generate_image, analyze_image
            logger.info("✓ Plugin imported successfully")
            return True
        except Exception as e:
            logger.error(f"Plugin import failed: {e}")
            return False
            
    def test_gpu(self):
        """Test GPU availability"""
        logger.info("Testing GPU...")
        
        try:
            import torch
            if torch.cuda.is_available():
                device_name = torch.cuda.get_device_name(0)
                logger.info(f"✓ GPU available: {device_name}")
                return True
            else:
                logger.warning("No GPU available, will use CPU")
                return True
        except Exception as e:
            logger.error(f"Error checking GPU: {e}")
            return False
            
    def test_model_access(self):
        """Test access to model files"""
        logger.info("Testing model access...")
        
        model_dir = os.getenv('COMFYUI_MODEL_DIR', '/app/comfyui/models')
        if not os.path.exists(model_dir):
            logger.error(f"Model directory not found: {model_dir}")
            return False
            
        # Check for at least one model file
        model_files = list(Path(model_dir).glob('*.ckpt')) + list(Path(model_dir).glob('*.safetensors'))
        if not model_files:
            logger.warning("No model files found")
            return False
            
        logger.info(f"✓ Found {len(model_files)} model files")
        return True
        
    def run_all_tests(self):
        """Run all tests"""
        logger.info("Starting Docker environment tests...")
        print("-" * 50)
        
        results = []
        for test in self.tests:
            try:
                result = test()
                results.append((test.__name__, result))
            except Exception as e:
                logger.error(f"Test {test.__name__} failed with error: {e}")
                results.append((test.__name__, False))
                
        # Print summary
        print("\nTest Summary:")
        print("-" * 50)
        passed = sum(1 for _, r in results if r)
        total = len(results)
        
        for name, result in results:
            status = "✓" if result else "✗"
            print(f"{status} {name}")
            
        print(f"\nPassed: {passed}/{total} tests")
        
        if passed == total:
            print("\n✓ Docker environment is properly configured!")
        else:
            print("\n✗ Some tests failed. Please check the logs and fix the issues.")
            
        return passed == total

def main():
    tester = DockerTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()