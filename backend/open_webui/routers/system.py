from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status

from open_webui.settings import get_settings
from open_webui.services.dependencies import (
    get_embedding_service,
    get_stt_service,
    get_tts_service,
    get_vector_db_service,
)


router = APIRouter()


@router.get("/health")
async def health(request: Request) -> Dict[str, Any]:
    settings = getattr(request.app.state, "settings", None) or get_settings()

    # Vector DB health is safe and lightweight
    try:
        vectordb = get_vector_db_service(request)
        vector_health = await vectordb.health()
    except HTTPException as exc:
        vector_health = {
            "status": "unavailable",
            "detail": exc.detail,
            "code": exc.status_code,
        }
    except Exception as exc:  # pragma: no cover - defensive fallback
        vector_health = {"status": "error", "detail": str(exc)}

    # For providers, do not force heavy imports in enterprise mode; just reflect engine
    resolved: Dict[str, Any] = {
        "mode": {
            "enterprise_mode": settings.enterprise_mode,
            "local_features_enabled": settings.local_features_enabled,
        },
        "engines": {
            "embeddings": settings.rag_embedding_engine,
            "stt": settings.audio_stt_engine,
            "tts": settings.audio_tts_engine,
            "vectordb": settings.vector_db,
            "ocr": settings.ocr_engine,
        },
        "vector_db": vector_health,
    }

    return resolved


@router.get("/capabilities")
async def capabilities(request: Request) -> Dict[str, Any]:
    settings = getattr(request.app.state, "settings", None) or get_settings()

    # A capability is considered available if an engine is set and settings validation allowed it
    caps = {
        "embeddings": bool(settings.rag_embedding_engine),
        "stt": bool(settings.audio_stt_engine),
        "tts": bool(settings.audio_tts_engine),
        "ocr": bool(settings.ocr_engine),
        "vectordb": bool(settings.vector_db),
    }

    return {
        "mode": {
            "enterprise_mode": settings.enterprise_mode,
            "local_features_enabled": settings.local_features_enabled,
        },
        "capabilities": caps,
        "engines": {
            "embeddings": settings.rag_embedding_engine,
            "stt": settings.audio_stt_engine,
            "tts": settings.audio_tts_engine,
            "vectordb": settings.vector_db,
            "ocr": settings.ocr_engine,
        },
    }
