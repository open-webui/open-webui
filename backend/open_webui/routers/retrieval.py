import json
import logging
import mimetypes
import os
import shutil
import time

import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterator, List, Optional, Sequence, Union
from uuid import UUID

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    Request,
    status,
    APIRouter,
)
from open_webui.utils.job_queue import (
    enqueue_file_processing_job,
    is_job_queue_available,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
import tiktoken


from langchain.text_splitter import RecursiveCharacterTextSplitter, TokenTextSplitter
from langchain_core.documents import Document

from open_webui.models.files import FileModel, Files
from open_webui.models.knowledge import Knowledges
from open_webui.models.users import Users
from open_webui.storage.provider import Storage
from open_webui.env import REDIS_URL
from open_webui.socket.utils import RedisLock, get_redis_pool
import redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError


from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT

# Document loaders
from open_webui.retrieval.loaders.main import Loader
from open_webui.retrieval.loaders.youtube import YoutubeLoader

# Web search engines
from open_webui.retrieval.web.main import SearchResult
from open_webui.retrieval.web.utils import get_web_loader
from open_webui.retrieval.web.brave import search_brave
from open_webui.retrieval.web.kagi import search_kagi
from open_webui.retrieval.web.mojeek import search_mojeek
from open_webui.retrieval.web.bocha import search_bocha
from open_webui.retrieval.web.duckduckgo import search_duckduckgo
from open_webui.retrieval.web.google_pse import search_google_pse
from open_webui.retrieval.web.jina_search import search_jina
from open_webui.retrieval.web.searchapi import search_searchapi
from open_webui.retrieval.web.serpapi import search_serpapi
from open_webui.retrieval.web.searxng import search_searxng
from open_webui.retrieval.web.serper import search_serper
from open_webui.retrieval.web.serply import search_serply
from open_webui.retrieval.web.serpstack import search_serpstack
from open_webui.retrieval.web.tavily import search_tavily
from open_webui.retrieval.web.bing import search_bing
from open_webui.retrieval.web.exa import search_exa


from open_webui.retrieval.utils import (
    get_single_batch_embedding_function,
    get_embedding_function,
    get_model_path,
    query_collection,
    query_collection_with_hybrid_search,
    query_doc,
    query_doc_with_hybrid_search,
)
from open_webui.utils.misc import (
    calculate_sha256_string,
)
from open_webui.utils.auth import get_admin_user, get_verified_user


from open_webui.config import (
    ENV,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
    RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
    RAG_RERANKING_MODEL_AUTO_UPDATE,
    RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
    UPLOAD_DIR,
    DEFAULT_LOCALE,
)
from open_webui.env import (
    SRC_LOG_LEVELS,
    DEVICE_TYPE,
    ENABLE_JOB_QUEUE,
    DOCKER,
)
from open_webui.constants import ERROR_MESSAGES

# OpenTelemetry instrumentation (conditional import)
try:
    from open_webui.utils.otel_instrumentation import (
        trace_span,
        add_span_event,
        set_span_attribute,
    )
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    # Create no-op functions if OTEL not available
    def trace_span(*args, **kwargs):
        from contextlib import contextmanager
        @contextmanager
        def _noop():
            yield None
        return _noop()
    def add_span_event(*args, **kwargs):
        pass
    def set_span_attribute(*args, **kwargs):
        pass

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

##########################################
#
# Utility functions
#
##########################################


def get_ef(
    engine: str,
    embedding_model: str,
    auto_update: bool = False,
):
    ef = None
    if embedding_model and engine == "":
        from sentence_transformers import SentenceTransformer

        try:
            ef = SentenceTransformer(
                get_model_path(embedding_model, auto_update),
                device=DEVICE_TYPE,
                trust_remote_code=RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
            )
        except Exception as e:
            log.debug(f"Error loading SentenceTransformer: {e}")

    return ef


def get_rf(
    reranking_model: str,
    auto_update: bool = False,
):
    rf = None
    if reranking_model:
        if any(model in reranking_model for model in ["jinaai/jina-colbert-v2"]):
            try:
                from open_webui.retrieval.models.colbert import ColBERT

                rf = ColBERT(
                    get_model_path(reranking_model, auto_update),
                    env="docker" if DOCKER else None,
                )

            except Exception as e:
                log.error(f"ColBERT: {e}")
                raise Exception(ERROR_MESSAGES.DEFAULT(e))
        else:
            import sentence_transformers

            try:
                rf = sentence_transformers.CrossEncoder(
                    get_model_path(reranking_model, auto_update),
                    device=DEVICE_TYPE,
                    trust_remote_code=RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
                )
            except:
                log.error("CrossEncoder error")
                raise Exception(ERROR_MESSAGES.DEFAULT("CrossEncoder error"))
    return rf


##########################################
#
# API routes
#
##########################################


router = APIRouter()


class CollectionNameForm(BaseModel):
    collection_name: Optional[str] = None


class ProcessUrlForm(CollectionNameForm):
    url: str


class SearchForm(CollectionNameForm):
    query: str


@router.get("/worker/status")
async def get_worker_status(request: Request, user=Depends(get_verified_user)):
    """
    Get worker and job queue status for debugging.
    """
    from open_webui.utils.job_queue import (
        get_job_queue,
        FILE_PROCESSING_QUEUE_NAME,
        is_job_queue_available,
    )
    from rq import Worker
    
    status = {
        "job_queue_enabled": ENABLE_JOB_QUEUE,
        "job_queue_available": False,
        "queue_name": FILE_PROCESSING_QUEUE_NAME,
        "queue_length": 0,
        "workers": [],
        "redis_connected": False,
    }
    
    try:
        if is_job_queue_available():
            status["job_queue_available"] = True
            queue = get_job_queue()
            if queue:
                status["queue_length"] = len(queue)
                status["redis_connected"] = True
                
                # Get active workers
                try:
                    workers = Worker.all(queue=queue)
                    status["workers"] = [
                        {
                            "name": w.name,
                            "state": w.get_state(),
                            "current_job": str(w.get_current_job_id()) if w.get_current_job_id() else None,
                        }
                        for w in workers
                    ]
                except Exception as worker_error:
                    log.warning(f"Could not get worker status: {worker_error}")
                    status["worker_error"] = str(worker_error)
    except Exception as e:
        log.error(f"Error checking worker status: {e}", exc_info=True)
        status["error"] = str(e)
    
    return status


@router.get("/")
async def get_status(request: Request, user=Depends(get_verified_user)):
    chunk_size = request.app.state.config.CHUNK_SIZE.get(user.email)
    chunk_overlap = request.app.state.config.CHUNK_OVERLAP.get(user.email)
    template = request.app.state.config.RAG_TEMPLATE.get(user.email)

    log.info(f"[get_status] user={user.email} | chunk_size={chunk_size} | chunk_overlap={chunk_overlap} | template={template}")

    return {
        "status": True,
        
        "chunk_size": request.app.state.config.CHUNK_SIZE.get(user.email),
        "chunk_overlap": request.app.state.config.CHUNK_OVERLAP.get(user.email),
        "template": request.app.state.config.RAG_TEMPLATE.get(user.email),
        "embedding_engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
        "embedding_model": request.app.state.config.RAG_EMBEDDING_MODEL,
        "reranking_model": request.app.state.config.RAG_RERANKING_MODEL,
        "embedding_batch_size": request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
    }


@router.get("/embedding")
async def get_embedding_config(request: Request, user=Depends(get_verified_user)):
    """
    Get embedding configuration for the requesting user.
    
    RBAC: The API key returned is scoped to the requesting user:
    - If user is an admin: Returns their own configured API key
    - If user is in a group: Returns the group creator's (admin's) API key
    - Other admins' API keys are NOT accessible (proper RBAC isolation)
    """
    return {
        "status": True,
        "embedding_engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
        "embedding_model": request.app.state.config.RAG_EMBEDDING_MODEL,
        "embedding_batch_size": request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
        "openai_config": {
            "url": request.app.state.config.RAG_OPENAI_API_BASE_URL,
            # RBAC: Per-admin API key - retrieved using requesting user's email
            # This ensures the key is only accessible to:
            # 1. The admin who configured it (when they request it)
            # 2. Users in groups created by that admin (via group inheritance)
            # 3. NOT accessible to other admins or their groups
            "key": request.app.state.config.RAG_OPENAI_API_KEY.get(user.email),
        },
        "ollama_config": {
            "url": request.app.state.config.RAG_OLLAMA_BASE_URL,
            "key": request.app.state.config.RAG_OLLAMA_API_KEY,
        },
    }


@router.get("/reranking")
async def get_reraanking_config(request: Request, user=Depends(get_verified_user)):
    return {
        "status": True,
        "reranking_model": request.app.state.config.RAG_RERANKING_MODEL,
    }


class OpenAIConfigForm(BaseModel):
    url: str
    key: str


class OllamaConfigForm(BaseModel):
    url: str
    key: str


class EmbeddingModelUpdateForm(BaseModel):
    openai_config: Optional[OpenAIConfigForm] = None
    ollama_config: Optional[OllamaConfigForm] = None
    embedding_engine: str
    embedding_model: str
    embedding_batch_size: Optional[int] = 1


@router.post("/embedding/update")
async def update_embedding_config(
    request: Request, form_data: EmbeddingModelUpdateForm, user=Depends(get_verified_user)
):
    log.info(
        f"Updating embedding model: {request.app.state.config.RAG_EMBEDDING_MODEL} to {form_data.embedding_model}"
    )
    try:
        request.app.state.config.RAG_EMBEDDING_ENGINE = form_data.embedding_engine
        request.app.state.config.RAG_EMBEDDING_MODEL = form_data.embedding_model

        if request.app.state.config.RAG_EMBEDDING_ENGINE in [
            "ollama",
            "openai",
            "portkey",
        ]:
            if form_data.openai_config is not None:
                request.app.state.config.RAG_OPENAI_API_BASE_URL = (
                    form_data.openai_config.url
                )
                # Per-admin API key - set for this admin and their group (RBAC-protected)
                # The key is stored under the admin's email and will be accessible to:
                # 1. The admin themselves
                # 2. Users in groups created by this admin
                # 3. NOT accessible to other admins or their groups
                request.app.state.config.RAG_OPENAI_API_KEY.set(
                    user.email, form_data.openai_config.key
                )
                log.info(
                    f"Admin {user.email} configured embedding API key (RBAC: accessible to admin and their group members only)"
                )

            if form_data.ollama_config is not None:
                request.app.state.config.RAG_OLLAMA_BASE_URL = (
                    form_data.ollama_config.url
                )
                request.app.state.config.RAG_OLLAMA_API_KEY = (
                    form_data.ollama_config.key
                )

            request.app.state.config.RAG_EMBEDDING_BATCH_SIZE = (
                form_data.embedding_batch_size
            )

        request.app.state.ef = get_ef(
            request.app.state.config.RAG_EMBEDDING_ENGINE,
            request.app.state.config.RAG_EMBEDDING_MODEL,
        )

        # Get user's API key for embedding function
        user_api_key = request.app.state.config.RAG_OPENAI_API_KEY.get(user.email)
        
        # Get base URL value - handle PersistentConfig objects properly
        if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai" or request.app.state.config.RAG_EMBEDDING_ENGINE == "portkey":
            base_url_config = request.app.state.config.RAG_OPENAI_API_BASE_URL
            base_url = (
                base_url_config.value
                if hasattr(base_url_config, 'value')
                else str(base_url_config)
            )
            # Fallback to default if empty (from config.py default)
            if not base_url or base_url.strip() == "":
                base_url = "https://ai-gateway.apps.cloud.rt.nyu.edu/v1"
                log.warning(f"RAG_OPENAI_API_BASE_URL is empty, using default: {base_url}")
        else:
            base_url_config = request.app.state.config.RAG_OLLAMA_BASE_URL
            base_url = (
                base_url_config.value
                if hasattr(base_url_config, 'value')
                else str(base_url_config)
            )
        
        request.app.state.EMBEDDING_FUNCTION = get_embedding_function(
            request.app.state.config.RAG_EMBEDDING_ENGINE,
            request.app.state.config.RAG_EMBEDDING_MODEL,
            request.app.state.ef,
            base_url,
            (
                user_api_key
                if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                or request.app.state.config.RAG_EMBEDDING_ENGINE == "portkey"
                else request.app.state.config.RAG_OLLAMA_API_KEY
            ),
            request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
        )

        return {
            "status": True,
            "embedding_engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
            "embedding_model": request.app.state.config.RAG_EMBEDDING_MODEL,
            "embedding_batch_size": request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
            "openai_config": {
                "url": request.app.state.config.RAG_OPENAI_API_BASE_URL,
                # Per-admin API key
                "key": user_api_key,
            },
            "ollama_config": {
                "url": request.app.state.config.RAG_OLLAMA_BASE_URL,
                "key": request.app.state.config.RAG_OLLAMA_API_KEY,
            },
        }
    except Exception as e:
        log.exception(f"Problem updating embedding model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


class RerankingModelUpdateForm(BaseModel):
    reranking_model: str


@router.post("/reranking/update")
async def update_reranking_config(
    request: Request, form_data: RerankingModelUpdateForm, user=Depends(get_admin_user)
):
    log.info(
        f"Updating reranking model: {request.app.state.config.RAG_RERANKING_MODEL} to {form_data.reranking_model}"
    )
    try:
        request.app.state.config.RAG_RERANKING_MODEL = form_data.reranking_model

        try:
            request.app.state.rf = get_rf(
                request.app.state.config.RAG_RERANKING_MODEL,
                True,
            )
        except Exception as e:
            log.error(f"Error loading reranking model: {e}")
            request.app.state.config.ENABLE_RAG_HYBRID_SEARCH = False

        return {
            "status": True,
            "reranking_model": request.app.state.config.RAG_RERANKING_MODEL,
        }
    except Exception as e:
        log.exception(f"Problem updating reranking model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.get("/config")
async def get_rag_config(request: Request, user=Depends(get_verified_user)):
    return {
        "status": True,
        "pdf_extract_images": request.app.state.config.PDF_EXTRACT_IMAGES,
        "RAG_FULL_CONTEXT": request.app.state.config.RAG_FULL_CONTEXT.get(user.email),
        "BYPASS_EMBEDDING_AND_RETRIEVAL": request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL,
        "enable_google_drive_integration": request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
        "enable_onedrive_integration": request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION,
        "content_extraction": {
            "engine": request.app.state.config.CONTENT_EXTRACTION_ENGINE,
            "tika_server_url": request.app.state.config.TIKA_SERVER_URL,
            "document_intelligence_config": {
                "endpoint": request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT,
                "key": request.app.state.config.DOCUMENT_INTELLIGENCE_KEY,
            },
        },
        "chunk": {
            "text_splitter": request.app.state.config.TEXT_SPLITTER,
            "chunk_size": request.app.state.config.CHUNK_SIZE.get(user.email),
            "chunk_overlap": request.app.state.config.CHUNK_OVERLAP.get(user.email),
        },
        "file": {
            "max_size": request.app.state.config.FILE_MAX_SIZE,
            "max_count": request.app.state.config.FILE_MAX_COUNT,
        },
        "youtube": {
            "language": request.app.state.config.YOUTUBE_LOADER_LANGUAGE,
            "translation": request.app.state.YOUTUBE_LOADER_TRANSLATION,
            "proxy_url": request.app.state.config.YOUTUBE_LOADER_PROXY_URL,
        },
        "web": {
            "ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION": request.app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
            "BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL": request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL.get(user.email),
            "search": {
                "enabled": request.app.state.config.ENABLE_RAG_WEB_SEARCH.get(user.email),
                "drive": request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
                "onedrive": request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION,
                "engine": request.app.state.config.RAG_WEB_SEARCH_ENGINE.get(user.email),
                "searxng_query_url": request.app.state.config.SEARXNG_QUERY_URL.get(user.email),
                "google_pse_api_key": request.app.state.config.GOOGLE_PSE_API_KEY.get(user.email),
                "google_pse_engine_id": request.app.state.config.GOOGLE_PSE_ENGINE_ID.get(user.email),
                "brave_search_api_key": request.app.state.config.BRAVE_SEARCH_API_KEY.get(user.email),
                "kagi_search_api_key": request.app.state.config.KAGI_SEARCH_API_KEY.get(user.email),
                "mojeek_search_api_key": request.app.state.config.MOJEEK_SEARCH_API_KEY.get(user.email),
                "bocha_search_api_key": request.app.state.config.BOCHA_SEARCH_API_KEY.get(user.email),
                "serpstack_api_key": request.app.state.config.SERPSTACK_API_KEY.get(user.email),
                "serpstack_https": request.app.state.config.SERPSTACK_HTTPS.get(user.email),
                "serper_api_key": request.app.state.config.SERPER_API_KEY.get(user.email),
                "serply_api_key": request.app.state.config.SERPLY_API_KEY.get(user.email),
                "tavily_api_key": request.app.state.config.TAVILY_API_KEY.get(user.email),
                "searchapi_api_key": request.app.state.config.SEARCHAPI_API_KEY.get(user.email),
                "searchapi_engine": request.app.state.config.SEARCHAPI_ENGINE.get(user.email),
                "serpapi_api_key": request.app.state.config.SERPAPI_API_KEY.get(user.email),
                "serpapi_engine": request.app.state.config.SERPAPI_ENGINE.get(user.email),
                "jina_api_key": request.app.state.config.JINA_API_KEY.get(user.email),
                "bing_search_v7_endpoint": request.app.state.config.BING_SEARCH_V7_ENDPOINT.get(user.email),
                "bing_search_v7_subscription_key": request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY.get(user.email),
                "exa_api_key": request.app.state.config.EXA_API_KEY.get(user.email),
                "result_count": request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(user.email),
                "trust_env": request.app.state.config.RAG_WEB_SEARCH_TRUST_ENV.get(user.email),
                "concurrent_requests": request.app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS.get(user.email),
                "domain_filter_list": request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(user.email),
                "website_blocklist": request.app.state.config.RAG_WEB_SEARCH_WEBSITE_BLOCKLIST.get(user.email),
                "internal_facilities_sites": request.app.state.config.RAG_WEB_SEARCH_INTERNAL_FACILITIES_SITES.get(user.email),
            },
        },
    }


class FileConfig(BaseModel):
    max_size: Optional[int] = None
    max_count: Optional[int] = None


class DocumentIntelligenceConfigForm(BaseModel):
    endpoint: str
    key: str


class ContentExtractionConfig(BaseModel):
    engine: str = ""
    tika_server_url: Optional[str] = None
    document_intelligence_config: Optional[DocumentIntelligenceConfigForm] = None


class ChunkParamUpdateForm(BaseModel):
    text_splitter: Optional[str] = None
    chunk_size: int
    chunk_overlap: int


class YoutubeLoaderConfig(BaseModel):
    language: list[str]
    translation: Optional[str] = None
    proxy_url: str = ""


class WebSearchConfig(BaseModel):
    enabled: bool
    engine: Optional[str] = None
    searxng_query_url: Optional[str] = None
    google_pse_api_key: Optional[str] = None
    google_pse_engine_id: Optional[str] = None
    brave_search_api_key: Optional[str] = None
    kagi_search_api_key: Optional[str] = None
    mojeek_search_api_key: Optional[str] = None
    bocha_search_api_key: Optional[str] = None
    serpstack_api_key: Optional[str] = None
    serpstack_https: Optional[bool] = None
    serper_api_key: Optional[str] = None
    serply_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None
    searchapi_api_key: Optional[str] = None
    searchapi_engine: Optional[str] = None
    serpapi_api_key: Optional[str] = None
    serpapi_engine: Optional[str] = None
    jina_api_key: Optional[str] = None
    bing_search_v7_endpoint: Optional[str] = None
    bing_search_v7_subscription_key: Optional[str] = None
    exa_api_key: Optional[str] = None
    result_count: Optional[int] = None
    concurrent_requests: Optional[int] = None
    trust_env: Optional[bool] = None
    domain_filter_list: Optional[List[str]] = []
    website_blocklist: Optional[List[str]] = []
    internal_facilities_sites: Optional[List[str]] = []


class WebConfig(BaseModel):
    search: WebSearchConfig
    ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION: Optional[bool] = None
    BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL: Optional[bool] = None


class ConfigUpdateForm(BaseModel):
    RAG_FULL_CONTEXT: Optional[bool] = None
    BYPASS_EMBEDDING_AND_RETRIEVAL: Optional[bool] = None
    pdf_extract_images: Optional[bool] = None
    enable_google_drive_integration: Optional[bool] = None
    enable_onedrive_integration: Optional[bool] = None
    file: Optional[FileConfig] = None
    content_extraction: Optional[ContentExtractionConfig] = None
    chunk: Optional[ChunkParamUpdateForm] = None
    youtube: Optional[YoutubeLoaderConfig] = None
    web: Optional[WebConfig] = None


@router.post("/config/update")
async def update_rag_config(
    request: Request, form_data: ConfigUpdateForm, user=Depends(get_admin_user)
):
    request.app.state.config.PDF_EXTRACT_IMAGES = (
        form_data.pdf_extract_images
        if form_data.pdf_extract_images is not None
        else request.app.state.config.PDF_EXTRACT_IMAGES
    )

    
    if form_data.RAG_FULL_CONTEXT is not None:
        request.app.state.config.RAG_FULL_CONTEXT.set(user.email,form_data.RAG_FULL_CONTEXT)
    else:
        request.app.state.config.RAG_FULL_CONTEXT.get(user.email)
    

    request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL = (
        form_data.BYPASS_EMBEDDING_AND_RETRIEVAL
        if form_data.BYPASS_EMBEDDING_AND_RETRIEVAL is not None
        else request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL
    )

    request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION = (
        form_data.enable_google_drive_integration
        if form_data.enable_google_drive_integration is not None
        else request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION
    )

    request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION = (
        form_data.enable_onedrive_integration
        if form_data.enable_onedrive_integration is not None
        else request.app.state.config.ENABLE_ONEDRIVE_INTEGRATION
    )

    if form_data.file is not None:
        request.app.state.config.FILE_MAX_SIZE = form_data.file.max_size
        request.app.state.config.FILE_MAX_COUNT = form_data.file.max_count

    if form_data.content_extraction is not None:
        log.info(
            f"Updating content extraction: {request.app.state.config.CONTENT_EXTRACTION_ENGINE} to {form_data.content_extraction.engine}"
        )
        request.app.state.config.CONTENT_EXTRACTION_ENGINE = (
            form_data.content_extraction.engine
        )
        request.app.state.config.TIKA_SERVER_URL = (
            form_data.content_extraction.tika_server_url
        )
        if form_data.content_extraction.document_intelligence_config is not None:
            request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT = (
                form_data.content_extraction.document_intelligence_config.endpoint
            )
            request.app.state.config.DOCUMENT_INTELLIGENCE_KEY = (
                form_data.content_extraction.document_intelligence_config.key
            )

    if form_data.chunk is not None:
        request.app.state.config.TEXT_SPLITTER = form_data.chunk.text_splitter
        request.app.state.config.CHUNK_SIZE.set(user.email,form_data.chunk.chunk_size)
        request.app.state.config.CHUNK_OVERLAP.set(user.email,form_data.chunk.chunk_overlap)

    if form_data.youtube is not None:
        request.app.state.config.YOUTUBE_LOADER_LANGUAGE = form_data.youtube.language
        request.app.state.config.YOUTUBE_LOADER_PROXY_URL = form_data.youtube.proxy_url
        request.app.state.YOUTUBE_LOADER_TRANSLATION = form_data.youtube.translation

    if form_data.web is not None:
        request.app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION = (
            # Note: When UI "Bypass SSL verification for Websites"=True then ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION=False
            form_data.web.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION
        )

        # request.app.state.config.ENABLE_RAG_WEB_SEARCH = form_data.web.search.enabled
        # request.app.state.config.RAG_WEB_SEARCH_ENGINE = form_data.web.search.engine

        request.app.state.config.ENABLE_RAG_WEB_SEARCH.set(user.email,form_data.web.search.enabled)
        request.app.state.config.RAG_WEB_SEARCH_ENGINE.set(user.email,form_data.web.search.engine) 

        # request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL = (
        #     form_data.web.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL
        # )

        request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL.set(user.email,
            form_data.web.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL
        )

        request.app.state.config.SEARXNG_QUERY_URL.set(user.email,
            form_data.web.search.searxng_query_url
        )
        request.app.state.config.GOOGLE_PSE_API_KEY.set(user.email,
            form_data.web.search.google_pse_api_key
        )
        request.app.state.config.GOOGLE_PSE_ENGINE_ID.set(user.email,
            form_data.web.search.google_pse_engine_id
        )
        request.app.state.config.BRAVE_SEARCH_API_KEY.set(user.email,
            form_data.web.search.brave_search_api_key
        )
        request.app.state.config.KAGI_SEARCH_API_KEY.set(user.email,
            form_data.web.search.kagi_search_api_key
        )
        request.app.state.config.MOJEEK_SEARCH_API_KEY.set(user.email,
            form_data.web.search.mojeek_search_api_key
        )
        request.app.state.config.BOCHA_SEARCH_API_KEY.set(user.email,
            form_data.web.search.bocha_search_api_key
        )
        request.app.state.config.SERPSTACK_API_KEY.set(user.email,
            form_data.web.search.serpstack_api_key
        )
        request.app.state.config.SERPSTACK_HTTPS.set(user.email,form_data.web.search.serpstack_https)
        request.app.state.config.SERPER_API_KEY.set(user.email,form_data.web.search.serper_api_key)
        request.app.state.config.SERPLY_API_KEY.set(user.email, form_data.web.search.serply_api_key)
        request.app.state.config.TAVILY_API_KEY.set(user.email,form_data.web.search.tavily_api_key)
        request.app.state.config.SEARCHAPI_API_KEY.set(user.email,
            form_data.web.search.searchapi_api_key
        )
        request.app.state.config.SEARCHAPI_ENGINE.set(user.email,
            form_data.web.search.searchapi_engine
        )

        request.app.state.config.SERPAPI_API_KEY.set(user.email,form_data.web.search.serpapi_api_key)
        request.app.state.config.SERPAPI_ENGINE.set(user.email,form_data.web.search.serpapi_engine)

        request.app.state.config.JINA_API_KEY.set(user.email,form_data.web.search.jina_api_key)
        request.app.state.config.BING_SEARCH_V7_ENDPOINT.set(user.email,
            form_data.web.search.bing_search_v7_endpoint
        )
        request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY.set(user.email,
            form_data.web.search.bing_search_v7_subscription_key
        )

        request.app.state.config.EXA_API_KEY.set(user.email,form_data.web.search.exa_api_key)

        request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.set(user.email,
            form_data.web.search.result_count
        )
        request.app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS.set(user.email,
            form_data.web.search.concurrent_requests
        )
        request.app.state.config.RAG_WEB_SEARCH_TRUST_ENV.set(user.email,
            form_data.web.search.trust_env
        )
        request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.set(user.email,
            form_data.web.search.domain_filter_list
        )
        request.app.state.config.RAG_WEB_SEARCH_WEBSITE_BLOCKLIST.set(user.email,
            form_data.web.search.website_blocklist
        )
        request.app.state.config.RAG_WEB_SEARCH_INTERNAL_FACILITIES_SITES.set(user.email,
            form_data.web.search.internal_facilities_sites
        )

    return {
        "status": True,
        "pdf_extract_images": request.app.state.config.PDF_EXTRACT_IMAGES,
        "RAG_FULL_CONTEXT": request.app.state.config.RAG_FULL_CONTEXT.get(user.email),
        "BYPASS_EMBEDDING_AND_RETRIEVAL": request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL,
        "file": {
            "max_size": request.app.state.config.FILE_MAX_SIZE,
            "max_count": request.app.state.config.FILE_MAX_COUNT,
        },
        "content_extraction": {
            "engine": request.app.state.config.CONTENT_EXTRACTION_ENGINE,
            "tika_server_url": request.app.state.config.TIKA_SERVER_URL,
            "document_intelligence_config": {
                "endpoint": request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT,
                "key": request.app.state.config.DOCUMENT_INTELLIGENCE_KEY,
            },
        },
        "chunk": {
            "text_splitter": request.app.state.config.TEXT_SPLITTER,
            "chunk_size": request.app.state.config.CHUNK_SIZE.get(user.email),
            "chunk_overlap": request.app.state.config.CHUNK_OVERLAP.get(user.email),
        },
        "youtube": {
            "language": request.app.state.config.YOUTUBE_LOADER_LANGUAGE,
            "proxy_url": request.app.state.config.YOUTUBE_LOADER_PROXY_URL,
            "translation": request.app.state.YOUTUBE_LOADER_TRANSLATION,
        },
        "web": {
            "ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION": request.app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
            "BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL": request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL.get(user.email),
            "search": {
                "enabled": request.app.state.config.ENABLE_RAG_WEB_SEARCH.get(user.email),
                "engine": request.app.state.config.RAG_WEB_SEARCH_ENGINE.get(user.email),
                "searxng_query_url": request.app.state.config.SEARXNG_QUERY_URL.get(user.email),
                "google_pse_api_key": request.app.state.config.GOOGLE_PSE_API_KEY.get(user.email),
                "google_pse_engine_id": request.app.state.config.GOOGLE_PSE_ENGINE_ID.get(user.email),
                "brave_search_api_key": request.app.state.config.BRAVE_SEARCH_API_KEY.get(user.email),
                "kagi_search_api_key": request.app.state.config.KAGI_SEARCH_API_KEY.get(user.email),
                "mojeek_search_api_key": request.app.state.config.MOJEEK_SEARCH_API_KEY.get(user.email),
                "bocha_search_api_key": request.app.state.config.BOCHA_SEARCH_API_KEY.get(user.email),
                "serpstack_api_key": request.app.state.config.SERPSTACK_API_KEY.get(user.email),
                "serpstack_https": request.app.state.config.SERPSTACK_HTTPS.get(user.email),
                "serper_api_key": request.app.state.config.SERPER_API_KEY.get(user.email),
                "serply_api_key": request.app.state.config.SERPLY_API_KEY.get(user.email),
                "searchapi_api_key": request.app.state.config.SEARCHAPI_API_KEY.get(user.email),
                "searchapi_engine": request.app.state.config.SEARCHAPI_ENGINE.get(user.email),
                "serpapi_api_key": request.app.state.config.SERPAPI_API_KEY.get(user.email),
                "serpapi_engine": request.app.state.config.SERPAPI_ENGINE.get(user.email),
                "tavily_api_key": request.app.state.config.TAVILY_API_KEY.get(user.email),
                "jina_api_key": request.app.state.config.JINA_API_KEY.get(user.email),
                "bing_search_v7_endpoint": request.app.state.config.BING_SEARCH_V7_ENDPOINT.get(user.email),
                "bing_search_v7_subscription_key": request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY.get(user.email),
                "exa_api_key": request.app.state.config.EXA_API_KEY.get(user.email),
                "result_count": request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(user.email),
                "concurrent_requests": request.app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS.get(user.email),
                "trust_env": request.app.state.config.RAG_WEB_SEARCH_TRUST_ENV.get(user.email),
                "domain_filter_list": request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(user.email),
                "website_blocklist": request.app.state.config.RAG_WEB_SEARCH_WEBSITE_BLOCKLIST.get(user.email),
                "internal_facilities_sites": request.app.state.config.RAG_WEB_SEARCH_INTERNAL_FACILITIES_SITES.get(user.email),
            },
        },
    }


@router.get("/template")
async def get_rag_template(request: Request, user=Depends(get_verified_user)):
    return {
        "status": True,
        "template": request.app.state.config.RAG_TEMPLATE.get(user.email),
    }


@router.get("/query/settings")
async def get_query_settings(request: Request, user=Depends(get_verified_user)):
    return {
        "status": True,
        "template": request.app.state.config.RAG_TEMPLATE.get(user.email),
        "k": request.app.state.config.TOP_K.get(user.email),
        "r": request.app.state.config.RELEVANCE_THRESHOLD,
        "hybrid": request.app.state.config.ENABLE_RAG_HYBRID_SEARCH.get(user.email),
    }


class QuerySettingsForm(BaseModel):
    k: Optional[int] = None
    r: Optional[float] = None
    template: Optional[str] = None
    hybrid: Optional[bool] = None


@router.post("/query/settings/update")
async def update_query_settings(
    request: Request, form_data: QuerySettingsForm, user=Depends(get_admin_user)
):
    request.app.state.config.RAG_TEMPLATE.set(user.email,form_data.template)
    request.app.state.config.TOP_K.set(user.email, form_data.k) if form_data.k else 4
    request.app.state.config.RELEVANCE_THRESHOLD = form_data.r if form_data.r else 1

    if form_data.hybrid is not None:
        request.app.state.config.ENABLE_RAG_HYBRID_SEARCH.set(user.email, form_data.hybrid)
    else:
        request.app.state.config.ENABLE_RAG_HYBRID_SEARCH.set(user.email,False)


    return {
        "status": True,
        "template": request.app.state.config.RAG_TEMPLATE.get(user.email),
        "k": request.app.state.config.TOP_K.get(user.email),
        "r": request.app.state.config.RELEVANCE_THRESHOLD,
        "hybrid": request.app.state.config.ENABLE_RAG_HYBRID_SEARCH.get(user.email),
    }


####################################
#
# Document process and retrieval
#
####################################

def _get_user_chunk_settings(request: Request, user=None):
    """
    Helper function to safely get user chunk settings.
    Handles cases where user is None (background tasks).
    """
    user_email = user.email if user and hasattr(user, 'email') else None
    if user_email:
        chunk_size = request.app.state.config.CHUNK_SIZE.get(user_email)
        chunk_overlap = request.app.state.config.CHUNK_OVERLAP.get(user_email)
    else:
        # Use default chunk size if user is not available
        chunk_size = request.app.state.config.CHUNK_SIZE.get(None) or 1000
        chunk_overlap = request.app.state.config.CHUNK_OVERLAP.get(None) or 200
    return user_email, chunk_size, chunk_overlap


def save_docs_to_vector_db(
    request: Request,
    docs,
    collection_name,
    metadata: Optional[dict] = None,
    overwrite: bool = False,
    split: bool = True,
    add: bool = False,
    user=None,
) -> bool:
    def _get_docs_info(docs: list[Document]) -> str:
        docs_info = set()

        # Trying to select relevant metadata identifying the document.
        for doc in docs:
            metadata = getattr(doc, "metadata", {})
            doc_name = metadata.get("name", "")
            if not doc_name:
                doc_name = metadata.get("title", "")
            if not doc_name:
                doc_name = metadata.get("source", "")
            if doc_name:
                docs_info.add(doc_name)

        return ", ".join(docs_info)

    log.info(
        f"save_docs_to_vector_db: document {_get_docs_info(docs)} {collection_name}"
    )

    # Create OTEL span for embedding generation and vector DB insertion
    with trace_span(
        name="file.embedding.save",
        attributes={
            "collection.name": collection_name,
            "document.count": len(docs),
            "embedding.engine": request.app.state.config.RAG_EMBEDDING_ENGINE if request and hasattr(request.app.state, 'config') else None,
            "embedding.model": request.app.state.config.RAG_EMBEDDING_MODEL if request and hasattr(request.app.state, 'config') else None,
        },
    ) as span:
        try:
            # Check if entries with the same hash (metadata.hash) already exist
            if metadata and "hash" in metadata:
                result = VECTOR_DB_CLIENT.query(
                    collection_name=collection_name,
                    filter={"hash": metadata["hash"]},
                )

                if result is not None:
                    existing_doc_ids = result.ids[0]
                    if existing_doc_ids:
                        log.info(f"Document with hash {metadata['hash']} already exists")
                        raise ValueError(ERROR_MESSAGES.DUPLICATE_CONTENT)

            # BUG #8 fix: Validate docs are not empty before splitting
            if len(docs) == 0:
                error_msg = (
                    f"[Embedding Failed] No documents to process. "
                    f"collection_name={collection_name} | "
                    f"This usually means the file content extraction returned empty text. "
                    f"Check the '[Content Extraction ERROR]' log above for details."
                )
                log.error(error_msg)
                raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

            if split:
                user_email, chunk_size, chunk_overlap = _get_user_chunk_settings(request, user)
                log.info(f"[Splitting] user={user_email or 'background'} | chunk_size={chunk_size} | chunk_overlap={chunk_overlap}")

                if request.app.state.config.TEXT_SPLITTER in ["", "character"]:
                    text_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        add_start_index=True,
                    )
                elif request.app.state.config.TEXT_SPLITTER == "token":
                    log.info(
                        f"Using token text splitter: {request.app.state.config.TIKTOKEN_ENCODING_NAME}"
                    )

                    tiktoken.get_encoding(str(request.app.state.config.TIKTOKEN_ENCODING_NAME))
                    text_splitter = TokenTextSplitter(
                        encoding_name=str(request.app.state.config.TIKTOKEN_ENCODING_NAME),
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        add_start_index=True,
                    )
                else:
                    raise ValueError(ERROR_MESSAGES.DEFAULT("Invalid text splitter"))

                docs = text_splitter.split_documents(docs)
                add_span_event("embedding.split.completed", {"chunk.count": len(docs)})
                if span:
                    set_span_attribute("chunk.count", len(docs))

            if len(docs) == 0:
                # Provide detailed error for debugging empty content issues
                log.error(
                    f"[Embedding Failed] No content to embed after text splitting. "
                    f"collection_name={collection_name} | "
                    f"This usually means the file content extraction returned empty text. "
                    f"Check the '[Content Extraction WARNING]' log above for details and suggestions."
                )
                raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

            texts = [doc.page_content for doc in docs]
            metadatas = [
                {
                    **doc.metadata,
                    **(metadata if metadata else {}),
                    "embedding_config": json.dumps(
                        {
                            "engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
                            "model": request.app.state.config.RAG_EMBEDDING_MODEL,
                        }
                    ),
                }
                for doc in docs
            ]

            # ChromaDB does not like datetime formats
            # for meta-data so convert them to string.
            for metadata in metadatas:
                for key, value in metadata.items():
                    if (
                        isinstance(value, datetime)
                        or isinstance(value, list)
                        or isinstance(value, dict)
                    ):
                        metadata[key] = str(value)

            try:
                if VECTOR_DB_CLIENT.has_collection(collection_name=collection_name):
                    log.info(f"collection {collection_name} already exists")

                    if overwrite:
                        VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
                        log.info(f"deleting existing collection {collection_name}")
                    elif add is False:
                        log.info(
                            f"collection {collection_name} already exists, overwrite is False and add is False"
                        )
                        return True

                log.info(f"adding to collection {collection_name}")
                
                # Get user's API key for embeddings (per-admin key)
                user_email = user.email if user else None
                user_api_key = (
                    request.app.state.config.RAG_OPENAI_API_KEY.get(user_email)
                    if user_email
                    else request.app.state.config.RAG_OPENAI_API_KEY.default
                )
                
                # Get base URL value - handle PersistentConfig objects properly
                if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai" or request.app.state.config.RAG_EMBEDDING_ENGINE == "portkey":
                    base_url_config = request.app.state.config.RAG_OPENAI_API_BASE_URL
                    base_url = (
                        base_url_config.value
                        if hasattr(base_url_config, 'value')
                        else str(base_url_config)
                    )
                    print(f"  [STEP 3.1] Extracted base_url: {base_url}", flush=True)
                    log.info(f"  [STEP 3.1] Extracted base_url: {base_url}")
                    
                    # Fallback to default if empty (from config.py default)
                    if not base_url or base_url.strip() == "" or base_url == "None":
                        base_url = "https://ai-gateway.apps.cloud.rt.nyu.edu/v1"
                        print(f"  [STEP 3.2] ⚠️  Base URL was empty/None, using default: {base_url}", flush=True)
                        log.warning(f"  [STEP 3.2] Base URL was empty/None, using default: {base_url}")
                    else:
                        print(f"  [STEP 3.2] ✅ Using configured base URL: {base_url}", flush=True)
                        log.info(f"  [STEP 3.2] ✅ Using configured base URL: {base_url}")
                    
                    api_key_to_use = user_api_key
                    print(f"  [STEP 3.3] Using OpenAI/Portkey API key (user_api_key)", flush=True)
                    log.info(f"  [STEP 3.3] Using OpenAI/Portkey API key (user_api_key)")
                else:
                    base_url_config = request.app.state.config.RAG_OLLAMA_BASE_URL
                    base_url = (
                        base_url_config.value
                        if hasattr(base_url_config, 'value')
                        else str(base_url_config)
                    )
                    api_key_to_use = request.app.state.config.RAG_OLLAMA_API_KEY
                    print(f"  [STEP 3.1] Using Ollama config: base_url={base_url}", flush=True)
                    log.info(f"  [STEP 3.1] Using Ollama config: base_url={base_url}")
                
                # CRITICAL BUG FIX: Validate API key before creating embedding function
                print(f"  [STEP 4] Validating API key before embedding function creation...", flush=True)
                log.info(f"  [STEP 4] Validating API key before embedding function creation...")
                print(f"    api_key_to_use is None: {api_key_to_use is None}", flush=True)
                print(f"    api_key_to_use is empty: {api_key_to_use == '' if api_key_to_use else 'N/A'}", flush=True)
                print(f"    api_key_to_use length: {len(api_key_to_use) if api_key_to_use else 0}", flush=True)
                log.info(f"    api_key_to_use is None: {api_key_to_use is None}")
                log.info(f"    api_key_to_use is empty: {api_key_to_use == '' if api_key_to_use else 'N/A'}")
                log.info(f"    api_key_to_use length: {len(api_key_to_use) if api_key_to_use else 0}")
                
                if not api_key_to_use or not api_key_to_use.strip():
                    error_msg = (
                        f"❌ CRITICAL BUG: API key is None or empty before embedding function creation. "
                        f"Cannot generate embeddings. "
                        f"user_email={user_email}, engine={request.app.state.config.RAG_EMBEDDING_ENGINE}"
                    )
                    print(f"  [STEP 4] ❌ {error_msg}", flush=True)
                    log.error(f"  [STEP 4] ❌ {error_msg}")
                    raise ValueError(error_msg)
                
                print(f"  [STEP 4] ✅ API key validated", flush=True)
                log.info(f"  [STEP 4] ✅ API key validated")
                
                # Embedding function that sends all texts at once
                print(f"  [STEP 5] Creating embedding function:", flush=True)
                print(f"    engine: {request.app.state.config.RAG_EMBEDDING_ENGINE}", flush=True)
                print(f"    model: {request.app.state.config.RAG_EMBEDDING_MODEL}", flush=True)
                print(f"    base_url: {base_url}", flush=True)
                print(f"    batch_size: {request.app.state.config.RAG_EMBEDDING_BATCH_SIZE}", flush=True)
                print(f"    api_key provided: {api_key_to_use is not None and len(api_key_to_use) > 0}", flush=True)
                log.info(f"  [STEP 5] Creating embedding function:")
                log.info(f"    engine: {request.app.state.config.RAG_EMBEDDING_ENGINE}")
                log.info(f"    model: {request.app.state.config.RAG_EMBEDDING_MODEL}")
                log.info(f"    base_url: {base_url}")
                log.info(f"    batch_size: {request.app.state.config.RAG_EMBEDDING_BATCH_SIZE}")
                log.info(f"    api_key provided: {api_key_to_use is not None and len(api_key_to_use) > 0}")
                
                embedding_function = get_single_batch_embedding_function(
                    request.app.state.config.RAG_EMBEDDING_ENGINE,
                    request.app.state.config.RAG_EMBEDDING_MODEL,
                    request.app.state.ef,
                    base_url,
                    api_key_to_use,
                    request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
                )
                
                print(f"  [STEP 5.1] Embedding function created:", flush=True)
                print(f"    embedding_function is None: {embedding_function is None}", flush=True)
                print(f"    embedding_function type: {type(embedding_function)}", flush=True)
                log.info(f"  [STEP 5.1] Embedding function created:")
                log.info(f"    embedding_function is None: {embedding_function is None}")
                log.info(f"    embedding_function type: {type(embedding_function)}")
                
                if embedding_function is None:
                    error_msg = "Failed to create embedding function - get_single_batch_embedding_function returned None"
                    print(f"  [STEP 5.1] ❌ {error_msg}", flush=True)
                    log.error(f"  [STEP 5.1] ❌ {error_msg}")
                    raise ValueError(error_msg)
                
                print(f"  [STEP 5.1] ✅ Embedding function created successfully", flush=True)
                log.info(f"  [STEP 5.1] ✅ Embedding function created successfully")

                # Process all text chunks in a single API call
                print(f"  [STEP 6] Generating embeddings for {len(texts)} chunks in a single batch", flush=True)
                log.info(f"  [STEP 6] Generating embeddings for {len(texts)} chunks in a single batch")
                
                add_span_event("embedding.generation.started", {"text.count": len(texts)})
                
                try:
                    embeddings = embedding_function(
                        list(map(lambda x: x.replace("\n", " "), texts)), user=user
                    )
                
                    print(f"  [STEP 6.1] Embedding generation result:", flush=True)
                    print(f"    embeddings is None: {embeddings is None}", flush=True)
                    print(f"    embeddings type: {type(embeddings)}", flush=True)
                    print(f"    embeddings length: {len(embeddings) if embeddings else 0}", flush=True)
                    if embeddings and len(embeddings) > 0:
                        print(f"    first embedding length: {len(embeddings[0]) if embeddings[0] else 0}", flush=True)
                    log.info(f"  [STEP 6.1] Embedding generation result:")
                    log.info(f"    embeddings is None: {embeddings is None}")
                    log.info(f"    embeddings type: {type(embeddings)}")
                    log.info(f"    embeddings length: {len(embeddings) if embeddings else 0}")
                    
                    if not embeddings or len(embeddings) == 0:
                        error_msg = "Embedding generation returned empty result"
                        print(f"  [STEP 6.1] ❌ {error_msg}", flush=True)
                        log.error(f"  [STEP 6.1] ❌ {error_msg}")
                        raise ValueError(error_msg)
                    
                    if len(embeddings) != len(texts):
                        error_msg = f"Embedding count mismatch: expected {len(texts)}, got {len(embeddings)}"
                        print(f"  [STEP 6.1] ❌ {error_msg}", flush=True)
                        log.error(f"  [STEP 6.1] ❌ {error_msg}")
                        raise ValueError(error_msg)
                    
                    print(f"  [STEP 6.1] ✅ Embeddings generated successfully", flush=True)
                    log.info(f"  [STEP 6.1] ✅ Embeddings generated successfully")
                    add_span_event("embedding.generation.completed", {"embedding.count": len(embeddings) if embeddings else 0})
                except Exception as embed_error:
                    error_msg = f"Failed to generate embeddings: {embed_error}"
                    print(f"  [STEP 6] ❌ {error_msg}", flush=True)
                    log.error(f"  [STEP 6] ❌ {error_msg}", exc_info=True)
                    add_span_event("embedding.generation.failed", {
                        "error.type": type(embed_error).__name__,
                        "error.message": str(embed_error)[:200],
                    })
                    raise

                print(f"  [STEP 7] Preparing items for vector DB insertion:", flush=True)
                print(f"    collection_name: {collection_name}", flush=True)
                print(f"    items count: {len(texts)}", flush=True)
                log.info(f"  [STEP 7] Preparing items for vector DB insertion:")
                log.info(f"    collection_name: {collection_name}, items count: {len(texts)}")
                
                items = [
                    {
                        "id": str(uuid.uuid4()),
                        "text": text,
                        "vector": embeddings[idx],
                        "metadata": metadatas[idx],
                    }
                    for idx, text in enumerate(texts)
                ]
                
                print(f"  [STEP 7.1] Items prepared, inserting into vector DB...", flush=True)
                log.info(f"  [STEP 7.1] Items prepared, inserting into vector DB...")

                add_span_event("vector_db.insert.started", {"item.count": len(items)})

                try:
                    VECTOR_DB_CLIENT.insert(
                        collection_name=collection_name,
                        items=items,
                    )
                    print(f"  [STEP 7.1] ✅ Successfully inserted {len(items)} items into collection: {collection_name}", flush=True)
                    log.info(f"  [STEP 7.1] ✅ Successfully inserted {len(items)} items into collection: {collection_name}")
                    add_span_event("vector_db.insert.completed", {"item.count": len(items)})
                except Exception as insert_error:
                    error_msg = f"Failed to insert into vector DB collection {collection_name}: {insert_error}"
                    print(f"  [STEP 7.1] ❌ {error_msg}", flush=True)
                    log.error(f"  [STEP 7.1] ❌ {error_msg}", exc_info=True)
                    add_span_event("vector_db.insert.failed", {
                        "error.type": type(insert_error).__name__,
                        "error.message": str(insert_error)[:200],
                    })
                    raise

                print(f"[EMBEDDING] ✅ Embeddings saved successfully", flush=True)
                log.info(f"[EMBEDDING] ✅ Embeddings saved successfully")
                print("=" * 80, flush=True)
                log.info("=" * 80)

                return True
            except Exception as e:
                log.exception(e)
                add_span_event("file.embedding.save.error", {
                    "error.type": type(e).__name__,
                    "error.message": str(e)[:200],
                })
                raise e
        except Exception as e:
            log.exception(e)
            add_span_event("file.embedding.save.error", {
                "error.type": type(e).__name__,
                "error.message": str(e)[:200],
            })
            raise e


def get_embeddings_with_fallback(
    embedding_engine: str,
    embedding_model: str,
    embedding_function: Callable,
    url: str,
    key: str,
    embedding_batch_size: int,
    texts: list[str],
    get_single_batch_embedding_function: Callable,
    get_embedding_function: Callable,
    user: Optional[Any] = None,
    backoff: bool = True,
) -> list[list[float]]:
    """
    Generate embeddings with a fallback mechanism to the default method of OpenWebUI with multiple API calls for each chunk

    Returns:
        list[list[float]]: List of embeddings for the input texts.
    """
    # Create OTEL span for embedding API calls
    with trace_span(
        name="file.embedding.generate",
        attributes={
            "embedding.engine": embedding_engine,
            "embedding.model": embedding_model,
            "text.count": len(texts),
            "embedding.batch_size": embedding_batch_size,
        },
    ) as span:
        try:
            # First, try single batch embedding function
            logging.info(f"Generating embeddings for {len(texts)} chunks in a single batch")
            add_span_event("embedding.api.request", {"method": "single_batch"})
            
            single_batch_func = get_single_batch_embedding_function(
                embedding_engine,
                embedding_model,
                embedding_function,
                url,
                key,
                embedding_batch_size,
                backoff=False,
            )

            # Explicitly try to generate embeddings with the single batch function
            result = single_batch_func(texts, user)
            add_span_event("embedding.api.response", {
                "status": "success",
                "method": "single_batch",
                "embedding.count": len(result) if result else 0,
            })
            return result

        except Exception as e:
            # Log the specific error from single batch attempt
            logging.warning(f"Single batch embedding failed. Error: {str(e)}")
            logging.warning(f"Falling back to batched embedding function")
            
            # Set fallback attribute
            if span:
                set_span_attribute("embedding.fallback_used", True)
            add_span_event("embedding.api.fallback", {
                "error.type": type(e).__name__,
                "error.message": str(e)[:200],
            })

            # Fallback to the original get_embedding_function
            fallback_func = get_embedding_function(
                embedding_engine,
                embedding_model,
                embedding_function,
                url,
                key,
                embedding_batch_size,
                backoff=True,
            )

            # Return the result from the fallback function
            try:
                result = fallback_func(texts, user)
                add_span_event("embedding.api.response", {
                    "status": "success",
                    "method": "fallback",
                    "embedding.count": len(result) if result else 0,
                })
                return result
            except Exception as fallback_error:
                add_span_event("embedding.api.fallback_failed", {
                    "error.type": type(fallback_error).__name__,
                    "error.message": str(fallback_error)[:200],
                })
                raise


def save_docs_to_multiple_collections(
    request: Request,
    docs,
    collections: list[str],
    metadata: Optional[dict] = None,
    overwrite: bool = False,
    split: bool = True,
    user=None,
) -> bool:
    """
    Save documents to multiple collections using a single embedding operation
    """

    def _get_docs_info(docs: list[Document]) -> str:
        docs_info = set()

        # Trying to select relevant metadata identifying the document.
        for doc in docs:
            metadata = getattr(doc, "metadata", {})
            doc_name = metadata.get("name", "")
            if not doc_name:
                doc_name = metadata.get("title", "")
            if not doc_name:
                doc_name = metadata.get("source", "")
            if doc_name:
                docs_info.add(doc_name)

        return ", ".join(docs_info)

    log.info(
        f"save_docs_to_multiple_collections: document {_get_docs_info(docs)} to collections {collections}"
    )

    # Check if entries with the same hash (metadata.hash) already exist in any collection (BUG #14 fix)
    if metadata and "hash" in metadata:
        # Check all collections, not just collections[1]
        for collection_name in collections:
            result = VECTOR_DB_CLIENT.query(
                collection_name=collection_name,
                filter={"hash": metadata["hash"]},
            )

            if result is not None:
                existing_doc_ids = result.ids[0]
                if existing_doc_ids:
                    error_msg = f"Document with hash {metadata['hash']} already exists in collection {collection_name}"
                    print(f"[DUPLICATE CHECK] ❌ {error_msg}", flush=True)
                    log.info(error_msg)
                    raise ValueError(ERROR_MESSAGES.DUPLICATE_CONTENT)

    # BUG #8 fix: Validate docs are not empty before splitting
    if len(docs) == 0:
        error_msg = (
            f"[Embedding Failed] No documents to process. "
            f"collections={collections} | "
            f"This usually means the file content extraction returned empty text. "
            f"Check the '[Content Extraction ERROR]' log above for details."
        )
        log.error(error_msg)
        raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

    if split:
        user_email, chunk_size, chunk_overlap = _get_user_chunk_settings(request, user)
        log.info(f"[Splitting] user={user_email or 'background'} | chunk_size={chunk_size} | chunk_overlap={chunk_overlap}")
        if request.app.state.config.TEXT_SPLITTER in ["", "character"]:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                add_start_index=True,
            )
        elif request.app.state.config.TEXT_SPLITTER == "token":
            log.info(
                f"Using token text splitter: {request.app.state.config.TIKTOKEN_ENCODING_NAME}"
            )

            tiktoken.get_encoding(str(request.app.state.config.TIKTOKEN_ENCODING_NAME))
            text_splitter = TokenTextSplitter(
                encoding_name=str(request.app.state.config.TIKTOKEN_ENCODING_NAME),
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                add_start_index=True,
            )
        else:
            raise ValueError(ERROR_MESSAGES.DEFAULT("Invalid text splitter"))

        docs = text_splitter.split_documents(docs)

    if len(docs) == 0:
        # Provide detailed error for debugging empty content issues (multiple collections)
        log.error(
            f"[Embedding Failed] No content to embed after text splitting. "
            f"collections={collections} | "
            f"This usually means the file content extraction returned empty text. "
            f"Check the '[Content Extraction WARNING]' log above for details and suggestions."
        )
        raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

    texts = [doc.page_content for doc in docs]
    metadatas = [
        {
            **doc.metadata,
            **(metadata if metadata else {}),
            "embedding_config": json.dumps(
                {
                    "engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
                    "model": request.app.state.config.RAG_EMBEDDING_MODEL,
                }
            ),
        }
        for doc in docs
    ]

    # ChromaDB does not like datetime formats
    # for meta-data so convert them to string.
    for metadata in metadatas:
        for key, value in metadata.items():
            if (
                isinstance(value, datetime)
                or isinstance(value, list)
                or isinstance(value, dict)
            ):
                metadata[key] = str(value)

    try:
        # Check and prepare collections
        for collection_name in collections:
            if not VECTOR_DB_CLIENT.has_collection(collection_name=collection_name):
                log.info(f"Creating new collection {collection_name}")
            else:
                log.info(f"Collection {collection_name} already exists")
                if overwrite:
                    VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
                    log.info(f"Deleting existing collection {collection_name}")

        # Get user's API key for embeddings (per-admin key)
        print("=" * 80, flush=True)
        print("[EMBEDDING] Starting embedding generation in save_docs_to_multiple_collections", flush=True)
        log.info("=" * 80)
        log.info("[EMBEDDING] Starting embedding generation in save_docs_to_multiple_collections")
        
        user_email = user.email if user else None
        print(f"  [STEP 1] User context:", flush=True)
        print(f"    user is None: {user is None}", flush=True)
        print(f"    user_email: {user_email}", flush=True)
        print(f"    collections: {collections}", flush=True)
        log.info(f"  [STEP 1] User context: user is None={user is None}, user_email={user_email}, collections={collections}")
        
        print(f"  [STEP 2] Retrieving API key from config...", flush=True)
        log.info(f"  [STEP 2] Retrieving API key from config...")
        user_api_key = (
            request.app.state.config.RAG_OPENAI_API_KEY.get(user_email)
            if user_email
            else request.app.state.config.RAG_OPENAI_API_KEY.default
        )
        
        print(f"  [STEP 2.1] API key retrieval result:", flush=True)
        print(f"    user_api_key is None: {user_api_key is None}", flush=True)
        print(f"    user_api_key is empty: {user_api_key == '' if user_api_key else 'N/A'}", flush=True)
        print(f"    user_api_key length: {len(user_api_key) if user_api_key else 0}", flush=True)
        if user_api_key:
            api_key_preview = user_api_key[-4:] if len(user_api_key) >= 4 else '***'
            print(f"    user_api_key ends with: ...{api_key_preview}", flush=True)
        log.info(f"  [STEP 2.1] API key retrieval result:")
        log.info(f"    user_api_key is None: {user_api_key is None}")
        log.info(f"    user_api_key is empty: {user_api_key == '' if user_api_key else 'N/A'}")
        log.info(f"    user_api_key length: {len(user_api_key) if user_api_key else 0}")
        
        # CRITICAL BUG FIX: Validate API key before use
        if not user_api_key or not user_api_key.strip():
            error_msg = (
                f"❌ CRITICAL BUG: No embedding API key found for user {user_email}. "
                f"Cannot generate embeddings. "
                f"Please ensure: 1) Admin has configured API key in Settings > Documents, "
                f"2) User is in a group created by that admin, 3) API key is not None/empty"
            )
            print(f"  [STEP 2.2] ❌ {error_msg}", flush=True)
            log.error(f"  [STEP 2.2] ❌ {error_msg}")
            raise ValueError(error_msg)
        
        print(f"  [STEP 2.2] ✅ API key validated", flush=True)
        log.info(f"  [STEP 2.2] ✅ API key validated")
        
        # Get base URL value - handle PersistentConfig objects properly
        print(f"  [STEP 3] Getting base URL for embedding engine: {request.app.state.config.RAG_EMBEDDING_ENGINE}", flush=True)
        log.info(f"  [STEP 3] Getting base URL for embedding engine: {request.app.state.config.RAG_EMBEDDING_ENGINE}")
        
        if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai" or request.app.state.config.RAG_EMBEDDING_ENGINE == "portkey":
            base_url_config = request.app.state.config.RAG_OPENAI_API_BASE_URL
            base_url = (
                base_url_config.value
                if hasattr(base_url_config, 'value')
                else str(base_url_config)
            )
            print(f"  [STEP 3.1] Extracted base_url: {base_url}", flush=True)
            log.info(f"  [STEP 3.1] Extracted base_url: {base_url}")
            
            # Fallback to default if empty (from config.py default)
            if not base_url or base_url.strip() == "" or base_url == "None":
                base_url = "https://ai-gateway.apps.cloud.rt.nyu.edu/v1"
                print(f"  [STEP 3.2] ⚠️  Base URL was empty/None, using default: {base_url}", flush=True)
                log.warning(f"  [STEP 3.2] Base URL was empty/None, using default: {base_url}")
            else:
                print(f"  [STEP 3.2] ✅ Using configured base URL: {base_url}", flush=True)
                log.info(f"  [STEP 3.2] ✅ Using configured base URL: {base_url}")
            
            api_key_to_use = user_api_key
            print(f"  [STEP 3.3] Using OpenAI/Portkey API key (user_api_key)", flush=True)
            log.info(f"  [STEP 3.3] Using OpenAI/Portkey API key (user_api_key)")
        else:
            base_url_config = request.app.state.config.RAG_OLLAMA_BASE_URL
            base_url = (
                base_url_config.value
                if hasattr(base_url_config, 'value')
                else str(base_url_config)
            )
            api_key_to_use = request.app.state.config.RAG_OLLAMA_API_KEY
            print(f"  [STEP 3.1] Using Ollama config: base_url={base_url}", flush=True)
            log.info(f"  [STEP 3.1] Using Ollama config: base_url={base_url}")
        
        # CRITICAL BUG FIX: Validate API key before calling embedding function
        print(f"  [STEP 4] Validating API key before embedding generation...", flush=True)
        log.info(f"  [STEP 4] Validating API key before embedding generation...")
        print(f"    api_key_to_use is None: {api_key_to_use is None}", flush=True)
        print(f"    api_key_to_use is empty: {api_key_to_use == '' if api_key_to_use else 'N/A'}", flush=True)
        print(f"    api_key_to_use length: {len(api_key_to_use) if api_key_to_use else 0}", flush=True)
        log.info(f"    api_key_to_use is None: {api_key_to_use is None}")
        log.info(f"    api_key_to_use is empty: {api_key_to_use == '' if api_key_to_use else 'N/A'}")
        log.info(f"    api_key_to_use length: {len(api_key_to_use) if api_key_to_use else 0}")
        
        if not api_key_to_use or not api_key_to_use.strip():
            error_msg = (
                f"❌ CRITICAL BUG: API key is None or empty before embedding generation. "
                f"Cannot generate embeddings. "
                f"user_email={user_email}, engine={request.app.state.config.RAG_EMBEDDING_ENGINE}"
            )
            print(f"  [STEP 4] ❌ {error_msg}", flush=True)
            log.error(f"  [STEP 4] ❌ {error_msg}")
            raise ValueError(error_msg)
        
        print(f"  [STEP 4] ✅ API key validated", flush=True)
        log.info(f"  [STEP 4] ✅ API key validated")
        
        # Usage of get_embeddings_with_fallback
        print(f"  [STEP 5] Calling get_embeddings_with_fallback:", flush=True)
        print(f"    engine: {request.app.state.config.RAG_EMBEDDING_ENGINE}", flush=True)
        print(f"    model: {request.app.state.config.RAG_EMBEDDING_MODEL}", flush=True)
        print(f"    base_url: {base_url}", flush=True)
        print(f"    batch_size: {request.app.state.config.RAG_EMBEDDING_BATCH_SIZE}", flush=True)
        print(f"    texts count: {len(texts)}", flush=True)
        print(f"    api_key provided: {api_key_to_use is not None and len(api_key_to_use) > 0}", flush=True)
        log.info(f"  [STEP 5] Calling get_embeddings_with_fallback:")
        log.info(f"    engine: {request.app.state.config.RAG_EMBEDDING_ENGINE}")
        log.info(f"    model: {request.app.state.config.RAG_EMBEDDING_MODEL}")
        log.info(f"    base_url: {base_url}")
        log.info(f"    batch_size: {request.app.state.config.RAG_EMBEDDING_BATCH_SIZE}")
        log.info(f"    texts count: {len(texts)}")
        log.info(f"    api_key provided: {api_key_to_use is not None and len(api_key_to_use) > 0}")
        
        try:
            embeddings = get_embeddings_with_fallback(
                request.app.state.config.RAG_EMBEDDING_ENGINE,
                request.app.state.config.RAG_EMBEDDING_MODEL,
                request.app.state.ef,
                base_url,
                api_key_to_use,
                request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
                list(map(lambda x: x.replace("\n", " "), texts)),
                get_single_batch_embedding_function,  # Pass this function
                get_embedding_function,  # Pass this function
                user=user,
            )
            
            print(f"  [STEP 5.1] Embedding generation result:", flush=True)
            print(f"    embeddings is None: {embeddings is None}", flush=True)
            print(f"    embeddings type: {type(embeddings)}", flush=True)
            print(f"    embeddings length: {len(embeddings) if embeddings else 0}", flush=True)
            if embeddings and len(embeddings) > 0:
                print(f"    first embedding length: {len(embeddings[0]) if embeddings[0] else 0}", flush=True)
            log.info(f"  [STEP 5.1] Embedding generation result:")
            log.info(f"    embeddings is None: {embeddings is None}")
            log.info(f"    embeddings type: {type(embeddings)}")
            log.info(f"    embeddings length: {len(embeddings) if embeddings else 0}")
            
            if not embeddings or len(embeddings) == 0:
                error_msg = "Embedding generation returned empty result"
                print(f"  [STEP 5.1] ❌ {error_msg}", flush=True)
                log.error(f"  [STEP 5.1] ❌ {error_msg}")
                raise ValueError(error_msg)
            
            if len(embeddings) != len(texts):
                error_msg = f"Embedding count mismatch: expected {len(texts)}, got {len(embeddings)}"
                print(f"  [STEP 5.1] ❌ {error_msg}", flush=True)
                log.error(f"  [STEP 5.1] ❌ {error_msg}")
                raise ValueError(error_msg)
            
            print(f"  [STEP 5.1] ✅ Embeddings generated successfully", flush=True)
            log.info(f"  [STEP 5.1] ✅ Embeddings generated successfully")
        except Exception as embed_error:
            error_msg = f"Failed to generate embeddings: {embed_error}"
            print(f"  [STEP 5] ❌ {error_msg}", flush=True)
            log.error(f"  [STEP 5] ❌ {error_msg}", exc_info=True)
            raise

        # Insert embeddings into all collections
        print(f"  [STEP 7] Inserting embeddings into {len(collections)} collection(s): {collections}", flush=True)
        log.info(f"  [STEP 7] Inserting embeddings into {len(collections)} collection(s): {collections}")
        
        for idx, collection_name in enumerate(collections):
            print(f"  [STEP 7.{idx+1}] Processing collection: {collection_name}", flush=True)
            log.info(f"  [STEP 7.{idx+1}] Processing collection: {collection_name}")
            
            items = [
                {
                    "id": str(uuid.uuid4()),
                    "text": text,
                    "vector": embeddings[idx],
                    "metadata": metadatas[idx],
                }
                for idx, text in enumerate(texts)
            ]
            
            print(f"    Preparing {len(items)} items for insertion", flush=True)
            log.info(f"    Preparing {len(items)} items for insertion")

            try:
                VECTOR_DB_CLIENT.insert(
                    collection_name=collection_name,
                    items=items,
                )
                print(f"  [STEP 7.{idx+1}] ✅ Successfully inserted into collection: {collection_name}", flush=True)
                log.info(f"  [STEP 7.{idx+1}] ✅ Successfully inserted into collection: {collection_name}")
            except Exception as insert_error:
                error_msg = f"Failed to insert into collection {collection_name}: {insert_error}"
                print(f"  [STEP 7.{idx+1}] ❌ {error_msg}", flush=True)
                log.error(f"  [STEP 7.{idx+1}] ❌ {error_msg}", exc_info=True)
                # BUG FIX: Don't continue if one collection fails - raise exception
                raise ValueError(error_msg)

        print(f"[EMBEDDING] ✅ All embeddings saved successfully", flush=True)
        log.info(f"[EMBEDDING] ✅ All embeddings saved successfully")
        print("=" * 80, flush=True)
        log.info("=" * 80)
        
        return True
    except Exception as e:
        log.exception(e)
        raise e


class ProcessFileForm(BaseModel):
    file_id: str
    content: Optional[str] = None
    collection_name: Optional[str] = None


def _process_file_sync(
    request: Request,
    file_id: str,
    content: Optional[str] = None,
    collection_name: Optional[str] = None,
    knowledge_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """
    Core file processing logic that runs synchronously.
    This is called from background tasks to process files.
    
    Args:
        request: FastAPI Request object
        file_id: ID of the file to process
        content: Optional pre-extracted content
        collection_name: Optional collection name
        knowledge_id: Optional knowledge base ID
        user_id: User ID for logging
    """
    print("=" * 80, flush=True)
    print("[BACKGROUND TASK] Starting _process_file_sync", flush=True)
    print(f"  file_id: {file_id}", flush=True)
    print(f"  user_id: {user_id}", flush=True)
    print(f"  collection_name: {collection_name}", flush=True)
    print(f"  knowledge_id: {knowledge_id}", flush=True)
    print(f"  content provided: {'Yes (' + str(len(content)) + ' chars)' if content else 'No'}", flush=True)
    log.info("=" * 80)
    log.info("[BACKGROUND TASK] Starting _process_file_sync")
    log.info(f"  file_id: {file_id}, user_id: {user_id}, collection_name: {collection_name}, knowledge_id: {knowledge_id}")
    
    try:
        # Get user object if user_id is provided
        print(f"  [STEP 1] Retrieving user object...", flush=True)
        log.info(f"  [STEP 1] Retrieving user object...")
        user = None
        if user_id:
            try:
                user = Users.get_user_by_id(user_id)
                if not user:
                    warning_msg = (
                        f"User {user_id} not found for file processing (file_id={file_id}), "
                        "processing without user context"
                    )
                    print(f"  [STEP 1] ⚠️  {warning_msg}", flush=True)
                    log.warning(warning_msg)
                else:
                    print(f"  [STEP 1] ✅ User retrieved: {user.email} (role: {user.role})", flush=True)
                    log.info(f"  [STEP 1] ✅ User retrieved: {user.email} (role: {user.role})")
            except Exception as user_error:
                warning_msg = (
                    f"Error retrieving user {user_id} for file processing (file_id={file_id}): {user_error}, "
                    "processing without user context"
                )
                print(f"  [STEP 1] ⚠️  {warning_msg}", flush=True)
                log.warning(warning_msg)
        else:
            print(f"  [STEP 1] ⚠️  No user_id provided, processing without user context", flush=True)
            log.warning(f"  [STEP 1] No user_id provided, processing without user context")
        
        # Update status to processing
        print(f"  [STEP 2] Updating file status to 'processing'...", flush=True)
        log.info(f"  [STEP 2] Updating file status to 'processing'...")
        Files.update_file_metadata_by_id(
            file_id,
            {
                "processing_status": "processing",
                "processing_started_at": int(time.time()),
            },
        )
        print(f"  [STEP 2] ✅ File status updated", flush=True)
        log.info(f"  [STEP 2] ✅ File status updated")
        
        print(f"  [STEP 3] Retrieving file object...", flush=True)
        log.info(f"  [STEP 3] Retrieving file object...")
        file = Files.get_file_by_id(file_id)
        if not file:
            error_msg = f"File {file_id} not found for processing (user_id={user_id})"
            print(f"  [STEP 3] ❌ {error_msg}", flush=True)
            log.error(error_msg)
            try:
                Files.update_file_metadata_by_id(
                    file_id,
                    {
                        "processing_status": "error",
                        "processing_error": error_msg,
                    },
                )
            except Exception as update_error:
                log.error(f"Failed to update file status: {update_error}")
            return

        if collection_name is None:
            collection_name = f"file-{file.id}"

        if content:
            # Update the content in the file
            try:
                VECTOR_DB_CLIENT.delete_collection(collection_name=f"file-{file.id}")
            except:
                # Audio file upload pipeline
                pass

            docs = [
                Document(
                    page_content=content.replace("<br/>", "\n"),
                    metadata={
                        **file.meta,
                        "name": file.filename,
                        "created_by": file.user_id,
                        "file_id": file.id,
                        "source": file.filename,
                    },
                )
            ]
            text_content = content
        else:
            # No content provided - need to extract from file or use cached
            docs = None
            text_content = None
            
            # First, check if file has already been processed and exists in vector DB
            if collection_name:
                print(f"  [CACHE CHECK] collection_name provided: {collection_name}", flush=True)
                log.info(f"  [CACHE CHECK] collection_name provided: {collection_name}")
                # BUG FIX: Use collection_name instead of f"file-{file.id}" when provided
                cache_collection = collection_name
                print(f"  [CACHE CHECK] Querying collection: {cache_collection} (not file-{file.id})", flush=True)
                log.info(f"  [CACHE CHECK] Querying collection: {cache_collection} (not file-{file.id})")
                try:
                    result = VECTOR_DB_CLIENT.query(
                        collection_name=cache_collection, filter={"file_id": file.id}
                    )
                    
                    if result is not None and result.ids and len(result.ids) > 0 and len(result.ids[0]) > 0:
                        # File already processed - use existing documents
                        docs = [
                            Document(
                                page_content=result.documents[0][idx],
                                metadata=result.metadatas[0][idx],
                            )
                            for idx, id in enumerate(result.ids[0])
                        ]
                        text_content = " ".join([doc.page_content for doc in docs])
                        log.info(f"[Content Cache Hit] file_id={file.id} | Using existing {len(docs)} chunks from vector DB")
                except Exception as query_error:
                    log.debug(f"Vector DB query failed for file_id={file.id}: {query_error}")
                    # Fall through to extraction
            
            # Also check if file.data already has content
            if docs is None and file.data.get("content", "").strip():
                existing_content = file.data.get("content", "")
                docs = [
                    Document(
                        page_content=existing_content,
                        metadata={
                            **file.meta,
                            "name": file.filename,
                            "created_by": file.user_id,
                            "file_id": file.id,
                            "source": file.filename,
                        },
                    )
                ]
                text_content = existing_content
                log.info(f"[Content Cache Hit] file_id={file.id} | Using existing content from file.data ({len(existing_content)} chars)")
            
            # If still no docs, extract from the actual file
            if docs is None:
                # Process the file and save the content
                file_path = file.path
                if file_path:
                    file_path = Storage.get_file(file_path)
                    
                    # Log extraction engine being used
                    extraction_engine = request.app.state.config.CONTENT_EXTRACTION_ENGINE or "default (PyPDF)"
                    log.info(
                        f"[Content Extraction] file_id={file.id} | filename={file.filename} | "
                        f"content_type={file.meta.get('content_type')} | engine={extraction_engine}"
                    )
                    
                    loader = Loader(
                        engine=request.app.state.config.CONTENT_EXTRACTION_ENGINE,
                        TIKA_SERVER_URL=request.app.state.config.TIKA_SERVER_URL,
                        PDF_EXTRACT_IMAGES=request.app.state.config.PDF_EXTRACT_IMAGES,
                        DOCUMENT_INTELLIGENCE_ENDPOINT=request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT,
                        DOCUMENT_INTELLIGENCE_KEY=request.app.state.config.DOCUMENT_INTELLIGENCE_KEY,
                    )
                    docs = loader.load(
                        file.filename, file.meta.get("content_type"), file_path
                    )
                    
                    # Log extraction results for debugging
                    total_chars = sum(len(doc.page_content) for doc in docs)
                    non_empty_docs = [doc for doc in docs if doc.page_content.strip()]
                    log.info(
                        f"[Content Extraction Result] file_id={file.id} | "
                        f"pages_extracted={len(docs)} | non_empty_pages={len(non_empty_docs)} | "
                        f"total_chars={total_chars}"
                    )
                    
                    # Fail early if extraction returned empty content (BUG #15 fix)
                    if total_chars == 0:
                        file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else "unknown"
                        error_msg = (
                            f"[Content Extraction ERROR] file_id={file.id} | filename={file.filename} | "
                            f"No text content extracted! Possible reasons:\n"
                            f"  - Scanned image PDF (no OCR text layer)\n"
                            f"  - Protected/encrypted file\n"
                            f"  - Unsupported encoding\n"
                            f"  Suggestions:\n"
                            f"  - For scanned PDFs: Enable Document Intelligence (Azure OCR) in Settings > Documents\n"
                            f"  - For better extraction: Configure Tika server\n"
                            f"  - Current engine: {extraction_engine}"
                        )
                        log.error(error_msg)
                        raise ValueError(f"Content extraction returned empty text for file {file.filename}. {error_msg}")

                    docs = [
                        Document(
                            page_content=doc.page_content,
                            metadata={
                                **doc.metadata,
                                "name": file.filename,
                                "created_by": file.user_id,
                                "file_id": file.id,
                                "source": file.filename,
                            },
                        )
                        for doc in docs
                    ]
                else:
                    # No file path - use empty content (should not happen normally)
                    log.warning(f"[Content Extraction] file_id={file.id} | No file path available, using empty content")
                    docs = [
                        Document(
                            page_content="",
                            metadata={
                                **file.meta,
                                "name": file.filename,
                                "created_by": file.user_id,
                                "file_id": file.id,
                                "source": file.filename,
                            },
                        )
                    ]
                text_content = " ".join([doc.page_content for doc in docs])

        log.debug(f"text_content: {text_content}")
        Files.update_file_data_by_id(
            file.id,
            {"content": text_content},
        )

        hash = calculate_sha256_string(text_content)
        Files.update_file_hash_by_id(file.id, hash)
        
        print(f"  [STEP 4] Checking BYPASS_EMBEDDING_AND_RETRIEVAL flag...", flush=True)
        log.info(f"  [STEP 4] Checking BYPASS_EMBEDDING_AND_RETRIEVAL flag...")
        print(f"    BYPASS_EMBEDDING_AND_RETRIEVAL: {request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL}", flush=True)
        log.info(f"    BYPASS_EMBEDDING_AND_RETRIEVAL: {request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL}")

        if not request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL:
            print(f"  [STEP 4] ✅ Embedding and retrieval enabled, proceeding with embedding generation", flush=True)
            log.info(f"  [STEP 4] ✅ Embedding and retrieval enabled, proceeding with embedding generation")
            try:
                # If knowledge_id is provided, we're adding to both collections at once
                if knowledge_id:
                    file_collection = f"file-{file.id}"
                    collections = [file_collection, knowledge_id]
                    
                    print(f"  [STEP 5] Knowledge ID provided, saving to multiple collections:", flush=True)
                    print(f"    collections: {collections}", flush=True)
                    log.info(
                        f"Processing file file_id={file.id}, filename={file.filename} "
                        f"for both file collection and knowledge base: collections={collections}, "
                        f"user_id={user_id}"
                    )

                    result = save_docs_to_multiple_collections(
                        request,
                        docs=docs,
                        collections=collections,
                        metadata={
                            "file_id": file.id,
                            "name": file.filename,
                            "hash": hash,
                        },
                        user=user,  # Use user object if available
                    )

                    # Use file collection name for file metadata
                    print(f"  [STEP 6] Embedding save result: {result}", flush=True)
                    log.info(f"  [STEP 6] Embedding save result: {result}")
                    
                    if result:
                        print(f"  [STEP 6] ✅ Embeddings saved successfully, updating file status to 'completed'", flush=True)
                        log.info(f"  [STEP 6] ✅ Embeddings saved successfully, updating file status to 'completed'")
                        Files.update_file_metadata_by_id(
                            file.id,
                            {
                                "collection_name": file_collection,
                                "processing_status": "completed",
                                "processing_completed_at": int(time.time()),
                            },
                        )
                        print(f"  [STEP 6.1] ✅ File status updated to 'completed'", flush=True)
                        log.info(f"  [STEP 6.1] ✅ File status updated to 'completed'")
                    else:
                        error_msg = "Failed to save to vector DB"
                        print(f"  [STEP 6] ❌ {error_msg}, updating file status to 'error'", flush=True)
                        log.error(f"  [STEP 6] ❌ {error_msg}, updating file status to 'error'")
                        Files.update_file_metadata_by_id(
                            file.id,
                            {
                                "processing_status": "error",
                                "processing_error": error_msg,
                            },
                        )
                        print(f"  [STEP 6.1] ⚠️  File status updated to 'error'", flush=True)
                        log.warning(f"  [STEP 6.1] File status updated to 'error'")
                else:
                    print(f"  [STEP 5] No knowledge ID, saving to single collection:", flush=True)
                    print(f"    collection_name: {collection_name}", flush=True)
                    log.info(f"  [STEP 5] No knowledge ID, saving to single collection: {collection_name}")
                    
                    result = save_docs_to_vector_db(
                        request,
                        docs=docs,
                        collection_name=collection_name,
                        metadata={
                            "file_id": file.id,
                            "name": file.filename,
                            "hash": hash,
                        },
                        add=(True if collection_name else False),
                        user=user,  # Use user object if available
                    )
                    
                    print(f"  [STEP 6] Embedding save result: {result}", flush=True)
                    log.info(f"  [STEP 6] Embedding save result: {result}")

                    if result:
                        print(f"  [STEP 6] ✅ Embeddings saved successfully, updating file status to 'completed'", flush=True)
                        log.info(f"  [STEP 6] ✅ Embeddings saved successfully, updating file status to 'completed'")
                        Files.update_file_metadata_by_id(
                            file.id,
                            {
                                "collection_name": collection_name,
                                "processing_status": "completed",
                                "processing_completed_at": int(time.time()),
                            },
                        )
                    else:
                        Files.update_file_metadata_by_id(
                            file.id,
                            {
                                "processing_status": "error",
                                "processing_error": "Failed to save to vector DB",
                            },
                        )
            except Exception as e:
                error_msg = str(e)
                log.error(
                    f"Error saving file to vector DB: file_id={file.id}, "
                    f"filename={file.filename}, user_id={user_id}, error={error_msg}"
                )
                log.exception(e)
                try:
                    Files.update_file_metadata_by_id(
                        file.id,
                        {
                            "processing_status": "error",
                            "processing_error": error_msg,
                        },
                    )
                except Exception as update_error:
                    log.error(f"Failed to update file status after vector DB error: {update_error}")
        else:
            # Bypass embedding, just mark as completed
            print(f"  [STEP 4] ⚠️  Embedding and retrieval bypassed (BYPASS_EMBEDDING_AND_RETRIEVAL=True)", flush=True)
            log.info(f"  [STEP 4] Embedding and retrieval bypassed (BYPASS_EMBEDDING_AND_RETRIEVAL=True)")
            Files.update_file_metadata_by_id(
                file.id,
                {
                    "processing_status": "completed",
                    "processing_completed_at": int(time.time()),
                },
            )
            print(f"  [STEP 4.1] ✅ File status updated to 'completed' (bypassed)", flush=True)
            log.info(f"  [STEP 4.1] File status updated to 'completed' (bypassed)")
        
        print(f"[BACKGROUND TASK] ✅ File processing completed successfully", flush=True)
        log.info(f"[BACKGROUND TASK] ✅ File processing completed successfully")
        print("=" * 80, flush=True)
        log.info("=" * 80)

    except Exception as e:
        # Consolidated error handling - log and update status
        error_msg = str(e)
        log.error(
            f"Error in background file processing for file_id={file_id}, "
            f"user_id={user_id}, error={error_msg}"
        )
        log.exception(e)
        
        # Update file status to error
        try:
            Files.update_file_metadata_by_id(
                file_id,
                {
                    "processing_status": "error",
                    "processing_error": error_msg,
                },
            )
        except Exception as update_error:
            # If we can't update status, log it but don't fail
            log.error(
                f"Failed to update file status after processing error for file_id={file_id}: {update_error}"
            )


@router.post("/process/file")
def process_file(
    request: Request,
    form_data: ProcessFileForm,
    background_tasks: BackgroundTasks,
    user=Depends(get_verified_user),
    knowledge_id: Optional[
        str
    ] = None,  # Add knowledge_id parameter to signify generating embeddings for both file and knowledge base at once
):
    """
    Process a file and generate embeddings.
    
    Processing runs in the background and the endpoint returns immediately
    with status "processing". The file metadata will be updated with processing status.
    """
    # BUG #8 fix: Validate file_id format before any operations
    try:
        UUID(form_data.file_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file ID format: {form_data.file_id}. File ID must be a valid UUID."
        )
    
    # BUG #7 fix: Cache file object to avoid multiple database fetches
    file = Files.get_file_by_id(form_data.file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    # Cache file object and metadata for reuse throughout the function
    cached_file = file
    cached_meta = file.meta or {}
    
    # Use Redis distributed lock to prevent race conditions in multi-replica deployments
    # This ensures only one pod can start processing a file at a time
    # Lock timeout is configurable via environment variable (default: 1 hour for large files)
    def _safe_int_env(key: str, default: int, min_value: int = 1, max_value: int = 86400) -> int:
        """Safely parse integer environment variable with fallback to default."""
        try:
            value = os.environ.get(key)
            if value is None:
                return default
            parsed = int(value)
            if parsed < min_value or parsed > max_value:
                log.warning(
                    f"Invalid value for {key} (must be between {min_value} and {max_value}): {parsed}, "
                    f"using default {default}"
                )
                return default
            return parsed
        except (ValueError, TypeError) as e:
            log.warning(
                f"Invalid value for {key}: {os.environ.get(key)}, using default {default}. Error: {e}"
            )
            return default
    
    lock_timeout = _safe_int_env("FILE_PROCESSING_LOCK_TIMEOUT", 3600, min_value=60, max_value=86400)  # 1 min to 24 hours
    lock_name = f"open-webui:file_processing_lock:{form_data.file_id}"
    
    processing_lock = None
    lock_acquired = False
    redis_available = True
    status_update_succeeded = False  # BUG #1 fix: Initialize at function level to avoid scope issues
    lock_released = False  # BUG #1 fix: Initialize at function level to avoid scope issues (used in background task block)
    
    try:
        # Validate REDIS_URL before attempting to create lock (BUG #8 fix)
        if not REDIS_URL:
            log.warning("REDIS_URL not configured, falling back to database-level checking")
            redis_available = False
        else:
            processing_lock = RedisLock(
                redis_url=REDIS_URL,
                lock_name=lock_name,
                timeout_secs=lock_timeout,
            )
            # Try to acquire lock - distinguish between "lock held" vs "Redis unavailable" (BUG #2 fix)
            lock_acquired = processing_lock.aquire_lock()
            
            if not lock_acquired:
                # Check if Redis is actually available by testing connection
                # If Redis is down, we'll fall through to database check
                try:
                    # BUG #5 fix: Reuse existing Redis connection from processing_lock instead of creating new one
                    # This is more efficient and avoids exhausting connection pools
                    # BUG #3 fix: No need to create new connection - reuse existing one or skip test
                    if processing_lock and processing_lock.redis:
                        # Reuse the existing connection
                        processing_lock.redis.ping()
                        redis_available = True
                    else:
                        # If processing_lock doesn't have redis, it means initialization failed
                        # Don't create a new connection (resource leak), just mark as unavailable
                        log.warning(
                            f"Redis lock for file {form_data.file_id} has no connection. "
                            "Marking Redis as unavailable."
                        )
                        redis_available = False
                    # Redis is available but lock is held - another pod is processing
                    # BUG #7 fix: Use cached file object instead of fetching again
                    meta = cached_meta
                    current_status = meta.get("processing_status", "processing")
                    
                    log.info(
                        f"File {form_data.file_id} is already being processed (lock held by another pod), "
                        f"skipping duplicate processing request from user {user.id}"
                    )
                    return {
                        "status": current_status,
                        "file_id": form_data.file_id,
                        "filename": cached_file.filename,
                        "message": f"File is already {current_status}. Please wait for completion.",
                        "collection_name": meta.get("collection_name"),
                        "content": None,
                    }
                except Exception as redis_test_error:
                    # Redis is unavailable - fall through to database check
                    log.warning(
                        f"Redis unavailable for file processing lock (file_id={form_data.file_id}): {redis_test_error}. "
                        "Falling back to database-level checking."
                    )
                    redis_available = False
                    lock_acquired = False
    except Exception as lock_init_error:
        # Lock initialization failed - fall back to database check
        log.warning(
            f"Failed to initialize Redis lock for file {form_data.file_id}: {lock_init_error}. "
            "Falling back to database-level checking.",
            exc_info=True  # BUG #6 fix: Include full exception traceback for debugging
        )
        redis_available = False
        lock_acquired = False
    
    # If Redis lock is not available, fall back to database-level checking
    # This provides graceful degradation when Redis is unavailable
    if not redis_available or not lock_acquired:
        # Fallback: Check database status (double-check pattern)
        # BUG #7 fix: Use cached file object, but refresh metadata to get latest status
        # Re-fetch only metadata to get latest processing status
        refreshed_file = Files.get_file_by_id(form_data.file_id)
        if not refreshed_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )
        # Update cached metadata with latest values
        cached_meta = refreshed_file.meta or {}
        # BUG #3 fix: Try to keep cached_file.meta in sync, but don't fail if assignment doesn't work
        # (Pydantic models are mutable by default, but assignment might fail in edge cases)
        try:
            cached_file.meta = cached_meta
        except (AttributeError, TypeError) as assign_error:
            # Assignment failed - not critical, we'll use cached_meta directly
            log.debug(f"Could not update cached_file.meta: {assign_error}, using cached_meta directly")
        meta = cached_meta
        current_status = meta.get("processing_status")
        
        # Check if already processing
        # CRITICAL FIX: Only skip if status is "processing" (job running), not "pending" (job queued)
        if current_status == "processing":
            log.info(
                f"File {form_data.file_id} is already {current_status} "
                f"(Redis unavailable, using database check), "
                f"skipping duplicate processing request from user {user.id}"
            )
            return {
                "status": current_status,
                "file_id": form_data.file_id,
                "filename": cached_file.filename,
                "message": f"File is already {current_status}. Please wait for completion.",
                "collection_name": meta.get("collection_name"),
                "content": None,
            }
        
        # Set initial status (database-level check passed)
        # BUG #2 fix: Use atomic database update to prevent race condition
        # Only update if status is not already "pending" or "processing"
        # This provides some protection against race conditions in fallback path
        try:
            from open_webui.internal.db import get_db, engine
            from sqlalchemy import text
            
            # Detect database type for appropriate SQL syntax
            # BUG #6 fix: Use engine.dialect.name for reliable database type detection
            try:
                is_postgresql = engine.dialect.name == 'postgresql'
            except (AttributeError, Exception) as db_detect_error:
                # Fallback to string matching if dialect.name not available
                log.warning(f"Could not detect database type via dialect.name: {db_detect_error}, using string matching")
                is_postgresql = "postgresql" in str(engine.url) if engine and engine.url else False
            
            with get_db() as db:
                if is_postgresql:
                    # PostgreSQL: Use JSONB functions for atomic update
                    result = db.execute(
                        text("""
                            UPDATE file 
                            SET meta = jsonb_set(
                                COALESCE(meta, '{}'::jsonb),
                                '{processing_status}',
                                '"pending"',
                                true
                            )
                            WHERE id = :file_id
                            AND (
                                meta->>'processing_status' IS NULL 
                                OR meta->>'processing_status' NOT IN ('pending', 'processing')
                            )
                            RETURNING id
                        """),
                        {"file_id": form_data.file_id}
                    )
                else:
                    # SQLite: Use JSON functions (json_set, json_extract)
                    result = db.execute(
                        text("""
                            UPDATE file 
                            SET meta = json_set(
                                COALESCE(meta, '{}'),
                                '$.processing_status',
                                'pending'
                            )
                            WHERE id = :file_id
                            AND (
                                json_extract(meta, '$.processing_status') IS NULL 
                                OR json_extract(meta, '$.processing_status') NOT IN ('pending', 'processing')
                            )
                        """),
                        {"file_id": form_data.file_id}
                    )
                db.commit()
                
                # Check if update actually happened (row was updated)
                # For SQLite, check rowcount; for PostgreSQL, check RETURNING result
                if is_postgresql:
                    updated_row = result.fetchone()
                    update_succeeded = updated_row is not None
                else:
                    update_succeeded = result.rowcount > 0
                
                if not update_succeeded:
                    # Another request already set status to pending/processing
                    # Re-fetch to get current status
                    refreshed_file = Files.get_file_by_id(form_data.file_id)
                    if refreshed_file:
                        meta = refreshed_file.meta or {}
                        current_status = meta.get("processing_status", "processing")
                        log.info(
                            f"File {form_data.file_id} status changed to {current_status} during atomic update, "
                            f"skipping duplicate processing request from user {user.id}"
                        )
                        return {
                            "status": current_status,
                            "file_id": form_data.file_id,
                            "filename": cached_file.filename,
                            "message": f"File is already {current_status}. Please wait for completion.",
                            "collection_name": meta.get("collection_name"),
                            "content": None,
                        }
        except Exception as atomic_update_error:
            # If atomic update fails (e.g., database doesn't support JSON functions), fall back to regular update
            log.warning(
                f"Atomic update failed for file {form_data.file_id}: {atomic_update_error}. "
                "Falling back to regular update (may have race condition).",
                exc_info=True
            )
            # BUG #4 fix: Check return value in fallback path too
            result = Files.update_file_metadata_by_id(
                form_data.file_id,
                {
                    "processing_status": "pending",
                },
            )
            if result is None:
                log.error(
                    f"Failed to update file status in fallback path for file_id={form_data.file_id}: "
                    "update_file_metadata_by_id returned None"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update file processing status. Please try again."
                )
    else:
        # We have the Redis lock, now check status atomically
        # BUG #5 fix: Wrap entire section in try-finally to ensure lock is always released
        # Note: lock_released is initialized at function level to avoid scope issues
        try:
            # BUG #7 fix: Re-fetch only metadata to get latest state (file object cached)
            refreshed_file = Files.get_file_by_id(form_data.file_id)
            if not refreshed_file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
            # Update cached metadata with latest values
            cached_meta = refreshed_file.meta or {}
            # BUG #3 fix: Try to keep cached_file.meta in sync, but don't fail if assignment doesn't work
            # (Pydantic models are mutable by default, but assignment might fail in edge cases)
            try:
                cached_file.meta = cached_meta
            except (AttributeError, TypeError) as assign_error:
                # Assignment failed - not critical, we'll use cached_meta directly
                log.debug(f"Could not update cached_file.meta: {assign_error}, using cached_meta directly")
            meta = cached_meta
            current_status = meta.get("processing_status")
            
            # Check if already processing (double-check after acquiring lock)
            # CRITICAL FIX: Only skip if status is "processing" (job running), not "pending" (job queued)
            # "pending" means job is queued but not started - we should allow re-enqueueing if needed
            # "processing" means job is currently running - we should skip to avoid duplicates
            if current_status == "processing":
                log.info(
                    f"File {form_data.file_id} status is {current_status} after acquiring lock, "
                    f"skipping duplicate processing request from user {user.id}"
                )
                # Release lock before returning (BUG #5 fix)
                if processing_lock and lock_acquired and not lock_released:
                    processing_lock.release_lock()
                    lock_released = True
                    log.debug(f"Released file processing lock for file_id={form_data.file_id} (already processing)")
                return {
                    "status": current_status,
                    "file_id": form_data.file_id,
                    "filename": cached_file.filename,
                    "message": f"File is already {current_status}. Please wait for completion.",
                    "collection_name": meta.get("collection_name"),
                    "content": None,
                }
            # If status is "pending", we can proceed - it means job was queued but may have failed or needs re-enqueueing
            # If status is None/"not_started"/"completed"/"error", we can also proceed
            
            # Set initial status (we have the lock, so this is safe)
            # Status update must succeed before we can proceed
            try:
                # Check return value to detect silent failures
                result = Files.update_file_metadata_by_id(
                    form_data.file_id,
                    {
                        "processing_status": "pending",
                    },
                )
                # Check if update actually succeeded (returns FileModel on success, None on failure)
                if result is None:
                    # Update failed silently - don't release lock
                    log.error(
                        f"Failed to update file status for file_id={form_data.file_id}: "
                        "update_file_metadata_by_id returned None"
                    )
                    status_update_succeeded = False
                    raise Exception("File status update failed: update returned None")
                # Status update succeeded
                status_update_succeeded = True
            except Exception as status_error:
                # Status update failed - don't release lock to prevent another request from starting
                log.error(
                    f"Failed to update file status for file_id={form_data.file_id}: {status_error}. "
                    "Lock will not be released to prevent duplicate processing."
                )
                status_update_succeeded = False
                raise  # Re-raise to let caller know it failed
        except Exception as outer_error:
            # If any other error occurs (e.g., file not found), ensure lock is released
            # Only release if not already released
            if processing_lock and lock_acquired and not lock_released:
                try:
                    processing_lock.release_lock()
                    lock_released = True
                    log.debug(f"Released file processing lock for file_id={form_data.file_id} after error")
                except Exception as release_error:
                    log.error(f"Failed to release lock after error: {release_error}")
            raise  # Re-raise the original error
    
    # Enqueue job to distributed job queue (RQ) if available, otherwise fall back to BackgroundTasks
    # This enables distributed processing across multiple pods in Kubernetes
    # CRITICAL: Keep lock held until we've successfully enqueued job or added BackgroundTask
    # This prevents race conditions where multiple requests could process the same file
    job_id = None
    use_job_queue = False
    job_enqueued = False
    background_task_added = False
    
    # Get the user's embedding API key for the worker (per-admin scoped)
    print("=" * 80, flush=True)
    print("[PROCESS FILE] Starting file processing request", flush=True)
    print(f"  file_id: {form_data.file_id}", flush=True)
    print(f"  user.email: {user.email}", flush=True)
    print(f"  user.id: {user.id}", flush=True)
    print(f"  user.role: {user.role}", flush=True)
    log.info("=" * 80)
    log.info("[PROCESS FILE] Starting file processing request")
    log.info(f"  file_id: {form_data.file_id}, user.email: {user.email}, user.id: {user.id}, user.role: {user.role}")
    
    embedding_api_key = None
    print(f"  [STEP 1] Checking embedding engine: {request.app.state.config.RAG_EMBEDDING_ENGINE}", flush=True)
    log.info(f"  [STEP 1] Checking embedding engine: {request.app.state.config.RAG_EMBEDDING_ENGINE}")
    
    if request.app.state.config.RAG_EMBEDDING_ENGINE in ["openai", "portkey"]:
        print(f"  [STEP 1.1] Engine is OpenAI/Portkey, retrieving API key...", flush=True)
        log.info(f"  [STEP 1.1] Engine is OpenAI/Portkey, retrieving API key...")
        
        embedding_api_key = request.app.state.config.RAG_OPENAI_API_KEY.get(user.email)
        
        print(f"  [STEP 1.2] API key retrieval result:", flush=True)
        print(f"    embedding_api_key is None: {embedding_api_key is None}", flush=True)
        print(f"    embedding_api_key is empty: {embedding_api_key == '' if embedding_api_key else 'N/A'}", flush=True)
        print(f"    embedding_api_key length: {len(embedding_api_key) if embedding_api_key else 0}", flush=True)
        if embedding_api_key:
            api_key_preview = embedding_api_key[-4:] if len(embedding_api_key) >= 4 else '***'
            print(f"    embedding_api_key ends with: ...{api_key_preview}", flush=True)
        log.info(f"  [STEP 1.2] API key retrieval result:")
        log.info(f"    embedding_api_key is None: {embedding_api_key is None}")
        log.info(f"    embedding_api_key is empty: {embedding_api_key == '' if embedding_api_key else 'N/A'}")
        log.info(f"    embedding_api_key length: {len(embedding_api_key) if embedding_api_key else 0}")
        
        if not embedding_api_key or not embedding_api_key.strip():
            error_msg = (
                f"❌ CRITICAL BUG: No embedding API key configured for user {user.email}. "
                f"File processing will fail without an API key. "
                f"Please configure the embedding API key in Settings > Documents > Embedding Model Engine. "
                f"If user is not admin, ensure user is in a group created by an admin who has configured the API key."
            )
            print(f"  [STEP 1.3] ❌ {error_msg}", flush=True)
            log.error(f"  [STEP 1.3] ❌ {error_msg}")
            # Return early with error - don't waste resources on processing that will fail
            return {
                "status": False,
                "file_id": form_data.file_id,
                "error": "No embedding API key configured. Please configure in Settings > Documents.",
            }
        
        print(f"  [STEP 1.3] ✅ API key retrieved and validated", flush=True)
        log.info(f"  [STEP 1.3] ✅ API key retrieved and validated")
    else:
        print(f"  [STEP 1.1] Engine is {request.app.state.config.RAG_EMBEDDING_ENGINE}, skipping OpenAI API key check", flush=True)
        log.info(f"  [STEP 1.1] Engine is {request.app.state.config.RAG_EMBEDDING_ENGINE}, skipping OpenAI API key check")
    
    try:
        # Try to use job queue first if available
        if is_job_queue_available():
            try:
                # Enqueue job to distributed job queue
                job_id = enqueue_file_processing_job(
                    file_id=form_data.file_id,
                    content=form_data.content,
                    collection_name=form_data.collection_name,
                    knowledge_id=knowledge_id,
                    user_id=user.id,
                    embedding_api_key=embedding_api_key,
                )
                
                if job_id is not None:
                    # Successfully enqueued job
                    use_job_queue = True
                    job_enqueued = True
                    log.info(f"Successfully enqueued job {job_id} for file_id={form_data.file_id}")
                else:
                    # Job queue unavailable, will fall back to BackgroundTasks
                    log.warning(
                        f"Job queue unavailable for file_id={form_data.file_id}, "
                        "falling back to BackgroundTasks"
                    )
            except Exception as job_enqueue_error:
                # If job enqueue fails, fall back to BackgroundTasks
                log.warning(
                    f"Failed to enqueue job for file_id={form_data.file_id}: {job_enqueue_error}, "
                    "falling back to BackgroundTasks",
                    exc_info=True
                )
        
        # Fall back to BackgroundTasks if job queue wasn't used
        if not job_enqueued:
            try:
                # Add background task (background_tasks is always provided by FastAPI)
                background_tasks.add_task(
                    _process_file_sync,
                    request=request,
                    file_id=form_data.file_id,
                    content=form_data.content,
                    collection_name=form_data.collection_name,
                    knowledge_id=knowledge_id,
                    user_id=user.id,
                )
                background_task_added = True
                log.debug(f"Added BackgroundTask for file_id={form_data.file_id}")
            except Exception as bg_task_error:
                # If background task addition fails, log and re-raise
                log.error(
                    f"Failed to add BackgroundTask for file_id={form_data.file_id}: {bg_task_error}",
                    exc_info=True
                )
                raise  # Re-raise the error - this will trigger lock release in finally block
        
        # Only mark as successful if we actually enqueued/added a task
        if not (job_enqueued or background_task_added):
            raise Exception("Failed to enqueue job or add BackgroundTask - no task was created")
            
    finally:
        # CRITICAL FIX: Release lock AFTER successfully enqueueing job or adding BackgroundTask
        # This ensures no race condition can occur
        # Only release if we have the lock and haven't released it yet
        if processing_lock and lock_acquired and not lock_released:
            # Only release if status was successfully updated
            # AND either job was enqueued OR background task was added
            if status_update_succeeded and (job_enqueued or background_task_added):
                try:
                    processing_lock.release_lock()
                    lock_released = True
                    log.debug(
                        f"Released file processing lock for file_id={form_data.file_id} "
                        f"after successful task creation (job_enqueued={job_enqueued}, "
                        f"background_task_added={background_task_added})"
                    )
                except Exception as release_error:
                    log.error(f"Failed to release lock after task creation: {release_error}")
            elif not status_update_succeeded:
                log.warning(
                    f"Lock NOT released for file_id={form_data.file_id} due to status update failure. "
                    "Lock will expire after timeout."
                )
            elif not (job_enqueued or background_task_added):
                log.warning(
                    f"Lock NOT released for file_id={form_data.file_id} due to task creation failure. "
                    "Lock will expire after timeout."
                )
    
    # Return immediately with processing status (backward compatible format)
    # Include both old format fields and new status for compatibility
    result = {
        "status": "processing",  # New format
        "file_id": form_data.file_id,
        "filename": cached_file.filename,
        "message": "File processing started in background",
        # Backward compatibility fields (will be None/empty until processing completes)
        "collection_name": None,
        "content": None,
    }
    
    # Add job_id if job was successfully enqueued
    if job_enqueued and job_id:
        result["job_id"] = job_id
    
    return result


class ProcessTextForm(BaseModel):
    name: str
    content: str
    collection_name: Optional[str] = None


@router.post("/process/text")
def process_text(
    request: Request,
    form_data: ProcessTextForm,
    user=Depends(get_verified_user),
):
    collection_name = form_data.collection_name
    if collection_name is None:
        collection_name = calculate_sha256_string(form_data.content)

    docs = [
        Document(
            page_content=form_data.content,
            metadata={"name": form_data.name, "created_by": user.id},
        )
    ]
    text_content = form_data.content
    log.debug(f"text_content: {text_content}")

    result = save_docs_to_vector_db(request, docs, collection_name, user=user)
    if result:
        return {
            "status": True,
            "collection_name": collection_name,
            "content": text_content,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


@router.post("/process/youtube")
def process_youtube_video(
    request: Request, form_data: ProcessUrlForm, user=Depends(get_verified_user)
):
    try:
        collection_name = form_data.collection_name
        if not collection_name:
            collection_name = calculate_sha256_string(form_data.url)[:63]

        loader = YoutubeLoader(
            form_data.url,
            language=request.app.state.config.YOUTUBE_LOADER_LANGUAGE,
            proxy_url=request.app.state.config.YOUTUBE_LOADER_PROXY_URL,
        )

        docs = loader.load()
        content = " ".join([doc.page_content for doc in docs])
        log.debug(f"text_content: {content}")

        save_docs_to_vector_db(
            request, docs, collection_name, overwrite=True, user=user
        )

        return {
            "status": True,
            "collection_name": collection_name,
            "filename": form_data.url,
            "file": {
                "data": {
                    "content": content,
                },
                "meta": {
                    "name": form_data.url,
                },
            },
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.post("/process/web")
def process_web(
    request: Request, form_data: ProcessUrlForm, user=Depends(get_verified_user)
):
    try:
        collection_name = form_data.collection_name
        if not collection_name:
            collection_name = calculate_sha256_string(form_data.url)[:63]

        loader = get_web_loader(
            form_data.url,
            verify_ssl=request.app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
            requests_per_second=request.app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS.get(user.email),
        )
        docs = loader.load()
        content = " ".join([doc.page_content for doc in docs])

        log.debug(f"text_content: {content}")
        save_docs_to_vector_db(
            request, docs, collection_name, overwrite=True, user=user
        )

        return {
            "status": True,
            "collection_name": collection_name,
            "filename": form_data.url,
            "file": {
                "data": {
                    "content": content,
                },
                "meta": {
                    "name": form_data.url,
                },
            },
        }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


def search_web(request: Request, engine: str, query: str, email: str) -> list[SearchResult]:
    """Search the web using a search engine and return the results as a list of SearchResult objects.
    Will look for a search engine API key in environment variables in the following order:
    - SEARXNG_QUERY_URL
    - GOOGLE_PSE_API_KEY + GOOGLE_PSE_ENGINE_ID
    - BRAVE_SEARCH_API_KEY
    - KAGI_SEARCH_API_KEY
    - MOJEEK_SEARCH_API_KEY
    - BOCHA_SEARCH_API_KEY
    - SERPSTACK_API_KEY
    - SERPER_API_KEY
    - SERPLY_API_KEY
    - TAVILY_API_KEY
    - EXA_API_KEY
    - SEARCHAPI_API_KEY + SEARCHAPI_ENGINE (by default `google`)
    - SERPAPI_API_KEY + SERPAPI_ENGINE (by default `google`)
    Args:
        query (str): The query to search for
    """

    # TODO: add playwright to search the web
    if engine == "searxng":
        if request.app.state.config.SEARXNG_QUERY_URL.get(email):
            return search_searxng(
                request.app.state.config.SEARXNG_QUERY_URL.get(email),
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(email),
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(email),
            )
        else:
            raise Exception("No SEARXNG_QUERY_URL found in environment variables")
    elif engine == "google_pse":
        if (
            request.app.state.config.GOOGLE_PSE_API_KEY.get(email)
            and request.app.state.config.GOOGLE_PSE_ENGINE_ID.get(email)
        ):
            return search_google_pse(
                request.app.state.config.GOOGLE_PSE_API_KEY.get(email),
                request.app.state.config.GOOGLE_PSE_ENGINE_ID.get(email),
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(email),
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(email),
            )
        else:
            raise Exception(
                "No GOOGLE_PSE_API_KEY or GOOGLE_PSE_ENGINE_ID found in environment variables"
            )
    elif engine == "brave":
        if request.app.state.config.BRAVE_SEARCH_API_KEY.get(email):
            return search_brave(
                request.app.state.config.BRAVE_SEARCH_API_KEY.get(email),
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(email),
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(email),
            )
        else:
            raise Exception("No BRAVE_SEARCH_API_KEY found in environment variables")
    elif engine == "kagi":
        if request.app.state.config.KAGI_SEARCH_API_KEY.get(email):
            return search_kagi(
                request.app.state.config.KAGI_SEARCH_API_KEY.get(email),
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(email),
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(email),
            )
        else:
            raise Exception("No KAGI_SEARCH_API_KEY found in environment variables")
    elif engine == "mojeek":
        if request.app.state.config.MOJEEK_SEARCH_API_KEY.get(email):
            return search_mojeek(
                request.app.state.config.MOJEEK_SEARCH_API_KEY.get(email),
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(email),
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(email),
            )
        else:
            raise Exception("No MOJEEK_SEARCH_API_KEY found in environment variables")
    elif engine == "bocha":
        if request.app.state.config.BOCHA_SEARCH_API_KEY.get(email):
            return search_bocha(
                request.app.state.config.BOCHA_SEARCH_API_KEY.get(email),
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(email),
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(email),
            )
        else:
            raise Exception("No BOCHA_SEARCH_API_KEY found in environment variables")
    elif engine == "serpstack":
        if request.app.state.config.SERPSTACK_API_KEY.get(email):
            return search_serpstack(
                request.app.state.config.SERPSTACK_API_KEY.get(email),
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(email),
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(email),
                https_enabled=request.app.state.config.SERPSTACK_HTTPS.get(email),
            )
        else:
            raise Exception("No SERPSTACK_API_KEY found in environment variables")
    elif engine == "serper":
        if request.app.state.config.SERPER_API_KEY.get(email):
            return search_serper(
                request.app.state.config.SERPER_API_KEY.get(email),
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(email),
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(email),
            )
        else:
            raise Exception("No SERPER_API_KEY found in environment variables")
    elif engine == "serply":
        if request.app.state.config.SERPLY_API_KEY.get(email):
            return search_serply(
                request.app.state.config.SERPLY_API_KEY.get(email),
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(email),
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(email),
            )
        else:
            raise Exception("No SERPLY_API_KEY found in environment variables")
    elif engine == "duckduckgo":
        return search_duckduckgo(
            query,
            request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(email),
            request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(email),
            request.app.state.config.RAG_WEB_SEARCH_WEBSITE_BLOCKLIST.get(email),
        )
    elif engine == "tavily":
        if request.app.state.config.TAVILY_API_KEY:
            return search_tavily(
                request.app.state.config.TAVILY_API_KEY.get(email),
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(email),
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(email),
                request.app.state.config.RAG_WEB_SEARCH_WEBSITE_BLOCKLIST.get(email),
            )
        else:
            raise Exception("No TAVILY_API_KEY found in environment variables")
    elif engine == "searchapi":
        if request.app.state.config.SEARCHAPI_API_KEY.get(email):
            return search_searchapi(
                request.app.state.config.SEARCHAPI_API_KEY.get(email),
                request.app.state.config.SEARCHAPI_ENGINE.get(email),
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(email),
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(email),
            )
        else:
            raise Exception("No SEARCHAPI_API_KEY found in environment variables")
    elif engine == "serpapi":
        if request.app.state.config.SERPAPI_API_KEY.get(email):
            return search_serpapi(
                request.app.state.config.SERPAPI_API_KEY.get(email),
                request.app.state.config.SERPAPI_ENGINE.get(email),
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(email),
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(email),
            )
        else:
            raise Exception("No SERPAPI_API_KEY found in environment variables")
    elif engine == "jina":
        return search_jina(
            request.app.state.config.JINA_API_KEY.get(email),
            query,
            request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(email),
        )
    elif engine == "bing":
        return search_bing(
            request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY.get(email),
            request.app.state.config.BING_SEARCH_V7_ENDPOINT.get(email),
            str(DEFAULT_LOCALE),
            query,
            request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(email),
            request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(email),
        )
    elif engine == "exa":
        return search_exa(
            request.app.state.config.EXA_API_KEY.get(email),
            query,
            request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT.get(email),
            request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST.get(email),
        )
    else:
        raise Exception("No search engine API key found in environment variables")


@router.post("/process/web/search")
async def process_web_search(
    request: Request, form_data: SearchForm, user=Depends(get_verified_user)
):
    try:
        logging.info(
            f"trying to web search with {request.app.state.config.RAG_WEB_SEARCH_ENGINE.get(user.email), form_data.query}"
        )
        web_results = search_web(
            request, request.app.state.config.RAG_WEB_SEARCH_ENGINE.get(user.email), form_data.query, user.email
        )
    except Exception as e:
        log.exception(e)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.WEB_SEARCH_ERROR(e),
        )

    log.debug(f"web_results: {web_results}")

    try:
        collection_name = form_data.collection_name
        if collection_name == "" or collection_name is None:
            collection_name = f"web-search-{calculate_sha256_string(form_data.query)}"[
                :63
            ]

        urls = [result.link for result in web_results]
        loader = get_web_loader(
            urls,
            verify_ssl=request.app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
            requests_per_second=request.app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS.get(user.email),
            trust_env=request.app.state.config.RAG_WEB_SEARCH_TRUST_ENV.get(user.email),
        )
        docs = await loader.aload()

        if request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL.get(user.email):
            return {
                "status": True,
                "collection_name": None,
                "filenames": urls,
                "docs": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                    }
                    for doc in docs
                ],
                "loaded_count": len(docs),
            }
        else:
            await run_in_threadpool(
                save_docs_to_vector_db,
                request,
                docs,
                collection_name,
                overwrite=True,
                user=user,
            )

            return {
                "status": True,
                "collection_name": collection_name,
                "filenames": urls,
                "loaded_count": len(docs),
            }
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


class QueryDocForm(BaseModel):
    collection_name: str
    query: str
    k: Optional[int] = None
    r: Optional[float] = None
    hybrid: Optional[bool] = None


@router.post("/query/doc")
def query_doc_handler(
    request: Request,
    form_data: QueryDocForm,
    user=Depends(get_verified_user),
):
    try:
        if request.app.state.config.ENABLE_RAG_HYBRID_SEARCH.get(user.email):
            return query_doc_with_hybrid_search(
                collection_name=form_data.collection_name,
                query=form_data.query,
                embedding_function=lambda query: request.app.state.EMBEDDING_FUNCTION(
                    query, user=user
                ),
                k=form_data.k if form_data.k else request.app.state.config.TOP_K.get(user.email),
                reranking_function=request.app.state.rf,
                r=(
                    form_data.r
                    if form_data.r
                    else request.app.state.config.RELEVANCE_THRESHOLD
                ),
                user=user,
            )
        else:
            return query_doc(
                collection_name=form_data.collection_name,
                query_embedding=request.app.state.EMBEDDING_FUNCTION(
                    form_data.query, user=user
                ),
                k=form_data.k if form_data.k else request.app.state.config.TOP_K.get(user.email),
                user=user,
            )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


class QueryCollectionsForm(BaseModel):
    collection_names: list[str]
    query: str
    k: Optional[int] = None
    r: Optional[float] = None
    hybrid: Optional[bool] = None


@router.post("/query/collection")
def query_collection_handler(
    request: Request,
    form_data: QueryCollectionsForm,
    user=Depends(get_verified_user),
):
    try:
        if request.app.state.config.ENABLE_RAG_HYBRID_SEARCH.get(user.email):
            return query_collection_with_hybrid_search(
                collection_names=form_data.collection_names,
                queries=[form_data.query],
                embedding_function=lambda query: request.app.state.EMBEDDING_FUNCTION(
                    query, user=user
                ),
                k=form_data.k if form_data.k else request.app.state.config.TOP_K.get(user.email),
                reranking_function=request.app.state.rf,
                r=(
                    form_data.r
                    if form_data.r
                    else request.app.state.config.RELEVANCE_THRESHOLD
                ),
            )
        else:
            return query_collection(
                collection_names=form_data.collection_names,
                queries=[form_data.query],
                embedding_function=lambda query: request.app.state.EMBEDDING_FUNCTION(
                    query, user=user
                ),
                k=form_data.k if form_data.k else request.app.state.config.TOP_K.get(user.email),
            )

    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


####################################
#
# Vector DB operations
#
####################################


class DeleteForm(BaseModel):
    collection_name: str
    file_id: str


@router.post("/delete")
def delete_entries_from_collection(form_data: DeleteForm, user=Depends(get_admin_user)):
    try:
        if VECTOR_DB_CLIENT.has_collection(collection_name=form_data.collection_name):
            file = Files.get_file_by_id(form_data.file_id)
            hash = file.hash

            VECTOR_DB_CLIENT.delete(
                collection_name=form_data.collection_name,
                metadata={"hash": hash},
            )
            return {"status": True}
        else:
            return {"status": False}
    except Exception as e:
        log.exception(e)
        return {"status": False}


@router.post("/reset/db")
def reset_vector_db(user=Depends(get_admin_user)):
    VECTOR_DB_CLIENT.reset()
    Knowledges.delete_all_knowledge()


@router.post("/reset/uploads")
def reset_upload_dir(user=Depends(get_admin_user)) -> bool:
    folder = f"{UPLOAD_DIR}"
    try:
        # Check if the directory exists
        if os.path.exists(folder):
            # Iterate over all the files and directories in the specified directory
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # Remove the file or link
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # Remove the directory
                except Exception as e:
                    log.exception(f"Failed to delete {file_path}. Reason: {e}")
        else:
            log.warning(f"The directory {folder} does not exist")
    except Exception as e:
        log.exception(f"Failed to process the directory {folder}. Reason: {e}")
    return True


if ENV == "dev":

    @router.get("/ef/{text}")
    async def get_embeddings(request: Request, text: Optional[str] = "Hello World!", user=Depends(get_verified_user)):
        # Pass user to ensure per-user API key is used for embeddings
        return {"result": request.app.state.EMBEDDING_FUNCTION(text, user=user)}


class BatchProcessFilesForm(BaseModel):
    files: List[FileModel]
    collection_name: str


class BatchProcessFilesResult(BaseModel):
    file_id: str
    status: str
    error: Optional[str] = None


class BatchProcessFilesResponse(BaseModel):
    results: List[BatchProcessFilesResult]
    errors: List[BatchProcessFilesResult]


@router.post("/process/files/batch")
def process_files_batch(
    request: Request,
    form_data: BatchProcessFilesForm,
    user=Depends(get_verified_user),
) -> BatchProcessFilesResponse:
    """
    Process a batch of files and save them to the vector database.
    """
    results: List[BatchProcessFilesResult] = []
    errors: List[BatchProcessFilesResult] = []
    collection_name = form_data.collection_name

    # Prepare all documents first
    all_docs: List[Document] = []
    for file in form_data.files:
        try:
            text_content = file.data.get("content", "")

            docs: List[Document] = [
                Document(
                    page_content=text_content.replace("<br/>", "\n"),
                    metadata={
                        **file.meta,
                        "name": file.filename,
                        "created_by": file.user_id,
                        "file_id": file.id,
                        "source": file.filename,
                    },
                )
            ]

            hash = calculate_sha256_string(text_content)
            Files.update_file_hash_by_id(file.id, hash)
            Files.update_file_data_by_id(file.id, {"content": text_content})

            all_docs.extend(docs)
            results.append(BatchProcessFilesResult(file_id=file.id, status="prepared"))

        except Exception as e:
            log.error(f"process_files_batch: Error processing file {file.id}: {str(e)}")
            errors.append(
                BatchProcessFilesResult(file_id=file.id, status="failed", error=str(e))
            )

    # Save all documents in one batch
    if all_docs:
        try:
            save_docs_to_vector_db(
                request=request,
                docs=all_docs,
                collection_name=collection_name,
                add=True,
                user=user,
            )

            # Update all files with collection name
            for result in results:
                Files.update_file_metadata_by_id(
                    result.file_id, {"collection_name": collection_name}
                )
                result.status = "completed"

        except Exception as e:
            log.error(
                f"process_files_batch: Error saving documents to vector DB: {str(e)}"
            )
            for result in results:
                result.status = "failed"
                errors.append(
                    BatchProcessFilesResult(file_id=result.file_id, error=str(e))
                )

    return BatchProcessFilesResponse(results=results, errors=errors)
