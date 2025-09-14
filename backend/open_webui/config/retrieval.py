import os
import json

from open_webui.config.base import PersistentConfig
from open_webui.config.llm import (
    OPENAI_API_BASE_URL,
    OPENAI_API_KEY,
    OLLAMA_BASE_URL,
)

from open_webui.env import (
    CACHE_DIR,
    OFFLINE_MODE,
    log,
)

####################################
# Cloud Storage Integration
####################################

# Google Drive Integration
ENABLE_GOOGLE_DRIVE_INTEGRATION = PersistentConfig(
    "ENABLE_GOOGLE_DRIVE_INTEGRATION",
    "google_drive.enable",
    os.getenv("ENABLE_GOOGLE_DRIVE_INTEGRATION", "False").lower() == "true",
)

GOOGLE_DRIVE_CLIENT_ID = PersistentConfig(
    "GOOGLE_DRIVE_CLIENT_ID",
    "google_drive.client_id",
    os.environ.get("GOOGLE_DRIVE_CLIENT_ID", ""),
)

GOOGLE_DRIVE_API_KEY = PersistentConfig(
    "GOOGLE_DRIVE_API_KEY",
    "google_drive.api_key",
    os.environ.get("GOOGLE_DRIVE_API_KEY", ""),
)

# OneDrive Integration
ENABLE_ONEDRIVE_INTEGRATION = PersistentConfig(
    "ENABLE_ONEDRIVE_INTEGRATION",
    "onedrive.enable",
    os.getenv("ENABLE_ONEDRIVE_INTEGRATION", "False").lower() == "true",
)

ONEDRIVE_CLIENT_ID = PersistentConfig(
    "ONEDRIVE_CLIENT_ID",
    "onedrive.client_id",
    os.environ.get("ONEDRIVE_CLIENT_ID", ""),
)

ONEDRIVE_SHAREPOINT_URL = PersistentConfig(
    "ONEDRIVE_SHAREPOINT_URL",
    "onedrive.sharepoint_url",
    os.environ.get("ONEDRIVE_SHAREPOINT_URL", ""),
)

ONEDRIVE_SHAREPOINT_TENANT_ID = PersistentConfig(
    "ONEDRIVE_SHAREPOINT_TENANT_ID",
    "onedrive.sharepoint_tenant_id",
    os.environ.get("ONEDRIVE_SHAREPOINT_TENANT_ID", ""),
)

####################################
# Document Content Extraction
####################################
CONTENT_EXTRACTION_ENGINE = PersistentConfig(
    "CONTENT_EXTRACTION_ENGINE",
    "rag.CONTENT_EXTRACTION_ENGINE",
    os.environ.get("CONTENT_EXTRACTION_ENGINE", "").lower(),
)

DATALAB_MARKER_API_KEY = PersistentConfig(
    "DATALAB_MARKER_API_KEY",
    "rag.datalab_marker_api_key",
    os.environ.get("DATALAB_MARKER_API_KEY", ""),
)

DATALAB_MARKER_API_BASE_URL = PersistentConfig(
    "DATALAB_MARKER_API_BASE_URL",
    "rag.datalab_marker_api_base_url",
    os.environ.get("DATALAB_MARKER_API_BASE_URL", ""),
)

DATALAB_MARKER_ADDITIONAL_CONFIG = PersistentConfig(
    "DATALAB_MARKER_ADDITIONAL_CONFIG",
    "rag.datalab_marker_additional_config",
    os.environ.get("DATALAB_MARKER_ADDITIONAL_CONFIG", ""),
)

DATALAB_MARKER_USE_LLM = PersistentConfig(
    "DATALAB_MARKER_USE_LLM",
    "rag.DATALAB_MARKER_USE_LLM",
    os.environ.get("DATALAB_MARKER_USE_LLM", "false").lower() == "true",
)

DATALAB_MARKER_SKIP_CACHE = PersistentConfig(
    "DATALAB_MARKER_SKIP_CACHE",
    "rag.datalab_marker_skip_cache",
    os.environ.get("DATALAB_MARKER_SKIP_CACHE", "false").lower() == "true",
)

DATALAB_MARKER_FORCE_OCR = PersistentConfig(
    "DATALAB_MARKER_FORCE_OCR",
    "rag.datalab_marker_force_ocr",
    os.environ.get("DATALAB_MARKER_FORCE_OCR", "false").lower() == "true",
)

DATALAB_MARKER_PAGINATE = PersistentConfig(
    "DATALAB_MARKER_PAGINATE",
    "rag.datalab_marker_paginate",
    os.environ.get("DATALAB_MARKER_PAGINATE", "false").lower() == "true",
)

DATALAB_MARKER_STRIP_EXISTING_OCR = PersistentConfig(
    "DATALAB_MARKER_STRIP_EXISTING_OCR",
    "rag.datalab_marker_strip_existing_ocr",
    os.environ.get("DATALAB_MARKER_STRIP_EXISTING_OCR", "false").lower() == "true",
)

DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION = PersistentConfig(
    "DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION",
    "rag.datalab_marker_disable_image_extraction",
    os.environ.get("DATALAB_MARKER_DISABLE_IMAGE_EXTRACTION", "false").lower()
    == "true",
)

DATALAB_MARKER_FORMAT_LINES = PersistentConfig(
    "DATALAB_MARKER_FORMAT_LINES",
    "rag.datalab_marker_format_lines",
    os.environ.get("DATALAB_MARKER_FORMAT_LINES", "false").lower() == "true",
)

DATALAB_MARKER_OUTPUT_FORMAT = PersistentConfig(
    "DATALAB_MARKER_OUTPUT_FORMAT",
    "rag.datalab_marker_output_format",
    os.environ.get("DATALAB_MARKER_OUTPUT_FORMAT", "markdown"),
)

# External Document Loaders
EXTERNAL_DOCUMENT_LOADER_URL = PersistentConfig(
    "EXTERNAL_DOCUMENT_LOADER_URL",
    "rag.external_document_loader_url",
    os.environ.get("EXTERNAL_DOCUMENT_LOADER_URL", ""),
)

EXTERNAL_DOCUMENT_LOADER_API_KEY = PersistentConfig(
    "EXTERNAL_DOCUMENT_LOADER_API_KEY",
    "rag.external_document_loader_api_key",
    os.environ.get("EXTERNAL_DOCUMENT_LOADER_API_KEY", ""),
)

# Tika Server (Apache Tika)
TIKA_SERVER_URL = PersistentConfig(
    "TIKA_SERVER_URL",
    "rag.tika_server_url",
    os.getenv("TIKA_SERVER_URL", "http://tika:9998"),  # Default for sidecar deployment
)

# Docling (IBM)
DOCLING_SERVER_URL = PersistentConfig(
    "DOCLING_SERVER_URL",
    "rag.docling_server_url",
    os.getenv("DOCLING_SERVER_URL", "http://docling:5001"),
)

DOCLING_DO_OCR = PersistentConfig(
    "DOCLING_DO_OCR",
    "rag.docling_do_ocr",
    os.getenv("DOCLING_DO_OCR", "True").lower() == "true",
)

DOCLING_FORCE_OCR = PersistentConfig(
    "DOCLING_FORCE_OCR",
    "rag.docling_force_ocr",
    os.getenv("DOCLING_FORCE_OCR", "False").lower() == "true",
)

DOCLING_OCR_ENGINE = PersistentConfig(
    "DOCLING_OCR_ENGINE",
    "rag.docling_ocr_engine",
    os.getenv("DOCLING_OCR_ENGINE", "tesseract"),
)

DOCLING_OCR_LANG = PersistentConfig(
    "DOCLING_OCR_LANG",
    "rag.docling_ocr_lang",
    os.getenv("DOCLING_OCR_LANG", "eng,fra,deu,spa"),
)

DOCLING_PDF_BACKEND = PersistentConfig(
    "DOCLING_PDF_BACKEND",
    "rag.docling_pdf_backend",
    os.getenv("DOCLING_PDF_BACKEND", "dlparse_v4"),
)

DOCLING_TABLE_MODE = PersistentConfig(
    "DOCLING_TABLE_MODE",
    "rag.docling_table_mode",
    os.getenv("DOCLING_TABLE_MODE", "accurate"),
)

DOCLING_PIPELINE = PersistentConfig(
    "DOCLING_PIPELINE",
    "rag.docling_pipeline",
    os.getenv("DOCLING_PIPELINE", "standard"),
)

DOCLING_DO_PICTURE_DESCRIPTION = PersistentConfig(
    "DOCLING_DO_PICTURE_DESCRIPTION",
    "rag.docling_do_picture_description",
    os.getenv("DOCLING_DO_PICTURE_DESCRIPTION", "False").lower() == "true",
)

DOCLING_PICTURE_DESCRIPTION_MODE = PersistentConfig(
    "DOCLING_PICTURE_DESCRIPTION_MODE",
    "rag.docling_picture_description_mode",
    os.getenv("DOCLING_PICTURE_DESCRIPTION_MODE", ""),
)


docling_picture_description_local = os.getenv("DOCLING_PICTURE_DESCRIPTION_LOCAL", "")
try:
    docling_picture_description_local = json.loads(docling_picture_description_local)
except json.JSONDecodeError:
    docling_picture_description_local = {}


DOCLING_PICTURE_DESCRIPTION_LOCAL = PersistentConfig(
    "DOCLING_PICTURE_DESCRIPTION_LOCAL",
    "rag.docling_picture_description_local",
    docling_picture_description_local,
)

docling_picture_description_api = os.getenv("DOCLING_PICTURE_DESCRIPTION_API", "")
try:
    docling_picture_description_api = json.loads(docling_picture_description_api)
except json.JSONDecodeError:
    docling_picture_description_api = {}


DOCLING_PICTURE_DESCRIPTION_API = PersistentConfig(
    "DOCLING_PICTURE_DESCRIPTION_API",
    "rag.docling_picture_description_api",
    docling_picture_description_api,
)

# Azure Document Intelligence
DOCUMENT_INTELLIGENCE_ENDPOINT = PersistentConfig(
    "DOCUMENT_INTELLIGENCE_ENDPOINT",
    "rag.document_intelligence_endpoint",
    os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT", ""),
)

DOCUMENT_INTELLIGENCE_KEY = PersistentConfig(
    "DOCUMENT_INTELLIGENCE_KEY",
    "rag.document_intelligence_key",
    os.getenv("DOCUMENT_INTELLIGENCE_KEY", ""),
)

# Mistral OCR
MISTRAL_OCR_API_KEY = PersistentConfig(
    "MISTRAL_OCR_API_KEY",
    "rag.mistral_ocr_api_key",
    os.getenv("MISTRAL_OCR_API_KEY", ""),
)

####################################
# RAG Core Configuration
####################################

BYPASS_EMBEDDING_AND_RETRIEVAL = PersistentConfig(
    "BYPASS_EMBEDDING_AND_RETRIEVAL",
    "rag.bypass_embedding_and_retrieval",
    os.environ.get("BYPASS_EMBEDDING_AND_RETRIEVAL", "False").lower() == "true",
)

RAG_TOP_K = PersistentConfig(
    "RAG_TOP_K", "rag.top_k", int(os.environ.get("RAG_TOP_K", "3"))
)
RAG_TOP_K_RERANKER = PersistentConfig(
    "RAG_TOP_K_RERANKER",
    "rag.top_k_reranker",
    int(os.environ.get("RAG_TOP_K_RERANKER", "3")),
)
RAG_RELEVANCE_THRESHOLD = PersistentConfig(
    "RAG_RELEVANCE_THRESHOLD",
    "rag.relevance_threshold",
    float(os.environ.get("RAG_RELEVANCE_THRESHOLD", "0.0")),
)
RAG_HYBRID_BM25_WEIGHT = PersistentConfig(
    "RAG_HYBRID_BM25_WEIGHT",
    "rag.hybrid_bm25_weight",
    float(os.environ.get("RAG_HYBRID_BM25_WEIGHT", "0.5")),
)

ENABLE_RAG_HYBRID_SEARCH = PersistentConfig(
    "ENABLE_RAG_HYBRID_SEARCH",
    "rag.enable_hybrid_search",
    os.environ.get("ENABLE_RAG_HYBRID_SEARCH", "").lower() == "true",
)

RAG_FULL_CONTEXT = PersistentConfig(
    "RAG_FULL_CONTEXT",
    "rag.full_context",
    os.getenv("RAG_FULL_CONTEXT", "False").lower() == "true",
)

RAG_FILE_MAX_COUNT = PersistentConfig(
    "RAG_FILE_MAX_COUNT",
    "rag.file.max_count",
    (
        int(os.environ.get("RAG_FILE_MAX_COUNT"))
        if os.environ.get("RAG_FILE_MAX_COUNT")
        else None
    ),
)

RAG_FILE_MAX_SIZE = PersistentConfig(
    "RAG_FILE_MAX_SIZE",
    "rag.file.max_size",
    (
        int(os.environ.get("RAG_FILE_MAX_SIZE"))
        if os.environ.get("RAG_FILE_MAX_SIZE")
        else None
    ),
)

FILE_IMAGE_COMPRESSION_WIDTH = PersistentConfig(
    "FILE_IMAGE_COMPRESSION_WIDTH",
    "file.image_compression_width",
    (
        int(os.environ.get("FILE_IMAGE_COMPRESSION_WIDTH"))
        if os.environ.get("FILE_IMAGE_COMPRESSION_WIDTH")
        else None
    ),
)

FILE_IMAGE_COMPRESSION_HEIGHT = PersistentConfig(
    "FILE_IMAGE_COMPRESSION_HEIGHT",
    "file.image_compression_height",
    (
        int(os.environ.get("FILE_IMAGE_COMPRESSION_HEIGHT"))
        if os.environ.get("FILE_IMAGE_COMPRESSION_HEIGHT")
        else None
    ),
)


RAG_ALLOWED_FILE_EXTENSIONS = PersistentConfig(
    "RAG_ALLOWED_FILE_EXTENSIONS",
    "rag.file.allowed_extensions",
    [
        ext.strip()
        for ext in os.environ.get("RAG_ALLOWED_FILE_EXTENSIONS", "").split(",")
        if ext.strip()
    ],
)

RAG_EMBEDDING_ENGINE = PersistentConfig(
    "RAG_EMBEDDING_ENGINE",
    "rag.embedding_engine",
    os.environ.get("RAG_EMBEDDING_ENGINE", ""),
)

PDF_EXTRACT_IMAGES = PersistentConfig(
    "PDF_EXTRACT_IMAGES",
    "rag.pdf_extract_images",
    os.environ.get("PDF_EXTRACT_IMAGES", "False").lower() == "true",
)

RAG_EMBEDDING_MODEL = PersistentConfig(
    "RAG_EMBEDDING_MODEL",
    "rag.embedding_model",
    os.environ.get("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
)
log.info(f"Embedding model set: {RAG_EMBEDDING_MODEL.value}")

RAG_EMBEDDING_MODEL_AUTO_UPDATE = (
    not OFFLINE_MODE
    and os.environ.get("RAG_EMBEDDING_MODEL_AUTO_UPDATE", "True").lower() == "true"
)

RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE = (
    os.environ.get("RAG_EMBEDDING_MODEL_TRUST_REMOTE_CODE", "True").lower() == "true"
)

RAG_EMBEDDING_BATCH_SIZE = PersistentConfig(
    "RAG_EMBEDDING_BATCH_SIZE",
    "rag.embedding_batch_size",
    int(
        os.environ.get("RAG_EMBEDDING_BATCH_SIZE")
        or os.environ.get("RAG_EMBEDDING_OPENAI_BATCH_SIZE", "1")
    ),
)

RAG_EMBEDDING_QUERY_PREFIX = os.environ.get("RAG_EMBEDDING_QUERY_PREFIX", None)

RAG_EMBEDDING_CONTENT_PREFIX = os.environ.get("RAG_EMBEDDING_CONTENT_PREFIX", None)

RAG_EMBEDDING_PREFIX_FIELD_NAME = os.environ.get(
    "RAG_EMBEDDING_PREFIX_FIELD_NAME", None
)

RAG_RERANKING_ENGINE = PersistentConfig(
    "RAG_RERANKING_ENGINE",
    "rag.reranking_engine",
    os.environ.get("RAG_RERANKING_ENGINE", ""),
)

RAG_RERANKING_MODEL = PersistentConfig(
    "RAG_RERANKING_MODEL",
    "rag.reranking_model",
    os.environ.get("RAG_RERANKING_MODEL", ""),
)
if RAG_RERANKING_MODEL.value != "":
    log.info(f"Reranking model set: {RAG_RERANKING_MODEL.value}")


RAG_RERANKING_MODEL_AUTO_UPDATE = (
    not OFFLINE_MODE
    and os.environ.get("RAG_RERANKING_MODEL_AUTO_UPDATE", "True").lower() == "true"
)

RAG_RERANKING_MODEL_TRUST_REMOTE_CODE = (
    os.environ.get("RAG_RERANKING_MODEL_TRUST_REMOTE_CODE", "True").lower() == "true"
)

RAG_EXTERNAL_RERANKER_URL = PersistentConfig(
    "RAG_EXTERNAL_RERANKER_URL",
    "rag.external_reranker_url",
    os.environ.get("RAG_EXTERNAL_RERANKER_URL", ""),
)

RAG_EXTERNAL_RERANKER_API_KEY = PersistentConfig(
    "RAG_EXTERNAL_RERANKER_API_KEY",
    "rag.external_reranker_api_key",
    os.environ.get("RAG_EXTERNAL_RERANKER_API_KEY", ""),
)


RAG_TEXT_SPLITTER = PersistentConfig(
    "RAG_TEXT_SPLITTER",
    "rag.text_splitter",
    os.environ.get("RAG_TEXT_SPLITTER", ""),
)


TIKTOKEN_CACHE_DIR = os.environ.get("TIKTOKEN_CACHE_DIR", f"{CACHE_DIR}/tiktoken")
TIKTOKEN_ENCODING_NAME = PersistentConfig(
    "TIKTOKEN_ENCODING_NAME",
    "rag.tiktoken_encoding_name",
    os.environ.get("TIKTOKEN_ENCODING_NAME", "cl100k_base"),
)


CHUNK_SIZE = PersistentConfig(
    "CHUNK_SIZE", "rag.chunk_size", int(os.environ.get("CHUNK_SIZE", "1000"))
)
CHUNK_OVERLAP = PersistentConfig(
    "CHUNK_OVERLAP",
    "rag.chunk_overlap",
    int(os.environ.get("CHUNK_OVERLAP", "100")),
)

DEFAULT_RAG_TEMPLATE = """### Task:
Respond to the user query using the provided context, incorporating inline citations in the format [id] **only when the <source> tag includes an explicit id attribute** (e.g., <source id="1">).

### Guidelines:
- If you don't know the answer, clearly state that.
- If uncertain, ask the user for clarification.
- Respond in the same language as the user's query.
- If the context is unreadable or of poor quality, inform the user and provide the best possible answer.
- If the answer isn't present in the context but you possess the knowledge, explain this to the user and provide the answer using your own understanding.
- **Only include inline citations using [id] (e.g., [1], [2]) when the <source> tag includes an id attribute.**
- Do not cite if the <source> tag does not contain an id attribute.
- Do not use XML tags in your response.
- Ensure citations are concise and directly related to the information provided.

### Example of Citation:
If the user asks about a specific topic and the information is found in a source with a provided id attribute, the response should include the citation like in the following example:
* "According to the study, the proposed method increases efficiency by 20% [1]."

### Output:
Provide a clear and direct response to the user's query, including inline citations in the format [id] only when the <source> tag with id attribute is present in the context.

<context>
{{CONTEXT}}
</context>

<user_query>
{{QUERY}}
</user_query>
"""

RAG_TEMPLATE = PersistentConfig(
    "RAG_TEMPLATE",
    "rag.template",
    os.environ.get("RAG_TEMPLATE", DEFAULT_RAG_TEMPLATE),
)

RAG_OPENAI_API_BASE_URL = PersistentConfig(
    "RAG_OPENAI_API_BASE_URL",
    "rag.openai_api_base_url",
    os.getenv("RAG_OPENAI_API_BASE_URL", OPENAI_API_BASE_URL),
)
RAG_OPENAI_API_KEY = PersistentConfig(
    "RAG_OPENAI_API_KEY",
    "rag.openai_api_key",
    os.getenv("RAG_OPENAI_API_KEY", OPENAI_API_KEY),
)

RAG_AZURE_OPENAI_BASE_URL = PersistentConfig(
    "RAG_AZURE_OPENAI_BASE_URL",
    "rag.azure_openai.base_url",
    os.getenv("RAG_AZURE_OPENAI_BASE_URL", ""),
)
RAG_AZURE_OPENAI_API_KEY = PersistentConfig(
    "RAG_AZURE_OPENAI_API_KEY",
    "rag.azure_openai.api_key",
    os.getenv("RAG_AZURE_OPENAI_API_KEY", ""),
)
RAG_AZURE_OPENAI_API_VERSION = PersistentConfig(
    "RAG_AZURE_OPENAI_API_VERSION",
    "rag.azure_openai.api_version",
    os.getenv("RAG_AZURE_OPENAI_API_VERSION", ""),
)

RAG_OLLAMA_BASE_URL = PersistentConfig(
    "RAG_OLLAMA_BASE_URL",
    "rag.ollama.url",
    os.getenv("RAG_OLLAMA_BASE_URL", OLLAMA_BASE_URL),
)

RAG_OLLAMA_API_KEY = PersistentConfig(
    "RAG_OLLAMA_API_KEY",
    "rag.ollama.key",
    os.getenv("RAG_OLLAMA_API_KEY", ""),
)

YOUTUBE_LOADER_LANGUAGE = PersistentConfig(
    "YOUTUBE_LOADER_LANGUAGE",
    "rag.youtube_loader_language",
    os.getenv("YOUTUBE_LOADER_LANGUAGE", "en").split(","),
)

YOUTUBE_LOADER_PROXY_URL = PersistentConfig(
    "YOUTUBE_LOADER_PROXY_URL",
    "rag.youtube_loader_proxy_url",
    os.getenv("YOUTUBE_LOADER_PROXY_URL", ""),
)


####################################
# Web Search (RAG)
####################################

ENABLE_RAG_LOCAL_WEB_FETCH = PersistentConfig(
    "ENABLE_RAG_LOCAL_WEB_FETCH",
    "rag.enable_rag_local_web_fetch",
    os.environ.get("ENABLE_RAG_LOCAL_WEB_FETCH", "False").lower() == "true",
)

ENABLE_WEB_SEARCH = PersistentConfig(
    "ENABLE_WEB_SEARCH",
    "rag.web.search.enable",
    os.getenv("ENABLE_WEB_SEARCH", "False").lower() == "true",
)

WEB_SEARCH_ENGINE = PersistentConfig(
    "WEB_SEARCH_ENGINE",
    "rag.web.search.engine",
    os.getenv("WEB_SEARCH_ENGINE", ""),
)

BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL = PersistentConfig(
    "BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL",
    "rag.web.search.bypass_embedding_and_retrieval",
    os.getenv("BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL", "False").lower() == "true",
)


BYPASS_WEB_SEARCH_WEB_LOADER = PersistentConfig(
    "BYPASS_WEB_SEARCH_WEB_LOADER",
    "rag.web.search.bypass_web_loader",
    os.getenv("BYPASS_WEB_SEARCH_WEB_LOADER", "False").lower() == "true",
)

WEB_SEARCH_RESULT_COUNT = PersistentConfig(
    "WEB_SEARCH_RESULT_COUNT",
    "rag.web.search.result_count",
    int(os.getenv("WEB_SEARCH_RESULT_COUNT", "3")),
)


# You can provide a list of your own websites to filter after performing a web search.
# This ensures the highest level of safety and reliability of the information sources.
WEB_SEARCH_DOMAIN_FILTER_LIST = PersistentConfig(
    "WEB_SEARCH_DOMAIN_FILTER_LIST",
    "rag.web.search.domain.filter_list",
    [
        # "wikipedia.com",
        # "wikimedia.org",
        # "wikidata.org",
    ],
)

WEB_SEARCH_CONCURRENT_REQUESTS = PersistentConfig(
    "WEB_SEARCH_CONCURRENT_REQUESTS",
    "rag.web.search.concurrent_requests",
    int(os.getenv("WEB_SEARCH_CONCURRENT_REQUESTS", "10")),
)


WEB_LOADER_ENGINE = PersistentConfig(
    "WEB_LOADER_ENGINE",
    "rag.web.loader.engine",
    os.environ.get("WEB_LOADER_ENGINE", ""),
)


WEB_LOADER_CONCURRENT_REQUESTS = PersistentConfig(
    "WEB_LOADER_CONCURRENT_REQUESTS",
    "rag.web.loader.concurrent_requests",
    int(os.getenv("WEB_LOADER_CONCURRENT_REQUESTS", "10")),
)


ENABLE_WEB_LOADER_SSL_VERIFICATION = PersistentConfig(
    "ENABLE_WEB_LOADER_SSL_VERIFICATION",
    "rag.web.loader.ssl_verification",
    os.environ.get("ENABLE_WEB_LOADER_SSL_VERIFICATION", "True").lower() == "true",
)

WEB_SEARCH_TRUST_ENV = PersistentConfig(
    "WEB_SEARCH_TRUST_ENV",
    "rag.web.search.trust_env",
    os.getenv("WEB_SEARCH_TRUST_ENV", "False").lower() == "true",
)


SEARXNG_QUERY_URL = PersistentConfig(
    "SEARXNG_QUERY_URL",
    "rag.web.search.searxng_query_url",
    os.getenv("SEARXNG_QUERY_URL", ""),
)

YACY_QUERY_URL = PersistentConfig(
    "YACY_QUERY_URL",
    "rag.web.search.yacy_query_url",
    os.getenv("YACY_QUERY_URL", ""),
)

YACY_USERNAME = PersistentConfig(
    "YACY_USERNAME",
    "rag.web.search.yacy_username",
    os.getenv("YACY_USERNAME", ""),
)

YACY_PASSWORD = PersistentConfig(
    "YACY_PASSWORD",
    "rag.web.search.yacy_password",
    os.getenv("YACY_PASSWORD", ""),
)

GOOGLE_PSE_API_KEY = PersistentConfig(
    "GOOGLE_PSE_API_KEY",
    "rag.web.search.google_pse_api_key",
    os.getenv("GOOGLE_PSE_API_KEY", ""),
)

GOOGLE_PSE_ENGINE_ID = PersistentConfig(
    "GOOGLE_PSE_ENGINE_ID",
    "rag.web.search.google_pse_engine_id",
    os.getenv("GOOGLE_PSE_ENGINE_ID", ""),
)

BRAVE_SEARCH_API_KEY = PersistentConfig(
    "BRAVE_SEARCH_API_KEY",
    "rag.web.search.brave_search_api_key",
    os.getenv("BRAVE_SEARCH_API_KEY", ""),
)

KAGI_SEARCH_API_KEY = PersistentConfig(
    "KAGI_SEARCH_API_KEY",
    "rag.web.search.kagi_search_api_key",
    os.getenv("KAGI_SEARCH_API_KEY", ""),
)

MOJEEK_SEARCH_API_KEY = PersistentConfig(
    "MOJEEK_SEARCH_API_KEY",
    "rag.web.search.mojeek_search_api_key",
    os.getenv("MOJEEK_SEARCH_API_KEY", ""),
)

BOCHA_SEARCH_API_KEY = PersistentConfig(
    "BOCHA_SEARCH_API_KEY",
    "rag.web.search.bocha_search_api_key",
    os.getenv("BOCHA_SEARCH_API_KEY", ""),
)

SERPSTACK_API_KEY = PersistentConfig(
    "SERPSTACK_API_KEY",
    "rag.web.search.serpstack_api_key",
    os.getenv("SERPSTACK_API_KEY", ""),
)

SERPSTACK_HTTPS = PersistentConfig(
    "SERPSTACK_HTTPS",
    "rag.web.search.serpstack_https",
    os.getenv("SERPSTACK_HTTPS", "True").lower() == "true",
)

SERPER_API_KEY = PersistentConfig(
    "SERPER_API_KEY",
    "rag.web.search.serper_api_key",
    os.getenv("SERPER_API_KEY", ""),
)

SERPLY_API_KEY = PersistentConfig(
    "SERPLY_API_KEY",
    "rag.web.search.serply_api_key",
    os.getenv("SERPLY_API_KEY", ""),
)

JINA_API_KEY = PersistentConfig(
    "JINA_API_KEY",
    "rag.web.search.jina_api_key",
    os.getenv("JINA_API_KEY", ""),
)

SEARCHAPI_API_KEY = PersistentConfig(
    "SEARCHAPI_API_KEY",
    "rag.web.search.searchapi_api_key",
    os.getenv("SEARCHAPI_API_KEY", ""),
)

SEARCHAPI_ENGINE = PersistentConfig(
    "SEARCHAPI_ENGINE",
    "rag.web.search.searchapi_engine",
    os.getenv("SEARCHAPI_ENGINE", ""),
)

SERPAPI_API_KEY = PersistentConfig(
    "SERPAPI_API_KEY",
    "rag.web.search.serpapi_api_key",
    os.getenv("SERPAPI_API_KEY", ""),
)

SERPAPI_ENGINE = PersistentConfig(
    "SERPAPI_ENGINE",
    "rag.web.search.serpapi_engine",
    os.getenv("SERPAPI_ENGINE", ""),
)

BING_SEARCH_V7_ENDPOINT = PersistentConfig(
    "BING_SEARCH_V7_ENDPOINT",
    "rag.web.search.bing_search_v7_endpoint",
    os.environ.get(
        "BING_SEARCH_V7_ENDPOINT", "https://api.bing.microsoft.com/v7.0/search"
    ),
)

BING_SEARCH_V7_SUBSCRIPTION_KEY = PersistentConfig(
    "BING_SEARCH_V7_SUBSCRIPTION_KEY",
    "rag.web.search.bing_search_v7_subscription_key",
    os.environ.get("BING_SEARCH_V7_SUBSCRIPTION_KEY", ""),
)

EXA_API_KEY = PersistentConfig(
    "EXA_API_KEY",
    "rag.web.search.exa_api_key",
    os.getenv("EXA_API_KEY", ""),
)

PERPLEXITY_API_KEY = PersistentConfig(
    "PERPLEXITY_API_KEY",
    "rag.web.search.perplexity_api_key",
    os.getenv("PERPLEXITY_API_KEY", ""),
)

PERPLEXITY_MODEL = PersistentConfig(
    "PERPLEXITY_MODEL",
    "rag.web.search.perplexity_model",
    os.getenv("PERPLEXITY_MODEL", "sonar"),
)

PERPLEXITY_SEARCH_CONTEXT_USAGE = PersistentConfig(
    "PERPLEXITY_SEARCH_CONTEXT_USAGE",
    "rag.web.search.perplexity_search_context_usage",
    os.getenv("PERPLEXITY_SEARCH_CONTEXT_USAGE", "medium"),
)

SOUGOU_API_SID = PersistentConfig(
    "SOUGOU_API_SID",
    "rag.web.search.sougou_api_sid",
    os.getenv("SOUGOU_API_SID", ""),
)

SOUGOU_API_SK = PersistentConfig(
    "SOUGOU_API_SK",
    "rag.web.search.sougou_api_sk",
    os.getenv("SOUGOU_API_SK", ""),
)

TAVILY_API_KEY = PersistentConfig(
    "TAVILY_API_KEY",
    "rag.web.search.tavily_api_key",
    os.getenv("TAVILY_API_KEY", ""),
)

TAVILY_EXTRACT_DEPTH = PersistentConfig(
    "TAVILY_EXTRACT_DEPTH",
    "rag.web.search.tavily_extract_depth",
    os.getenv("TAVILY_EXTRACT_DEPTH", "basic"),
)

PLAYWRIGHT_WS_URL = PersistentConfig(
    "PLAYWRIGHT_WS_URL",
    "rag.web.loader.playwright_ws_url",
    os.environ.get("PLAYWRIGHT_WS_URL", ""),
)

PLAYWRIGHT_TIMEOUT = PersistentConfig(
    "PLAYWRIGHT_TIMEOUT",
    "rag.web.loader.playwright_timeout",
    int(os.environ.get("PLAYWRIGHT_TIMEOUT", "10000")),
)

FIRECRAWL_API_KEY = PersistentConfig(
    "FIRECRAWL_API_KEY",
    "rag.web.loader.firecrawl_api_key",
    os.environ.get("FIRECRAWL_API_KEY", ""),
)

FIRECRAWL_API_BASE_URL = PersistentConfig(
    "FIRECRAWL_API_BASE_URL",
    "rag.web.loader.firecrawl_api_url",
    os.environ.get("FIRECRAWL_API_BASE_URL", "https://api.firecrawl.dev"),
)

EXTERNAL_WEB_SEARCH_URL = PersistentConfig(
    "EXTERNAL_WEB_SEARCH_URL",
    "rag.web.search.external_web_search_url",
    os.environ.get("EXTERNAL_WEB_SEARCH_URL", ""),
)

EXTERNAL_WEB_SEARCH_API_KEY = PersistentConfig(
    "EXTERNAL_WEB_SEARCH_API_KEY",
    "rag.web.search.external_web_search_api_key",
    os.environ.get("EXTERNAL_WEB_SEARCH_API_KEY", ""),
)

EXTERNAL_WEB_LOADER_URL = PersistentConfig(
    "EXTERNAL_WEB_LOADER_URL",
    "rag.web.loader.external_web_loader_url",
    os.environ.get("EXTERNAL_WEB_LOADER_URL", ""),
)

EXTERNAL_WEB_LOADER_API_KEY = PersistentConfig(
    "EXTERNAL_WEB_LOADER_API_KEY",
    "rag.web.loader.external_web_loader_api_key",
    os.environ.get("EXTERNAL_WEB_LOADER_API_KEY", ""),
)
