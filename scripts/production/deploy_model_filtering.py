#!/usr/bin/env python3
"""
Production deployment script for mAI OpenRouter model filtering.
Manages deployment across multiple client instances with proper validation and rollback.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from model_filtering_config import (
    PRODUCTION_MODEL_CONFIG,
    get_model_config_json,
    validate_model_config,
    get_expected_models
)

class ProductionDeployment:
    """Manages production deployment of model filtering configuration."""
    
    def __init__(self, base_dir: str = "/Users/patpil/Documents/Projects/mAI"):
        self.base_dir = Path(base_dir)
        self.env_file = self.base_dir / ".env"
        self.compose_file = self.base_dir / "docker-compose-customization.yaml"
        self.backup_dir = self.base_dir / "backups" / "model-filtering"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def create_backup(self) -> str:
        """Create backup of current configuration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(exist_ok=True)
        
        # Backup .env file
        if self.env_file.exists():
            shutil.copy2(self.env_file, backup_path / ".env")
            
        # Backup docker-compose file
        if self.compose_file.exists():
            shutil.copy2(self.compose_file, backup_path / "docker-compose-customization.yaml")
            
        # Backup database if exists
        db_file = self.base_dir / "backend" / "data" / "webui.db"
        if db_file.exists():
            shutil.copy2(db_file, backup_path / "webui.db")
            
        print(f"✅ Backup created: {backup_path}")
        return str(backup_path)
    
    def update_env_file(self) -> bool:
        """Update .env file with model filtering configuration."""
        try:
            # Read current .env file
            env_content = []
            if self.env_file.exists():
                with open(self.env_file, 'r') as f:
                    env_content = f.readlines()
            
            # Remove existing OPENAI_API_CONFIGS line if present
            env_content = [line for line in env_content 
                          if not line.strip().startswith('OPENAI_API_CONFIGS=')]
            
            # Add new configuration
            config_json = get_model_config_json(compact=True)
            new_line = f"OPENAI_API_CONFIGS='{config_json}'\n"
            
            # Find the right place to insert (after OpenRouter configuration)
            insert_index = len(env_content)
            for i, line in enumerate(env_content):
                if line.strip().startswith('# OpenRouter Model Filtering') or \
                   line.strip().startswith('# CORS and Networking'):
                    insert_index = i
                    break
            
            # Insert the configuration
            if insert_index < len(env_content) and not env_content[insert_index].strip().startswith('# OpenRouter Model Filtering'):
                env_content.insert(insert_index, "# OpenRouter Model Filtering (12 specific models)\n")
                env_content.insert(insert_index + 1, new_line)
                env_content.insert(insert_index + 2, "\n")
            else:
                env_content.append("# OpenRouter Model Filtering (12 specific models)\n")
                env_content.append(new_line)
                env_content.append("\n")
            
            # Write updated .env file
            with open(self.env_file, 'w') as f:
                f.writelines(env_content)
            
            print("✅ Updated .env file with model filtering configuration")
            return True
            
        except Exception as e:
            print(f"❌ Failed to update .env file: {e}")
            return False
    
    def validate_docker_compose(self) -> bool:
        """Validate docker-compose configuration."""
        try:
            result = subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "config"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ Docker Compose configuration is valid")
                return True
            else:
                print(f"❌ Docker Compose validation failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Docker Compose validation timed out")
            return False
        except Exception as e:
            print(f"❌ Docker Compose validation error: {e}")
            return False
    
    def build_and_deploy(self) -> bool:
        """Build and deploy the updated configuration."""
        try:
            print("🔄 Building Docker image with updated configuration...")
            
            # Stop current containers
            result = subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "down"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print(f"⚠️  Warning: Failed to stop containers: {result.stderr}")
            
            # Build new image
            result = subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "build", "--no-cache"],
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout for build
            )
            
            if result.returncode != 0:
                print(f"❌ Docker build failed: {result.stderr}")
                return False
            
            # Start containers
            result = subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "up", "-d"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                print(f"❌ Failed to start containers: {result.stderr}")
                return False
            
            print("✅ Docker containers rebuilt and started successfully")
            return True
            
        except subprocess.TimeoutExpired:
            print("❌ Docker build/deploy timed out")
            return False
        except Exception as e:
            print(f"❌ Docker build/deploy error: {e}")
            return False
    
    def verify_deployment(self) -> bool:
        """Verify that the deployment is working correctly."""
        try:
            print("🔍 Verifying deployment...")
            
            # Wait for container to be ready
            time.sleep(10)
            
            # Check if container is running
            result = subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "ps"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if "Up" not in result.stdout:
                print("❌ Container is not running")
                return False
            
            # Check logs for configuration loading
            result = subprocess.run(
                ["docker-compose", "-f", str(self.compose_file), "logs", "--tail=50"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            logs = result.stdout
            
            # Verify configuration is loaded
            if "Number of API configs: 1" not in logs:
                print("❌ Model filtering configuration not loaded")
                return False
            
            # Check for model_ids in logs
            expected_models = get_expected_models()
            models_found = 0
            for model in expected_models[:3]:  # Check first 3 models
                if model in logs:
                    models_found += 1
            
            if models_found < 2:
                print("❌ Expected models not found in configuration logs")
                return False
            
            print("✅ Deployment verification successful")
            print(f"✅ Configuration loaded with {len(expected_models)} models")
            return True
            
        except Exception as e:
            print(f"❌ Deployment verification failed: {e}")
            return False
    
    def rollback(self, backup_path: str) -> bool:
        """Rollback to previous configuration."""
        try:
            print(f"🔄 Rolling back to backup: {backup_path}")
            backup_dir = Path(backup_path)
            
            # Restore .env file
            backup_env = backup_dir / ".env"
            if backup_env.exists():
                shutil.copy2(backup_env, self.env_file)
            
            # Restore docker-compose file
            backup_compose = backup_dir / "docker-compose-customization.yaml"
            if backup_compose.exists():
                shutil.copy2(backup_compose, self.compose_file)
            
            # Rebuild and restart
            return self.build_and_deploy()
            
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return False
    
    def deploy(self) -> bool:
        """Execute full production deployment."""
        print("🚀 Starting production deployment of model filtering...")
        print("=" * 60)
        
        # Create backup
        backup_path = self.create_backup()
        
        try:
            # Validate configuration
            if not validate_model_config(PRODUCTION_MODEL_CONFIG):
                print("❌ Configuration validation failed")
                return False
            
            # Update .env file
            if not self.update_env_file():
                print("❌ Failed to update .env file")
                return False
            
            # Validate docker-compose
            if not self.validate_docker_compose():
                print("❌ Docker Compose validation failed")
                return False
            
            # Build and deploy
            if not self.build_and_deploy():
                print("❌ Build and deploy failed")
                print(f"🔄 Attempting rollback to: {backup_path}")
                self.rollback(backup_path)
                return False
            
            # Verify deployment
            if not self.verify_deployment():
                print("❌ Deployment verification failed")
                print(f"🔄 Attempting rollback to: {backup_path}")
                self.rollback(backup_path)
                return False
            
            print("\n🎉 Production deployment completed successfully!")
            print(f"📦 Backup available at: {backup_path}")
            print(f"🎯 {len(get_expected_models())} models now filtered and active")
            return True
            
        except Exception as e:
            print(f"❌ Deployment failed with error: {e}")
            print(f"🔄 Attempting rollback to: {backup_path}")
            self.rollback(backup_path)
            return False

def main():
    """Main deployment function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Production deployment for mAI OpenRouter model filtering",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--deploy", action="store_true",
                       help="Execute full production deployment")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only validate configuration without deploying")
    parser.add_argument("--backup-only", action="store_true",
                       help="Only create backup without deploying")
    parser.add_argument("--verify-only", action="store_true",
                       help="Only verify current deployment")
    
    args = parser.parse_args()
    
    deployment = ProductionDeployment()
    
    if args.validate_only:
        success = validate_model_config(PRODUCTION_MODEL_CONFIG)
        sys.exit(0 if success else 1)
    elif args.backup_only:
        deployment.create_backup()
    elif args.verify_only:
        success = deployment.verify_deployment()
        sys.exit(0 if success else 1)
    elif args.deploy:
        success = deployment.deploy()
        sys.exit(0 if success else 1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()