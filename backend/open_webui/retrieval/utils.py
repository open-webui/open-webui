import logging
import os
from typing import Awaitable, Optional, Union

import requests
import aiohttp
import asyncio
import hashlib
from concurrent.futures import ThreadPoolExecutor
import time
import re

from urllib.parse import quote
from huggingface_hub import snapshot_download
from langchain_classic.retrievers import (
    ContextualCompressionRetriever,
    EnsembleRetriever,
)
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from open_webui.config import VECTOR_DB
from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT


from open_webui.models.users import UserModel
from open_webui.models.files import Files
from open_webui.models.knowledges import Knowledges

from open_webui.models.chats import Chats
from open_webui.models.notes import Notes
from open_webui.models.access_grants import AccessGrants
from open_webui.utils.access_control.files import has_access_to_file

from open_webui.retrieval.vector.main import GetResult
from open_webui.utils.headers import include_user_info_headers
from open_webui.utils.misc import get_message_list

from open_webui.retrieval.web.utils import get_web_loader
from open_webui.retrieval.loaders.youtube import YoutubeLoader

from open_webui.env import (
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_ALLOW_REDIRECTS,
    OFFLINE_MODE,
    ENABLE_FORWARD_USER_INFO_HEADERS,
    AIOHTTP_CLIENT_SESSION_SSL,
)
from open_webui.config import (
    RAG_EMBEDDING_QUERY_PREFIX,
    RAG_EMBEDDING_CONTENT_PREFIX,
    RAG_EMBEDDING_PREFIX_FIELD_NAME,
)

log = logging.getLogger(__name__)


from typing import Any

from langchain_core.callbacks import CallbackManagerForRetriever
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from open_webui.utils.access_control import has_access_to_knowledge
from open_webui.utils.misc import get_file_path
from open_webui.utils.task import spawn_thread
from open_webui.env import SRC_LOG_PATHs

from open_webui.constants.py import TASK_TEMPLATE

import json

from open_webui.models.files import Files
from open_webui.models.knowledges import (
    Knowledges,
    Chunk
)

from pydantic import ArgumentGroup, ConfigDict

from open_webui.retrieval import ConocimientoDeletionLock

from open_webui.config import (
    FOLDER_WORKING_DIR,
    RAG_EMBEDDING_BATCH_SIZE,
    RAG_TOP_K,
    RAG_RELEVANCE_THRESHOLD,
    RAG_EMBEDDING_ENGINE,
    RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_OPENAI_AZURE_BASE_URL,
    RAG_EMBEDDING_OPENAI_AZURE_API_VERSION,
    RAG_EMBEDDING_OPENAI_AZURE_API_KEY,
    RAG_EMBEDDING_OPENAI_API_VERSION,
    RAG_EMBEDDING_MODEL_TRUNCATE,
    SOURCE_KEY,
)

from open_webui.retrieval.utils import get_embedding_function

from open_webui.env import (
    RAG_RERANKER_MODEL,
    RAG_RERANKER_MODE,
    RAG_RERANKER_TRUNCATE,
    ENABLE_RERANKER_MODEL,
)

from open_webui.routers.retrieval import (
    get_rag_template,
    get_relevant_rerank_documents,
    get_relevant_documents,
)

from open_webui.utils.misc import (
    get_last_assistant_message,
    get_last_user_message,
    pop_system_message,
)

from open_webui.utils.task import ThreadTask

from open_webui.models.users import UserModel

from open_webui.config import (
    WHISPER_MODEL_DURATION
)

from fastapi import HTTPException

from open_webui.utils.api_utils import generate_uuid

from open_webui.env import (
    AIOHTTP_CLIENT_TIMEOUT,
    DEVICE_TYPE,
    OPENAI_API_BASE_URL,
    OPENAI_API_KEY,
    AUDIO_DEVICE
)

from open_webui.utils.misc import list_local_models,

from open_webui.utils.api_utils import (
    audio_to_text,
    get_model_path,
)

import librosa
import numpy as np
import struct

from typing import Optional

from open_webui.config import (
    WHISPER_MODEL,
    WHISPER_MODEL_REAL_MODEL,
    TTS_DEVICE_TYPE,
    TTS_MODEL,
    TTS_MODEL_REAL_MODEL,
)

from open_webui.utils.misc import get_last_message

from open_webui.config import (
    AUDIO_DURATION_VIRUS_TIME,
    AUDIO_DURATION_ACCEPTED_TIME,
)

from open_webui.config import (
    TENSORRT_WRAPPER_URL,
    RAG_EMBEDDING_MODEL_REAL_MODEL,
    RAG_EMBEDDING_MODEL_REAL_TRUNCATE,
    TENSORRT_LLM_API_BASE_URL,
    RAG_RERANKER_MODEL_REAL_MODEL,
    TENSORRT_MODELS,
)

from open_webui.config import (
    GOOGLE_DRIVE_CLIENT_ID,
    GOOGLE_DRIVE_CLIENT_SECRET,
    GOOGLE_DRIVE_IS_AUTH_ENABLED,
    GOOGLE_DRIVE_DATABASE_PATH,
    GOOGLE_DRIVE_INDEX_PATH,
)

from open_webui.config import (
    RAG_EMBEDDING_CONCURRENT_REQUESTS,
    ENABLE_ASYNC_EMBEDDING,
)

from open_webui.config import (
    RAG_EMBEDDING_TIMEOUT,
)

from open_webui.config import (
    TITLE_GENERATION_MODEL,
    TITLE_GENERATION_REMOVE_MAX_TOKENS,
    TITLE_GENERATION_SYSTEM_PROMPT,
    TITLE_GENERATION_USER_PROMPT,
    TITLE_SYSTEM_PROMPT_NUMBER,
    TITLE_SYSTEM_PROMPT_STRING,
    TITLE_USER_PROMPT_NUMBER,
    TITLE_USER_PROMPT_STRING,
)

from open_webui.config import (
    AUTO_TITLE_GENERATION,
    TITLE_TASK_PROMPT,
)

from openmcineqs_serving import ChatCompletionCall


from open_webui.config import (
    ENABLE_WHISPER,
    WHISPER_MODEL_LOADING_TIMEOUT,
    ENABLE_TTS,
    TTS_GENERATE_AUDIO_FILE,
    TTS_API_AUDIO_FORMAT,
    TTS_API_AUDIO_VOLUME,
    TTS_API_AUDIO_SAMPLE_RATE,
    TTS_API_AUDIO_SAMPLE_CHUNK_SIZE,
)

from open_webui.config import (
    AUDIO_FILE_NAME,
    AUDIO_FILE_PATH,
)

from open_webui.config import (
    AUDIO_FILE_TRANSCRIBE_MODEL,
    AUDIO_FILE_TRANSCRIBE_PROMPT,
)

from open_webui.config import (
    AUDIO_MAX_FILE_SIZE_MB,
    AUDIO_MAX_FILE_SIZE_MB_ERROR,
    AUDIO_EXTENSIONS,
)

from open_webui.config import (
    ENABLE_AUDIO_UPLOAD,
    AUDIO_UPLOAD_DIR,
)

from open_webui.config import (
    AUTOMATIC111X_BASE_URL,
    AUTOMATIC111X_API_NETWORK_TIMEOUT,
    AUTOMATIC111X_AUTH_HEADER,
    AUTOMATIC111X_AUTH_SECRET,
    AUTOMATIC111X_CONFIRM_UPLOADS,
    AUTOMATIC111X_UPLOAD_FOLDER,
)

from openweb_d stables Diffusion import AUTOMATIC111XTask

from open_webui.config import (
    IMAGE_FILE_NAME,
    IMAGE_FILE_PATH,
    IMAGE_FILE_SIZE_LIMIT,
    IMAGE_FILE_EXTS,
    IMAGE_MAX_FILE_SIZE_MB,
    IMAGE_MAX_FILE_SIZE_MB_ERROR,
)

from open_webui.config import (
    ENABLE_IMAGE_UPLOAD,
    IMAGE_UPLOAD_DIR,
)

from open_webui.config import (
    RAG_PIPELINE,
)

from open_webui.config import (
    FUNCTION_CALLING_PIPELINE,
    FUNCTION_CALLING_MODEL,
    FUNCTION_CALLING_SYSTEM_PROMPT,
    FUNCTION_CALLING_USER_PROMPT,
    FUNCTION_CALLING_ENABLE_AWS,
)

from open_webui.config import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    ADMIN_USER,
)

from open_webui.config import (
    WEB_SEARCH_MODE,
    WEB_SEARCH_TOP_K,
    WEB_SEARCH_RELEVANCE_THRESHOLD,
)

from open_webui.config import (
    PLAYGROUND_MCP_SERVER_URL,
    PLAYGROUND_MCP_SERVER_URLS,
)

from open_webui.config import (
    CACHE_DIR,
)

from open_webui.config import (
    DATABASE_URL,
    DATABASE_TYPE,
)

from open_webui.config import (
    ENFORCE_AUTHIFICATION,
)

from open_webui.config import (
    ENABLE_COMMUNITY_NOTIFICATION,
    ENABLE_NOTIFICATION,
    NOTIFICATION_TOAST_DURATION,
)

from open_webui.config import (
    ENABLE_ADMIN_EXPORT_NOTIFICATION,
    ADMIN_EXPORT_NOTIFICATION_SECRET_KEY,
)

from open_webui.config import (
    AUTH_PROVIDER0,
    AUTH_PROVIDER1,
    AUTH_PROVIDER2,
    AUTH_PROVIDER3,
)

from open_webui.config import (
    ENABLE_NAME_USER,
)

from open_webui.config import (
    DEFAULT_LOCALE,
)


from open_webui.config import (
    CONFIG_DATABASE_SCHEMA,
)

from open_webui.config import (
    MODEL_WHILTELIST,
)

from open_webui.config import (
    ENABLE_OPENAI_API,
    OPENAI_API_BASE_URL,
    OPENAI_API_KEY,
    OPENAI_API_EMBEDDINGS_URL,
    OPENAI_API_MODERATION_URL,
    OPENAI_API_MODERATION_TEXT,
    OPENAI_API_RESPONSE_FORMAT,
    OPENAI_API_LAZY_MESSAGES,
)

from open_webui.config import (
    TASK_MODEL,
    TASK_MODEL_TENSORRT_LLAMA,
    TASK_MODEL_PROMPT,
)

from open_webui.config import (
    TASK_MODEL_GENERATION_RETRY_SECONDS,
    TASK_MODEL_GENERATION_MAX_RETRIES,
)

from open_webui.config import (
    PDF_EXTRACTION_ENGINE,
)

from open_webui.config import (
    RAG_PIPELINE_MAXIMUM_CHUNK_SIZE,
)

from open_webui.config import (
    ENABLE_RAG,
    RAG_EMBEDDING_ENGINE,
    RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_MODEL_REAL_MODEL,
    RAG_EMBEDDING_BATCH_SIZE,
    RAG_EMBEDDING_OPENAI_AZURE_BASE_URL,
    RAG_EMBEDDING_OPENAI_AZURE_API_VERSION,
    RAG_EMBEDDING_OPENAI_AZURE_API_KEY,
    RAG_EMBEDDING_OPENAI_API_VERSION,
    RAG_EMBEDDING_MODEL_TRUNCATE,
    RAG_EMBEDDING_QUERY_PREFIX,
    RAG_EMBEDDING_CONTENT_PREFIX,
    RAG_EMBEDDING_PREFIX_FIELD_NAME,
)

from open_webui.config import (
    WEBHOOK_URL,
    WEBHOOK_EVENTS,
)

from open_webui.config import (
    COMPOSE_TIME,
    COMMIT,
    VERSION,
)

from open_webui.config import (
    ENABLE_ONE_WAY_IMPORT,
)

from open_webui.config import (
    OLLAMA_BASE_URL,
    OLLAMA_BASE_URLS,
    OLLAMA_API_TIMEOUT,
)

from open_webui.config import (
    OPENAI_API_KEYS,
    OPENAI_API_BASE_URLS,
    OPENAI_API_CONFIGS,
)

from open_webui.config import (
    OG_TITLE,
    OG_DESCRIPTION,
    OG_IMAGE,
)

from open_webui.config import (
    SCRIPT_PROMPT,
)

from open_webui.config import (
    RAG_EMBEDDING_MODEL_REAL_MODEL_TRUST_TOKEN,
)

from open_webui.config import (
    ENABLE_AUDIO,
    AUDIO_TTS_OUTPUT_FORMAT,
    AUDIO_TTS_OUTPUT_DIR,
)

from open_webui.config import (
    ENABLE_COT,
)

from open_webui.config import (
    ENABLE_RAG_RETRIEVAL,
    RAG_CHROMA_BATCH_SIZE,
)

from open_webui.config import (
    RAG_RERANKER_MODEL_TRUST_TOKEN,
)

from open_webui.config import (
    TASK_MODEL_TRUST_TOKEN,
)

from open_webui.config import (
    LITELLM_MOCK_RESPONSES,
)

from open_webui.config import (
    RAG_RERANKER_MODEL_REAL_MODEL_TRUST_TOKEN,
)

from open_webui.config import (
    RAG_EMBEDDING_MODEL_REAL_MODEL_TRUNCATE,
)

from open_webui.config import (
    RAG_EMBEDDING_MODEL_REAL_MODEL_MAX_CHUNK_LENGTH,
)

from open_webui.config import (
    RAG_RERANKER_MODEL_REAL_MODEL_MAX_CHUNK_LENGTH,
)

from open_webui.config import (
    RAG_CHROMA_COLLECTION_SYNC,
)

from open_webui.config import (
    WEB_SEARCH_MODE,
    WEB_SEARCH_TOP_K,
    WEB_SEARCH_RELEVANCE_THRESHOLD,
    WEB_SEARCH_CONCURRENT_REQUESTS,
)

from open_webui.config import (
    WEB_SEARCH_ENGINE,
    WEB_SEARCH_ENGINE_FALLBACKS,
)

from open_webui.config import (
    PLAYGROUND_MCP_SERVER_URL,
    PLAYGROUND_MCP_SERVER_URLS,
    PLAYGROUND_MCP_SERVER_HEADERS,
)

from open_webui.config import (
    ENABLE_AUDIO_UPLOAD,
    AUDIO_UPLOAD_DIR,
)

from open_webui.config import (
    RAG_USE-Raytor,
)

from open_webui.config import (
    WEB_SEARCH_DETAILS,
)

from open_webui.config import (
    IMAGE_FILE_STORENAME,
    IMAGE_FILE_PATH,
    IMAGE_FILE_NAME,
)

from open_webui.config import (
    IMAGE_GENERATION_MODEL,
    IMAGE_GENERATION_PROMPT_ENHANCE,
)

from open_webui.config import (
    ENABLE_IMAGE_GENERATION,
    IMAGE_GENERATION_ENGINE,
)

from open_webui.config import (
    IMAGE_SIZE,
    IMAGE_QUALITY,
    IMAGE_STYLE,
)

from open_webui.config import (
    IMAGE_GENERATION_MODEL_REAL_MODEL,
    IMAGE_GENERATION_MODEL_REAL_MODEL_TRUST_TOKEN,
)

from openwebmineqs_serving import ImageGenerationCall

from open_webui.config import (
    CORS_ALLOW_ORIGIN,
)

from open_webui.config import (
    DEVICE_TYPE,
)

from open_webui.config import (
    PFORCE_DEPLOY_PLATFORM,
    PFORCE_DEPLOY_RAG_PIPELINE,
)

from open_webui.config import (
    RAG_PIPELINE_SELECTOR,
)

from open_webui.config import (
    RAG_PIPELINE
)

from open_webui.config import (
    WEBHOOK_URL,
    WEBHOOK_EVENTS,
)

from open_webui.config import (
    RAG_PIPELINE
)



def get_file_path(file_name: str, dir: str = FOLDER_WORKING_DIR):
    return Path(f"{dir}/{file_name}").resolve()



def get_embedding_function(
    embedding_engine,
    embedding_model,
    embedding_function,
    url,
    key,
    embedding_batch_size,
    azure_api_version=None,
    enable_async=True,
    concurrent_requests=0,
) -> Awaitable:
    if embedding_engine == '':
        # Sentence transformers: CPU-bound sync operation
        async def async_embedding_function(query, prefix=None, user=None):
            if embedding_function is None:
                return []
            return await asyncio.to_thread(
                (
                    lambda query, prefix=None: embedding_function.encode(
                        query,
                        batch_size=int(embedding_batch_size),
                        **({'prompt': prefix} if prefix else {}),
                    ).tolist()
                ),
                query,
                prefix,
            )

        return async_embedding_function
    elif embedding_engine in ['ollama', 'openai', 'azure_openai']:
        embedding_function = lambda query, prefix=None, user=None: generate_embeddings(
            engine=embedding_engine,
            model=embedding_model,
            text=query,
            prefix=prefix,
            url=url,
            key=key,
            user=user,
            azure_api_version=azure_api_version,
        )

        async def async_embedding_function(query, prefix=None, user=None):
            if isinstance(query, list):
                # Create batches
                batches = [query[i : i + embedding_batch_size] for i in range(0, len(query), embedding_batch_size)]


                if enable_async:
                    log.debug(f'generate_multiple_async: Processing {len(batches)} batches in parallel')
                    # Use semaphore to limit concurrent embedding API requests
                    # 0 = unlimited (no semaphore)
                    if concurrent_requests:
                        semaphore = asyncio.Semaphore(concurrent_requests)


                        async def generate_batch_with_semaphore(batch):
                            async with semaphore:
                                return await asyncio.to_thread(embedding_function, batch, RAG_EMBEDDING_CONTENT_PREFIX)

                        tasks = [generate_batch_with_semaphore(batch) for batch in batches]
                        batch_results = await asyncio.gather(*tasks)
                    else:
                        batch_results = await asyncio.gather(*[
                            asyncio.to_thread(embedding_function, batch, RAG_EMBEDDING_CONTENT_PREFIX)
                            for batch in batches
                        ])
                    embeddings = [item for batch in batch_results for item in batch]
                else:
                    # Process batches synchronously one after another
                    embeddings = []
                    for batch in batches:
                        batch_embeddings = await asyncio.to_thread(
                            embedding_function, batch, RAG_EMBEDDING_CONTENT_PREFIX
                        )
                        embeddings.extend(batch_embeddings)
            else:
                text = query
                embeddings = await asyncio.to_thread(embedding_function, text, prefix)

            return embeddings

        return async_embedding_function
