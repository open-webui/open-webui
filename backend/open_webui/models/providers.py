from open_webui.internal.db import Base, JSONField, get_db
from pydantic import BaseModel, ConfigDict
from typing import Optional
from sqlalchemy import Column, String, Text, Integer, Boolean, BigInteger
import time
import re
import logging

log = logging.getLogger(__name__)


class Provider(Base):
    __tablename__ = "provider"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    logo_light_url = Column(Text, nullable=True)
    logo_dark_url = Column(Text, nullable=True)
    logo_url = Column(Text, nullable=True)
    model_id_patterns = Column(JSONField, nullable=False)
    model_patterns = Column(JSONField, nullable=True)  # Model-specific logo overrides
    priority = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)


class ModelPattern(BaseModel):
    """Model-specific logo configuration within a provider."""
    name: str
    patterns: list[str]
    logo_url: Optional[str] = None
    logo_light_url: Optional[str] = None
    logo_dark_url: Optional[str] = None


class ProviderModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    logo_light_url: Optional[str] = None
    logo_dark_url: Optional[str] = None
    logo_url: Optional[str] = None
    model_id_patterns: list[str]
    model_patterns: Optional[list[ModelPattern]] = None
    priority: int = 0
    is_active: bool = True
    created_at: int
    updated_at: int


class ProviderForm(BaseModel):
    id: str
    name: str
    logo_light_url: Optional[str] = None
    logo_dark_url: Optional[str] = None
    logo_url: Optional[str] = None
    model_id_patterns: list[str]
    model_patterns: Optional[list[ModelPattern]] = None
    priority: int = 0
    is_active: bool = True


class Providers:
    @staticmethod
    def get_all_providers(db=None):
        """Get all providers sorted by priority descending."""
        if db is None:
            with get_db() as db:
                return Providers.get_all_providers(db)

        return [
            ProviderModel.model_validate(provider)
            for provider in db.query(Provider)
            .order_by(Provider.priority.desc(), Provider.id)
            .all()
        ]

    @staticmethod
    def get_active_providers(db=None):
        """Get all active providers sorted by priority descending."""
        if db is None:
            with get_db() as db:
                return Providers.get_active_providers(db)

        return [
            ProviderModel.model_validate(provider)
            for provider in db.query(Provider)
            .filter(Provider.is_active == True)
            .order_by(Provider.priority.desc(), Provider.id)
            .all()
        ]

    @staticmethod
    def get_provider_by_id(provider_id: str, db=None):
        """Get provider by ID."""
        if db is None:
            with get_db() as db:
                return Providers.get_provider_by_id(provider_id, db)

        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        return ProviderModel.model_validate(provider) if provider else None

    @staticmethod
    def create_provider(form_data: ProviderForm, db=None):
        """Create new provider."""
        if db is None:
            with get_db() as db:
                return Providers.create_provider(form_data, db)

        provider = Provider(
            **form_data.model_dump(),
            created_at=int(time.time()),
            updated_at=int(time.time()),
        )
        db.add(provider)
        db.commit()
        db.refresh(provider)
        return ProviderModel.model_validate(provider)

    @staticmethod
    def update_provider_by_id(provider_id: str, form_data: ProviderForm, db=None):
        """Update provider."""
        if db is None:
            with get_db() as db:
                return Providers.update_provider_by_id(provider_id, form_data, db)

        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if not provider:
            return None

        for key, value in form_data.model_dump().items():
            setattr(provider, key, value)

        provider.updated_at = int(time.time())
        db.commit()
        db.refresh(provider)
        return ProviderModel.model_validate(provider)

    @staticmethod
    def delete_provider_by_id(provider_id: str, db=None):
        """Delete provider."""
        if db is None:
            with get_db() as db:
                return Providers.delete_provider_by_id(provider_id, db)

        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if provider:
            db.delete(provider)
            db.commit()
            return True
        return False

    @staticmethod
    def detect_provider_logo(model_id: str, owned_by: str, theme: str = "light", db=None):
        """
        Detect provider logo based on model ID patterns with model-specific overrides.

        Priority hierarchy:
        1. Model-specific patterns (e.g., "claude" within Anthropic)
        2. Provider-level patterns (e.g., all Claude models → Anthropic)
        3. Ollama fallback

        Args:
            model_id: The model identifier (e.g., "gpt-4", "claude-3-opus")
            owned_by: The model's owned_by field ("ollama", "openai", etc.)
            theme: "light" or "dark"
            db: Database session

        Returns:
            Logo URL string or None if no match
        """
        if db is None:
            with get_db() as db:
                return Providers.detect_provider_logo(model_id, owned_by, theme, db)

        providers = Providers.get_active_providers(db)

        # First pass: Check model-specific patterns (highest priority)
        for provider in providers:
            if provider.id == "ollama":
                continue

            if provider.model_patterns:
                for model_pattern in provider.model_patterns:
                    for pattern in model_pattern.patterns:
                        try:
                            if re.match(pattern, model_id, re.IGNORECASE):
                                log.debug(f"Model '{model_id}' matched model-specific pattern '{pattern}' in provider '{provider.id}'")
                                return Providers._get_model_logo_for_theme(model_pattern, theme)
                        except re.error as e:
                            log.warning(f"Invalid regex pattern '{pattern}' for model '{model_pattern.name}': {e}")
                            continue

        # Second pass: Check provider-level patterns
        for provider in providers:
            if provider.id == "ollama":
                continue

            for pattern in provider.model_id_patterns:
                try:
                    if re.match(pattern, model_id, re.IGNORECASE):
                        log.debug(f"Model '{model_id}' matched provider '{provider.id}' with pattern '{pattern}'")
                        return Providers._get_logo_for_theme(provider, theme)
                except re.error as e:
                    log.warning(f"Invalid regex pattern '{pattern}' for provider '{provider.id}': {e}")
                    continue

        # Third pass: Ollama fallback for models served via Ollama with no pattern match
        if owned_by == "ollama":
            ollama_provider = next((p for p in providers if p.id == "ollama"), None)
            if ollama_provider:
                log.debug(f"Model '{model_id}' using Ollama fallback logo (owned_by='ollama')")
                return Providers._get_logo_for_theme(ollama_provider, theme)

        return None

    @staticmethod
    def _get_logo_for_theme(provider: ProviderModel, theme: str) -> Optional[str]:
        """Get appropriate logo URL for given theme."""
        if theme == "dark" and provider.logo_dark_url:
            return provider.logo_dark_url
        elif theme == "light" and provider.logo_light_url:
            return provider.logo_light_url
        else:
            return provider.logo_url

    @staticmethod
    def _get_model_logo_for_theme(model_pattern: ModelPattern, theme: str) -> Optional[str]:
        """Get appropriate model-specific logo URL for given theme."""
        if theme == "dark" and model_pattern.logo_dark_url:
            return model_pattern.logo_dark_url
        elif theme == "light" and model_pattern.logo_light_url:
            return model_pattern.logo_light_url
        else:
            return model_pattern.logo_url
