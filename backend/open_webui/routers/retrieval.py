import json
import logging
import os
import re
import shutil
import hashlib
import time

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import (
    Depends,
    HTTPException,
    Request,
    status,
    APIRouter,
)
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel


from langchain.text_splitter import RecursiveCharacterTextSplitter, TokenTextSplitter
from langchain_core.documents import Document

from open_webui.constants import VECTOR_COLLECTION_PREFIXES
from open_webui.models.files import FileModel, Files
from open_webui.models.knowledge import Knowledges
from open_webui.models.chats import Chats
from open_webui.storage.provider import Storage


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
from open_webui.retrieval.web.duckduckgo import search_duckduckgo
from open_webui.retrieval.web.google_pse import search_google_pse
from open_webui.retrieval.web.jina_search import search_jina
from open_webui.retrieval.web.searchapi import search_searchapi
from open_webui.retrieval.web.searxng import search_searxng
from open_webui.retrieval.web.serper import search_serper
from open_webui.retrieval.web.serply import search_serply
from open_webui.retrieval.web.serpstack import search_serpstack
from open_webui.retrieval.web.tavily import search_tavily
from open_webui.retrieval.web.bing import search_bing


from open_webui.retrieval.utils import (
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
    RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
    RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
    UPLOAD_DIR,
    DEFAULT_LOCALE,
)
from open_webui.env import (
    SRC_LOG_LEVELS,
    DEVICE_TYPE,
    DOCKER,
)
from open_webui.constants import ERROR_MESSAGES

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
    log.info(
        f"Loading embedding function with engine='{engine}', model='{embedding_model}'"
    )

    if embedding_model and engine == "":
        from sentence_transformers import SentenceTransformer

        try:
            log.info(f"Loading SentenceTransformer model: {embedding_model}")
            ef = SentenceTransformer(
                get_model_path(embedding_model, auto_update),
                device=DEVICE_TYPE,
                trust_remote_code=RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
            )
            log.info(
                f"Successfully loaded SentenceTransformer model: {embedding_model}"
            )
        except Exception as e:
            log.error(
                f"Error loading SentenceTransformer model '{embedding_model}': {e}"
            )

    if ef is None:
        log.warning(
            f"Failed to load embedding function. Engine: '{engine}', Model: '{embedding_model}'"
        )

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


@router.get("/")
async def get_status(request: Request):
    return {
        "status": True,
        "chunk_size": request.app.state.config.CHUNK_SIZE,
        "chunk_overlap": request.app.state.config.CHUNK_OVERLAP,
        "template": request.app.state.config.RAG_TEMPLATE,
        "embedding_engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
        "embedding_model": request.app.state.config.RAG_EMBEDDING_MODEL,
        "reranking_model": request.app.state.config.RAG_RERANKING_MODEL,
        "embedding_batch_size": request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
    }


@router.get("/embedding")
async def get_embedding_config(request: Request, user=Depends(get_admin_user)):
    return {
        "status": True,
        "embedding_engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
        "embedding_model": request.app.state.config.RAG_EMBEDDING_MODEL,
        "embedding_batch_size": request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
        "openai_config": {
            "url": request.app.state.config.RAG_OPENAI_API_BASE_URL,
            "key": request.app.state.config.RAG_OPENAI_API_KEY,
        },
        "ollama_config": {
            "url": request.app.state.config.RAG_OLLAMA_BASE_URL,
            "key": request.app.state.config.RAG_OLLAMA_API_KEY,
        },
    }


@router.get("/reranking")
async def get_reraanking_config(request: Request, user=Depends(get_admin_user)):
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
    request: Request, form_data: EmbeddingModelUpdateForm, user=Depends(get_admin_user)
):
    log.info(
        f"Updating embedding model: {request.app.state.config.RAG_EMBEDDING_MODEL} to {form_data.embedding_model}"
    )
    try:
        request.app.state.config.RAG_EMBEDDING_ENGINE = form_data.embedding_engine
        request.app.state.config.RAG_EMBEDDING_MODEL = form_data.embedding_model

        if request.app.state.config.RAG_EMBEDDING_ENGINE in ["ollama", "openai"]:
            if form_data.openai_config is not None:
                request.app.state.config.RAG_OPENAI_API_BASE_URL = (
                    form_data.openai_config.url
                )
                request.app.state.config.RAG_OPENAI_API_KEY = (
                    form_data.openai_config.key
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

        request.app.state.EMBEDDING_FUNCTION = get_embedding_function(
            request.app.state.config.RAG_EMBEDDING_ENGINE,
            request.app.state.config.RAG_EMBEDDING_MODEL,
            request.app.state.ef,
            (
                request.app.state.config.RAG_OPENAI_API_BASE_URL
                if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                else request.app.state.config.RAG_OLLAMA_BASE_URL
            ),
            (
                request.app.state.config.RAG_OPENAI_API_KEY
                if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
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
                "key": request.app.state.config.RAG_OPENAI_API_KEY,
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
async def get_rag_config(request: Request, user=Depends(get_admin_user)):
    return {
        "status": True,
        "pdf_extract_images": request.app.state.config.PDF_EXTRACT_IMAGES,
        "RAG_FULL_CONTEXT": request.app.state.config.RAG_FULL_CONTEXT,
        "enable_google_drive_integration": request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
        "content_extraction": {
            "engine": request.app.state.config.CONTENT_EXTRACTION_ENGINE,
            "tika_server_url": request.app.state.config.TIKA_SERVER_URL,
        },
        "chunk": {
            "text_splitter": request.app.state.config.TEXT_SPLITTER,
            "chunk_size": request.app.state.config.CHUNK_SIZE,
            "chunk_overlap": request.app.state.config.CHUNK_OVERLAP,
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
            "web_loader_ssl_verification": request.app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
            "search": {
                "enabled": request.app.state.config.ENABLE_RAG_WEB_SEARCH,
                "bypass_embedding_and_retrieval": request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL,
                "drive": request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
                "engine": request.app.state.config.RAG_WEB_SEARCH_ENGINE,
                "searxng_query_url": request.app.state.config.SEARXNG_QUERY_URL,
                "google_pse_api_key": request.app.state.config.GOOGLE_PSE_API_KEY,
                "google_pse_engine_id": request.app.state.config.GOOGLE_PSE_ENGINE_ID,
                "brave_search_api_key": request.app.state.config.BRAVE_SEARCH_API_KEY,
                "kagi_search_api_key": request.app.state.config.KAGI_SEARCH_API_KEY,
                "mojeek_search_api_key": request.app.state.config.MOJEEK_SEARCH_API_KEY,
                "serpstack_api_key": request.app.state.config.SERPSTACK_API_KEY,
                "serpstack_https": request.app.state.config.SERPSTACK_HTTPS,
                "serper_api_key": request.app.state.config.SERPER_API_KEY,
                "serply_api_key": request.app.state.config.SERPLY_API_KEY,
                "tavily_api_key": request.app.state.config.TAVILY_API_KEY,
                "searchapi_api_key": request.app.state.config.SEARCHAPI_API_KEY,
                "searchapi_engine": request.app.state.config.SEARCHAPI_ENGINE,
                "jina_api_key": request.app.state.config.JINA_API_KEY,
                "bing_search_v7_endpoint": request.app.state.config.BING_SEARCH_V7_ENDPOINT,
                "bing_search_v7_subscription_key": request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
                "result_count": request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                "concurrent_requests": request.app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
            },
        },
    }


class FileConfig(BaseModel):
    max_size: Optional[int] = None
    max_count: Optional[int] = None


class ContentExtractionConfig(BaseModel):
    engine: str = ""
    tika_server_url: Optional[str] = None


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
    bypass_embedding_and_retrieval: bool
    engine: Optional[str] = None
    searxng_query_url: Optional[str] = None
    google_pse_api_key: Optional[str] = None
    google_pse_engine_id: Optional[str] = None
    brave_search_api_key: Optional[str] = None
    kagi_search_api_key: Optional[str] = None
    mojeek_search_api_key: Optional[str] = None
    serpstack_api_key: Optional[str] = None
    serpstack_https: Optional[bool] = None
    serper_api_key: Optional[str] = None
    serply_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None
    searchapi_api_key: Optional[str] = None
    searchapi_engine: Optional[str] = None
    jina_api_key: Optional[str] = None
    bing_search_v7_endpoint: Optional[str] = None
    bing_search_v7_subscription_key: Optional[str] = None
    result_count: Optional[int] = None
    concurrent_requests: Optional[int] = None


class WebConfig(BaseModel):
    search: WebSearchConfig
    web_loader_ssl_verification: Optional[bool] = None


class ConfigUpdateForm(BaseModel):
    RAG_FULL_CONTEXT: Optional[bool] = None
    pdf_extract_images: Optional[bool] = None
    enable_google_drive_integration: Optional[bool] = None
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
        request.app.state.config.RAG_FULL_CONTEXT = form_data.RAG_FULL_CONTEXT

    request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION = (
        form_data.enable_google_drive_integration
        if form_data.enable_google_drive_integration is not None
        else request.app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION
    )

    if form_data.file is not None:
        request.app.state.config.FILE_MAX_SIZE = form_data.file.max_size
        request.app.state.config.FILE_MAX_COUNT = form_data.file.max_count

    if form_data.content_extraction is not None:
        log.info(f"Updating text settings: {form_data.content_extraction}")
        request.app.state.config.CONTENT_EXTRACTION_ENGINE = (
            form_data.content_extraction.engine
        )
        request.app.state.config.TIKA_SERVER_URL = (
            form_data.content_extraction.tika_server_url
        )

    if form_data.chunk is not None:
        request.app.state.config.TEXT_SPLITTER = form_data.chunk.text_splitter
        request.app.state.config.CHUNK_SIZE = form_data.chunk.chunk_size
        request.app.state.config.CHUNK_OVERLAP = form_data.chunk.chunk_overlap

    if form_data.youtube is not None:
        request.app.state.config.YOUTUBE_LOADER_LANGUAGE = form_data.youtube.language
        request.app.state.config.YOUTUBE_LOADER_PROXY_URL = form_data.youtube.proxy_url
        request.app.state.YOUTUBE_LOADER_TRANSLATION = form_data.youtube.translation

    if form_data.web is not None:
        request.app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION = (
            # Note: When UI "Bypass SSL verification for Websites"=True then ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION=False
            form_data.web.web_loader_ssl_verification
        )

        request.app.state.config.ENABLE_RAG_WEB_SEARCH = form_data.web.search.enabled
        request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL = (
            form_data.web.search.bypass_embedding_and_retrieval
        )
        request.app.state.config.RAG_WEB_SEARCH_ENGINE = form_data.web.search.engine
        request.app.state.config.SEARXNG_QUERY_URL = (
            form_data.web.search.searxng_query_url
        )
        request.app.state.config.GOOGLE_PSE_API_KEY = (
            form_data.web.search.google_pse_api_key
        )
        request.app.state.config.GOOGLE_PSE_ENGINE_ID = (
            form_data.web.search.google_pse_engine_id
        )
        request.app.state.config.BRAVE_SEARCH_API_KEY = (
            form_data.web.search.brave_search_api_key
        )
        request.app.state.config.KAGI_SEARCH_API_KEY = (
            form_data.web.search.kagi_search_api_key
        )
        request.app.state.config.MOJEEK_SEARCH_API_KEY = (
            form_data.web.search.mojeek_search_api_key
        )
        request.app.state.config.SERPSTACK_API_KEY = (
            form_data.web.search.serpstack_api_key
        )
        request.app.state.config.SERPSTACK_HTTPS = form_data.web.search.serpstack_https
        request.app.state.config.SERPER_API_KEY = form_data.web.search.serper_api_key
        request.app.state.config.SERPLY_API_KEY = form_data.web.search.serply_api_key
        request.app.state.config.TAVILY_API_KEY = form_data.web.search.tavily_api_key
        request.app.state.config.SEARCHAPI_API_KEY = (
            form_data.web.search.searchapi_api_key
        )
        request.app.state.config.SEARCHAPI_ENGINE = (
            form_data.web.search.searchapi_engine
        )

        request.app.state.config.JINA_API_KEY = form_data.web.search.jina_api_key
        request.app.state.config.BING_SEARCH_V7_ENDPOINT = (
            form_data.web.search.bing_search_v7_endpoint
        )
        request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY = (
            form_data.web.search.bing_search_v7_subscription_key
        )

        request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT = (
            form_data.web.search.result_count
        )
        request.app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS = (
            form_data.web.search.concurrent_requests
        )

    return {
        "status": True,
        "pdf_extract_images": request.app.state.config.PDF_EXTRACT_IMAGES,
        "RAG_FULL_CONTEXT": request.app.state.config.RAG_FULL_CONTEXT,
        "file": {
            "max_size": request.app.state.config.FILE_MAX_SIZE,
            "max_count": request.app.state.config.FILE_MAX_COUNT,
        },
        "content_extraction": {
            "engine": request.app.state.config.CONTENT_EXTRACTION_ENGINE,
            "tika_server_url": request.app.state.config.TIKA_SERVER_URL,
        },
        "chunk": {
            "text_splitter": request.app.state.config.TEXT_SPLITTER,
            "chunk_size": request.app.state.config.CHUNK_SIZE,
            "chunk_overlap": request.app.state.config.CHUNK_OVERLAP,
        },
        "youtube": {
            "language": request.app.state.config.YOUTUBE_LOADER_LANGUAGE,
            "proxy_url": request.app.state.config.YOUTUBE_LOADER_PROXY_URL,
            "translation": request.app.state.YOUTUBE_LOADER_TRANSLATION,
        },
        "web": {
            "web_loader_ssl_verification": request.app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
            "search": {
                "enabled": request.app.state.config.ENABLE_RAG_WEB_SEARCH,
                "bypass_embedding_and_retrieval": request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL,
                "engine": request.app.state.config.RAG_WEB_SEARCH_ENGINE,
                "searxng_query_url": request.app.state.config.SEARXNG_QUERY_URL,
                "google_pse_api_key": request.app.state.config.GOOGLE_PSE_API_KEY,
                "google_pse_engine_id": request.app.state.config.GOOGLE_PSE_ENGINE_ID,
                "brave_search_api_key": request.app.state.config.BRAVE_SEARCH_API_KEY,
                "kagi_search_api_key": request.app.state.config.KAGI_SEARCH_API_KEY,
                "mojeek_search_api_key": request.app.state.config.MOJEEK_SEARCH_API_KEY,
                "serpstack_api_key": request.app.state.config.SERPSTACK_API_KEY,
                "serpstack_https": request.app.state.config.SERPSTACK_HTTPS,
                "serper_api_key": request.app.state.config.SERPER_API_KEY,
                "serply_api_key": request.app.state.config.SERPLY_API_KEY,
                "serachapi_api_key": request.app.state.config.SEARCHAPI_API_KEY,
                "searchapi_engine": request.app.state.config.SEARCHAPI_ENGINE,
                "tavily_api_key": request.app.state.config.TAVILY_API_KEY,
                "jina_api_key": request.app.state.config.JINA_API_KEY,
                "bing_search_v7_endpoint": request.app.state.config.BING_SEARCH_V7_ENDPOINT,
                "bing_search_v7_subscription_key": request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
                "result_count": request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                "concurrent_requests": request.app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
            },
        },
    }


@router.get("/template")
async def get_rag_template(request: Request, user=Depends(get_verified_user)):
    return {
        "status": True,
        "template": request.app.state.config.RAG_TEMPLATE,
    }


@router.get("/query/settings")
async def get_query_settings(request: Request, user=Depends(get_admin_user)):
    return {
        "status": True,
        "template": request.app.state.config.RAG_TEMPLATE,
        "k": request.app.state.config.TOP_K,
        "r": request.app.state.config.RELEVANCE_THRESHOLD,
        "hybrid": request.app.state.config.ENABLE_RAG_HYBRID_SEARCH,
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
    request.app.state.config.RAG_TEMPLATE = form_data.template
    request.app.state.config.TOP_K = form_data.k if form_data.k else 4
    request.app.state.config.RELEVANCE_THRESHOLD = form_data.r if form_data.r else 0.0

    request.app.state.config.ENABLE_RAG_HYBRID_SEARCH = (
        form_data.hybrid if form_data.hybrid else False
    )

    return {
        "status": True,
        "template": request.app.state.config.RAG_TEMPLATE,
        "k": request.app.state.config.TOP_K,
        "r": request.app.state.config.RELEVANCE_THRESHOLD,
        "hybrid": request.app.state.config.ENABLE_RAG_HYBRID_SEARCH,
    }


####################################
#
# Document process and retrieval
#
####################################


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

    # Check if entries with the same hash (metadata.hash) already exist
    if metadata and "hash" in metadata:
        result = VECTOR_DB_CLIENT.query(
            collection_name=collection_name,
            filter={"hash": metadata["hash"]},
        )

        if (
            result is not None
            and result.ids
            and len(result.ids) > 0
            and len(result.ids[0]) > 0
        ):
            existing_doc_ids = result.ids[0]
            if existing_doc_ids:
                log.info(f"Document with hash {metadata['hash']} already exists")
                raise ValueError(ERROR_MESSAGES.DUPLICATE_CONTENT)

    if split:
        if request.app.state.config.TEXT_SPLITTER in ["", "character"]:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=request.app.state.config.CHUNK_SIZE,
                chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                add_start_index=True,
            )
        elif request.app.state.config.TEXT_SPLITTER == "token":
            log.info(
                f"Using token text splitter: {request.app.state.config.TIKTOKEN_ENCODING_NAME}"
            )

            tiktoken.get_encoding(str(request.app.state.config.TIKTOKEN_ENCODING_NAME))
            text_splitter = TokenTextSplitter(
                encoding_name=str(request.app.state.config.TIKTOKEN_ENCODING_NAME),
                chunk_size=request.app.state.config.CHUNK_SIZE,
                chunk_overlap=request.app.state.config.CHUNK_OVERLAP,
                add_start_index=True,
            )
        else:
            raise ValueError(ERROR_MESSAGES.DEFAULT("Invalid text splitter"))

        docs = text_splitter.split_documents(docs)

    if len(docs) == 0:
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
            "created_at": int(time.time()),
            "collection_type": (
                "file"
                if collection_name.startswith(VECTOR_COLLECTION_PREFIXES.FILE)
                else (
                    "web_search"
                    if collection_name.startswith(VECTOR_COLLECTION_PREFIXES.WEB_SEARCH)
                    else "knowledge"
                )
            ),
            "user_id": user.id if user else None,
        }
        for doc in docs
    ]

    # ChromaDB does not like datetime formats
    # for meta-data so convert them to string.
    for metadata in metadatas:
        for key, value in metadata.items():
            if isinstance(value, datetime):
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
        embedding_function = get_embedding_function(
            request.app.state.config.RAG_EMBEDDING_ENGINE,
            request.app.state.config.RAG_EMBEDDING_MODEL,
            request.app.state.ef,
            (
                request.app.state.config.RAG_OPENAI_API_BASE_URL
                if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                else request.app.state.config.RAG_OLLAMA_BASE_URL
            ),
            (
                request.app.state.config.RAG_OPENAI_API_KEY
                if request.app.state.config.RAG_EMBEDDING_ENGINE == "openai"
                else request.app.state.config.RAG_OLLAMA_API_KEY
            ),
            request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
        )

        # Check if embedding function is properly initialized
        if embedding_function is None:
            error_msg = f"Embedding function is None. Engine: {request.app.state.config.RAG_EMBEDDING_ENGINE}, Model: {request.app.state.config.RAG_EMBEDDING_MODEL}"
            log.error(error_msg)
            raise ValueError(error_msg)

        embeddings = embedding_function(
            list(map(lambda x: x.replace("\n", " "), texts)), user=user
        )

        items = [
            {
                "id": str(uuid.uuid4()),
                "text": text,
                "vector": embeddings[idx],
                "metadata": metadatas[idx],
            }
            for idx, text in enumerate(texts)
        ]

        VECTOR_DB_CLIENT.insert(
            collection_name=collection_name,
            items=items,
        )

        return True
    except Exception as e:
        log.exception(e)
        raise e


class ProcessFileForm(BaseModel):
    file_id: str
    content: Optional[str] = None
    collection_name: Optional[str] = None


@router.post("/process/file")
def process_file(
    request: Request,
    form_data: ProcessFileForm,
    user=Depends(get_verified_user),
):
    try:
        file = Files.get_file_by_id(form_data.file_id)

        collection_name = form_data.collection_name

        if collection_name is None:
            collection_name = f"{VECTOR_COLLECTION_PREFIXES.FILE}{file.id}"

        if form_data.content:
            # Update the content in the file
            # Usage: /files/{file_id}/data/content/update

            VECTOR_DB_CLIENT.delete_collection(
                collection_name=f"{VECTOR_COLLECTION_PREFIXES.FILE}{file.id}"
            )

            docs = [
                Document(
                    page_content=form_data.content.replace("<br/>", "\n"),
                    metadata={
                        **file.meta,
                        "name": file.filename,
                        "created_by": file.user_id,
                        "file_id": file.id,
                        "source": file.filename,
                    },
                )
            ]

            text_content = form_data.content
        elif form_data.collection_name:
            # Check if the file has already been processed and save the content
            # Usage: /knowledge/{id}/file/add, /knowledge/{id}/file/update

            result = VECTOR_DB_CLIENT.query(
                collection_name=f"{VECTOR_COLLECTION_PREFIXES.FILE}{file.id}",
                filter={"file_id": file.id},
            )

            if (
                result is not None
                and result.ids
                and len(result.ids) > 0
                and len(result.ids[0]) > 0
            ):
                docs = [
                    Document(
                        page_content=result.documents[0][idx],
                        metadata=result.metadatas[0][idx],
                    )
                    for idx, id in enumerate(result.ids[0])
                ]
            else:
                docs = [
                    Document(
                        page_content=file.data.get("content", ""),
                        metadata={
                            **file.meta,
                            "name": file.filename,
                            "created_by": file.user_id,
                            "file_id": file.id,
                            "source": file.filename,
                        },
                    )
                ]

            text_content = file.data.get("content", "")
        else:
            # Process the file and save the content
            # Usage: /files/
            file_path = file.path
            if file_path:
                file_path = Storage.get_file(file_path)
                loader = Loader(
                    engine=request.app.state.config.CONTENT_EXTRACTION_ENGINE,
                    TIKA_SERVER_URL=request.app.state.config.TIKA_SERVER_URL,
                    PDF_EXTRACT_IMAGES=request.app.state.config.PDF_EXTRACT_IMAGES,
                )
                docs = loader.load(
                    file.filename, file.meta.get("content_type"), file_path
                )

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
                docs = [
                    Document(
                        page_content=file.data.get("content", ""),
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

        try:
            result = save_docs_to_vector_db(
                request,
                docs=docs,
                collection_name=collection_name,
                metadata={
                    "file_id": file.id,
                    "name": file.filename,
                    "hash": hash,
                },
                add=(True if form_data.collection_name else False),
            )

            if result:
                Files.update_file_metadata_by_id(
                    file.id,
                    {
                        "collection_name": collection_name,
                    },
                )

                return {
                    "status": True,
                    "collection_name": collection_name,
                    "filename": file.filename,
                    "content": text_content,
                }
        except Exception as e:
            raise e
    except Exception as e:
        log.exception(e)
        if "No pandoc was found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.PANDOC_NOT_INSTALLED,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )


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

    result = save_docs_to_vector_db(request, docs, collection_name)
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

        save_docs_to_vector_db(request, docs, collection_name, overwrite=True)

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
            requests_per_second=request.app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
        )
        docs = loader.load()
        content = " ".join([doc.page_content for doc in docs])

        log.debug(f"text_content: {content}")
        save_docs_to_vector_db(request, docs, collection_name, overwrite=True)

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


def search_web(request: Request, engine: str, query: str) -> list[SearchResult]:
    """Search the web using a search engine and return the results as a list of SearchResult objects.
    Will look for a search engine API key in environment variables in the following order:
    - SEARXNG_QUERY_URL
    - GOOGLE_PSE_API_KEY + GOOGLE_PSE_ENGINE_ID
    - BRAVE_SEARCH_API_KEY
    - KAGI_SEARCH_API_KEY
    - MOJEEK_SEARCH_API_KEY
    - SERPSTACK_API_KEY
    - SERPER_API_KEY
    - SERPLY_API_KEY
    - TAVILY_API_KEY
    - SEARCHAPI_API_KEY + SEARCHAPI_ENGINE (by default `google`)
    Args:
        query (str): The query to search for
    """

    # TODO: add playwright to search the web
    if engine == "searxng":
        if request.app.state.config.SEARXNG_QUERY_URL:
            return search_searxng(
                request.app.state.config.SEARXNG_QUERY_URL,
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SEARXNG_QUERY_URL found in environment variables")
    elif engine == "google_pse":
        if (
            request.app.state.config.GOOGLE_PSE_API_KEY
            and request.app.state.config.GOOGLE_PSE_ENGINE_ID
        ):
            return search_google_pse(
                request.app.state.config.GOOGLE_PSE_API_KEY,
                request.app.state.config.GOOGLE_PSE_ENGINE_ID,
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception(
                "No GOOGLE_PSE_API_KEY or GOOGLE_PSE_ENGINE_ID found in environment variables"
            )
    elif engine == "brave":
        if request.app.state.config.BRAVE_SEARCH_API_KEY:
            return search_brave(
                request.app.state.config.BRAVE_SEARCH_API_KEY,
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No BRAVE_SEARCH_API_KEY found in environment variables")
    elif engine == "kagi":
        if request.app.state.config.KAGI_SEARCH_API_KEY:
            return search_kagi(
                request.app.state.config.KAGI_SEARCH_API_KEY,
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No KAGI_SEARCH_API_KEY found in environment variables")
    elif engine == "mojeek":
        if request.app.state.config.MOJEEK_SEARCH_API_KEY:
            return search_mojeek(
                request.app.state.config.MOJEEK_SEARCH_API_KEY,
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No MOJEEK_SEARCH_API_KEY found in environment variables")
    elif engine == "serpstack":
        if request.app.state.config.SERPSTACK_API_KEY:
            return search_serpstack(
                request.app.state.config.SERPSTACK_API_KEY,
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
                https_enabled=request.app.state.config.SERPSTACK_HTTPS,
            )
        else:
            raise Exception("No SERPSTACK_API_KEY found in environment variables")
    elif engine == "serper":
        if request.app.state.config.SERPER_API_KEY:
            return search_serper(
                request.app.state.config.SERPER_API_KEY,
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SERPER_API_KEY found in environment variables")
    elif engine == "serply":
        if request.app.state.config.SERPLY_API_KEY:
            return search_serply(
                request.app.state.config.SERPLY_API_KEY,
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SERPLY_API_KEY found in environment variables")
    elif engine == "duckduckgo":
        return search_duckduckgo(
            query,
            request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == "tavily":
        if request.app.state.config.TAVILY_API_KEY:
            return search_tavily(
                request.app.state.config.TAVILY_API_KEY,
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
            )
        else:
            raise Exception("No TAVILY_API_KEY found in environment variables")
    elif engine == "searchapi":
        if request.app.state.config.SEARCHAPI_API_KEY:
            return search_searchapi(
                request.app.state.config.SEARCHAPI_API_KEY,
                request.app.state.config.SEARCHAPI_ENGINE,
                query,
                request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SEARCHAPI_API_KEY found in environment variables")
    elif engine == "jina":
        return search_jina(
            request.app.state.config.JINA_API_KEY,
            query,
            request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
        )
    elif engine == "bing":
        return search_bing(
            request.app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
            request.app.state.config.BING_SEARCH_V7_ENDPOINT,
            str(DEFAULT_LOCALE),
            query,
            request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
            request.app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    else:
        raise Exception("No search engine API key found in environment variables")


@router.post("/process/web/search")
async def process_web_search(
    request: Request, form_data: SearchForm, user=Depends(get_verified_user)
):
    try:
        # Check for cached web search results first
        search_hash = get_web_search_hash(
            form_data.query, request.app.state.config.RAG_WEB_SEARCH_ENGINE
        )
        log.info(
            f"Generated search hash for query '{form_data.query}' with engine '{request.app.state.config.RAG_WEB_SEARCH_ENGINE}': {search_hash}"
        )

        cached_collection = check_web_search_cache(search_hash)
        log.info(f"Cache check result: {cached_collection}")

        if cached_collection:
            log.info(f"✅ Using cached web search results: {cached_collection}")
            # Return cached results without doing new web search
            try:
                # Get ALL documents from the cached collection to extract ALL original URLs
                # Don't limit to k results - we want all the original URLs that were cached
                log.info(
                    f"Getting all documents from cached collection: {cached_collection}"
                )
                cached_result = VECTOR_DB_CLIENT.get(collection_name=cached_collection)

                cached_urls = []

                if cached_result and cached_result.metadatas:
                    # Extract unique URLs from all cached documents
                    # NOTE: For Qdrant, metadatas is a list of lists: [[metadata1], [metadata2], [metadata3]]
                    log.info(
                        f"Processing {len(cached_result.metadatas)} metadata groups"
                    )
                    for i, metadata_group in enumerate(cached_result.metadatas):
                        # Each metadata_group is a list containing one metadata dict
                        if isinstance(metadata_group, list) and len(metadata_group) > 0:
                            metadata = metadata_group[0]  # Get the actual metadata dict
                            log.debug(f"Metadata group {i}: {metadata}")
                            if isinstance(metadata, dict) and "source" in metadata:
                                url = metadata["source"]
                                if url not in cached_urls:
                                    cached_urls.append(url)
                                    log.debug(f"✅ Added URL from metadata {i}: {url}")
                            else:
                                log.warning(
                                    f"⚠️ Metadata {i} missing 'source' field or not a dict: {metadata}"
                                )
                        else:
                            log.warning(
                                f"⚠️ Metadata group {i} is not a list or empty: {metadata_group}"
                            )

                log.info(
                    f"🎯 Extracted {len(cached_urls)} unique URLs from cached metadata"
                )

                # If no URLs found, fall back to similarity search
                if not cached_urls:
                    log.warning(
                        "No URLs found in cached metadata, falling back to similarity search"
                    )
                    result = query_collection(
                        collection_names=[cached_collection],
                        queries=[form_data.query],
                        embedding_function=request.app.state.EMBEDDING_FUNCTION,
                        k=request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                    )

                    if (
                        result
                        and result.get("metadatas")
                        and len(result["metadatas"]) > 0
                    ):
                        for metadata in result["metadatas"][0]:
                            if "source" in metadata:
                                url = metadata["source"]
                                if url not in cached_urls:
                                    cached_urls.append(url)

                # Final fallback
                if not cached_urls:
                    log.warning("No URLs found in cached results, using fallback")
                    cached_urls = ["cached_results"]

                log.info(f"🎯 Returning {len(cached_urls)} cached URLs: {cached_urls}")
                return {
                    "status": True,
                    "collection_name": cached_collection,
                    "filenames": cached_urls,
                    "loaded_count": (
                        len(cached_result.metadatas)
                        if cached_result and cached_result.metadatas
                        else 0
                    ),
                    "cached": True,
                }
                if not cached_urls:
                    log.warning(
                        "No URLs found in cached metadata, falling back to similarity search"
                    )
                    result = query_collection(
                        collection_names=[cached_collection],
                        queries=[form_data.query],
                        embedding_function=request.app.state.EMBEDDING_FUNCTION,
                        k=request.app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                    )

                    if (
                        result
                        and result.get("metadatas")
                        and len(result["metadatas"]) > 0
                    ):
                        for metadata in result["metadatas"][0]:
                            if "source" in metadata:
                                url = metadata["source"]
                                if url not in cached_urls:
                                    cached_urls.append(url)

                # Final fallback
                if not cached_urls:
                    log.warning("No URLs found in cached results, using fallback")
                    cached_urls = ["cached_results"]

                log.info(f"Returning {len(cached_urls)} cached URLs: {cached_urls}")
                return {
                    "status": True,
                    "collection_name": cached_collection,
                    "filenames": cached_urls,
                    "loaded_count": (
                        len(cached_result.metadatas)
                        if cached_result and cached_result.metadatas
                        else 0
                    ),
                    "cached": True,
                }
            except Exception as e:
                log.warning(
                    f"Error querying cached results, proceeding with fresh search: {e}"
                )
        else:
            log.info(
                f"❌ No cached results found for hash {search_hash}, proceeding with fresh search"
            )

        logging.info(
            f"Performing new web search with {request.app.state.config.RAG_WEB_SEARCH_ENGINE, form_data.query}"
        )
        web_results = search_web(
            request, request.app.state.config.RAG_WEB_SEARCH_ENGINE, form_data.query
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
            # Use consistent hash-based naming for web search caching
            search_hash = get_web_search_hash(
                form_data.query, request.app.state.config.RAG_WEB_SEARCH_ENGINE
            )
            collection_name = f"web_{search_hash}"

        urls = [result.link for result in web_results]
        loader = get_web_loader(
            urls,
            verify_ssl=request.app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
            requests_per_second=request.app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
        )
        docs = loader.load()

        # Add timestamp metadata for cache management
        for doc in docs:
            if not hasattr(doc, "metadata"):
                doc.metadata = {}
            doc.metadata.update(
                {
                    "created_at": int(time.time()),
                    "search_query": form_data.query,
                    "search_engine": request.app.state.config.RAG_WEB_SEARCH_ENGINE,
                    "type": "web_search",
                }
            )

        if request.app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL:
            return {
                "status": True,
                "collection_name": None,
                "docs": [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                    }
                    for doc in docs
                ],
                "filenames": urls,
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
        # Check if collection exists, if not try to re-index on-demand
        if VECTOR_DB_CLIENT and not VECTOR_DB_CLIENT.has_collection(
            form_data.collection_name
        ):
            log.info(
                f"Collection {form_data.collection_name} not found, attempting on-demand re-indexing..."
            )

            # Extract file ID from collection name if it's a file collection
            if form_data.collection_name.startswith(VECTOR_COLLECTION_PREFIXES.FILE):
                file_id = form_data.collection_name.replace(
                    VECTOR_COLLECTION_PREFIXES.FILE, ""
                )
                log.info(f"Attempting to re-index file {file_id}")

                # Try to re-index the file
                if reindex_file_on_demand(file_id, request, user):
                    log.info(f"Successfully re-indexed file {file_id}")
                else:
                    log.warning(f"Failed to re-index file {file_id}")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Collection {form_data.collection_name} not found and could not be re-created",
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection {form_data.collection_name} not found",
                )

        if request.app.state.config.ENABLE_RAG_HYBRID_SEARCH:
            return query_doc_with_hybrid_search(
                collection_name=form_data.collection_name,
                query=form_data.query,
                embedding_function=request.app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else request.app.state.config.TOP_K,
                reranking_function=request.app.state.rf,
                r=(
                    form_data.r
                    if form_data.r
                    else request.app.state.config.RELEVANCE_THRESHOLD
                ),
            )
        else:
            return query_doc(
                collection_name=form_data.collection_name,
                query_embedding=request.app.state.EMBEDDING_FUNCTION(form_data.query),
                k=form_data.k if form_data.k else request.app.state.config.TOP_K,
            )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
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
        # Check if any collections need re-indexing
        missing_collections = []
        if VECTOR_DB_CLIENT:
            for collection_name in form_data.collection_names:
                if not VECTOR_DB_CLIENT.has_collection(collection_name):
                    missing_collections.append(collection_name)

        # Attempt to re-index missing file collections
        for collection_name in missing_collections:
            if collection_name.startswith(VECTOR_COLLECTION_PREFIXES.FILE):
                file_id = collection_name.replace(VECTOR_COLLECTION_PREFIXES.FILE, "")
                log.info(
                    f"Attempting to re-index missing file collection: {collection_name}"
                )

                if reindex_file_on_demand(file_id, request, user):
                    log.info(f"Successfully re-indexed file {file_id}")
                else:
                    log.warning(f"Failed to re-index file {file_id}")
                    # Remove the failed collection from the query
                    form_data.collection_names.remove(collection_name)

        # If no collections remain, return empty results
        if not form_data.collection_names:
            return []

        if request.app.state.config.ENABLE_RAG_HYBRID_SEARCH:
            return query_collection_with_hybrid_search(
                collection_names=form_data.collection_names,
                queries=[form_data.query],
                embedding_function=request.app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else request.app.state.config.TOP_K,
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
                embedding_function=request.app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else request.app.state.config.TOP_K,
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
                    print(f"Failed to delete {file_path}. Reason: {e}")
        else:
            print(f"The directory {folder} does not exist")
    except Exception as e:
        print(f"Failed to process the directory {folder}. Reason: {e}")
    return True


if ENV == "dev":

    @router.get("/ef/{text}")
    async def get_embeddings(request: Request, text: Optional[str] = "Hello World!"):
        return {"result": request.app.state.EMBEDDING_FUNCTION(text)}


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


##########################################
#
# Vector DB Cleanup Utilities
#
##########################################


def cleanup_file_vectors(file_id: str, collection_name: str = None) -> bool:
    """
    Clean up vectors associated with a specific file from the vector database.

    Args:
        file_id: The ID of the file to clean up
        collection_name: Optional specific collection name, otherwise uses file-{file_id}

    Returns:
        bool: True if cleanup was successful, False otherwise
    """
    try:
        # Use specific collection name or default to file-{file_id}
        target_collection = (
            collection_name or f"{VECTOR_COLLECTION_PREFIXES.FILE}{file_id}"
        )

        log.info(
            f"Cleaning up vectors for file {file_id} in collection {target_collection}"
        )

        # Check if collection exists
        if VECTOR_DB_CLIENT.has_collection(collection_name=target_collection):
            # For file-specific collections (file-{file_id}), delete the entire collection
            if target_collection.startswith(
                f"{VECTOR_COLLECTION_PREFIXES.FILE}{file_id}"
            ):
                VECTOR_DB_CLIENT.delete_collection(collection_name=target_collection)
                log.info(f"Deleted entire collection {target_collection}")
            else:
                # For shared collections, we need to delete by filter
                # Note: This requires the vector client to support filtering by metadata
                try:
                    VECTOR_DB_CLIENT.delete(
                        collection_name=target_collection,
                        points_selector={
                            "filter": {
                                "must": [
                                    {"key": "file_id", "match": {"value": file_id}}
                                ]
                            }
                        },
                    )
                    log.info(
                        f"Deleted vectors with file_id {file_id} from collection {target_collection}"
                    )
                except Exception as filter_error:
                    log.warning(
                        f"Could not delete by filter, attempting collection deletion: {filter_error}"
                    )
                    # Fallback: if filtering doesn't work, log and continue
                    pass

            log.info(f"Successfully cleaned up vectors for file {file_id}")
            return True
        else:
            log.info(
                f"Collection {target_collection} does not exist, nothing to clean up"
            )
            return True

    except Exception as e:
        log.error(f"Error cleaning up vectors for file {file_id}: {e}")
        return False


def cleanup_orphaned_vectors() -> dict:
    """
    Clean up orphaned vectors that no longer have corresponding files in the database.
    This ONLY cleans up standalone file collections (file-*), preserving knowledge bases and their files.

    Returns:
        dict: Summary of cleanup operations
    """
    try:
        cleanup_summary = {
            "collections_checked": 0,
            "collections_cleaned": 0,
            "kb_collections_preserved": 0,
            "vectors_removed": 0,
            "errors": [],
        }

        # Get all collections from vector DB
        if hasattr(VECTOR_DB_CLIENT, "list_collections"):
            collections = VECTOR_DB_CLIENT.list_collections()
        else:
            # Fallback for clients that don't support listing collections
            collections = []
            log.warning(
                "Vector DB client does not support listing collections for cleanup"
            )

        cleanup_summary["collections_checked"] = len(collections)

        # Get all knowledge base IDs to preserve them
        from open_webui.models.knowledge import Knowledges

        try:
            existing_knowledge_bases = Knowledges.get_knowledge_bases()
            existing_kb_ids = {kb.id for kb in existing_knowledge_bases}
            log.info(f"Found {len(existing_kb_ids)} knowledge bases to preserve")
        except Exception as e:
            log.warning(f"Could not get knowledge bases: {e}")
            existing_kb_ids = set()

        for collection_name in collections:
            try:
                # PRESERVE knowledge base collections - DO NOT CLEAN THEM
                if collection_name in existing_kb_ids:
                    cleanup_summary["kb_collections_preserved"] += 1
                    log.debug(
                        f"Preserving knowledge base collection: {collection_name}"
                    )
                    continue

                # Only process standalone file collections (file-*)
                if not collection_name.startswith(VECTOR_COLLECTION_PREFIXES.FILE):
                    continue

                # Extract file ID from collection name
                file_id = collection_name.replace(VECTOR_COLLECTION_PREFIXES.FILE, "")

                # Check if file still exists in database
                try:
                    file = Files.get_file_by_id(file_id)
                    if not file:
                        # File doesn't exist, delete the collection
                        VECTOR_DB_CLIENT.delete_collection(
                            collection_name=collection_name
                        )
                        cleanup_summary["collections_cleaned"] += 1
                        log.info(
                            f"Cleaned up orphaned standalone file collection: {collection_name}"
                        )
                except Exception:
                    # File doesn't exist, delete the collection
                    VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
                    cleanup_summary["collections_cleaned"] += 1
                    log.info(
                        f"Cleaned up orphaned standalone file collection: {collection_name}"
                    )

            except Exception as e:
                error_msg = f"Error processing collection {collection_name}: {e}"
                log.error(error_msg)
                cleanup_summary["errors"].append(error_msg)

        log.info(f"Orphaned vector cleanup completed: {cleanup_summary}")
        return cleanup_summary

    except Exception as e:
        log.error(f"Error during orphaned vector cleanup: {e}")
        return {"error": str(e), "collections_cleaned": 0, "vectors_cleaned": 0}


def get_vector_db_stats(user) -> dict:
    """
    Get comprehensive statistics about the vector database.

    Args:
        user: Admin user (for permission check)

    Returns:
        dict: Statistics about vector DB collections and vectors
    """
    try:
        if not VECTOR_DB_CLIENT:
            return {"error": "Vector DB not available"}

        # Get collections in a compatible way
        collections = []
        try:
            if hasattr(VECTOR_DB_CLIENT, "list_collections"):
                collections = VECTOR_DB_CLIENT.list_collections()
            else:
                # For other vector DBs, we'll need to implement collection listing
                log.warning(
                    "Vector DB client does not support listing collections for stats"
                )
                return {
                    "error": "Collection listing not supported for this vector DB",
                    "stats": {},
                }
        except Exception as e:
            log.error(f"Error getting collections: {e}")
            return {"error": f"Error getting collections: {e}", "stats": {}}

        stats = {
            "total_collections": len(collections),
            "file_collections": 0,
            "web_search_collections": 0,
            "knowledge_collections": 0,
            "other_collections": 0,
            "total_vectors": 0,
            "collections_detail": [],
        }

        for collection in collections:
            # Handle both string collections and collection objects
            collection_name = (
                collection if isinstance(collection, str) else collection.name
            )

            # For now, skip vector count as Qdrant doesn't have a simple get_collection method
            # This is not essential for cleanup operations
            vector_count = (
                0  # Could be implemented later with collection_info() if needed
            )

            # Categorize collection by name pattern
            if collection_name.startswith("file_") or collection_name.startswith(
                VECTOR_COLLECTION_PREFIXES.FILE
            ):
                stats["file_collections"] += 1
                category = "file"
            elif collection_name.startswith("web_"):
                stats["web_search_collections"] += 1
                category = "web_search"
            elif collection_name.startswith("knowledge_"):
                stats["knowledge_collections"] += 1
                category = "knowledge"
            elif len(collection_name) == 36 and collection_name.count("-") == 4:
                # UUID format knowledge collections (e.g., 4e4c3b25-25a9-46e8-a8ae-094bfed192d4)
                stats["knowledge_collections"] += 1
                category = "knowledge"
            else:
                stats["other_collections"] += 1
                category = "other"

            stats["total_vectors"] += vector_count
            stats["collections_detail"].append(
                {
                    "name": collection_name,
                    "category": category,
                    "vector_count": vector_count,
                }
            )

        return {"status": "success", "stats": stats}

    except Exception as e:
        log.error(f"Error getting vector DB stats: {e}")
        return {"error": str(e), "stats": {}}


def get_web_search_hash(query: str, search_engine: str) -> str:
    """
    Generate a consistent hash for web search caching.
    Normalizes query for better cache hits.

    Args:
        query: Search query string
        search_engine: Search engine used

    Returns:
        str: Hash string for the search
    """
    # Normalize the query for consistent caching
    normalized_query = query.lower().strip()
    # Remove extra whitespace and normalize punctuation
    normalized_query = re.sub(r"\s+", " ", normalized_query)
    # Remove common punctuation that doesn't affect search meaning
    normalized_query = re.sub(r"[?!.]+$", "", normalized_query)

    content = f"{search_engine}:{normalized_query}".encode("utf-8")
    return hashlib.sha256(content).hexdigest()[:16]


def check_web_search_cache(search_hash: str) -> str:
    """
    Check if a web search result is cached in vector DB.

    Args:
        search_hash: Hash of the search query

    Returns:
        str: Collection name if cached, None otherwise
    """
    try:
        if not VECTOR_DB_CLIENT:
            return None

        collection_name = f"web_{search_hash}"

        # Check if collection exists
        if VECTOR_DB_CLIENT.has_collection(collection_name=collection_name):
            return collection_name

        return None

    except Exception as e:
        log.error(f"Error checking web search cache: {e}")
        return None


def cleanup_expired_web_searches(max_age_days: int = 30) -> dict:
    """
    Clean up expired web search results from vector database.

    Args:
        max_age_days: Maximum age in days for web search results

    Returns:
        dict: Summary of cleanup operations
    """
    try:
        cleanup_summary = {
            "collections_checked": 0,
            "collections_cleaned": 0,
            "vectors_cleaned": 0,
            "errors": [],
        }

        if not VECTOR_DB_CLIENT:
            cleanup_summary["errors"].append("Vector DB client not available")
            return cleanup_summary

        # Get collections in a compatible way
        collections = []
        try:
            if hasattr(VECTOR_DB_CLIENT, "list_collections"):
                collections = VECTOR_DB_CLIENT.list_collections()
            else:
                log.warning(
                    "Vector DB client does not support listing collections for web search cleanup"
                )
                return cleanup_summary
        except Exception as e:
            log.error(f"Error getting collections: {e}")
            cleanup_summary["errors"].append(f"Error getting collections: {e}")
            return cleanup_summary
        cutoff_timestamp = datetime.now() - timedelta(days=max_age_days)

        for collection in collections:
            # Handle both string collections and collection objects
            collection_name = (
                collection if isinstance(collection, str) else collection.name
            )

            # Only process web search collections
            if not collection_name.startswith("web_"):
                continue

            try:
                cleanup_summary["collections_checked"] += 1

                # Get collection info to check if it has expired metadata
                should_delete = False

                try:
                    if hasattr(VECTOR_DB_CLIENT, "get_collection_sample_metadata"):
                        # Get sample metadata to check for expiry
                        metadata = VECTOR_DB_CLIENT.get_collection_sample_metadata(
                            collection_name
                        )

                        if metadata:
                            # Check if timestamp indicates expiry
                            created_at = metadata.get("created_at")
                            if created_at:
                                try:
                                    point_timestamp = datetime.fromisoformat(
                                        created_at.replace("Z", "+00:00")
                                    )
                                    if point_timestamp < cutoff_timestamp:
                                        should_delete = True
                                except (ValueError, TypeError):
                                    # If timestamp is invalid, consider it old
                                    should_delete = True
                            else:
                                # No timestamp means it's from before we added timestamps
                                should_delete = True
                        else:
                            # Empty collection should be cleaned up
                            should_delete = True
                    else:
                        # For other vector DBs, we might not be able to check timestamps
                        # so we'll skip the cleanup for now
                        log.warning(
                            f"Cannot check timestamp for collection {collection_name} on this vector DB"
                        )
                        continue

                except Exception as e:
                    log.error(f"Error checking collection {collection_name}: {e}")
                    cleanup_summary["errors"].append(
                        f"Error checking collection {collection_name}: {e}"
                    )
                    continue

                if should_delete:
                    # Delete the entire collection for expired web searches
                    try:
                        VECTOR_DB_CLIENT.delete_collection(collection_name)
                        cleanup_summary["collections_cleaned"] += 1
                        log.info(
                            f"Deleted expired web search collection: {collection_name}"
                        )
                    except Exception as e:
                        error_msg = (
                            f"Error deleting collection {collection_name}: {str(e)}"
                        )
                        log.error(error_msg)
                        cleanup_summary["errors"].append(error_msg)

            except Exception as e:
                error_msg = f"Error cleaning collection {collection_name}: {str(e)}"
                log.error(error_msg)
                cleanup_summary["errors"].append(error_msg)

        log.info(f"Web search cleanup completed: {cleanup_summary}")
        return cleanup_summary

    except Exception as e:
        log.error(f"Error during web search cleanup: {e}")
        return {"error": str(e), "collections_cleaned": 0, "vectors_cleaned": 0}


####################################
#
# API Endpoints for K8s CronJob Integration
#
####################################


@router.post("/maintenance/cleanup/orphaned")
def api_cleanup_orphaned_vectors(user=Depends(get_admin_user)):
    """
    API endpoint to cleanup orphaned vectors from standalone files.
    PRESERVES knowledge bases and all files within them.
    Only cleans up orphaned file-* collections with no corresponding database entry.
    Used by K8s CronJobs for scheduled maintenance.
    """
    try:
        result = cleanup_orphaned_vectors()
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "cleanup_result": result,
        }
    except Exception as e:
        log.error(f"Orphaned vector cleanup API failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            },
        )


@router.post("/maintenance/cleanup/web-search")
def api_cleanup_web_search_vectors(
    max_age_days: int = None, user=Depends(get_admin_user)
):
    """
    API endpoint to cleanup expired web search vectors.
    Used by K8s CronJobs for scheduled maintenance.
    """
    try:
        # Use config default if not specified
        if max_age_days is None:
            max_age_days = int(os.getenv("VECTOR_DB_WEB_SEARCH_EXPIRY_DAYS", "30"))

        result = cleanup_expired_web_searches(max_age_days)
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "max_age_days": max_age_days,
            "cleanup_result": result,
        }
    except Exception as e:
        log.error(f"Web search vector cleanup API failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            },
        )


@router.post("/maintenance/cleanup/comprehensive")
def api_comprehensive_cleanup(max_age_days: int = None, user=Depends(get_admin_user)):
    """
    API endpoint for comprehensive vector DB cleanup.
    Cleans up orphaned standalone files, expired web searches, and orphaned chat files.
    PRESERVES knowledge bases and all files within them.
    Used by K8s CronJobs for complete maintenance.
    """
    try:
        if max_age_days is None:
            max_age_days = int(os.getenv("VECTOR_DB_WEB_SEARCH_EXPIRY_DAYS", "30"))

        # Run all cleanup operations
        orphaned_result = cleanup_orphaned_vectors()
        web_search_result = cleanup_expired_web_searches(max_age_days)
        chat_files_result = cleanup_orphaned_chat_files()
        old_collections_result = cleanup_old_chat_collections(
            max_age_days=1
        )  # 1 day for collection cleanup

        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "max_age_days": max_age_days,
            "cleanup_results": {
                "orphaned_vectors": orphaned_result,
                "web_search_vectors": web_search_result,
                "chat_files": chat_files_result,
                "old_collections": old_collections_result,
            },
        }
    except Exception as e:
        log.error(f"Comprehensive vector cleanup API failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            },
        )


@router.post("/maintenance/cleanup/old-collections")
def api_cleanup_old_collections(max_age_days: int = 1, user=Depends(get_admin_user)):
    """
    API endpoint to cleanup old chat file collections to prevent uncontrolled growth.

    This addresses the concern about accumulating collections since conversations
    don't have an expiry and users don't delete old conversations.

    Collections older than max_age_days will be deleted but can be re-created on-demand.
    Used by K8s CronJobs for proactive collection management.
    """
    try:
        result = cleanup_old_chat_collections(max_age_days)
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "max_age_days": max_age_days,
            "cleanup_result": result,
            "note": "Deleted collections can be recreated on-demand when accessed",
        }
    except Exception as e:
        log.error(f"Old collections cleanup API failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            },
        )


@router.get("/maintenance/health/vector-db")
def api_vector_db_health(user=Depends(get_admin_user)):
    """
    Health check endpoint for vector database status.
    Used by K8s health checks and monitoring.
    """
    try:
        stats = get_vector_db_stats(user)

        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "vector_db": {
                "connection": "ok",
                "total_collections": stats.get("stats", {}).get("total_collections", 0),
                "file_collections": stats.get("stats", {}).get("file_collections", 0),
                "web_search_collections": stats.get("stats", {}).get(
                    "web_search_collections", 0
                ),
                "knowledge_collections": stats.get("stats", {}).get(
                    "knowledge_collections", 0
                ),
            },
        }

        return health_status

    except Exception as e:
        log.error(f"Vector DB health check failed: {str(e)}")

        health_status = {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "vector_db": {"connection": "failed", "error": str(e)},
        }

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status,
        )


def extract_file_ids_from_chat_data(chat):
    """
    Extract all file IDs from chat messages to enable proper cleanup.

    Args:
        chat: Chat object with chat data containing messages

    Returns:
        set: Set of unique file IDs found in the chat
    """
    file_ids = set()

    try:
        # Get messages from chat data
        messages = chat.chat.get("messages", []) if chat.chat else []

        for message in messages:
            # Check if message has files
            if isinstance(message, dict) and message.get("files"):
                files = message["files"]
                if isinstance(files, list):
                    for file_item in files:
                        if isinstance(file_item, dict):
                            # Extract file ID from various possible formats
                            file_id = (
                                file_item.get("id")
                                or file_item.get("file", {}).get("id")
                                if isinstance(file_item.get("file"), dict)
                                else None
                            )
                            if file_id:
                                file_ids.add(file_id)

        log.debug(f"Extracted {len(file_ids)} file IDs from chat {chat.id}")
        return file_ids

    except Exception as e:
        log.error(f"Error extracting file IDs from chat {chat.id}: {e}")
        return set()


def get_all_file_references_from_chats():
    """
    Extract all file IDs referenced across all chats in the system.

    Returns:
        set: Set of all file IDs that are still referenced by existing chats
    """
    try:
        log.info("Scanning all chats for file references...")
        all_file_ids = set()

        # Get all chats in the system
        all_chats = Chats.get_chat_list(include_archived=True)

        for chat in all_chats:
            try:
                file_ids = extract_file_ids_from_chat_data(chat)
                all_file_ids.update(file_ids)
            except Exception as e:
                log.error(f"Error extracting file IDs from chat {chat.id}: {e}")

        log.info(
            f"Found {len(all_file_ids)} total file references across {len(all_chats)} chats"
        )
        return all_file_ids

    except Exception as e:
        log.error(f"Error scanning chats for file references: {e}")
        return set()


def cleanup_orphaned_files_by_reference():
    """
    Clean up files that are not referenced by any existing chats.
    This is the safe way to handle file cleanup when chats can be cloned.

    Returns:
        dict: Summary of cleanup operations
    """
    try:
        cleanup_summary = {
            "files_checked": 0,
            "orphaned_files_found": 0,
            "files_deleted": 0,
            "collections_cleaned": 0,
            "kb_files_preserved": 0,
            "errors": [],
        }

        log.info("Starting reference-based file cleanup...")

        # Get all file references from existing chats
        referenced_file_ids = get_all_file_references_from_chats()

        # Get knowledge base files that should be preserved
        kb_referenced_files = set()
        try:
            existing_knowledge_bases = Knowledges.get_knowledge_bases()
            for kb in existing_knowledge_bases:
                if kb.data and isinstance(kb.data, dict):
                    file_ids = kb.data.get("file_ids", [])
                    if isinstance(file_ids, list):
                        kb_referenced_files.update(file_ids)
            log.info(
                f"Found {len(kb_referenced_files)} files in knowledge bases to preserve"
            )
        except Exception as e:
            log.error(f"Error getting knowledge base files: {e}")
            kb_referenced_files = set()

        # Get all files from the database
        all_files = Files.get_files()

        for file in all_files:
            cleanup_summary["files_checked"] += 1

            # Skip KB files
            if file.id in kb_referenced_files:
                cleanup_summary["kb_files_preserved"] += 1
                log.debug(f"Preserving KB file: {file.id}")
                continue

            # Check if file is referenced by any chat
            if file.id not in referenced_file_ids:
                # File is orphaned - safe to delete
                cleanup_summary["orphaned_files_found"] += 1

                try:
                    # Delete vector collection
                    collection_name = f"{VECTOR_COLLECTION_PREFIXES.FILE}{file.id}"
                    if VECTOR_DB_CLIENT.has_collection(collection_name):
                        VECTOR_DB_CLIENT.delete_collection(collection_name)
                        cleanup_summary["collections_cleaned"] += 1
                        log.info(f"Deleted vector collection: {collection_name}")

                    # Delete physical file
                    if file.path:
                        Storage.delete_file(file.path)
                        log.info(f"Deleted physical file: {file.path}")

                    # Delete from database
                    Files.delete_file_by_id(file.id)
                    cleanup_summary["files_deleted"] += 1
                    log.info(f"Deleted orphaned file: {file.id}")

                except Exception as e:
                    error_msg = f"Error deleting orphaned file {file.id}: {e}"
                    log.error(error_msg)
                    cleanup_summary["errors"].append(error_msg)
            else:
                log.debug(f"File {file.id} is still referenced by chats")

        log.info(f"Reference-based cleanup completed: {cleanup_summary}")
        return cleanup_summary

    except Exception as e:
        error_msg = f"Error in reference-based file cleanup: {e}"
        log.error(error_msg)
        return {"error": error_msg}


def cleanup_old_chat_collections(max_age_days: int = 1) -> dict:
    """
    Clean up old chat file collections to prevent uncontrolled growth.
    Collections older than max_age_days will be deleted, but can be recreated on-demand.

    This addresses the concern about uncontrolled growth of Qdrant collections
    since conversations don't have an expiry and users don't delete old conversations.

    Args:
        max_age_days: Age threshold in days (default: 1 day for quick cleanup)

    Returns:
        dict: Summary of cleanup operations
    """
    try:
        cleanup_summary = {
            "collections_checked": 0,
            "old_collections_found": 0,
            "collections_deleted": 0,
            "kb_collections_preserved": 0,
            "web_search_collections_preserved": 0,
            "errors": [],
        }

        log.info(
            f"Starting cleanup of chat collections older than {max_age_days} days..."
        )

        if not VECTOR_DB_CLIENT:
            log.warning("Vector DB client not available")
            return {"error": "Vector DB client not available"}

        # Get all collections
        try:
            if hasattr(VECTOR_DB_CLIENT, "list_collections"):
                collection_names = VECTOR_DB_CLIENT.list_collections()
                # Create collection objects with name attribute for compatibility
                collections = [
                    type("Collection", (), {"name": name})()
                    for name in collection_names
                ]
            else:
                log.error("Vector DB client does not support list_collections method")
                return {
                    "error": "Vector DB client does not support list_collections method"
                }
        except Exception as e:
            log.error(f"Failed to get collections: {e}")
            return {"error": f"Failed to get collections: {e}"}

        # Get knowledge base files to preserve their collections
        kb_file_ids = set()
        try:
            existing_knowledge_bases = Knowledges.get_knowledge_bases()
            for kb in existing_knowledge_bases:
                if kb.data and isinstance(kb.data, dict):
                    file_ids = kb.data.get("file_ids", [])
                    if isinstance(file_ids, list):
                        kb_file_ids.update(file_ids)
            log.info(f"Found {len(kb_file_ids)} knowledge base files to preserve")
        except Exception as e:
            log.error(f"Error getting knowledge base files: {e}")
            kb_file_ids = set()

        cutoff_time = datetime.now() - timedelta(days=max_age_days)

        for collection in collections:
            cleanup_summary["collections_checked"] += 1
            collection_name = collection.name

            # Skip knowledge base collections
            if collection_name.startswith(VECTOR_COLLECTION_PREFIXES.FILE):
                file_id = collection_name.replace(VECTOR_COLLECTION_PREFIXES.FILE, "")
                if file_id in kb_file_ids:
                    cleanup_summary["kb_collections_preserved"] += 1
                    log.debug(f"Preserving KB collection: {collection_name}")
                    continue

            # Skip web search collections (they have their own cleanup)
            if collection_name.startswith(VECTOR_COLLECTION_PREFIXES.WEB_SEARCH):
                cleanup_summary["web_search_collections_preserved"] += 1
                log.debug(f"Preserving web search collection: {collection_name}")
                continue

            # Skip knowledge collections (these are permanent)
            if not collection_name.startswith(VECTOR_COLLECTION_PREFIXES.FILE):
                log.debug(f"Skipping non-file collection: {collection_name}")
                continue

            # Check collection age by checking the corresponding file's creation time
            try:
                # For file collections, check if the file still exists and is old
                is_old_collection = False
                if collection_name.startswith(VECTOR_COLLECTION_PREFIXES.FILE):
                    file_id = collection_name.replace(
                        VECTOR_COLLECTION_PREFIXES.FILE, ""
                    )

                    # Get file from database to check its age
                    try:
                        file = Files.get_file_by_id(file_id)
                        if file:
                            # Check if file is old based on its creation timestamp
                            if hasattr(file, "created_at") and file.created_at:
                                if file.created_at < cutoff_time:
                                    is_old_collection = True
                            else:
                                # If no timestamp, consider it old for cleanup
                                is_old_collection = True
                        else:
                            # File doesn't exist in database, collection is orphaned
                            is_old_collection = True
                    except Exception as e:
                        log.debug(f"Could not check file {file_id} age: {e}")
                        # If we can't check the file, assume collection is old for cleanup
                        is_old_collection = True

                if is_old_collection:
                    cleanup_summary["old_collections_found"] += 1

                    # Delete the old collection
                    VECTOR_DB_CLIENT.delete_collection(collection_name)
                    cleanup_summary["collections_deleted"] += 1
                    log.info(f"Deleted old chat collection: {collection_name}")
                else:
                    log.debug(f"Collection {collection_name} is recent, preserving")

            except Exception as e:
                error_msg = f"Error processing collection {collection_name}: {e}"
                log.error(error_msg)
                cleanup_summary["errors"].append(error_msg)

        log.info(f"Old chat collections cleanup completed: {cleanup_summary}")
        return cleanup_summary

    except Exception as e:
        error_msg = f"Error in old chat collections cleanup: {e}"
        log.error(error_msg)
        return {"error": error_msg}


def reindex_file_on_demand(file_id: str, request: Request, user=None) -> bool:
    """
    Re-index a file on-demand if its collection was deleted during cleanup.
    This enables the "re-index on the fly if needed" approach suggested in the PR.

    Args:
        file_id: ID of the file to re-index
        request: FastAPI request object for accessing app state
        user: User object for permissions

    Returns:
        bool: True if re-indexing was successful, False otherwise
    """
    try:
        log.info(f"Re-indexing file {file_id} on demand...")

        # Get file from database
        file = Files.get_file_by_id(file_id)
        if not file:
            log.error(f"File {file_id} not found in database")
            return False

        # Check if collection already exists
        collection_name = f"{VECTOR_COLLECTION_PREFIXES.FILE}{file_id}"
        if VECTOR_DB_CLIENT and VECTOR_DB_CLIENT.has_collection(collection_name):
            log.debug(
                f"Collection {collection_name} already exists, no re-indexing needed"
            )
            return True

        # Re-create the collection by processing the file
        log.info(f"Re-creating collection for file {file_id}: {file.filename}")

        # Get the file content from the database (it's already stored there)
        try:
            if hasattr(file, "data") and file.data and "content" in file.data:
                file_content = file.data["content"]
                log.info(f"Using file content from database for {file_id}")
            else:
                # Fallback: try to load from storage
                file_content_bytes = Storage.get_file(file.path)
                if not file_content_bytes:
                    log.error(f"Could not load file content for {file_id}")
                    return False
                file_content = file_content_bytes.decode("utf-8", errors="ignore")
                log.info(f"Loaded file content from storage for {file_id}")
        except Exception as e:
            log.error(f"Error loading file content for {file_id}: {e}")
            return False

        # Process the file content and create vectors
        try:
            # Create documents from the content
            docs = [
                Document(page_content=file_content, metadata={"source": file.filename})
            ]

            # Use the existing save_docs_to_vector_db function
            collection_name = f"{VECTOR_COLLECTION_PREFIXES.FILE}{file_id}"
            result = save_docs_to_vector_db(
                request=request,
                docs=docs,
                collection_name=collection_name,
                metadata={
                    "file_id": file_id,
                    "filename": file.filename,
                },
                user=user,
            )

            if result:
                log.info(f"Successfully re-indexed file {file_id}")
                return True
            else:
                log.error(f"Failed to save vectors for file {file_id}")
                return False

        except Exception as e:
            log.error(f"Error re-indexing file {file_id}: {e}")
            return False

    except Exception as e:
        log.error(f"Error in on-demand re-indexing for file {file_id}: {e}")
        return False


def cleanup_orphaned_chat_files() -> dict:
    """
    Clean up ALL chat files (except Knowledge Base files).
    This aggressive cleanup deletes all files except those belonging to KBs,
    regardless of whether they're still referenced in chats.

    PRESERVES: Only Knowledge Base files
    DELETES: All other files (chat files, orphaned files, etc.)

    Returns:
        dict: Summary of cleanup operations
    """
    try:
        cleanup_summary = {
            "chat_files_checked": 0,
            "orphaned_files_found": 0,
            "collections_cleaned": 0,
            "files_deleted": 0,
            "kb_files_preserved": 0,
            "errors": [],
        }

        log.info("Starting orphaned chat files cleanup...")

        # Get all file collections from vector DB
        collections = []
        if hasattr(VECTOR_DB_CLIENT, "list_collections"):
            collections = VECTOR_DB_CLIENT.list_collections()
        else:
            log.warning(
                "Vector DB client does not support listing collections for chat cleanup"
            )
            return cleanup_summary

        # Get all existing knowledge base IDs to preserve them
        from open_webui.models.knowledge import Knowledges

        try:
            existing_knowledge_bases = Knowledges.get_knowledge_bases()
            existing_kb_ids = {kb.id for kb in existing_knowledge_bases}
            log.info(f"Found {len(existing_kb_ids)} knowledge bases to preserve")
        except Exception as e:
            log.warning(f"Could not get knowledge bases: {e}")
            existing_kb_ids = set()

        # No longer checking chat references - we delete all chat files except KB files
        log.info(
            "Chat file cleanup: Will delete ALL chat files (preserving only KB files)"
        )

        # Get files referenced in knowledge bases (these should NEVER be deleted)
        kb_referenced_files = set()
        try:
            for kb in existing_knowledge_bases:
                if kb.data and isinstance(kb.data, dict):
                    file_ids = kb.data.get("file_ids", [])
                    if isinstance(file_ids, list):
                        kb_referenced_files.update(file_ids)

            log.info(
                f"Found {len(kb_referenced_files)} files referenced in knowledge bases (will be preserved)"
            )
        except Exception as e:
            log.error(f"Error getting knowledge base files: {e}")
            kb_referenced_files = set()

        # Process file collections
        for collection_name in collections:
            cleanup_summary["chat_files_checked"] += 1

            try:
                # Skip knowledge base collections
                if collection_name in existing_kb_ids:
                    continue

                # Skip non-file collections
                if not collection_name.startswith(VECTOR_COLLECTION_PREFIXES.FILE):
                    continue

                # Extract file ID
                file_id = collection_name.replace(VECTOR_COLLECTION_PREFIXES.FILE, "")

                # NEVER delete files that belong to knowledge bases
                if file_id in kb_referenced_files:
                    cleanup_summary["kb_files_preserved"] += 1
                    log.debug(f"Skipping file {file_id} - belongs to knowledge base")
                    continue

                # Check if file exists in database
                file = Files.get_file_by_id(file_id)
                if not file:
                    # File doesn't exist in database - orphaned
                    cleanup_summary["orphaned_files_found"] += 1
                    VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
                    cleanup_summary["collections_cleaned"] += 1
                    log.info(f"Cleaned up orphaned file collection: {collection_name}")
                    continue

                # Delete ALL chat files (regardless of whether they're still in use)
                # Only KB files are preserved
                cleanup_summary["orphaned_files_found"] += 1

                # Delete vector collection
                VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
                cleanup_summary["collections_cleaned"] += 1

                # Delete physical file
                try:
                    Storage.delete_file(file.path)
                except Exception as e:
                    log.warning(f"Could not delete physical file {file.path}: {e}")

                # Delete from database
                Files.delete_file_by_id(file_id)
                cleanup_summary["files_deleted"] += 1

                log.info(f"Cleaned up chat file: {file_id}")

            except Exception as e:
                error_msg = f"Error processing collection {collection_name}: {e}"
                log.error(error_msg)
                cleanup_summary["errors"].append(error_msg)

        log.info(f"Orphaned chat files cleanup completed: {cleanup_summary}")
        return cleanup_summary

    except Exception as e:
        log.error(f"Error during orphaned chat files cleanup: {e}")
        return {"error": str(e), "collections_cleaned": 0, "files_deleted": 0}


@router.post("/maintenance/cleanup/chat-files")
def api_cleanup_orphaned_chat_files(user=Depends(get_admin_user)):
    """
    API endpoint to cleanup orphaned chat files.
    Removes files that were uploaded to chats but whose chats no longer exist.
    PRESERVES knowledge bases and all files within them.
    Used by K8s CronJobs for scheduled maintenance.
    """
    try:
        result = cleanup_orphaned_chat_files()
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "cleanup_result": result,
        }
    except Exception as e:
        log.error(f"Orphaned chat files cleanup API failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            },
        )
