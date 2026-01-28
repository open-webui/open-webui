"""Unit tests for Provider model and provider logo detection."""

import pytest
import time
from open_webui.models.providers import (
    Providers,
    ProviderForm,
    ProviderModel,
)
from open_webui.internal.db import get_db


@pytest.fixture
def test_provider_form():
    """Create a test provider form."""
    return ProviderForm(
        id="test_provider",
        name="Test Provider",
        logo_url="/static/providers/test.png",
        logo_light_url="/static/providers/test-light.png",
        logo_dark_url="/static/providers/test-dark.png",
        model_id_patterns=["^test-"],
        priority=50,
        is_active=True
    )


class TestProviderCRUD:
    """Test Provider CRUD operations."""

    def test_create_provider(self, test_provider_form):
        """Test creating a new provider."""
        with get_db() as db:
            # Clean up any existing test provider first
            Providers.delete_provider_by_id("test_provider", db=db)

            provider = Providers.create_provider(test_provider_form, db=db)

            assert provider is not None
            assert provider.id == "test_provider"
            assert provider.name == "Test Provider"
            assert provider.logo_url == "/static/providers/test.png"
            assert provider.model_id_patterns == ["^test-"]
            assert provider.priority == 50
            assert provider.is_active is True
            assert provider.created_at > 0
            assert provider.updated_at > 0

            # Cleanup
            Providers.delete_provider_by_id("test_provider", db=db)

    def test_get_provider_by_id(self, test_provider_form):
        """Test retrieving a provider by ID."""
        with get_db() as db:
            # Clean up any existing test provider first
            Providers.delete_provider_by_id("test_provider", db=db)

            # Create provider
            created = Providers.create_provider(test_provider_form, db=db)

            # Retrieve it
            provider = Providers.get_provider_by_id("test_provider", db=db)

            assert provider is not None
            assert provider.id == created.id
            assert provider.name == created.name

            # Cleanup
            Providers.delete_provider_by_id("test_provider", db=db)

    def test_get_provider_by_id_not_found(self):
        """Test retrieving a non-existent provider."""
        with get_db() as db:
            provider = Providers.get_provider_by_id("nonexistent", db=db)
            assert provider is None

    def test_update_provider(self, test_provider_form):
        """Test updating a provider."""
        with get_db() as db:
            # Clean up any existing test provider first
            Providers.delete_provider_by_id("test_provider", db=db)

            # Create provider
            Providers.create_provider(test_provider_form, db=db)

            # Wait 1 second to ensure updated_at will be different
            time.sleep(1)

            # Update it
            updated_form = ProviderForm(
                id="test_provider",
                name="Updated Test Provider",
                logo_url="/static/providers/updated.png",
                model_id_patterns=["^test-", "^updated-"],
                priority=75,
                is_active=False
            )

            updated = Providers.update_provider_by_id("test_provider", updated_form, db=db)

            assert updated is not None
            assert updated.name == "Updated Test Provider"
            assert updated.logo_url == "/static/providers/updated.png"
            assert updated.model_id_patterns == ["^test-", "^updated-"]
            assert updated.priority == 75
            assert updated.is_active is False
            assert updated.updated_at > updated.created_at

            # Cleanup
            Providers.delete_provider_by_id("test_provider", db=db)

    def test_delete_provider(self, test_provider_form):
        """Test deleting a provider."""
        with get_db() as db:
            # Clean up any existing test provider first
            Providers.delete_provider_by_id("test_provider", db=db)

            # Create provider
            Providers.create_provider(test_provider_form, db=db)

            # Delete it
            success = Providers.delete_provider_by_id("test_provider", db=db)
            assert success is True

            # Verify deletion
            provider = Providers.get_provider_by_id("test_provider", db=db)
            assert provider is None

    def test_delete_nonexistent_provider(self):
        """Test deleting a non-existent provider."""
        with get_db() as db:
            success = Providers.delete_provider_by_id("nonexistent", db=db)
            assert success is False

    def test_get_all_providers(self):
        """Test retrieving all providers."""
        with get_db() as db:
            providers = Providers.get_all_providers(db=db)

            # Should have default providers from migration
            assert len(providers) >= 5
            provider_ids = [p.id for p in providers]
            assert "openai" in provider_ids
            assert "anthropic" in provider_ids
            assert "google" in provider_ids
            assert "meta" in provider_ids
            assert "ollama" in provider_ids

    def test_get_active_providers(self, test_provider_form):
        """Test retrieving only active providers."""
        with get_db() as db:
            # Create inactive provider
            inactive_form = ProviderForm(
                id="inactive_provider",
                name="Inactive Provider",
                logo_url="/static/providers/inactive.png",
                model_id_patterns=["^inactive-"],
                priority=50,
                is_active=False
            )
            Providers.create_provider(inactive_form, db=db)

            # Get active providers
            active_providers = Providers.get_active_providers(db=db)
            active_ids = [p.id for p in active_providers]

            # Should not include inactive provider
            assert "inactive_provider" not in active_ids

            # Should include default active providers
            assert "openai" in active_ids

            # Cleanup
            Providers.delete_provider_by_id("inactive_provider", db=db)

    def test_providers_sorted_by_priority(self, test_provider_form):
        """Test that providers are sorted by priority descending."""
        with get_db() as db:
            # Create providers with different priorities
            high_priority = ProviderForm(
                id="high_priority",
                name="High Priority",
                logo_url="/static/test.png",
                model_id_patterns=["^high-"],
                priority=200,
                is_active=True
            )
            low_priority = ProviderForm(
                id="low_priority",
                name="Low Priority",
                logo_url="/static/test.png",
                model_id_patterns=["^low-"],
                priority=5,
                is_active=True
            )

            Providers.create_provider(high_priority, db=db)
            Providers.create_provider(low_priority, db=db)

            providers = Providers.get_active_providers(db=db)

            # Find positions
            high_idx = next(i for i, p in enumerate(providers) if p.id == "high_priority")
            low_idx = next(i for i, p in enumerate(providers) if p.id == "low_priority")

            # High priority should come before low priority
            assert high_idx < low_idx

            # Cleanup
            Providers.delete_provider_by_id("high_priority", db=db)
            Providers.delete_provider_by_id("low_priority", db=db)


class TestProviderLogoDetection:
    """Test provider logo detection logic."""

    def test_detect_openai_logo_gpt(self):
        """Test OpenAI logo detection for gpt- models."""
        with get_db() as db:
            logo = Providers.detect_provider_logo("gpt-4", "openai", "light", db=db)
            assert logo is not None
            assert "openai" in logo.lower()

    def test_detect_openai_logo_o1(self):
        """Test OpenAI logo detection for o1- models."""
        with get_db() as db:
            logo = Providers.detect_provider_logo("o1-preview", "openai", "light", db=db)
            assert logo is not None
            assert "openai" in logo.lower()

    def test_detect_anthropic_logo(self):
        """Test Anthropic logo detection for claude- models."""
        with get_db() as db:
            logo = Providers.detect_provider_logo("claude-3-opus", "openai", "light", db=db)
            assert logo is not None
            assert "anthropic" in logo.lower()

    def test_detect_google_logo_gemini(self):
        """Test Google logo detection for gemini- models."""
        with get_db() as db:
            logo = Providers.detect_provider_logo("gemini-pro", "openai", "light", db=db)
            assert logo is not None
            assert "google" in logo.lower()

    def test_detect_meta_logo_llama(self):
        """Test Meta logo detection for llama- models."""
        with get_db() as db:
            logo = Providers.detect_provider_logo("llama-2-70b", "openai", "light", db=db)
            assert logo is not None
            assert "meta" in logo.lower()

    def test_detect_ollama_logo_by_owned_by(self):
        """Test Ollama logo detection via owned_by field."""
        with get_db() as db:
            logo = Providers.detect_provider_logo("mistral", "ollama", "light", db=db)
            assert logo is not None
            assert "ollama" in logo.lower()

    def test_detect_no_match(self):
        """Test that unmatched models return None."""
        with get_db() as db:
            logo = Providers.detect_provider_logo("unknown-model-xyz", "openai", "light", db=db)
            assert logo is None

    def test_pattern_case_insensitive(self):
        """Test that pattern matching is case-insensitive."""
        with get_db() as db:
            logo_lower = Providers.detect_provider_logo("gpt-4", "openai", "light", db=db)
            logo_upper = Providers.detect_provider_logo("GPT-4", "openai", "light", db=db)
            logo_mixed = Providers.detect_provider_logo("GpT-4", "openai", "light", db=db)

            assert logo_lower == logo_upper == logo_mixed
            assert logo_lower is not None

    def test_priority_ordering(self):
        """Test that higher priority providers are checked first."""
        with get_db() as db:
            # Create two providers with overlapping patterns
            high_priority = ProviderForm(
                id="high_priority_test",
                name="High Priority Test",
                logo_url="/static/providers/high.png",
                model_id_patterns=["^test-"],
                priority=200,
                is_active=True
            )
            low_priority = ProviderForm(
                id="low_priority_test",
                name="Low Priority Test",
                logo_url="/static/providers/low.png",
                model_id_patterns=["^test-"],
                priority=5,
                is_active=True
            )

            Providers.create_provider(high_priority, db=db)
            Providers.create_provider(low_priority, db=db)

            # Should match high priority provider
            logo = Providers.detect_provider_logo("test-model", "openai", "light", db=db)
            assert logo == "/static/providers/high.png"

            # Cleanup
            Providers.delete_provider_by_id("high_priority_test", db=db)
            Providers.delete_provider_by_id("low_priority_test", db=db)


class TestProviderThemeSupport:
    """Test light/dark theme logo selection."""

    def test_light_theme_logo(self):
        """Test that light theme logo is selected when available."""
        with get_db() as db:
            form = ProviderForm(
                id="theme_test",
                name="Theme Test",
                logo_url="/static/providers/default.png",
                logo_light_url="/static/providers/light.png",
                logo_dark_url="/static/providers/dark.png",
                model_id_patterns=["^theme-"],
                priority=50,
                is_active=True
            )
            Providers.create_provider(form, db=db)

            logo = Providers.detect_provider_logo("theme-model", "openai", "light", db=db)
            assert logo == "/static/providers/light.png"

            # Cleanup
            Providers.delete_provider_by_id("theme_test", db=db)

    def test_dark_theme_logo(self):
        """Test that dark theme logo is selected when available."""
        with get_db() as db:
            form = ProviderForm(
                id="theme_test",
                name="Theme Test",
                logo_url="/static/providers/default.png",
                logo_light_url="/static/providers/light.png",
                logo_dark_url="/static/providers/dark.png",
                model_id_patterns=["^theme-"],
                priority=50,
                is_active=True
            )
            Providers.create_provider(form, db=db)

            logo = Providers.detect_provider_logo("theme-model", "openai", "dark", db=db)
            assert logo == "/static/providers/dark.png"

            # Cleanup
            Providers.delete_provider_by_id("theme_test", db=db)

    def test_fallback_to_default_logo(self):
        """Test fallback to default logo when theme-specific logo not available."""
        with get_db() as db:
            form = ProviderForm(
                id="fallback_test",
                name="Fallback Test",
                logo_url="/static/providers/default.png",
                logo_light_url=None,
                logo_dark_url=None,
                model_id_patterns=["^fallback-"],
                priority=50,
                is_active=True
            )
            Providers.create_provider(form, db=db)

            light_logo = Providers.detect_provider_logo("fallback-model", "openai", "light", db=db)
            dark_logo = Providers.detect_provider_logo("fallback-model", "openai", "dark", db=db)

            # Both should return default logo
            assert light_logo == "/static/providers/default.png"
            assert dark_logo == "/static/providers/default.png"

            # Cleanup
            Providers.delete_provider_by_id("fallback_test", db=db)


class TestProviderEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_regex_pattern(self):
        """Test that invalid regex patterns are skipped."""
        with get_db() as db:
            form = ProviderForm(
                id="invalid_regex_test",
                name="Invalid Regex Test",
                logo_url="/static/providers/test.png",
                model_id_patterns=["[invalid(regex", "^valid-"],
                priority=50,
                is_active=True
            )
            Providers.create_provider(form, db=db)

            # Should skip invalid pattern and match valid one
            logo = Providers.detect_provider_logo("valid-model", "openai", "light", db=db)
            assert logo == "/static/providers/test.png"

            # Cleanup
            Providers.delete_provider_by_id("invalid_regex_test", db=db)

    def test_empty_pattern_list(self):
        """Test provider with empty pattern list (like Ollama)."""
        with get_db() as db:
            # Ollama has empty pattern list and relies on owned_by
            logo = Providers.detect_provider_logo("any-model", "ollama", "light", db=db)
            assert logo is not None
            assert "ollama" in logo.lower()

    def test_multiple_patterns(self):
        """Test provider with multiple model ID patterns."""
        with get_db() as db:
            form = ProviderForm(
                id="multi_pattern_test",
                name="Multi Pattern Test",
                logo_url="/static/providers/multi.png",
                model_id_patterns=["^model1-", "^model2-", "^model3-"],
                priority=50,
                is_active=True
            )
            Providers.create_provider(form, db=db)

            # All patterns should match
            logo1 = Providers.detect_provider_logo("model1-test", "openai", "light", db=db)
            logo2 = Providers.detect_provider_logo("model2-test", "openai", "light", db=db)
            logo3 = Providers.detect_provider_logo("model3-test", "openai", "light", db=db)

            assert logo1 == logo2 == logo3 == "/static/providers/multi.png"

            # Cleanup
            Providers.delete_provider_by_id("multi_pattern_test", db=db)
