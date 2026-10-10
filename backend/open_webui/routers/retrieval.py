from __future__ import annotations

import asyncio
import io
import logging
import mimetypes
import os
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterator, Optional, Sequence, Union
from urllib.parse import unquote, urlparse

import tiktoken
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
    TokenTextSplitter,
)
from open_webui.config import (
    Config,
    DEFAULT_LOCALE,
    ENV,
    RAG_EMBEDDING_CONTENT_PREFIX,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
    RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
    RAG_EMBEDDING_QUERY_PREFIX,
    RAG_RERANKING_MODEL_AUTO_UPDATE,
    RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
    UPLOAD_DIR,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import (
    AIOHTTP_CLIENT_ALLOW_REDIRECTS,
    AIOHTTP_CLIENT_SESSION_SSL,
    DEVICE_TYPE,
    DOCKER,
    RAG_EMBEDDING_TIMEOUT,
    SENTENCE_TRANSFORMERS_BACKEND,
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND,
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS,
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_SIGMOID_ACTIVATION_FUNCTION,
    SENTENCE_TRANSFORMERS_MODEL_KWARGS,
    USE_SLIM,
    USER_AGENT,
)
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_db, get_async_session
from open_webui.models.files import FileModel, Files, FileUpdateForm
from open_webui.models.knowledge import Knowledges

# Document loaders
from open_webui.retrieval.loaders.youtube import YoutubeLoader, YoutubeTranscriptError
from open_webui.retrieval.utils import (
    build_loader_from_config,
    filter_accessible_collections,
    get_content_from_url,
    get_embedding_function,
    get_model_path,
    get_reranking_function,
    is_youtube_url,
    query_collection,
    query_collection_with_hybrid_search,
    query_doc,
    query_doc_with_hybrid_search,
)
from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT
from open_webui.retrieval.vector.factory import get_vector_db_client
from open_webui.retrieval.vector.utils import filter_metadata
from open_webui.retrieval.web.azure import search_azure
from open_webui.retrieval.web.bing import search_bing
from open_webui.retrieval.web.bocha import search_bocha
from open_webui.retrieval.web.brave import search_brave
from open_webui.retrieval.web.brave_llm_context import search_brave_llm_context
from open_webui.retrieval.web.duckduckgo import search_duckduckgo
from open_webui.retrieval.web.exa import search_exa
from open_webui.retrieval.web.external import search_external
from open_webui.retrieval.web.firecrawl import search_firecrawl
from open_webui.retrieval.web.google_pse import search_google_pse
from open_webui.retrieval.web.jina_search import search_jina
from open_webui.retrieval.web.kagi import search_kagi
from open_webui.retrieval.web.utils import get_ssrf_safe_session, validate_url

# Web search engines
from open_webui.retrieval.web.main import SearchResult
from open_webui.retrieval.web.microsoft_web_iq import search_microsoft_web_iq
from open_webui.retrieval.web.mojeek import search_mojeek
from open_webui.retrieval.web.ollama import search_ollama_cloud
from open_webui.retrieval.web.perplexity import search_perplexity
from open_webui.retrieval.web.perplexity_search import search_perplexity_search
from open_webui.retrieval.web.searchapi import search_searchapi
from open_webui.retrieval.web.openserp import search_openserp
from open_webui.retrieval.web.searxng import search_searxng
from open_webui.retrieval.web.serpapi import search_serpapi
from open_webui.retrieval.web.serper import search_serper
from open_webui.retrieval.web.serphouse import search_serphouse
from open_webui.retrieval.web.serply import search_serply
from open_webui.retrieval.web.serpstack import search_serpstack
from open_webui.retrieval.web.sougou import search_sougou
from open_webui.retrieval.web.staan import search_staan
from open_webui.retrieval.web.tavily import search_tavily
from open_webui.retrieval.web.utils import get_web_loader
from open_webui.retrieval.web.yacy import search_yacy
from open_webui.retrieval.web.yandex import search_yandex
from open_webui.retrieval.web.ydc import search_youcom
from open_webui.retrieval.web.linkup import search_linkup
from open_webui.storage.provider import Storage
from open_webui.utils.access_control import has_permission
from open_webui.utils.access_control.files import has_access_to_file
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.misc import (
    calculate_sha256_string,
    sanitize_text_for_db,
)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

TIKTOKEN_DISALLOWED_SPECIAL = ()

##########################################
#
# Utility functions
# Give us this day our relevant chunks, and lead us
# not into hallucination, but deliver us from noise.
#
##########################################


def get_ef(
    engine: str,
    embedding_model: str,
    auto_update: bool = RAG_EMBEDDING_MODEL_AUTO_UPDATE,
):
    ef = None
    if embedding_model and engine == '' and not USE_SLIM:
        from sentence_transformers import SentenceTransformer

        try:
            ef = SentenceTransformer(
                get_model_path(embedding_model, auto_update),
                device=DEVICE_TYPE,
                trust_remote_code=RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
                backend=SENTENCE_TRANSFORMERS_BACKEND,
                model_kwargs=SENTENCE_TRANSFORMERS_MODEL_KWARGS,
            )
        except Exception as e:
            log.error(f'Error loading SentenceTransformer: {e}')

    return ef


def get_rf(
    engine: str = '',
    reranking_model: str | None = None,
    external_reranker_url: str = '',
    external_reranker_api_key: str = '',
    external_reranker_timeout: str = '',
    auto_update: bool = RAG_RERANKING_MODEL_AUTO_UPDATE,
):
    rf = None
    # Convert timeout string to int or None (system default)
    timeout_value = int(external_reranker_timeout) if external_reranker_timeout else None
    if reranking_model and engine == 'external':
        from open_webui.retrieval.models.external import ExternalReranker

        return ExternalReranker(
            url=external_reranker_url,
            api_key=external_reranker_api_key,
            model=reranking_model,
            timeout=timeout_value,
        )
    if USE_SLIM:
        return None
    if reranking_model:
        if any(model in reranking_model for model in ['jinaai/jina-colbert-v2']):
            try:
                from open_webui.retrieval.models.colbert import ColBERT

                rf = ColBERT(
                    get_model_path(reranking_model, auto_update),
                    env='docker' if DOCKER else None,
                )

            except Exception as e:
                log.error(f'ColBERT: {e}')
                raise Exception(ERROR_MESSAGES.DEFAULT(e, 'Error loading reranking model'))
        else:
            import sentence_transformers
            import torch

            try:
                rf = sentence_transformers.CrossEncoder(
                    get_model_path(reranking_model, auto_update),
                    device=DEVICE_TYPE,
                    trust_remote_code=RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
                    backend=SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND,
                    model_kwargs=SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS,
                    activation_fn=(
                        torch.nn.Sigmoid() if SENTENCE_TRANSFORMERS_CROSS_ENCODER_SIGMOID_ACTIVATION_FUNCTION else None
                    ),
                )
            except Exception as e:
                log.error(f'CrossEncoder: {e}')
                raise Exception(ERROR_MESSAGES.DEFAULT(e, 'CrossEncoder error'))

            # Safely adjust pad_token_id if missing as some models do not have this in config
            try:
                model_cfg = getattr(rf, 'model', None)
                if model_cfg and hasattr(model_cfg, 'config'):
                    cfg = model_cfg.config
                    if getattr(cfg, 'pad_token_id', None) is None:
                        # Fallback to eos_token_id when available
                        eos = getattr(cfg, 'eos_token_id', None)
                        if eos is not None:
                            cfg.pad_token_id = eos
                            log.debug('Missing pad_token_id detected; set to eos_token_id=%s', eos)
                        else:
                            log.warning('Neither pad_token_id nor eos_token_id present in model config')
            except Exception as e2:
                log.warning(f'Failed to adjust pad_token_id on CrossEncoder: {e2}')

    return rf


##########################################
#
# API routes
#
##########################################


RETRIEVAL_CONFIG_KEYS = {
    'ALLOWED_FILE_EXTENSIONS': 'rag.file.allowed_extensions',
    'AZURE_AI_SEARCH_API_KEY': 'web.search.azure_ai_search_api_key',
    'AZURE_AI_SEARCH_ENDPOINT': 'web.search.azure_ai_search_endpoint',
    'AZURE_AI_SEARCH_INDEX_NAME': 'web.search.azure_ai_search_index_name',
    'BING_SEARCH_V7_ENDPOINT': 'web.search.bing_search_v7_endpoint',
    'BING_SEARCH_V7_SUBSCRIPTION_KEY': 'web.search.bing_search_v7_subscription_key',
    'BOCHA_SEARCH_API_KEY': 'web.search.bocha_search_api_key',
    'BRAVE_SEARCH_API_KEY': 'web.search.brave_search_api_key',
    'BRAVE_SEARCH_CONTEXT_TOKENS': 'web.search.brave_search_context_tokens',
    'BYPASS_EMBEDDING_AND_RETRIEVAL': 'rag.bypass_embedding_and_retrieval',
    'BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL': 'web.search.bypass_embedding_and_retrieval',
    'BYPASS_WEB_SEARCH_WEB_LOADER': 'web.search.bypass_web_loader',
    'CHUNK_MIN_SIZE_TARGET': 'rag.chunk_min_size_target',
    'CHUNK_OVERLAP': 'rag.chunk_overlap',
    'CHUNK_SIZE': 'rag.chunk_size',
    'CONTENT_EXTRACTION_SUPPORTED_MEDIA_MIME_TYPES': 'rag.content_extraction.supported_media_mime_types',
    'CONTENT_EXTRACTION_ENGINE': 'rag.content_extraction_engine',
    'DATALAB_MARKER_ADDITIONAL_CONFIG': 'rag.datalab_marker_additional_config',
    'DATALAB_MARKER_API_BASE_URL': 'rag.datalab_marker_api_base_url',
    'DATALAB_MARKER_API_KEY': 'rag.datalab_marker_api_key',
    'DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION': 'rag.datalab_marker_disable_image_extraction',
    'DATALAB_MARKER_FORCE_OCR': 'rag.datalab_marker_force_ocr',
    'DATALAB_MARKER_FORMAT_LINES': 'rag.datalab_marker_format_lines',
    'DATALAB_MARKER_OUTPUT_FORMAT': 'rag.datalab_marker_output_format',
    'DATALAB_MARKER_PAGINATE': 'rag.datalab_marker_paginate',
    'DATALAB_MARKER_SKIP_CACHE': 'rag.datalab_marker_skip_cache',
    'DATALAB_MARKER_STRIP_EXISTING_OCR': 'rag.datalab_marker_strip_existing_ocr',
    'DATALAB_MARKER_USE_LLM': 'rag.datalab_marker_use_llm',
    'DDGS_BACKEND': 'web.search.ddgs_backend',
    'DOCLING_API_KEY': 'rag.docling_api_key',
    'DOCLING_PARAMS': 'rag.docling_params',
    'DOCLING_SERVER_URL': 'rag.docling_server_url',
    'DOCUMENT_INTELLIGENCE_ENDPOINT': 'rag.document_intelligence_endpoint',
    'DOCUMENT_INTELLIGENCE_KEY': 'rag.document_intelligence_key',
    'DOCUMENT_INTELLIGENCE_MODEL': 'rag.document_intelligence_model',
    'ENABLE_ASYNC_EMBEDDING': 'rag.enable_async_embedding',
    'ENABLE_GOOGLE_DRIVE_INTEGRATION': 'google_drive.enable',
    'ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER': 'rag.enable_markdown_header_text_splitter',
    'ENABLE_ONEDRIVE_INTEGRATION': 'onedrive.enable',
    'ENABLE_RAG_HYBRID_SEARCH': 'rag.enable_hybrid_search',
    'ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS': 'rag.enable_hybrid_search_enriched_texts',
    'ENABLE_WEB_LOADER_SSL_VERIFICATION': 'web.loader.ssl_verification',
    'ENABLE_WEB_SEARCH': 'web.search.enable',
    'ENABLE_WEB_SEARCH_CONFIRMATION': 'web.search.confirmation.enable',
    'WEB_SEARCH_CONFIRMATION_CONTENT': 'web.search.confirmation.content',
    'EXA_API_KEY': 'web.search.exa_api_key',
    'EXA_MAX_CONTENT_LENGTH': 'web.search.exa_max_content_length',
    'EXTERNAL_DOCUMENT_LOADER_API_KEY': 'rag.external_document_loader_api_key',
    'EXTERNAL_DOCUMENT_LOADER_HEADERS': 'rag.external_document_loader_headers',
    'EXTERNAL_DOCUMENT_LOADER_URL': 'rag.external_document_loader_url',
    'EXTERNAL_WEB_LOADER_API_KEY': 'web.loader.external_web_loader_api_key',
    'EXTERNAL_WEB_LOADER_URL': 'web.loader.external_web_loader_url',
    'EXTERNAL_WEB_SEARCH_API_KEY': 'web.search.external_web_search_api_key',
    'EXTERNAL_WEB_SEARCH_URL': 'web.search.external_web_search_url',
    'FILE_IMAGE_COMPRESSION_HEIGHT': 'file.image_compression_height',
    'FILE_IMAGE_COMPRESSION_WIDTH': 'file.image_compression_width',
    'FILE_MAX_COUNT': 'rag.file.max_count',
    'FILE_MAX_SIZE': 'rag.file.max_size',
    'FIRECRAWL_API_BASE_URL': 'web.loader.firecrawl_api_url',
    'FIRECRAWL_API_KEY': 'web.loader.firecrawl_api_key',
    'FIRECRAWL_TIMEOUT': 'web.loader.firecrawl_timeout',
    'GOOGLE_PSE_API_KEY': 'web.search.google_pse_api_key',
    'GOOGLE_PSE_ENGINE_ID': 'web.search.google_pse_engine_id',
    'HYBRID_BM25_WEIGHT': 'rag.hybrid_bm25_weight',
    'JINA_API_BASE_URL': 'web.search.jina_api_base_url',
    'JINA_API_KEY': 'web.search.jina_api_key',
    'KAGI_SEARCH_API_KEY': 'web.search.kagi_search_api_key',
    'LINKUP_API_KEY': 'web.search.linkup_api_key',
    'LINKUP_SEARCH_PARAMS': 'web.search.linkup_search_params',
    'MINERU_API_KEY': 'rag.mineru_api_key',
    'MINERU_API_MODE': 'rag.mineru_api_mode',
    'MINERU_API_TIMEOUT': 'rag.mineru_api_timeout',
    'MINERU_API_URL': 'rag.mineru_api_url',
    'MINERU_FILE_EXTENSIONS': 'rag.mineru_file_extensions',
    'MINERU_PARAMS': 'rag.mineru_params',
    'MICROSOFT_WEB_IQ_API_BASE_URL': 'web.search.microsoft_web_iq_api_base_url',
    'MICROSOFT_WEB_IQ_API_KEY': 'web.search.microsoft_web_iq_api_key',
    'MICROSOFT_WEB_IQ_LANGUAGE': 'web.search.microsoft_web_iq_language',
    'MISTRAL_OCR_API_BASE_URL': 'rag.mistral_ocr_api_base_url',
    'MISTRAL_OCR_API_KEY': 'rag.mistral_ocr_api_key',
    'MISTRAL_OCR_USE_BASE64': 'rag.mistral_ocr_use_base64',
    'MOJEEK_SEARCH_API_KEY': 'web.search.mojeek_search_api_key',
    'OLLAMA_CLOUD_WEB_SEARCH_API_KEY': 'web.search.ollama_cloud_api_key',
    'PADDLEOCR_VL_BASE_URL': 'rag.paddleocr_vl_base_url',
    'PADDLEOCR_VL_TOKEN': 'rag.paddleocr_vl_token',
    'PDF_EXTRACT_IMAGES': 'rag.pdf_extract_images',
    'PDF_LOADER_MODE': 'rag.pdf_loader_mode',
    'PERPLEXITY_API_KEY': 'web.search.perplexity_api_key',
    'PERPLEXITY_MODEL': 'web.search.perplexity_model',
    'PERPLEXITY_SEARCH_API_URL': 'web.search.perplexity_search_api_url',
    'PERPLEXITY_SEARCH_CONTEXT_USAGE': 'web.search.perplexity_search_context_usage',
    'PLAYWRIGHT_TIMEOUT': 'web.loader.playwright_timeout',
    'PLAYWRIGHT_WS_URL': 'web.loader.playwright_ws_url',
    'RAG_AZURE_OPENAI_API_KEY': 'rag.azure_openai.api_key',
    'RAG_AZURE_OPENAI_API_VERSION': 'rag.azure_openai.api_version',
    'RAG_AZURE_OPENAI_BASE_URL': 'rag.azure_openai.base_url',
    'RAG_EMBEDDING_BATCH_SIZE': 'rag.embedding_batch_size',
    'RAG_EMBEDDING_CONCURRENT_REQUESTS': 'rag.embedding_concurrent_requests',
    'RAG_EMBEDDING_ENGINE': 'rag.embedding_engine',
    'RAG_EMBEDDING_MODEL': 'rag.embedding_model',
    'RAG_TOKENIZER_MODEL': 'rag.tokenizer_model',
    'RAG_EXTERNAL_RERANKER_API_KEY': 'rag.external_reranker_api_key',
    'RAG_EXTERNAL_RERANKER_TIMEOUT': 'rag.external_reranker_timeout',
    'RAG_EXTERNAL_RERANKER_URL': 'rag.external_reranker_url',
    'RAG_FULL_CONTEXT': 'rag.full_context',
    'RAG_OLLAMA_API_KEY': 'rag.ollama.api_key',
    'RAG_OLLAMA_BASE_URL': 'rag.ollama.base_url',
    'RAG_OPENAI_API_BASE_URL': 'rag.openai.api_base_url',
    'RAG_OPENAI_API_KEY': 'rag.openai.api_key',
    'RAG_RERANKING_BATCH_SIZE': 'rag.reranking_batch_size',
    'RAG_RERANKING_ENGINE': 'rag.reranking_engine',
    'RAG_RERANKING_MODEL': 'rag.reranking_model',
    'RAG_TEMPLATE': 'rag.template',
    'RELEVANCE_THRESHOLD': 'rag.relevance_threshold',
    'SEARCHAPI_API_KEY': 'web.search.searchapi_api_key',
    'SEARCHAPI_ENGINE': 'web.search.searchapi_engine',
    'SEARXNG_LANGUAGE': 'web.search.searxng_language',
    'SEARXNG_QUERY_URL': 'web.search.searxng_query_url',
    'OPENSERP_BASE_URL': 'web.search.openserp_base_url',
    'SERPAPI_API_KEY': 'web.search.serpapi_api_key',
    'SERPAPI_ENGINE': 'web.search.serpapi_engine',
    'SERPER_API_KEY': 'web.search.serper_api_key',
    'SERPHOUSE_API_KEY': 'web.search.serphouse_api_key',
    'SERPHOUSE_DOMAIN': 'web.search.serphouse_domain',
    'SERPLY_API_KEY': 'web.search.serply_api_key',
    'SERPSTACK_API_KEY': 'web.search.serpstack_api_key',
    'SERPSTACK_HTTPS': 'web.search.serpstack_https',
    'SOUGOU_API_SID': 'web.search.sougou_api_sid',
    'SOUGOU_API_SK': 'web.search.sougou_api_sk',
    'STAAN_API_KEY': 'web.search.staan_api_key',
    'STAAN_MARKET': 'web.search.staan_market',
    'STAAN_MAX_SNIPPETS': 'web.search.staan_max_snippets',
    'TAVILY_API_KEY': 'web.search.tavily_api_key',
    'TAVILY_EXTRACT_DEPTH': 'web.search.tavily_extract_depth',
    'TAVILY_SEARCH_DEPTH': 'web.search.tavily_search_depth',
    'TEXT_SPLITTER': 'rag.text_splitter',
    'TIKA_SERVER_URL': 'rag.tika_server_url',
    'TIKA_SERVER_VERSION': 'rag.tika_server_version',
    'TIKTOKEN_ENCODING_NAME': 'rag.tiktoken_encoding_name',
    'TOP_K': 'rag.top_k',
    'TOP_K_RERANKER': 'rag.top_k_reranker',
    'USER_PERMISSIONS': 'user.permissions',
    'WEBUI_URL': 'webui.url',
    'WEB_FETCH_MAX_CONTENT_LENGTH': 'web.fetch.max_content_length',
    'WEB_LOADER_CONCURRENT_REQUESTS': 'web.loader.concurrent_requests',
    'WEB_LOADER_ENGINE': 'web.loader.engine',
    'WEB_LOADER_TIMEOUT': 'web.loader.timeout',
    'WEB_SEARCH_CONCURRENT_REQUESTS': 'web.search.concurrent_requests',
    'WEB_SEARCH_DOMAIN_FILTER_LIST': 'web.search.domain.filter_list',
    'WEB_SEARCH_ENGINE': 'web.search.engine',
    'WEB_SEARCH_RESULT_COUNT': 'web.search.result_count',
    'WEB_SEARCH_TRUST_ENV': 'web.search.trust_env',
    'YACY_PASSWORD': 'web.search.yacy_password',
    'YACY_QUERY_URL': 'web.search.yacy_query_url',
    'YACY_USERNAME': 'web.search.yacy_username',
    'YANDEX_WEB_SEARCH_API_KEY': 'web.search.yandex_web_search_api_key',
    'YANDEX_WEB_SEARCH_CONFIG': 'web.search.yandex_web_search_config',
    'YANDEX_WEB_SEARCH_URL': 'web.search.yandex_web_search_url',
    'YOUCOM_API_KEY': 'web.search.youcom_api_key',
    'YOUTUBE_LOADER_LANGUAGE': 'rag.youtube_loader_language',
    'YOUTUBE_LOADER_PROXY_URL': 'rag.youtube_loader_proxy_url',
}


router = APIRouter()


class CollectionNameForm(BaseModel):
    collection_name: str | None = None


class ProcessUrlForm(CollectionNameForm):
    url: str


class ProcessUrlResponse(BaseModel):
    status: bool
    type: str
    name: str
    url: str
    collection_name: str | None = None
    content: str | None = None
    file: dict | None = None


class SearchForm(BaseModel):
    queries: list[str]


@router.get('/embedding')
async def get_embedding_config(request: Request, user=Depends(get_admin_user)):
    config = await Config.get_many(*RETRIEVAL_CONFIG_KEYS.values())
    return {
        'status': True,
        'RAG_EMBEDDING_ENGINE': config['rag.embedding_engine'],
        'RAG_EMBEDDING_MODEL': config['rag.embedding_model'],
        'RAG_EMBEDDING_BATCH_SIZE': config['rag.embedding_batch_size'],
        'ENABLE_ASYNC_EMBEDDING': config['rag.enable_async_embedding'],
        'RAG_EMBEDDING_CONCURRENT_REQUESTS': config['rag.embedding_concurrent_requests'],
        'openai_config': {
            'url': config['rag.openai.api_base_url'],
            'key': config['rag.openai.api_key'],
        },
        'ollama_config': {
            'url': config['rag.ollama.base_url'],
            'key': config['rag.ollama.api_key'],
        },
        'azure_openai_config': {
            'url': config['rag.azure_openai.base_url'],
            'key': config['rag.azure_openai.api_key'],
            'version': config['rag.azure_openai.api_version'],
        },
    }


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


async def unload_embedding_model(request: Request):
    config = await Config.get_many(*RETRIEVAL_CONFIG_KEYS.values())
    if config['rag.embedding_engine'] == '':
        # unloads current internal embedding model and clears VRAM cache
        request.app.state.ef = None
        request.app.state.EMBEDDING_FUNCTION = None
        import gc

        gc.collect()
        if DEVICE_TYPE == 'cuda':
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()


@router.post('/embedding/update')
async def update_embedding_config(request: Request, form_data: EmbeddingModelUpdateForm, user=Depends(get_admin_user)):
    if USE_SLIM and form_data.RAG_EMBEDDING_ENGINE == '':
        raise HTTPException(400, 'Slim requires an external embedding engine (openai, ollama, azure_openai).')
    config = await Config.get_many(*RETRIEVAL_CONFIG_KEYS.values())
    log.info('Updating embedding model: %s to %s', config['rag.embedding_model'], form_data.RAG_EMBEDDING_MODEL)
    await unload_embedding_model(request)
    try:
        updates = {
            'rag.embedding_engine': form_data.RAG_EMBEDDING_ENGINE,
            'rag.embedding_model': form_data.RAG_EMBEDDING_MODEL.strip(),
            'rag.embedding_batch_size': form_data.RAG_EMBEDDING_BATCH_SIZE,
            'rag.enable_async_embedding': form_data.ENABLE_ASYNC_EMBEDDING,
            'rag.embedding_concurrent_requests': form_data.RAG_EMBEDDING_CONCURRENT_REQUESTS,
        }
        if form_data.RAG_EMBEDDING_ENGINE == 'openai' and form_data.openai_config is not None:
            updates['rag.openai.api_base_url'] = form_data.openai_config.url or ''
            updates['rag.openai.api_key'] = form_data.openai_config.key or ''
        if form_data.RAG_EMBEDDING_ENGINE == 'ollama' and form_data.ollama_config is not None:
            updates['rag.ollama.base_url'] = form_data.ollama_config.url or ''
            updates['rag.ollama.api_key'] = form_data.ollama_config.key or ''
        if form_data.RAG_EMBEDDING_ENGINE == 'azure_openai' and form_data.azure_openai_config is not None:
            updates['rag.azure_openai.base_url'] = form_data.azure_openai_config.url or ''
            updates['rag.azure_openai.api_key'] = form_data.azure_openai_config.key or ''
            updates['rag.azure_openai.api_version'] = form_data.azure_openai_config.version or ''
        config.update(updates)

        request.app.state.ef = get_ef(
            config['rag.embedding_engine'],
            config['rag.embedding_model'],
        )

        request.app.state.EMBEDDING_FUNCTION = get_embedding_function(
            config['rag.embedding_engine'],
            config['rag.embedding_model'],
            request.app.state.ef,
            (
                config['rag.openai.api_base_url']
                if config['rag.embedding_engine'] == 'openai'
                else (
                    config['rag.ollama.base_url']
                    if config['rag.embedding_engine'] == 'ollama'
                    else config['rag.azure_openai.base_url']
                )
            ),
            (
                config['rag.openai.api_key']
                if config['rag.embedding_engine'] == 'openai'
                else (
                    config['rag.ollama.api_key']
                    if config['rag.embedding_engine'] == 'ollama'
                    else config['rag.azure_openai.api_key']
                )
            ),
            config['rag.embedding_batch_size'],
            azure_api_version=(
                config['rag.azure_openai.api_version'] if config['rag.embedding_engine'] == 'azure_openai' else None
            ),
            enable_async=config['rag.enable_async_embedding'],
            concurrent_requests=config['rag.embedding_concurrent_requests'],
        )

        await Config.upsert(updates)
        return {
            'status': True,
            'RAG_EMBEDDING_ENGINE': config['rag.embedding_engine'],
            'RAG_EMBEDDING_MODEL': config['rag.embedding_model'],
            'RAG_EMBEDDING_BATCH_SIZE': config['rag.embedding_batch_size'],
            'ENABLE_ASYNC_EMBEDDING': config['rag.enable_async_embedding'],
            'RAG_EMBEDDING_CONCURRENT_REQUESTS': config['rag.embedding_concurrent_requests'],
            'openai_config': {
                'url': config['rag.openai.api_base_url'],
                'key': config['rag.openai.api_key'],
            },
            'ollama_config': {
                'url': config['rag.ollama.base_url'],
                'key': config['rag.ollama.api_key'],
            },
            'azure_openai_config': {
                'url': config['rag.azure_openai.base_url'],
                'key': config['rag.azure_openai.api_key'],
                'version': config['rag.azure_openai.api_version'],
            },
        }
    except Exception as e:
        log.exception(f'Problem updating embedding model: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error updating embedding configuration'),
        )


@router.get('/config')
async def get_rag_config(request: Request, user=Depends(get_admin_user)):
    config = await Config.get_many(*RETRIEVAL_CONFIG_KEYS.values())
    return {
        'status': True,
        # RAG settings
        'RAG_TEMPLATE': config['rag.template'],
        'TOP_K': config['rag.top_k'],
        'BYPASS_EMBEDDING_AND_RETRIEVAL': config['rag.bypass_embedding_and_retrieval'],
        'RAG_FULL_CONTEXT': config['rag.full_context'],
        # Hybrid search settings
        'ENABLE_RAG_HYBRID_SEARCH': config['rag.enable_hybrid_search'],
        'ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS': config['rag.enable_hybrid_search_enriched_texts'],
        'TOP_K_RERANKER': config['rag.top_k_reranker'],
        'RELEVANCE_THRESHOLD': config['rag.relevance_threshold'],
        'HYBRID_BM25_WEIGHT': config['rag.hybrid_bm25_weight'],
        # Content extraction settings
        'CONTENT_EXTRACTION_ENGINE': config['rag.content_extraction_engine'],
        'CONTENT_EXTRACTION_SUPPORTED_MEDIA_MIME_TYPES': config['rag.content_extraction.supported_media_mime_types'],
        'PDF_EXTRACT_IMAGES': config['rag.pdf_extract_images'],
        'PDF_LOADER_MODE': config['rag.pdf_loader_mode'],
        'DATALAB_MARKER_API_KEY': config['rag.datalab_marker_api_key'],
        'DATALAB_MARKER_API_BASE_URL': config['rag.datalab_marker_api_base_url'],
        'DATALAB_MARKER_ADDITIONAL_CONFIG': config['rag.datalab_marker_additional_config'],
        'DATALAB_MARKER_SKIP_CACHE': config['rag.datalab_marker_skip_cache'],
        'DATALAB_MARKER_FORCE_OCR': config['rag.datalab_marker_force_ocr'],
        'DATALAB_MARKER_PAGINATE': config['rag.datalab_marker_paginate'],
        'DATALAB_MARKER_STRIP_EXISTING_OCR': config['rag.datalab_marker_strip_existing_ocr'],
        'DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION': config['rag.datalab_marker_disable_image_extraction'],
        'DATALAB_MARKER_FORMAT_LINES': config['rag.datalab_marker_format_lines'],
        'DATALAB_MARKER_USE_LLM': config['rag.datalab_marker_use_llm'],
        'DATALAB_MARKER_OUTPUT_FORMAT': config['rag.datalab_marker_output_format'],
        'EXTERNAL_DOCUMENT_LOADER_URL': config['rag.external_document_loader_url'],
        'EXTERNAL_DOCUMENT_LOADER_API_KEY': config['rag.external_document_loader_api_key'],
        'EXTERNAL_DOCUMENT_LOADER_HEADERS': config['rag.external_document_loader_headers'],
        'TIKA_SERVER_URL': config['rag.tika_server_url'],
        'TIKA_SERVER_VERSION': config['rag.tika_server_version'],
        'DOCLING_SERVER_URL': config['rag.docling_server_url'],
        'DOCLING_API_KEY': config['rag.docling_api_key'],
        'DOCLING_PARAMS': config['rag.docling_params'],
        'DOCUMENT_INTELLIGENCE_ENDPOINT': config['rag.document_intelligence_endpoint'],
        'DOCUMENT_INTELLIGENCE_KEY': config['rag.document_intelligence_key'],
        'DOCUMENT_INTELLIGENCE_MODEL': config['rag.document_intelligence_model'],
        'MISTRAL_OCR_API_BASE_URL': config['rag.mistral_ocr_api_base_url'],
        'MISTRAL_OCR_API_KEY': config['rag.mistral_ocr_api_key'],
        'MISTRAL_OCR_USE_BASE64': config['rag.mistral_ocr_use_base64'],
        'PADDLEOCR_VL_BASE_URL': config['rag.paddleocr_vl_base_url'],
        'PADDLEOCR_VL_TOKEN': config['rag.paddleocr_vl_token'],
        # MinerU settings
        'MINERU_API_MODE': config['rag.mineru_api_mode'],
        'MINERU_API_URL': config['rag.mineru_api_url'],
        'MINERU_API_KEY': config['rag.mineru_api_key'],
        'MINERU_API_TIMEOUT': config['rag.mineru_api_timeout'],
        'MINERU_PARAMS': config['rag.mineru_params'],
        'MINERU_FILE_EXTENSIONS': config['rag.mineru_file_extensions'],
        # Reranking settings
        'RAG_RERANKING_MODEL': config['rag.reranking_model'],
        'RAG_RERANKING_ENGINE': config['rag.reranking_engine'],
        'RAG_RERANKING_BATCH_SIZE': config['rag.reranking_batch_size'],
        'RAG_EXTERNAL_RERANKER_URL': config['rag.external_reranker_url'],
        'RAG_EXTERNAL_RERANKER_API_KEY': config['rag.external_reranker_api_key'],
        'RAG_EXTERNAL_RERANKER_TIMEOUT': config['rag.external_reranker_timeout'],
        # Chunking settings
        'TEXT_SPLITTER': config['rag.text_splitter'],
        'RAG_TOKENIZER_MODEL': config['rag.tokenizer_model'],
        'ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER': config['rag.enable_markdown_header_text_splitter'],
        'CHUNK_SIZE': config['rag.chunk_size'],
        'CHUNK_MIN_SIZE_TARGET': config['rag.chunk_min_size_target'],
        'CHUNK_OVERLAP': config['rag.chunk_overlap'],
        # File upload settings
        'FILE_MAX_SIZE': config['rag.file.max_size'],
        'FILE_MAX_COUNT': config['rag.file.max_count'],
        'FILE_IMAGE_COMPRESSION_WIDTH': config['file.image_compression_width'],
        'FILE_IMAGE_COMPRESSION_HEIGHT': config['file.image_compression_height'],
        'ALLOWED_FILE_EXTENSIONS': config['rag.file.allowed_extensions'],
        # Integration settings
        'ENABLE_GOOGLE_DRIVE_INTEGRATION': config['google_drive.enable'],
        'ENABLE_ONEDRIVE_INTEGRATION': config['onedrive.enable'],
        # Web search settings
        'web': {
            'ENABLE_WEB_SEARCH': config['web.search.enable'],
            'ENABLE_WEB_SEARCH_CONFIRMATION': config['web.search.confirmation.enable'],
            'WEB_SEARCH_CONFIRMATION_CONTENT': config['web.search.confirmation.content'],
            'WEB_SEARCH_ENGINE': config['web.search.engine'],
            'WEB_SEARCH_TRUST_ENV': config['web.search.trust_env'],
            'WEB_SEARCH_RESULT_COUNT': config['web.search.result_count'],
            'WEB_SEARCH_CONCURRENT_REQUESTS': config['web.search.concurrent_requests'],
            'WEB_FETCH_MAX_CONTENT_LENGTH': config['web.fetch.max_content_length'],
            'WEB_LOADER_CONCURRENT_REQUESTS': config['web.loader.concurrent_requests'],
            'WEB_SEARCH_DOMAIN_FILTER_LIST': config['web.search.domain.filter_list'],
            'BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL': config['web.search.bypass_embedding_and_retrieval'],
            'BYPASS_WEB_SEARCH_WEB_LOADER': config['web.search.bypass_web_loader'],
            'OLLAMA_CLOUD_WEB_SEARCH_API_KEY': config['web.search.ollama_cloud_api_key'],
            'SEARXNG_QUERY_URL': config['web.search.searxng_query_url'],
            'SEARXNG_LANGUAGE': config['web.search.searxng_language'],
            'OPENSERP_BASE_URL': config['web.search.openserp_base_url'],
            'YACY_QUERY_URL': config['web.search.yacy_query_url'],
            'YACY_USERNAME': config['web.search.yacy_username'],
            'YACY_PASSWORD': config['web.search.yacy_password'],
            'GOOGLE_PSE_API_KEY': config['web.search.google_pse_api_key'],
            'GOOGLE_PSE_ENGINE_ID': config['web.search.google_pse_engine_id'],
            'BRAVE_SEARCH_API_KEY': config['web.search.brave_search_api_key'],
            'BRAVE_SEARCH_CONTEXT_TOKENS': config['web.search.brave_search_context_tokens'],
            'KAGI_SEARCH_API_KEY': config['web.search.kagi_search_api_key'],
            'MOJEEK_SEARCH_API_KEY': config['web.search.mojeek_search_api_key'],
            'BOCHA_SEARCH_API_KEY': config['web.search.bocha_search_api_key'],
            'SERPSTACK_API_KEY': config['web.search.serpstack_api_key'],
            'SERPSTACK_HTTPS': config['web.search.serpstack_https'],
            'SERPER_API_KEY': config['web.search.serper_api_key'],
            'SERPHOUSE_API_KEY': config['web.search.serphouse_api_key'],
            'SERPHOUSE_DOMAIN': config['web.search.serphouse_domain'],
            'SERPLY_API_KEY': config['web.search.serply_api_key'],
            'DDGS_BACKEND': config['web.search.ddgs_backend'],
            'TAVILY_API_KEY': config['web.search.tavily_api_key'],
            'STAAN_API_KEY': config['web.search.staan_api_key'],
            'STAAN_MARKET': config['web.search.staan_market'],
            'STAAN_MAX_SNIPPETS': config['web.search.staan_max_snippets'],
            'SEARCHAPI_API_KEY': config['web.search.searchapi_api_key'],
            'SEARCHAPI_ENGINE': config['web.search.searchapi_engine'],
            'SERPAPI_API_KEY': config['web.search.serpapi_api_key'],
            'SERPAPI_ENGINE': config['web.search.serpapi_engine'],
            'JINA_API_KEY': config['web.search.jina_api_key'],
            'JINA_API_BASE_URL': config['web.search.jina_api_base_url'],
            'BING_SEARCH_V7_ENDPOINT': config['web.search.bing_search_v7_endpoint'],
            'BING_SEARCH_V7_SUBSCRIPTION_KEY': config['web.search.bing_search_v7_subscription_key'],
            'EXA_API_KEY': config['web.search.exa_api_key'],
            'EXA_MAX_CONTENT_LENGTH': config['web.search.exa_max_content_length'],
            'PERPLEXITY_API_KEY': config['web.search.perplexity_api_key'],
            'PERPLEXITY_MODEL': config['web.search.perplexity_model'],
            'PERPLEXITY_SEARCH_CONTEXT_USAGE': config['web.search.perplexity_search_context_usage'],
            'PERPLEXITY_SEARCH_API_URL': config['web.search.perplexity_search_api_url'],
            'MICROSOFT_WEB_IQ_API_BASE_URL': config['web.search.microsoft_web_iq_api_base_url'],
            'MICROSOFT_WEB_IQ_API_KEY': config['web.search.microsoft_web_iq_api_key'],
            'MICROSOFT_WEB_IQ_LANGUAGE': config['web.search.microsoft_web_iq_language'],
            'SOUGOU_API_SID': config['web.search.sougou_api_sid'],
            'SOUGOU_API_SK': config['web.search.sougou_api_sk'],
            'WEB_LOADER_ENGINE': config['web.loader.engine'],
            'WEB_LOADER_TIMEOUT': config['web.loader.timeout'],
            'ENABLE_WEB_LOADER_SSL_VERIFICATION': config['web.loader.ssl_verification'],
            'PLAYWRIGHT_WS_URL': config['web.loader.playwright_ws_url'],
            'PLAYWRIGHT_TIMEOUT': config['web.loader.playwright_timeout'],
            'FIRECRAWL_API_KEY': config['web.loader.firecrawl_api_key'],
            'FIRECRAWL_API_BASE_URL': config['web.loader.firecrawl_api_url'],
            'FIRECRAWL_TIMEOUT': config['web.loader.firecrawl_timeout'],
            'TAVILY_EXTRACT_DEPTH': config['web.search.tavily_extract_depth'],
            'TAVILY_SEARCH_DEPTH': config['web.search.tavily_search_depth'],
            'EXTERNAL_WEB_SEARCH_URL': config['web.search.external_web_search_url'],
            'EXTERNAL_WEB_SEARCH_API_KEY': config['web.search.external_web_search_api_key'],
            'EXTERNAL_WEB_LOADER_URL': config['web.loader.external_web_loader_url'],
            'EXTERNAL_WEB_LOADER_API_KEY': config['web.loader.external_web_loader_api_key'],
            'YOUTUBE_LOADER_LANGUAGE': config['rag.youtube_loader_language'],
            'YOUTUBE_LOADER_PROXY_URL': config['rag.youtube_loader_proxy_url'],
            'YOUTUBE_LOADER_TRANSLATION': request.app.state.YOUTUBE_LOADER_TRANSLATION,
            'YANDEX_WEB_SEARCH_URL': config['web.search.yandex_web_search_url'],
            'YANDEX_WEB_SEARCH_API_KEY': config['web.search.yandex_web_search_api_key'],
            'YANDEX_WEB_SEARCH_CONFIG': config['web.search.yandex_web_search_config'],
            'YOUCOM_API_KEY': config['web.search.youcom_api_key'],
            'LINKUP_API_KEY': config['web.search.linkup_api_key'],
            'LINKUP_SEARCH_PARAMS': config['web.search.linkup_search_params'],
        },
    }


class WebConfig(BaseModel):
    ENABLE_WEB_SEARCH: bool | None = None
    ENABLE_WEB_SEARCH_CONFIRMATION: bool | None = None
    WEB_SEARCH_CONFIRMATION_CONTENT: str | None = None
    WEB_SEARCH_ENGINE: str | None = None
    WEB_SEARCH_TRUST_ENV: bool | None = None
    WEB_SEARCH_RESULT_COUNT: int | None = None
    WEB_SEARCH_CONCURRENT_REQUESTS: int | None = None
    WEB_SEARCH_DOMAIN_FILTER_LIST: list[str] | None = []
    WEB_FETCH_MAX_CONTENT_LENGTH: int | None = None
    WEB_LOADER_CONCURRENT_REQUESTS: int | None = None
    BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL: bool | None = None
    BYPASS_WEB_SEARCH_WEB_LOADER: bool | None = None
    OLLAMA_CLOUD_WEB_SEARCH_API_KEY: str | None = None
    SEARXNG_QUERY_URL: str | None = None
    SEARXNG_LANGUAGE: str | None = None
    OPENSERP_BASE_URL: str | None = None
    YACY_QUERY_URL: str | None = None
    YACY_USERNAME: str | None = None
    YACY_PASSWORD: str | None = None
    GOOGLE_PSE_API_KEY: str | None = None
    GOOGLE_PSE_ENGINE_ID: str | None = None
    BRAVE_SEARCH_API_KEY: str | None = None
    BRAVE_SEARCH_CONTEXT_TOKENS: int | None = None
    KAGI_SEARCH_API_KEY: str | None = None
    MOJEEK_SEARCH_API_KEY: str | None = None
    BOCHA_SEARCH_API_KEY: str | None = None
    SERPSTACK_API_KEY: str | None = None
    SERPSTACK_HTTPS: bool | None = None
    SERPER_API_KEY: str | None = None
    SERPHOUSE_API_KEY: str | None = None
    SERPHOUSE_DOMAIN: str | None = None
    SERPLY_API_KEY: str | None = None
    DDGS_BACKEND: str | None = None
    TAVILY_API_KEY: str | None = None
    STAAN_API_KEY: str | None = None
    STAAN_MARKET: str | None = None
    STAAN_MAX_SNIPPETS: int | None = None
    SEARCHAPI_API_KEY: str | None = None
    SEARCHAPI_ENGINE: str | None = None
    SERPAPI_API_KEY: str | None = None
    SERPAPI_ENGINE: str | None = None
    JINA_API_KEY: str | None = None
    JINA_API_BASE_URL: str | None = None
    BING_SEARCH_V7_ENDPOINT: str | None = None
    BING_SEARCH_V7_SUBSCRIPTION_KEY: str | None = None
    EXA_API_KEY: str | None = None
    EXA_MAX_CONTENT_LENGTH: int | None = Field(default=None, gt=0, strict=True)
    PERPLEXITY_API_KEY: str | None = None
    PERPLEXITY_MODEL: str | None = None
    PERPLEXITY_SEARCH_CONTEXT_USAGE: str | None = None
    PERPLEXITY_SEARCH_API_URL: str | None = None
    MICROSOFT_WEB_IQ_API_BASE_URL: str | None = None
    MICROSOFT_WEB_IQ_API_KEY: str | None = None
    MICROSOFT_WEB_IQ_LANGUAGE: str | None = None
    SOUGOU_API_SID: str | None = None
    SOUGOU_API_SK: str | None = None
    WEB_LOADER_ENGINE: str | None = None
    WEB_LOADER_TIMEOUT: str | None = None
    ENABLE_WEB_LOADER_SSL_VERIFICATION: bool | None = None
    PLAYWRIGHT_WS_URL: str | None = None
    PLAYWRIGHT_TIMEOUT: int | None = None
    FIRECRAWL_API_KEY: str | None = None
    FIRECRAWL_API_BASE_URL: str | None = None
    FIRECRAWL_TIMEOUT: str | None = None
    TAVILY_EXTRACT_DEPTH: str | None = None
    TAVILY_SEARCH_DEPTH: str | None = None
    EXTERNAL_WEB_SEARCH_URL: str | None = None
    EXTERNAL_WEB_SEARCH_API_KEY: str | None = None
    EXTERNAL_WEB_LOADER_URL: str | None = None
    EXTERNAL_WEB_LOADER_API_KEY: str | None = None
    YOUTUBE_LOADER_LANGUAGE: list[str] | None = None
    YOUTUBE_LOADER_PROXY_URL: str | None = None
    YOUTUBE_LOADER_TRANSLATION: str | None = None
    YANDEX_WEB_SEARCH_URL: str | None = None
    YANDEX_WEB_SEARCH_API_KEY: str | None = None
    YANDEX_WEB_SEARCH_CONFIG: str | None = None
    YOUCOM_API_KEY: str | None = None
    LINKUP_API_KEY: str | None = None
    LINKUP_SEARCH_PARAMS: dict | None = None


class ConfigForm(BaseModel):
    # RAG settings
    RAG_TEMPLATE: str | None = None
    TOP_K: int | None = None
    BYPASS_EMBEDDING_AND_RETRIEVAL: bool | None = None
    RAG_FULL_CONTEXT: bool | None = None

    # Hybrid search settings
    ENABLE_RAG_HYBRID_SEARCH: bool | None = None
    ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS: bool | None = None
    TOP_K_RERANKER: int | None = None
    RELEVANCE_THRESHOLD: float | None = None
    HYBRID_BM25_WEIGHT: float | None = None

    # Content extraction settings
    CONTENT_EXTRACTION_ENGINE: str | None = None
    CONTENT_EXTRACTION_SUPPORTED_MEDIA_MIME_TYPES: list[str] | None = None
    PDF_EXTRACT_IMAGES: bool | None = None
    PDF_LOADER_MODE: str | None = None

    DATALAB_MARKER_API_KEY: str | None = None
    DATALAB_MARKER_API_BASE_URL: str | None = None
    DATALAB_MARKER_ADDITIONAL_CONFIG: str | None = None
    DATALAB_MARKER_SKIP_CACHE: bool | None = None
    DATALAB_MARKER_FORCE_OCR: bool | None = None
    DATALAB_MARKER_PAGINATE: bool | None = None
    DATALAB_MARKER_STRIP_EXISTING_OCR: bool | None = None
    DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION: bool | None = None
    DATALAB_MARKER_FORMAT_LINES: bool | None = None
    DATALAB_MARKER_USE_LLM: bool | None = None
    DATALAB_MARKER_OUTPUT_FORMAT: str | None = None

    EXTERNAL_DOCUMENT_LOADER_URL: str | None = None
    EXTERNAL_DOCUMENT_LOADER_API_KEY: str | None = None
    EXTERNAL_DOCUMENT_LOADER_HEADERS: dict | None = None

    TIKA_SERVER_URL: str | None = None
    TIKA_SERVER_VERSION: str | None = None
    DOCLING_SERVER_URL: str | None = None
    DOCLING_API_KEY: str | None = None
    DOCLING_PARAMS: dict | None = None
    DOCUMENT_INTELLIGENCE_ENDPOINT: str | None = None
    DOCUMENT_INTELLIGENCE_KEY: str | None = None
    DOCUMENT_INTELLIGENCE_MODEL: str | None = None
    MISTRAL_OCR_API_BASE_URL: str | None = None
    MISTRAL_OCR_API_KEY: str | None = None
    MISTRAL_OCR_USE_BASE64: bool | None = None
    PADDLEOCR_VL_BASE_URL: str | None = None
    PADDLEOCR_VL_TOKEN: str | None = None

    # MinerU settings
    MINERU_API_MODE: str | None = None
    MINERU_API_URL: str | None = None
    MINERU_API_KEY: str | None = None
    MINERU_API_TIMEOUT: int | None = None
    MINERU_PARAMS: dict | None = None
    MINERU_FILE_EXTENSIONS: list[str] | None = None

    # Reranking settings
    RAG_RERANKING_MODEL: str | None = None
    RAG_RERANKING_ENGINE: str | None = None
    RAG_RERANKING_BATCH_SIZE: int | None = None
    RAG_EXTERNAL_RERANKER_URL: str | None = None
    RAG_EXTERNAL_RERANKER_API_KEY: str | None = None
    RAG_EXTERNAL_RERANKER_TIMEOUT: str | None = None

    # Chunking settings
    TEXT_SPLITTER: str | None = None
    RAG_TOKENIZER_MODEL: str | None = None
    ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER: bool | None = None
    CHUNK_SIZE: int | None = None
    CHUNK_MIN_SIZE_TARGET: int | None = None
    CHUNK_OVERLAP: int | None = None

    # File upload settings
    FILE_MAX_SIZE: Union[int, str | None] = None
    FILE_MAX_COUNT: Union[int, str | None] = None
    FILE_IMAGE_COMPRESSION_WIDTH: Union[int, str | None] = None
    FILE_IMAGE_COMPRESSION_HEIGHT: Union[int, str | None] = None
    ALLOWED_FILE_EXTENSIONS: list[str] | None = None

    # Integration settings
    ENABLE_GOOGLE_DRIVE_INTEGRATION: bool | None = None
    ENABLE_ONEDRIVE_INTEGRATION: bool | None = None

    # Web search settings
    web: WebConfig | None = None


@router.post('/config/update')
async def update_rag_config(request: Request, form_data: ConfigForm, user=Depends(get_admin_user)):
    # RAG settings
    config = await Config.get_many(*RETRIEVAL_CONFIG_KEYS.values())
    if USE_SLIM:
        if (
            form_data.web
            and form_data.web.WEB_SEARCH_ENGINE == 'duckduckgo'
            and config['web.search.engine'] != 'duckduckgo'
        ):
            raise HTTPException(
                400,
                'DDGS is unavailable in slim. Configure another web search provider in Admin Settings > Web Search.',
            )
        if (
            form_data.web
            and form_data.web.WEB_LOADER_ENGINE == 'playwright'
            and config['web.loader.engine'] != 'playwright'
        ):
            raise HTTPException(
                400, 'Playwright is unavailable in slim. Use basic HTTP fetching or an external web loader.'
            )
        if form_data.TEXT_SPLITTER == 'token_transformers' and config['rag.text_splitter'] != 'token_transformers':
            raise HTTPException(
                400, 'Transformers tokenization is unavailable in slim. Use character or token splitting.'
            )
        reranker_engine = (
            form_data.RAG_RERANKING_ENGINE
            if form_data.RAG_RERANKING_ENGINE is not None
            else config['rag.reranking_engine']
        )
        reranker_model = (
            form_data.RAG_RERANKING_MODEL
            if form_data.RAG_RERANKING_MODEL is not None
            else config['rag.reranking_model']
        )
        if (
            reranker_engine != 'external'
            and reranker_model
            and (reranker_engine != config['rag.reranking_engine'] or reranker_model != config['rag.reranking_model'])
        ):
            raise HTTPException(
                400, 'Slim requires an external reranker, or an empty reranking model for cosine scoring.'
            )
    # Only write submitted values; unrelated settings may have changed since this read.
    updates = {
        RETRIEVAL_CONFIG_KEYS[field]: value
        for field, value in form_data.model_dump(exclude={'web'}, exclude_none=True).items()
    }
    if form_data.RAG_TOKENIZER_MODEL is not None:
        updates['rag.tokenizer_model'] = form_data.RAG_TOKENIZER_MODEL.strip()
    for field in ('FILE_MAX_SIZE', 'FILE_MAX_COUNT', 'FILE_IMAGE_COMPRESSION_WIDTH', 'FILE_IMAGE_COMPRESSION_HEIGHT'):
        if getattr(form_data, field) == '':
            updates[RETRIEVAL_CONFIG_KEYS[field]] = None

    # Unload the previous internal reranker before applying its new settings.
    if config['rag.reranking_engine'] == '':
        request.app.state.rf = None
        request.app.state.RERANKING_FUNCTION = None
        import gc

        gc.collect()
        if DEVICE_TYPE == 'cuda':
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    if form_data.RAG_RERANKING_MODEL is not None:
        log.info('Updating reranking model: %s to %s', config['rag.reranking_model'], form_data.RAG_RERANKING_MODEL)
    config.update(updates)
    try:
        if config['rag.enable_hybrid_search'] and not config['rag.bypass_embedding_and_retrieval']:
            request.app.state.rf = get_rf(
                config['rag.reranking_engine'],
                config['rag.reranking_model'],
                config['rag.external_reranker_url'],
                config['rag.external_reranker_api_key'],
                config['rag.external_reranker_timeout'],
            )
            request.app.state.RERANKING_FUNCTION = get_reranking_function(
                config['rag.reranking_engine'],
                config['rag.reranking_model'],
                request.app.state.rf,
                reranking_batch_size=config['rag.reranking_batch_size'],
            )
    except Exception as e:
        log.error(f'Error loading reranking model: {e}')
        updates['rag.enable_hybrid_search'] = False
        config['rag.enable_hybrid_search'] = False

    if form_data.web is not None:
        for field, value in form_data.web.model_dump(exclude_unset=True).items():
            if field == 'YOUTUBE_LOADER_TRANSLATION':
                request.app.state.YOUTUBE_LOADER_TRANSLATION = value
            elif field == 'BRAVE_SEARCH_CONTEXT_TOKENS' and value is None:
                continue
            else:
                updates[RETRIEVAL_CONFIG_KEYS[field]] = value
        config.update(updates)

    await Config.upsert(updates)

    return {
        'status': True,
        # RAG settings
        'RAG_TEMPLATE': config['rag.template'],
        'TOP_K': config['rag.top_k'],
        'BYPASS_EMBEDDING_AND_RETRIEVAL': config['rag.bypass_embedding_and_retrieval'],
        'RAG_FULL_CONTEXT': config['rag.full_context'],
        # Hybrid search settings
        'ENABLE_RAG_HYBRID_SEARCH': config['rag.enable_hybrid_search'],
        'TOP_K_RERANKER': config['rag.top_k_reranker'],
        'RELEVANCE_THRESHOLD': config['rag.relevance_threshold'],
        'HYBRID_BM25_WEIGHT': config['rag.hybrid_bm25_weight'],
        # Content extraction settings
        'CONTENT_EXTRACTION_ENGINE': config['rag.content_extraction_engine'],
        'CONTENT_EXTRACTION_SUPPORTED_MEDIA_MIME_TYPES': config['rag.content_extraction.supported_media_mime_types'],
        'PDF_EXTRACT_IMAGES': config['rag.pdf_extract_images'],
        'PDF_LOADER_MODE': config['rag.pdf_loader_mode'],
        'DATALAB_MARKER_API_KEY': config['rag.datalab_marker_api_key'],
        'DATALAB_MARKER_API_BASE_URL': config['rag.datalab_marker_api_base_url'],
        'DATALAB_MARKER_ADDITIONAL_CONFIG': config['rag.datalab_marker_additional_config'],
        'DATALAB_MARKER_SKIP_CACHE': config['rag.datalab_marker_skip_cache'],
        'DATALAB_MARKER_FORCE_OCR': config['rag.datalab_marker_force_ocr'],
        'DATALAB_MARKER_PAGINATE': config['rag.datalab_marker_paginate'],
        'DATALAB_MARKER_STRIP_EXISTING_OCR': config['rag.datalab_marker_strip_existing_ocr'],
        'DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION': config['rag.datalab_marker_disable_image_extraction'],
        'DATALAB_MARKER_USE_LLM': config['rag.datalab_marker_use_llm'],
        'DATALAB_MARKER_OUTPUT_FORMAT': config['rag.datalab_marker_output_format'],
        'EXTERNAL_DOCUMENT_LOADER_URL': config['rag.external_document_loader_url'],
        'EXTERNAL_DOCUMENT_LOADER_API_KEY': config['rag.external_document_loader_api_key'],
        'EXTERNAL_DOCUMENT_LOADER_HEADERS': config['rag.external_document_loader_headers'],
        'TIKA_SERVER_URL': config['rag.tika_server_url'],
        'TIKA_SERVER_VERSION': config['rag.tika_server_version'],
        'DOCLING_SERVER_URL': config['rag.docling_server_url'],
        'DOCLING_API_KEY': config['rag.docling_api_key'],
        'DOCLING_PARAMS': config['rag.docling_params'],
        'DOCUMENT_INTELLIGENCE_ENDPOINT': config['rag.document_intelligence_endpoint'],
        'DOCUMENT_INTELLIGENCE_KEY': config['rag.document_intelligence_key'],
        'DOCUMENT_INTELLIGENCE_MODEL': config['rag.document_intelligence_model'],
        'MISTRAL_OCR_API_BASE_URL': config['rag.mistral_ocr_api_base_url'],
        'MISTRAL_OCR_API_KEY': config['rag.mistral_ocr_api_key'],
        'MISTRAL_OCR_USE_BASE64': config['rag.mistral_ocr_use_base64'],
        'PADDLEOCR_VL_BASE_URL': config['rag.paddleocr_vl_base_url'],
        'PADDLEOCR_VL_TOKEN': config['rag.paddleocr_vl_token'],
        # MinerU settings
        'MINERU_API_MODE': config['rag.mineru_api_mode'],
        'MINERU_API_URL': config['rag.mineru_api_url'],
        'MINERU_API_KEY': config['rag.mineru_api_key'],
        'MINERU_API_TIMEOUT': config['rag.mineru_api_timeout'],
        'MINERU_PARAMS': config['rag.mineru_params'],
        # Reranking settings
        'RAG_RERANKING_MODEL': config['rag.reranking_model'],
        'RAG_RERANKING_ENGINE': config['rag.reranking_engine'],
        'RAG_EXTERNAL_RERANKER_URL': config['rag.external_reranker_url'],
        'RAG_EXTERNAL_RERANKER_API_KEY': config['rag.external_reranker_api_key'],
        'RAG_EXTERNAL_RERANKER_TIMEOUT': config['rag.external_reranker_timeout'],
        # Chunking settings
        'TEXT_SPLITTER': config['rag.text_splitter'],
        'RAG_TOKENIZER_MODEL': config['rag.tokenizer_model'],
        'CHUNK_SIZE': config['rag.chunk_size'],
        'CHUNK_MIN_SIZE_TARGET': config['rag.chunk_min_size_target'],
        'ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER': config['rag.enable_markdown_header_text_splitter'],
        'CHUNK_OVERLAP': config['rag.chunk_overlap'],
        # File upload settings
        'FILE_MAX_SIZE': config['rag.file.max_size'],
        'FILE_MAX_COUNT': config['rag.file.max_count'],
        'FILE_IMAGE_COMPRESSION_WIDTH': config['file.image_compression_width'],
        'FILE_IMAGE_COMPRESSION_HEIGHT': config['file.image_compression_height'],
        'ALLOWED_FILE_EXTENSIONS': config['rag.file.allowed_extensions'],
        # Integration settings
        'ENABLE_GOOGLE_DRIVE_INTEGRATION': config['google_drive.enable'],
        'ENABLE_ONEDRIVE_INTEGRATION': config['onedrive.enable'],
        # Web search settings
        'web': {
            'ENABLE_WEB_SEARCH': config['web.search.enable'],
            'ENABLE_WEB_SEARCH_CONFIRMATION': config['web.search.confirmation.enable'],
            'WEB_SEARCH_CONFIRMATION_CONTENT': config['web.search.confirmation.content'],
            'WEB_SEARCH_ENGINE': config['web.search.engine'],
            'WEB_SEARCH_TRUST_ENV': config['web.search.trust_env'],
            'WEB_SEARCH_RESULT_COUNT': config['web.search.result_count'],
            'WEB_SEARCH_CONCURRENT_REQUESTS': config['web.search.concurrent_requests'],
            'WEB_FETCH_MAX_CONTENT_LENGTH': config['web.fetch.max_content_length'],
            'WEB_LOADER_CONCURRENT_REQUESTS': config['web.loader.concurrent_requests'],
            'WEB_SEARCH_DOMAIN_FILTER_LIST': config['web.search.domain.filter_list'],
            'BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL': config['web.search.bypass_embedding_and_retrieval'],
            'BYPASS_WEB_SEARCH_WEB_LOADER': config['web.search.bypass_web_loader'],
            'OLLAMA_CLOUD_WEB_SEARCH_API_KEY': config['web.search.ollama_cloud_api_key'],
            'SEARXNG_QUERY_URL': config['web.search.searxng_query_url'],
            'SEARXNG_LANGUAGE': config['web.search.searxng_language'],
            'OPENSERP_BASE_URL': config['web.search.openserp_base_url'],
            'YACY_QUERY_URL': config['web.search.yacy_query_url'],
            'YACY_USERNAME': config['web.search.yacy_username'],
            'YACY_PASSWORD': config['web.search.yacy_password'],
            'GOOGLE_PSE_API_KEY': config['web.search.google_pse_api_key'],
            'GOOGLE_PSE_ENGINE_ID': config['web.search.google_pse_engine_id'],
            'BRAVE_SEARCH_API_KEY': config['web.search.brave_search_api_key'],
            'BRAVE_SEARCH_CONTEXT_TOKENS': config['web.search.brave_search_context_tokens'],
            'KAGI_SEARCH_API_KEY': config['web.search.kagi_search_api_key'],
            'MOJEEK_SEARCH_API_KEY': config['web.search.mojeek_search_api_key'],
            'BOCHA_SEARCH_API_KEY': config['web.search.bocha_search_api_key'],
            'SERPSTACK_API_KEY': config['web.search.serpstack_api_key'],
            'SERPSTACK_HTTPS': config['web.search.serpstack_https'],
            'SERPER_API_KEY': config['web.search.serper_api_key'],
            'SERPHOUSE_API_KEY': config['web.search.serphouse_api_key'],
            'SERPHOUSE_DOMAIN': config['web.search.serphouse_domain'],
            'SERPLY_API_KEY': config['web.search.serply_api_key'],
            'TAVILY_API_KEY': config['web.search.tavily_api_key'],
            'STAAN_API_KEY': config['web.search.staan_api_key'],
            'STAAN_MARKET': config['web.search.staan_market'],
            'STAAN_MAX_SNIPPETS': config['web.search.staan_max_snippets'],
            'SEARCHAPI_API_KEY': config['web.search.searchapi_api_key'],
            'SEARCHAPI_ENGINE': config['web.search.searchapi_engine'],
            'SERPAPI_API_KEY': config['web.search.serpapi_api_key'],
            'SERPAPI_ENGINE': config['web.search.serpapi_engine'],
            'JINA_API_KEY': config['web.search.jina_api_key'],
            'JINA_API_BASE_URL': config['web.search.jina_api_base_url'],
            'BING_SEARCH_V7_ENDPOINT': config['web.search.bing_search_v7_endpoint'],
            'BING_SEARCH_V7_SUBSCRIPTION_KEY': config['web.search.bing_search_v7_subscription_key'],
            'EXA_API_KEY': config['web.search.exa_api_key'],
            'EXA_MAX_CONTENT_LENGTH': config['web.search.exa_max_content_length'],
            'PERPLEXITY_API_KEY': config['web.search.perplexity_api_key'],
            'PERPLEXITY_MODEL': config['web.search.perplexity_model'],
            'PERPLEXITY_SEARCH_CONTEXT_USAGE': config['web.search.perplexity_search_context_usage'],
            'PERPLEXITY_SEARCH_API_URL': config['web.search.perplexity_search_api_url'],
            'MICROSOFT_WEB_IQ_API_BASE_URL': config['web.search.microsoft_web_iq_api_base_url'],
            'MICROSOFT_WEB_IQ_API_KEY': config['web.search.microsoft_web_iq_api_key'],
            'MICROSOFT_WEB_IQ_LANGUAGE': config['web.search.microsoft_web_iq_language'],
            'SOUGOU_API_SID': config['web.search.sougou_api_sid'],
            'SOUGOU_API_SK': config['web.search.sougou_api_sk'],
            'WEB_LOADER_ENGINE': config['web.loader.engine'],
            'WEB_LOADER_TIMEOUT': config['web.loader.timeout'],
            'ENABLE_WEB_LOADER_SSL_VERIFICATION': config['web.loader.ssl_verification'],
            'PLAYWRIGHT_WS_URL': config['web.loader.playwright_ws_url'],
            'PLAYWRIGHT_TIMEOUT': config['web.loader.playwright_timeout'],
            'FIRECRAWL_API_KEY': config['web.loader.firecrawl_api_key'],
            'FIRECRAWL_API_BASE_URL': config['web.loader.firecrawl_api_url'],
            'FIRECRAWL_TIMEOUT': config['web.loader.firecrawl_timeout'],
            'TAVILY_EXTRACT_DEPTH': config['web.search.tavily_extract_depth'],
            'TAVILY_SEARCH_DEPTH': config['web.search.tavily_search_depth'],
            'EXTERNAL_WEB_SEARCH_URL': config['web.search.external_web_search_url'],
            'EXTERNAL_WEB_SEARCH_API_KEY': config['web.search.external_web_search_api_key'],
            'EXTERNAL_WEB_LOADER_URL': config['web.loader.external_web_loader_url'],
            'EXTERNAL_WEB_LOADER_API_KEY': config['web.loader.external_web_loader_api_key'],
            'YOUTUBE_LOADER_LANGUAGE': config['rag.youtube_loader_language'],
            'YOUTUBE_LOADER_PROXY_URL': config['rag.youtube_loader_proxy_url'],
            'YOUTUBE_LOADER_TRANSLATION': request.app.state.YOUTUBE_LOADER_TRANSLATION,
            'YANDEX_WEB_SEARCH_URL': config['web.search.yandex_web_search_url'],
            'YANDEX_WEB_SEARCH_API_KEY': config['web.search.yandex_web_search_api_key'],
            'YANDEX_WEB_SEARCH_CONFIG': config['web.search.yandex_web_search_config'],
            'YOUCOM_API_KEY': config['web.search.youcom_api_key'],
            'LINKUP_API_KEY': config['web.search.linkup_api_key'],
            'LINKUP_SEARCH_PARAMS': config['web.search.linkup_search_params'],
        },
    }


####################################
#
# Document process and retrieval
#
####################################


def can_merge_chunks(a: Document, b: Document) -> bool:
    if a.metadata.get('source') != b.metadata.get('source'):
        return False

    a_file_id = a.metadata.get('file_id')
    b_file_id = b.metadata.get('file_id')

    if a_file_id is not None and b_file_id is not None:
        return a_file_id == b_file_id

    return True


def merge_docs_to_target_size(
    request: Request,
    chunks: list[Document],
    config: dict,
) -> list[Document]:
    """
    Best-effort normalization of chunk sizes.

    Attempts to grow small chunks up to a desired minimum size,
    without exceeding the maximum size or crossing source/file
    boundaries.

    Uses forward merging first (absorb the next chunk), then
    backward merging (append into the previous emitted chunk)
    for undersized chunks that can't grow forward.
    """
    min_size = config['rag.chunk_min_size_target']
    max_size = config['rag.chunk_size']

    if min_size <= 0:
        return chunks

    measure = get_splitter_length_function(request, config)

    def _merge_backward(result: list[Document], content: str, chunk: Document) -> bool:
        """Try to append content into the last emitted chunk. Returns True on success."""
        if not result:
            return False
        prev = result[-1]
        if not can_merge_chunks(prev, chunk):
            return False
        merged = f'{prev.page_content}\n\n{content}'
        if measure(merged) > max_size:
            return False
        result[-1] = Document(page_content=merged, metadata={**prev.metadata})
        return True

    def _emit(result: list[Document], content: str, chunk: Document) -> None:
        """Emit a chunk, trying backward merge first if it's undersized."""
        is_undersized = measure(content) < min_size
        if is_undersized and _merge_backward(result, content, chunk):
            return
        result.append(Document(page_content=content, metadata={**chunk.metadata}))

    result: list[Document] = []
    current_chunk: Document | None = None
    current_content: str = ''

    for next_chunk in chunks:
        if current_chunk is None:
            current_chunk = next_chunk
            current_content = next_chunk.page_content
            continue

        # Forward merge: absorb next chunk into current if undersized and fits
        merged_content = f'{current_content}\n\n{next_chunk.page_content}'
        can_merge_forward = (
            can_merge_chunks(current_chunk, next_chunk)
            and measure(current_content) < min_size
            and measure(merged_content) <= max_size
        )

        if can_merge_forward:
            current_content = merged_content
        else:
            _emit(result, current_content, current_chunk)
            current_chunk = next_chunk
            current_content = next_chunk.page_content

    if current_chunk is not None:
        _emit(result, current_content, current_chunk)

    return result


def get_transformers_tokenizer(request: Request, config: dict):
    if USE_SLIM:
        raise HTTPException(503, 'Transformers tokenization is unavailable in slim. Use character or token splitting.')
    if config['rag.tokenizer_model']:
        from transformers import AutoTokenizer

        tokenizer_model = config['rag.tokenizer_model']
        if not os.path.exists(tokenizer_model) and '/' not in tokenizer_model:
            tokenizer_model = f'sentence-transformers/{tokenizer_model}'

        cache_dir = os.getenv('SENTENCE_TRANSFORMERS_HOME') or os.getenv('HF_HUB_CACHE')
        local_files_only = not RAG_EMBEDDING_MODEL_AUTO_UPDATE
        tokenizer_key = (tokenizer_model, cache_dir, local_files_only)
        cached_tokenizer = getattr(request.app.state, 'transformers_tokenizer', None)
        if cached_tokenizer and cached_tokenizer[0] == tokenizer_key:
            return cached_tokenizer[1]

        tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_model,
            cache_dir=cache_dir,
            trust_remote_code=RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
            local_files_only=local_files_only,
        )
        request.app.state.transformers_tokenizer = (tokenizer_key, tokenizer)
        return tokenizer

    tokenizer = getattr(getattr(request.app.state, 'ef', None), 'tokenizer', None)
    if tokenizer is not None:
        return tokenizer

    raise ValueError('Tokenizer model required for Token (Transformers) text splitter')


def get_splitter_length_function(
    request: Request,
    config: dict,
) -> Callable[[str], int]:
    if config['rag.text_splitter'] == 'token':
        encoding = tiktoken.get_encoding(str(config['rag.tiktoken_encoding_name']))
        return lambda text: len(encoding.encode(text, disallowed_special=TIKTOKEN_DISALLOWED_SPECIAL))

    if config['rag.text_splitter'] == 'token_transformers':
        tokenizer = get_transformers_tokenizer(request, config)
        return lambda text: len(tokenizer.encode(text))

    return len


def filter_file_metadata(metadata: dict | None) -> dict:
    metadata = dict(metadata or {})
    data = metadata.pop('data', None)
    if isinstance(data, dict):
        metadata = {**filter_metadata(data), **metadata}
    return filter_metadata(metadata)


def has_duplicate_content(collection_name: str, hash: str, file_id: str | None) -> bool:
    result = get_vector_db_client().query(
        collection_name=collection_name,
        filter={'hash': hash},
    )

    if result is not None and result.ids and len(result.ids) > 0:
        existing_doc_ids = result.ids[0]
        if existing_doc_ids:
            # Check if the existing document belongs to the same file
            # If same file_id, this is a re-add/reindex - allow it
            # If different file_id, this is a duplicate - block it
            existing_file_id = None
            if result.metadatas and result.metadatas[0]:
                existing_file_id = result.metadatas[0][0].get('file_id')

            return existing_file_id != file_id

    return False


def save_docs_to_vector_db(
    request: Request,
    docs,
    collection_name,
    config: dict,
    metadata: dict | None = None,
    overwrite: bool = False,
    split: bool = True,
    add: bool = False,
    user=None,
) -> bool:
    def _get_docs_info(docs: list[Document]) -> str:
        docs_info = set()

        # Trying to select relevant metadata identifying the document.
        for doc in docs:
            metadata = getattr(doc, 'metadata', {})
            doc_name = metadata.get('name', '')
            if not doc_name:
                doc_name = metadata.get('title', '')
            if not doc_name:
                doc_name = metadata.get('source', '')
            if doc_name:
                docs_info.add(doc_name)

        return ', '.join(docs_info)

    log.debug('save_docs_to_vector_db: document %s %s', _get_docs_info(docs), collection_name)

    # Check if entries with the same hash (metadata.hash) already exist
    if metadata and 'hash' in metadata:
        if has_duplicate_content(collection_name, metadata['hash'], metadata.get('file_id')):
            log.info('Document with hash %s already exists', metadata['hash'])
            raise ValueError(ERROR_MESSAGES.DUPLICATE_CONTENT)

    if split:
        if config['rag.enable_markdown_header_text_splitter']:
            log.info('Using markdown header text splitter')
            # Define headers to split on - covering most common markdown header levels
            markdown_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=[
                    ('#', 'Header 1'),
                    ('##', 'Header 2'),
                    ('###', 'Header 3'),
                    ('####', 'Header 4'),
                    ('#####', 'Header 5'),
                    ('######', 'Header 6'),
                ],
                strip_headers=False,  # Keep headers in content for context
            )

            split_docs = []
            for doc in docs:
                split_docs.extend(
                    [
                        Document(
                            page_content=split_chunk.page_content,
                            metadata={**doc.metadata},
                        )
                        for split_chunk in markdown_splitter.split_text(doc.page_content)
                    ]
                )

            docs = split_docs
            if config['rag.chunk_min_size_target'] > 0:
                docs = merge_docs_to_target_size(request, docs, config)

        if config['rag.text_splitter'] in ['', 'character']:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=config['rag.chunk_size'],
                chunk_overlap=config['rag.chunk_overlap'],
                add_start_index=True,
            )
            docs = text_splitter.split_documents(docs)
        elif config['rag.text_splitter'] == 'token':
            log.info('Using token text splitter: %s', config['rag.tiktoken_encoding_name'])

            tiktoken.get_encoding(str(config['rag.tiktoken_encoding_name']))
            text_splitter = TokenTextSplitter(
                encoding_name=str(config['rag.tiktoken_encoding_name']),
                chunk_size=config['rag.chunk_size'],
                chunk_overlap=config['rag.chunk_overlap'],
                add_start_index=True,
                disallowed_special=TIKTOKEN_DISALLOWED_SPECIAL,
            )
            docs = text_splitter.split_documents(docs)
        elif config['rag.text_splitter'] == 'token_transformers':
            log.info('Using transformers token text splitter')

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=config['rag.chunk_size'],
                chunk_overlap=config['rag.chunk_overlap'],
                length_function=get_splitter_length_function(request, config),
                add_start_index=True,
            )
            docs = text_splitter.split_documents(docs)
        else:
            raise ValueError(ERROR_MESSAGES.DEFAULT('Invalid text splitter'))

    if len(docs) == 0:
        raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

    texts = [sanitize_text_for_db(doc.page_content) for doc in docs]
    metadatas = [
        {
            **doc.metadata,
            **(metadata if metadata else {}),
            'embedding_config': {
                'engine': config['rag.embedding_engine'],
                'model': config['rag.embedding_model'],
            },
        }
        for doc in docs
    ]

    try:
        if get_vector_db_client().has_collection(collection_name=collection_name):
            log.info('collection %s already exists', collection_name)

            if overwrite:
                get_vector_db_client().delete_collection(collection_name=collection_name)
                log.info('deleting existing collection %s', collection_name)
            elif add is False:
                log.info('collection %s already exists, overwrite is False and add is False', collection_name)
                return True

        log.info('generating embeddings for %s', collection_name)
        embedding_function = get_embedding_function(
            config['rag.embedding_engine'],
            config['rag.embedding_model'],
            request.app.state.ef,
            (
                config['rag.openai.api_base_url']
                if config['rag.embedding_engine'] == 'openai'
                else (
                    config['rag.ollama.base_url']
                    if config['rag.embedding_engine'] == 'ollama'
                    else config['rag.azure_openai.base_url']
                )
            ),
            (
                config['rag.openai.api_key']
                if config['rag.embedding_engine'] == 'openai'
                else (
                    config['rag.ollama.api_key']
                    if config['rag.embedding_engine'] == 'ollama'
                    else config['rag.azure_openai.api_key']
                )
            ),
            config['rag.embedding_batch_size'],
            azure_api_version=(
                config['rag.azure_openai.api_version'] if config['rag.embedding_engine'] == 'azure_openai' else None
            ),
            enable_async=config['rag.enable_async_embedding'],
            concurrent_requests=config['rag.embedding_concurrent_requests'],
        )

        # Run async embedding in sync context using the main event loop
        # This allows the main loop to stay responsive to health checks during long operations
        embedding_timeout = RAG_EMBEDDING_TIMEOUT

        future = asyncio.run_coroutine_threadsafe(
            embedding_function(
                list(map(lambda x: x.replace('\n', ' '), texts)),
                prefix=RAG_EMBEDDING_CONTENT_PREFIX,
                user=user,
            ),
            request.app.state.main_loop,
        )
        embeddings = future.result(timeout=embedding_timeout)
        log.info('embeddings generated %s for %s items', len(embeddings), len(texts))

        items = [
            {
                'id': str(uuid.uuid4()),
                'text': text,
                'vector': embeddings[idx],
                'metadata': metadatas[idx],
            }
            for idx, text in enumerate(texts)
        ]

        log.info('adding to collection %s', collection_name)
        get_vector_db_client().insert(
            collection_name=collection_name,
            items=items,
        )

        log.info('added %s items to collection %s', len(items), collection_name)
        return True
    except Exception as e:
        log.exception(e)
        raise e


class ProcessFileForm(BaseModel):
    file_id: str
    content: str | None = None
    collection_name: str | None = None


def has_vector_results(result) -> bool:
    return bool(result and result.ids and result.ids[0])


@router.post('/process/file')
async def process_file(
    request: Request,
    form_data: ProcessFileForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Process a file and save its content to the vector database.
    Note: granular session management is used to prevent connection pool exhaustion.
    The session is committed before external API calls, and updates use a fresh session.
    """
    config = await Config.get_many(*RETRIEVAL_CONFIG_KEYS.values())
    file = await Files.get_file_by_id(form_data.file_id, db=db)
    if file and file.user_id != user.id and user.role != 'admin':
        if not await has_access_to_file(file.id, 'write', user, db=db):
            file = None

    if file:
        try:
            collection_name = form_data.collection_name
            file_collection_name = f'file-{file.id}'

            if collection_name is None:
                collection_name = file_collection_name
            else:
                await _validate_collection_access([collection_name], user, access_type='write')
            collection_names = [collection_name]

            if form_data.content:
                # Update the content in the file
                # Usage: /files/{file_id}/data/content/update, /files/ (audio file upload pipeline)

                try:
                    # /files/{file_id}/data/content/update
                    await ASYNC_VECTOR_DB_CLIENT.delete_collection(collection_name=file_collection_name)
                except Exception:
                    # Audio file upload pipeline
                    pass

                docs = [
                    Document(
                        page_content=form_data.content.replace('<br/>', '\n'),
                        metadata={
                            **filter_file_metadata(file.meta),
                            'name': file.filename,
                            'created_by': file.user_id,
                            'file_id': file.id,
                            'source': file.filename,
                        },
                    )
                ]

                text_content = form_data.content
            elif form_data.collection_name:
                # Add this file to a knowledge collection.
                # Usage: /knowledge/{id}/file/add, /knowledge/{id}/file/update
                # Reuse file-{id} chunks when they exist; otherwise restore file-{id}
                # from stored file content while adding the file to the knowledge collection.

                file_result = await ASYNC_VECTOR_DB_CLIENT.query(
                    collection_name=file_collection_name, filter={'file_id': file.id}
                )
                stored_content = (file.data or {}).get('content')

                if has_vector_results(file_result):
                    # Normal path: reuse the already-processed per-file chunks.
                    docs = [
                        Document(
                            page_content=file_result.documents[0][idx],
                            metadata=file_result.metadatas[0][idx],
                        )
                        for idx, id in enumerate(file_result.ids[0])
                    ]
                elif stored_content is not None:
                    # Repair path: vector chunks are missing, but SQL still has the file text.
                    docs = [
                        Document(
                            page_content=stored_content,
                            metadata={
                                **filter_file_metadata(file.meta),
                                'name': file.filename,
                                'created_by': file.user_id,
                                'file_id': file.id,
                                'source': file.filename,
                            },
                        )
                    ]
                    collection_names.append(file_collection_name)
                else:
                    raise ValueError(ERROR_MESSAGES.EMPTY_CONTENT)

                text_content = stored_content or ''
            else:
                # Process the file and save the content
                # Usage: /files/
                file_path = file.path
                if file_path:
                    file_path = await asyncio.to_thread(Storage.get_file, file_path)
                    loader = build_loader_from_config(config)
                    loader.user = user
                    loader.metadata = {
                        'file_id': file.id,
                        'file_name': file.filename,
                        'file_content_type': file.meta.get('content_type'),
                    }
                    docs = await loader.aload(file.filename, file.meta.get('content_type'), file_path)

                    docs = [
                        Document(
                            page_content=doc.page_content,
                            metadata={
                                **filter_file_metadata(file.meta),
                                **filter_metadata(doc.metadata),
                                'name': file.filename,
                                'created_by': file.user_id,
                                'file_id': file.id,
                                'source': file.filename,
                            },
                        )
                        for doc in docs
                    ]
                else:
                    docs = [
                        Document(
                            page_content=file.data.get('content', ''),
                            metadata={
                                **filter_file_metadata(file.meta),
                                'name': file.filename,
                                'created_by': file.user_id,
                                'file_id': file.id,
                                'source': file.filename,
                            },
                        )
                    ]
                text_content = ' '.join([doc.page_content for doc in docs])

            log.debug('text_content: %s', text_content)
            await Files.update_file_data_by_id(
                file.id,
                {'content': text_content},
                db=db,
            )
            hash = calculate_sha256_string(text_content)

            if config['rag.bypass_embedding_and_retrieval']:
                await Files.update_file_data_by_id(file.id, {'status': 'completed', 'error': None}, db=db)
                await Files.update_file_hash_by_id(file.id, hash, db=db)
                await publish_event(
                    request,
                    EVENTS.RETRIEVAL_CONTENT_PROCESSED,
                    actor=user,
                    subject_id=file.id,
                    subject_type='file',
                    data={'collection_name': None, 'filename': file.filename},
                )
                return {
                    'status': True,
                    'collection_name': None,
                    'filename': file.filename,
                    'content': text_content,
                }
            else:
                try:
                    # Commit any pending changes before the slow embedding step.
                    # Note: file is already a Pydantic model (not ORM), so no expunge needed.
                    await db.commit()

                    # External embedding API takes time (5-60s+).
                    # Subsequent updates use fresh async sessions.
                    # NOTE: save_docs_to_vector_db is a sync function that
                    # calls asyncio.run_coroutine_threadsafe(..., main_loop).result()
                    # which blocks the calling thread.  We MUST run it in a
                    # worker thread to avoid deadlocking the event loop.
                    result = True
                    for name in collection_names:
                        result = await run_in_threadpool(
                            save_docs_to_vector_db,
                            request,
                            docs=docs,
                            collection_name=name,
                            config=config,
                            metadata={
                                'file_id': file.id,
                                'name': file.filename,
                                'hash': hash,
                            },
                            add=(True if form_data.collection_name else False),
                            user=user,
                        )
                    log.info('added %s items to collection %s', len(docs), collection_name)

                    if result:
                        # Fresh session for the final update.
                        async with get_async_db() as session:
                            await Files.update_file_metadata_by_id(
                                file.id,
                                {
                                    'collection_name': collection_name,
                                },
                                db=session,
                            )

                            await Files.update_file_data_by_id(
                                file.id,
                                {'status': 'completed', 'error': None},
                                db=session,
                            )
                            await Files.update_file_hash_by_id(file.id, hash, db=session)

                            await publish_event(
                                request,
                                EVENTS.RETRIEVAL_CONTENT_PROCESSED,
                                actor=user,
                                subject_id=file.id,
                                subject_type='file',
                                data={'collection_name': collection_name, 'filename': file.filename},
                            )
                            return {
                                'status': True,
                                'collection_name': collection_name,
                                'filename': file.filename,
                                'content': text_content,
                            }
                    else:
                        raise Exception('Error saving document to vector database')
                except Exception as e:
                    raise e

        except Exception as e:
            log.exception(e)
            # Fresh session for error status update.
            async with get_async_db() as session:
                await Files.update_file_data_by_id(
                    file.id,
                    {'status': 'failed', 'error': str(e)},
                    db=session,
                )
                # Clear the hash so the file can be re-uploaded after fixing the issue
                await Files.update_file_hash_by_id(file.id, None, db=session)

            await publish_event(
                request,
                EVENTS.RETRIEVAL_CONTENT_PROCESS_FAILED,
                actor=user,
                subject_id=file.id,
                subject_type='file',
                data={
                    'collection_name': collection_name,
                    'filename': file.filename,
                    'message': f'{file.filename}: {e}',
                },
            )

            if 'No pandoc was found' in str(e):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.PANDOC_NOT_INSTALLED,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )

    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)


class ProcessTextForm(BaseModel):
    name: str
    content: str
    collection_name: str | None = None


@router.post('/process/text')
async def process_text(
    request: Request,
    form_data: ProcessTextForm,
    user=Depends(get_verified_user),
):
    collection_name = form_data.collection_name
    if collection_name is None:
        collection_name = calculate_sha256_string(form_data.content)
    else:
        await _validate_collection_access([collection_name], user, access_type='write')

    docs = [
        Document(
            page_content=form_data.content,
            metadata={'name': form_data.name, 'created_by': user.id},
        )
    ]
    text_content = form_data.content
    log.debug('text_content: %s', text_content)

    config = await Config.get_many(*RETRIEVAL_CONFIG_KEYS.values())
    result = await run_in_threadpool(save_docs_to_vector_db, request, docs, collection_name, config, user=user)
    if result:
        await publish_event(
            request,
            EVENTS.RETRIEVAL_CONTENT_PROCESSED,
            actor=user,
            subject_id=collection_name,
            subject_type='retrieval.collection',
            data={'name': form_data.name, 'content_preview': text_content[:300]},
        )
        return {
            'status': True,
            'collection_name': collection_name,
            'content': text_content,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


async def _fetch_url(url: str, max_size_mb: int | str | None) -> dict:
    await asyncio.to_thread(validate_url, url)
    max_bytes = None
    if max_size_mb:
        try:
            max_bytes = int(max_size_mb) * 1024 * 1024
        except (TypeError, ValueError):
            max_bytes = None

    headers = {'User-Agent': USER_AGENT} if USER_AGENT else None

    async with get_ssrf_safe_session() as session:
        async with session.get(
            url, headers=headers, ssl=AIOHTTP_CLIENT_SESSION_SSL, allow_redirects=AIOHTTP_CLIENT_ALLOW_REDIRECTS
        ) as response:
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '')
            content_disposition = response.headers.get('Content-Disposition', '')
            content_length = response.headers.get('Content-Length')
            base_content_type = content_type.split(';')[0].strip().lower()
            is_attachment = content_disposition.split(';')[0].strip().lower() == 'attachment'

            chunks = []
            total = 0

            iterator = response.content.iter_chunked(64 * 1024)
            first_chunk = await anext(iterator, b'')

            if not is_attachment and base_content_type in {'text/html', 'application/xhtml+xml'}:
                return {'kind': 'web'}

            if not is_attachment and base_content_type in {'', 'application/octet-stream', 'binary/octet-stream'}:
                sample = first_chunk[:4096].lstrip().lower()
                if (
                    sample.startswith((b'<!doctype html', b'<html', b'<head', b'<body', b'<?xml'))
                    or b'<html' in sample[:1024]
                ):
                    return {'kind': 'web'}

            if max_bytes and content_length:
                try:
                    if int(content_length) > max_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=ERROR_MESSAGES.FILE_TOO_LARGE(size=f'{max_size_mb} MB'),
                        )
                except ValueError:
                    pass

            if first_chunk:
                chunks.append(first_chunk)
                total += len(first_chunk)
                if max_bytes and total > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=ERROR_MESSAGES.FILE_TOO_LARGE(size=f'{max_size_mb} MB'),
                    )

            async for chunk in iterator:
                if not chunk:
                    continue
                chunks.append(chunk)
                total += len(chunk)
                if max_bytes and total > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=ERROR_MESSAGES.FILE_TOO_LARGE(size=f'{max_size_mb} MB'),
                    )

            data = b''.join(chunks)

            image_mime = None
            try:
                from PIL import Image

                image = Image.open(io.BytesIO(data))
                image.verify()
                image_mime = Image.MIME.get(image.format) if image.format else None
            except Exception:
                image_mime = None

            if base_content_type.startswith('image/') and image_mime is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT('Invalid image content'),
                )

            filename = ''
            filename_star = re.search(r"filename\*=UTF-8''([^;]+)", content_disposition, re.IGNORECASE)
            filename_plain = re.search(r'filename="?([^";]+)"?', content_disposition, re.IGNORECASE)
            if filename_star:
                filename = unquote(filename_star.group(1))
            elif filename_plain:
                filename = filename_plain.group(1)
            if not filename:
                filename = os.path.basename(urlparse(url).path)
            filename = os.path.basename(filename or 'download')

            resolved_content_type = (
                image_mime or base_content_type or mimetypes.guess_type(filename)[0] or 'application/octet-stream'
            )
            if not os.path.splitext(filename)[1]:
                filename = f'{filename}{mimetypes.guess_extension(resolved_content_type) or ".bin"}'

            return {
                'kind': 'file',
                'data': data,
                'filename': filename,
                'content_type': resolved_content_type,
            }


@router.post('/process/url', response_model=ProcessUrlResponse)
async def process_url(
    request: Request,
    form_data: ProcessUrlForm,
    process: bool = Query(True, description='Whether to process and save the content'),
    user=Depends(get_verified_user),
):
    try:
        if is_youtube_url(form_data.url):
            result = await process_web(request, form_data, process=process, user=user)
            return {
                'status': True,
                'type': 'youtube',
                'name': form_data.url,
                'url': form_data.url,
                'collection_name': result.get('collection_name'),
                'content': result.get('content'),
            }

        config = await Config.get_many(*RETRIEVAL_CONFIG_KEYS.values())
        try:
            url_result = await _fetch_url(form_data.url, config['rag.file.max_size'])
        except HTTPException:
            raise
        except Exception as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e, f'Could not read content from {form_data.url}'),
            )

        if url_result['kind'] == 'web':
            result = await process_web(request, form_data, process=process, user=user)
            return {
                'status': True,
                'type': 'web',
                'name': form_data.url,
                'url': form_data.url,
                'collection_name': result.get('collection_name'),
                'content': result.get('content'),
            }

        from open_webui.routers.files import upload_file_handler

        is_image = url_result['content_type'].startswith('image/')
        file = UploadFile(
            file=io.BytesIO(url_result['data']),
            filename=url_result['filename'],
            headers={'content-type': url_result['content_type']},
        )
        uploaded_file = await upload_file_handler(
            request,
            file=file,
            metadata={'source_url': form_data.url},
            process=process and not is_image,
            process_in_background=False,
            user=user,
        )
        file_data = uploaded_file.model_dump() if hasattr(uploaded_file, 'model_dump') else uploaded_file
        file_id = file_data.get('id') if isinstance(file_data, dict) else None
        if file_id:
            refreshed_file = await Files.get_file_by_id(file_id)
            if refreshed_file:
                file_data = refreshed_file.model_dump()
        return {
            'status': True,
            'type': 'image' if is_image else 'file',
            'name': url_result['filename'],
            'url': form_data.url,
            'collection_name': (file_data.get('meta') or {}).get('collection_name'),
            'file': file_data,
        }
    except HTTPException:
        raise
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error processing URL'),
        )


@router.post('/process/youtube')
@router.post('/process/web')
async def process_web(
    request: Request,
    form_data: ProcessUrlForm,
    process: bool = Query(True, description='Whether to process and save the content'),
    overwrite: bool = Query(True, description='Whether to overwrite existing collection'),
    user=Depends(get_verified_user),
):
    config = await Config.get_many(*RETRIEVAL_CONFIG_KEYS.values())

    try:
        content, docs = await get_content_from_url(request, form_data.url, config=config)
    except HTTPException:
        raise
    except YoutubeTranscriptError as e:
        log.warning('YouTube transcript unavailable for %s: %s', form_data.url, e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, f'Could not read content from {form_data.url}'),
        )

    # web loaders swallow fetch errors and return no documents
    if not docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(f'Could not read content from {form_data.url}'),
        )

    try:
        log.debug('text_content: %s', content)

        if process:
            collection_name = form_data.collection_name
            if not collection_name:
                collection_name = calculate_sha256_string(form_data.url)[:63]
            else:
                await _validate_collection_access([collection_name], user, access_type='write')

            if not config['web.search.bypass_embedding_and_retrieval']:
                await run_in_threadpool(
                    save_docs_to_vector_db,
                    request,
                    docs,
                    collection_name,
                    config,
                    overwrite=overwrite,
                    add=(not overwrite),
                    user=user,
                )
            else:
                collection_name = None

            return {
                'status': True,
                'collection_name': collection_name,
                'filename': form_data.url,
                'content': content,
                'file': {
                    'data': {
                        'content': content,
                    },
                    'meta': {
                        'name': form_data.url,
                        'source': form_data.url,
                    },
                },
            }
        else:
            return {
                'status': True,
                'content': content,
            }
    except HTTPException:
        raise
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error querying knowledge base'),
        )


async def search_web(
    request: Request, engine: str, query: str, user=None, *, config: dict | None = None
) -> list[SearchResult]:
    """Dispatch a web search query to the configured engine and return results.

    Providers that have been migrated to async (aiohttp) are awaited natively.
    Legacy sync providers are offloaded via ``asyncio.to_thread`` to avoid
    blocking the event loop.
    """

    # TODO: add playwright to search the web
    if config is None:
        config = await Config.get_many(*RETRIEVAL_CONFIG_KEYS.values())
    if engine == 'ollama_cloud':
        return await asyncio.to_thread(
            search_ollama_cloud,
            'https://ollama.com',
            config['web.search.ollama_cloud_api_key'],
            query,
            config['web.search.result_count'],
            config['web.search.domain.filter_list'],
        )
    elif engine == 'perplexity_search':
        if config['web.search.perplexity_api_key']:
            return await asyncio.to_thread(
                search_perplexity_search,
                config['web.search.perplexity_api_key'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
                config['web.search.perplexity_search_api_url'],
                user,
            )
        else:
            raise Exception('No PERPLEXITY_API_KEY found in environment variables')
    elif engine == 'searxng':
        if config['web.search.searxng_query_url']:
            searxng_kwargs = {'language': config['web.search.searxng_language']}
            return await search_searxng(
                config['web.search.searxng_query_url'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
                **searxng_kwargs,
            )
        else:
            raise Exception('No SEARXNG_QUERY_URL found in environment variables')
    elif engine == 'openserp':
        if config['web.search.openserp_base_url']:
            return await search_openserp(
                config['web.search.openserp_base_url'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
            )
        else:
            raise Exception('No OPENSERP_BASE_URL found in environment variables')
    elif engine == 'yacy':
        if config['web.search.yacy_query_url']:
            return await asyncio.to_thread(
                search_yacy,
                config['web.search.yacy_query_url'],
                config['web.search.yacy_username'],
                config['web.search.yacy_password'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
            )
        else:
            raise Exception('No YACY_QUERY_URL found in environment variables')
    elif engine == 'google_pse':
        if config['web.search.google_pse_api_key'] and config['web.search.google_pse_engine_id']:
            return await search_google_pse(
                config['web.search.google_pse_api_key'],
                config['web.search.google_pse_engine_id'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
                referer=config['webui.url'],
            )
        else:
            raise Exception('No GOOGLE_PSE_API_KEY or GOOGLE_PSE_ENGINE_ID found in environment variables')
    elif engine == 'brave':
        if config['web.search.brave_search_api_key']:
            return await search_brave(
                config['web.search.brave_search_api_key'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
            )
        else:
            raise Exception('No BRAVE_SEARCH_API_KEY found in environment variables')
    elif engine == 'brave_llm_context':
        if config['web.search.brave_search_api_key']:
            return await asyncio.to_thread(
                search_brave_llm_context,
                config['web.search.brave_search_api_key'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
                config['web.search.brave_search_context_tokens'],
            )
        else:
            raise Exception('No BRAVE_SEARCH_API_KEY found in environment variables')
    elif engine == 'kagi':
        if config['web.search.kagi_search_api_key']:
            return await asyncio.to_thread(
                search_kagi,
                config['web.search.kagi_search_api_key'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
            )
        else:
            raise Exception('No KAGI_SEARCH_API_KEY found in environment variables')
    elif engine == 'mojeek':
        if config['web.search.mojeek_search_api_key']:
            return await asyncio.to_thread(
                search_mojeek,
                config['web.search.mojeek_search_api_key'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
            )
        else:
            raise Exception('No MOJEEK_SEARCH_API_KEY found in environment variables')
    elif engine == 'bocha':
        if config['web.search.bocha_search_api_key']:
            return await asyncio.to_thread(
                search_bocha,
                config['web.search.bocha_search_api_key'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
            )
        else:
            raise Exception('No BOCHA_SEARCH_API_KEY found in environment variables')
    elif engine == 'serpstack':
        if config['web.search.serpstack_api_key']:
            return await search_serpstack(
                config['web.search.serpstack_api_key'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
                https_enabled=config['web.search.serpstack_https'],
            )
        else:
            raise Exception('No SERPSTACK_API_KEY found in environment variables')
    elif engine == 'serper':
        if config['web.search.serper_api_key']:
            return await search_serper(
                config['web.search.serper_api_key'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
            )
        else:
            raise Exception('No SERPER_API_KEY found in environment variables')
    elif engine == 'serphouse':
        if config['web.search.serphouse_api_key']:
            return await search_serphouse(
                config['web.search.serphouse_api_key'],
                config['web.search.serphouse_domain'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
            )
        else:
            raise Exception('No SERPHOUSE_API_KEY found in environment variables')
    elif engine == 'serply':
        if config['web.search.serply_api_key']:
            return await asyncio.to_thread(
                search_serply,
                config['web.search.serply_api_key'],
                query,
                config['web.search.result_count'],
                filter_list=config['web.search.domain.filter_list'],
            )
        else:
            raise Exception('No SERPLY_API_KEY found in environment variables')
    elif engine == 'duckduckgo':
        return await asyncio.to_thread(
            search_duckduckgo,
            query,
            config['web.search.result_count'],
            config['web.search.domain.filter_list'],
            concurrent_requests=config['web.search.concurrent_requests'],
            backend=config['web.search.ddgs_backend'],
        )
    elif engine == 'tavily':
        if config['web.search.tavily_api_key']:
            return await asyncio.to_thread(
                search_tavily,
                config['web.search.tavily_api_key'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
                search_depth=config['web.search.tavily_search_depth'],
            )
        else:
            raise Exception('No TAVILY_API_KEY found in environment variables')
    elif engine == 'staan':
        if config['web.search.staan_api_key']:
            return await asyncio.to_thread(
                search_staan,
                config['web.search.staan_api_key'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
                market=config['web.search.staan_market'],
                max_snippets=config['web.search.staan_max_snippets'],
            )
        else:
            raise Exception('No STAAN_API_KEY found in environment variables')
    elif engine == 'exa':
        if config['web.search.exa_api_key']:
            return await asyncio.to_thread(
                search_exa,
                config['web.search.exa_api_key'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
                max_content_length=config['web.search.exa_max_content_length'],
            )
        else:
            raise Exception('No EXA_API_KEY found in environment variables')
    elif engine == 'searchapi':
        if config['web.search.searchapi_api_key']:
            return await asyncio.to_thread(
                search_searchapi,
                config['web.search.searchapi_api_key'],
                config['web.search.searchapi_engine'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
            )
        else:
            raise Exception('No SEARCHAPI_API_KEY found in environment variables')
    elif engine == 'serpapi':
        if config['web.search.serpapi_api_key']:
            return await asyncio.to_thread(
                search_serpapi,
                config['web.search.serpapi_api_key'],
                config['web.search.serpapi_engine'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
            )
        else:
            raise Exception('No SERPAPI_API_KEY found in environment variables')
    elif engine == 'jina':
        return await asyncio.to_thread(
            search_jina,
            config['web.search.jina_api_key'],
            query,
            config['web.search.result_count'],
            config['web.search.jina_api_base_url'],
        )
    elif engine == 'bing':
        return await asyncio.to_thread(
            search_bing,
            config['web.search.bing_search_v7_subscription_key'],
            config['web.search.bing_search_v7_endpoint'],
            str(DEFAULT_LOCALE),
            query,
            config['web.search.result_count'],
            config['web.search.domain.filter_list'],
        )
    elif engine == 'azure':
        if (
            config['web.search.azure_ai_search_api_key']
            and config['web.search.azure_ai_search_endpoint']
            and config['web.search.azure_ai_search_index_name']
        ):
            return await asyncio.to_thread(
                search_azure,
                config['web.search.azure_ai_search_api_key'],
                config['web.search.azure_ai_search_endpoint'],
                config['web.search.azure_ai_search_index_name'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
            )
        else:
            raise Exception(
                'AZURE_AI_SEARCH_API_KEY, AZURE_AI_SEARCH_ENDPOINT, and AZURE_AI_SEARCH_INDEX_NAME are required for Azure AI Search'
            )
    elif engine == 'perplexity':
        return await asyncio.to_thread(
            search_perplexity,
            config['web.search.perplexity_api_key'],
            query,
            config['web.search.result_count'],
            config['web.search.domain.filter_list'],
            model=config['web.search.perplexity_model'],
            search_context_usage=config['web.search.perplexity_search_context_usage'],
        )
    elif engine == 'microsoft_web_iq':
        if config['web.search.microsoft_web_iq_api_key']:
            return await asyncio.to_thread(
                search_microsoft_web_iq,
                config['web.search.microsoft_web_iq_api_base_url'],
                config['web.search.microsoft_web_iq_api_key'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
                config['web.search.microsoft_web_iq_language'],
                user,
            )
        else:
            raise Exception('No MICROSOFT_WEB_IQ_API_KEY found in environment variables')
    elif engine == 'sougou':
        if config['web.search.sougou_api_sid'] and config['web.search.sougou_api_sk']:
            return await asyncio.to_thread(
                search_sougou,
                config['web.search.sougou_api_sid'],
                config['web.search.sougou_api_sk'],
                query,
                config['web.search.result_count'],
                config['web.search.domain.filter_list'],
            )
        else:
            raise Exception('No SOUGOU_API_SID or SOUGOU_API_SK found in environment variables')
    elif engine == 'firecrawl':
        return await asyncio.to_thread(
            search_firecrawl,
            config['web.loader.firecrawl_api_url'],
            config['web.loader.firecrawl_api_key'],
            query,
            config['web.search.result_count'],
            config['web.search.domain.filter_list'],
        )
    elif engine == 'external':
        return await asyncio.to_thread(
            search_external,
            request,
            config['web.search.external_web_search_url'],
            config['web.search.external_web_search_api_key'],
            query,
            config['web.search.result_count'],
            config['web.search.domain.filter_list'],
            user=user,
        )
    elif engine == 'yandex':
        return await asyncio.to_thread(
            search_yandex,
            request,
            config['web.search.yandex_web_search_url'],
            config['web.search.yandex_web_search_api_key'],
            config['web.search.yandex_web_search_config'],
            query,
            config['web.search.result_count'],
            config['web.search.domain.filter_list'],
            user=user,
        )
    elif engine == 'youcom':
        return await asyncio.to_thread(
            search_youcom,
            config['web.search.youcom_api_key'],
            query,
            config['web.search.result_count'],
            config['web.search.domain.filter_list'],
        )
    elif engine == 'linkup':
        if config['web.search.linkup_api_key']:
            return await asyncio.to_thread(
                search_linkup,
                api_key=config['web.search.linkup_api_key'],
                query=query,
                count=config['web.search.result_count'],
                filter_list=config['web.search.domain.filter_list'],
                params=config['web.search.linkup_search_params'],
            )
        else:
            raise Exception('No LINKUP_API_KEY found in environment variables')
    else:
        raise Exception('No search engine API key found in environment variables')


@router.post('/process/web/search')
async def process_web_search(request: Request, form_data: SearchForm, user=Depends(get_verified_user)):
    config = await Config.get_many(*RETRIEVAL_CONFIG_KEYS.values())
    if not config['web.search.enable']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if user.role != 'admin' and not await has_permission(user.id, 'features.web_search', config['user.permissions']):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    urls = []
    result_items = []

    try:
        logging.debug('trying to web search with %s', (config['web.search.engine'], form_data.queries))

        # Use semaphore to limit concurrent requests based on WEB_SEARCH_CONCURRENT_REQUESTS
        # 0 or None = unlimited (previous behavior), positive number = limited concurrency
        # Set to 1 for sequential execution (rate-limited APIs like Brave free tier)
        concurrent_limit = config['web.search.concurrent_requests']

        if concurrent_limit:
            # Limited concurrency with semaphore
            semaphore = asyncio.Semaphore(concurrent_limit)

            async def search_query_with_semaphore(query):
                async with semaphore:
                    return await search_web(
                        request,
                        config['web.search.engine'],
                        query,
                        user,
                        config=config,
                    )

            search_tasks = [search_query_with_semaphore(query) for query in form_data.queries]
        else:
            # Unlimited parallel execution
            search_tasks = [
                search_web(
                    request,
                    config['web.search.engine'],
                    query,
                    user,
                    config=config,
                )
                for query in form_data.queries
            ]

        search_results = await asyncio.gather(*search_tasks)

        for result in search_results:
            if result:
                for item in result:
                    if item and item.link:
                        result_items.append(item)
                        urls.append(item.link)

        urls = list(dict.fromkeys(urls))
        log.debug('urls: %s', urls)

    except Exception as e:
        log.exception('Web search failed')
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, ERROR_MESSAGES.WEB_SEARCH_ERROR),
        )

    if len(urls) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.DEFAULT('No results found from web search'),
        )

    try:
        if config['web.search.bypass_web_loader']:
            search_results = [item for result in search_results for item in result if result]

            docs = [
                Document(
                    page_content=result.snippet,
                    metadata={
                        'source': result.link,
                        'title': result.title,
                        'snippet': result.snippet,
                        'link': result.link,
                    },
                )
                for result in search_results
                if hasattr(result, 'snippet') and result.snippet is not None
            ]
        else:
            loader = get_web_loader(urls, config)
            docs = await loader.aload()

        urls = [
            doc.metadata.get('source') for doc in docs if doc.metadata.get('source')
        ]  # only keep the urls returned by the loader
        url_set = set(urls)
        result_items = [
            dict(item) for item in result_items if item.link in url_set
        ]  # only keep the search results that have been loaded

        if config['web.search.bypass_embedding_and_retrieval']:
            return {
                'status': True,
                'collection_name': None,
                'filenames': urls,
                'items': result_items,
                'docs': [
                    {
                        'content': doc.page_content,
                        'metadata': doc.metadata,
                    }
                    for doc in docs
                ],
                'loaded_count': len(docs),
            }
        else:
            if not any(doc.page_content.strip() for doc in docs):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.DEFAULT('None of the web search results could be loaded'),
                )

            # Create a single collection for all documents
            # Bind the ephemeral collection to its owner so filter_accessible_collections can scope it per-user.
            collection_name = f'web-search-{user.id}-{calculate_sha256_string("-".join(form_data.queries))}'[:63]

            try:
                await run_in_threadpool(
                    save_docs_to_vector_db,
                    request,
                    docs,
                    collection_name,
                    config,
                    overwrite=True,
                    user=user,
                )
            except Exception as e:
                # Surface the failure instead of returning an unusable collection
                log.exception(f'Error saving web search results to vector DB: {e}')
                raise HTTPException(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='Failed to embed and store the retrieved web pages. Check the embedding configuration in Admin Settings > Documents.',
                )

            return {
                'status': True,
                'collection_names': [collection_name],
                'items': result_items,
                'filenames': urls,
                'loaded_count': len(docs),
            }
    except HTTPException:
        raise
    except Exception as e:
        log.exception('Web search content loading failed')
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, ERROR_MESSAGES.WEB_SEARCH_ERROR),
        )


async def _validate_collection_access(collection_names: list[str], user, access_type: str = 'read') -> None:
    """
    Raise 403 if the user lacks access to any of the requested collections.
    Delegates to the shared filter_accessible_collections utility so the
    access rules stay in one place.
    """
    requested = set(collection_names)
    allowed = await filter_accessible_collections(requested, user, access_type=access_type)
    denied = requested - allowed
    if denied:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


class QueryDocForm(BaseModel):
    collection_name: str
    query: str
    k: int | None = None
    k_reranker: int | None = None
    r: float | None = None
    hybrid: bool | None = None
    hybrid_bm25_weight: float | None = None


@router.post('/query/doc')
async def query_doc_handler(
    request: Request,
    form_data: QueryDocForm,
    user=Depends(get_verified_user),
):
    config = await Config.get_many(*RETRIEVAL_CONFIG_KEYS.values())
    await _validate_collection_access([form_data.collection_name], user)

    try:
        if config['rag.enable_hybrid_search'] and (form_data.hybrid is None or form_data.hybrid):
            return await query_doc_with_hybrid_search(
                collection_name=form_data.collection_name,
                collection_result=None,
                query=form_data.query,
                embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                    query, prefix=prefix, user=user
                ),
                k=form_data.k if form_data.k else config['rag.top_k'],
                reranking_function=(
                    (lambda query, documents: request.app.state.RERANKING_FUNCTION(query, documents, user=user))
                    if request.app.state.RERANKING_FUNCTION
                    else None
                ),
                k_reranker=form_data.k_reranker or config['rag.top_k_reranker'],
                r=(form_data.r if form_data.r else config['rag.relevance_threshold']),
                hybrid_bm25_weight=(
                    form_data.hybrid_bm25_weight
                    if form_data.hybrid_bm25_weight is not None
                    else config['rag.hybrid_bm25_weight']
                ),
            )
        else:
            query_embedding = await request.app.state.EMBEDDING_FUNCTION(
                form_data.query, prefix=RAG_EMBEDDING_QUERY_PREFIX, user=user
            )
            # query_doc wraps a blocking get_vector_db_client().search call;
            # offload so the request's event loop stays responsive.
            return await asyncio.to_thread(
                query_doc,
                collection_name=form_data.collection_name,
                query_embedding=query_embedding,
                k=form_data.k if form_data.k else config['rag.top_k'],
                user=user,
            )
    except HTTPException:
        raise
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error querying knowledge base'),
        )


class QueryCollectionsForm(BaseModel):
    collection_names: list[str]
    query: str
    k: int | None = None
    k_reranker: int | None = None
    r: float | None = None
    hybrid: bool | None = None
    hybrid_bm25_weight: float | None = None
    enable_enriched_texts: bool | None = None


@router.post('/query/collection')
async def query_collection_handler(
    request: Request,
    form_data: QueryCollectionsForm,
    user=Depends(get_verified_user),
):
    config = await Config.get_many(*RETRIEVAL_CONFIG_KEYS.values())
    await _validate_collection_access(form_data.collection_names, user)

    try:
        if config['rag.enable_hybrid_search'] and (form_data.hybrid is None or form_data.hybrid):
            return await query_collection_with_hybrid_search(
                collection_names=form_data.collection_names,
                queries=[form_data.query],
                embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                    query, prefix=prefix, user=user
                ),
                k=form_data.k if form_data.k else config['rag.top_k'],
                reranking_function=(
                    (lambda query, documents: request.app.state.RERANKING_FUNCTION(query, documents, user=user))
                    if request.app.state.RERANKING_FUNCTION
                    else None
                ),
                k_reranker=form_data.k_reranker or config['rag.top_k_reranker'],
                r=(form_data.r if form_data.r else config['rag.relevance_threshold']),
                hybrid_bm25_weight=(
                    form_data.hybrid_bm25_weight
                    if form_data.hybrid_bm25_weight is not None
                    else config['rag.hybrid_bm25_weight']
                ),
                enable_enriched_texts=(
                    form_data.enable_enriched_texts
                    if form_data.enable_enriched_texts is not None
                    else config['rag.enable_hybrid_search_enriched_texts']
                ),
            )
        else:
            return await query_collection(
                request,
                collection_names=form_data.collection_names,
                queries=[form_data.query],
                embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                    query, prefix=prefix, user=user
                ),
                k=form_data.k if form_data.k else config['rag.top_k'],
                user=user,
            )

    except HTTPException:
        raise
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error querying knowledge base'),
        )


####################################
#
# Vector DB operations
#
####################################


class DeleteForm(BaseModel):
    collection_name: str
    file_id: str


@router.post('/delete')
async def delete_entries_from_collection(
    request: Request,
    form_data: DeleteForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        if await ASYNC_VECTOR_DB_CLIENT.has_collection(collection_name=form_data.collection_name):
            file = await Files.get_file_by_id(form_data.file_id, db=db)
            if not file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
            hash = file.hash

            # Refuse to issue a `filter={'hash': None}` query — the
            # match semantics of a null filter value are
            # backend-dependent (some backends ignore the key, some
            # match every row whose metadata lacks `hash`) and risk
            # deleting unrelated entries. Files without a hash are
            # typically unprocessed / failed / legacy records that
            # can't be targeted by hash anyway.
            if hash is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT('File has no hash; cannot delete vector entries by hash.'),
                )

            # Pre-existing bug: this used `metadata=` which is not a
            # parameter on `VectorDBBase.delete` nor on any backend
            # implementation, so the call always raised TypeError that
            # was silently swallowed by the surrounding `except
            # Exception` and the endpoint reported `{'status': False}`
            # for every request. Use `filter` to actually do what the
            # endpoint name promises.
            await ASYNC_VECTOR_DB_CLIENT.delete(
                collection_name=form_data.collection_name,
                filter={'hash': hash},
            )
            await publish_event(
                request,
                EVENTS.RETRIEVAL_COLLECTION_DELETED,
                actor=user,
                subject_id=form_data.collection_name,
                data={'file_id': form_data.file_id},
            )
            return {'status': True}
        else:
            return {'status': False}
    except HTTPException:
        # Caller-meaningful errors (404/400 above) must not be
        # swallowed and re-shaped as `{'status': False}`.
        raise
    except Exception as e:
        log.exception(e)
        return {'status': False}


@router.post('/reset/db')
async def reset_vector_db(
    request: Request,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    await ASYNC_VECTOR_DB_CLIENT.reset()
    await Knowledges.delete_all_knowledge(db=db)
    await publish_event(
        request,
        EVENTS.RETRIEVAL_VECTOR_DB_RESET,
        actor=user,
        subject_id='default',
    )


@router.post('/reset/uploads')
async def reset_upload_dir(request: Request, user=Depends(get_admin_user)) -> bool:
    folder = f'{UPLOAD_DIR}'
    try:
        # Check if the directory exists
        if await asyncio.to_thread(os.path.exists, folder):
            # Iterate over all the files and directories in the specified directory
            for filename in await asyncio.to_thread(os.listdir, folder):
                file_path = os.path.join(folder, filename)
                try:
                    if await asyncio.to_thread(os.path.isfile, file_path) or await asyncio.to_thread(
                        os.path.islink, file_path
                    ):
                        await asyncio.to_thread(os.unlink, file_path)  # Remove the file or link
                    elif await asyncio.to_thread(os.path.isdir, file_path):
                        await asyncio.to_thread(shutil.rmtree, file_path)  # Remove the directory
                except Exception as e:
                    log.exception(f'Failed to delete {file_path}. Reason: {e}')
        else:
            log.warning(f'The directory {folder} does not exist')
    except Exception as e:
        log.exception(f'Failed to process the directory {folder}. Reason: {e}')

    await publish_event(
        request,
        EVENTS.RETRIEVAL_UPLOADS_RESET,
        actor=user,
        subject_id='all',
        subject_type='file.uploads',
    )
    return True


if ENV == 'dev':

    @router.get('/ef/{text}')
    async def get_embeddings(request: Request, text: str | None = 'Hello World!'):
        return {'result': await request.app.state.EMBEDDING_FUNCTION(text, prefix=RAG_EMBEDDING_QUERY_PREFIX)}


class BatchProcessFilesForm(BaseModel):
    files: list[FileModel]
    collection_name: str


class BatchProcessFilesResult(BaseModel):
    file_id: str
    status: str
    error: str | None = None


class BatchProcessFilesResponse(BaseModel):
    results: list[BatchProcessFilesResult]
    errors: list[BatchProcessFilesResult]


@router.post('/process/files/batch')
async def process_files_batch(
    request: Request,
    form_data: BatchProcessFilesForm,
    user=Depends(get_verified_user),
    db=None,
) -> BatchProcessFilesResponse:
    """
    Process a batch of files and save them to the vector database.

    NOTE: We intentionally do NOT use Depends(get_async_session) here.
    The save_docs_to_vector_db() call makes external embedding API calls which
    can take 5-60+ seconds for batch operations. Database operations after
    embedding (Files.update_file_by_id) manage their own short-lived sessions.
    """

    config = await Config.get_many(*RETRIEVAL_CONFIG_KEYS.values())
    collection_name = form_data.collection_name

    if collection_name:
        await _validate_collection_access([collection_name], user, access_type='write')

    file_results: list[BatchProcessFilesResult] = []
    file_errors: list[BatchProcessFilesResult] = []
    file_updates: list[FileUpdateForm] = []
    seen_hashes: set[str] = set()

    # Prepare all documents first
    all_docs: list[Document] = []

    for file in form_data.files:
        try:
            # Ownership check: verify the requesting user owns the file or is an admin
            db_file = await Files.get_file_by_id(file.id, db=db)
            if not db_file:
                file_errors.append(
                    BatchProcessFilesResult(
                        file_id=file.id,
                        status='failed',
                        error='File not found',
                    )
                )
                continue
            if db_file.user_id != user.id and user.role != 'admin':
                file_errors.append(
                    BatchProcessFilesResult(
                        file_id=file.id,
                        status='failed',
                        error='Permission denied: not file owner',
                    )
                )
                continue

            text_content = file.data.get('content', '')
            hash = calculate_sha256_string(text_content)
            if hash in seen_hashes or await run_in_threadpool(has_duplicate_content, collection_name, hash, file.id):
                raise ValueError(ERROR_MESSAGES.DUPLICATE_CONTENT)
            seen_hashes.add(hash)

            docs: list[Document] = [
                Document(
                    page_content=text_content.replace('<br/>', '\n'),
                    metadata={
                        **filter_file_metadata(file.meta),
                        'name': file.filename,
                        'created_by': file.user_id,
                        'file_id': file.id,
                        'source': file.filename,
                        'hash': hash,
                    },
                )
            ]

            all_docs.extend(docs)

            file_updates.append(
                FileUpdateForm(
                    hash=hash,
                    data={'content': text_content},
                )
            )
            file_results.append(BatchProcessFilesResult(file_id=file.id, status='prepared'))

        except Exception as e:
            log.error(f'process_files_batch: Error processing file {file.id}: {str(e)}')
            file_errors.append(BatchProcessFilesResult(file_id=file.id, status='failed', error=str(e)))

    # Save all documents in one batch
    if all_docs:
        try:
            await run_in_threadpool(
                save_docs_to_vector_db,
                request,
                all_docs,
                collection_name,
                config,
                add=True,
                user=user,
            )

            # Update all files with collection name
            for file_update, file_result in zip(file_updates, file_results):
                await Files.update_file_by_id(id=file_result.file_id, form_data=file_update, db=db)
                file_result.status = 'completed'

        except Exception as e:
            log.error(f'process_files_batch: Error saving documents to vector DB: {str(e)}')
            for file_result in file_results:
                file_result.status = 'failed'
                file_errors.append(BatchProcessFilesResult(file_id=file_result.file_id, status='failed', error=str(e)))

    response = BatchProcessFilesResponse(results=file_results, errors=file_errors)
    await publish_event(
        request,
        EVENTS.RETRIEVAL_CONTENT_PROCESSED,
        actor=user,
        subject_id=collection_name,
        subject_type='retrieval.collection',
        data={
            'count': len([item for item in file_results if item.status == 'completed']),
            'errors': len(file_errors),
        },
    )
    return response
