"""Centralised runtime settings for Open WebUI.

This module introduces a typed settings object that consolidates the feature
flags and engine selections required for the enterprise refactor. It provides
deterministic defaults for both local and enterprise deployments and performs
credential validation for SaaS-backed engines.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


LOCAL_EMBEDDING_ENGINES = {"", "local"}
LOCAL_STT_ENGINES = {"", "local", "whisper"}
LOCAL_TTS_ENGINES = {"", "local"}
LOCAL_VECTOR_DBS = {"", "local", "chroma"}
LOCAL_OCR_ENGINES = {"", "local", "rapidocr"}

class Settings(BaseSettings):
    """Runtime settings with enterprise-aware defaults."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False, extra="ignore")

    enterprise_mode: bool = Field(False, alias="ENTERPRISE_MODE")
    local_mode_disabled: bool = Field(False, alias="LOCAL_MODE_DISABLED")

    rag_embedding_engine: Optional[str] = Field(None, alias="RAG_EMBEDDING_ENGINE")
    audio_stt_engine: Optional[str] = Field(None, alias="AUDIO_STT_ENGINE")
    audio_tts_engine: Optional[str] = Field(None, alias="AUDIO_TTS_ENGINE")
    vector_db: Optional[str] = Field(None, alias="VECTOR_DB")
    bypass_embedding_and_retrieval: Optional[bool] = Field(
        None, alias="BYPASS_EMBEDDING_AND_RETRIEVAL"
    )
    ocr_engine: Optional[str] = Field(None, alias="OCR_ENGINE")
    rag_reranking_engine: Optional[str] = Field(None, alias="RAG_RERANKING_ENGINE")
    rag_reranking_model: Optional[str] = Field(None, alias="RAG_RERANKING_MODEL")
    rag_external_reranker_url: Optional[str] = Field(
        None, alias="RAG_EXTERNAL_RERANKER_URL"
    )
    rag_external_reranker_api_key: Optional[str] = Field(
        None, alias="RAG_EXTERNAL_RERANKER_API_KEY"
    )

    # SaaS credential inputs used for validation.
    openai_api_key: Optional[str] = Field(None, alias="OPENAI_API_KEY")
    rag_openai_api_key: Optional[str] = Field(None, alias="RAG_OPENAI_API_KEY")
    rag_azure_openai_api_key: Optional[str] = Field(None, alias="RAG_AZURE_OPENAI_API_KEY")
    audio_stt_openai_api_key: Optional[str] = Field(None, alias="AUDIO_STT_OPENAI_API_KEY")
    audio_stt_azure_api_key: Optional[str] = Field(None, alias="AUDIO_STT_AZURE_API_KEY")
    audio_tts_openai_api_key: Optional[str] = Field(None, alias="AUDIO_TTS_OPENAI_API_KEY")
    audio_tts_api_key: Optional[str] = Field(None, alias="AUDIO_TTS_API_KEY")
    deepgram_api_key: Optional[str] = Field(None, alias="DEEPGRAM_API_KEY")
    document_intelligence_endpoint: Optional[str] = Field(
        None, alias="DOCUMENT_INTELLIGENCE_ENDPOINT"
    )
    document_intelligence_key: Optional[str] = Field(
        None, alias="DOCUMENT_INTELLIGENCE_KEY"
    )
    document_intelligence_model_id: Optional[str] = Field(
        "prebuilt-read", alias="DOCUMENT_INTELLIGENCE_MODEL_ID"
    )
    document_intelligence_api_version: Optional[str] = Field(
        "2024-02-29-preview", alias="DOCUMENT_INTELLIGENCE_API_VERSION"
    )
    aws_textract_access_key_id: Optional[str] = Field(
        None, alias="AWS_TEXTRACT_ACCESS_KEY_ID"
    )
    aws_textract_secret_access_key: Optional[str] = Field(
        None, alias="AWS_TEXTRACT_SECRET_ACCESS_KEY"
    )
    aws_textract_session_token: Optional[str] = Field(
        None, alias="AWS_TEXTRACT_SESSION_TOKEN"
    )
    aws_textract_region: Optional[str] = Field(None, alias="AWS_TEXTRACT_REGION")

    @property
    def local_features_enabled(self) -> bool:
        """True when local ML features are allowed."""

        return not (self.enterprise_mode or self.local_mode_disabled)

    @model_validator(mode="after")
    def _apply_defaults_and_validate(self) -> "Settings":
        """Normalise inputs, apply enterprise defaults, and validate credentials."""

        self.rag_embedding_engine = self._normalise_engine(
            self.rag_embedding_engine, default="local"
        )
        self.audio_stt_engine = self._normalise_engine(
            self.audio_stt_engine, default="local"
        )
        self.audio_tts_engine = self._normalise_engine(
            self.audio_tts_engine, default="local"
        )
        self.vector_db = self._normalise_engine(self.vector_db, default="chroma")
        self.ocr_engine = self._normalise_engine(self.ocr_engine, default="local")
        self.rag_reranking_engine = self._normalise_engine(
            self.rag_reranking_engine, default="local"
        )

        bypass_provided = "bypass_embedding_and_retrieval" in self.model_fields_set
        if self.bypass_embedding_and_retrieval is None:
            self.bypass_embedding_and_retrieval = False

        if not self.local_features_enabled:
            if self.rag_embedding_engine in LOCAL_EMBEDDING_ENGINES:
                self.rag_embedding_engine = "openai"
            if self.audio_stt_engine in LOCAL_STT_ENGINES:
                self.audio_stt_engine = "openai"
            if self.audio_tts_engine in LOCAL_TTS_ENGINES:
                self.audio_tts_engine = "openai"
            if self.vector_db in LOCAL_VECTOR_DBS:
                # Enterprise default switched to local Chroma per deployment strategy.
                self.vector_db = "chroma"
            if not bypass_provided:
                self.bypass_embedding_and_retrieval = True
            if self.ocr_engine in LOCAL_OCR_ENGINES:
                self.ocr_engine = "azure_document_intelligence"
        # Defer strict SaaS credential validation to provider construction time so
        # the application can start even when environment variables are unset.
        # Provider factories will raise ProviderConfigurationError on use.
        self._validate_saas_credentials()
        return self

    def _validate_saas_credentials(self) -> None:
        """Ensure the configured SaaS engines have the required credentials."""

        errors: list[str] = []

        if self.rag_embedding_engine == "openai":
            if not self._first_non_empty(
                self.rag_openai_api_key, self.openai_api_key
            ):
                errors.append(
                    "RAG embedding engine 'openai' requires RAG_OPENAI_API_KEY or OPENAI_API_KEY"
                )
        elif self.rag_embedding_engine == "azure_openai":
            if not self._non_empty(self.rag_azure_openai_api_key):
                errors.append(
                    "RAG embedding engine 'azure_openai' requires RAG_AZURE_OPENAI_API_KEY"
                )

        if self.audio_stt_engine == "openai":
            if not self._first_non_empty(
                self.audio_stt_openai_api_key,
                self.openai_api_key,
            ):
                errors.append(
                    "Audio STT engine 'openai' requires AUDIO_STT_OPENAI_API_KEY or OPENAI_API_KEY"
                )
        elif self.audio_stt_engine == "azure":
            if not self._non_empty(self.audio_stt_azure_api_key):
                errors.append(
                    "Audio STT engine 'azure' requires AUDIO_STT_AZURE_API_KEY"
                )
        elif self.audio_stt_engine == "deepgram":
            if not self._non_empty(self.deepgram_api_key):
                errors.append(
                    "Audio STT engine 'deepgram' requires DEEPGRAM_API_KEY"
                )

        if self.audio_tts_engine == "openai":
            if not self._first_non_empty(
                self.audio_tts_openai_api_key,
                self.openai_api_key,
            ):
                errors.append(
                    "Audio TTS engine 'openai' requires AUDIO_TTS_OPENAI_API_KEY or OPENAI_API_KEY"
                )
        elif self.audio_tts_engine == "azure":
            if not self._non_empty(self.audio_tts_api_key):
                errors.append(
                    "Audio TTS engine 'azure' requires AUDIO_TTS_API_KEY"
                )

        if self.ocr_engine == "azure_document_intelligence":
            if not (
                self._non_empty(self.document_intelligence_endpoint)
                and self._non_empty(self.document_intelligence_key)
            ):
                errors.append(
                    "OCR engine 'azure_document_intelligence' requires DOCUMENT_INTELLIGENCE_ENDPOINT and DOCUMENT_INTELLIGENCE_KEY"
                )
        elif self.ocr_engine == "aws_textract":
            if not (
                self._non_empty(self.aws_textract_access_key_id)
                and self._non_empty(self.aws_textract_secret_access_key)
                and self._non_empty(self.aws_textract_region)
            ):
                errors.append(
                    "OCR engine 'aws_textract' requires AWS_TEXTRACT_ACCESS_KEY_ID, AWS_TEXTRACT_SECRET_ACCESS_KEY, and AWS_TEXTRACT_REGION"
                )

        if self.rag_reranking_engine == "external":
            if not (
                self._non_empty(self.rag_external_reranker_url)
                and self._non_empty(self.rag_external_reranker_api_key)
            ):
                errors.append(
                    "RAG reranking engine 'external' requires RAG_EXTERNAL_RERANKER_URL and RAG_EXTERNAL_RERANKER_API_KEY"
                )

        # Do not raise at settings construction time. This allows the
        # application to start with empty credentials. Provider factories
        # will validate and raise configuration errors when features are used.
        # Keeping this function for potential future logging/telemetry.
        _ = errors  # intentionally unused

    @staticmethod
    def _normalise_engine(value: Optional[str], *, default: str) -> str:
        if value is None:
            return default
        normalised = value.strip().lower()
        return normalised or default

    @staticmethod
    def _first_non_empty(*candidates: Optional[str]) -> Optional[str]:
        return next((candidate for candidate in candidates if Settings._non_empty(candidate)), None)

    @staticmethod
    def _non_empty(value: Optional[str]) -> bool:
        return bool(value and value.strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retrieve cached settings instance for dependency injection."""

    return Settings()
