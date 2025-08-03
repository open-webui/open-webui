#!/usr/bin/env python3
"""
generate_client_env_dev_interactive.py

Interactive development environment initialization script for mAI.
Creates .env.dev with proper settings for local development and hot reload.

Usage:
    python generate_client_env_dev_interactive.py

Features:
    - Interactive terminal guidance
    - Development-specific configuration
    - Hot reload setup
    - Separate API key for testing
    - Docker dev environment preparation
"""

import os
import sys
import secrets
from datetime import datetime
from pathlib import Path

# Import the existing components
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_client_env.main import EnvironmentGeneratorApplication
from generate_client_env.presentation.cli_interface import OutputFormatter


class DevelopmentEnvironmentSetup:
    """Interactive development environment setup for mAI"""
    
    def __init__(self):
        self.output = OutputFormatter()
        self.dev_config = {
            'secret_key': 'mai-secret-key-development-2025',  # Fixed for dev consistency
            'frontend_url': 'http://localhost:5173',
            'backend_url': 'http://localhost:8080',
            'cors_origins': 'http://localhost:5173;http://localhost:3001',
        }
    
    def run_interactive_setup(self):
        """Run complete interactive development setup"""
        self.print_welcome()
        
        try:
            # Step 1: Check prerequisites
            self.check_prerequisites()
            
            # Step 2: Collect development settings
            self.collect_dev_settings()
            
            # Step 3: Generate OpenRouter dev configuration
            self.generate_openrouter_dev_config()
            
            # Step 4: Create development .env.dev file
            self.create_dev_env_file()
            
            # Step 5: Setup Docker dev environment
            self.setup_docker_dev_environment()
            
            # Step 6: Database initialization guidance
            self.provide_database_guidance()
            
            # Step 7: Hot reload instructions
            self.show_hot_reload_instructions()
            
            # Step 8: Development checklist
            self.show_dev_checklist()
            
            return 0
            
        except KeyboardInterrupt:
            self.output.print_error("\n🛑 Setup interrupted by user.")
            return 130
        except Exception as e:
            self.output.print_error(f"❌ Setup failed: {str(e)}")
            return 1
    
    def print_welcome(self):
        """Print welcome message and setup overview"""
        print("🔧 " + "=" * 70)
        print("     mAI Development Environment Setup - Interactive Wizard")  
        print("     Mode: Local Development with Hot Reload")
        print("=" * 72)
        print()
        print("This wizard will guide you through setting up your development environment:")
        print("🏗️  1. Check prerequisites")
        print("⚙️  2. Configure development settings")
        print("🔑 3. Generate OpenRouter dev API configuration")
        print("📄 4. Create .env.dev file") 
        print("🐳 5. Setup Docker development environment")
        print("💾 6. Database initialization")
        print("🔥 7. Hot reload configuration")
        print("✅ 8. Development checklist")
        print()
        print("⚠️  This is for DEVELOPMENT only - separate from production!")
        print()
        
        response = input("Ready to begin? [Y/n]: ").strip().lower()
        if response in ['n', 'no']:
            print("Setup cancelled.")
            sys.exit(0)
        print()
    
    def check_prerequisites(self):
        """Check that development prerequisites are met"""
        self.output.print_step("Checking Prerequisites", 1)
        print("🔍 Verifying development environment...")
        
        checks = []
        
        # Check for venv
        venv_active = hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        )
        checks.append(("Python virtual environment", venv_active))
        
        # Check for Node.js (needed for frontend)
        try:
            import subprocess
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            node_installed = result.returncode == 0
            if node_installed:
                node_version = result.stdout.strip()
                checks.append((f"Node.js ({node_version})", True))
            else:
                checks.append(("Node.js", False))
        except:
            checks.append(("Node.js", False))
        
        # Check for Docker
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            docker_installed = result.returncode == 0
            checks.append(("Docker", docker_installed))
        except:
            checks.append(("Docker", False))
        
        # Check for existing .env.dev
        env_dev_exists = Path('.env.dev').exists()
        if env_dev_exists:
            checks.append((".env.dev", "⚠️  Exists (will be backed up)"))
        else:
            checks.append((".env.dev", True))
        
        # Display results
        all_good = True
        for check, status in checks:
            if isinstance(status, bool):
                icon = "✅" if status else "❌"
                print(f"   {icon} {check}")
                if not status:
                    all_good = False
            else:
                print(f"   {status}")
        
        if not all_good:
            print("\n❌ Some prerequisites are missing!")
            print("Please install missing components before continuing.")
            sys.exit(1)
        
        print("\n✅ All prerequisites met!")
        print()
    
    def collect_dev_settings(self):
        """Collect development-specific settings"""
        self.output.print_step("Development Settings", 2)
        print("⚙️  Configure your development environment:")
        print()
        
        # Organization name for dev
        while True:
            org_name = input("🏢 Development organization name (e.g., 'Dev Testing'): ").strip()
            if org_name:
                self.dev_config['org_name'] = f"{org_name} (DEV)"
                break
            print("❌ Organization name is required!")
        
        # Frontend port (usually 5173 for Vite)
        frontend_port = input("🌐 Frontend port [5173]: ").strip() or "5173"
        self.dev_config['frontend_url'] = f"http://localhost:{frontend_port}"
        
        # Backend port (usually 8080)
        backend_port = input("🔧 Backend port [8080]: ").strip() or "8080"
        self.dev_config['backend_url'] = f"http://localhost:{backend_port}"
        
        # Update CORS origins
        self.dev_config['cors_origins'] = f"http://localhost:{frontend_port};http://localhost:3001"
        
        # Development features
        print("\n🔥 Development features:")
        enable_signup = input("Enable user signup? [Y/n]: ").strip().lower() != 'n'
        self.dev_config['enable_signup'] = enable_signup
        
        show_admin = input("Show admin details? [Y/n]: ").strip().lower() != 'n'
        self.dev_config['show_admin_details'] = show_admin
        
        print("✅ Development settings configured!")
        print()
    
    def generate_openrouter_dev_config(self):
        """Generate OpenRouter configuration for development"""
        self.output.print_step("OpenRouter Development Configuration", 3)
        print("🔑 Setting up OpenRouter API for development...")
        print()
        print("⚠️  This will create a SEPARATE development API key")
        print("   Your production API key will NOT be affected")
        print()
        
        # Get provisioning key
        while True:
            print("📝 OpenRouter Provisioning API Key:")
            print("   (Same key used for both dev and prod)")
            prov_key = input("Provisioning Key: ").strip()
            if prov_key.startswith('sk-or-v1-'):
                self.dev_config['provisioning_key'] = prov_key
                break
            print("❌ Invalid format! Must start with 'sk-or-v1-'")
        
        # Use existing infrastructure to create dev API key
        try:
            app = EnvironmentGeneratorApplication()
            
            # Create a closure to capture dev_config
            dev_config = self.dev_config
            
            # Mock the CLI to use our dev settings
            def mock_interactive_setup():
                return (
                    dev_config['provisioning_key'],
                    dev_config['org_name'],
                    'unlimited'  # Dev always unlimited
                )
            
            app.cli.run_interactive_setup = mock_interactive_setup
            
            # Run workflow without database init
            result = app._run_workflow(init_database=False)
            
            if result == 0:
                print("✅ OpenRouter dev configuration generated!")
                
                # Extract values from generated .env
                if os.path.exists('.env'):
                    with open('.env', 'r') as f:
                        env_content = f.read()
                    
                    for line in env_content.split('\n'):
                        if line.startswith('OPENROUTER_API_KEY='):
                            self.dev_config['api_key'] = line.split('=', 1)[1]
                        elif line.startswith('OPENROUTER_EXTERNAL_USER='):
                            external_user = line.split('=', 1)[1]
                            self.dev_config['external_user'] = f"dev_{external_user}"
                    
                    # Rename .env to .env.openrouter.tmp
                    os.rename('.env', '.env.openrouter.tmp')
                    print("📄 Temporary file saved as .env.openrouter.tmp")
                
                print()
                return True
            else:
                print("❌ Failed to generate OpenRouter configuration!")
                return False
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False
    
    def create_dev_env_file(self):
        """Create the development .env.dev file"""
        self.output.print_step("Creating Development Environment File", 4)
        print("📄 Generating .env.dev for hot reload development...")
        
        # Backup existing .env.dev if exists
        if Path('.env.dev').exists():
            backup_name = f'.env.dev.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            os.rename('.env.dev', backup_name)
            print(f"📋 Existing .env.dev backed up as {backup_name}")
        
        # Generate development environment content
        env_content = f"""# ================================================================
# mAI Development Environment Configuration
# Generated: {datetime.now().isoformat()}
# Mode: Hot Reload Development (Two-Container Architecture)
# ================================================================

# ============= CORE APPLICATION (DEVELOPMENT) =============
ENV=dev
PORT=8080
UVICORN_WORKERS=1

# Development URLs
WEBUI_URL={self.dev_config['frontend_url']}
BACKEND_URL={self.dev_config['backend_url']}
WEBUI_NAME=mAI Development (BACKEND)
ADMIN_EMAIL=dev@localhost

# ============= SECURITY (RELAXED FOR DEV) =============
# Authentication
WEBUI_AUTH=True
JWT_EXPIRES_IN=24h
ENABLE_PERSISTENT_CONFIG=True

# Development Security (HTTP-friendly)
WEBUI_SESSION_COOKIE_SECURE=False
WEBUI_AUTH_COOKIE_SECURE=False
WEBUI_SESSION_COOKIE_SAME_SITE=lax
WEBUI_AUTH_COOKIE_SAME_SITE=lax

# Development Secret Key (fixed for consistency)
WEBUI_SECRET_KEY={self.dev_config['secret_key']}

# CORS (Allow frontend and hot reload ports)
CORS_ALLOW_ORIGIN={self.dev_config['cors_origins']}

# Development Settings
SHOW_ADMIN_DETAILS={'True' if self.dev_config.get('show_admin_details', True) else 'False'}
ENABLE_VERSION_UPDATE_CHECK=False
RESET_CONFIG_ON_START=False
SAFE_MODE=False

# ============= USER MANAGEMENT (DEV) =============
ENABLE_SIGNUP={'True' if self.dev_config.get('enable_signup', True) else 'False'}
ENABLE_LOGIN_FORM=True
DEFAULT_USER_ROLE=user
DEFAULT_LOCALE=en

# Admin Capabilities
ENABLE_ADMIN_EXPORT=True
ENABLE_ADMIN_CHAT_ACCESS=True

# ============= OPENROUTER DEVELOPMENT =============
ENABLE_OPENAI_API=True
OPENAI_API_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY={self.dev_config.get('api_key', '')}
OPENROUTER_API_KEY={self.dev_config.get('api_key', '')}
OPENROUTER_HOST=https://openrouter.ai/api/v1
OPENROUTER_EXTERNAL_USER={self.dev_config.get('external_user', '')}
ORGANIZATION_NAME={self.dev_config.get('org_name', 'Development')}
SPENDING_LIMIT=unlimited
ENABLE_FORWARD_USER_INFO_HEADERS=True

# ============= DEVELOPMENT FEATURES =============
# All features enabled for testing
ENABLE_TITLE_GENERATION=True
ENABLE_FOLLOW_UP_GENERATION=True
ENABLE_TAGS_GENERATION=True
ENABLE_MESSAGE_RATING=True
ENABLE_COMMUNITY_SHARING=False

ENABLE_IMAGE_GENERATION=True
ENABLE_WEB_SEARCH=True
ENABLE_CODE_EXECUTION=True
ENABLE_CODE_INTERPRETER=True
ENABLE_AUTOCOMPLETE_GENERATION=True

ENABLE_API_KEY=True
ENABLE_API_KEY_ENDPOINT_RESTRICTIONS=False
ENABLE_USER_WEBHOOKS=True

# ============= DATABASE (DEVELOPMENT) =============
DATABASE_URL=sqlite:///${{DATA_DIR}}/webui.db
DATABASE_POOL_SIZE=5
DATABASE_POOL_TIMEOUT=30

# ============= STORAGE =============
DATA_DIR=./data
STATIC_DIR=./static

# ============= DEVELOPMENT NOTES =============
# This configuration is for LOCAL DEVELOPMENT ONLY
# - Frontend runs on {self.dev_config['frontend_url']}
# - Backend runs on {self.dev_config['backend_url']}
# - Hot reload enabled for both containers
# - Separate API key from production
# - Database volume: mai_backend_dev_data
# 
# Start with: ./dev-hot-reload.sh up
# ================================================================
"""
        
        # Write the .env.dev file
        try:
            with open('.env.dev', 'w') as f:
                f.write(env_content)
            
            print("✅ Development .env.dev created successfully!")
            print(f"📄 File: {os.path.abspath('.env.dev')}")
            
            # Clean up temporary file
            if os.path.exists('.env.openrouter.tmp'):
                os.remove('.env.openrouter.tmp')
            
            print()
            return True
            
        except Exception as e:
            print(f"❌ Error creating .env.dev: {str(e)}")
            return False
    
    def setup_docker_dev_environment(self):
        """Verify Docker development setup"""
        self.output.print_step("Docker Development Environment", 5)
        print("🐳 Verifying Docker development setup...")
        print()
        
        # Check for dev-hot-reload.sh
        if Path('dev-hot-reload.sh').exists():
            print("✅ dev-hot-reload.sh found")
            
            # Make it executable
            try:
                import subprocess
                subprocess.run(['chmod', '+x', 'dev-hot-reload.sh'], check=True)
                print("✅ dev-hot-reload.sh is executable")
            except:
                print("⚠️  Could not set executable permission on dev-hot-reload.sh")
        else:
            print("❌ dev-hot-reload.sh not found!")
            print("   This script is required for development!")
        
        # Check for docker-compose.dev.yml
        if Path('docker-compose.dev.yml').exists():
            print("✅ docker-compose.dev.yml found")
        else:
            print("⚠️  docker-compose.dev.yml not found")
            print("   Development may not work properly!")
        
        print()
        print("📋 Docker network setup:")
        print("   docker network create mai-network  # (if not exists)")
        print()
    
    def provide_database_guidance(self):
        """Provide database initialization guidance"""
        self.output.print_step("Database Initialization", 6)
        print("💾 Development database setup:")
        print()
        print("📋 The development database will be created automatically when you:")
        print("   1. Start the containers with ./dev-hot-reload.sh up")
        print("   2. The first user to register becomes admin")
        print()
        print("🗄️  Database location:")
        print("   Volume: mai_backend_dev_data")
        print("   Isolated from production data")
        print()
        print("💡 Tips:")
        print("   - Database persists between container restarts")
        print("   - To reset: docker volume rm mai_backend_dev_data")
        print("   - First signup creates admin user")
        print()
    
    def show_hot_reload_instructions(self):
        """Show hot reload development instructions"""
        self.output.print_step("Hot Reload Setup", 7)
        print("🔥 Hot reload development environment:")
        print()
        print("📋 Container architecture:")
        print("   • Frontend: Vite dev server (port {})".format(
            self.dev_config['frontend_url'].split(':')[-1]
        ))
        print("   • Backend: FastAPI with --reload (port 8080)")
        print("   • Changes reflect immediately")
        print()
        print("🚀 Start development:")
        print("   ./dev-hot-reload.sh up")
        print()
        print("🛠️  Available commands:")
        print("   ./dev-hot-reload.sh up       # Start containers")
        print("   ./dev-hot-reload.sh down     # Stop containers")
        print("   ./dev-hot-reload.sh logs     # View logs")
        print("   ./dev-hot-reload.sh logs -f  # Follow logs")
        print("   ./dev-hot-reload.sh shell-fe # Frontend shell")
        print("   ./dev-hot-reload.sh shell-be # Backend shell")
        print("   ./dev-hot-reload.sh build    # Rebuild containers")
        print()
    
    def show_dev_checklist(self):
        """Show development checklist"""
        self.output.print_step("Development Checklist", 8)
        print("✅ Setup Complete! Your development environment is ready.")
        print()
        print("📋 Quick Start Guide:")
        print("=" * 50)
        print()
        print("1️⃣  Start the development environment:")
        print(f"   ./dev-hot-reload.sh up")
        print()
        print("2️⃣  Access the application:")
        print(f"   Frontend: {self.dev_config['frontend_url']}")
        print(f"   Backend API: {self.dev_config['backend_url']}")
        print()
        print("3️⃣  Create your admin user:")
        print("   - Visit the frontend URL")
        print("   - Sign up with your email")
        print("   - First user becomes admin")
        print()
        print("4️⃣  Test features:")
        print("   - All features enabled for development")
        print("   - Separate API key from production")
        print("   - Safe to experiment")
        print()
        print("🔧 Development Tips:")
        print("   • Frontend changes: Instant HMR")
        print("   • Backend changes: Auto-restart")
        print("   • View logs: ./dev-hot-reload.sh logs -f")
        print("   • Stop: ./dev-hot-reload.sh down")
        print()
        print("📚 Configuration Summary:")
        print(f"   Organization: {self.dev_config.get('org_name', 'Development')}")
        print(f"   Frontend: {self.dev_config['frontend_url']}")
        print(f"   Backend: {self.dev_config['backend_url']}")
        print(f"   Signup: {'Enabled' if self.dev_config.get('enable_signup', True) else 'Disabled'}")
        print()
        print("🎉 Happy developing! 🚀")


def main():
    """Main entry point"""
    setup = DevelopmentEnvironmentSetup()
    return setup.run_interactive_setup()


if __name__ == "__main__":
    sys.exit(main())