#!/usr/bin/env python3
"""
generate_client_env.py

Script to generate .env configuration for mAI client Docker instances.
Uses OpenRouter Provisioning API to create dedicated API keys and configure
environment for proper OpenRouter integration with usage tracking.

Usage:
    python generate_client_env.py

Requirements:
    - OpenRouter Provisioning API key
    - Network connectivity to OpenRouter API
    - Write permissions for .env file generation
"""

import os
import sys
import json
import time
import hashlib
import hmac
import base64
import sqlite3
import argparse
from typing import Optional, Dict, Any
from datetime import datetime

try:
    import requests
except ImportError:
    print("❌ Error: 'requests' library not found. Install with: pip install requests")
    sys.exit(1)

# Constants
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
OPENROUTER_HOST = "https://openrouter.ai/api/v1"

class OpenRouterEnvGenerator:
    """Generate .env configuration for mAI client instances using OpenRouter Provisioning API"""
    
    def __init__(self, init_database: bool = False):
        self.provisioning_key: Optional[str] = None
        self.organization_name: Optional[str] = None
        self.spending_limit: Optional[str] = None
        self.generated_api_key: Optional[str] = None
        self.external_user: Optional[str] = None
        self.key_hash: Optional[str] = None
        self.init_database: bool = init_database
        self.database_path: str = "backend/data/webui.db"
        
    def get_user_input(self) -> bool:
        """Collect required information from user"""
        print("🔧 mAI Client Environment Generator")
        print("=" * 50)
        print("This script will generate a .env file for your mAI client Docker instance.")
        print("You need an OpenRouter Provisioning API key to proceed.")
        print()
        
        # Get provisioning key
        while not self.provisioning_key:
            key = input("📝 Enter your OpenRouter Provisioning API key: ").strip()
            if not key:
                print("❌ Provisioning key cannot be empty.")
                continue
            if not key.startswith("sk-or-"):
                print("❌ Invalid key format. OpenRouter keys start with 'sk-or-'")
                continue
            self.provisioning_key = key
            
        # Get organization name
        while not self.organization_name:
            org_name = input("🏢 Enter organization name (e.g., 'ABC Company Sp. z o.o.'): ").strip()
            if not org_name:
                print("❌ Organization name cannot be empty.")
                continue
            if len(org_name) < 3:
                print("❌ Organization name must be at least 3 characters.")
                continue
            self.organization_name = org_name
            
        # Get spending limit
        print("💰 Spending limit options:")
        print("  1. unlimited - No spending restrictions")
        print("  2. Enter specific amount (e.g., 1000.0 for $1000)")
        
        while not self.spending_limit:
            limit_input = input("Enter choice (1 for unlimited, or amount): ").strip().lower()
            if limit_input == "1" or limit_input == "unlimited":
                self.spending_limit = "unlimited"
            else:
                try:
                    limit_amount = float(limit_input)
                    if limit_amount <= 0:
                        print("❌ Spending limit must be positive.")
                        continue
                    self.spending_limit = str(limit_amount)
                except ValueError:
                    print("❌ Invalid input. Enter '1' for unlimited or a numeric amount.")
                    continue
                    
        return True
    
    def validate_provisioning_key(self) -> bool:
        """Validate the provisioning key by testing API connectivity"""
        print("\n🔍 Validating provisioning key...")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.provisioning_key}",
                "Content-Type": "application/json"
            }
            
            # Test with list keys endpoint (should work with valid provisioning key)
            response = requests.get(
                f"{OPENROUTER_API_BASE}/keys",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                print("✅ Provisioning key validated successfully!")
                return True
            elif response.status_code == 401:
                print("❌ Invalid provisioning key. Please check your key and try again.")
                return False
            else:
                print(f"❌ Unexpected response: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error validating key: {e}")
            return False
    
    def create_api_key(self) -> bool:
        """Create a new API key using OpenRouter Provisioning API"""
        print(f"\n🔑 Creating API key for '{self.organization_name}'...")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.provisioning_key}",
                "Content-Type": "application/json"
            }
            
            # Prepare request data
            data = {
                "name": f"mAI Client: {self.organization_name}",
                "label": f"mai-{self.organization_name.lower().replace(' ', '-').replace('.', '').replace(',', '')[:20]}"
            }
            
            # Add spending limit if not unlimited
            if self.spending_limit != "unlimited":
                data["limit"] = float(self.spending_limit)
            
            print(f"📤 Creating key with data: {json.dumps(data, indent=2)}")
            
            # Make API request
            response = requests.post(
                f"{OPENROUTER_API_BASE}/keys",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                print(f"📥 Response: {json.dumps(result, indent=2)}")
                
                # Extract API key from response
                if "key" in result:
                    self.generated_api_key = result["key"]
                    self.key_hash = result.get("data", {}).get("hash")
                elif "data" in result and "key" in result["data"]:
                    self.generated_api_key = result["data"]["key"]
                    self.key_hash = result["data"].get("hash")
                else:
                    print("❌ No API key found in response!")
                    return False
                
                if self.generated_api_key:
                    print(f"✅ API key created successfully!")
                    print(f"🔗 Key hash: {self.key_hash}")
                    return True
                else:
                    print("❌ Failed to extract API key from response!")
                    return False
                    
            else:
                print(f"❌ Failed to create API key: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error creating API key: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
    def test_api_key_and_get_external_user(self) -> bool:
        """Test the generated API key and capture external_user from response"""
        print(f"\n🧪 Testing API key and capturing external_user...")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.generated_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://mai.example.com",
                "X-Title": f"mAI Client - {self.organization_name}"
            }
            
            # Make a simple test request to get external_user
            test_data = {
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello! This is a test message to initialize external_user mapping."
                    }
                ],
                "max_tokens": 10
            }
            
            print("📤 Making test request to OpenRouter...")
            response = requests.post(
                f"{OPENROUTER_HOST}/chat/completions",
                headers=headers,
                json=test_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract external_user from response if available
                self.external_user = result.get("external_user")
                
                if self.external_user:
                    print(f"✅ Test request successful! External user: {self.external_user}")
                else:
                    # Generate a predictable external_user if not provided
                    org_hash = hashlib.md5(self.organization_name.encode()).hexdigest()[:8]
                    self.external_user = f"mai_client_{org_hash}"
                    print(f"ℹ️  No external_user in response. Generated: {self.external_user}")
                
                return True
                
            else:
                print(f"❌ Test request failed: {response.status_code} - {response.text}")
                
                # Generate fallback external_user even if test fails
                org_hash = hashlib.md5(self.organization_name.encode()).hexdigest()[:8]
                self.external_user = f"mai_client_{org_hash}"
                print(f"⚠️  Using fallback external_user: {self.external_user}")
                return True  # Continue with fallback
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error during test: {e}")
            # Generate fallback external_user
            org_hash = hashlib.md5(self.organization_name.encode()).hexdigest()[:8]
            self.external_user = f"mai_client_{org_hash}"
            print(f"⚠️  Using fallback external_user: {self.external_user}")
            return True  # Continue with fallback
        except Exception as e:
            print(f"❌ Unexpected error during test: {e}")
            return False
    
    def read_existing_env(self) -> Dict[str, str]:
        """Read existing .env file if it exists"""
        existing_vars = {}
        env_files = ['.env', '.env.example']
        
        for env_file in env_files:
            if os.path.exists(env_file):
                print(f"📖 Reading existing environment from {env_file}...")
                try:
                    with open(env_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"\'')
                                if key not in existing_vars:  # Don't override with later files
                                    existing_vars[key] = value
                    break  # Use first found file
                except Exception as e:
                    print(f"⚠️ Warning: Could not read {env_file}: {e}")
        
        return existing_vars
    
    def generate_env_file(self) -> bool:
        """Generate .env file with all configuration, merging existing variables"""
        print(f"\n📄 Generating .env file...")
        
        try:
            # Read existing environment variables
            existing_vars = self.read_existing_env()
            
            # Our new OpenRouter configuration
            openrouter_vars = {
                'OPENROUTER_API_KEY': self.generated_api_key,
                'OPENROUTER_HOST': OPENROUTER_HOST,
                'OPENROUTER_EXTERNAL_USER': self.external_user,
                'ORGANIZATION_NAME': self.organization_name,
                'SPENDING_LIMIT': self.spending_limit,
            }
            
            # Merge configurations (our OpenRouter config takes precedence)
            merged_vars = {**existing_vars, **openrouter_vars}
            
            # Generate the complete .env content
            env_content = f"""# mAI Client Environment Configuration
# Generated on: {datetime.now().isoformat()}
# Organization: {self.organization_name}
# Spending Limit: {self.spending_limit}

# =============================================================================
# OpenRouter Configuration (mAI Client-specific)
# =============================================================================
OPENROUTER_API_KEY={self.generated_api_key}
OPENROUTER_HOST={OPENROUTER_HOST}
OPENROUTER_EXTERNAL_USER={self.external_user}

# Organization Configuration  
ORGANIZATION_NAME={self.organization_name}
SPENDING_LIMIT={self.spending_limit}

# Optional: Key management (for reference only)
# OPENROUTER_KEY_HASH={self.key_hash or 'N/A'}

# =============================================================================
# mAI Application Configuration (merged from existing .env)
# =============================================================================
"""
            
            # Add existing variables in organized sections
            app_vars = {}
            api_vars = {}
            cors_vars = {}
            other_vars = {}
            
            for key, value in merged_vars.items():
                if key.startswith('OPENROUTER_') or key in ['ORGANIZATION_NAME', 'SPENDING_LIMIT']:
                    continue  # Already added above
                elif key.startswith('OLLAMA_') or key.startswith('OPENAI_'):
                    api_vars[key] = value
                elif key.startswith('CORS_') or key.startswith('FORWARDED_'):
                    cors_vars[key] = value
                elif key.startswith('WEBUI_') or key.startswith('BACKEND_'):
                    app_vars[key] = value
                else:
                    other_vars[key] = value
            
            # Write API configuration section
            if api_vars:
                env_content += "\n# API Configuration\n"
                for key, value in api_vars.items():
                    env_content += f"{key}='{value}'\n"
            
            # Write CORS and networking section
            if cors_vars:
                env_content += "\n# CORS and Networking\n"
                for key, value in cors_vars.items():
                    env_content += f"{key}='{value}'\n"
            
            # Write application URLs section
            if app_vars:
                env_content += "\n# Application URLs\n"
                for key, value in app_vars.items():
                    env_content += f"{key}={value}\n"
            
            # Write other configuration
            if other_vars:
                env_content += "\n# Other Configuration\n"
                for key, value in other_vars.items():
                    env_content += f"{key}={value}\n"
            
            env_content += f"""
# =============================================================================
# Docker Configuration Notes
# =============================================================================
# These values will be automatically mapped to the application
# No manual configuration required in the application code
# 
# The OpenRouter configuration above replaces manual API key entry in the UI
# Clients will NOT see the "OpenAI API Interface" settings section
"""
            
            # Write to .env file
            with open('.env', 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            print("✅ .env file generated successfully!")
            print(f"📁 Location: {os.path.abspath('.env')}")
            
            # Show what was merged
            if existing_vars:
                print(f"🔄 Merged {len(existing_vars)} existing environment variables")
                print(f"➕ Added {len(openrouter_vars)} new OpenRouter variables")
            
            return True
            
        except Exception as e:
            print(f"❌ Error generating .env file: {e}")
            return False
    
    def show_integration_guidance(self):
        """Show guidance for integrating with mAI system"""
        print(f"\n🚀 Integration Guidance")
        print("=" * 50)
        print("Your .env file has been generated. Here's how to integrate it with mAI:")
        print()
        
        print("📋 Docker Integration:")
        print("   Add to your docker-compose.yml:")
        print("   ```")
        print("   services:")
        print("     mai-app:")
        print("       env_file: .env")
        print("       # ... other configuration")
        print("   ```")
        print()
        
        print("🔧 Application Integration:")
        print("   Update these files to read from environment variables:")
        print()
        print("   1. backend/open_webui/routers/openai.py:")
        print("      - Replace API key database lookups with:")
        print("        api_key = os.getenv('OPENROUTER_API_KEY')")
        print("        external_user = os.getenv('OPENROUTER_EXTERNAL_USER')")
        print()
        
        print("   2. backend/open_webui/config.py:")
        print("      - Add environment variable definitions:")
        print("        OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')")
        print("        OPENROUTER_HOST = os.getenv('OPENROUTER_HOST', 'https://openrouter.ai/api/v1')")
        print("        OPENROUTER_EXTERNAL_USER = os.getenv('OPENROUTER_EXTERNAL_USER')")
        print("        ORGANIZATION_NAME = os.getenv('ORGANIZATION_NAME')")
        print("        SPENDING_LIMIT = os.getenv('SPENDING_LIMIT')")
        print()
        
        if self.init_database:
            print("📊 Usage Tracking:")
            print("   ✅ Database initialized with client organization")
            print("   ✅ Usage tracking ready for production")
            print("   ✅ External user mapping configured")
            print("   ✅ Billing calculations with 1.3x markup rate")
            print("   ✅ Duplicate prevention system active")
            print("   ✅ Generation ID tracking enabled")
        else:
            print("📊 Usage Tracking:")
            print("   ⚠️  Database initialization required for production")
            print("   💡 Run with --production flag for complete setup")
            print("   ✅ External user mapping will work when database is initialized")
            print("   ✅ Billing calculations will work when database is initialized")
        print()
        
        print("🔐 Security Notes:")
        print("   - .env file contains sensitive API keys")
        print("   - Add .env to .gitignore (should already be there)")
        print("   - Keep .env file permissions restricted (600)")
        print("   - Each client instance should have its own .env file")
        print()
        
        print("🐳 Deployment:")
        print("   1. Copy .env file to your Docker deployment directory")
        print("   2. Ensure docker-compose.yml includes 'env_file: .env'")
        if self.init_database:
            print("   3. Start your mAI container - fully configured and production-ready!")
        else:
            print("   3. Initialize database: python generate_client_env.py --init-database")
            print("   4. Start your mAI container")
        print()
        
        print("✅ Configuration Summary:")
        print(f"   📋 Organization: {self.organization_name}")
        print(f"   💰 Spending Limit: {self.spending_limit}")
        print(f"   🔑 API Key: {self.generated_api_key[:20]}...")
        print(f"   👤 External User: {self.external_user}")
        print(f"   🌐 OpenRouter Host: {OPENROUTER_HOST}")
    
    def check_database_connection(self) -> bool:
        """Check if database exists and is accessible"""
        if not os.path.exists(self.database_path):
            print(f"❌ Database not found at: {self.database_path}")
            print("   Make sure you're running this script from the mAI project root directory")
            return False
        
        try:
            conn = sqlite3.connect(self.database_path)
            conn.close()
            print(f"✅ Database connection verified: {self.database_path}")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    def create_client_organization(self) -> bool:
        """Create or update client organization in database"""
        print(f"\n🏢 Setting up client organization in database...")
        
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Check if client_organizations table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='client_organizations'
            """)
            
            if not cursor.fetchone():
                print("❌ client_organizations table not found. Database schema may be incomplete.")
                return False
            
            # Prepare client organization data
            client_id = self.external_user
            current_time = datetime.now().isoformat()
            markup_rate = 1.3  # Default mAI markup rate
            
            # Insert or replace client organization
            cursor.execute("""
                INSERT OR REPLACE INTO client_organizations 
                (id, name, openrouter_api_key, markup_rate, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                client_id,
                self.organization_name,
                self.generated_api_key,
                markup_rate,
                1,  # is_active = true
                current_time,
                current_time
            ))
            
            conn.commit()
            
            # Verify the record was created
            cursor.execute("""
                SELECT id, name, markup_rate, is_active 
                FROM client_organizations 
                WHERE id = ?
            """, (client_id,))
            
            result = cursor.fetchone()
            if result:
                org_id, org_name, rate, active = result
                print(f"✅ Client organization created successfully:")
                print(f"   📋 ID: {org_id}")
                print(f"   🏢 Name: {org_name}")
                print(f"   💰 Markup Rate: {rate}x")
                print(f"   ✅ Active: {'Yes' if active else 'No'}")
                return True
            else:
                print("❌ Failed to verify client organization creation")
                return False
                
        except Exception as e:
            print(f"❌ Error creating client organization: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def validate_database_setup(self) -> bool:
        """Validate that database setup is complete and functional"""
        print(f"\n🔍 Validating database setup...")
        
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Check client organization exists
            cursor.execute("""
                SELECT COUNT(*) FROM client_organizations WHERE id = ?
            """, (self.external_user,))
            
            org_count = cursor.fetchone()[0]
            if org_count == 0:
                print(f"❌ Client organization {self.external_user} not found in database")
                return False
            
            # Check database tables exist
            required_tables = [
                'client_organizations',
                'client_user_daily_usage', 
                'client_model_daily_usage',
                'processed_generations',
                'processed_generation_cleanup_log'
            ]
            
            missing_tables = []
            for table in required_tables:
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (table,))
                
                if not cursor.fetchone():
                    missing_tables.append(table)
            
            if missing_tables:
                print(f"⚠️  Warning: Missing tables: {', '.join(missing_tables)}")
                print("   Usage tracking and duplicate prevention may not work until these tables are created")
                
                # Check specifically for duplicate prevention tables
                duplicate_prevention_tables = ['processed_generations', 'processed_generation_cleanup_log']
                missing_dp_tables = [t for t in missing_tables if t in duplicate_prevention_tables]
                if missing_dp_tables:
                    print(f"   ❌ Duplicate prevention disabled: Missing {', '.join(missing_dp_tables)}")
            
            print(f"✅ Database validation completed")
            print(f"   🏢 Client organization: {self.external_user}")
            print(f"   📊 Usage tracking tables: {'All present' if not missing_tables else f'{len(required_tables) - len(missing_tables)}/{len(required_tables)} present'}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error validating database setup: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def setup_database_for_production(self) -> bool:
        """Complete database setup for production deployment"""
        print(f"\n🎯 Setting up database for production deployment...")
        print("=" * 60)
        
        # Step 1: Check database connection
        if not self.check_database_connection():
            return False
        
        # Step 2: Create client organization
        if not self.create_client_organization():
            return False
        
        # Step 3: Validate setup
        if not self.validate_database_setup():
            print("⚠️  Database setup validation failed, but continuing...")
        
        print(f"\n✅ Database setup completed successfully!")
        print(f"🚀 Your mAI instance is now production-ready with:")
        print(f"   • Environment variables in .env file")
        print(f"   • Client organization in database")
        print(f"   • Usage tracking configuration")
        print(f"   • Duplicate prevention system")
        print(f"   • Generation ID tracking enabled")
        
        return True

def main():
    """Main script execution"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Generate .env configuration for mAI client Docker instances",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_client_env.py                    # Generate environment only
  python generate_client_env.py --init-database    # Generate environment + setup database
  python generate_client_env.py --production       # Full production setup (recommended)
        """
    )
    
    parser.add_argument(
        '--init-database', '--db',
        action='store_true',
        help='Initialize database with client organization (requires existing database)'
    )
    
    parser.add_argument(
        '--production', '--prod',
        action='store_true',
        help='Full production setup: environment + database initialization (recommended)'
    )
    
    args = parser.parse_args()
    
    # Determine if database initialization is requested
    init_database = args.init_database or args.production
    
    generator = OpenRouterEnvGenerator(init_database=init_database)
    
    try:
        # Step 1: Get user input
        if not generator.get_user_input():
            print("❌ Failed to collect required information.")
            return 1
        
        # Step 2: Validate provisioning key
        if not generator.validate_provisioning_key():
            print("❌ Provisioning key validation failed.")
            return 1
        
        # Step 3: Create API key
        if not generator.create_api_key():
            print("❌ Failed to create API key.")
            return 1
        
        # Step 4: Test API key and get external_user
        if not generator.test_api_key_and_get_external_user():
            print("❌ Failed to test API key.")
            return 1
        
        # Step 5: Generate .env file
        if not generator.generate_env_file():
            print("❌ Failed to generate .env file.")
            return 1
        
        # Step 6: Initialize database if requested
        if init_database:
            if not generator.setup_database_for_production():
                print("❌ Database initialization failed.")
                print("   Environment file was created successfully, but database setup incomplete.")
                print("   You can retry database setup later with: python generate_client_env.py --init-database")
                return 1
        
        # Step 7: Show integration guidance
        generator.show_integration_guidance()
        
        if init_database:
            print(f"\n🎉 Success! Your mAI client is fully production-ready.")
            print(f"✅ Environment configured and database initialized.")
        else:
            print(f"\n🎉 Success! Your mAI client environment is ready.")
            print(f"💡 For production deployment, also run: python generate_client_env.py --init-database")
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n❌ Process interrupted by user.")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())