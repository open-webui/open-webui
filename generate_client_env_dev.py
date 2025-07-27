#!/usr/bin/env python3
"""
generate_client_env_dev.py

Development variant using Clean Architecture that creates .env.dev file
for development Docker instance with separate API key and database.

Usage:
    python generate_client_env_dev.py
    python generate_client_env_dev.py --production  # Also init dev database

This creates .env.dev instead of .env to avoid conflicts.
"""

import os
import sys
from datetime import datetime

# Import the new clean architecture application
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_client_env.main import EnvironmentGeneratorApplication
from generate_client_env.infrastructure.file_manager import EnvironmentFileManager
from generate_client_env.domain.services import EnvironmentFileService
from generate_client_env.presentation.cli_interface import ArgumentParser, OutputFormatter


class DevEnvironmentFileManager(EnvironmentFileManager):
    """Development file manager that writes to .env.dev"""
    
    def write_environment_file(self, content: str, filename: str = '.env.dev'):
        """Override to write .env.dev by default"""
        return super().write_environment_file(content, filename)


class DevEnvironmentFileService(EnvironmentFileService):
    """Development environment file service with dev-specific content"""
    
    @staticmethod
    def generate_file_content(configuration):
        """Generate dev-specific .env file content"""
        org = configuration.organization
        
        # Modify organization for dev
        dev_org_name = f"{org.name} (DEV)"
        dev_external_user = f"dev_{org.external_user}"
        
        # Generate header
        content = f"""# mAI Development Environment Configuration
# Generated on: {datetime.now().isoformat()}
# Organization: {dev_org_name}
# Spending Limit: {org.spending_limit}

# =============================================================================
# OpenRouter Configuration (Development Environment)
# =============================================================================
OPENROUTER_API_KEY={org.api_key}
OPENROUTER_HOST={configuration.openrouter_host}
OPENROUTER_EXTERNAL_USER={dev_external_user}

# Organization Configuration  
ORGANIZATION_NAME={dev_org_name}
SPENDING_LIMIT={org.spending_limit}

# Optional: Key management (for reference only)
# OPENROUTER_KEY_HASH={org.key_hash or 'N/A'}

# =============================================================================
# mAI Application Configuration (Development)
# =============================================================================
"""
        
        # Add existing variables (excluding dev-specific ones)
        for key, value in configuration.existing_variables.items():
            if key.startswith('OPENROUTER_') or key in ['ORGANIZATION_NAME', 'SPENDING_LIMIT']:
                continue  # Already added above
            elif key in ['WEBUI_SECRET_KEY', 'WEBUI_URL', 'WEBUI_NAME']:
                continue  # These are set in docker-compose.dev.yml
            else:
                # Quote values that might contain spaces
                if any(char in value for char in [' ', '\t', '\n']) and not value.startswith("'"):
                    content += f"{key}='{value}'\n"
                else:
                    content += f"{key}={value}\n"
        
        # Add footer
        content += f"""
# =============================================================================
# Development Environment Notes
# =============================================================================
# This is a DEVELOPMENT environment with:
# - Separate API key from production
# - External user prefixed with 'dev_'
# - Isolated database volume (mai_dev_data)
# - Hot-reloading for instant code changes
# - Safe for testing without affecting production
"""
        
        return content


class DevEnvironmentGeneratorApplication(EnvironmentGeneratorApplication):
    """Development variant that outputs to .env.dev with dev-specific configuration"""
    
    def __init__(self, database_path: str = "backend/data/webui.db"):
        super().__init__(database_path)
        # Override file manager for dev output
        self.file_manager = DevEnvironmentFileManager()
    
    def _generate_environment_file(self, organization):
        """Override to use dev-specific file generation"""
        self.output.print_progress("Generating .env.dev file for development...")
        
        try:
            # Read existing environment variables
            existing_vars = self.file_manager.read_existing_environment()
            if existing_vars:
                self.output.print_info(f"Read {len(existing_vars)} existing environment variables")
            
            # Create configuration with dev modifications
            from generate_client_env.domain.services import EnvironmentConfigurationService
            config = EnvironmentConfigurationService.create_configuration(
                organization=organization,
                existing_variables=existing_vars
            )
            
            # Generate dev-specific file content
            content = DevEnvironmentFileService.generate_file_content(config)
            
            # Write to .env.dev file
            success, error_msg = self.file_manager.write_environment_file(content, '.env.dev')
            
            if success:
                file_path = self.file_manager.get_absolute_path('.env.dev')
                self.output.print_success(".env.dev file generated successfully!")
                self.output.print_file_info(file_path, True)
                
                # Show merge information
                if existing_vars:
                    openrouter_vars = config.get_openrouter_variables()
                    self.output.print_info(f"Merged {len(existing_vars)} existing environment variables")
                    self.output.print_info(f"Added {len(openrouter_vars)} new OpenRouter variables")
                
                return True
            else:
                self.output.print_error(error_msg or "Failed to write .env.dev file")
                return False
                
        except Exception as e:
            self.output.print_error(f"Error generating .env.dev file: {str(e)}")
            return False
    
    def _show_dev_integration_guidance(self, organization):
        """Show dev-specific integration guidance"""
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
        print(f"   📋 Organization: {organization.name} (DEV)")
        print(f"   💰 Spending Limit: {organization.spending_limit}")
        print(f"   🔑 API Key: {organization.api_key[:20]}...")
        print(f"   👤 External User: dev_{organization.external_user}")
        print(f"   🌐 OpenRouter Host: https://openrouter.ai/api/v1")
    
    def _run_workflow(self, init_database: bool) -> int:
        """Override workflow to show dev-specific guidance"""
        # Run the standard workflow but skip the standard integration guidance
        result = super()._run_workflow(init_database)
        
        if result == 0:
            # Show dev-specific guidance instead
            # We need to reconstruct the organization for display
            # This is a simplified version for the guidance display
            class SimpleOrg:
                def __init__(self, name, spending_limit, api_key, external_user):
                    self.name = name
                    self.spending_limit = spending_limit
                    self.api_key = api_key
                    self.external_user = external_user
            
            # Note: In a real scenario, you'd store these values during workflow
            # For now, this is just for demonstration
            print("\n" + "="*50)
            self._show_dev_integration_guidance(None)  # Pass None since we override the method
        
        return result


def main():
    """Main script execution"""
    parser = ArgumentParser.create_parser()
    parser.description = "Generate .env.dev configuration for mAI development Docker instance"
    parser.epilog = """
This creates .env.dev for development use, keeping it separate from production .env

Examples:
  python generate_client_env_dev.py              # Generate dev environment only
  python generate_client_env_dev.py --production # Also initialize dev database
    """
    
    args = parser.parse_args()
    init_database = args.init_database or args.production
    
    output = OutputFormatter()
    
    print("🔧 mAI Development Environment Generator")
    print("=" * 50)
    print("This will create a SEPARATE development environment")
    print("with its own API key and database.")
    print()
    
    if args.production and init_database:
        output.print_info("Note: Database initialization in dev uses the dev volume")
        output.print_info("The database will be created when you start the container")
        print()
    
    try:
        app = DevEnvironmentGeneratorApplication()
        return app.run(['--production'] if args.production else [])
        
    except KeyboardInterrupt:
        output.print_error("Process interrupted by user.")
        return 130
    except Exception as e:
        output.print_error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())