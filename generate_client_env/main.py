"""
Main application composition root for mAI client environment generation.

Coordinates all layers of the clean architecture and provides the main entry point.
"""

import sys
import os
from pathlib import Path
from typing import Optional

# Domain layer imports
from .domain.entities import ClientOrganization, ApiKeyCreationRequest, EnvironmentConfiguration
from .domain.services import (
    OrganizationService, 
    ExternalUserService, 
    ApiKeyRequestService,
    EnvironmentConfigurationService,
    EnvironmentFileService,
    DatabaseSetupService
)
from .domain.validators import ValidationError

# Infrastructure layer imports
from .infrastructure.openrouter_client import OpenRouterClient, OpenRouterApiError
from .infrastructure.database_client import DatabaseClient, DatabaseError
from .infrastructure.file_manager import EnvironmentFileManager, FileManagerError

# Presentation layer imports
from .presentation.cli_interface import CliInterface, CliError, ArgumentParser, OutputFormatter


class ApplicationError(Exception):
    """Raised when application-level operations fail."""
    pass


class EnvironmentGeneratorApplication:
    """Main application that coordinates all operations."""
    
    def __init__(self, database_path: Optional[str] = None):
        # Determine database path using the same logic as the main application
        if database_path is None:
            database_path = self._determine_database_path()
        
        # Initialize infrastructure components
        self.openrouter_client = OpenRouterClient()
        self.database_client = DatabaseClient(database_path)
        self.file_manager = EnvironmentFileManager()
        
        # Initialize presentation layer
        self.cli = CliInterface()
        self.output = OutputFormatter()
        
        # Configuration
        self.database_path = database_path
    
    def _determine_database_path(self) -> str:
        """
        Determine database path using the same logic as the main application.
        
        This replicates the logic from backend/open_webui/env.py to ensure
        the client initialization script uses the same database path as the
        running application.
        """
        # Determine base directories (same as env.py)
        open_webui_dir = Path("backend/open_webui").resolve()
        backend_dir = open_webui_dir.parent
        
        # Check if running in Docker
        docker = os.environ.get("DOCKER", "False").lower() == "true"
        
        # Determine DATA_DIR based on environment
        if docker:
            data_dir = Path(os.getenv("DATA_DIR", open_webui_dir / "data")).resolve()
        else:
            data_dir = Path(os.getenv("DATA_DIR", backend_dir / "data")).resolve()
        
        # Return the database file path
        database_path = str(data_dir / "webui.db")
        
        return database_path
    
    def run(self, args: Optional[list] = None) -> int:
        """
        Main application entry point.
        
        Args:
            args: Command-line arguments (uses sys.argv if None)
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            # Parse arguments
            parsed_args = ArgumentParser.parse_arguments(args)
            init_database = parsed_args.init_database or parsed_args.production
            
            # Run the complete workflow
            return self._run_workflow(init_database)
            
        except Exception as e:
            return self.cli.handle_error(e)
    
    def _run_workflow(self, init_database: bool) -> int:
        """
        Execute the complete environment generation workflow.
        
        Args:
            init_database: Whether to initialize database
            
        Returns:
            Exit code
        """
        try:
            # Step 1: Collect user input
            self.output.print_step("Collecting user information", 1)
            provisioning_key, org_name, spending_limit = self.cli.run_interactive_setup()
            
            # Step 2: Validate provisioning key
            self.output.print_step("Validating provisioning key", 2)
            if not self._validate_provisioning_key(provisioning_key):
                return 1
            
            # Step 3: Create API key
            self.output.print_step("Creating API key", 3)
            api_key, key_hash = self._create_api_key(provisioning_key, org_name, spending_limit)
            if not api_key:
                return 1
            
            # Step 4: Test API key and get external user
            self.output.print_step("Testing API key", 4)
            external_user = self._test_api_key_and_get_external_user(api_key, org_name)
            if not external_user:
                return 1
            
            # Step 5: Create domain entities
            organization = OrganizationService.create_organization(
                name=org_name,
                spending_limit=spending_limit,
                api_key=api_key,
                key_hash=key_hash
            )
            # Override external_user if we got one from API test
            organization.external_user = external_user
            
            # Step 6: Generate environment file
            self.output.print_step("Generating environment file", 5)
            if not self._generate_environment_file(organization):
                return 1
            
            # Step 7: Initialize database if requested
            if init_database:
                self.output.print_step("Initializing database", 6)
                if not self._setup_database(organization):
                    self.output.print_error("Database initialization failed.")
                    self.output.print_info("Environment file was created successfully, but database setup incomplete.")
                    self.output.print_info("You can retry database setup later with: python generate_client_env.py --init-database")
                    return 1
            
            # Step 8: Show integration guidance
            self.output.print_step("Integration guidance", 7)
            self.cli.output_formatter.print_integration_guidance(
                org_name, external_user, init_database
            )
            
            # Print configuration summary
            self.cli.output_formatter.print_configuration_summary(
                org_name, spending_limit, api_key, external_user,
                EnvironmentConfigurationService.DEFAULT_OPENROUTER_HOST
            )
            
            # Final success message
            self.cli.print_final_success(init_database)
            return 0
            
        except Exception as e:
            return self.cli.handle_error(e)
    
    def _validate_provisioning_key(self, provisioning_key: str) -> bool:
        """Validate the provisioning key."""
        self.output.print_progress("Validating provisioning key...")
        
        try:
            response = self.openrouter_client.validate_provisioning_key(provisioning_key)
            
            if response.success:
                self.output.print_success("Provisioning key validated successfully!")
                return True
            else:
                self.output.print_error(response.error_message or "Provisioning key validation failed")
                return False
                
        except Exception as e:
            self.output.print_error(f"Error validating provisioning key: {str(e)}")
            return False
    
    def _create_api_key(self, provisioning_key: str, org_name: str, spending_limit: str) -> tuple:
        """Create API key using OpenRouter API."""
        self.output.print_progress(f"Creating API key for '{org_name}'...")
        
        try:
            # Create request using domain service
            key_request = ApiKeyRequestService.create_key_request(org_name, spending_limit)
            key_data = key_request.to_api_payload()
            
            self.output.print_info(f"Creating key with data: {key_data}")
            
            # Make API call
            response = self.openrouter_client.create_api_key(provisioning_key, key_data)
            
            if response.success:
                api_key = response.data["api_key"]
                key_hash = response.data.get("key_hash")
                
                self.output.print_success("API key created successfully!")
                if key_hash:
                    self.output.print_info(f"Key hash: {key_hash}")
                
                return api_key, key_hash
            else:
                self.output.print_error(response.error_message or "Failed to create API key")
                return None, None
                
        except ValidationError as e:
            self.output.print_error(f"Validation error: {str(e)}")
            return None, None
        except Exception as e:
            self.output.print_error(f"Error creating API key: {str(e)}")
            return None, None
    
    def _test_api_key_and_get_external_user(self, api_key: str, org_name: str) -> Optional[str]:
        """Test API key and get external user ID."""
        self.output.print_progress("Testing API key and capturing external_user...")
        
        try:
            response = self.openrouter_client.test_api_key(api_key, org_name)
            
            if response.success and response.data.get("test_successful"):
                external_user = response.data.get("external_user")
                if external_user:
                    self.output.print_success(f"Test request successful! External user: {external_user}")
                    return external_user
                else:
                    # Generate fallback external_user
                    external_user = ExternalUserService.generate_external_user(org_name)
                    self.output.print_info(f"No external_user in response. Generated: {external_user}")
                    return external_user
            else:
                # Generate fallback external_user even if test fails
                external_user = ExternalUserService.generate_external_user(org_name)
                self.output.print_warning(f"Test request failed. Using fallback external_user: {external_user}")
                return external_user
                
        except Exception as e:
            # Generate fallback external_user on error
            try:
                external_user = ExternalUserService.generate_external_user(org_name)
                self.output.print_warning(f"Error during test: {str(e)}. Using fallback external_user: {external_user}")
                return external_user
            except Exception:
                self.output.print_error(f"Error during test and fallback generation: {str(e)}")
                return None
    
    def _generate_environment_file(self, organization: ClientOrganization) -> bool:
        """Generate the environment file."""
        self.output.print_progress("Generating .env file...")
        
        try:
            # Read existing environment variables
            existing_vars = self.file_manager.read_existing_environment()
            if existing_vars:
                self.output.print_info(f"Read {len(existing_vars)} existing environment variables")
            
            # Create configuration
            config = EnvironmentConfigurationService.create_configuration(
                organization=organization,
                existing_variables=existing_vars
            )
            
            # Generate file content
            content = EnvironmentFileService.generate_file_content(config)
            
            # Write to file
            success, error_msg = self.file_manager.write_environment_file(content)
            
            if success:
                file_path = self.file_manager.get_absolute_path('.env')
                self.output.print_success(".env file generated successfully!")
                self.output.print_file_info(file_path, True)
                
                # Show merge information
                if existing_vars:
                    openrouter_vars = config.get_openrouter_variables()
                    self.output.print_info(f"Merged {len(existing_vars)} existing environment variables")
                    self.output.print_info(f"Added {len(openrouter_vars)} new OpenRouter variables")
                
                return True
            else:
                self.output.print_error(error_msg or "Failed to write environment file")
                return False
                
        except ValidationError as e:
            self.output.print_error(f"Validation error: {str(e)}")
            return False
        except Exception as e:
            self.output.print_error(f"Error generating environment file: {str(e)}")
            return False
    
    def _setup_database(self, organization: ClientOrganization) -> bool:
        """Setup database for production deployment."""
        self.output.print_progress("Setting up database for production deployment...")
        print("=" * 60)
        
        try:
            # Check database connection
            success, error_msg = self.database_client.check_connection()
            if not success:
                self.output.print_error(error_msg)
                self.output.print_info("Make sure you're running this script from the mAI project root directory")
                return False
            
            self.output.print_success(f"Database connection verified: {self.database_path}")
            
            # Validate database schema
            try:
                existing_tables = self.database_client.get_existing_tables()
                DatabaseSetupService.validate_database_schema(existing_tables)
            except ValidationError as e:
                self.output.print_error(str(e))
                return False
            
            # Check for missing non-critical tables
            schema_valid, existing_tables, missing_tables = self.database_client.validate_database_schema()
            if missing_tables:
                self.output.print_warning(f"Missing tables: {', '.join(missing_tables)}")
                self.output.print_info("Creating missing tables for complete functionality...")
                
                # Create missing tables
                try:
                    success = self.database_client.create_missing_tables(missing_tables)
                    if success:
                        self.output.print_success(f"Successfully created {len(missing_tables)} missing tables")
                        # Verify tables were created
                        _, existing_after, remaining_missing = self.database_client.validate_database_schema()
                        if remaining_missing:
                            self.output.print_warning(f"Some tables still missing: {', '.join(remaining_missing)}")
                        else:
                            self.output.print_success("All required tables are now present")
                    else:
                        self.output.print_error("Failed to create missing tables")
                        return False
                except Exception as e:
                    self.output.print_error(f"Error creating missing tables: {e}")
                    return False
            
            # Re-check schema after potential table creation
            schema_valid, existing_tables, missing_tables = self.database_client.validate_database_schema()
            if missing_tables:
                # Check specifically for duplicate prevention tables
                duplicate_prevention_tables = ['processed_generations', 'processed_generation_cleanup_log']
                missing_dp_tables = [t for t in missing_tables if t in duplicate_prevention_tables]
                if missing_dp_tables:
                    self.output.print_warning(f"Duplicate prevention disabled: Missing {', '.join(missing_dp_tables)}")
                else:
                    self.output.print_info("All critical tables present - duplicate prevention enabled")
            
            # Create/update client organization
            org_data = DatabaseSetupService.prepare_organization_for_database(organization)
            success = self.database_client.insert_client_organization(org_data)
            
            if success:
                # Verify the record was created
                stored_org = self.database_client.get_client_organization(organization.client_id)
                if stored_org:
                    self.output.print_success("Client organization created successfully:")
                    self.output.print_info(f"ID: {stored_org['id']}")
                    self.output.print_info(f"Name: {stored_org['name']}")
                    self.output.print_info(f"Markup Rate: {stored_org['markup_rate']}x")
                    self.output.print_info(f"Active: {'Yes' if stored_org['is_active'] else 'No'}")
                    
                    # Final validation
                    self.output.print_success("Database setup completed successfully!")
                    self.output.print_info("Your mAI instance is now production-ready with:")
                    self.output.print_info("• Environment variables in .env file")
                    self.output.print_info("• Client organization in database")
                    self.output.print_info("• Usage tracking configuration")
                    self.output.print_info("• Duplicate prevention system")
                    self.output.print_info("• Generation ID tracking enabled")
                    
                    return True
                else:
                    self.output.print_error("Failed to verify client organization creation")
                    return False
            else:
                self.output.print_error("Failed to create client organization")
                return False
                
        except DatabaseError as e:
            self.output.print_error(str(e))
            return False
        except ValidationError as e:
            self.output.print_error(f"Validation error: {str(e)}")
            return False
        except Exception as e:
            self.output.print_error(f"Unexpected error during database setup: {str(e)}")
            return False


def main(args: Optional[list] = None) -> int:
    """
    Main entry point for the application.
    
    Args:
        args: Command-line arguments (uses sys.argv if None)
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    app = EnvironmentGeneratorApplication()
    return app.run(args)


if __name__ == "__main__":
    sys.exit(main())