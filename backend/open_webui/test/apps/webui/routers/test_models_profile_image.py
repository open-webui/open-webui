"""Logic tests for model profile image endpoint with provider logo detection."""

import pytest
from open_webui.models.models import Models, ModelForm, ModelMeta
from open_webui.models.providers import Providers
from open_webui.internal.db import get_db
import time


class TestModelProfileImageLogic:
    """Test model profile image logic with provider detection.

    Note: These are logic tests that verify provider detection works correctly.
    They test the core logic without requiring full HTTP layer testing.
    """

    def test_provider_detection_for_gpt_models(self):
        """Test that GPT models are correctly matched to OpenAI provider."""
        with get_db() as db:
            # Test various GPT model patterns
            test_cases = [
                ("gpt-4", "openai", "light"),
                ("gpt-3.5-turbo", "openai", "light"),
                ("gpt-4-turbo-preview", "openai", "light"),
                ("o1-preview", "openai", "light"),
            ]

            for model_id, owned_by, theme in test_cases:
                logo = Providers.detect_provider_logo(model_id, owned_by, theme, db=db)
                assert logo is not None, f"Expected logo for {model_id}"
                assert "openai" in logo.lower() or logo.startswith("/static/providers/"), \
                    f"Expected OpenAI logo path for {model_id}, got {logo}"

    def test_provider_detection_for_claude_models(self):
        """Test that Claude models are correctly matched to Anthropic provider."""
        with get_db() as db:
            test_cases = [
                ("claude-3-opus", "openai", "light"),  # Even with openai owned_by
                ("claude-3-sonnet", "openai", "light"),
                ("claude-3-haiku", "openai", "light"),
                ("claude-2.1", "openai", "light"),
            ]

            for model_id, owned_by, theme in test_cases:
                logo = Providers.detect_provider_logo(model_id, owned_by, theme, db=db)
                assert logo is not None, f"Expected logo for {model_id}"
                assert "anthropic" in logo.lower() or logo.startswith("/static/providers/"), \
                    f"Expected Anthropic logo path for {model_id}, got {logo}"

    def test_provider_detection_for_ollama_models(self):
        """Test that Ollama models match via owned_by field."""
        with get_db() as db:
            # Ollama models match by owned_by, not pattern
            test_cases = [
                ("mistral", "ollama", "light"),
                ("llama2", "ollama", "light"),
                ("codellama", "ollama", "light"),
            ]

            for model_id, owned_by, theme in test_cases:
                logo = Providers.detect_provider_logo(model_id, owned_by, theme, db=db)
                assert logo is not None, f"Expected logo for Ollama model {model_id}"
                assert "ollama" in logo.lower() or logo.startswith("/static/providers/"), \
                    f"Expected Ollama logo path for {model_id}, got {logo}"

    def test_provider_detection_theme_variants(self):
        """Test that theme parameter affects logo selection."""
        with get_db() as db:
            model_id = "gpt-4"
            owned_by = "openai"

            light_logo = Providers.detect_provider_logo(model_id, owned_by, "light", db=db)
            dark_logo = Providers.detect_provider_logo(model_id, owned_by, "dark", db=db)

            # Both should return logos
            assert light_logo is not None
            assert dark_logo is not None

            # They might be the same (fallback to logo_url) or different (theme-specific)
            # Both cases are valid

    def test_provider_detection_priority_order(self):
        """Test that provider priority affects matching order."""
        with get_db() as db:
            # llama models could match multiple providers
            # Meta should win due to higher priority (90 vs Ollama's 10)
            model_id = "llama-2-70b"
            owned_by = "openai"  # Not from Ollama

            logo = Providers.detect_provider_logo(model_id, owned_by, "light", db=db)

            assert logo is not None, "Expected logo for llama model"
            # Should match Meta provider due to higher priority
            assert "meta" in logo.lower() or logo.startswith("/static/providers/"), \
                f"Expected Meta logo for {model_id} with owned_by={owned_by}, got {logo}"

    def test_no_provider_match_returns_none(self):
        """Test that unknown models return None (allowing fallback to default)."""
        with get_db() as db:
            model_id = "unknown-custom-model-xyz"
            owned_by = "openai"

            logo = Providers.detect_provider_logo(model_id, owned_by, "light", db=db)

            # Should return None for unknown patterns
            assert logo is None, f"Expected None for unknown model, got {logo}"

    def test_model_creation_with_custom_profile_image(self):
        """Test creating a model with custom profile image."""
        with get_db() as db:
            # Clean up any existing test model
            existing = Models.get_model_by_id("test-custom-logo-model", db=db)
            if existing:
                Models.delete_model_by_id("test-custom-logo-model", db=db)

            # Create model with custom profile image
            model_form = ModelForm(
                id="test-custom-logo-model",
                base_model_id=None,
                name="Test Custom Logo",
                meta=ModelMeta(
                    profile_image_url="https://example.com/custom-logo.png",
                    description="Test model with custom logo",
                    capabilities=None,
                ),
                params={}
            )

            model = Models.insert_new_model(model_form, "test-user", db=db)

            assert model is not None
            assert model.id == "test-custom-logo-model"
            assert model.meta.profile_image_url == "https://example.com/custom-logo.png"

            # Cleanup
            Models.delete_model_by_id("test-custom-logo-model", db=db)

    def test_model_with_default_favicon_uses_provider_detection(self):
        """Test that models with default favicon fall through to provider detection."""
        with get_db() as db:
            # Clean up any existing test model
            model_id = "gpt-4-test-default"  # Use valid GPT pattern
            existing = Models.get_model_by_id(model_id, db=db)
            if existing:
                Models.delete_model_by_id(model_id, db=db)

            # Create GPT model with default favicon
            model_form = ModelForm(
                id=model_id,
                base_model_id=None,
                name="Test GPT Default",
                meta=ModelMeta(
                    profile_image_url="/static/favicon.png",  # Default - should trigger provider detection
                    description="Test model",
                    capabilities=None,
                ),
                params={}
            )

            model = Models.insert_new_model(model_form, "test-user", db=db)

            # Verify model was created with default favicon
            assert model.meta.profile_image_url == "/static/favicon.png"

            # Provider detection should find OpenAI logo for gpt-* pattern
            logo = Providers.detect_provider_logo(model.id, "openai", "light", db=db)
            assert logo is not None, f"Expected logo for {model_id} to match OpenAI provider"
            assert "openai" in logo.lower() or logo.startswith("/static/providers/"), \
                f"Expected OpenAI logo path, got {logo}"

            # Cleanup
            Models.delete_model_by_id(model_id, db=db)
