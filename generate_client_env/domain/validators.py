"""
Domain validation logic for client environment generation.

Contains business rules and validation logic independent of infrastructure.
"""

import re
from typing import List, Tuple


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class OrganizationValidator:
    """Validates organization-related data."""
    
    MIN_NAME_LENGTH = 3
    MAX_NAME_LENGTH = 100
    
    @classmethod
    def validate_name(cls, name: str) -> None:
        """Validate organization name."""
        if not name or not name.strip():
            raise ValidationError("Organization name cannot be empty")
        
        name = name.strip()
        if len(name) < cls.MIN_NAME_LENGTH:
            raise ValidationError(
                f"Organization name must be at least {cls.MIN_NAME_LENGTH} characters"
            )
        
        if len(name) > cls.MAX_NAME_LENGTH:
            raise ValidationError(
                f"Organization name cannot exceed {cls.MAX_NAME_LENGTH} characters"
            )

    @classmethod
    def validate_spending_limit(cls, limit: str) -> None:
        """Validate spending limit value."""
        if not limit or not limit.strip():
            raise ValidationError("Spending limit cannot be empty")
        
        limit = limit.strip().lower()
        if limit == "unlimited":
            return
        
        try:
            amount = float(limit)
            if amount <= 0:
                raise ValidationError("Spending limit must be positive")
        except ValueError:
            raise ValidationError(
                "Spending limit must be 'unlimited' or a positive number"
            )


class ApiKeyValidator:
    """Validates OpenRouter API keys."""
    
    OPENROUTER_KEY_PREFIX = "sk-or-"
    MIN_KEY_LENGTH = 20
    
    @classmethod
    def validate_provisioning_key(cls, key: str) -> None:
        """Validate OpenRouter provisioning key format."""
        if not key or not key.strip():
            raise ValidationError("API key cannot be empty")
        
        key = key.strip()
        if not key.startswith(cls.OPENROUTER_KEY_PREFIX):
            raise ValidationError(
                f"Invalid key format. OpenRouter keys start with '{cls.OPENROUTER_KEY_PREFIX}'"
            )
        
        if len(key) < cls.MIN_KEY_LENGTH:
            raise ValidationError(
                f"API key too short. Must be at least {cls.MIN_KEY_LENGTH} characters"
            )

    @classmethod
    def validate_generated_key(cls, key: str) -> None:
        """Validate generated API key."""
        if not key or not key.strip():
            raise ValidationError("Generated API key is empty")
        
        if len(key.strip()) < cls.MIN_KEY_LENGTH:
            raise ValidationError("Generated API key is too short")


class DatabaseValidator:
    """Validates database-related operations."""
    
    REQUIRED_TABLES = [
        'client_organizations',
        'client_user_daily_usage',
        'client_model_daily_usage',
        'processed_generations',
        'processed_generation_cleanup_log'
    ]
    
    @classmethod
    def validate_required_tables(cls, existing_tables: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate that all required tables exist.
        
        Returns:
            Tuple of (all_present: bool, missing_tables: List[str])
        """
        missing_tables = [
            table for table in cls.REQUIRED_TABLES 
            if table not in existing_tables
        ]
        return len(missing_tables) == 0, missing_tables

    @classmethod
    def validate_client_id(cls, client_id: str) -> None:
        """Validate client ID format."""
        if not client_id or not client_id.strip():
            raise ValidationError("Client ID cannot be empty")
        
        # Basic alphanumeric and underscore validation
        if not re.match(r'^[a-zA-Z0-9_]+$', client_id.strip()):
            raise ValidationError(
                "Client ID must contain only letters, numbers, and underscores"
            )


class EnvironmentValidator:
    """Validates environment configuration."""
    
    OPENROUTER_VARIABLES = [
        'OPENROUTER_API_KEY',
        'OPENROUTER_HOST', 
        'OPENROUTER_EXTERNAL_USER',
        'ORGANIZATION_NAME',
        'SPENDING_LIMIT'
    ]
    
    @classmethod
    def validate_required_variables(cls, variables: dict) -> None:
        """Validate that all required environment variables are present."""
        missing = [
            var for var in cls.OPENROUTER_VARIABLES 
            if var not in variables or not variables[var]
        ]
        
        if missing:
            raise ValidationError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

    @classmethod
    def validate_environment_file_content(cls, content: str) -> None:
        """Validate environment file content format."""
        if not content or not content.strip():
            raise ValidationError("Environment file content cannot be empty")
        
        # Check for basic .env format
        lines = content.strip().split('\n')
        has_config = False
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                has_config = True
                break
        
        if not has_config:
            raise ValidationError("Environment file must contain at least one configuration variable")