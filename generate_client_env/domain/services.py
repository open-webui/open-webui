"""
Domain services containing business logic for client environment generation.

These services orchestrate business operations without depending on infrastructure.
"""

import hashlib
from typing import Dict, Optional
from datetime import datetime

from .entities import ClientOrganization, ApiKeyCreationRequest, EnvironmentConfiguration
from .validators import (
    OrganizationValidator, 
    ApiKeyValidator, 
    DatabaseValidator,
    EnvironmentValidator,
    ValidationError
)


class OrganizationService:
    """Business logic for managing client organizations."""
    
    @staticmethod
    def create_organization(
        name: str, 
        spending_limit: str, 
        api_key: str,
        key_hash: Optional[str] = None
    ) -> ClientOrganization:
        """
        Create a new client organization with validation.
        
        Args:
            name: Organization name
            spending_limit: Spending limit ("unlimited" or numeric value)
            api_key: Generated OpenRouter API key
            key_hash: Optional key hash from OpenRouter
            
        Returns:
            ClientOrganization instance
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate inputs
        OrganizationValidator.validate_name(name)
        OrganizationValidator.validate_spending_limit(spending_limit)
        ApiKeyValidator.validate_generated_key(api_key)
        
        # Generate external user ID
        external_user = ExternalUserService.generate_external_user(name)
        
        return ClientOrganization(
            name=name.strip(),
            spending_limit=spending_limit.strip(),
            external_user=external_user,
            api_key=api_key.strip(),
            key_hash=key_hash
        )

    @staticmethod
    def validate_organization_data(organization: ClientOrganization) -> None:
        """Validate complete organization data."""
        OrganizationValidator.validate_name(organization.name)
        OrganizationValidator.validate_spending_limit(organization.spending_limit)
        ApiKeyValidator.validate_generated_key(organization.api_key)
        DatabaseValidator.validate_client_id(organization.external_user)


class ExternalUserService:
    """Business logic for external user ID generation."""
    
    @staticmethod
    def generate_external_user(organization_name: str) -> str:
        """
        Generate a consistent external user ID from organization name.
        
        Args:
            organization_name: Name of the organization
            
        Returns:
            External user ID in format: mai_client_{hash}
        """
        if not organization_name or not organization_name.strip():
            raise ValidationError("Organization name required for external user generation")
        
        # Create deterministic hash from organization name
        org_hash = hashlib.md5(organization_name.encode()).hexdigest()[:8]
        return f"mai_client_{org_hash}"


class ApiKeyRequestService:
    """Business logic for API key creation requests."""
    
    @staticmethod
    def create_key_request(
        organization_name: str, 
        spending_limit: str
    ) -> ApiKeyCreationRequest:
        """
        Create a validated API key creation request.
        
        Args:
            organization_name: Name of the organization
            spending_limit: Spending limit value
            
        Returns:
            ApiKeyCreationRequest instance
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate inputs
        OrganizationValidator.validate_name(organization_name)
        OrganizationValidator.validate_spending_limit(spending_limit)
        
        return ApiKeyCreationRequest(
            organization_name=organization_name.strip(),
            spending_limit=spending_limit.strip()
        )


class EnvironmentConfigurationService:
    """Business logic for environment configuration."""
    
    DEFAULT_OPENROUTER_HOST = "https://openrouter.ai/api/v1"
    
    @staticmethod
    def create_configuration(
        organization: ClientOrganization,
        existing_variables: Dict[str, str],
        openrouter_host: Optional[str] = None
    ) -> EnvironmentConfiguration:
        """
        Create environment configuration with validation.
        
        Args:
            organization: Client organization
            existing_variables: Existing environment variables
            openrouter_host: OpenRouter host URL (uses default if None)
            
        Returns:
            EnvironmentConfiguration instance
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate organization
        OrganizationService.validate_organization_data(organization)
        
        # Use default host if not provided
        if not openrouter_host:
            openrouter_host = EnvironmentConfigurationService.DEFAULT_OPENROUTER_HOST
        
        # Create configuration
        config = EnvironmentConfiguration(
            organization=organization,
            openrouter_host=openrouter_host,
            existing_variables=existing_variables or {}
        )
        
        # Validate the merged configuration
        merged_vars = config.get_merged_variables()
        EnvironmentValidator.validate_required_variables(merged_vars)
        
        return config


class EnvironmentFileService:
    """Business logic for environment file generation."""
    
    @staticmethod
    def generate_file_content(configuration: EnvironmentConfiguration) -> str:
        """Generate complete .env file content with proper organization."""
        # Generate all sections
        header = EnvironmentFileService._generate_header(configuration.organization)
        openrouter_section = EnvironmentFileService._generate_openrouter_section(configuration)
        app_sections = EnvironmentFileService._generate_app_sections(configuration)
        footer = EnvironmentFileService._generate_footer()
        
        # Combine all sections
        content = header + openrouter_section + app_sections + footer
        
        # Validate the generated content
        EnvironmentValidator.validate_environment_file_content(content)
        return content

    @staticmethod
    def _generate_header(organization) -> str:
        """Generate file header section."""
        return f"""# mAI Client Environment Configuration
# Generated on: {datetime.now().isoformat()}
# Organization: {organization.name}
# Spending Limit: {organization.spending_limit}

"""

    @staticmethod
    def _generate_openrouter_section(configuration: EnvironmentConfiguration) -> str:
        """Generate OpenRouter configuration section."""
        org = configuration.organization
        return f"""# =============================================================================
# OpenRouter Configuration (mAI Client-specific)
# =============================================================================
OPENROUTER_API_KEY={org.api_key}
OPENROUTER_HOST={configuration.openrouter_host}
OPENROUTER_EXTERNAL_USER={org.external_user}

# Organization Configuration  
ORGANIZATION_NAME={org.name}
SPENDING_LIMIT={org.spending_limit}

# Optional: Key management (for reference only)
# OPENROUTER_KEY_HASH={org.key_hash or 'N/A'}

# =============================================================================
# mAI Application Configuration (merged from existing .env)
# =============================================================================
"""

    @staticmethod
    def _generate_app_sections(configuration: EnvironmentConfiguration) -> str:
        """Generate application configuration sections."""
        sections = EnvironmentFileService._organize_variables(
            configuration.existing_variables, 
            configuration.get_openrouter_variables().keys()
        )
        
        content = ""
        for section_name, variables in sections.items():
            if variables:
                content += f"\n# {section_name}\n"
                content += EnvironmentFileService._format_variables(variables)
        
        return content

    @staticmethod
    def _format_variables(variables: dict) -> str:
        """Format variables for .env file."""
        content = ""
        for key, value in variables.items():
            # Quote values that might contain spaces
            if any(char in value for char in [' ', '\t', '\n']) and not value.startswith("'"):
                content += f"{key}='{value}'\n"
            else:
                content += f"{key}={value}\n"
        return content

    @staticmethod
    def _generate_footer() -> str:
        """Generate file footer section."""
        return f"""
# =============================================================================
# Docker Configuration Notes
# =============================================================================
# These values will be automatically mapped to the application
# No manual configuration required in the application code
# 
# The OpenRouter configuration above replaces manual API key entry in the UI
# Clients will NOT see the "OpenAI API Interface" settings section
"""

    @staticmethod
    def _organize_variables(
        existing_vars: Dict[str, str], 
        exclude_keys: set
    ) -> Dict[str, Dict[str, str]]:
        """Organize variables into logical sections."""
        sections = {
            "API Configuration": {},
            "CORS and Networking": {},
            "Application URLs": {},
            "Other Configuration": {}
        }
        
        for key, value in existing_vars.items():
            # Skip OpenRouter variables (already handled)
            if key in exclude_keys:
                continue
            
            # Categorize variables
            if key.startswith(('OLLAMA_', 'OPENAI_')):
                sections["API Configuration"][key] = value
            elif key.startswith(('CORS_', 'FORWARDED_')):
                sections["CORS and Networking"][key] = value
            elif key.startswith(('WEBUI_', 'BACKEND_')):
                sections["Application URLs"][key] = value
            else:
                sections["Other Configuration"][key] = value
        
        return sections


class DatabaseSetupService:
    """Business logic for database setup operations."""
    
    @staticmethod
    def validate_database_schema(existing_tables: list) -> None:
        """
        Validate that database schema is compatible.
        
        Args:
            existing_tables: List of existing table names
            
        Raises:
            ValidationError: If schema validation fails
        """
        all_present, missing_tables = DatabaseValidator.validate_required_tables(existing_tables)
        
        if missing_tables:
            # Determine severity based on which tables are missing
            critical_tables = ['client_organizations']
            missing_critical = [t for t in missing_tables if t in critical_tables]
            
            if missing_critical:
                raise ValidationError(
                    f"Critical database tables missing: {', '.join(missing_critical)}. "
                    "Database schema is incompatible."
                )
            
            # Non-critical tables missing - log warning but allow to continue
            # This will be handled by the caller
    
    @staticmethod
    def prepare_organization_for_database(organization: ClientOrganization) -> dict:
        """
        Prepare organization data for database insertion.
        
        Args:
            organization: Client organization
            
        Returns:
            Dictionary with database-ready organization data
        """
        DatabaseValidator.validate_client_id(organization.client_id)
        
        current_time = datetime.now().isoformat()
        
        return {
            'id': organization.client_id,
            'name': organization.name,
            'openrouter_api_key': organization.api_key,
            'markup_rate': organization.markup_rate,
            'is_active': 1 if organization.is_active else 0,
            'created_at': organization.created_at.isoformat() if organization.created_at else current_time,
            'updated_at': current_time
        }