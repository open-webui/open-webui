"""
Test model logo detection with model-specific patterns.
"""

import pytest
from open_webui.models.providers import Providers, Provider, ProviderModel, ModelPattern
from unittest.mock import MagicMock


@pytest.fixture
def mock_providers():
    """Mock provider data matching migration 019."""
    return [
        ProviderModel(
            id="anthropic",
            name="Anthropic",
            logo_light_url="/providers/anthropic-light.svg",
            logo_dark_url="/providers/anthropic-dark.svg",
            logo_url="/providers/anthropic-light.svg",
            model_id_patterns=["^claude-"],
            model_patterns=[
                ModelPattern(
                    name="claude",
                    patterns=["^claude-3", "^claude-instant"],
                    logo_url="/providers/models/claude-light.svg",
                    logo_light_url="/providers/models/claude-light.svg",
                    logo_dark_url="/providers/models/claude-dark.svg",
                )
            ],
            priority=100,
            is_active=True,
            created_at=1,
            updated_at=1,
        ),
        ProviderModel(
            id="google",
            name="Google",
            logo_light_url="/providers/google-light.svg",
            logo_dark_url="/providers/google-dark.svg",
            logo_url="/providers/google-light.svg",
            model_id_patterns=["^gemini-", "^gemini:", "^palm-", "^gemma:", "^gemma[0-9]"],
            model_patterns=[
                ModelPattern(
                    name="gemini",
                    patterns=["^gemini-", "^gemini:"],
                    logo_url="/providers/models/gemini-light.svg",
                    logo_light_url="/providers/models/gemini-light.svg",
                    logo_dark_url="/providers/models/gemini-dark.svg",
                )
            ],
            priority=100,
            is_active=True,
            created_at=1,
            updated_at=1,
        ),
        ProviderModel(
            id="openai",
            name="OpenAI",
            logo_light_url="/providers/openai-light.svg",
            logo_dark_url="/providers/openai-dark.svg",
            logo_url="/providers/openai-light.svg",
            model_id_patterns=["^gpt-", "^o1-"],
            model_patterns=None,
            priority=100,
            is_active=True,
            created_at=1,
            updated_at=1,
        ),
        ProviderModel(
            id="ollama",
            name="Ollama",
            logo_light_url="/providers/ollama-light.svg",
            logo_dark_url="/providers/ollama-dark.svg",
            logo_url="/providers/ollama-light.svg",
            model_id_patterns=[],
            model_patterns=None,
            priority=10,
            is_active=True,
            created_at=1,
            updated_at=1,
        ),
    ]


@pytest.fixture
def mock_db(monkeypatch, mock_providers):
    """Mock Providers.get_active_providers to return test data."""
    monkeypatch.setattr(
        "open_webui.models.providers.Providers.get_active_providers",
        lambda db=None: mock_providers,
    )


class TestModelLogoDetection:
    """Test model-specific logo detection."""

    def test_claude_3_gets_model_specific_logo(self, mock_db):
        """Claude 3 models should get Claude-specific logo, not Anthropic."""
        result = Providers.detect_provider_logo("claude-3-opus", "anthropic", "light")
        assert result == "/providers/models/claude-light.svg"

        result = Providers.detect_provider_logo("claude-3-sonnet", "anthropic", "dark")
        assert result == "/providers/models/claude-dark.svg"

    def test_claude_instant_gets_model_specific_logo(self, mock_db):
        """Claude Instant should get Claude-specific logo."""
        result = Providers.detect_provider_logo("claude-instant-1", "anthropic", "light")
        assert result == "/providers/models/claude-light.svg"

    def test_claude_1_gets_provider_logo(self, mock_db):
        """Claude 1 should fall back to Anthropic provider logo."""
        result = Providers.detect_provider_logo("claude-1", "anthropic", "light")
        assert result == "/providers/anthropic-light.svg"

    def test_gemini_gets_model_specific_logo(self, mock_db):
        """Gemini models should get Gemini-specific logo."""
        result = Providers.detect_provider_logo("gemini-pro", "google", "light")
        assert result == "/providers/models/gemini-light.svg"

        result = Providers.detect_provider_logo("gemini:latest", "google", "dark")
        assert result == "/providers/models/gemini-dark.svg"

    def test_palm_gets_provider_logo(self, mock_db):
        """Palm models should get Google provider logo."""
        result = Providers.detect_provider_logo("palm-2", "google", "light")
        assert result == "/providers/google-light.svg"

    def test_gemma_gets_provider_logo(self, mock_db):
        """Gemma models should get Google provider logo (not model-specific)."""
        result = Providers.detect_provider_logo("gemma:7b", "google", "light")
        assert result == "/providers/google-light.svg"

    def test_gpt_4_gets_provider_logo(self, mock_db):
        """GPT-4 should get OpenAI provider logo (no model-specific)."""
        result = Providers.detect_provider_logo("gpt-4", "openai", "light")
        assert result == "/providers/openai-light.svg"

    def test_ollama_fallback(self, mock_db):
        """Unknown models with owned_by=ollama should get Ollama logo."""
        result = Providers.detect_provider_logo("llama-custom", "ollama", "light")
        assert result == "/providers/ollama-light.svg"

    def test_no_match_returns_none(self, mock_db):
        """Models with no pattern match should return None."""
        result = Providers.detect_provider_logo("unknown-model", "unknown", "light")
        assert result is None

    def test_priority_model_specific_over_provider(self, mock_db):
        """Model-specific patterns should have priority over provider patterns."""
        # claude-3 matches both model pattern and provider pattern
        # Should use model-specific logo
        result = Providers.detect_provider_logo("claude-3-opus", "anthropic", "light")
        assert "models/claude" in result
        assert "anthropic" not in result or "models" in result
