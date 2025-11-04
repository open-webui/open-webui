"""FastAPI dependency helpers for service providers."""

from __future__ import annotations

from typing import Callable, TypeVar

from fastapi import HTTPException, Request, status

from open_webui.settings import Settings, get_settings
from open_webui.services.interfaces import (
    EmbeddingService,
    STTService,
    TTSService,
    VectorDBService,
    OCRService,
    RerankerService,
)
from open_webui.services.registry import (
    get_embedding_service as build_embedding_service,
    get_stt_service as build_stt_service,
    get_tts_service as build_tts_service,
    get_vectordb_service as build_vectordb_service,
    get_ocr_service as build_ocr_service,
    get_reranker_service as build_reranker_service,
)
from open_webui.services.errors import (
    ProviderConfigurationError,
    LocalFeatureDisabledError,
)


ServiceT = TypeVar("ServiceT")


def _ensure_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        settings = get_settings()
        request.app.state.settings = settings
    return settings


def _resolve_service(
    request: Request,
    attr: str,
    builder: Callable[[Settings], ServiceT],
) -> ServiceT:
    cached = getattr(request.app.state, attr, None)
    if cached is not None:
        return cached

    settings = _ensure_settings(request)
    try:
        service = builder(settings)
    except LocalFeatureDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    except ProviderConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    setattr(request.app.state, attr, service)
    return service


def get_embedding_service(request: Request) -> EmbeddingService:
    return _resolve_service(request, "embedding_service", build_embedding_service)


def get_stt_service(request: Request) -> STTService:
    return _resolve_service(request, "stt_service", build_stt_service)


def get_tts_service(request: Request) -> TTSService:
    return _resolve_service(request, "tts_service", build_tts_service)


def get_vector_db_service(request: Request) -> VectorDBService:
    return _resolve_service(request, "vector_service", build_vectordb_service)


def get_ocr_service(request: Request) -> OCRService:
    return _resolve_service(request, "ocr_service", build_ocr_service)


def get_reranker_service(request: Request) -> RerankerService:
    return _resolve_service(request, "reranker_service", build_reranker_service)
