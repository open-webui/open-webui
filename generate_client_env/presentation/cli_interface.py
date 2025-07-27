"""
Command-line interface for mAI client environment generation.

Handles all user interactions and input/output operations.
"""

import argparse
import sys
from typing import Optional, Tuple

from ..domain.validators import ValidationError


class CliError(Exception):
    """Raised when CLI operations fail."""
    pass


class UserInputCollector:
    """Handles collection of user input with validation."""
    
    def collect_provisioning_key(self) -> str:
        """
        Collect OpenRouter provisioning key from user.
        
        Returns:
            Valid provisioning key
            
        Raises:
            CliError: If user cancels or input is invalid
        """
        print("📝 Enter your OpenRouter Provisioning API key:")
        print("   (Format: sk-or-xxxxx...)")
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                key = input("API Key: ").strip()
                
                if not key:
                    print("❌ API key cannot be empty.")
                    continue
                
                if not key.startswith("sk-or-"):
                    print("❌ Invalid key format. OpenRouter keys start with 'sk-or-'")
                    continue
                
                if len(key) < 20:  # Basic length check
                    print("❌ API key appears too short.")
                    continue
                
                return key
                
            except KeyboardInterrupt:
                raise CliError("User cancelled input")
            except EOFError:
                raise CliError("Unexpected end of input")
        
        raise CliError(f"Failed to collect valid API key after {max_attempts} attempts")
    
    def collect_organization_name(self) -> str:
        """
        Collect organization name from user.
        
        Returns:
            Valid organization name
            
        Raises:
            CliError: If user cancels or input is invalid
        """
        print("\n🏢 Enter organization name:")
        print("   (e.g., 'ABC Company Sp. z o.o.')")
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                name = input("Organization: ").strip()
                
                if not name:
                    print("❌ Organization name cannot be empty.")
                    continue
                
                if len(name) < 3:
                    print("❌ Organization name must be at least 3 characters.")
                    continue
                
                if len(name) > 100:
                    print("❌ Organization name too long (max 100 characters).")
                    continue
                
                return name
                
            except KeyboardInterrupt:
                raise CliError("User cancelled input")
            except EOFError:
                raise CliError("Unexpected end of input")
        
        raise CliError(f"Failed to collect valid organization name after {max_attempts} attempts")
    
    def collect_spending_limit(self) -> str:
        """
        Collect spending limit from user.
        
        Returns:
            Valid spending limit value
            
        Raises:
            CliError: If user cancels or input is invalid
        """
        print("\n💰 Spending limit options:")
        print("  1. unlimited - No spending restrictions")
        print("  2. Enter specific amount (e.g., 1000.0 for $1000)")
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                limit_input = input("Enter choice (1 for unlimited, or amount): ").strip().lower()
                
                if limit_input == "1" or limit_input == "unlimited":
                    return "unlimited"
                
                # Try to parse as number
                try:
                    limit_amount = float(limit_input)
                    if limit_amount <= 0:
                        print("❌ Spending limit must be positive.")
                        continue
                    return str(limit_amount)
                    
                except ValueError:
                    print("❌ Invalid input. Enter '1' for unlimited or a numeric amount.")
                    continue
                    
            except KeyboardInterrupt:
                raise CliError("User cancelled input")
            except EOFError:
                raise CliError("Unexpected end of input")
        
        raise CliError(f"Failed to collect valid spending limit after {max_attempts} attempts")


class OutputFormatter:
    """Handles formatted output and user feedback."""
    
    @staticmethod
    def print_header():
        """Print application header."""
        print("🔧 mAI Client Environment Generator")
        print("=" * 50)
        print("This script will generate a .env file for your mAI client Docker instance.")
        print("You need an OpenRouter Provisioning API key to proceed.")
        print()
    
    @staticmethod
    def print_step(step_name: str, step_number: Optional[int] = None):
        """Print step header."""
        prefix = f"Step {step_number}: " if step_number else ""
        print(f"\n{prefix}{step_name}")
    
    @staticmethod
    def print_success(message: str):
        """Print success message."""
        print(f"✅ {message}")
    
    @staticmethod
    def print_error(message: str):
        """Print error message."""
        print(f"❌ {message}")
    
    @staticmethod
    def print_warning(message: str):
        """Print warning message."""
        print(f"⚠️  {message}")
    
    @staticmethod
    def print_info(message: str):
        """Print info message."""
        print(f"ℹ️  {message}")
    
    @staticmethod
    def print_progress(message: str):
        """Print progress message."""
        print(f"🔍 {message}")
    
    @staticmethod
    def print_validation_result(success: bool, message: str):
        """Print validation result."""
        if success:
            OutputFormatter.print_success(message)
        else:
            OutputFormatter.print_error(message)
    
    @staticmethod
    def print_api_response(response_data: dict, title: str = "API Response"):
        """Print formatted API response."""
        print(f"📥 {title}:")
        import json
        print(json.dumps(response_data, indent=2))
    
    @staticmethod
    def print_file_info(file_path: str, exists: bool):
        """Print file information."""
        status = "✅ Created" if exists else "❌ Not found"
        print(f"📁 {status}: {file_path}")
    
    @staticmethod
    def print_configuration_summary(org_name: str, spending_limit: str, 
                                  api_key: str, external_user: str, host: str):
        """Print configuration summary."""
        print("\n✅ Configuration Summary:")
        print(f"   📋 Organization: {org_name}")
        print(f"   💰 Spending Limit: {spending_limit}")
        print(f"   🔑 API Key: {api_key[:20]}...")
        print(f"   👤 External User: {external_user}")
        print(f"   🌐 OpenRouter Host: {host}")
    
    @staticmethod
    def print_integration_guidance(organization_name: str, external_user: str, 
                                 has_database: bool):
        """Print integration guidance."""
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
        
        if has_database:
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
        if has_database:
            print("   3. Start your mAI container - fully configured and production-ready!")
        else:
            print("   3. Initialize database: python generate_client_env.py --init-database")
            print("   4. Start your mAI container")
        print()


class ArgumentParser:
    """Handles command-line argument parsing."""
    
    @staticmethod
    def create_parser() -> argparse.ArgumentParser:
        """Create and configure argument parser."""
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
        
        return parser
    
    @staticmethod
    def parse_arguments(args: Optional[list] = None) -> argparse.Namespace:
        """Parse command-line arguments."""
        parser = ArgumentParser.create_parser()
        return parser.parse_args(args)


class CliInterface:
    """Main CLI interface coordinator."""
    
    def __init__(self):
        self.input_collector = UserInputCollector()
        self.output_formatter = OutputFormatter()
    
    def run_interactive_setup(self) -> Tuple[str, str, str]:
        """
        Run interactive setup to collect user input.
        
        Returns:
            Tuple of (provisioning_key, organization_name, spending_limit)
            
        Raises:
            CliError: If setup fails
        """
        try:
            self.output_formatter.print_header()
            
            # Collect inputs
            provisioning_key = self.input_collector.collect_provisioning_key()
            organization_name = self.input_collector.collect_organization_name()
            spending_limit = self.input_collector.collect_spending_limit()
            
            return provisioning_key, organization_name, spending_limit
            
        except (KeyboardInterrupt, EOFError):
            raise CliError("Setup cancelled by user")
        except Exception as e:
            raise CliError(f"Setup failed: {str(e)}")
    
    def handle_error(self, error: Exception) -> int:
        """
        Handle and display error appropriately.
        
        Args:
            error: Exception to handle
            
        Returns:
            Exit code
        """
        if isinstance(error, KeyboardInterrupt):
            self.output_formatter.print_error("Process interrupted by user.")
            return 130  # Standard exit code for SIGINT
        elif isinstance(error, ValidationError):
            self.output_formatter.print_error(f"Validation error: {str(error)}")
            return 1
        elif isinstance(error, CliError):
            self.output_formatter.print_error(str(error))
            return 1
        else:
            self.output_formatter.print_error(f"Unexpected error: {str(error)}")
            return 1
    
    def print_final_success(self, has_database: bool):
        """Print final success message."""
        if has_database:
            print(f"\n🎉 Success! Your mAI client is fully production-ready.")
            print(f"✅ Environment configured and database initialized.")
        else:
            print(f"\n🎉 Success! Your mAI client environment is ready.")
            print(f"💡 For production deployment, also run: python generate_client_env.py --init-database")