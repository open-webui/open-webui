"""
Domain entities for mAI client environment generation.

These represent core business concepts and contain no infrastructure dependencies.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class ClientOrganization:
    """Represents a client organization with OpenRouter integration."""
    name: str
    spending_limit: str
    external_user: str
    api_key: str
    key_hash: Optional[str] = None
    markup_rate: float = 1.3
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    @property
    def client_id(self) -> str:
        """Get the unique identifier for this client."""
        return self.external_user

    def is_unlimited_spending(self) -> bool:
        """Check if organization has unlimited spending."""
        return self.spending_limit.lower() == "unlimited"

    def get_spending_limit_float(self) -> Optional[float]:
        """Get spending limit as float, or None if unlimited."""
        if self.is_unlimited_spending():
            return None
        try:
            return float(self.spending_limit)
        except ValueError:
            return None


@dataclass
class ApiKeyCreationRequest:
    """Request data for creating an OpenRouter API key."""
    organization_name: str
    spending_limit: str

    @property
    def key_name(self) -> str:
        """Generate standardized key name."""
        return f"mAI Client: {self.organization_name}"

    @property
    def key_label(self) -> str:
        """Generate standardized key label."""
        clean_name = (
            self.organization_name.lower()
            .replace(' ', '-')
            .replace('.', '')
            .replace(',', '')
        )
        return f"mai-{clean_name[:20]}"

    def to_api_payload(self) -> dict:
        """Convert to OpenRouter API payload."""
        payload = {
            "name": self.key_name,
            "label": self.key_label
        }
        
        if self.spending_limit.lower() != "unlimited":
            try:
                payload["limit"] = float(self.spending_limit)
            except ValueError:
                pass  # Skip invalid limits
        
        return payload


@dataclass
class EnvironmentConfiguration:
    """Complete environment configuration for a mAI client."""
    organization: ClientOrganization
    openrouter_host: str
    existing_variables: dict
    
    def get_openrouter_variables(self) -> dict:
        """Get OpenRouter-specific environment variables."""
        # Define the 12 mAI business models
        mai_models = [
            "anthropic/claude-sonnet-4",
            "google/gemini-2.5-flash",
            "google/gemini-2.5-pro",
            "deepseek/deepseek-chat-v3-0324",
            "anthropic/claude-3.7-sonnet",
            "google/gemini-2.5-flash-lite-preview-06-17",
            "openai/gpt-4.1",
            "x-ai/grok-4",
            "openai/gpt-4o-mini",
            "openai/o4-mini-high",
            "openai/o3",
            "openai/chatgpt-4o-latest"
        ]
        
        # Create OPENAI_API_CONFIGS JSON string
        openai_api_configs = {
            "0": {
                "enable": True,
                "model_ids": mai_models
            }
        }
        
        import json
        openai_api_configs_str = json.dumps(openai_api_configs, separators=(',', ':'))
        
        return {
            'OPENROUTER_API_KEY': self.organization.api_key,
            'OPENROUTER_HOST': self.openrouter_host,
            'OPENROUTER_EXTERNAL_USER': self.organization.external_user,
            'ORGANIZATION_NAME': self.organization.name,
            'SPENDING_LIMIT': self.organization.spending_limit,
            # OpenAI API Configuration
            'ENABLE_OPENAI_API': 'True',
            'OPENAI_API_BASE_URL': self.openrouter_host,
            'OPENAI_API_KEY': self.organization.api_key,
            # Model Access Control
            'ENABLE_MODEL_FILTER': 'True',
            'BYPASS_MODEL_ACCESS_CONTROL': 'False',
            # Model Configuration
            'OPENAI_API_CONFIGS': openai_api_configs_str,
        }

    def get_merged_variables(self) -> dict:
        """Get all environment variables merged together."""
        return {**self.existing_variables, **self.get_openrouter_variables()}