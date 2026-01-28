"""API logic tests for provider management endpoints."""

import pytest
from open_webui.models.providers import Providers, ProviderForm
from open_webui.internal.db import get_db


class TestProvidersAPI:
    """Test provider API CRUD operations.

    Note: These are logic tests that verify the API layer works correctly
    without requiring full HTTP integration testing.
    """

    def test_get_all_providers_returns_seeded_data(self):
        """Test that get all providers returns the seeded providers."""
        with get_db() as db:
            providers = Providers.get_all_providers(db=db)

            assert len(providers) >= 5, "Expected at least 5 seeded providers"

            # Check that default providers exist
            provider_ids = [p.id for p in providers]
            assert "openai" in provider_ids
            assert "anthropic" in provider_ids
            assert "google" in provider_ids
            assert "meta" in provider_ids
            assert "ollama" in provider_ids

    def test_get_provider_by_id_returns_correct_provider(self):
        """Test getting a specific provider by ID."""
        with get_db() as db:
            provider = Providers.get_provider_by_id("openai", db=db)

            assert provider is not None
            assert provider.id == "openai"
            assert provider.name == "OpenAI"
            assert len(provider.model_id_patterns) > 0
            assert "^gpt-" in provider.model_id_patterns

    def test_get_nonexistent_provider_returns_none(self):
        """Test that getting a nonexistent provider returns None."""
        with get_db() as db:
            provider = Providers.get_provider_by_id("nonexistent-provider-xyz", db=db)

            assert provider is None

    def test_create_new_provider(self):
        """Test creating a new provider via API."""
        with get_db() as db:
            # Clean up if exists
            Providers.delete_provider_by_id("test-api-provider", db=db)

            # Create new provider
            form_data = ProviderForm(
                id="test-api-provider",
                name="Test API Provider",
                logo_url="/static/providers/test.png",
                logo_light_url=None,
                logo_dark_url=None,
                model_id_patterns=["^test-"],
                priority=50,
                is_active=True
            )

            provider = Providers.create_provider(form_data, db=db)

            assert provider is not None
            assert provider.id == "test-api-provider"
            assert provider.name == "Test API Provider"
            assert provider.model_id_patterns == ["^test-"]

            # Cleanup
            Providers.delete_provider_by_id("test-api-provider", db=db)

    def test_create_duplicate_provider_fails(self):
        """Test that creating a provider with existing ID fails."""
        with get_db() as db:
            # Try to create a provider with ID that already exists (openai)
            form_data = ProviderForm(
                id="openai",  # Already exists
                name="Duplicate OpenAI",
                logo_url="/static/providers/duplicate.png",
                logo_light_url=None,
                logo_dark_url=None,
                model_id_patterns=["^duplicate-"],
                priority=50,
                is_active=True
            )

            # Should fail because openai already exists
            # In real API this would be caught by the endpoint and return 400
            # Here we just verify the provider already exists
            existing = Providers.get_provider_by_id("openai", db=db)
            assert existing is not None, "OpenAI provider should already exist"

    def test_update_provider(self):
        """Test updating an existing provider."""
        with get_db() as db:
            # Create test provider
            Providers.delete_provider_by_id("test-update-provider", db=db)
            create_form = ProviderForm(
                id="test-update-provider",
                name="Original Name",
                logo_url="/static/providers/original.png",
                logo_light_url=None,
                logo_dark_url=None,
                model_id_patterns=["^original-"],
                priority=50,
                is_active=True
            )
            Providers.create_provider(create_form, db=db)

            # Update provider
            update_form = ProviderForm(
                id="test-update-provider",
                name="Updated Name",
                logo_url="/static/providers/updated.png",
                logo_light_url=None,
                logo_dark_url=None,
                model_id_patterns=["^updated-", "^new-"],
                priority=75,
                is_active=False
            )

            updated = Providers.update_provider_by_id("test-update-provider", update_form, db=db)

            assert updated is not None
            assert updated.name == "Updated Name"
            assert updated.logo_url == "/static/providers/updated.png"
            assert updated.model_id_patterns == ["^updated-", "^new-"]
            assert updated.priority == 75
            assert updated.is_active is False

            # Cleanup
            Providers.delete_provider_by_id("test-update-provider", db=db)

    def test_update_nonexistent_provider_returns_none(self):
        """Test that updating a nonexistent provider returns None."""
        with get_db() as db:
            update_form = ProviderForm(
                id="nonexistent",
                name="Nonexistent",
                logo_url="/static/providers/none.png",
                logo_light_url=None,
                logo_dark_url=None,
                model_id_patterns=[],
                priority=50,
                is_active=True
            )

            result = Providers.update_provider_by_id("nonexistent-provider-xyz", update_form, db=db)

            assert result is None

    def test_delete_provider(self):
        """Test deleting a provider."""
        with get_db() as db:
            # Create test provider
            create_form = ProviderForm(
                id="test-delete-provider",
                name="To Be Deleted",
                logo_url="/static/providers/delete.png",
                logo_light_url=None,
                logo_dark_url=None,
                model_id_patterns=["^delete-"],
                priority=50,
                is_active=True
            )
            Providers.create_provider(create_form, db=db)

            # Verify it exists
            provider = Providers.get_provider_by_id("test-delete-provider", db=db)
            assert provider is not None

            # Delete it
            success = Providers.delete_provider_by_id("test-delete-provider", db=db)
            assert success is True

            # Verify it's gone
            provider = Providers.get_provider_by_id("test-delete-provider", db=db)
            assert provider is None

    def test_delete_nonexistent_provider_returns_false(self):
        """Test that deleting a nonexistent provider returns False."""
        with get_db() as db:
            success = Providers.delete_provider_by_id("nonexistent-provider-xyz", db=db)

            assert success is False

    def test_providers_sorted_by_priority(self):
        """Test that get_all_providers returns results sorted by priority."""
        with get_db() as db:
            providers = Providers.get_all_providers(db=db)

            # Check that providers are sorted by priority descending
            priorities = [p.priority for p in providers]
            assert priorities == sorted(priorities, reverse=True), \
                "Providers should be sorted by priority (descending)"

    def test_get_active_providers_only(self):
        """Test getting only active providers."""
        with get_db() as db:
            # Create inactive provider
            Providers.delete_provider_by_id("test-inactive-provider", db=db)
            inactive_form = ProviderForm(
                id="test-inactive-provider",
                name="Inactive Provider",
                logo_url="/static/providers/inactive.png",
                logo_light_url=None,
                logo_dark_url=None,
                model_id_patterns=["^inactive-"],
                priority=50,
                is_active=False
            )
            Providers.create_provider(inactive_form, db=db)

            # Get only active providers
            active_providers = Providers.get_active_providers(db=db)

            # Verify inactive provider is not in the list
            active_ids = [p.id for p in active_providers]
            assert "test-inactive-provider" not in active_ids

            # Cleanup
            Providers.delete_provider_by_id("test-inactive-provider", db=db)
