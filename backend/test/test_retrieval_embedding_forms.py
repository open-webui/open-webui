"""
Regression test for issue #27729:
RAG Embedding settings save fails with 422 when Ollama/Azure OpenAI config fields are null.

The frontend sends null for unused provider config fields (e.g. ollama_config.key=null
when using OpenAI embedding engine). The Pydantic forms must accept nullable fields
to avoid 422 Unprocessable Content responses.

This test replicates the exact Pydantic model definitions from
backend/open_webui/routers/retrieval.py to validate that nullable fields are accepted.
"""

import pytest
from pydantic import BaseModel, ValidationError


# --- Replicated model definitions from retrieval.py (must stay in sync) ---

class OpenAIConfigForm(BaseModel):
    url: str | None = None
    key: str | None = None


class OllamaConfigForm(BaseModel):
    url: str | None = None
    key: str | None = None


class AzureOpenAIConfigForm(BaseModel):
    url: str | None = None
    key: str | None = None
    version: str | None = None


class EmbeddingModelUpdateForm(BaseModel):
    openai_config: OpenAIConfigForm | None = None
    ollama_config: OllamaConfigForm | None = None
    azure_openai_config: AzureOpenAIConfigForm | None = None
    RAG_EMBEDDING_ENGINE: str
    RAG_EMBEDDING_MODEL: str
    RAG_EMBEDDING_BATCH_SIZE: int | None = 1
    ENABLE_ASYNC_EMBEDDING: bool | None = True
    RAG_EMBEDDING_CONCURRENT_REQUESTS: int | None = 0


# --- Tests ---

class TestOpenAIConfigForm:
    def test_accepts_all_null(self):
        form = OpenAIConfigForm(url=None, key=None)
        assert form.url is None
        assert form.key is None

    def test_accepts_partial_null(self):
        form = OpenAIConfigForm(url="https://api.openai.com", key=None)
        assert form.url == "https://api.openai.com"
        assert form.key is None

    def test_accepts_valid_values(self):
        form = OpenAIConfigForm(url="https://api.openai.com", key="sk-test")
        assert form.url == "https://api.openai.com"
        assert form.key == "sk-test"

    def test_accepts_empty_body(self):
        form = OpenAIConfigForm()
        assert form.url is None
        assert form.key is None


class TestOllamaConfigForm:
    def test_accepts_all_null(self):
        """Regression for #27729: ollama_config with null fields caused 422."""
        form = OllamaConfigForm(url=None, key=None)
        assert form.url is None
        assert form.key is None

    def test_accepts_partial_null(self):
        form = OllamaConfigForm(url="http://localhost:11434", key=None)
        assert form.url == "http://localhost:11434"
        assert form.key is None

    def test_accepts_valid_values(self):
        form = OllamaConfigForm(url="http://localhost:11434", key="ollama-key")
        assert form.url == "http://localhost:11434"
        assert form.key == "ollama-key"


class TestAzureOpenAIConfigForm:
    def test_accepts_all_null(self):
        """Regression for #27729: azure_openai_config with null fields caused 422."""
        form = AzureOpenAIConfigForm(url=None, key=None, version=None)
        assert form.url is None
        assert form.key is None
        assert form.version is None

    def test_accepts_partial_null(self):
        form = AzureOpenAIConfigForm(url="https://my.openai.azure.com", key=None, version=None)
        assert form.url == "https://my.openai.azure.com"
        assert form.key is None

    def test_accepts_valid_values(self):
        form = AzureOpenAIConfigForm(
            url="https://my.openai.azure.com", key="azure-key", version="2024-02-01"
        )
        assert form.url == "https://my.openai.azure.com"
        assert form.key == "azure-key"
        assert form.version == "2024-02-01"


class TestEmbeddingModelUpdateForm:
    def test_issue_27729_exact_payload(self):
        """
        Reproduce the exact payload from issue #27729 that previously caused 422.
        User selects OpenAI engine, leaves Ollama/Azure fields empty.
        """
        payload = {
            "RAG_EMBEDDING_ENGINE": "openai",
            "RAG_EMBEDDING_MODEL": "openai/text-embedding-3-large",
            "RAG_EMBEDDING_BATCH_SIZE": 1,
            "ENABLE_ASYNC_EMBEDDING": True,
            "RAG_EMBEDDING_CONCURRENT_REQUESTS": 0,
            "openai_config": {
                "url": "https://openrouter.ai/api/v1",
                "key": "sk-or-v1-fake-key",
            },
            "ollama_config": {
                "url": "http://host.docker.internal:11434",
                "key": None,
            },
            "azure_openai_config": {
                "url": None,
                "key": None,
                "version": None,
            },
        }
        # Must NOT raise ValidationError
        form = EmbeddingModelUpdateForm(**payload)
        assert form.RAG_EMBEDDING_ENGINE == "openai"
        assert form.ollama_config.key is None
        assert form.azure_openai_config.url is None
        assert form.azure_openai_config.key is None
        assert form.azure_openai_config.version is None

    def test_all_null_provider_configs(self):
        """All provider configs can be None entirely."""
        payload = {
            "RAG_EMBEDDING_ENGINE": "openai",
            "RAG_EMBEDDING_MODEL": "text-embedding-3-small",
            "openai_config": None,
            "ollama_config": None,
            "azure_openai_config": None,
        }
        form = EmbeddingModelUpdateForm(**payload)
        assert form.openai_config is None
        assert form.ollama_config is None
        assert form.azure_openai_config is None

    def test_ollama_engine_with_null_openai_and_azure(self):
        """When using Ollama engine, OpenAI and Azure configs may have null fields."""
        payload = {
            "RAG_EMBEDDING_ENGINE": "ollama",
            "RAG_EMBEDDING_MODEL": "nomic-embed-text",
            "openai_config": {"url": None, "key": None},
            "ollama_config": {"url": "http://localhost:11434", "key": None},
            "azure_openai_config": {"url": None, "key": None, "version": None},
        }
        form = EmbeddingModelUpdateForm(**payload)
        assert form.ollama_config.url == "http://localhost:11434"
        assert form.openai_config.url is None
