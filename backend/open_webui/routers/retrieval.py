from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import os
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, Iterator, Optional, Sequence, Union

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
    DEVICE_TYPE,
    DOCKER,
    RAG_EMBEDDING_TIMEOUT,
    SENTENCE_TRANSFORMERS_BACKEND,
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_BACKEND,
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_MODEL_KWARGS,
    SENTENCE_TRANSFORMERS_CROSS_ENCODER_SIGMOID_ACTIVATION_FUNCTION,
    SENTENCE_TRANSFORMERS_MODEL_KWARGS,
)
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_db, get_async_session
from open_webui.models.files import FileModel, Files, FileUpdateForm
from open_webui.models.knowledge import Knowledges
from open_webui.models.config import Config

# Document loaders
from open_webui.retrieval.loaders.youtube import YoutubeLoader
from open_webui.retrieval.utils import (
    build_loader_from_config,
    get_loader_config,
    filter_accessible_collections,
    get_content_from_url,
    get_embedding_function,
    get_model_path,
    get_reranking_function,
    query_collection,
    query_collection_with_hybrid_search,
    query_doc,
    query_doc_with_hybrid_search,
)
from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
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

# Web search engines
from open_webui.retrieval.web.main import SearchResult
from open_webui.retrieval.web.microsoft_web_iq import search_microsoft_web_iq
from open_webui.retrieval.web.mojeek import search_mojeek
from open_webui.retrieval.web.ollama import search_ollama_cloud
from open_webui.retrieval.web.perplexity import search_perplexity
from open_webui.retrieval.web.perplexity_search import search_perplexity_search
from open_webui.retrieval.web.searchapi import search_searchapi
from open_webui.retrieval.web.searxng import search_searxng
from open_webui.retrieval.web.serpapi import search_serpapi
from open_webui.retrieval.web.serper import search_serper
from open_webui.retrieval.web.serphouse import search_serphouse
from open_webui.retrieval.web.serply import search_serply
from open_webui.retrieval.web.serpstack import search_serpstack
from open_webui.retrieval.web.sougou import search_sougou
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
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

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
    if embedding_model and engine == '':
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
            if engine == 'external':
                try:
                    from open_webui.retrieval.models.external import ExternalReranker

                    rf = ExternalReranker(
                        url=external_reranker_url,
                        api_key=external_reranker_api_key,
                        model=reranking_model,
                        timeout=timeout_value,
                    )
                except Exception as e:
                    log.error(f'ExternalReranking: {e}')
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
                            torch.nn.Sigmoid()
                            if SENTENCE_TRANSFORMERS_CROSS_ENCODER_SIGMOID_ACTIVATION_FUNCTION
                            else None
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
                                log.debug(f'Missing pad_token_id detected; set to eos_token_id={eos}')
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


router = APIRouter()

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
    'TAVILY_API_KEY': 'web.search.tavily_api_key',
    'TAVILY_EXTRACT_DEPTH': 'web.search.tavily_extract_depth',
    'TEXT_SPLITTER': 'rag.text_splitter',
    'TIKA_SERVER_URL': 'rag.tika_server_url',
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


class RetrievalConfig(SimpleNamespace):
    def __init__(self, values: dict):
        super().__init__(**values)
        object.__setattr__(self, '_updates', {})

    def __setattr__(self, key: str, value):
        if key.startswith('_'):
            object.__setattr__(self, key, value)
            return
        object.__setattr__(self, key, value)
        if key in RETRIEVAL_CONFIG_KEYS:
            self._updates[RETRIEVAL_CONFIG_KEYS[key]] = value

    async def save(self) -> None:
        if self._updates:
            await Config.upsert(dict(self._updates))
            self._updates.clear()


async def get_config_values(key_map: dict[str, str]) -> dict:
    values = await Config.get_many(*key_map.values())
    return {field: values[storage_key] for field, storage_key in key_map.items() if storage_key in values}


async def get_retrieval_config() -> RetrievalConfig:
    return RetrievalConfig(await get_config_values(RETRIEVAL_CONFIG_KEYS))


class CollectionNameForm(BaseModel):
    collection_name: str | None = None


class ProcessUrlForm(CollectionNameForm):
    url: str


class SearchForm(BaseModel):
    queries: list[str]


@router.get('/embedding')
async def get_embedding_config(request: Request, user=Depends(get_admin_user)):
    config = await get_retrieval_config()
    return {
        'status': True,
        'RAG_EMBEDDING_ENGINE': config.RAG_EMBEDDING_ENGINE,
        'RAG_EMBEDDING_MODEL': config.RAG_EMBEDDING_MODEL,
        'RAG_EMBEDDING_BATCH_SIZE': config.RAG_EMBEDDING_BATCH_SIZE,
        'ENABLE_ASYNC_EMBEDDING': config.ENABLE_ASYNC_EMBEDDING,
        'RAG_EMBEDDING_CONCURRENT_REQUESTS': config.RAG_EMBEDDING_CONCURRENT_REQUESTS,
        'openai_config': {
            'url': config.RAG_OPENAI_API_BASE_URL,
            'key': config.RAG_OPENAI_API_KEY,
        },
        'ollama_config': {
            'url': config.RAG_OLLAMA_BASE_URL,
            'key': config.RAG_OLLAMA_API_KEY,
        },
        'azure_openai_config': {
            'url': config.RAG_AZURE_OPENAI_BASE_URL,
            'key': config.RAG_AZURE_OPENAI_API_KEY,
            'version': config.RAG_AZURE_OPENAI_API_VERSION,
        },
    }


class OpenAIConfigForm(BaseModel):
    url: str
    key: str


class OllamaConfigForm(BaseModel):
    url: str
    key: str


class AzureOpenAIConfigForm(BaseModel):
    url: str
    key: str
    version: str


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
    config = await get_retrieval_config()
    if config.RAG_EMBEDDING_ENGINE == '':
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
    config = await get_retrieval_config()
    log.info(f'Updating embedding model: {config.RAG_EMBEDDING_MODEL} to {form_data.RAG_EMBEDDING_MODEL}')
    await unload_embedding_model(request)
    try:
        config.RAG_EMBEDDING_ENGINE = form_data.RAG_EMBEDDING_ENGINE
        config.RAG_EMBEDDING_MODEL = form_data.RAG_EMBEDDING_MODEL.strip()
        config.RAG_EMBEDDING_BATCH_SIZE = form_data.RAG_EMBEDDING_BATCH_SIZE
        config.ENABLE_ASYNC_EMBEDDING = form_data.ENABLE_ASYNC_EMBEDDING
        config.RAG_EMBEDDING_CONCURRENT_REQUESTS = form_data.RAG_EMBEDDING_CONCURRENT_REQUESTS

        if config.RAG_EMBEDDING_ENGINE in [
            'ollama',
            'openai',
            'azure_openai',
        ]:
            if form_data.openai_config is not None:
                config.RAG_OPENAI_API_BASE_URL = form_data.openai_config.url
                config.RAG_OPENAI_API_KEY = form_data.openai_config.key

            if form_data.ollama_config is not None:
                config.RAG_OLLAMA_BASE_URL = form_data.ollama_config.url
                config.RAG_OLLAMA_API_KEY = form_data.ollama_config.key

            if form_data.azure_openai_config is not None:
                config.RAG_AZURE_OPENAI_BASE_URL = form_data.azure_openai_config.url
                config.RAG_AZURE_OPENAI_API_KEY = form_data.azure_openai_config.key
                config.RAG_AZURE_OPENAI_API_VERSION = form_data.azure_openai_config.version

        request.app.state.ef = get_ef(
            config.RAG_EMBEDDING_ENGINE,
            config.RAG_EMBEDDING_MODEL,
        )

        request.app.state.EMBEDDING_FUNCTION = get_embedding_function(
            config.RAG_EMBEDDING_ENGINE,
            config.RAG_EMBEDDING_MODEL,
            request.app.state.ef,
            (
                config.RAG_OPENAI_API_BASE_URL
                if config.RAG_EMBEDDING_ENGINE == 'openai'
                else (
                    config.RAG_OLLAMA_BASE_URL
                    if config.RAG_EMBEDDING_ENGINE == 'ollama'
                    else config.RAG_AZURE_OPENAI_BASE_URL
                )
            ),
            (
                config.RAG_OPENAI_API_KEY
                if config.RAG_EMBEDDING_ENGINE == 'openai'
                else (
                    config.RAG_OLLAMA_API_KEY
                    if config.RAG_EMBEDDING_ENGINE == 'ollama'
                    else config.RAG_AZURE_OPENAI_API_KEY
                )
            ),
            config.RAG_EMBEDDING_BATCH_SIZE,
            azure_api_version=(
                config.RAG_AZURE_OPENAI_API_VERSION if config.RAG_EMBEDDING_ENGINE == 'azure_openai' else None
            ),
            enable_async=config.ENABLE_ASYNC_EMBEDDING,
            concurrent_requests=config.RAG_EMBEDDING_CONCURRENT_REQUESTS,
        )

        await config.save()
        return {
            'status': True,
            'RAG_EMBEDDING_ENGINE': config.RAG_EMBEDDING_ENGINE,
            'RAG_EMBEDDING_MODEL': config.RAG_EMBEDDING_MODEL,
            'RAG_EMBEDDING_BATCH_SIZE': config.RAG_EMBEDDING_BATCH_SIZE,
            'ENABLE_ASYNC_EMBEDDING': config.ENABLE_ASYNC_EMBEDDING,
            'RAG_EMBEDDING_CONCURRENT_REQUESTS': config.RAG_EMBEDDING_CONCURRENT_REQUESTS,
            'openai_config': {
                'url': config.RAG_OPENAI_API_BASE_URL,
                'key': config.RAG_OPENAI_API_KEY,
            },
            'ollama_config': {
                'url': config.RAG_OLLAMA_BASE_URL,
                'key': config.RAG_OLLAMA_API_KEY,
            },
            'azure_openai_config': {
                'url': config.RAG_AZURE_OPENAI_BASE_URL,
                'key': config.RAG_AZURE_OPENAI_API_KEY,
                'version': config.RAG_AZURE_OPENAI_API_VERSION,
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
    config = await get_retrieval_config()
    await config.save()
    return {
        'status': True,
        # RAG settings
        'RAG_TEMPLATE': config.RAG_TEMPLATE,
        'TOP_K': config.TOP_K,
        'BYPASS_EMBEDDING_AND_RETRIEVAL': config.BYPASS_EMBEDDING_AND_RETRIEVAL,
        'RAG_FULL_CONTEXT': config.RAG_FULL_CONTEXT,
        # Hybrid search settings
        'ENABLE_RAG_HYBRID_SEARCH': config.ENABLE_RAG_HYBRID_SEARCH,
        'ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS': config.ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS,
        'TOP_K_RERANKER': config.TOP_K_RERANKER,
        'RELEVANCE_THRESHOLD': config.RELEVANCE_THRESHOLD,
        'HYBRID_BM25_WEIGHT': config.HYBRID_BM25_WEIGHT,
        # Content extraction settings
        'CONTENT_EXTRACTION_ENGINE': config.CONTENT_EXTRACTION_ENGINE,
        'PDF_EXTRACT_IMAGES': config.PDF_EXTRACT_IMAGES,
        'PDF_LOADER_MODE': config.PDF_LOADER_MODE,
        'DATALAB_MARKER_API_KEY': config.DATALAB_MARKER_API_KEY,
        'DATALAB_MARKER_API_BASE_URL': config.DATALAB_MARKER_API_BASE_URL,
        'DATALAB_MARKER_ADDITIONAL_CONFIG': config.DATALAB_MARKER_ADDITIONAL_CONFIG,
        'DATALAB_MARKER_SKIP_CACHE': config.DATALAB_MARKER_SKIP_CACHE,
        'DATALAB_MARKER_FORCE_OCR': config.DATALAB_MARKER_FORCE_OCR,
        'DATALAB_MARKER_PAGINATE': config.DATALAB_MARKER_PAGINATE,
        'DATALAB_MARKER_STRIP_EXISTING_OCR': config.DATALAB_MARKER_STRIP_EXISTING_OCR,
        'DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION': config.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION,
        'DATALAB_MARKER_FORMAT_LINES': config.DATALAB_MARKER_FORMAT_LINES,
        'DATALAB_MARKER_USE_LLM': config.DATALAB_MARKER_USE_LLM,
        'DATALAB_MARKER_OUTPUT_FORMAT': config.DATALAB_MARKER_OUTPUT_FORMAT,
        'EXTERNAL_DOCUMENT_LOADER_URL': config.EXTERNAL_DOCUMENT_LOADER_URL,
        'EXTERNAL_DOCUMENT_LOADER_API_KEY': config.EXTERNAL_DOCUMENT_LOADER_API_KEY,
        'EXTERNAL_DOCUMENT_LOADER_HEADERS': config.EXTERNAL_DOCUMENT_LOADER_HEADERS,
        'TIKA_SERVER_URL': config.TIKA_SERVER_URL,
        'DOCLING_SERVER_URL': config.DOCLING_SERVER_URL,
        'DOCLING_API_KEY': config.DOCLING_API_KEY,
        'DOCLING_PARAMS': config.DOCLING_PARAMS,
        'DOCUMENT_INTELLIGENCE_ENDPOINT': config.DOCUMENT_INTELLIGENCE_ENDPOINT,
        'DOCUMENT_INTELLIGENCE_KEY': config.DOCUMENT_INTELLIGENCE_KEY,
        'DOCUMENT_INTELLIGENCE_MODEL': config.DOCUMENT_INTELLIGENCE_MODEL,
        'MISTRAL_OCR_API_BASE_URL': config.MISTRAL_OCR_API_BASE_URL,
        'MISTRAL_OCR_API_KEY': config.MISTRAL_OCR_API_KEY,
        'MISTRAL_OCR_USE_BASE64': config.MISTRAL_OCR_USE_BASE64,
        'PADDLEOCR_VL_BASE_URL': config.PADDLEOCR_VL_BASE_URL,
        'PADDLEOCR_VL_TOKEN': config.PADDLEOCR_VL_TOKEN,
        # MinerU settings
        'MINERU_API_MODE': config.MINERU_API_MODE,
        'MINERU_API_URL': config.MINERU_API_URL,
        'MINERU_API_KEY': config.MINERU_API_KEY,
        'MINERU_API_TIMEOUT': config.MINERU_API_TIMEOUT,
        'MINERU_PARAMS': config.MINERU_PARAMS,
        'MINERU_FILE_EXTENSIONS': config.MINERU_FILE_EXTENSIONS,
        # Reranking settings
        'RAG_RERANKING_MODEL': config.RAG_RERANKING_MODEL,
        'RAG_RERANKING_ENGINE': config.RAG_RERANKING_ENGINE,
        'RAG_RERANKING_BATCH_SIZE': config.RAG_RERANKING_BATCH_SIZE,
        'RAG_EXTERNAL_RERANKER_URL': config.RAG_EXTERNAL_RERANKER_URL,
        'RAG_EXTERNAL_RERANKER_API_KEY': config.RAG_EXTERNAL_RERANKER_API_KEY,
        'RAG_EXTERNAL_RERANKER_TIMEOUT': config.RAG_EXTERNAL_RERANKER_TIMEOUT,
        # Chunking settings
        'TEXT_SPLITTER': config.TEXT_SPLITTER,
        'RAG_TOKENIZER_MODEL': config.RAG_TOKENIZER_MODEL,
        'ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER': config.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER,
        'CHUNK_SIZE': config.CHUNK_SIZE,
        'CHUNK_MIN_SIZE_TARGET': config.CHUNK_MIN_SIZE_TARGET,
        'CHUNK_OVERLAP': config.CHUNK_OVERLAP,
        # File upload settings
        'FILE_MAX_SIZE': config.FILE_MAX_SIZE,
        'FILE_MAX_COUNT': config.FILE_MAX_COUNT,
        'FILE_IMAGE_COMPRESSION_WIDTH': config.FILE_IMAGE_COMPRESSION_WIDTH,
        'FILE_IMAGE_COMPRESSION_HEIGHT': config.FILE_IMAGE_COMPRESSION_HEIGHT,
        'ALLOWED_FILE_EXTENSIONS': config.ALLOWED_FILE_EXTENSIONS,
        # Integration settings
        'ENABLE_GOOGLE_DRIVE_INTEGRATION': config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
        'ENABLE_ONEDRIVE_INTEGRATION': config.ENABLE_ONEDRIVE_INTEGRATION,
        # Web search settings
        'web': {
            'ENABLE_WEB_SEARCH': config.ENABLE_WEB_SEARCH,
            'ENABLE_WEB_SEARCH_CONFIRMATION': config.ENABLE_WEB_SEARCH_CONFIRMATION,
            'WEB_SEARCH_CONFIRMATION_CONTENT': config.WEB_SEARCH_CONFIRMATION_CONTENT,
            'WEB_SEARCH_ENGINE': config.WEB_SEARCH_ENGINE,
            'WEB_SEARCH_TRUST_ENV': config.WEB_SEARCH_TRUST_ENV,
            'WEB_SEARCH_RESULT_COUNT': config.WEB_SEARCH_RESULT_COUNT,
            'WEB_SEARCH_CONCURRENT_REQUESTS': config.WEB_SEARCH_CONCURRENT_REQUESTS,
            'WEB_FETCH_MAX_CONTENT_LENGTH': config.WEB_FETCH_MAX_CONTENT_LENGTH,
            'WEB_LOADER_CONCURRENT_REQUESTS': config.WEB_LOADER_CONCURRENT_REQUESTS,
            'WEB_SEARCH_DOMAIN_FILTER_LIST': config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            'BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL': config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL,
            'BYPASS_WEB_SEARCH_WEB_LOADER': config.BYPASS_WEB_SEARCH_WEB_LOADER,
            'OLLAMA_CLOUD_WEB_SEARCH_API_KEY': config.OLLAMA_CLOUD_WEB_SEARCH_API_KEY,
            'SEARXNG_QUERY_URL': config.SEARXNG_QUERY_URL,
            'SEARXNG_LANGUAGE': config.SEARXNG_LANGUAGE,
            'YACY_QUERY_URL': config.YACY_QUERY_URL,
            'YACY_USERNAME': config.YACY_USERNAME,
            'YACY_PASSWORD': config.YACY_PASSWORD,
            'GOOGLE_PSE_API_KEY': config.GOOGLE_PSE_API_KEY,
            'GOOGLE_PSE_ENGINE_ID': config.GOOGLE_PSE_ENGINE_ID,
            'BRAVE_SEARCH_API_KEY': config.BRAVE_SEARCH_API_KEY,
            'BRAVE_SEARCH_CONTEXT_TOKENS': config.BRAVE_SEARCH_CONTEXT_TOKENS,
            'KAGI_SEARCH_API_KEY': config.KAGI_SEARCH_API_KEY,
            'MOJEEK_SEARCH_API_KEY': config.MOJEEK_SEARCH_API_KEY,
            'BOCHA_SEARCH_API_KEY': config.BOCHA_SEARCH_API_KEY,
            'SERPSTACK_API_KEY': config.SERPSTACK_API_KEY,
            'SERPSTACK_HTTPS': config.SERPSTACK_HTTPS,
            'SERPER_API_KEY': config.SERPER_API_KEY,
            'SERPHOUSE_API_KEY': config.SERPHOUSE_API_KEY,
            'SERPHOUSE_DOMAIN': config.SERPHOUSE_DOMAIN,
            'SERPLY_API_KEY': config.SERPLY_API_KEY,
            'DDGS_BACKEND': config.DDGS_BACKEND,
            'TAVILY_API_KEY': config.TAVILY_API_KEY,
            'SEARCHAPI_API_KEY': config.SEARCHAPI_API_KEY,
            'SEARCHAPI_ENGINE': config.SEARCHAPI_ENGINE,
            'SERPAPI_API_KEY': config.SERPAPI_API_KEY,
            'SERPAPI_ENGINE': config.SERPAPI_ENGINE,
            'JINA_API_KEY': config.JINA_API_KEY,
            'JINA_API_BASE_URL': config.JINA_API_BASE_URL,
            'BING_SEARCH_V7_ENDPOINT': config.BING_SEARCH_V7_ENDPOINT,
            'BING_SEARCH_V7_SUBSCRIPTION_KEY': config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
            'EXA_API_KEY': config.EXA_API_KEY,
            'PERPLEXITY_API_KEY': config.PERPLEXITY_API_KEY,
            'PERPLEXITY_MODEL': config.PERPLEXITY_MODEL,
            'PERPLEXITY_SEARCH_CONTEXT_USAGE': config.PERPLEXITY_SEARCH_CONTEXT_USAGE,
            'PERPLEXITY_SEARCH_API_URL': config.PERPLEXITY_SEARCH_API_URL,
            'MICROSOFT_WEB_IQ_API_BASE_URL': config.MICROSOFT_WEB_IQ_API_BASE_URL,
            'MICROSOFT_WEB_IQ_API_KEY': config.MICROSOFT_WEB_IQ_API_KEY,
            'MICROSOFT_WEB_IQ_LANGUAGE': config.MICROSOFT_WEB_IQ_LANGUAGE,
            'SOUGOU_API_SID': config.SOUGOU_API_SID,
            'SOUGOU_API_SK': config.SOUGOU_API_SK,
            'WEB_LOADER_ENGINE': config.WEB_LOADER_ENGINE,
            'WEB_LOADER_TIMEOUT': config.WEB_LOADER_TIMEOUT,
            'ENABLE_WEB_LOADER_SSL_VERIFICATION': config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
            'PLAYWRIGHT_WS_URL': config.PLAYWRIGHT_WS_URL,
            'PLAYWRIGHT_TIMEOUT': config.PLAYWRIGHT_TIMEOUT,
            'FIRECRAWL_API_KEY': config.FIRECRAWL_API_KEY,
            'FIRECRAWL_API_BASE_URL': config.FIRECRAWL_API_BASE_URL,
            'FIRECRAWL_TIMEOUT': config.FIRECRAWL_TIMEOUT,
            'TAVILY_EXTRACT_DEPTH': config.TAVILY_EXTRACT_DEPTH,
            'EXTERNAL_WEB_SEARCH_URL': config.EXTERNAL_WEB_SEARCH_URL,
            'EXTERNAL_WEB_SEARCH_API_KEY': config.EXTERNAL_WEB_SEARCH_API_KEY,
            'EXTERNAL_WEB_LOADER_URL': config.EXTERNAL_WEB_LOADER_URL,
            'EXTERNAL_WEB_LOADER_API_KEY': config.EXTERNAL_WEB_LOADER_API_KEY,
            'YOUTUBE_LOADER_LANGUAGE': config.YOUTUBE_LOADER_LANGUAGE,
            'YOUTUBE_LOADER_PROXY_URL': config.YOUTUBE_LOADER_PROXY_URL,
            'YOUTUBE_LOADER_TRANSLATION': request.app.state.YOUTUBE_LOADER_TRANSLATION,
            'YANDEX_WEB_SEARCH_URL': config.YANDEX_WEB_SEARCH_URL,
            'YANDEX_WEB_SEARCH_API_KEY': config.YANDEX_WEB_SEARCH_API_KEY,
            'YANDEX_WEB_SEARCH_CONFIG': config.YANDEX_WEB_SEARCH_CONFIG,
            'YOUCOM_API_KEY': config.YOUCOM_API_KEY,
            'LINKUP_API_KEY': config.LINKUP_API_KEY,
            'LINKUP_SEARCH_PARAMS': config.LINKUP_SEARCH_PARAMS,
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
    WEB_SEARCH_DOMAIN_FILTER_LIST: list[str | None] = []
    WEB_FETCH_MAX_CONTENT_LENGTH: int | None = None
    WEB_LOADER_CONCURRENT_REQUESTS: int | None = None
    BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL: bool | None = None
    BYPASS_WEB_SEARCH_WEB_LOADER: bool | None = None
    OLLAMA_CLOUD_WEB_SEARCH_API_KEY: str | None = None
    SEARXNG_QUERY_URL: str | None = None
    SEARXNG_LANGUAGE: str | None = None
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
    SEARCHAPI_API_KEY: str | None = None
    SEARCHAPI_ENGINE: str | None = None
    SERPAPI_API_KEY: str | None = None
    SERPAPI_ENGINE: str | None = None
    JINA_API_KEY: str | None = None
    JINA_API_BASE_URL: str | None = None
    BING_SEARCH_V7_ENDPOINT: str | None = None
    BING_SEARCH_V7_SUBSCRIPTION_KEY: str | None = None
    EXA_API_KEY: str | None = None
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
    EXTERNAL_WEB_SEARCH_URL: str | None = None
    EXTERNAL_WEB_SEARCH_API_KEY: str | None = None
    EXTERNAL_WEB_LOADER_URL: str | None = None
    EXTERNAL_WEB_LOADER_API_KEY: str | None = None
    YOUTUBE_LOADER_LANGUAGE: list[str | None] = None
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
    ALLOWED_FILE_EXTENSIONS: list[str | None] = None

    # Integration settings
    ENABLE_GOOGLE_DRIVE_INTEGRATION: bool | None = None
    ENABLE_ONEDRIVE_INTEGRATION: bool | None = None

    # Web search settings
    web: WebConfig | None = None


@router.post('/config/update')
async def update_rag_config(request: Request, form_data: ConfigForm, user=Depends(get_admin_user)):
    # RAG settings
    config = await get_retrieval_config()
    config.RAG_TEMPLATE = form_data.RAG_TEMPLATE if form_data.RAG_TEMPLATE is not None else config.RAG_TEMPLATE
    config.TOP_K = form_data.TOP_K if form_data.TOP_K is not None else config.TOP_K
    config.BYPASS_EMBEDDING_AND_RETRIEVAL = (
        form_data.BYPASS_EMBEDDING_AND_RETRIEVAL
        if form_data.BYPASS_EMBEDDING_AND_RETRIEVAL is not None
        else config.BYPASS_EMBEDDING_AND_RETRIEVAL
    )
    config.RAG_FULL_CONTEXT = (
        form_data.RAG_FULL_CONTEXT if form_data.RAG_FULL_CONTEXT is not None else config.RAG_FULL_CONTEXT
    )

    # Hybrid search settings
    config.ENABLE_RAG_HYBRID_SEARCH = (
        form_data.ENABLE_RAG_HYBRID_SEARCH
        if form_data.ENABLE_RAG_HYBRID_SEARCH is not None
        else config.ENABLE_RAG_HYBRID_SEARCH
    )
    config.ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS = (
        form_data.ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS
        if form_data.ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS is not None
        else config.ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS
    )

    config.TOP_K_RERANKER = form_data.TOP_K_RERANKER if form_data.TOP_K_RERANKER is not None else config.TOP_K_RERANKER
    config.RELEVANCE_THRESHOLD = (
        form_data.RELEVANCE_THRESHOLD if form_data.RELEVANCE_THRESHOLD is not None else config.RELEVANCE_THRESHOLD
    )
    config.HYBRID_BM25_WEIGHT = (
        form_data.HYBRID_BM25_WEIGHT if form_data.HYBRID_BM25_WEIGHT is not None else config.HYBRID_BM25_WEIGHT
    )

    # Content extraction settings
    config.CONTENT_EXTRACTION_ENGINE = (
        form_data.CONTENT_EXTRACTION_ENGINE
        if form_data.CONTENT_EXTRACTION_ENGINE is not None
        else config.CONTENT_EXTRACTION_ENGINE
    )
    config.PDF_EXTRACT_IMAGES = (
        form_data.PDF_EXTRACT_IMAGES if form_data.PDF_EXTRACT_IMAGES is not None else config.PDF_EXTRACT_IMAGES
    )
    config.PDF_LOADER_MODE = (
        form_data.PDF_LOADER_MODE if form_data.PDF_LOADER_MODE is not None else config.PDF_LOADER_MODE
    )
    config.DATALAB_MARKER_API_KEY = (
        form_data.DATALAB_MARKER_API_KEY
        if form_data.DATALAB_MARKER_API_KEY is not None
        else config.DATALAB_MARKER_API_KEY
    )
    config.DATALAB_MARKER_API_BASE_URL = (
        form_data.DATALAB_MARKER_API_BASE_URL
        if form_data.DATALAB_MARKER_API_BASE_URL is not None
        else config.DATALAB_MARKER_API_BASE_URL
    )
    config.DATALAB_MARKER_ADDITIONAL_CONFIG = (
        form_data.DATALAB_MARKER_ADDITIONAL_CONFIG
        if form_data.DATALAB_MARKER_ADDITIONAL_CONFIG is not None
        else config.DATALAB_MARKER_ADDITIONAL_CONFIG
    )
    config.DATALAB_MARKER_SKIP_CACHE = (
        form_data.DATALAB_MARKER_SKIP_CACHE
        if form_data.DATALAB_MARKER_SKIP_CACHE is not None
        else config.DATALAB_MARKER_SKIP_CACHE
    )
    config.DATALAB_MARKER_FORCE_OCR = (
        form_data.DATALAB_MARKER_FORCE_OCR
        if form_data.DATALAB_MARKER_FORCE_OCR is not None
        else config.DATALAB_MARKER_FORCE_OCR
    )
    config.DATALAB_MARKER_PAGINATE = (
        form_data.DATALAB_MARKER_PAGINATE
        if form_data.DATALAB_MARKER_PAGINATE is not None
        else config.DATALAB_MARKER_PAGINATE
    )
    config.DATALAB_MARKER_STRIP_EXISTING_OCR = (
        form_data.DATALAB_MARKER_STRIP_EXISTING_OCR
        if form_data.DATALAB_MARKER_STRIP_EXISTING_OCR is not None
        else config.DATALAB_MARKER_STRIP_EXISTING_OCR
    )
    config.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION = (
        form_data.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION
        if form_data.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION is not None
        else config.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION
    )
    config.DATALAB_MARKER_FORMAT_LINES = (
        form_data.DATALAB_MARKER_FORMAT_LINES
        if form_data.DATALAB_MARKER_FORMAT_LINES is not None
        else config.DATALAB_MARKER_FORMAT_LINES
    )
    config.DATALAB_MARKER_OUTPUT_FORMAT = (
        form_data.DATALAB_MARKER_OUTPUT_FORMAT
        if form_data.DATALAB_MARKER_OUTPUT_FORMAT is not None
        else config.DATALAB_MARKER_OUTPUT_FORMAT
    )
    config.DATALAB_MARKER_USE_LLM = (
        form_data.DATALAB_MARKER_USE_LLM
        if form_data.DATALAB_MARKER_USE_LLM is not None
        else config.DATALAB_MARKER_USE_LLM
    )
    config.EXTERNAL_DOCUMENT_LOADER_URL = (
        form_data.EXTERNAL_DOCUMENT_LOADER_URL
        if form_data.EXTERNAL_DOCUMENT_LOADER_URL is not None
        else config.EXTERNAL_DOCUMENT_LOADER_URL
    )
    config.EXTERNAL_DOCUMENT_LOADER_API_KEY = (
        form_data.EXTERNAL_DOCUMENT_LOADER_API_KEY
        if form_data.EXTERNAL_DOCUMENT_LOADER_API_KEY is not None
        else config.EXTERNAL_DOCUMENT_LOADER_API_KEY
    )
    config.EXTERNAL_DOCUMENT_LOADER_HEADERS = (
        form_data.EXTERNAL_DOCUMENT_LOADER_HEADERS
        if form_data.EXTERNAL_DOCUMENT_LOADER_HEADERS is not None
        else config.EXTERNAL_DOCUMENT_LOADER_HEADERS
    )
    config.TIKA_SERVER_URL = (
        form_data.TIKA_SERVER_URL if form_data.TIKA_SERVER_URL is not None else config.TIKA_SERVER_URL
    )
    config.DOCLING_SERVER_URL = (
        form_data.DOCLING_SERVER_URL if form_data.DOCLING_SERVER_URL is not None else config.DOCLING_SERVER_URL
    )
    config.DOCLING_API_KEY = (
        form_data.DOCLING_API_KEY if form_data.DOCLING_API_KEY is not None else config.DOCLING_API_KEY
    )
    config.DOCLING_PARAMS = form_data.DOCLING_PARAMS if form_data.DOCLING_PARAMS is not None else config.DOCLING_PARAMS
    config.DOCUMENT_INTELLIGENCE_ENDPOINT = (
        form_data.DOCUMENT_INTELLIGENCE_ENDPOINT
        if form_data.DOCUMENT_INTELLIGENCE_ENDPOINT is not None
        else config.DOCUMENT_INTELLIGENCE_ENDPOINT
    )
    config.DOCUMENT_INTELLIGENCE_KEY = (
        form_data.DOCUMENT_INTELLIGENCE_KEY
        if form_data.DOCUMENT_INTELLIGENCE_KEY is not None
        else config.DOCUMENT_INTELLIGENCE_KEY
    )
    config.DOCUMENT_INTELLIGENCE_MODEL = (
        form_data.DOCUMENT_INTELLIGENCE_MODEL
        if form_data.DOCUMENT_INTELLIGENCE_MODEL is not None
        else config.DOCUMENT_INTELLIGENCE_MODEL
    )

    config.MISTRAL_OCR_API_BASE_URL = (
        form_data.MISTRAL_OCR_API_BASE_URL
        if form_data.MISTRAL_OCR_API_BASE_URL is not None
        else config.MISTRAL_OCR_API_BASE_URL
    )
    config.MISTRAL_OCR_API_KEY = (
        form_data.MISTRAL_OCR_API_KEY if form_data.MISTRAL_OCR_API_KEY is not None else config.MISTRAL_OCR_API_KEY
    )
    config.MISTRAL_OCR_USE_BASE64 = (
        form_data.MISTRAL_OCR_USE_BASE64
        if form_data.MISTRAL_OCR_USE_BASE64 is not None
        else config.MISTRAL_OCR_USE_BASE64
    )
    config.PADDLEOCR_VL_BASE_URL = (
        form_data.PADDLEOCR_VL_BASE_URL if form_data.PADDLEOCR_VL_BASE_URL is not None else config.PADDLEOCR_VL_BASE_URL
    )
    config.PADDLEOCR_VL_TOKEN = (
        form_data.PADDLEOCR_VL_TOKEN if form_data.PADDLEOCR_VL_TOKEN is not None else config.PADDLEOCR_VL_TOKEN
    )

    # MinerU settings
    config.MINERU_API_MODE = (
        form_data.MINERU_API_MODE if form_data.MINERU_API_MODE is not None else config.MINERU_API_MODE
    )
    config.MINERU_API_URL = form_data.MINERU_API_URL if form_data.MINERU_API_URL is not None else config.MINERU_API_URL
    config.MINERU_API_KEY = form_data.MINERU_API_KEY if form_data.MINERU_API_KEY is not None else config.MINERU_API_KEY
    config.MINERU_API_TIMEOUT = (
        form_data.MINERU_API_TIMEOUT if form_data.MINERU_API_TIMEOUT is not None else config.MINERU_API_TIMEOUT
    )
    config.MINERU_PARAMS = form_data.MINERU_PARAMS if form_data.MINERU_PARAMS is not None else config.MINERU_PARAMS
    config.MINERU_FILE_EXTENSIONS = (
        form_data.MINERU_FILE_EXTENSIONS
        if form_data.MINERU_FILE_EXTENSIONS is not None
        else config.MINERU_FILE_EXTENSIONS
    )

    # Reranking settings
    if config.RAG_RERANKING_ENGINE == '':
        # Unloading the internal reranker and clear VRAM memory
        request.app.state.rf = None
        request.app.state.RERANKING_FUNCTION = None
        import gc

        gc.collect()
        if DEVICE_TYPE == 'cuda':
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    config.RAG_RERANKING_ENGINE = (
        form_data.RAG_RERANKING_ENGINE if form_data.RAG_RERANKING_ENGINE is not None else config.RAG_RERANKING_ENGINE
    )

    config.RAG_EXTERNAL_RERANKER_URL = (
        form_data.RAG_EXTERNAL_RERANKER_URL
        if form_data.RAG_EXTERNAL_RERANKER_URL is not None
        else config.RAG_EXTERNAL_RERANKER_URL
    )

    config.RAG_EXTERNAL_RERANKER_API_KEY = (
        form_data.RAG_EXTERNAL_RERANKER_API_KEY
        if form_data.RAG_EXTERNAL_RERANKER_API_KEY is not None
        else config.RAG_EXTERNAL_RERANKER_API_KEY
    )

    config.RAG_EXTERNAL_RERANKER_TIMEOUT = (
        form_data.RAG_EXTERNAL_RERANKER_TIMEOUT
        if form_data.RAG_EXTERNAL_RERANKER_TIMEOUT is not None
        else config.RAG_EXTERNAL_RERANKER_TIMEOUT
    )

    config.RAG_RERANKING_BATCH_SIZE = (
        form_data.RAG_RERANKING_BATCH_SIZE
        if form_data.RAG_RERANKING_BATCH_SIZE is not None
        else config.RAG_RERANKING_BATCH_SIZE
    )

    log.info(f'Updating reranking model: {config.RAG_RERANKING_MODEL} to {form_data.RAG_RERANKING_MODEL}')
    try:
        config.RAG_RERANKING_MODEL = (
            form_data.RAG_RERANKING_MODEL if form_data.RAG_RERANKING_MODEL is not None else config.RAG_RERANKING_MODEL
        )

        try:
            if config.ENABLE_RAG_HYBRID_SEARCH and not config.BYPASS_EMBEDDING_AND_RETRIEVAL:
                request.app.state.rf = get_rf(
                    config.RAG_RERANKING_ENGINE,
                    config.RAG_RERANKING_MODEL,
                    config.RAG_EXTERNAL_RERANKER_URL,
                    config.RAG_EXTERNAL_RERANKER_API_KEY,
                    config.RAG_EXTERNAL_RERANKER_TIMEOUT,
                )

                request.app.state.RERANKING_FUNCTION = get_reranking_function(
                    config.RAG_RERANKING_ENGINE,
                    config.RAG_RERANKING_MODEL,
                    request.app.state.rf,
                    reranking_batch_size=config.RAG_RERANKING_BATCH_SIZE,
                )
        except Exception as e:
            log.error(f'Error loading reranking model: {e}')
            config.ENABLE_RAG_HYBRID_SEARCH = False
    except Exception as e:
        log.exception(f'Problem updating reranking model: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error updating reranking configuration'),
        )

    # Chunking settings
    config.TEXT_SPLITTER = form_data.TEXT_SPLITTER if form_data.TEXT_SPLITTER is not None else config.TEXT_SPLITTER
    config.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER = (
        form_data.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER
        if form_data.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER is not None
        else config.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER
    )
    config.CHUNK_SIZE = form_data.CHUNK_SIZE if form_data.CHUNK_SIZE is not None else config.CHUNK_SIZE
    config.CHUNK_MIN_SIZE_TARGET = (
        form_data.CHUNK_MIN_SIZE_TARGET if form_data.CHUNK_MIN_SIZE_TARGET is not None else config.CHUNK_MIN_SIZE_TARGET
    )
    config.CHUNK_OVERLAP = form_data.CHUNK_OVERLAP if form_data.CHUNK_OVERLAP is not None else config.CHUNK_OVERLAP
    config.RAG_TOKENIZER_MODEL = (
        form_data.RAG_TOKENIZER_MODEL.strip()
        if form_data.RAG_TOKENIZER_MODEL is not None
        else config.RAG_TOKENIZER_MODEL
    )

    # File upload settings
    # Empty string means "clear to None" (unlimited/no compression),
    # None means "don't change", int means "set to this value"
    if form_data.FILE_MAX_SIZE is not None:
        config.FILE_MAX_SIZE = None if form_data.FILE_MAX_SIZE == '' else form_data.FILE_MAX_SIZE
    if form_data.FILE_MAX_COUNT is not None:
        config.FILE_MAX_COUNT = None if form_data.FILE_MAX_COUNT == '' else form_data.FILE_MAX_COUNT
    if form_data.FILE_IMAGE_COMPRESSION_WIDTH is not None:
        config.FILE_IMAGE_COMPRESSION_WIDTH = (
            None if form_data.FILE_IMAGE_COMPRESSION_WIDTH == '' else form_data.FILE_IMAGE_COMPRESSION_WIDTH
        )
    if form_data.FILE_IMAGE_COMPRESSION_HEIGHT is not None:
        config.FILE_IMAGE_COMPRESSION_HEIGHT = (
            None if form_data.FILE_IMAGE_COMPRESSION_HEIGHT == '' else form_data.FILE_IMAGE_COMPRESSION_HEIGHT
        )

    config.ALLOWED_FILE_EXTENSIONS = (
        form_data.ALLOWED_FILE_EXTENSIONS
        if form_data.ALLOWED_FILE_EXTENSIONS is not None
        else config.ALLOWED_FILE_EXTENSIONS
    )

    # Integration settings
    config.ENABLE_GOOGLE_DRIVE_INTEGRATION = (
        form_data.ENABLE_GOOGLE_DRIVE_INTEGRATION
        if form_data.ENABLE_GOOGLE_DRIVE_INTEGRATION is not None
        else config.ENABLE_GOOGLE_DRIVE_INTEGRATION
    )
    config.ENABLE_ONEDRIVE_INTEGRATION = (
        form_data.ENABLE_ONEDRIVE_INTEGRATION
        if form_data.ENABLE_ONEDRIVE_INTEGRATION is not None
        else config.ENABLE_ONEDRIVE_INTEGRATION
    )

    if form_data.web is not None:
        # Web search settings
        config.ENABLE_WEB_SEARCH = form_data.web.ENABLE_WEB_SEARCH
        config.ENABLE_WEB_SEARCH_CONFIRMATION = form_data.web.ENABLE_WEB_SEARCH_CONFIRMATION
        config.WEB_SEARCH_CONFIRMATION_CONTENT = form_data.web.WEB_SEARCH_CONFIRMATION_CONTENT
        config.WEB_SEARCH_ENGINE = form_data.web.WEB_SEARCH_ENGINE
        config.WEB_SEARCH_TRUST_ENV = form_data.web.WEB_SEARCH_TRUST_ENV
        config.WEB_SEARCH_RESULT_COUNT = form_data.web.WEB_SEARCH_RESULT_COUNT
        config.WEB_SEARCH_CONCURRENT_REQUESTS = form_data.web.WEB_SEARCH_CONCURRENT_REQUESTS
        config.WEB_FETCH_MAX_CONTENT_LENGTH = form_data.web.WEB_FETCH_MAX_CONTENT_LENGTH
        config.WEB_LOADER_CONCURRENT_REQUESTS = form_data.web.WEB_LOADER_CONCURRENT_REQUESTS
        config.WEB_SEARCH_DOMAIN_FILTER_LIST = form_data.web.WEB_SEARCH_DOMAIN_FILTER_LIST
        config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL = form_data.web.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL
        config.BYPASS_WEB_SEARCH_WEB_LOADER = form_data.web.BYPASS_WEB_SEARCH_WEB_LOADER
        config.OLLAMA_CLOUD_WEB_SEARCH_API_KEY = form_data.web.OLLAMA_CLOUD_WEB_SEARCH_API_KEY
        config.SEARXNG_QUERY_URL = form_data.web.SEARXNG_QUERY_URL
        config.SEARXNG_LANGUAGE = form_data.web.SEARXNG_LANGUAGE
        config.YACY_QUERY_URL = form_data.web.YACY_QUERY_URL
        config.YACY_USERNAME = form_data.web.YACY_USERNAME
        config.YACY_PASSWORD = form_data.web.YACY_PASSWORD
        config.GOOGLE_PSE_API_KEY = form_data.web.GOOGLE_PSE_API_KEY
        config.GOOGLE_PSE_ENGINE_ID = form_data.web.GOOGLE_PSE_ENGINE_ID
        config.BRAVE_SEARCH_API_KEY = form_data.web.BRAVE_SEARCH_API_KEY
        if form_data.web.BRAVE_SEARCH_CONTEXT_TOKENS is not None:
            config.BRAVE_SEARCH_CONTEXT_TOKENS = form_data.web.BRAVE_SEARCH_CONTEXT_TOKENS
        config.KAGI_SEARCH_API_KEY = form_data.web.KAGI_SEARCH_API_KEY
        config.MOJEEK_SEARCH_API_KEY = form_data.web.MOJEEK_SEARCH_API_KEY
        config.BOCHA_SEARCH_API_KEY = form_data.web.BOCHA_SEARCH_API_KEY
        config.SERPSTACK_API_KEY = form_data.web.SERPSTACK_API_KEY
        config.SERPSTACK_HTTPS = form_data.web.SERPSTACK_HTTPS
        config.SERPER_API_KEY = form_data.web.SERPER_API_KEY
        config.SERPHOUSE_API_KEY = form_data.web.SERPHOUSE_API_KEY
        config.SERPHOUSE_DOMAIN = form_data.web.SERPHOUSE_DOMAIN
        config.SERPLY_API_KEY = form_data.web.SERPLY_API_KEY
        config.DDGS_BACKEND = form_data.web.DDGS_BACKEND
        config.TAVILY_API_KEY = form_data.web.TAVILY_API_KEY
        config.SEARCHAPI_API_KEY = form_data.web.SEARCHAPI_API_KEY
        config.SEARCHAPI_ENGINE = form_data.web.SEARCHAPI_ENGINE
        config.SERPAPI_API_KEY = form_data.web.SERPAPI_API_KEY
        config.SERPAPI_ENGINE = form_data.web.SERPAPI_ENGINE
        config.JINA_API_KEY = form_data.web.JINA_API_KEY
        config.JINA_API_BASE_URL = form_data.web.JINA_API_BASE_URL
        config.BING_SEARCH_V7_ENDPOINT = form_data.web.BING_SEARCH_V7_ENDPOINT
        config.BING_SEARCH_V7_SUBSCRIPTION_KEY = form_data.web.BING_SEARCH_V7_SUBSCRIPTION_KEY
        config.EXA_API_KEY = form_data.web.EXA_API_KEY
        config.PERPLEXITY_API_KEY = form_data.web.PERPLEXITY_API_KEY
        config.PERPLEXITY_MODEL = form_data.web.PERPLEXITY_MODEL
        config.PERPLEXITY_SEARCH_CONTEXT_USAGE = form_data.web.PERPLEXITY_SEARCH_CONTEXT_USAGE
        config.PERPLEXITY_SEARCH_API_URL = form_data.web.PERPLEXITY_SEARCH_API_URL
        config.MICROSOFT_WEB_IQ_API_BASE_URL = form_data.web.MICROSOFT_WEB_IQ_API_BASE_URL
        config.MICROSOFT_WEB_IQ_API_KEY = form_data.web.MICROSOFT_WEB_IQ_API_KEY
        config.MICROSOFT_WEB_IQ_LANGUAGE = form_data.web.MICROSOFT_WEB_IQ_LANGUAGE
        config.SOUGOU_API_SID = form_data.web.SOUGOU_API_SID
        config.SOUGOU_API_SK = form_data.web.SOUGOU_API_SK

        # Web loader settings
        config.WEB_LOADER_ENGINE = form_data.web.WEB_LOADER_ENGINE
        config.WEB_LOADER_TIMEOUT = form_data.web.WEB_LOADER_TIMEOUT

        config.ENABLE_WEB_LOADER_SSL_VERIFICATION = form_data.web.ENABLE_WEB_LOADER_SSL_VERIFICATION
        config.PLAYWRIGHT_WS_URL = form_data.web.PLAYWRIGHT_WS_URL
        config.PLAYWRIGHT_TIMEOUT = form_data.web.PLAYWRIGHT_TIMEOUT
        config.FIRECRAWL_API_KEY = form_data.web.FIRECRAWL_API_KEY
        config.FIRECRAWL_API_BASE_URL = form_data.web.FIRECRAWL_API_BASE_URL
        config.FIRECRAWL_TIMEOUT = form_data.web.FIRECRAWL_TIMEOUT
        config.EXTERNAL_WEB_SEARCH_URL = form_data.web.EXTERNAL_WEB_SEARCH_URL
        config.EXTERNAL_WEB_SEARCH_API_KEY = form_data.web.EXTERNAL_WEB_SEARCH_API_KEY
        config.EXTERNAL_WEB_LOADER_URL = form_data.web.EXTERNAL_WEB_LOADER_URL
        config.EXTERNAL_WEB_LOADER_API_KEY = form_data.web.EXTERNAL_WEB_LOADER_API_KEY
        config.TAVILY_EXTRACT_DEPTH = form_data.web.TAVILY_EXTRACT_DEPTH
        config.YOUTUBE_LOADER_LANGUAGE = form_data.web.YOUTUBE_LOADER_LANGUAGE
        config.YOUTUBE_LOADER_PROXY_URL = form_data.web.YOUTUBE_LOADER_PROXY_URL
        request.app.state.YOUTUBE_LOADER_TRANSLATION = form_data.web.YOUTUBE_LOADER_TRANSLATION
        config.YANDEX_WEB_SEARCH_URL = form_data.web.YANDEX_WEB_SEARCH_URL
        config.YANDEX_WEB_SEARCH_API_KEY = form_data.web.YANDEX_WEB_SEARCH_API_KEY
        config.YANDEX_WEB_SEARCH_CONFIG = form_data.web.YANDEX_WEB_SEARCH_CONFIG
        config.YOUCOM_API_KEY = form_data.web.YOUCOM_API_KEY
        config.LINKUP_API_KEY = form_data.web.LINKUP_API_KEY
        config.LINKUP_SEARCH_PARAMS = form_data.web.LINKUP_SEARCH_PARAMS

    await config.save()

    return {
        'status': True,
        # RAG settings
        'RAG_TEMPLATE': config.RAG_TEMPLATE,
        'TOP_K': config.TOP_K,
        'BYPASS_EMBEDDING_AND_RETRIEVAL': config.BYPASS_EMBEDDING_AND_RETRIEVAL,
        'RAG_FULL_CONTEXT': config.RAG_FULL_CONTEXT,
        # Hybrid search settings
        'ENABLE_RAG_HYBRID_SEARCH': config.ENABLE_RAG_HYBRID_SEARCH,
        'TOP_K_RERANKER': config.TOP_K_RERANKER,
        'RELEVANCE_THRESHOLD': config.RELEVANCE_THRESHOLD,
        'HYBRID_BM25_WEIGHT': config.HYBRID_BM25_WEIGHT,
        # Content extraction settings
        'CONTENT_EXTRACTION_ENGINE': config.CONTENT_EXTRACTION_ENGINE,
        'PDF_EXTRACT_IMAGES': config.PDF_EXTRACT_IMAGES,
        'PDF_LOADER_MODE': config.PDF_LOADER_MODE,
        'DATALAB_MARKER_API_KEY': config.DATALAB_MARKER_API_KEY,
        'DATALAB_MARKER_API_BASE_URL': config.DATALAB_MARKER_API_BASE_URL,
        'DATALAB_MARKER_ADDITIONAL_CONFIG': config.DATALAB_MARKER_ADDITIONAL_CONFIG,
        'DATALAB_MARKER_SKIP_CACHE': config.DATALAB_MARKER_SKIP_CACHE,
        'DATALAB_MARKER_FORCE_OCR': config.DATALAB_MARKER_FORCE_OCR,
        'DATALAB_MARKER_PAGINATE': config.DATALAB_MARKER_PAGINATE,
        'DATALAB_MARKER_STRIP_EXISTING_OCR': config.DATALAB_MARKER_STRIP_EXISTING_OCR,
        'DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION': config.DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION,
        'DATALAB_MARKER_USE_LLM': config.DATALAB_MARKER_USE_LLM,
        'DATALAB_MARKER_OUTPUT_FORMAT': config.DATALAB_MARKER_OUTPUT_FORMAT,
        'EXTERNAL_DOCUMENT_LOADER_URL': config.EXTERNAL_DOCUMENT_LOADER_URL,
        'EXTERNAL_DOCUMENT_LOADER_API_KEY': config.EXTERNAL_DOCUMENT_LOADER_API_KEY,
        'EXTERNAL_DOCUMENT_LOADER_HEADERS': config.EXTERNAL_DOCUMENT_LOADER_HEADERS,
        'TIKA_SERVER_URL': config.TIKA_SERVER_URL,
        'DOCLING_SERVER_URL': config.DOCLING_SERVER_URL,
        'DOCLING_API_KEY': config.DOCLING_API_KEY,
        'DOCLING_PARAMS': config.DOCLING_PARAMS,
        'DOCUMENT_INTELLIGENCE_ENDPOINT': config.DOCUMENT_INTELLIGENCE_ENDPOINT,
        'DOCUMENT_INTELLIGENCE_KEY': config.DOCUMENT_INTELLIGENCE_KEY,
        'DOCUMENT_INTELLIGENCE_MODEL': config.DOCUMENT_INTELLIGENCE_MODEL,
        'MISTRAL_OCR_API_BASE_URL': config.MISTRAL_OCR_API_BASE_URL,
        'MISTRAL_OCR_API_KEY': config.MISTRAL_OCR_API_KEY,
        'MISTRAL_OCR_USE_BASE64': config.MISTRAL_OCR_USE_BASE64,
        'PADDLEOCR_VL_BASE_URL': config.PADDLEOCR_VL_BASE_URL,
        'PADDLEOCR_VL_TOKEN': config.PADDLEOCR_VL_TOKEN,
        # MinerU settings
        'MINERU_API_MODE': config.MINERU_API_MODE,
        'MINERU_API_URL': config.MINERU_API_URL,
        'MINERU_API_KEY': config.MINERU_API_KEY,
        'MINERU_API_TIMEOUT': config.MINERU_API_TIMEOUT,
        'MINERU_PARAMS': config.MINERU_PARAMS,
        # Reranking settings
        'RAG_RERANKING_MODEL': config.RAG_RERANKING_MODEL,
        'RAG_RERANKING_ENGINE': config.RAG_RERANKING_ENGINE,
        'RAG_EXTERNAL_RERANKER_URL': config.RAG_EXTERNAL_RERANKER_URL,
        'RAG_EXTERNAL_RERANKER_API_KEY': config.RAG_EXTERNAL_RERANKER_API_KEY,
        'RAG_EXTERNAL_RERANKER_TIMEOUT': config.RAG_EXTERNAL_RERANKER_TIMEOUT,
        # Chunking settings
        'TEXT_SPLITTER': config.TEXT_SPLITTER,
        'RAG_TOKENIZER_MODEL': config.RAG_TOKENIZER_MODEL,
        'CHUNK_SIZE': config.CHUNK_SIZE,
        'CHUNK_MIN_SIZE_TARGET': config.CHUNK_MIN_SIZE_TARGET,
        'ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER': config.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER,
        'CHUNK_OVERLAP': config.CHUNK_OVERLAP,
        # File upload settings
        'FILE_MAX_SIZE': config.FILE_MAX_SIZE,
        'FILE_MAX_COUNT': config.FILE_MAX_COUNT,
        'FILE_IMAGE_COMPRESSION_WIDTH': config.FILE_IMAGE_COMPRESSION_WIDTH,
        'FILE_IMAGE_COMPRESSION_HEIGHT': config.FILE_IMAGE_COMPRESSION_HEIGHT,
        'ALLOWED_FILE_EXTENSIONS': config.ALLOWED_FILE_EXTENSIONS,
        # Integration settings
        'ENABLE_GOOGLE_DRIVE_INTEGRATION': config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
        'ENABLE_ONEDRIVE_INTEGRATION': config.ENABLE_ONEDRIVE_INTEGRATION,
        # Web search settings
        'web': {
            'ENABLE_WEB_SEARCH': config.ENABLE_WEB_SEARCH,
            'ENABLE_WEB_SEARCH_CONFIRMATION': config.ENABLE_WEB_SEARCH_CONFIRMATION,
            'WEB_SEARCH_CONFIRMATION_CONTENT': config.WEB_SEARCH_CONFIRMATION_CONTENT,
            'WEB_SEARCH_ENGINE': config.WEB_SEARCH_ENGINE,
            'WEB_SEARCH_TRUST_ENV': config.WEB_SEARCH_TRUST_ENV,
            'WEB_SEARCH_RESULT_COUNT': config.WEB_SEARCH_RESULT_COUNT,
            'WEB_SEARCH_CONCURRENT_REQUESTS': config.WEB_SEARCH_CONCURRENT_REQUESTS,
            'WEB_FETCH_MAX_CONTENT_LENGTH': config.WEB_FETCH_MAX_CONTENT_LENGTH,
            'WEB_LOADER_CONCURRENT_REQUESTS': config.WEB_LOADER_CONCURRENT_REQUESTS,
            'WEB_SEARCH_DOMAIN_FILTER_LIST': config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            'BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL': config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL,
            'BYPASS_WEB_SEARCH_WEB_LOADER': config.BYPASS_WEB_SEARCH_WEB_LOADER,
            'OLLAMA_CLOUD_WEB_SEARCH_API_KEY': config.OLLAMA_CLOUD_WEB_SEARCH_API_KEY,
            'SEARXNG_QUERY_URL': config.SEARXNG_QUERY_URL,
            'SEARXNG_LANGUAGE': config.SEARXNG_LANGUAGE,
            'YACY_QUERY_URL': config.YACY_QUERY_URL,
            'YACY_USERNAME': config.YACY_USERNAME,
            'YACY_PASSWORD': config.YACY_PASSWORD,
            'GOOGLE_PSE_API_KEY': config.GOOGLE_PSE_API_KEY,
            'GOOGLE_PSE_ENGINE_ID': config.GOOGLE_PSE_ENGINE_ID,
            'BRAVE_SEARCH_API_KEY': config.BRAVE_SEARCH_API_KEY,
            'BRAVE_SEARCH_CONTEXT_TOKENS': config.BRAVE_SEARCH_CONTEXT_TOKENS,
            'KAGI_SEARCH_API_KEY': config.KAGI_SEARCH_API_KEY,
            'MOJEEK_SEARCH_API_KEY': config.MOJEEK_SEARCH_API_KEY,
            'BOCHA_SEARCH_API_KEY': config.BOCHA_SEARCH_API_KEY,
            'SERPSTACK_API_KEY': config.SERPSTACK_API_KEY,
            'SERPSTACK_HTTPS': config.SERPSTACK_HTTPS,
            'SERPER_API_KEY': config.SERPER_API_KEY,
            'SERPHOUSE_API_KEY': config.SERPHOUSE_API_KEY,
            'SERPHOUSE_DOMAIN': config.SERPHOUSE_DOMAIN,
            'SERPLY_API_KEY': config.SERPLY_API_KEY,
            'TAVILY_API_KEY': config.TAVILY_API_KEY,
            'SEARCHAPI_API_KEY': config.SEARCHAPI_API_KEY,
            'SEARCHAPI_ENGINE': config.SEARCHAPI_ENGINE,
            'SERPAPI_API_KEY': config.SERPAPI_API_KEY,
            'SERPAPI_ENGINE': config.SERPAPI_ENGINE,
            'JINA_API_KEY': config.JINA_API_KEY,
            'JINA_API_BASE_URL': config.JINA_API_BASE_URL,
            'BING_SEARCH_V7_ENDPOINT': config.BING_SEARCH_V7_ENDPOINT,
            'BING_SEARCH_V7_SUBSCRIPTION_KEY': config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
            'EXA_API_KEY': config.EXA_API_KEY,
            'PERPLEXITY_API_KEY': config.PERPLEXITY_API_KEY,
            'PERPLEXITY_MODEL': config.PERPLEXITY_MODEL,
            'PERPLEXITY_SEARCH_CONTEXT_USAGE': config.PERPLEXITY_SEARCH_CONTEXT_USAGE,
            'PERPLEXITY_SEARCH_API_URL': config.PERPLEXITY_SEARCH_API_URL,
            'MICROSOFT_WEB_IQ_API_BASE_URL': config.MICROSOFT_WEB_IQ_API_BASE_URL,
            'MICROSOFT_WEB_IQ_API_KEY': config.MICROSOFT_WEB_IQ_API_KEY,
            'MICROSOFT_WEB_IQ_LANGUAGE': config.MICROSOFT_WEB_IQ_LANGUAGE,
            'SOUGOU_API_SID': config.SOUGOU_API_SID,
            'SOUGOU_API_SK': config.SOUGOU_API_SK,
            'WEB_LOADER_ENGINE': config.WEB_LOADER_ENGINE,
            'WEB_LOADER_TIMEOUT': config.WEB_LOADER_TIMEOUT,
            'ENABLE_WEB_LOADER_SSL_VERIFICATION': config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
            'PLAYWRIGHT_WS_URL': config.PLAYWRIGHT_WS_URL,
            'PLAYWRIGHT_TIMEOUT': config.PLAYWRIGHT_TIMEOUT,
            'FIRECRAWL_API_KEY': config.FIRECRAWL_API_KEY,
            'FIRECRAWL_API_BASE_URL': config.FIRECRAWL_API_BASE_URL,
            'FIRECRAWL_TIMEOUT': config.FIRECRAWL_TIMEOUT,
            'TAVILY_EXTRACT_DEPTH': config.TAVILY_EXTRACT_DEPTH,
            'EXTERNAL_WEB_SEARCH_URL': config.EXTERNAL_WEB_SEARCH_URL,
            'EXTERNAL_WEB_SEARCH_API_KEY': config.EXTERNAL_WEB_SEARCH_API_KEY,
            'EXTERNAL_WEB_LOADER_URL': config.EXTERNAL_WEB_LOADER_URL,
            'EXTERNAL_WEB_LOADER_API_KEY': config.EXTERNAL_WEB_LOADER_API_KEY,
            'YOUTUBE_LOADER_LANGUAGE': config.YOUTUBE_LOADER_LANGUAGE,
            'YOUTUBE_LOADER_PROXY_URL': config.YOUTUBE_LOADER_PROXY_URL,
            'YOUTUBE_LOADER_TRANSLATION': request.app.state.YOUTUBE_LOADER_TRANSLATION,
            'YANDEX_WEB_SEARCH_URL': config.YANDEX_WEB_SEARCH_URL,
            'YANDEX_WEB_SEARCH_API_KEY': config.YANDEX_WEB_SEARCH_API_KEY,
            'YANDEX_WEB_SEARCH_CONFIG': config.YANDEX_WEB_SEARCH_CONFIG,
            'YOUCOM_API_KEY': config.YOUCOM_API_KEY,
            'LINKUP_API_KEY': config.LINKUP_API_KEY,
            'LINKUP_SEARCH_PARAMS': config.LINKUP_SEARCH_PARAMS,
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
    config: RetrievalConfig,
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
    min_size = config.CHUNK_MIN_SIZE_TARGET
    max_size = config.CHUNK_SIZE

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


def get_transformers_tokenizer(request: Request, config: RetrievalConfig):
    if config.RAG_TOKENIZER_MODEL:
        from transformers import AutoTokenizer

        tokenizer_model = config.RAG_TOKENIZER_MODEL
        if not os.path.exists(tokenizer_model) and '/' not in tokenizer_model:
            tokenizer_model = f'sentence-transformers/{tokenizer_model}'

        return AutoTokenizer.from_pretrained(
            tokenizer_model,
            cache_dir=os.getenv('SENTENCE_TRANSFORMERS_HOME') or os.getenv('HF_HUB_CACHE'),
            trust_remote_code=RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
            local_files_only=not RAG_EMBEDDING_MODEL_AUTO_UPDATE,
        )

    tokenizer = getattr(getattr(request.app.state, 'ef', None), 'tokenizer', None)
    if tokenizer is not None:
        return tokenizer

    raise ValueError('Tokenizer model required for Token (Transformers) text splitter')


def get_splitter_length_function(
    request: Request,
    config: RetrievalConfig,
) -> Callable[[str], int]:
    if config.TEXT_SPLITTER == 'token':
        encoding = tiktoken.get_encoding(str(config.TIKTOKEN_ENCODING_NAME))
        return lambda text: len(encoding.encode(text, disallowed_special=()))

    if config.TEXT_SPLITTER == 'token_transformers':
        tokenizer = get_transformers_tokenizer(request, config)
        return lambda text: len(tokenizer.encode(text))

    return len


def save_docs_to_vector_db(
    request: Request,
    docs,
    collection_name,
    config: RetrievalConfig,
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

    log.debug(f'save_docs_to_vector_db: document {_get_docs_info(docs)} {collection_name}')

    # Check if entries with the same hash (metadata.hash) already exist
    if metadata and 'hash' in metadata:
        result = VECTOR_DB_CLIENT.query(
            collection_name=collection_name,
            filter={'hash': metadata['hash']},
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

                if existing_file_id != metadata.get('file_id'):
                    log.info(f'Document with hash {metadata["hash"]} already exists')
                    raise ValueError(ERROR_MESSAGES.DUPLICATE_CONTENT)

    if split:
        if config.ENABLE_MARKDOWN_HEADER_TEXT_SPLITTER:
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
            if config.CHUNK_MIN_SIZE_TARGET > 0:
                docs = merge_docs_to_target_size(request, docs, config)

        if config.TEXT_SPLITTER in ['', 'character']:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=config.CHUNK_SIZE,
                chunk_overlap=config.CHUNK_OVERLAP,
                add_start_index=True,
            )
            docs = text_splitter.split_documents(docs)
        elif config.TEXT_SPLITTER == 'token':
            log.info(f'Using token text splitter: {config.TIKTOKEN_ENCODING_NAME}')

            tiktoken.get_encoding(str(config.TIKTOKEN_ENCODING_NAME))
            text_splitter = TokenTextSplitter(
                encoding_name=str(config.TIKTOKEN_ENCODING_NAME),
                chunk_size=config.CHUNK_SIZE,
                chunk_overlap=config.CHUNK_OVERLAP,
                add_start_index=True,
            )
            docs = text_splitter.split_documents(docs)
        elif config.TEXT_SPLITTER == 'token_transformers':
            log.info('Using transformers token text splitter')

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=config.CHUNK_SIZE,
                chunk_overlap=config.CHUNK_OVERLAP,
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
                'engine': config.RAG_EMBEDDING_ENGINE,
                'model': config.RAG_EMBEDDING_MODEL,
            },
        }
        for doc in docs
    ]

    try:
        if VECTOR_DB_CLIENT.has_collection(collection_name=collection_name):
            log.info(f'collection {collection_name} already exists')

            if overwrite:
                VECTOR_DB_CLIENT.delete_collection(collection_name=collection_name)
                log.info(f'deleting existing collection {collection_name}')
            elif add is False:
                log.info(f'collection {collection_name} already exists, overwrite is False and add is False')
                return True

        log.info(f'generating embeddings for {collection_name}')
        embedding_function = get_embedding_function(
            config.RAG_EMBEDDING_ENGINE,
            config.RAG_EMBEDDING_MODEL,
            request.app.state.ef,
            (
                config.RAG_OPENAI_API_BASE_URL
                if config.RAG_EMBEDDING_ENGINE == 'openai'
                else (
                    config.RAG_OLLAMA_BASE_URL
                    if config.RAG_EMBEDDING_ENGINE == 'ollama'
                    else config.RAG_AZURE_OPENAI_BASE_URL
                )
            ),
            (
                config.RAG_OPENAI_API_KEY
                if config.RAG_EMBEDDING_ENGINE == 'openai'
                else (
                    config.RAG_OLLAMA_API_KEY
                    if config.RAG_EMBEDDING_ENGINE == 'ollama'
                    else config.RAG_AZURE_OPENAI_API_KEY
                )
            ),
            config.RAG_EMBEDDING_BATCH_SIZE,
            azure_api_version=(
                config.RAG_AZURE_OPENAI_API_VERSION if config.RAG_EMBEDDING_ENGINE == 'azure_openai' else None
            ),
            enable_async=config.ENABLE_ASYNC_EMBEDDING,
            concurrent_requests=config.RAG_EMBEDDING_CONCURRENT_REQUESTS,
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
        log.info(f'embeddings generated {len(embeddings)} for {len(texts)} items')

        items = [
            {
                'id': str(uuid.uuid4()),
                'text': text,
                'vector': embeddings[idx],
                'metadata': metadatas[idx],
            }
            for idx, text in enumerate(texts)
        ]

        log.info(f'adding to collection {collection_name}')
        VECTOR_DB_CLIENT.insert(
            collection_name=collection_name,
            items=items,
        )

        log.info(f'added {len(items)} items to collection {collection_name}')
        return True
    except Exception as e:
        log.exception(e)
        raise e


class ProcessFileForm(BaseModel):
    file_id: str
    content: str | None = None
    collection_name: str | None = None


@router.post('/process/file')
async def process_file(
    request: Request,
    form_data: ProcessFileForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Process a file and save its content to the vector database.
    Process a file and save its content to the vector database.
    Note: granular session management is used to prevent connection pool exhaustion.
    The session is committed before external API calls, and updates use a fresh session.
    """
    config = await get_retrieval_config()
    if user.role == 'admin':
        file = await Files.get_file_by_id(form_data.file_id, db=db)
    else:
        file = await Files.get_file_by_id_and_user_id(form_data.file_id, user.id, db=db)

    if file:
        try:
            collection_name = form_data.collection_name

            if collection_name is None:
                collection_name = f'file-{file.id}'
            else:
                await _validate_collection_access([collection_name], user, access_type='write')

            if form_data.content:
                # Update the content in the file
                # Usage: /files/{file_id}/data/content/update, /files/ (audio file upload pipeline)

                try:
                    # /files/{file_id}/data/content/update
                    await ASYNC_VECTOR_DB_CLIENT.delete_collection(collection_name=f'file-{file.id}')
                except Exception:
                    # Audio file upload pipeline
                    pass

                docs = [
                    Document(
                        page_content=form_data.content.replace('<br/>', '\n'),
                        metadata={
                            **file.meta,
                            'name': file.filename,
                            'created_by': file.user_id,
                            'file_id': file.id,
                            'source': file.filename,
                        },
                    )
                ]

                text_content = form_data.content
            elif form_data.collection_name:
                # Check if the file has already been processed and save the content
                # Usage: /knowledge/{id}/file/add, /knowledge/{id}/file/update

                result = await ASYNC_VECTOR_DB_CLIENT.query(
                    collection_name=f'file-{file.id}', filter={'file_id': file.id}
                )

                if result is not None and len(result.ids[0]) > 0:
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
                            page_content=file.data.get('content', ''),
                            metadata={
                                **file.meta,
                                'name': file.filename,
                                'created_by': file.user_id,
                                'file_id': file.id,
                                'source': file.filename,
                            },
                        )
                    ]

                text_content = file.data.get('content', '')
            else:
                # Process the file and save the content
                # Usage: /files/
                file_path = file.path
                if file_path:
                    file_path = await asyncio.to_thread(Storage.get_file, file_path)
                    loader_config = await get_loader_config()
                    loader = build_loader_from_config(request, loader_config)
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
                                **file.meta,
                                'name': file.filename,
                                'created_by': file.user_id,
                                'file_id': file.id,
                                'source': file.filename,
                            },
                        )
                    ]
                text_content = ' '.join([doc.page_content for doc in docs])

            log.debug(f'text_content: {text_content}')
            await Files.update_file_data_by_id(
                file.id,
                {'content': text_content},
                db=db,
            )
            hash = calculate_sha256_string(text_content)

            if config.BYPASS_EMBEDDING_AND_RETRIEVAL:
                await Files.update_file_data_by_id(file.id, {'status': 'completed'}, db=db)
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
                    result = await run_in_threadpool(
                        save_docs_to_vector_db,
                        request,
                        docs=docs,
                        collection_name=collection_name,
                        config=config,
                        metadata={
                            'file_id': file.id,
                            'name': file.filename,
                            'hash': hash,
                        },
                        add=(True if form_data.collection_name else False),
                        user=user,
                    )
                    log.info(f'added {len(docs)} items to collection {collection_name}')

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
                                {'status': 'completed'},
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
                    {'status': 'failed'},
                    db=session,
                )
                # Clear the hash so the file can be re-uploaded after fixing the issue
                await Files.update_file_hash_by_id(file.id, None, db=session)

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
    log.debug(f'text_content: {text_content}')

    config = await get_retrieval_config()
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


@router.post('/process/youtube')
@router.post('/process/web')
async def process_web(
    request: Request,
    form_data: ProcessUrlForm,
    process: bool = Query(True, description='Whether to process and save the content'),
    overwrite: bool = Query(True, description='Whether to overwrite existing collection'),
    user=Depends(get_verified_user),
):
    config = await get_retrieval_config()
    try:
        content, docs = await get_content_from_url(request, form_data.url)
        log.debug(f'text_content: {content}')

        if process:
            collection_name = form_data.collection_name
            if not collection_name:
                collection_name = calculate_sha256_string(form_data.url)[:63]
            else:
                await _validate_collection_access([collection_name], user, access_type='write')

            if not config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL:
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


async def search_web(request: Request, engine: str, query: str, user=None) -> list[SearchResult]:
    """Dispatch a web search query to the configured engine and return results.

    Providers that have been migrated to async (aiohttp) are awaited natively.
    Legacy sync providers are offloaded via ``asyncio.to_thread`` to avoid
    blocking the event loop.
    """

    # TODO: add playwright to search the web
    config = await get_retrieval_config()
    if engine == 'ollama_cloud':
        return await asyncio.to_thread(
            search_ollama_cloud,
            'https://ollama.com',
            config.OLLAMA_CLOUD_WEB_SEARCH_API_KEY,
            query,
            config.WEB_SEARCH_RESULT_COUNT,
            config.WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == 'perplexity_search':
        if config.PERPLEXITY_API_KEY:
            return await asyncio.to_thread(
                search_perplexity_search,
                config.PERPLEXITY_API_KEY,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                config.PERPLEXITY_SEARCH_API_URL,
                user,
            )
        else:
            raise Exception('No PERPLEXITY_API_KEY found in environment variables')
    elif engine == 'searxng':
        if config.SEARXNG_QUERY_URL:
            searxng_kwargs = {'language': config.SEARXNG_LANGUAGE}
            return await search_searxng(
                config.SEARXNG_QUERY_URL,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                **searxng_kwargs,
            )
        else:
            raise Exception('No SEARXNG_QUERY_URL found in environment variables')
    elif engine == 'yacy':
        if config.YACY_QUERY_URL:
            return await asyncio.to_thread(
                search_yacy,
                config.YACY_QUERY_URL,
                config.YACY_USERNAME,
                config.YACY_PASSWORD,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No YACY_QUERY_URL found in environment variables')
    elif engine == 'google_pse':
        if config.GOOGLE_PSE_API_KEY and config.GOOGLE_PSE_ENGINE_ID:
            return await search_google_pse(
                config.GOOGLE_PSE_API_KEY,
                config.GOOGLE_PSE_ENGINE_ID,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                referer=config.WEBUI_URL,
            )
        else:
            raise Exception('No GOOGLE_PSE_API_KEY or GOOGLE_PSE_ENGINE_ID found in environment variables')
    elif engine == 'brave':
        if config.BRAVE_SEARCH_API_KEY:
            return await search_brave(
                config.BRAVE_SEARCH_API_KEY,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No BRAVE_SEARCH_API_KEY found in environment variables')
    elif engine == 'brave_llm_context':
        if config.BRAVE_SEARCH_API_KEY:
            return await asyncio.to_thread(
                search_brave_llm_context,
                config.BRAVE_SEARCH_API_KEY,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                config.BRAVE_SEARCH_CONTEXT_TOKENS,
            )
        else:
            raise Exception('No BRAVE_SEARCH_API_KEY found in environment variables')
    elif engine == 'kagi':
        if config.KAGI_SEARCH_API_KEY:
            return await asyncio.to_thread(
                search_kagi,
                config.KAGI_SEARCH_API_KEY,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No KAGI_SEARCH_API_KEY found in environment variables')
    elif engine == 'mojeek':
        if config.MOJEEK_SEARCH_API_KEY:
            return await asyncio.to_thread(
                search_mojeek,
                config.MOJEEK_SEARCH_API_KEY,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No MOJEEK_SEARCH_API_KEY found in environment variables')
    elif engine == 'bocha':
        if config.BOCHA_SEARCH_API_KEY:
            return await asyncio.to_thread(
                search_bocha,
                config.BOCHA_SEARCH_API_KEY,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No BOCHA_SEARCH_API_KEY found in environment variables')
    elif engine == 'serpstack':
        if config.SERPSTACK_API_KEY:
            return await search_serpstack(
                config.SERPSTACK_API_KEY,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                https_enabled=config.SERPSTACK_HTTPS,
            )
        else:
            raise Exception('No SERPSTACK_API_KEY found in environment variables')
    elif engine == 'serper':
        if config.SERPER_API_KEY:
            return await search_serper(
                config.SERPER_API_KEY,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No SERPER_API_KEY found in environment variables')
    elif engine == 'serphouse':
        if config.SERPHOUSE_API_KEY:
            return await search_serphouse(
                config.SERPHOUSE_API_KEY,
                config.SERPHOUSE_DOMAIN,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No SERPHOUSE_API_KEY found in environment variables')
    elif engine == 'serply':
        if config.SERPLY_API_KEY:
            return await asyncio.to_thread(
                search_serply,
                config.SERPLY_API_KEY,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                filter_list=config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No SERPLY_API_KEY found in environment variables')
    elif engine == 'duckduckgo':
        return await asyncio.to_thread(
            search_duckduckgo,
            query,
            config.WEB_SEARCH_RESULT_COUNT,
            config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            concurrent_requests=config.WEB_SEARCH_CONCURRENT_REQUESTS,
            backend=config.DDGS_BACKEND,
        )
    elif engine == 'tavily':
        if config.TAVILY_API_KEY:
            return await asyncio.to_thread(
                search_tavily,
                config.TAVILY_API_KEY,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No TAVILY_API_KEY found in environment variables')
    elif engine == 'exa':
        if config.EXA_API_KEY:
            return await asyncio.to_thread(
                search_exa,
                config.EXA_API_KEY,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No EXA_API_KEY found in environment variables')
    elif engine == 'searchapi':
        if config.SEARCHAPI_API_KEY:
            return await asyncio.to_thread(
                search_searchapi,
                config.SEARCHAPI_API_KEY,
                config.SEARCHAPI_ENGINE,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No SEARCHAPI_API_KEY found in environment variables')
    elif engine == 'serpapi':
        if config.SERPAPI_API_KEY:
            return await asyncio.to_thread(
                search_serpapi,
                config.SERPAPI_API_KEY,
                config.SERPAPI_ENGINE,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No SERPAPI_API_KEY found in environment variables')
    elif engine == 'jina':
        return await asyncio.to_thread(
            search_jina,
            config.JINA_API_KEY,
            query,
            config.WEB_SEARCH_RESULT_COUNT,
            config.JINA_API_BASE_URL,
        )
    elif engine == 'bing':
        return await asyncio.to_thread(
            search_bing,
            config.BING_SEARCH_V7_SUBSCRIPTION_KEY,
            config.BING_SEARCH_V7_ENDPOINT,
            str(DEFAULT_LOCALE),
            query,
            config.WEB_SEARCH_RESULT_COUNT,
            config.WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == 'azure':
        if config.AZURE_AI_SEARCH_API_KEY and config.AZURE_AI_SEARCH_ENDPOINT and config.AZURE_AI_SEARCH_INDEX_NAME:
            return await asyncio.to_thread(
                search_azure,
                config.AZURE_AI_SEARCH_API_KEY,
                config.AZURE_AI_SEARCH_ENDPOINT,
                config.AZURE_AI_SEARCH_INDEX_NAME,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception(
                'AZURE_AI_SEARCH_API_KEY, AZURE_AI_SEARCH_ENDPOINT, and AZURE_AI_SEARCH_INDEX_NAME are required for Azure AI Search'
            )
    elif engine == 'perplexity':
        return await asyncio.to_thread(
            search_perplexity,
            config.PERPLEXITY_API_KEY,
            query,
            config.WEB_SEARCH_RESULT_COUNT,
            config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            model=config.PERPLEXITY_MODEL,
            search_context_usage=config.PERPLEXITY_SEARCH_CONTEXT_USAGE,
        )
    elif engine == 'microsoft_web_iq':
        if config.MICROSOFT_WEB_IQ_API_KEY:
            return await asyncio.to_thread(
                search_microsoft_web_iq,
                config.MICROSOFT_WEB_IQ_API_BASE_URL,
                config.MICROSOFT_WEB_IQ_API_KEY,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                config.MICROSOFT_WEB_IQ_LANGUAGE,
                user,
            )
        else:
            raise Exception('No MICROSOFT_WEB_IQ_API_KEY found in environment variables')
    elif engine == 'sougou':
        if config.SOUGOU_API_SID and config.SOUGOU_API_SK:
            return await asyncio.to_thread(
                search_sougou,
                config.SOUGOU_API_SID,
                config.SOUGOU_API_SK,
                query,
                config.WEB_SEARCH_RESULT_COUNT,
                config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception('No SOUGOU_API_SID or SOUGOU_API_SK found in environment variables')
    elif engine == 'firecrawl':
        return await asyncio.to_thread(
            search_firecrawl,
            config.FIRECRAWL_API_BASE_URL,
            config.FIRECRAWL_API_KEY,
            query,
            config.WEB_SEARCH_RESULT_COUNT,
            config.WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == 'external':
        return await asyncio.to_thread(
            search_external,
            request,
            config.EXTERNAL_WEB_SEARCH_URL,
            config.EXTERNAL_WEB_SEARCH_API_KEY,
            query,
            config.WEB_SEARCH_RESULT_COUNT,
            config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            user=user,
        )
    elif engine == 'yandex':
        return await asyncio.to_thread(
            search_yandex,
            request,
            config.YANDEX_WEB_SEARCH_URL,
            config.YANDEX_WEB_SEARCH_API_KEY,
            config.YANDEX_WEB_SEARCH_CONFIG,
            query,
            config.WEB_SEARCH_RESULT_COUNT,
            config.WEB_SEARCH_DOMAIN_FILTER_LIST,
            user=user,
        )
    elif engine == 'youcom':
        return await asyncio.to_thread(
            search_youcom,
            config.YOUCOM_API_KEY,
            query,
            config.WEB_SEARCH_RESULT_COUNT,
            config.WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == 'linkup':
        if config.LINKUP_API_KEY:
            return await asyncio.to_thread(
                search_linkup,
                api_key=config.LINKUP_API_KEY,
                query=query,
                count=config.WEB_SEARCH_RESULT_COUNT,
                filter_list=config.WEB_SEARCH_DOMAIN_FILTER_LIST,
                params=config.LINKUP_SEARCH_PARAMS,
            )
        else:
            raise Exception('No LINKUP_API_KEY found in environment variables')
    else:
        raise Exception('No search engine API key found in environment variables')


@router.post('/process/web/search')
async def process_web_search(request: Request, form_data: SearchForm, user=Depends(get_verified_user)):
    config = await get_retrieval_config()
    if not config.ENABLE_WEB_SEARCH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if user.role != 'admin' and not await has_permission(user.id, 'features.web_search', config.USER_PERMISSIONS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    urls = []
    result_items = []

    try:
        logging.debug(f'trying to web search with {config.WEB_SEARCH_ENGINE, form_data.queries}')

        # Use semaphore to limit concurrent requests based on WEB_SEARCH_CONCURRENT_REQUESTS
        # 0 or None = unlimited (previous behavior), positive number = limited concurrency
        # Set to 1 for sequential execution (rate-limited APIs like Brave free tier)
        concurrent_limit = config.WEB_SEARCH_CONCURRENT_REQUESTS

        if concurrent_limit:
            # Limited concurrency with semaphore
            semaphore = asyncio.Semaphore(concurrent_limit)

            async def search_query_with_semaphore(query):
                async with semaphore:
                    return await search_web(
                        request,
                        config.WEB_SEARCH_ENGINE,
                        query,
                        user,
                    )

            search_tasks = [search_query_with_semaphore(query) for query in form_data.queries]
        else:
            # Unlimited parallel execution
            search_tasks = [
                search_web(
                    request,
                    config.WEB_SEARCH_ENGINE,
                    query,
                    user,
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
        log.debug(f'urls: {urls}')

    except Exception as e:
        log.exception('Web search failed')
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.WEB_SEARCH_ERROR(e))

    if len(urls) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.DEFAULT('No results found from web search'),
        )

    try:
        if config.BYPASS_WEB_SEARCH_WEB_LOADER:
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
            loader = get_web_loader(
                urls,
                verify_ssl=config.ENABLE_WEB_LOADER_SSL_VERIFICATION,
                requests_per_second=config.WEB_LOADER_CONCURRENT_REQUESTS,
                trust_env=config.WEB_SEARCH_TRUST_ENV,
            )
            docs = await loader.aload()

        urls = [
            doc.metadata.get('source') for doc in docs if doc.metadata.get('source')
        ]  # only keep the urls returned by the loader
        result_items = [
            dict(item) for item in result_items if item.link in urls
        ]  # only keep the search results that have been loaded

        if config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL:
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
            # Create a single collection for all documents
            collection_name = f'web-search-{calculate_sha256_string("-".join(form_data.queries))}'[:63]

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
                log.debug(f'error saving docs: {e}')

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
            detail=ERROR_MESSAGES.DEFAULT(e, ERROR_MESSAGES.WEB_SEARCH_ERROR()),
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
    config = await get_retrieval_config()
    await _validate_collection_access([form_data.collection_name], user)

    try:
        if config.ENABLE_RAG_HYBRID_SEARCH and (form_data.hybrid is None or form_data.hybrid):
            return await query_doc_with_hybrid_search(
                collection_name=form_data.collection_name,
                collection_result=None,
                query=form_data.query,
                embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                    query, prefix=prefix, user=user
                ),
                k=form_data.k if form_data.k else config.TOP_K,
                reranking_function=(
                    (lambda query, documents: request.app.state.RERANKING_FUNCTION(query, documents, user=user))
                    if request.app.state.RERANKING_FUNCTION
                    else None
                ),
                k_reranker=form_data.k_reranker or config.TOP_K_RERANKER,
                r=(form_data.r if form_data.r else config.RELEVANCE_THRESHOLD),
                hybrid_bm25_weight=(
                    form_data.hybrid_bm25_weight
                    if form_data.hybrid_bm25_weight is not None
                    else config.HYBRID_BM25_WEIGHT
                ),
            )
        else:
            query_embedding = await request.app.state.EMBEDDING_FUNCTION(
                form_data.query, prefix=RAG_EMBEDDING_QUERY_PREFIX, user=user
            )
            # query_doc wraps a blocking VECTOR_DB_CLIENT.search call;
            # offload so the request's event loop stays responsive.
            return await asyncio.to_thread(
                query_doc,
                collection_name=form_data.collection_name,
                query_embedding=query_embedding,
                k=form_data.k if form_data.k else config.TOP_K,
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
    config = await get_retrieval_config()
    await _validate_collection_access(form_data.collection_names, user)

    try:
        if config.ENABLE_RAG_HYBRID_SEARCH and (form_data.hybrid is None or form_data.hybrid):
            return await query_collection_with_hybrid_search(
                collection_names=form_data.collection_names,
                queries=[form_data.query],
                embedding_function=lambda query, prefix: request.app.state.EMBEDDING_FUNCTION(
                    query, prefix=prefix, user=user
                ),
                k=form_data.k if form_data.k else config.TOP_K,
                reranking_function=(
                    (lambda query, documents: request.app.state.RERANKING_FUNCTION(query, documents, user=user))
                    if request.app.state.RERANKING_FUNCTION
                    else None
                ),
                k_reranker=form_data.k_reranker or config.TOP_K_RERANKER,
                r=(form_data.r if form_data.r else config.RELEVANCE_THRESHOLD),
                hybrid_bm25_weight=(
                    form_data.hybrid_bm25_weight
                    if form_data.hybrid_bm25_weight is not None
                    else config.HYBRID_BM25_WEIGHT
                ),
                enable_enriched_texts=(
                    form_data.enable_enriched_texts
                    if form_data.enable_enriched_texts is not None
                    else config.ENABLE_RAG_HYBRID_SEARCH_ENRICHED_TEXTS
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
                k=form_data.k if form_data.k else config.TOP_K,
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

    config = await get_retrieval_config()
    collection_name = form_data.collection_name

    if collection_name:
        await _validate_collection_access([collection_name], user, access_type='write')

    file_results: list[BatchProcessFilesResult] = []
    file_errors: list[BatchProcessFilesResult] = []
    file_updates: list[FileUpdateForm] = []

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
            docs: list[Document] = [
                Document(
                    page_content=text_content.replace('<br/>', '\n'),
                    metadata={
                        **file.meta,
                        'name': file.filename,
                        'created_by': file.user_id,
                        'file_id': file.id,
                        'source': file.filename,
                    },
                )
            ]

            all_docs.extend(docs)

            file_updates.append(
                FileUpdateForm(
                    hash=calculate_sha256_string(text_content),
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
