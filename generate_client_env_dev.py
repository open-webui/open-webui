#!/usr/bin/env python3
"""
generate_client_env_dev.py

Development variant of generate_client_env.py that creates .env.dev file
for development Docker instance with separate API key and database.

Usage:
    python generate_client_env_dev.py
    python generate_client_env_dev.py --production  # Also init dev database

This creates .env.dev instead of .env to avoid conflicts.
"""

import os
import sys
import subprocess

# Import the main generator class
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_client_env import OpenRouterEnvGenerator

class DevOpenRouterEnvGenerator(OpenRouterEnvGenerator):
    """Development variant that outputs to .env.dev"""
    
    def __init__(self, init_database: bool = False):
        super().__init__(init_database)
        # Override database path for dev environment
        self.database_path = "backend/data/webui.db"  # Will use dev volume
        
    def generate_env_file(self) -> bool:
        """Generate .env.dev file instead of .env"""
        print(f"\n📄 Generating .env.dev file for development...")
        
        try:
            # Read existing environment variables from .env.example
            existing_vars = self.read_existing_env()
            
            # Our new OpenRouter configuration with DEV prefix
            openrouter_vars = {
                'OPENROUTER_API_KEY': self.generated_api_key,
                'OPENROUTER_HOST': "https://openrouter.ai/api/v1",
                'OPENROUTER_EXTERNAL_USER': f"dev_{self.external_user}",  # Prefix with dev_
                'ORGANIZATION_NAME': f"{self.organization_name} (DEV)",
                'SPENDING_LIMIT': self.spending_limit,
            }
            
            # Merge configurations
            merged_vars = {**existing_vars, **openrouter_vars}
            
            # Generate the complete .env.dev content
            from datetime import datetime
            env_content = f"""# mAI Development Environment Configuration
# Generated on: {datetime.now().isoformat()}
# Organization: {self.organization_name} (DEV)
# Spending Limit: {self.spending_limit}

# =============================================================================
# OpenRouter Configuration (Development Environment)
# =============================================================================
OPENROUTER_API_KEY={self.generated_api_key}
OPENROUTER_HOST=https://openrouter.ai/api/v1
OPENROUTER_EXTERNAL_USER=dev_{self.external_user}

# Organization Configuration  
ORGANIZATION_NAME={self.organization_name} (DEV)
SPENDING_LIMIT={self.spending_limit}

# =============================================================================
# mAI Application Configuration (Development)
# =============================================================================
"""
            
            # Add existing variables
            for key, value in merged_vars.items():
                if key.startswith('OPENROUTER_') or key in ['ORGANIZATION_NAME', 'SPENDING_LIMIT']:
                    continue  # Already added above
                elif key in ['WEBUI_SECRET_KEY', 'WEBUI_URL', 'WEBUI_NAME']:
                    continue  # These are set in docker-compose.dev.yml
                else:
                    env_content += f"{key}={value}\n"
            
            # Write to .env.dev file
            with open('.env.dev', 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            print("✅ .env.dev file generated successfully!")
            print(f"📁 Location: {os.path.abspath('.env.dev')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error generating .env.dev file: {e}")
            return False
    
    def show_integration_guidance(self):
        """Show guidance for development environment"""
        print(f"\n🚀 Development Environment Setup")
        print("=" * 50)
        print("Your .env.dev file has been generated for development use.")
        print()
        
        print("📋 Next Steps:")
        print("1. Start the development container:")
        print("   docker-compose -f docker-compose.dev.yml up -d")
        print()
        print("2. Access development instance at:")
        print("   http://localhost:3001")
        print()
        print("3. First user to register becomes admin")
        print()
        
        print("🔧 Development Features:")
        print("   ✅ Hot-reloading enabled (instant code changes)")
        print("   ✅ Separate database (mai_dev_data volume)")
        print("   ✅ Separate API key from production")
        print("   ✅ External user prefixed with 'dev_'")
        print("   ✅ Duplicate prevention system included")
        print("   ✅ Safe for testing without affecting production data")
        print()
        
        print("⚠️  Important:")
        print("   - This is completely separate from production")
        print("   - Changes to code are reflected instantly")
        print("   - Database is isolated from production")
        print("   - Safe for testing and experimentation")
        print()
        
        print("✅ Configuration Summary:")
        print(f"   📋 Organization: {self.organization_name} (DEV)")
        print(f"   💰 Spending Limit: {self.spending_limit}")
        print(f"   🔑 API Key: {self.generated_api_key[:20]}...")
        print(f"   👤 External User: dev_{self.external_user}")
        print(f"   🌐 OpenRouter Host: https://openrouter.ai/api/v1")

def main():
    """Main script execution"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate .env.dev configuration for mAI development Docker instance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This creates .env.dev for development use, keeping it separate from production .env

Examples:
  python generate_client_env_dev.py              # Generate dev environment only
  python generate_client_env_dev.py --production # Also initialize dev database
        """
    )
    
    parser.add_argument(
        '--production', '--prod',
        action='store_true',
        help='Also initialize database for development environment'
    )
    
    args = parser.parse_args()
    
    generator = DevOpenRouterEnvGenerator(init_database=args.production)
    
    print("🔧 mAI Development Environment Generator")
    print("=" * 50)
    print("This will create a SEPARATE development environment")
    print("with its own API key and database.")
    print()
    
    try:
        # Run the generation process
        if not generator.get_user_input():
            return 1
            
        if not generator.validate_provisioning_key():
            return 1
            
        if not generator.create_api_key():
            return 1
            
        if not generator.test_api_key_and_get_external_user():
            return 1
            
        if not generator.generate_env_file():
            return 1
            
        if args.production and generator.init_database:
            print("\n⚠️  Note: Database initialization in dev uses the dev volume")
            print("   The database will be created when you start the container")
        
        generator.show_integration_guidance()
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n❌ Process interrupted by user.")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())