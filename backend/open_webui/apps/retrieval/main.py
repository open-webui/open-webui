# TODO: Merge this with the webui_app and make it a single app

import json
import logging
import mimetypes
import os
import shutil

import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional, Sequence, Union

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


from open_webui.storage.provider import Storage
from open_webui.apps.webui.models.knowledge import Knowledges
from open_webui.apps.retrieval.vector.connector import VECTOR_DB_CLIENT

# Document loaders
from open_webui.apps.retrieval.loaders.main import Loader

# Web search engines
from open_webui.apps.retrieval.web.main import SearchResult
from open_webui.apps.retrieval.web.utils import get_web_loader
from open_webui.apps.retrieval.web.brave import search_brave
from open_webui.apps.retrieval.web.duckduckgo import search_duckduckgo
from open_webui.apps.retrieval.web.google_pse import search_google_pse
from open_webui.apps.retrieval.web.jina_search import search_jina
from open_webui.apps.retrieval.web.searchapi import search_searchapi
from open_webui.apps.retrieval.web.searxng import search_searxng
from open_webui.apps.retrieval.web.serper import search_serper
from open_webui.apps.retrieval.web.serply import search_serply
from open_webui.apps.retrieval.web.serpstack import search_serpstack
from open_webui.apps.retrieval.web.tavily import search_tavily


from open_webui.apps.retrieval.utils import (
    get_embedding_function,
    get_model_path,
    query_collection,
    query_collection_with_hybrid_search,
    query_doc,
    query_doc_with_hybrid_search,
)

from open_webui.apps.webui.models.files import Files
from open_webui.config import (
    BRAVE_SEARCH_API_KEY,
    TIKTOKEN_ENCODING_NAME,
    RAG_TEXT_SPLITTER,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CONTENT_EXTRACTION_ENGINE,
    CORS_ALLOW_ORIGIN,
    ENABLE_RAG_HYBRID_SEARCH,
    ENABLE_RAG_LOCAL_WEB_FETCH,
    ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
    ENABLE_RAG_WEB_SEARCH,
    ENV,
    GOOGLE_PSE_API_KEY,
    GOOGLE_PSE_ENGINE_ID,
    PDF_EXTRACT_IMAGES,
    RAG_EMBEDDING_ENGINE,
    RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
    RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
    RAG_EMBEDDING_BATCH_SIZE,
    RAG_FILE_MAX_COUNT,
    RAG_FILE_MAX_SIZE,
    RAG_OPENAI_API_BASE_URL,
    RAG_OPENAI_API_KEY,
    RAG_RELEVANCE_THRESHOLD,
    RAG_RERANKING_MODEL,
    RAG_RERANKING_MODEL_AUTO_UPDATE,
    RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
    DEFAULT_RAG_TEMPLATE,
    RAG_TEMPLATE,
    RAG_TOP_K,
    RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
    RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
    RAG_WEB_SEARCH_ENGINE,
    RAG_WEB_SEARCH_RESULT_COUNT,
    SEARCHAPI_API_KEY,
    SEARCHAPI_ENGINE,
    SEARXNG_QUERY_URL,
    SERPER_API_KEY,
    SERPLY_API_KEY,
    SERPSTACK_API_KEY,
    SERPSTACK_HTTPS,
    TAVILY_API_KEY,
    TIKA_SERVER_URL,
    UPLOAD_DIR,
    YOUTUBE_LOADER_LANGUAGE,
    AppConfig,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS, DEVICE_TYPE, DOCKER
from open_webui.utils.misc import (
    calculate_sha256,
    calculate_sha256_string,
    extract_folders_after_data_docs,
    sanitize_filename,
)
from open_webui.utils.utils import get_admin_user, get_verified_user

from langchain.text_splitter import RecursiveCharacterTextSplitter, TokenTextSplitter
from langchain_community.document_loaders import (
    YoutubeLoader,
)
from langchain_core.documents import Document


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

app = FastAPI()

app.state.config = AppConfig()

app.state.config.TOP_K = RAG_TOP_K
app.state.config.RELEVANCE_THRESHOLD = RAG_RELEVANCE_THRESHOLD
app.state.config.FILE_MAX_SIZE = RAG_FILE_MAX_SIZE
app.state.config.FILE_MAX_COUNT = RAG_FILE_MAX_COUNT

app.state.config.ENABLE_RAG_HYBRID_SEARCH = ENABLE_RAG_HYBRID_SEARCH
app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION = (
    ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION
)

app.state.config.CONTENT_EXTRACTION_ENGINE = CONTENT_EXTRACTION_ENGINE
app.state.config.TIKA_SERVER_URL = TIKA_SERVER_URL

app.state.config.TEXT_SPLITTER = RAG_TEXT_SPLITTER
app.state.config.TIKTOKEN_ENCODING_NAME = TIKTOKEN_ENCODING_NAME

app.state.config.CHUNK_SIZE = CHUNK_SIZE
app.state.config.CHUNK_OVERLAP = CHUNK_OVERLAP

app.state.config.RAG_EMBEDDING_ENGINE = RAG_EMBEDDING_ENGINE
app.state.config.RAG_EMBEDDING_MODEL = RAG_EMBEDDING_MODEL
app.state.config.RAG_EMBEDDING_BATCH_SIZE = RAG_EMBEDDING_BATCH_SIZE
app.state.config.RAG_RERANKING_MODEL = RAG_RERANKING_MODEL
app.state.config.RAG_TEMPLATE = RAG_TEMPLATE

app.state.config.OPENAI_API_BASE_URL = RAG_OPENAI_API_BASE_URL
app.state.config.OPENAI_API_KEY = RAG_OPENAI_API_KEY

app.state.config.PDF_EXTRACT_IMAGES = PDF_EXTRACT_IMAGES

app.state.config.YOUTUBE_LOADER_LANGUAGE = YOUTUBE_LOADER_LANGUAGE
app.state.YOUTUBE_LOADER_TRANSLATION = None


app.state.config.ENABLE_RAG_WEB_SEARCH = ENABLE_RAG_WEB_SEARCH
app.state.config.RAG_WEB_SEARCH_ENGINE = RAG_WEB_SEARCH_ENGINE
app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST = RAG_WEB_SEARCH_DOMAIN_FILTER_LIST

app.state.config.SEARXNG_QUERY_URL = SEARXNG_QUERY_URL
app.state.config.GOOGLE_PSE_API_KEY = GOOGLE_PSE_API_KEY
app.state.config.GOOGLE_PSE_ENGINE_ID = GOOGLE_PSE_ENGINE_ID
app.state.config.BRAVE_SEARCH_API_KEY = BRAVE_SEARCH_API_KEY
app.state.config.SERPSTACK_API_KEY = SERPSTACK_API_KEY
app.state.config.SERPSTACK_HTTPS = SERPSTACK_HTTPS
app.state.config.SERPER_API_KEY = SERPER_API_KEY
app.state.config.SERPLY_API_KEY = SERPLY_API_KEY
app.state.config.TAVILY_API_KEY = TAVILY_API_KEY
app.state.config.SEARCHAPI_API_KEY = SEARCHAPI_API_KEY
app.state.config.SEARCHAPI_ENGINE = SEARCHAPI_ENGINE
app.state.config.RAG_WEB_SEARCH_RESULT_COUNT = RAG_WEB_SEARCH_RESULT_COUNT
app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS = RAG_WEB_SEARCH_CONCURRENT_REQUESTS


def update_embedding_model(
    embedding_model: str,
    auto_update: bool = False,
):
    if embedding_model and app.state.config.RAG_EMBEDDING_ENGINE == "":
        from sentence_transformers import SentenceTransformer

        app.state.sentence_transformer_ef = SentenceTransformer(
            get_model_path(embedding_model, auto_update),
            device=DEVICE_TYPE,
            trust_remote_code=RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE,
        )
    else:
        app.state.sentence_transformer_ef = None


def update_reranking_model(
    reranking_model: str,
    auto_update: bool = False,
):
    if reranking_model:
        if any(model in reranking_model for model in ["jinaai/jina-colbert-v2"]):
            try:
                from open_webui.apps.retrieval.models.colbert import ColBERT

                app.state.sentence_transformer_rf = ColBERT(
                    get_model_path(reranking_model, auto_update),
                    env="docker" if DOCKER else None,
                )
            except Exception as e:
                log.error(f"ColBERT: {e}")
                app.state.sentence_transformer_rf = None
                app.state.config.ENABLE_RAG_HYBRID_SEARCH = False
        else:
            import sentence_transformers

            try:
                app.state.sentence_transformer_rf = sentence_transformers.CrossEncoder(
                    get_model_path(reranking_model, auto_update),
                    device=DEVICE_TYPE,
                    trust_remote_code=RAG_RERANKING_MODEL_TRUST_REMOTE_CODE,
                )
            except:
                log.error("CrossEncoder error")
                app.state.sentence_transformer_rf = None
                app.state.config.ENABLE_RAG_HYBRID_SEARCH = False
    else:
        app.state.sentence_transformer_rf = None


update_embedding_model(
    app.state.config.RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
)

update_reranking_model(
    app.state.config.RAG_RERANKING_MODEL,
    RAG_RERANKING_MODEL_AUTO_UPDATE,
)


app.state.EMBEDDING_FUNCTION = get_embedding_function(
    app.state.config.RAG_EMBEDDING_ENGINE,
    app.state.config.RAG_EMBEDDING_MODEL,
    app.state.sentence_transformer_ef,
    app.state.config.OPENAI_API_KEY,
    app.state.config.OPENAI_API_BASE_URL,
    app.state.config.RAG_EMBEDDING_BATCH_SIZE,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CollectionNameForm(BaseModel):
    collection_name: Optional[str] = None


class ProcessUrlForm(CollectionNameForm):
    url: str


class SearchForm(CollectionNameForm):
    query: str


@app.get("/")
async def get_status():
    return {
        "status": True,
        "chunk_size": app.state.config.CHUNK_SIZE,
        "chunk_overlap": app.state.config.CHUNK_OVERLAP,
        "template": app.state.config.RAG_TEMPLATE,
        "embedding_engine": app.state.config.RAG_EMBEDDING_ENGINE,
        "embedding_model": app.state.config.RAG_EMBEDDING_MODEL,
        "reranking_model": app.state.config.RAG_RERANKING_MODEL,
        "embedding_batch_size": app.state.config.RAG_EMBEDDING_BATCH_SIZE,
    }


@app.get("/embedding")
async def get_embedding_config(user=Depends(get_admin_user)):
    return {
        "status": True,
        "embedding_engine": app.state.config.RAG_EMBEDDING_ENGINE,
        "embedding_model": app.state.config.RAG_EMBEDDING_MODEL,
        "embedding_batch_size": app.state.config.RAG_EMBEDDING_BATCH_SIZE,
        "openai_config": {
            "url": app.state.config.OPENAI_API_BASE_URL,
            "key": app.state.config.OPENAI_API_KEY,
        },
    }


@app.get("/reranking")
async def get_reraanking_config(user=Depends(get_admin_user)):
    return {
        "status": True,
        "reranking_model": app.state.config.RAG_RERANKING_MODEL,
    }


class OpenAIConfigForm(BaseModel):
    url: str
    key: str


class EmbeddingModelUpdateForm(BaseModel):
    openai_config: Optional[OpenAIConfigForm] = None
    embedding_engine: str
    embedding_model: str
    embedding_batch_size: Optional[int] = 1


@app.post("/embedding/update")
async def update_embedding_config(
    form_data: EmbeddingModelUpdateForm, user=Depends(get_admin_user)
):
    log.info(
        f"Updating embedding model: {app.state.config.RAG_EMBEDDING_MODEL} to {form_data.embedding_model}"
    )
    try:
        app.state.config.RAG_EMBEDDING_ENGINE = form_data.embedding_engine
        app.state.config.RAG_EMBEDDING_MODEL = form_data.embedding_model

        if app.state.config.RAG_EMBEDDING_ENGINE in ["ollama", "openai"]:
            if form_data.openai_config is not None:
                app.state.config.OPENAI_API_BASE_URL = form_data.openai_config.url
                app.state.config.OPENAI_API_KEY = form_data.openai_config.key
            app.state.config.RAG_EMBEDDING_BATCH_SIZE = form_data.embedding_batch_size

        update_embedding_model(app.state.config.RAG_EMBEDDING_MODEL)

        app.state.EMBEDDING_FUNCTION = get_embedding_function(
            app.state.config.RAG_EMBEDDING_ENGINE,
            app.state.config.RAG_EMBEDDING_MODEL,
            app.state.sentence_transformer_ef,
            app.state.config.OPENAI_API_KEY,
            app.state.config.OPENAI_API_BASE_URL,
            app.state.config.RAG_EMBEDDING_BATCH_SIZE,
        )

        return {
            "status": True,
            "embedding_engine": app.state.config.RAG_EMBEDDING_ENGINE,
            "embedding_model": app.state.config.RAG_EMBEDDING_MODEL,
            "embedding_batch_size": app.state.config.RAG_EMBEDDING_BATCH_SIZE,
            "openai_config": {
                "url": app.state.config.OPENAI_API_BASE_URL,
                "key": app.state.config.OPENAI_API_KEY,
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


@app.post("/reranking/update")
async def update_reranking_config(
    form_data: RerankingModelUpdateForm, user=Depends(get_admin_user)
):
    log.info(
        f"Updating reranking model: {app.state.config.RAG_RERANKING_MODEL} to {form_data.reranking_model}"
    )
    try:
        app.state.config.RAG_RERANKING_MODEL = form_data.reranking_model

        update_reranking_model(app.state.config.RAG_RERANKING_MODEL, True)

        return {
            "status": True,
            "reranking_model": app.state.config.RAG_RERANKING_MODEL,
        }
    except Exception as e:
        log.exception(f"Problem updating reranking model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@app.get("/config")
async def get_rag_config(user=Depends(get_admin_user)):
    return {
        "status": True,
        "pdf_extract_images": app.state.config.PDF_EXTRACT_IMAGES,
        "content_extraction": {
            "engine": app.state.config.CONTENT_EXTRACTION_ENGINE,
            "tika_server_url": app.state.config.TIKA_SERVER_URL,
        },
        "chunk": {
            "text_splitter": app.state.config.TEXT_SPLITTER,
            "chunk_size": app.state.config.CHUNK_SIZE,
            "chunk_overlap": app.state.config.CHUNK_OVERLAP,
        },
        "file": {
            "max_size": app.state.config.FILE_MAX_SIZE,
            "max_count": app.state.config.FILE_MAX_COUNT,
        },
        "youtube": {
            "language": app.state.config.YOUTUBE_LOADER_LANGUAGE,
            "translation": app.state.YOUTUBE_LOADER_TRANSLATION,
        },
        "web": {
            "ssl_verification": app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
            "search": {
                "enabled": app.state.config.ENABLE_RAG_WEB_SEARCH,
                "engine": app.state.config.RAG_WEB_SEARCH_ENGINE,
                "searxng_query_url": app.state.config.SEARXNG_QUERY_URL,
                "google_pse_api_key": app.state.config.GOOGLE_PSE_API_KEY,
                "google_pse_engine_id": app.state.config.GOOGLE_PSE_ENGINE_ID,
                "brave_search_api_key": app.state.config.BRAVE_SEARCH_API_KEY,
                "serpstack_api_key": app.state.config.SERPSTACK_API_KEY,
                "serpstack_https": app.state.config.SERPSTACK_HTTPS,
                "serper_api_key": app.state.config.SERPER_API_KEY,
                "serply_api_key": app.state.config.SERPLY_API_KEY,
                "tavily_api_key": app.state.config.TAVILY_API_KEY,
                "searchapi_api_key": app.state.config.SEARCHAPI_API_KEY,
                "seaarchapi_engine": app.state.config.SEARCHAPI_ENGINE,
                "result_count": app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                "concurrent_requests": app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
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


class WebSearchConfig(BaseModel):
    enabled: bool
    engine: Optional[str] = None
    searxng_query_url: Optional[str] = None
    google_pse_api_key: Optional[str] = None
    google_pse_engine_id: Optional[str] = None
    brave_search_api_key: Optional[str] = None
    serpstack_api_key: Optional[str] = None
    serpstack_https: Optional[bool] = None
    serper_api_key: Optional[str] = None
    serply_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None
    searchapi_api_key: Optional[str] = None
    searchapi_engine: Optional[str] = None
    result_count: Optional[int] = None
    concurrent_requests: Optional[int] = None


class WebConfig(BaseModel):
    search: WebSearchConfig
    web_loader_ssl_verification: Optional[bool] = None


class ConfigUpdateForm(BaseModel):
    pdf_extract_images: Optional[bool] = None
    file: Optional[FileConfig] = None
    content_extraction: Optional[ContentExtractionConfig] = None
    chunk: Optional[ChunkParamUpdateForm] = None
    youtube: Optional[YoutubeLoaderConfig] = None
    web: Optional[WebConfig] = None


@app.post("/config/update")
async def update_rag_config(form_data: ConfigUpdateForm, user=Depends(get_admin_user)):
    app.state.config.PDF_EXTRACT_IMAGES = (
        form_data.pdf_extract_images
        if form_data.pdf_extract_images is not None
        else app.state.config.PDF_EXTRACT_IMAGES
    )

    if form_data.file is not None:
        app.state.config.FILE_MAX_SIZE = form_data.file.max_size
        app.state.config.FILE_MAX_COUNT = form_data.file.max_count

    if form_data.content_extraction is not None:
        log.info(f"Updating text settings: {form_data.content_extraction}")
        app.state.config.CONTENT_EXTRACTION_ENGINE = form_data.content_extraction.engine
        app.state.config.TIKA_SERVER_URL = form_data.content_extraction.tika_server_url

    if form_data.chunk is not None:
        app.state.config.TEXT_SPLITTER = form_data.chunk.text_splitter
        app.state.config.CHUNK_SIZE = form_data.chunk.chunk_size
        app.state.config.CHUNK_OVERLAP = form_data.chunk.chunk_overlap

    if form_data.youtube is not None:
        app.state.config.YOUTUBE_LOADER_LANGUAGE = form_data.youtube.language
        app.state.YOUTUBE_LOADER_TRANSLATION = form_data.youtube.translation

    if form_data.web is not None:
        app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION = (
            form_data.web.web_loader_ssl_verification
        )

        app.state.config.ENABLE_RAG_WEB_SEARCH = form_data.web.search.enabled
        app.state.config.RAG_WEB_SEARCH_ENGINE = form_data.web.search.engine
        app.state.config.SEARXNG_QUERY_URL = form_data.web.search.searxng_query_url
        app.state.config.GOOGLE_PSE_API_KEY = form_data.web.search.google_pse_api_key
        app.state.config.GOOGLE_PSE_ENGINE_ID = (
            form_data.web.search.google_pse_engine_id
        )
        app.state.config.BRAVE_SEARCH_API_KEY = (
            form_data.web.search.brave_search_api_key
        )
        app.state.config.SERPSTACK_API_KEY = form_data.web.search.serpstack_api_key
        app.state.config.SERPSTACK_HTTPS = form_data.web.search.serpstack_https
        app.state.config.SERPER_API_KEY = form_data.web.search.serper_api_key
        app.state.config.SERPLY_API_KEY = form_data.web.search.serply_api_key
        app.state.config.TAVILY_API_KEY = form_data.web.search.tavily_api_key
        app.state.config.SEARCHAPI_API_KEY = form_data.web.search.searchapi_api_key
        app.state.config.SEARCHAPI_ENGINE = form_data.web.search.searchapi_engine
        app.state.config.RAG_WEB_SEARCH_RESULT_COUNT = form_data.web.search.result_count
        app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS = (
            form_data.web.search.concurrent_requests
        )

    return {
        "status": True,
        "pdf_extract_images": app.state.config.PDF_EXTRACT_IMAGES,
        "file": {
            "max_size": app.state.config.FILE_MAX_SIZE,
            "max_count": app.state.config.FILE_MAX_COUNT,
        },
        "content_extraction": {
            "engine": app.state.config.CONTENT_EXTRACTION_ENGINE,
            "tika_server_url": app.state.config.TIKA_SERVER_URL,
        },
        "chunk": {
            "text_splitter": app.state.config.TEXT_SPLITTER,
            "chunk_size": app.state.config.CHUNK_SIZE,
            "chunk_overlap": app.state.config.CHUNK_OVERLAP,
        },
        "youtube": {
            "language": app.state.config.YOUTUBE_LOADER_LANGUAGE,
            "translation": app.state.YOUTUBE_LOADER_TRANSLATION,
        },
        "web": {
            "ssl_verification": app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
            "search": {
                "enabled": app.state.config.ENABLE_RAG_WEB_SEARCH,
                "engine": app.state.config.RAG_WEB_SEARCH_ENGINE,
                "searxng_query_url": app.state.config.SEARXNG_QUERY_URL,
                "google_pse_api_key": app.state.config.GOOGLE_PSE_API_KEY,
                "google_pse_engine_id": app.state.config.GOOGLE_PSE_ENGINE_ID,
                "brave_search_api_key": app.state.config.BRAVE_SEARCH_API_KEY,
                "serpstack_api_key": app.state.config.SERPSTACK_API_KEY,
                "serpstack_https": app.state.config.SERPSTACK_HTTPS,
                "serper_api_key": app.state.config.SERPER_API_KEY,
                "serply_api_key": app.state.config.SERPLY_API_KEY,
                "serachapi_api_key": app.state.config.SEARCHAPI_API_KEY,
                "searchapi_engine": app.state.config.SEARCHAPI_ENGINE,
                "tavily_api_key": app.state.config.TAVILY_API_KEY,
                "result_count": app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                "concurrent_requests": app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
            },
        },
    }


@app.get("/template")
async def get_rag_template(user=Depends(get_verified_user)):
    return {
        "status": True,
        "template": app.state.config.RAG_TEMPLATE,
    }


@app.get("/query/settings")
async def get_query_settings(user=Depends(get_admin_user)):
    return {
        "status": True,
        "template": app.state.config.RAG_TEMPLATE,
        "k": app.state.config.TOP_K,
        "r": app.state.config.RELEVANCE_THRESHOLD,
        "hybrid": app.state.config.ENABLE_RAG_HYBRID_SEARCH,
    }


class QuerySettingsForm(BaseModel):
    k: Optional[int] = None
    r: Optional[float] = None
    template: Optional[str] = None
    hybrid: Optional[bool] = None


@app.post("/query/settings/update")
async def update_query_settings(
    form_data: QuerySettingsForm, user=Depends(get_admin_user)
):
    app.state.config.RAG_TEMPLATE = form_data.template
    app.state.config.TOP_K = form_data.k if form_data.k else 4
    app.state.config.RELEVANCE_THRESHOLD = form_data.r if form_data.r else 0.0

    app.state.config.ENABLE_RAG_HYBRID_SEARCH = (
        form_data.hybrid if form_data.hybrid else False
    )

    return {
        "status": True,
        "template": app.state.config.RAG_TEMPLATE,
        "k": app.state.config.TOP_K,
        "r": app.state.config.RELEVANCE_THRESHOLD,
        "hybrid": app.state.config.ENABLE_RAG_HYBRID_SEARCH,
    }


####################################
#
# Document process and retrieval
#
####################################


def save_docs_to_vector_db(
    docs,
    collection_name,
    metadata: Optional[dict] = None,
    overwrite: bool = False,
    split: bool = True,
    add: bool = False,
) -> bool:
    log.info(f"save_docs_to_vector_db {docs} {collection_name}")

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

    if split:
        if app.state.config.TEXT_SPLITTER in ["", "character"]:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=app.state.config.CHUNK_SIZE,
                chunk_overlap=app.state.config.CHUNK_OVERLAP,
                add_start_index=True,
            )
        elif app.state.config.TEXT_SPLITTER == "token":
            text_splitter = TokenTextSplitter(
                encoding_name=app.state.config.TIKTOKEN_ENCODING_NAME,
                chunk_size=app.state.config.CHUNK_SIZE,
                chunk_overlap=app.state.config.CHUNK_OVERLAP,
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
                    "engine": app.state.config.RAG_EMBEDDING_ENGINE,
                    "model": app.state.config.RAG_EMBEDDING_MODEL,
                }
            ),
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
            app.state.config.RAG_EMBEDDING_ENGINE,
            app.state.config.RAG_EMBEDDING_MODEL,
            app.state.sentence_transformer_ef,
            app.state.config.OPENAI_API_KEY,
            app.state.config.OPENAI_API_BASE_URL,
            app.state.config.RAG_EMBEDDING_BATCH_SIZE,
        )

        embeddings = embedding_function(
            list(map(lambda x: x.replace("\n", " "), texts))
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
        return False


class ProcessFileForm(BaseModel):
    file_id: str
    content: Optional[str] = None
    collection_name: Optional[str] = None


@app.post("/process/file")
def process_file(
    form_data: ProcessFileForm,
    user=Depends(get_verified_user),
):
    try:
        file = Files.get_file_by_id(form_data.file_id)

        collection_name = form_data.collection_name

        if collection_name is None:
            collection_name = f"file-{file.id}"

        if form_data.content:
            # Update the content in the file
            # Usage: /files/{file_id}/data/content/update

            VECTOR_DB_CLIENT.delete(
                collection_name=f"file-{file.id}",
                filter={"file_id": file.id},
            )

            docs = [
                Document(
                    page_content=form_data.content,
                    metadata={
                        "name": file.meta.get("name", file.filename),
                        "created_by": file.user_id,
                        "file_id": file.id,
                        **file.meta,
                    },
                )
            ]

            text_content = form_data.content
        elif form_data.collection_name:
            # Check if the file has already been processed and save the content
            # Usage: /knowledge/{id}/file/add, /knowledge/{id}/file/update

            result = VECTOR_DB_CLIENT.query(
                collection_name=f"file-{file.id}", filter={"file_id": file.id}
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
                        page_content=file.data.get("content", ""),
                        metadata={
                            "name": file.meta.get("name", file.filename),
                            "created_by": file.user_id,
                            "file_id": file.id,
                            **file.meta,
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
                    engine=app.state.config.CONTENT_EXTRACTION_ENGINE,
                    TIKA_SERVER_URL=app.state.config.TIKA_SERVER_URL,
                    PDF_EXTRACT_IMAGES=app.state.config.PDF_EXTRACT_IMAGES,
                )
                docs = loader.load(
                    file.filename, file.meta.get("content_type"), file_path
                )
            else:
                docs = [
                    Document(
                        page_content=file.data.get("content", ""),
                        metadata={
                            "name": file.filename,
                            "created_by": file.user_id,
                            "file_id": file.id,
                            **file.meta,
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
                docs=docs,
                collection_name=collection_name,
                metadata={
                    "file_id": file.id,
                    "name": file.meta.get("name", file.filename),
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
                    "filename": file.meta.get("name", file.filename),
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


@app.post("/process/text")
def process_text(
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

    result = save_docs_to_vector_db(docs, collection_name)

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


@app.post("/process/youtube")
def process_youtube_video(form_data: ProcessUrlForm, user=Depends(get_verified_user)):
    try:
        collection_name = form_data.collection_name
        if not collection_name:
            collection_name = calculate_sha256_string(form_data.url)[:63]

        loader = YoutubeLoader.from_youtube_url(
            form_data.url,
            add_video_info=True,
            language=app.state.config.YOUTUBE_LOADER_LANGUAGE,
            translation=app.state.YOUTUBE_LOADER_TRANSLATION,
        )
        docs = loader.load()
        content = " ".join([doc.page_content for doc in docs])
        log.debug(f"text_content: {content}")
        save_docs_to_vector_db(docs, collection_name, overwrite=True)

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


@app.post("/process/web")
def process_web(form_data: ProcessUrlForm, user=Depends(get_verified_user)):
    try:
        collection_name = form_data.collection_name
        if not collection_name:
            collection_name = calculate_sha256_string(form_data.url)[:63]

        loader = get_web_loader(
            form_data.url,
            verify_ssl=app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
            requests_per_second=app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
        )
        docs = loader.load()
        content = " ".join([doc.page_content for doc in docs])
        log.debug(f"text_content: {content}")
        save_docs_to_vector_db(docs, collection_name, overwrite=True)

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


def search_web(engine: str, query: str) -> list[SearchResult]:
    """Search the web using a search engine and return the results as a list of SearchResult objects.
    Will look for a search engine API key in environment variables in the following order:
    - SEARXNG_QUERY_URL
    - GOOGLE_PSE_API_KEY + GOOGLE_PSE_ENGINE_ID
    - BRAVE_SEARCH_API_KEY
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
        if app.state.config.SEARXNG_QUERY_URL:
            return search_searxng(
                app.state.config.SEARXNG_QUERY_URL,
                query,
                app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SEARXNG_QUERY_URL found in environment variables")
    elif engine == "google_pse":
        if (
            app.state.config.GOOGLE_PSE_API_KEY
            and app.state.config.GOOGLE_PSE_ENGINE_ID
        ):
            return search_google_pse(
                app.state.config.GOOGLE_PSE_API_KEY,
                app.state.config.GOOGLE_PSE_ENGINE_ID,
                query,
                app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception(
                "No GOOGLE_PSE_API_KEY or GOOGLE_PSE_ENGINE_ID found in environment variables"
            )
    elif engine == "brave":
        if app.state.config.BRAVE_SEARCH_API_KEY:
            return search_brave(
                app.state.config.BRAVE_SEARCH_API_KEY,
                query,
                app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No BRAVE_SEARCH_API_KEY found in environment variables")
    elif engine == "serpstack":
        if app.state.config.SERPSTACK_API_KEY:
            return search_serpstack(
                app.state.config.SERPSTACK_API_KEY,
                query,
                app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
                https_enabled=app.state.config.SERPSTACK_HTTPS,
            )
        else:
            raise Exception("No SERPSTACK_API_KEY found in environment variables")
    elif engine == "serper":
        if app.state.config.SERPER_API_KEY:
            return search_serper(
                app.state.config.SERPER_API_KEY,
                query,
                app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SERPER_API_KEY found in environment variables")
    elif engine == "serply":
        if app.state.config.SERPLY_API_KEY:
            return search_serply(
                app.state.config.SERPLY_API_KEY,
                query,
                app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SERPLY_API_KEY found in environment variables")
    elif engine == "duckduckgo":
        return search_duckduckgo(
            query,
            app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
            app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
        )
    elif engine == "tavily":
        if app.state.config.TAVILY_API_KEY:
            return search_tavily(
                app.state.config.TAVILY_API_KEY,
                query,
                app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
            )
        else:
            raise Exception("No TAVILY_API_KEY found in environment variables")
    elif engine == "searchapi":
        if app.state.config.SEARCHAPI_API_KEY:
            return search_searchapi(
                app.state.config.SEARCHAPI_API_KEY,
                app.state.config.SEARCHAPI_ENGINE,
                query,
                app.state.config.RAG_WEB_SEARCH_RESULT_COUNT,
                app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
            )
        else:
            raise Exception("No SEARCHAPI_API_KEY found in environment variables")
    elif engine == "jina":
        return search_jina(query, app.state.config.RAG_WEB_SEARCH_RESULT_COUNT)
    else:
        raise Exception("No search engine API key found in environment variables")


@app.post("/process/web/search")
def process_web_search(form_data: SearchForm, user=Depends(get_verified_user)):
    try:
        logging.info(
            f"trying to web search with {app.state.config.RAG_WEB_SEARCH_ENGINE, form_data.query}"
        )
        web_results = search_web(
            app.state.config.RAG_WEB_SEARCH_ENGINE, form_data.query
        )
    except Exception as e:
        log.exception(e)

        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.WEB_SEARCH_ERROR(e),
        )

    try:
        collection_name = form_data.collection_name
        if collection_name == "":
            collection_name = calculate_sha256_string(form_data.query)[:63]

        urls = [result.link for result in web_results]

        loader = get_web_loader(urls)
        docs = loader.load()

        save_docs_to_vector_db(docs, collection_name, overwrite=True)

        return {
            "status": True,
            "collection_name": collection_name,
            "filenames": urls,
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


@app.post("/query/doc")
def query_doc_handler(
    form_data: QueryDocForm,
    user=Depends(get_verified_user),
):
    try:
        if app.state.config.ENABLE_RAG_HYBRID_SEARCH:
            return query_doc_with_hybrid_search(
                collection_name=form_data.collection_name,
                query=form_data.query,
                embedding_function=app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else app.state.config.TOP_K,
                reranking_function=app.state.sentence_transformer_rf,
                r=(
                    form_data.r if form_data.r else app.state.config.RELEVANCE_THRESHOLD
                ),
            )
        else:
            return query_doc(
                collection_name=form_data.collection_name,
                query=form_data.query,
                embedding_function=app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else app.state.config.TOP_K,
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


@app.post("/query/collection")
def query_collection_handler(
    form_data: QueryCollectionsForm,
    user=Depends(get_verified_user),
):
    try:
        if app.state.config.ENABLE_RAG_HYBRID_SEARCH:
            return query_collection_with_hybrid_search(
                collection_names=form_data.collection_names,
                query=form_data.query,
                embedding_function=app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else app.state.config.TOP_K,
                reranking_function=app.state.sentence_transformer_rf,
                r=(
                    form_data.r if form_data.r else app.state.config.RELEVANCE_THRESHOLD
                ),
            )
        else:
            return query_collection(
                collection_names=form_data.collection_names,
                query=form_data.query,
                embedding_function=app.state.EMBEDDING_FUNCTION,
                k=form_data.k if form_data.k else app.state.config.TOP_K,
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


@app.post("/delete")
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


@app.post("/reset/db")
def reset_vector_db(user=Depends(get_admin_user)):
    VECTOR_DB_CLIENT.reset()
    Knowledges.delete_all_knowledge()


@app.post("/reset/uploads")
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

    @app.get("/ef")
    async def get_embeddings():
        return {"result": app.state.EMBEDDING_FUNCTION("hello world")}

    @app.get("/ef/{text}")
    async def get_embeddings_text(text: str):
        return {"result": app.state.EMBEDDING_FUNCTION(text)}
