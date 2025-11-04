from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Iterable

import pytest
from pydantic import ValidationError

BACKEND_SRC = Path(__file__).resolve().parents[1]
SETTINGS_PATH = BACKEND_SRC / "open_webui" / "settings.py"

spec = importlib.util.spec_from_file_location("open_webui.settings", SETTINGS_PATH)
if spec is None or spec.loader is None:  # pragma: no cover - defensive guard
    raise RuntimeError("Unable to load open_webui.settings module")
settings = importlib.util.module_from_spec(spec)
sys.modules.setdefault("open_webui.settings", settings)
spec.loader.exec_module(settings)


RELEVANT_ENV_VARS: Iterable[str] = (
    "ENTERPRISE_MODE",
    "LOCAL_MODE_DISABLED",
    "RAG_EMBEDDING_ENGINE",
    "AUDIO_STT_ENGINE",
    "AUDIO_TTS_ENGINE",
    "VECTOR_DB",
    "BYPASS_EMBEDDING_AND_RETRIEVAL",
    "OPENAI_API_KEY",
    "RAG_OPENAI_API_KEY",
    "RAG_AZURE_OPENAI_API_KEY",
    "AUDIO_STT_OPENAI_API_KEY",
    "AUDIO_STT_AZURE_API_KEY",
    "AUDIO_TTS_OPENAI_API_KEY",
    "AUDIO_TTS_API_KEY",
    "DEEPGRAM_API_KEY",
    "DOCUMENT_INTELLIGENCE_ENDPOINT",
    "DOCUMENT_INTELLIGENCE_KEY",
    "DOCUMENT_INTELLIGENCE_MODEL_ID",
    "DOCUMENT_INTELLIGENCE_API_VERSION",
    "AWS_TEXTRACT_ACCESS_KEY_ID",
    "AWS_TEXTRACT_SECRET_ACCESS_KEY",
    "AWS_TEXTRACT_SESSION_TOKEN",
    "AWS_TEXTRACT_REGION",
    "OCR_ENGINE",
)


def _reset_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in RELEVANT_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    settings.get_settings.cache_clear()


def test_defaults_allow_local_features(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env(monkeypatch)

    cfg = settings.Settings()

    assert cfg.local_features_enabled is True
    assert cfg.rag_embedding_engine == "local"
    assert cfg.audio_stt_engine == "local"
    assert cfg.audio_tts_engine == "local"
    assert cfg.vector_db == "chroma"
    assert cfg.bypass_embedding_and_retrieval is False


def test_enterprise_defaults_force_saas(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env(monkeypatch)
    monkeypatch.setenv("ENTERPRISE_MODE", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("DOCUMENT_INTELLIGENCE_ENDPOINT", "https://example.com")
    monkeypatch.setenv("DOCUMENT_INTELLIGENCE_KEY", "azure-key")

    cfg = settings.Settings()

    assert cfg.local_features_enabled is False
    assert cfg.rag_embedding_engine == "openai"
    assert cfg.audio_stt_engine == "openai"
    assert cfg.audio_tts_engine == "openai"
    assert cfg.vector_db == "pgvector"
    assert cfg.bypass_embedding_and_retrieval is True


def test_local_mode_disabled_behaves_like_enterprise(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env(monkeypatch)
    monkeypatch.setenv("LOCAL_MODE_DISABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("DOCUMENT_INTELLIGENCE_ENDPOINT", "https://example.com")
    monkeypatch.setenv("DOCUMENT_INTELLIGENCE_KEY", "azure-key")

    cfg = settings.Settings()

    assert cfg.local_features_enabled is False
    assert cfg.rag_embedding_engine == "openai"
    assert cfg.audio_stt_engine == "openai"
    assert cfg.audio_tts_engine == "openai"
    assert cfg.vector_db == "pgvector"
    assert cfg.bypass_embedding_and_retrieval is True


def test_missing_openai_credentials_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env(monkeypatch)
    monkeypatch.setenv("ENTERPRISE_MODE", "true")

    with pytest.raises(ValidationError) as exc_info:
        settings.Settings()

    message = str(exc_info.value)
    assert "OPENAI_API_KEY" in message
    assert "RAG embedding engine" in message


def test_azure_tts_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_env(monkeypatch)
    monkeypatch.setenv("AUDIO_TTS_ENGINE", "azure")

    with pytest.raises(ValidationError) as exc_info:
        settings.Settings()

    assert "AUDIO_TTS_API_KEY" in str(exc_info.value)
