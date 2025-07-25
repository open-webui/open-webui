#!/usr/bin/env python3
"""
Multi-client deployment script for mAI OpenRouter model filtering.
Manages deployment across multiple client instances on Hetzner Cloud infrastructure.
"""

import json
import os
import subprocess
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from model_filtering_config import (
    PRODUCTION_MODEL_CONFIG,
    get_model_config_json,
    validate_model_config
)

@dataclass
class ClientConfig:
    """Configuration for a single client instance."""
    name: str
    organization_name: str
    openrouter_api_key: str
    external_user_id: str
    port_offset: int = 0  # For port allocation (3000 + offset, 8080 + offset)
    server_ip: Optional[str] = None
    
    @property
    def frontend_port(self) -> int:
        return 3000 + self.port_offset
    
    @property 
    def backend_port(self) -> int:
        return 8080 + self.port_offset

class MultiClientDeployment:
    """Manages deployment across multiple client instances."""
    
    def __init__(self, config_file: str = "scripts/production/clients.yaml"):
        self.config_file = Path(config_file)
        self.base_dir = Path("/Users/patpil/Documents/Projects/mAI")
        self.clients = self._load_client_configs()
    
    def _load_client_configs(self) -> List[ClientConfig]:
        """Load client configurations from YAML file."""
        if not self.config_file.exists():
            print(f"⚠️  Client config file not found: {self.config_file}")
            return []
        
        try:
            with open(self.config_file, 'r') as f:
                data = yaml.safe_load(f)
            
            clients = []
            for client_data in data.get('clients', []):
                client = ClientConfig(**client_data)
                clients.append(client)
            
            print(f"✅ Loaded {len(clients)} client configurations")
            return clients
            
        except Exception as e:
            print(f"❌ Failed to load client configs: {e}")
            return []
    
    def generate_client_env(self, client: ClientConfig, output_dir: Path) -> bool:
        """Generate .env file for a specific client."""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            env_file = output_dir / ".env"
            
            # Read template
            template_file = self.base_dir / "scripts/production/env_template.env"
            with open(template_file, 'r') as f:
                content = f.read()
            
            # Replace placeholders
            content = content.replace("CLIENT_ORGANIZATION_NAME", client.organization_name)
            content = content.replace("YOUR_CLIENT_API_KEY_HERE", client.openrouter_api_key)
            content = content.replace("mai_client_UNIQUE_ID", client.external_user_id)
            content = content.replace("localhost:5173", f"localhost:{client.frontend_port}")
            content = content.replace("localhost:8080", f"localhost:{client.backend_port}")
            content = content.replace("$(date +%Y-%m-%d)", f"{datetime.now().strftime('%Y-%m-%d')}")
            
            # Write client-specific .env file
            with open(env_file, 'w') as f:
                f.write(content)
            
            print(f"✅ Generated .env for {client.name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to generate .env for {client.name}: {e}")
            return False
    
    def generate_client_compose(self, client: ClientConfig, output_dir: Path) -> bool:
        """Generate docker-compose file for a specific client."""
        try:
            # Read base compose file
            base_compose = self.base_dir / "docker-compose-customization.yaml"
            with open(base_compose, 'r') as f:
                compose_data = yaml.safe_load(f)
            
            # Update service name and ports
            service_name = f"mai-{client.name.lower().replace('_', '-')}"
            
            if 'services' in compose_data:
                # Get the main service (should be first one)
                main_service_key = list(compose_data['services'].keys())[0]
                service_config = compose_data['services'][main_service_key]
                
                # Update ports
                if 'ports' in service_config:
                    # Update port mapping to client-specific ports
                    new_ports = []
                    for port_mapping in service_config['ports']:
                        if isinstance(port_mapping, str):
                            if ":8080" in port_mapping:
                                new_ports.append(f"{client.backend_port}:8080")
                            elif ":3000" in port_mapping:
                                new_ports.append(f"{client.frontend_port}:3000")
                            else:
                                new_ports.append(port_mapping)
                        else:
                            new_ports.append(port_mapping)
                    service_config['ports'] = new_ports
                
                # Update container name
                service_config['container_name'] = service_name
                
                # Update the service key
                compose_data['services'] = {service_name: service_config}
            
            # Write client-specific compose file
            compose_file = output_dir / "docker-compose.yaml"
            with open(compose_file, 'w') as f:
                yaml.dump(compose_data, f, default_flow_style=False)
            
            print(f"✅ Generated docker-compose.yaml for {client.name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to generate docker-compose for {client.name}: {e}")
            return False
    
    def deploy_client(self, client: ClientConfig, dry_run: bool = False) -> bool:
        """Deploy configuration for a single client."""
        try:
            print(f"\n🚀 Deploying {client.name}...")
            print(f"   Organization: {client.organization_name}")
            print(f"   Ports: {client.frontend_port}, {client.backend_port}")
            
            if dry_run:
                print(f"   [DRY RUN] Would deploy {client.name}")
                return True
            
            # Create client deployment directory
            client_dir = self.base_dir / "deployments" / client.name
            client_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate configuration files
            if not self.generate_client_env(client, client_dir):
                return False
            
            if not self.generate_client_compose(client, client_dir):
                return False
            
            # Validate configuration
            config_json = get_model_config_json(compact=False)
            if not validate_model_config(json.loads(config_json)):
                print(f"❌ Configuration validation failed for {client.name}")
                return False
            
            print(f"✅ Successfully deployed configuration for {client.name}")
            print(f"   📁 Deployment files: {client_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Deployment failed for {client.name}: {e}")
            return False
    
    def deploy_all_clients(self, dry_run: bool = False, max_workers: int = 5) -> Dict[str, bool]:
        """Deploy configuration to all clients in parallel."""
        print("🌐 Starting multi-client deployment...")
        print(f"📊 Total clients: {len(self.clients)}")
        print(f"🔧 Model filtering: {len(PRODUCTION_MODEL_CONFIG['0']['model_ids'])} models")
        
        if dry_run:
            print("🧪 DRY RUN MODE - No actual deployment")
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit deployment tasks
            future_to_client = {
                executor.submit(self.deploy_client, client, dry_run): client.name
                for client in self.clients
            }
            
            # Collect results
            for future in as_completed(future_to_client):
                client_name = future_to_client[future]
                try:
                    success = future.result()
                    results[client_name] = success
                except Exception as e:
                    print(f"❌ Exception deploying {client_name}: {e}")
                    results[client_name] = False
        
        # Summary
        successful = sum(1 for success in results.values() if success)
        failed = len(results) - successful
        
        print(f"\n📋 Deployment Summary:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        
        if failed == 0:
            print("🎉 All client deployments completed successfully!")
        else:
            print("⚠️  Some deployments failed. Check logs above.")
            
        return results
    
    def validate_all_configs(self) -> bool:
        """Validate configurations for all clients."""
        print("🔍 Validating all client configurations...")
        
        all_valid = True
        for client in self.clients:
            print(f"\nValidating {client.name}:")
            
            # Check required fields
            if not client.organization_name:
                print(f"❌ Missing organization_name")
                all_valid = False
            
            if not client.openrouter_api_key or not client.openrouter_api_key.startswith('sk-or-v1-'):
                print(f"❌ Invalid OpenRouter API key format")
                all_valid = False
            
            if not client.external_user_id:
                print(f"❌ Missing external_user_id")
                all_valid = False
            
            # Check for port conflicts
            for other_client in self.clients:
                if other_client.name != client.name:
                    if (client.frontend_port == other_client.frontend_port or 
                        client.backend_port == other_client.backend_port):
                        print(f"❌ Port conflict with {other_client.name}")
                        all_valid = False
            
            if all_valid:
                print(f"✅ Configuration valid")
        
        return all_valid

def main():
    """Main deployment function."""
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(
        description="Multi-client deployment for mAI OpenRouter model filtering",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--deploy-all", action="store_true",
                       help="Deploy to all configured clients")
    parser.add_argument("--deploy-client", type=str,
                       help="Deploy to specific client by name")
    parser.add_argument("--validate", action="store_true",
                       help="Validate all client configurations")
    parser.add_argument("--dry-run", action="store_true",
                       help="Perform dry run without actual deployment")
    parser.add_argument("--max-workers", type=int, default=5,
                       help="Maximum parallel deployments")
    parser.add_argument("--config", type=str, default="scripts/production/clients.yaml",
                       help="Client configuration file")
    
    args = parser.parse_args()
    
    deployment = MultiClientDeployment(config_file=args.config)
    
    if args.validate:
        success = deployment.validate_all_configs()
        sys.exit(0 if success else 1)
    elif args.deploy_all:
        results = deployment.deploy_all_clients(
            dry_run=args.dry_run,
            max_workers=args.max_workers
        )
        failed_count = sum(1 for success in results.values() if not success)
        sys.exit(0 if failed_count == 0 else 1)
    elif args.deploy_client:
        client = next((c for c in deployment.clients if c.name == args.deploy_client), None)
        if client:
            success = deployment.deploy_client(client, dry_run=args.dry_run)
            sys.exit(0 if success else 1)
        else:
            print(f"❌ Client '{args.deploy_client}' not found")
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()