"""Factory helpers for resolving runtime service providers."""

from __future__ import annotations

import logging
from typing import Dict, Type

from open_webui.settings import Settings
from open_webui.services.interfaces import (
    EmbeddingService,
    STTService,
    TTSService,
    VectorDBService,
    OCRService,
    RerankerService,
)
from open_webui.services.errors import (
    ProviderConfigurationError,
    LocalFeatureDisabledError,
)
from open_webui.services.providers.vectordb_chroma import ChromaVectorDBService
from open_webui.services.providers.vectordb_pgvector import PgvectorVectorDBService
from open_webui.services.providers.vectordb_pinecone import PineconeVectorDBService
from open_webui.services.providers.vectordb_qdrant import QdrantVectorDBService
from open_webui.services.providers.ocr_external import (
    AzureDocumentIntelligenceConfig,
    AzureDocumentIntelligenceService,
    AWSTextractConfig,
    AWSTextractService,
)
from open_webui.services.providers.ocr_external import (
    AzureDocumentIntelligenceConfig,
    AzureDocumentIntelligenceService,
    AWSTextractConfig,
    AWSTextractService,
)

from open_webui.config import (
    RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
    RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
    RAG_OPENAI_API_BASE_URL,
    RAG_OPENAI_API_KEY,
    RAG_AZURE_OPENAI_BASE_URL,
    RAG_AZURE_OPENAI_API_KEY,
    RAG_AZURE_OPENAI_API_VERSION,
    AUDIO_STT_OPENAI_API_BASE_URL,
    AUDIO_STT_OPENAI_API_KEY,
    AUDIO_STT_MODEL,
    AUDIO_STT_AZURE_API_KEY,
    AUDIO_STT_AZURE_REGION,
    AUDIO_STT_AZURE_BASE_URL,
    AUDIO_STT_AZURE_LOCALES,
    AUDIO_STT_AZURE_MAX_SPEAKERS,
    DEEPGRAM_API_KEY,
    WHISPER_MODEL,
    WHISPER_MODEL_DIR,
    WHISPER_VAD_FILTER,
    WHISPER_MODEL_AUTO_UPDATE,
    AUDIO_TTS_MODEL,
    AUDIO_TTS_VOICE,
    AUDIO_TTS_OPENAI_API_BASE_URL,
    AUDIO_TTS_OPENAI_API_KEY,
    AUDIO_TTS_OPENAI_PARAMS,
    AUDIO_TTS_API_KEY,
    AUDIO_TTS_AZURE_SPEECH_REGION,
    AUDIO_TTS_AZURE_SPEECH_BASE_URL,
    AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT,
    DOCUMENT_INTELLIGENCE_ENDPOINT,
    DOCUMENT_INTELLIGENCE_KEY,
    DOCUMENT_INTELLIGENCE_MODEL_ID,
    DOCUMENT_INTELLIGENCE_API_VERSION,
    AWS_TEXTRACT_ACCESS_KEY_ID,
    AWS_TEXTRACT_SECRET_ACCESS_KEY,
    AWS_TEXTRACT_SESSION_TOKEN,
    AWS_TEXTRACT_REGION,
    DOCUMENT_INTELLIGENCE_ENDPOINT,
    DOCUMENT_INTELLIGENCE_KEY,
    DOCUMENT_INTELLIGENCE_MODEL_ID,
    DOCUMENT_INTELLIGENCE_API_VERSION,
    AWS_TEXTRACT_ACCESS_KEY_ID,
    AWS_TEXTRACT_SECRET_ACCESS_KEY,
    AWS_TEXTRACT_SESSION_TOKEN,
    AWS_TEXTRACT_REGION,
    RAG_RERANKING_MODEL,
    RAG_RERANKING_MODEL_AUTO_UPDATE,
    RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
    RAG_EXTERNAL_RERANKER_URL,
    RAG_EXTERNAL_RERANKER_API_KEY,
)
from open_webui.env import DEVICE_TYPE


log = logging.getLogger(__name__)


def _require_local(settings: Settings, feature: str) -> None:
    if not settings.local_features_enabled:
        raise LocalFeatureDisabledError(
            f"{feature} local providers are disabled in enterprise mode."
        )


def get_embedding_service(settings: Settings) -> EmbeddingService:
    engine = settings.rag_embedding_engine

    if engine in {"", "local"}:
        _require_local(settings, "Embedding")
        from open_webui.services.providers.embedding_local import (
            LocalEmbeddingService,
        )
        service = LocalEmbeddingService(
            model_name=RAG_EMBEDDING_MODEL.value,
            auto_update=RAG_EMBEDDING_MODEL_AUTO_UPDATE,
            trust_remote_code=RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
        )
        log.debug("Embedding provider resolved: %s", service.__class__.__name__)
        return service
    if engine == "openai":
        from open_webui.services.providers.embedding_openai import (
            OpenAIEmbeddingService,
        )
        key = settings.rag_openai_api_key or settings.openai_api_key or RAG_OPENAI_API_KEY.value
        if not key:
            raise ProviderConfigurationError(
                "OpenAI embeddings require RAG_OPENAI_API_KEY or OPENAI_API_KEY."
            )
        service = OpenAIEmbeddingService(
            model=RAG_EMBEDDING_MODEL.value,
            api_base=RAG_OPENAI_API_BASE_URL.value,
            api_key=key,
        )
        log.debug("Embedding provider resolved: %s", service.__class__.__name__)
        return service
    if engine == "azure_openai":
        from open_webui.services.providers.embedding_azure_openai import (
            AzureOpenAIEmbeddingService,
        )
        base = RAG_AZURE_OPENAI_BASE_URL.value
        key = settings.rag_azure_openai_api_key or RAG_AZURE_OPENAI_API_KEY.value
        version = RAG_AZURE_OPENAI_API_VERSION.value
        if not (base and key and version):
            raise ProviderConfigurationError(
                "Azure OpenAI embeddings require base URL, API key, and API version."
            )
        service = AzureOpenAIEmbeddingService(
            deployment=RAG_EMBEDDING_MODEL.value,
            api_base=base,
            api_key=key,
            api_version=version,
        )
        log.debug("Embedding provider resolved: %s", service.__class__.__name__)
        return service

    raise ProviderConfigurationError(f"Unsupported embedding engine '{engine}'")


def get_stt_service(settings: Settings) -> STTService:
    engine = settings.audio_stt_engine

    if engine in {"", "local", "whisper"}:
        _require_local(settings, "STT")
        from open_webui.services.providers.stt_local import LocalWhisperSTTService
        device = "cuda" if DEVICE_TYPE == "cuda" else "cpu"
        service = LocalWhisperSTTService(
            model_size=WHISPER_MODEL.value,
            device=device,
            compute_type="int8",
            download_root=WHISPER_MODEL_DIR,
            vad_filter=WHISPER_VAD_FILTER.value,
            local_files_only=not WHISPER_MODEL_AUTO_UPDATE,
        )
        log.debug("STT provider resolved: %s", service.__class__.__name__)
        return service
    if engine == "openai":
        from open_webui.services.providers.stt_openai import OpenAISTTService
        key = settings.audio_stt_openai_api_key or settings.openai_api_key or AUDIO_STT_OPENAI_API_KEY.value
        if not key:
            raise ProviderConfigurationError(
                "OpenAI STT requires AUDIO_STT_OPENAI_API_KEY or OPENAI_API_KEY."
            )
        service = OpenAISTTService(
            api_key=key,
            api_base=AUDIO_STT_OPENAI_API_BASE_URL.value,
            model=AUDIO_STT_MODEL.value or "whisper-1",
        )
        log.debug("STT provider resolved: %s", service.__class__.__name__)
        return service
    if engine == "azure":
        from open_webui.services.providers.stt_azure import AzureSTTService
        base_url = AUDIO_STT_AZURE_BASE_URL.value
        key = settings.audio_stt_azure_api_key or AUDIO_STT_AZURE_API_KEY.value
        region = AUDIO_STT_AZURE_REGION.value
        if not (key and region):
            raise ProviderConfigurationError(
                "Azure STT requires AUDIO_STT_AZURE_API_KEY and AUDIO_STT_AZURE_REGION."
            )
        locales = AUDIO_STT_AZURE_LOCALES.value
        max_speakers_raw = AUDIO_STT_AZURE_MAX_SPEAKERS.value
        try:
            max_speakers = int(max_speakers_raw) if max_speakers_raw else 3
        except ValueError:
            max_speakers = 3
        service = AzureSTTService(
            api_key=key,
            region=region,
            base_url=base_url or None,
            api_version="2024-11-15",
            model=AUDIO_STT_MODEL.value or None,
            locales=locales,
            max_speakers=max_speakers,
        )
        log.debug("STT provider resolved: %s", service.__class__.__name__)
        return service
    if engine == "deepgram":
        from open_webui.services.providers.stt_deepgram import DeepgramSTTService
        key = settings.deepgram_api_key or DEEPGRAM_API_KEY.value
        if not key:
            raise ProviderConfigurationError("Deepgram STT requires DEEPGRAM_API_KEY.")
        service = DeepgramSTTService(
            api_key=key, model=AUDIO_STT_MODEL.value or None
        )
        log.debug("STT provider resolved: %s", service.__class__.__name__)
        return service

    raise ProviderConfigurationError(f"Unsupported STT engine '{engine}'")


def get_tts_service(settings: Settings) -> TTSService:
    engine = settings.audio_tts_engine

    if engine in {"", "local"}:
        _require_local(settings, "TTS")
        from open_webui.services.providers.tts_local import LocalTTSService
        speaker = AUDIO_TTS_VOICE.value or None
        speaker_index = None
        service = LocalTTSService(
            model=AUDIO_TTS_MODEL.value or "microsoft/speecht5_tts",
            speaker_dataset="Matthijs/cmu-arctic-xvectors",
            speaker_index=speaker_index,
        )
        log.debug("TTS provider resolved: %s", service.__class__.__name__)
        return service
    if engine == "openai":
        from open_webui.services.providers.tts_openai import OpenAITTSService
        key = settings.audio_tts_openai_api_key or settings.openai_api_key or AUDIO_TTS_OPENAI_API_KEY.value
        if not key:
            raise ProviderConfigurationError(
                "OpenAI TTS requires AUDIO_TTS_OPENAI_API_KEY or OPENAI_API_KEY."
            )
        service = OpenAITTSService(
            api_key=key,
            api_base=AUDIO_TTS_OPENAI_API_BASE_URL.value,
            model=AUDIO_TTS_MODEL.value or "gpt-4o-mini-tts",
            default_voice=AUDIO_TTS_VOICE.value or None,
            request_overrides=AUDIO_TTS_OPENAI_PARAMS.value or {},
        )
        log.debug("TTS provider resolved: %s", service.__class__.__name__)
        return service
    if engine == "azure":
        from open_webui.services.providers.tts_azure import AzureTTSService
        api_key = settings.audio_tts_api_key or AUDIO_TTS_API_KEY.value
        if not api_key:
            raise ProviderConfigurationError("Azure TTS requires AUDIO_TTS_API_KEY.")
        voice = AUDIO_TTS_VOICE.value or "en-US-AriaNeural"
        service = AzureTTSService(
            api_key=api_key,
            region=AUDIO_TTS_AZURE_SPEECH_REGION.value or "eastus",
            voice=voice,
            base_url=AUDIO_TTS_AZURE_SPEECH_BASE_URL.value or None,
            output_format=AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT.value
            or "audio-24khz-160kbitrate-mono-mp3",
        )
        log.debug("TTS provider resolved: %s", service.__class__.__name__)
        return service

    raise ProviderConfigurationError(f"Unsupported TTS engine '{engine}'")


def get_reranker_service(settings: Settings) -> RerankerService:
    engine = (settings.rag_reranking_engine or "").strip().lower()

    if engine in {"", "local"}:
        _require_local(settings, "Reranker")
        from open_webui.services.providers.reranker_local import (
            LocalRerankerService,
        )
        model_name = settings.rag_reranking_model or RAG_RERANKING_MODEL.value
        if not model_name:
            raise ProviderConfigurationError(
                "Local reranker requires RAG_RERANKING_MODEL to be set."
            )
        service = LocalRerankerService(
            model_name=model_name,
            auto_update=RAG_RERANKING_MODEL_AUTO_UPDATE,
            trust_remote_code=RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
        )
        log.debug("Reranker provider resolved: %s", service.__class__.__name__)
        return service

    if engine == "external":
        from open_webui.services.providers.reranker_external import (
            ExternalRerankerService,
        )
        url = settings.rag_external_reranker_url or RAG_EXTERNAL_RERANKER_URL.value
        api_key = (
            settings.rag_external_reranker_api_key or RAG_EXTERNAL_RERANKER_API_KEY.value
        )
        if not (url and api_key):
            raise ProviderConfigurationError(
                "External reranker requires RAG_EXTERNAL_RERANKER_URL and RAG_EXTERNAL_RERANKER_API_KEY."
            )
        model_name = settings.rag_reranking_model or RAG_RERANKING_MODEL.value or "reranker"
        service = ExternalRerankerService(
            model=model_name,
            url=url,
            api_key=api_key,
        )
        log.debug("Reranker provider resolved: %s", service.__class__.__name__)
        return service

    raise ProviderConfigurationError(f"Unsupported reranking engine '{engine}'")


VECTOR_PROVIDERS: Dict[str, Type[VectorDBService]] = {
    "chroma": ChromaVectorDBService,
    "pgvector": PgvectorVectorDBService,
    "pinecone": PineconeVectorDBService,
    "qdrant": QdrantVectorDBService,
}


def get_vectordb_service(settings: Settings) -> VectorDBService:
    engine = (settings.vector_db or "").strip().lower()

    if engine in {"", "local"}:
        # Default to Chroma when no explicit vector DB is configured. Chroma is
        # considered lightweight enough to be allowed in enterprise mode.
        engine = "chroma"

    provider_cls = VECTOR_PROVIDERS.get(engine)
    if not provider_cls:
        raise ProviderConfigurationError(f"Unsupported vector DB engine '{engine}'")

    service = provider_cls()
    log.debug("Vector DB provider resolved: %s", service.__class__.__name__)
    return service


def get_ocr_service(settings: Settings) -> OCRService:
    engine = settings.ocr_engine

    if engine in {"", "local", "rapidocr"}:
        _require_local(settings, "OCR")
        raise ProviderConfigurationError(
            "Local OCR provider is not available in enterprise mode."
        )

    if engine == "azure_document_intelligence":
        endpoint = (
            settings.document_intelligence_endpoint
            or DOCUMENT_INTELLIGENCE_ENDPOINT.value
        )
        api_key = (
            settings.document_intelligence_key or DOCUMENT_INTELLIGENCE_KEY.value
        )
        model_id = (
            settings.document_intelligence_model_id
            or DOCUMENT_INTELLIGENCE_MODEL_ID.value
        )
        api_version = (
            settings.document_intelligence_api_version
            or DOCUMENT_INTELLIGENCE_API_VERSION.value
        )
        if not endpoint or not api_key:
            raise ProviderConfigurationError(
                "Azure Document Intelligence OCR requires endpoint and API key."
            )
        config = AzureDocumentIntelligenceConfig(
            endpoint=endpoint.rstrip("/"),
            api_key=api_key,
            model_id=model_id,
            api_version=api_version,
        )
        service = AzureDocumentIntelligenceService(config)
        log.debug("OCR provider resolved: %s", service.__class__.__name__)
        return service

    if engine == "aws_textract":
        access_key = (
            settings.aws_textract_access_key_id or AWS_TEXTRACT_ACCESS_KEY_ID.value
        )
        secret_key = (
            settings.aws_textract_secret_access_key
            or AWS_TEXTRACT_SECRET_ACCESS_KEY.value
        )
        region = settings.aws_textract_region or AWS_TEXTRACT_REGION.value
        session_token = (
            settings.aws_textract_session_token or AWS_TEXTRACT_SESSION_TOKEN.value
        )
        if not (access_key and secret_key and region):
            raise ProviderConfigurationError(
                "AWS Textract OCR requires access key, secret key, and region."
            )
        config = AWSTextractConfig(
            access_key_id=access_key,
            secret_access_key=secret_key,
            region=region,
            session_token=session_token or None,
        )
        service = AWSTextractService(config)
        log.debug("OCR provider resolved: %s", service.__class__.__name__)
        return service

    raise ProviderConfigurationError(f"Unsupported OCR engine '{engine}'")
