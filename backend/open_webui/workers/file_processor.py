"""
File Processing Worker for RQ Job Queue

This module contains the worker function that processes file jobs enqueued in Redis.
Workers run in separate processes and can be distributed across multiple pods.
"""

import logging
import os
import sys
import time
import traceback
from typing import Optional

# Ensure logging is configured for worker process
# The worker process redirects stdout/stderr to /tmp/rq-worker.log
# So we need to ensure logs go to stdout/stderr
if not logging.root.handlers:
    # Configure basic logging if not already configured
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
        stream=sys.stdout,
        force=True
    )

# Import os early for environment variable access in fallback config

from langchain_core.documents import Document

from open_webui.models.files import FileModel, Files
from open_webui.models.users import Users
from open_webui.models.knowledge import Knowledges
from open_webui.storage.provider import Storage
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.retrieval.loaders.main import Loader
from open_webui.internal.db import Session
from open_webui.routers.retrieval import (
    save_docs_to_vector_db,
    save_docs_to_multiple_collections,
    calculate_sha256_string,
    get_ef,
    get_rf,
)
from open_webui.config import (
    AppConfig,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
    RAG_RERANKING_MODEL_AUTO_UPDATE,
    # Import all RAG config objects needed by worker
    RAG_EMBEDDING_ENGINE,
    RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_BATCH_SIZE,
    RAG_RERANKING_MODEL,
    RAG_OPENAI_API_BASE_URL,
    RAG_OPENAI_API_KEY,
    RAG_OLLAMA_BASE_URL,
    RAG_OLLAMA_API_KEY,
    CONTENT_EXTRACTION_ENGINE,
    RAG_TEXT_SPLITTER,
    CHUNK_SIZE,  # UserScopedConfig
    CHUNK_OVERLAP,  # UserScopedConfig
    PDF_EXTRACT_IMAGES,
    DOCUMENT_INTELLIGENCE_ENDPOINT,
    DOCUMENT_INTELLIGENCE_KEY,
    BYPASS_EMBEDDING_AND_RETRIEVAL,
)
from open_webui.retrieval.utils import get_embedding_function

# OpenTelemetry instrumentation (conditional import)
try:
    from open_webui.utils.otel_instrumentation import (
        trace_span,
        add_span_event,
        set_span_attribute,
    )
    from open_webui.utils.otel_config import is_otel_enabled
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
    def is_otel_enabled():
        return False

log = logging.getLogger(__name__)
# Ensure logger is configured for worker process - use INFO level to capture all detailed logs
log.setLevel(logging.INFO)
# Force propagation to root logger to ensure logs are captured by worker's stdout/stderr redirection
log.propagate = True

# Also add a direct stdout handler as fallback to ensure logs are always visible
if not any(isinstance(h, logging.StreamHandler) for h in log.handlers):
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(logging.Formatter('%(levelname)s [%(name)s] %(message)s'))
    log.addHandler(stdout_handler)

# Global cached AppConfig instance (initialized once at worker startup, reused for all jobs)
# Note: RQ workers process jobs sequentially by default, so no threading.Lock needed
# If concurrent job processing is enabled, initialization happens once anyway during module import
_worker_config = None


def get_worker_config():
    """
    Get or create a cached AppConfig instance for the worker.
    
    This config is initialized once at worker startup and reused for all jobs,
    preventing unnecessary AppConfig creation and database connection overhead.
    
    Note: RQ workers process jobs sequentially by default, so no lock is needed.
    The initialization happens lazily on first job or can be called at worker startup.
    
    Returns:
        AppConfig: Cached AppConfig instance with all RAG config values assigned
    """
    global _worker_config
    if _worker_config is None:
        try:
            _worker_config = AppConfig()
            # CRITICAL: Assign all config values to AppConfig, just like main.py does
            # Without this, AppConfig._state is empty and accessing config values fails
            # Assign all RAG config values to AppConfig (same as main.py)
            _worker_config.RAG_EMBEDDING_ENGINE = RAG_EMBEDDING_ENGINE
            _worker_config.RAG_EMBEDDING_MODEL = RAG_EMBEDDING_MODEL
            _worker_config.RAG_EMBEDDING_BATCH_SIZE = RAG_EMBEDDING_BATCH_SIZE
            _worker_config.RAG_RERANKING_MODEL = RAG_RERANKING_MODEL
            _worker_config.RAG_OPENAI_API_BASE_URL = RAG_OPENAI_API_BASE_URL
            _worker_config.RAG_OPENAI_API_KEY = RAG_OPENAI_API_KEY
            _worker_config.RAG_OLLAMA_BASE_URL = RAG_OLLAMA_BASE_URL
            _worker_config.RAG_OLLAMA_API_KEY = RAG_OLLAMA_API_KEY
            _worker_config.CONTENT_EXTRACTION_ENGINE = CONTENT_EXTRACTION_ENGINE
            _worker_config.TEXT_SPLITTER = RAG_TEXT_SPLITTER
            _worker_config.CHUNK_SIZE = CHUNK_SIZE  # UserScopedConfig
            _worker_config.CHUNK_OVERLAP = CHUNK_OVERLAP  # UserScopedConfig
            _worker_config.PDF_EXTRACT_IMAGES = PDF_EXTRACT_IMAGES
            _worker_config.DOCUMENT_INTELLIGENCE_ENDPOINT = DOCUMENT_INTELLIGENCE_ENDPOINT
            _worker_config.DOCUMENT_INTELLIGENCE_KEY = DOCUMENT_INTELLIGENCE_KEY
            _worker_config.BYPASS_EMBEDDING_AND_RETRIEVAL = BYPASS_EMBEDDING_AND_RETRIEVAL
            
            # Verify config is populated
            if not hasattr(_worker_config, '_state') or 'RAG_EMBEDDING_ENGINE' not in _worker_config._state:
                raise ValueError("AppConfig._state not properly populated with RAG_EMBEDDING_ENGINE")
            
            log.info("Worker AppConfig initialized successfully with all RAG config values (cached for reuse)")
        except Exception as config_error:
            log.error(
                f"Failed to initialize AppConfig in worker process: {config_error}. "
                "Using fallback configuration. This may cause issues with file processing.",
                exc_info=True
            )
            # Create a minimal fallback config object
            _worker_config = _create_fallback_config()
    return _worker_config


class MockRequest:
    """
    Mock Request object for workers that need app.state.config.
    Workers run in separate processes and don't have access to the FastAPI Request object.
    """
    def __init__(self, embedding_api_key: Optional[str] = None):
        self.app = MockApp(embedding_api_key=embedding_api_key)


class MockApp:
    """
    Mock app object that provides access to config and other app state.
    """
    def __init__(self, embedding_api_key: Optional[str] = None):
        # Initialize config (this reads from environment and database)
        self.state = MockState(embedding_api_key=embedding_api_key)


class MockState:
    """
    Mock state object that provides access to configuration and embedding functions.
    """
    def __init__(self, embedding_api_key: Optional[str] = None):
        # Use cached worker config (initialized once at worker startup)
        # This avoids creating a new AppConfig() for every job, which prevents
        # unnecessary database connection overhead and improves performance
        try:
            self.config = get_worker_config()
            log.debug("Using cached worker AppConfig (reused from worker startup)")
        except Exception as config_error:
            log.error(
                f"Failed to get worker config: {config_error}. "
                "Using fallback configuration. This may cause issues with file processing.",
                exc_info=True
            )
            # Create a minimal fallback config object that has required attributes
            # This allows the worker to continue but with limited functionality
            self.config = _create_fallback_config()
        
        # Store embedding_api_key for per-job initialization
        self._embedding_api_key = embedding_api_key
        
        # Initialize base embedding functions (ef, rf) - these don't need API key
        # EMBEDDING_FUNCTION will be initialized per-job with the correct API key
        try:
            # Initialize embedding function model (ef) - no API key needed
            self.ef = get_ef(
                self.config.RAG_EMBEDDING_ENGINE,
                self.config.RAG_EMBEDDING_MODEL,
                RAG_EMBEDDING_MODEL_AUTO_UPDATE,
            )
            
            # Initialize reranking function (rf) - no API key needed
            self.rf = get_rf(
                self.config.RAG_RERANKING_MODEL,
                RAG_RERANKING_MODEL_AUTO_UPDATE,
            )
            
            log.debug(
                f"Initialized base embedding functions in worker: "
                f"engine={self.config.RAG_EMBEDDING_ENGINE}, "
                f"model={self.config.RAG_EMBEDDING_MODEL}"
            )
        except Exception as embedding_error:
            log.error(
                f"Failed to initialize base embedding functions in worker process: {embedding_error}. "
                "File processing may fail if embeddings are required.",
                exc_info=True
            )
            # Set to None - functions that use these should handle None gracefully
            self.ef = None
            self.rf = None
        
        # EMBEDDING_FUNCTION will be initialized per-job with the correct per-user API key
        self.EMBEDDING_FUNCTION = None
    
    def initialize_embedding_function(self, embedding_api_key: Optional[str] = None):
        """
        Initialize EMBEDDING_FUNCTION with the correct per-user/per-admin API key.
        This is called per-job to ensure RBAC-protected API keys are used.
        
        Args:
            embedding_api_key: Per-user/per-admin API key from job (RBAC-protected)
        """
        print("=" * 80, flush=True)
        print("[EMBEDDING INIT] Starting embedding function initialization", flush=True)
        print(f"  [INPUT] embedding_api_key={'PROVIDED (' + str(len(embedding_api_key)) + ' chars)' if embedding_api_key else 'None'}", flush=True)
        log.info("=" * 80)
        log.info("[EMBEDDING INIT] Starting embedding function initialization")
        log.info(f"  [INPUT] embedding_api_key={'PROVIDED (' + str(len(embedding_api_key)) + ' chars)' if embedding_api_key else 'None'}")
        
        # Use the passed API key (from job) or the one stored during initialization
        api_key = embedding_api_key or self._embedding_api_key
        print(f"  [STEP 1] API key resolution: {'Using provided key' if embedding_api_key else 'Using stored key or None'}", flush=True)
        log.info(f"  [STEP 1] API key resolution: {'Using provided key' if embedding_api_key else 'Using stored key or None'}")
        
        try:
            # Determine API URL and key based on engine type
            print(f"  [STEP 2] Embedding engine: {self.config.RAG_EMBEDDING_ENGINE}", flush=True)
            log.info(f"  [STEP 2] Embedding engine: {self.config.RAG_EMBEDDING_ENGINE}")
            
            if self.config.RAG_EMBEDDING_ENGINE in ["openai", "portkey"]:
                print(f"  [STEP 3] Engine type: OpenAI/Portkey (API-based)", flush=True)
                log.info(f"  [STEP 3] Engine type: OpenAI/Portkey (API-based)")
                
                base_url_config = self.config.RAG_OPENAI_API_BASE_URL
                print(f"  [STEP 3.1] base_url_config type: {type(base_url_config)}", flush=True)
                log.info(f"  [STEP 3.1] base_url_config type: {type(base_url_config)}")
                
                api_url = (
                    base_url_config.value
                    if hasattr(base_url_config, 'value')
                    else str(base_url_config)
                )
                print(f"  [STEP 3.2] Extracted api_url: {api_url}", flush=True)
                log.info(f"  [STEP 3.2] Extracted api_url: {api_url}")
                
                # Fallback to default if empty (from config.py default)
                if not api_url or api_url.strip() == "" or api_url == "None":
                    api_url = "https://ai-gateway.apps.cloud.rt.nyu.edu/v1"
                    print(f"  [STEP 3.3] ⚠️  Base URL was empty/None, using default: {api_url}", flush=True)
                    log.warning(f"  [STEP 3.3] Base URL was empty/None, using default: {api_url}")
                else:
                    print(f"  [STEP 3.3] ✅ Using configured base URL: {api_url}", flush=True)
                    log.info(f"  [STEP 3.3] ✅ Using configured base URL: {api_url}")
                
                # CRITICAL: Use per-user/per-admin API key from job (RBAC-protected)
                # Do NOT fall back to env var - that would break RBAC
                print(f"  [STEP 4] API key validation:", flush=True)
                print(f"    api_key is None: {api_key is None}", flush=True)
                print(f"    api_key is empty string: {api_key == '' if api_key else 'N/A'}", flush=True)
                print(f"    api_key length: {len(api_key) if api_key else 0}", flush=True)
                log.info(f"  [STEP 4] API key validation:")
                log.info(f"    api_key is None: {api_key is None}")
                log.info(f"    api_key is empty string: {api_key == '' if api_key else 'N/A'}")
                log.info(f"    api_key length: {len(api_key) if api_key else 0}")
                
                if not api_key or not api_key.strip():
                    error_msg = (
                        "❌ CRITICAL: No embedding API key provided in job! "
                        "Embedding will fail. This key should come from admin config (RBAC-protected). "
                        "Please ensure the admin has configured an API key in Settings > Documents > Embedding."
                    )
                    print(f"  [STEP 4] ❌ {error_msg}", flush=True)
                    log.error(f"  [STEP 4] ❌ {error_msg}")
                    print(f"[EMBEDDING ERROR] {error_msg}", flush=True)
                    # Raise exception to fail fast
                    raise ValueError(error_msg)
                else:
                    api_key_preview = api_key[-4:] if len(api_key) >= 4 else '***'
                    print(f"  [STEP 4] ✅ API key validated:", flush=True)
                    print(f"    Key length: {len(api_key)} chars", flush=True)
                    print(f"    Key ends with: ...{api_key_preview}", flush=True)
                    log.info(
                        f"  [STEP 4] ✅ API key validated: "
                        f"length={len(api_key)}, ends_with=...{api_key_preview}"
                    )
                    print(
                        f"[EMBEDDING] ✅ Using RBAC-scoped API key (length: {len(api_key)}, "
                        f"ends with ...{api_key_preview})",
                        flush=True
                    )
                # For API-based engines (Portkey/OpenAI), ef can be None - that's OK
                # They use API calls, not local models
            else:
                print(f"  [STEP 3] Engine type: {self.config.RAG_EMBEDDING_ENGINE} (non-OpenAI)", flush=True)
                log.info(f"  [STEP 3] Engine type: {self.config.RAG_EMBEDDING_ENGINE} (non-OpenAI)")
                
                base_url_config = self.config.RAG_OLLAMA_BASE_URL
                api_url = (
                    base_url_config.value
                    if hasattr(base_url_config, 'value')
                    else str(base_url_config)
                )
                api_key = self.config.RAG_OLLAMA_API_KEY
                print(f"  [STEP 3.1] Using Ollama config: api_url={api_url}", flush=True)
                log.info(f"  [STEP 3.1] Using Ollama config: api_url={api_url}")
                
                # For local engines (sentence-transformers), ef must not be None
                if self.ef is None:
                    error_msg = "Cannot initialize EMBEDDING_FUNCTION: ef (embedding function model) is None for local engine"
                    print(f"  [STEP 3.2] ❌ {error_msg}", flush=True)
                    log.error(f"  [STEP 3.2] ❌ {error_msg}")
                    raise ValueError(error_msg)
                else:
                    print(f"  [STEP 3.2] ✅ ef (embedding function model) is available", flush=True)
                    log.info(f"  [STEP 3.2] ✅ ef (embedding function model) is available")
            
            # For API-based engines (Portkey/OpenAI), ef can be None - get_embedding_function handles this
            print(f"  [STEP 5] Initializing embedding function:", flush=True)
            print(f"    engine: {self.config.RAG_EMBEDDING_ENGINE}", flush=True)
            print(f"    model: {self.config.RAG_EMBEDDING_MODEL}", flush=True)
            print(f"    api_url: {api_url}", flush=True)
            print(f"    api_key provided: {api_key is not None and len(api_key) > 0}", flush=True)
            print(f"    batch_size: {self.config.RAG_EMBEDDING_BATCH_SIZE}", flush=True)
            print(f"    ef is None: {self.ef is None} (OK for API engines)", flush=True)
            log.info(f"  [STEP 5] Initializing embedding function:")
            log.info(f"    engine: {self.config.RAG_EMBEDDING_ENGINE}")
            log.info(f"    model: {self.config.RAG_EMBEDDING_MODEL}")
            log.info(f"    api_url: {api_url}")
            log.info(f"    api_key provided: {api_key is not None and len(api_key) > 0}")
            log.info(f"    batch_size: {self.config.RAG_EMBEDDING_BATCH_SIZE}")
            log.info(f"    ef is None: {self.ef is None} (OK for API engines)")
            
            self.EMBEDDING_FUNCTION = get_embedding_function(
                self.config.RAG_EMBEDDING_ENGINE,
                self.config.RAG_EMBEDDING_MODEL,
                self.ef,  # Can be None for API-based engines
                api_url,
                api_key,
                self.config.RAG_EMBEDDING_BATCH_SIZE,
            )
            
            print(f"  [STEP 6] Embedding function creation result:", flush=True)
            print(f"    EMBEDDING_FUNCTION is None: {self.EMBEDDING_FUNCTION is None}", flush=True)
            print(f"    EMBEDDING_FUNCTION type: {type(self.EMBEDDING_FUNCTION)}", flush=True)
            log.info(f"  [STEP 6] Embedding function creation result:")
            log.info(f"    EMBEDDING_FUNCTION is None: {self.EMBEDDING_FUNCTION is None}")
            log.info(f"    EMBEDDING_FUNCTION type: {type(self.EMBEDDING_FUNCTION)}")
            
            if self.EMBEDDING_FUNCTION is None:
                error_msg = "Failed to create embedding function - get_embedding_function returned None"
                print(f"  [STEP 6] ❌ {error_msg}", flush=True)
                log.error(f"  [STEP 6] ❌ {error_msg}")
                raise ValueError(error_msg)
            else:
                print(f"  [STEP 6] ✅ Embedding function created successfully", flush=True)
                log.info(f"  [STEP 6] ✅ Embedding function created successfully")
            
            print(f"[EMBEDDING INIT] ✅ Initialization completed successfully", flush=True)
            log.info(f"[EMBEDDING INIT] ✅ Initialization completed successfully")
            print("=" * 80, flush=True)
            log.info("=" * 80)
            
        except Exception as embedding_error:
            error_msg = f"Failed to initialize EMBEDDING_FUNCTION per-job: {embedding_error}"
            print(f"[EMBEDDING INIT] ❌ {error_msg}", flush=True)
            log.error(f"[EMBEDDING INIT] ❌ {error_msg}", exc_info=True)
            print("=" * 80, flush=True)
            self.EMBEDDING_FUNCTION = None
            raise  # Re-raise to fail fast


class _FallbackConfig:
    """
    Fallback configuration object used when AppConfig initialization fails.
    Provides minimal required attributes with safe defaults.
    """
    def __init__(self):
        # Set minimal required attributes with safe defaults from environment
        self.RAG_EMBEDDING_ENGINE = os.environ.get("RAG_EMBEDDING_ENGINE", "portkey")
        self.RAG_EMBEDDING_MODEL = os.environ.get("RAG_EMBEDDING_MODEL", "@openai-embedding/text-embedding-3-small")
        self.RAG_EMBEDDING_BATCH_SIZE = int(os.environ.get("RAG_EMBEDDING_BATCH_SIZE", "1"))
        self.RAG_RERANKING_MODEL = os.environ.get("RAG_RERANKING_MODEL", "")
        self.RAG_OPENAI_API_BASE_URL = os.environ.get("RAG_OPENAI_API_BASE_URL", "")
        # For UserScopedConfig, create a mock object with .default property
        class MockUserScopedConfig:
            def __init__(self, default_value):
                self.default = default_value
        self.RAG_OPENAI_API_KEY = MockUserScopedConfig(os.environ.get("RAG_OPENAI_API_KEY", ""))
        self.RAG_OLLAMA_BASE_URL = os.environ.get("RAG_OLLAMA_BASE_URL", "")
        self.RAG_OLLAMA_API_KEY = os.environ.get("RAG_OLLAMA_API_KEY", "")
        self.CONTENT_EXTRACTION_ENGINE = os.environ.get("CONTENT_EXTRACTION_ENGINE", "auto")
        self.TIKA_SERVER_URL = os.environ.get("TIKA_SERVER_URL", "")
        self.PDF_EXTRACT_IMAGES = os.environ.get("PDF_EXTRACT_IMAGES", "False").lower() == "true"
        self.TEXT_SPLITTER = os.environ.get("RAG_TEXT_SPLITTER", "recursive")
        # UserScopedConfig - use .default for fallback
        self.CHUNK_SIZE = MockUserScopedConfig(int(os.environ.get("CHUNK_SIZE", "1000")))
        self.CHUNK_OVERLAP = MockUserScopedConfig(int(os.environ.get("CHUNK_OVERLAP", "100")))
        self.DOCUMENT_INTELLIGENCE_ENDPOINT = os.environ.get("DOCUMENT_INTELLIGENCE_ENDPOINT", "")
        self.DOCUMENT_INTELLIGENCE_KEY = os.environ.get("DOCUMENT_INTELLIGENCE_KEY", "")
        self.BYPASS_EMBEDDING_AND_RETRIEVAL = os.environ.get("BYPASS_EMBEDDING_AND_RETRIEVAL", "False").lower() == "true"
        # Add TIKA_SERVER_URL for fallback (even though we don't use it, it might be accessed)
        self.TIKA_SERVER_URL = os.environ.get("TIKA_SERVER_URL", "")
        # Add missing config attributes that might be accessed
        self.RAG_EMBEDDING_ENGINE = os.environ.get("RAG_EMBEDDING_ENGINE", "portkey")
        self.RAG_EMBEDDING_MODEL = os.environ.get("RAG_EMBEDDING_MODEL", "@openai-embedding/text-embedding-3-small")
        self.RAG_EMBEDDING_BATCH_SIZE = int(os.environ.get("RAG_EMBEDDING_BATCH_SIZE", "1"))
        self.RAG_OPENAI_API_BASE_URL = os.environ.get("RAG_OPENAI_API_BASE_URL", "")
        self.RAG_OLLAMA_BASE_URL = os.environ.get("RAG_OLLAMA_BASE_URL", "")
        self.RAG_OLLAMA_API_KEY = os.environ.get("RAG_OLLAMA_API_KEY", "")
    
    def __getattr__(self, name):
        # Return None for any other attributes to prevent AttributeError
        log.warning(f"FallbackConfig: Attribute '{name}' not available, returning None")
        return None


def _create_fallback_config():
    """Create a fallback configuration object."""
    return _FallbackConfig()


def process_file_job(
    file_id: str,
    content: Optional[str] = None,
    collection_name: Optional[str] = None,
    knowledge_id: Optional[str] = None,
    user_id: Optional[str] = None,
    embedding_api_key: Optional[str] = None,
    _otel_trace_context: Optional[dict] = None,
) -> dict:
    """
    Process a file job. This function is called by RQ workers.
    
    Args:
        file_id: ID of the file to process
        content: Optional pre-extracted content (for text files)
        collection_name: Optional collection name for embeddings
        knowledge_id: Optional knowledge base ID
        user_id: User ID who initiated the processing
        embedding_api_key: API key for embedding service (per-user, from admin config)
        _otel_trace_context: Optional trace context for distributed tracing (internal use)
        
    Returns:
        Dictionary with processing result
    """
    start_time = time.time()
    
    # Restore trace context from job metadata if available
    # This enables distributed tracing across process boundaries (main app → RQ worker)
    context_token = None
    if OTEL_AVAILABLE and is_otel_enabled() and _otel_trace_context:
        try:
            from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
            from opentelemetry import context, trace
            
            # Extract trace context from job metadata
            propagator = TraceContextTextMapPropagator()
            extracted_context = propagator.extract(_otel_trace_context)
            
            # Attach the extracted context to this worker process
            context_token = context.attach(extracted_context)
            log.debug(f"Restored trace context for job processing: file_id={file_id}")
        except Exception as trace_error:
            log.debug(f"Failed to restore trace context: {trace_error}")
            context_token = None
    
    try:
        # Generate job_id_str for instrumentation
        job_id_str = f"file_processing_{file_id}"
        
        # Create OTEL span for job processing (linked to parent via trace context if available)
        with trace_span(
            name="job.process",
            attributes={
                "job.id": job_id_str,
                "job.file_id": file_id,
                "job.user_id": str(user_id) if user_id else None,
                "job.knowledge_id": knowledge_id,
                "job.collection_name": collection_name,
                "job.has_trace_context": bool(_otel_trace_context),
            },
        ) as span:
            try:
                add_span_event("job.started", {"file_id": file_id})
                
                # Initialize request to None so it's accessible in finally block for cleanup
                request = None
                
                # Force flush stdout/stderr to ensure logs are written immediately
                sys.stdout.flush()
                sys.stderr.flush()
                
                # Use both logging and print to ensure visibility (print goes directly to stdout)
                print("=" * 80, flush=True)
                print(f"[JOB START] Processing file job: file_id={file_id}", flush=True)
                log.info("=" * 80)
                log.info(f"[JOB START] Processing file job: file_id={file_id}")
                sys.stdout.flush()  # Flush after each critical log to ensure visibility
                print(f"  INPUT PARAMETERS:", flush=True)
                print(f"    file_id={file_id}", flush=True)
                print(f"    user_id={user_id}", flush=True)
                print(f"    collection_name={collection_name}", flush=True)
                print(f"    knowledge_id={knowledge_id}", flush=True)
                print(f"    content={'PROVIDED (' + str(len(content)) + ' chars)' if content else 'None'}", flush=True)
                print(f"    embedding_api_key={'PROVIDED (' + str(len(embedding_api_key)) + ' chars, ends with ...' + embedding_api_key[-4:] + ')' if embedding_api_key else 'None'}", flush=True)
                print(f"  START_TIME={start_time}", flush=True)
                log.info(f"  INPUT PARAMETERS:")
                log.info(f"    file_id={file_id}")
                log.info(f"    user_id={user_id}")
                log.info(f"    collection_name={collection_name}")
                log.info(f"    knowledge_id={knowledge_id}")
                log.info(f"    content={'PROVIDED (' + str(len(content)) + ' chars)' if content else 'None'}")
                log.info(f"    embedding_api_key={'PROVIDED (' + str(len(embedding_api_key)) + ' chars, ends with ...' + embedding_api_key[-4:] + ')' if embedding_api_key else 'None'}")
                log.info(f"  START_TIME={start_time}")
                sys.stdout.flush()
                
                # Create mock request object for compatibility with existing code
                # Pass the embedding_api_key so it can initialize the embedding function per-job
                print(f"[STEP 1] Initializing MockRequest and embedding function...", flush=True)
                log.info(f"[STEP 1] Initializing MockRequest and embedding function...")
                try:
                    print(f"  [STEP 1.1] Creating MockRequest with embedding_api_key={'PROVIDED' if embedding_api_key else 'None'}", flush=True)
                    log.info(f"  [STEP 1.1] Creating MockRequest with embedding_api_key={'PROVIDED' if embedding_api_key else 'None'}")
                    request = MockRequest(embedding_api_key=embedding_api_key)
                    print(f"  [STEP 1.1] ✅ MockRequest created successfully", flush=True)
                    print(f"    request.app.state.config.RAG_EMBEDDING_ENGINE={request.app.state.config.RAG_EMBEDDING_ENGINE}", flush=True)
                    print(f"    request.app.state.config.RAG_EMBEDDING_MODEL={request.app.state.config.RAG_EMBEDDING_MODEL}", flush=True)
                    print(f"    request.app.state.ef={'SET' if request.app.state.ef is not None else 'None (OK for API engines)'}", flush=True)
                    log.info(f"  [STEP 1.1] ✅ MockRequest created successfully")
                    log.info(f"    request.app.state.config.RAG_EMBEDDING_ENGINE={request.app.state.config.RAG_EMBEDDING_ENGINE}")
                    log.info(f"    request.app.state.config.RAG_EMBEDDING_MODEL={request.app.state.config.RAG_EMBEDDING_MODEL}")
                    log.info(f"    request.app.state.ef={'SET' if request.app.state.ef is not None else 'None (OK for API engines)'}")
                    sys.stdout.flush()
                    
                    # CRITICAL: Validate API key BEFORE initialization
                    print(f"  [STEP 1.2] Validating embedding API key...", flush=True)
                    log.info(f"  [STEP 1.2] Validating embedding API key...")
                    print(f"    embedding_api_key is None: {embedding_api_key is None}", flush=True)
                    print(f"    embedding_api_key is empty: {embedding_api_key == '' if embedding_api_key else 'N/A'}", flush=True)
                    print(f"    embedding_api_key length: {len(embedding_api_key) if embedding_api_key else 0}", flush=True)
                    log.info(f"    embedding_api_key is None: {embedding_api_key is None}")
                    log.info(f"    embedding_api_key is empty: {embedding_api_key == '' if embedding_api_key else 'N/A'}")
                    log.info(f"    embedding_api_key length: {len(embedding_api_key) if embedding_api_key else 0}")
                    
                    if not embedding_api_key or not embedding_api_key.strip():
                        error_msg = (
                            f"❌ CRITICAL BUG: No embedding API key provided in job for file_id={file_id}! "
                            f"This will cause embedding generation to fail. "
                            f"The API key should have been retrieved from admin config and passed to the job. "
                            f"Please check: 1) Admin has configured API key in Settings > Documents, "
                            f"2) User is in a group created by that admin, 3) API key was passed to enqueue_file_processing_job()"
                        )
                        print(f"  [STEP 1.2] ❌ {error_msg}", flush=True)
                        log.error(f"  [STEP 1.2] ❌ {error_msg}")
                        raise ValueError(error_msg)
                    
                    print(f"  [STEP 1.2] ✅ API key validation passed", flush=True)
                    log.info(f"  [STEP 1.2] ✅ API key validation passed")
                    
                    # CRITICAL: Initialize EMBEDDING_FUNCTION per-job with the correct per-user/per-admin API key
                    # This ensures RBAC-protected API keys are used (each admin has their own key)
                    print(f"  [STEP 1.3] Initializing EMBEDDING_FUNCTION with per-job API key...", flush=True)
                    log.info(f"  [STEP 1.3] Initializing EMBEDDING_FUNCTION with per-job API key...")
                    
                    try:
                        request.app.state.initialize_embedding_function(embedding_api_key=embedding_api_key)
                        
                        if request.app.state.EMBEDDING_FUNCTION is None:
                            error_msg = (
                                f"❌ CRITICAL BUG: EMBEDDING_FUNCTION is None after initialization for file_id={file_id}. "
                                f"This will cause embedding generation to fail. "
                                f"Check: 1) API key is valid, 2) Base URL is correct, 3) Embedding model is configured"
                            )
                            print(f"  [STEP 1.3] ❌ {error_msg}", flush=True)
                            log.error(f"  [STEP 1.3] ❌ {error_msg}")
                            raise ValueError(error_msg)
                        else:
                            print(f"  [STEP 1.3] ✅ EMBEDDING_FUNCTION initialized successfully", flush=True)
                            print(f"    Function type: {type(request.app.state.EMBEDDING_FUNCTION)}", flush=True)
                            log.info(f"  [STEP 1.3] ✅ EMBEDDING_FUNCTION initialized successfully")
                            log.info(f"    Function type: {type(request.app.state.EMBEDDING_FUNCTION)}")
                    except ValueError as ve:
                        # Re-raise validation errors
                        raise
                    except Exception as init_error:
                        error_msg = f"Failed to initialize EMBEDDING_FUNCTION: {init_error}"
                        print(f"  [STEP 1.3] ❌ {error_msg}", flush=True)
                        log.error(f"  [STEP 1.3] ❌ {error_msg}", exc_info=True)
                        raise
                    sys.stdout.flush()
                except Exception as init_error:
                    print(f"  [STEP 1] ❌ Failed to initialize MockRequest for file_id={file_id}: {init_error}", flush=True)
                    log.error(f"  [STEP 1] ❌ Failed to initialize MockRequest for file_id={file_id}: {init_error}", exc_info=True)
                    sys.stdout.flush()
                    raise
                
                try:
                    # Get user object if user_id is provided
                    print(f"[STEP 2] Retrieving user and updating file status...", flush=True)
                    log.info(f"[STEP 2] Retrieving user and updating file status...")
                    user = None
                    if user_id:
                        print(f"  [STEP 2.1] user_id provided, retrieving user from database...", flush=True)
                        log.info(f"  [STEP 2.1] user_id provided, retrieving user from database...")
                        try:
                            user = Users.get_user_by_id(user_id)
                            print(f"  [STEP 2.1] Users.get_user_by_id({user_id}) returned: {user.email if user else 'None'}", flush=True)
                            log.info(f"  [STEP 2.1] Users.get_user_by_id({user_id}) returned: {user.email if user else 'None'}")
                            if not user:
                                log.warning(
                                    f"  [STEP 2.1] ⚠️  User {user_id} not found for file processing (file_id={file_id}), "
                                    "processing without user context"
                                )
                            else:
                                log.info(f"  [STEP 2.1] ✅ Retrieved user: email={user.email} | id={user.id} | role={user.role}")
                                
                                # CRITICAL: Set the user's API key in the config for save_docs_to_vector_db
                                # This ensures RBAC-protected API keys are used (each admin has their own key)
                                # Users inherit from their group admin's key
                                if embedding_api_key and user.email:
                                    log.info(f"  [STEP 2.2] Setting user's API key in config (RBAC-protected)...")
                                    try:
                                        # Update the config with the user's API key to ensure consistency
                                        # This is important because save_docs_to_vector_db retrieves the key from config
                                        if request.app.state.config.RAG_EMBEDDING_ENGINE in ["openai", "portkey"]:
                                            # Set the user's API key in the config cache (RBAC-protected)
                                            request.app.state.config.RAG_OPENAI_API_KEY.set(user.email, embedding_api_key)
                                            log.info(f"  [STEP 2.2] ✅ Set user's API key in config for {user.email} (RBAC-protected)")
                                        else:
                                            log.info(f"  [STEP 2.2] Skipped (engine is {request.app.state.config.RAG_EMBEDDING_ENGINE}, not openai/portkey)")
                                    except Exception as config_update_error:
                                        # Non-critical - the key is already passed and will be used as fallback
                                        log.warning(f"  [STEP 2.2] ⚠️  Could not update config with user API key: {config_update_error}")
                        except Exception as user_error:
                            log.warning(
                                f"  [STEP 2.1] ⚠️  Error retrieving user {user_id} for file processing (file_id={file_id}): {user_error}, "
                                "processing without user context", exc_info=True
                            )
                    else:
                        log.info(f"  [STEP 2.1] No user_id provided, processing without user context")
                    
                    # Update status to processing
                    log.info(f"  [STEP 2.3] Updating file status to 'processing'...")
                    processing_start_time = int(time.time())
                    Files.update_file_metadata_by_id(
                        file_id,
                        {
                            "processing_status": "processing",
                            "processing_started_at": processing_start_time,
                        },
                    )
                    log.info(f"  [STEP 2.3] ✅ File status updated: processing_status=processing, processing_started_at={processing_start_time}")
                    
                    print(f"[STEP 3] Retrieving file from database...", flush=True)
                    log.info(f"[STEP 3] Retrieving file from database...")
                    file = Files.get_file_by_id(file_id)
                    print(f"  [STEP 3] Files.get_file_by_id({file_id}) returned: {'File object' if file else 'None'}", flush=True)
                    log.info(f"  [STEP 3] Files.get_file_by_id({file_id}) returned: {'File object' if file else 'None'}")
                    sys.stdout.flush()
                    if not file:
                        error_msg = "File not found"
                        log.error(f"[JOB ERROR] File {file_id} not found for processing (user_id={user_id})")
                        add_span_event("job.file.not_found", {"file_id": file_id})
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
                        return {"status": "error", "error": error_msg}

                        print(f"  [STEP 3] ✅ File found:", flush=True)
                        print(f"    filename={file.filename}", flush=True)
                        print(f"    content_type={file.meta.get('content_type')}", flush=True)
                        print(f"    file.path={file.path}", flush=True)
                        print(f"    file.id={file.id}", flush=True)
                        print(f"    file.user_id={file.user_id}", flush=True)
                        print(f"    file.data.keys()={list(file.data.keys()) if file.data else 'None'}", flush=True)
                        print(f"    file.meta.keys()={list(file.meta.keys()) if file.meta else 'None'}", flush=True)
                        log.info(f"  [STEP 3] ✅ File found:")
                        log.info(f"    filename={file.filename}")
                        log.info(f"    content_type={file.meta.get('content_type')}")
                        log.info(f"    file.path={file.path}")
                        log.info(f"    file.id={file.id}")
                        log.info(f"    file.user_id={file.user_id}")
                        log.info(f"    file.data.keys()={list(file.data.keys()) if file.data else 'None'}")
                        log.info(f"    file.meta.keys()={list(file.meta.keys()) if file.meta else 'None'}")
                        sys.stdout.flush()

                    print(f"[STEP 4] Determining processing path...", flush=True)
                    log.info(f"[STEP 4] Determining processing path...")
                    # Determine the collection name for vector DB storage (always needed for saving)
                    # But don't use it to determine processing path - that depends on how file was uploaded
                    vector_collection_name = collection_name if collection_name else f"file-{file.id}"
                    print(f"  [STEP 4.1] Processing path determination:", flush=True)
                    print(f"    collection_name (from params)={collection_name}", flush=True)
                    print(f"    vector_collection_name (for storage)={vector_collection_name}", flush=True)
                    print(f"    content is not None: {content is not None}", flush=True)
                    log.info(f"  [STEP 4.1] Processing path determination:")
                    log.info(f"    collection_name (from params)={collection_name}")
                    log.info(f"    vector_collection_name (for storage)={vector_collection_name}")
                    log.info(f"    content is not None: {content is not None}")
                    sys.stdout.flush()

                    log.info(f"  [STEP 4.2] Checking processing path:")
                    log.info(f"    content is not None: {content is not None}")
                    log.info(f"    collection_name is not None: {collection_name is not None}")
                    
                    if content:
            print(f"  [STEP 4.2] ✅ Taking path: content provided (pre-extracted text)", flush=True)
            log.info(f"  [STEP 4.2] ✅ Taking path: content provided (pre-extracted text)")
            # Update the content in the file
            try:
                VECTOR_DB_CLIENT.delete_collection(collection_name=vector_collection_name)
            except:
                # Audio file upload pipeline - ignore deletion errors
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
            # Set collection_name for vector DB storage
            if not collection_name:
                collection_name = vector_collection_name
        elif collection_name:
            # File is from a knowledge collection - check if already processed
            print(f"  [STEP 4.2] ✅ Taking path: collection_name provided (from knowledge collection)", flush=True)
            log.info(f"  [STEP 4.2] ✅ Taking path: collection_name provided (from knowledge collection)")
            # Check if the file has already been processed and save the content
            print(f"  [STEP 5] Checking if file already processed in vector DB...", flush=True)
            log.info(f"  [STEP 5] Checking if file already processed in vector DB...")
            print(f"    Querying collection: {vector_collection_name}", flush=True)
            log.info(f"    Querying collection: {vector_collection_name}")
            print(f"    Filter: file_id={file.id}", flush=True)
            log.info(f"    Filter: file_id={file.id}")
            sys.stdout.flush()
            result = VECTOR_DB_CLIENT.query(
                collection_name=vector_collection_name, filter={"file_id": file.id}
            )
            log.info(f"  [STEP 5.1] Query result:")
            log.info(f"    result is not None: {result is not None}")
            if result:
                log.info(f"    result.ids: {result.ids}")
                log.info(f"    result.ids length: {len(result.ids[0]) if result.ids and len(result.ids) > 0 and result.ids[0] else 0}")

            if result is not None and result.ids and len(result.ids) > 0 and len(result.ids[0]) > 0:
                log.info(f"  [STEP 5.2] ✅ File already processed, using existing documents from vector DB")
                docs = [
                    Document(
                        page_content=result.documents[0][idx],
                        metadata=result.metadatas[0][idx],
                    )
                    for idx, id in enumerate(result.ids[0])
                ]
                log.info(f"    Created {len(docs)} document(s) from vector DB")
            else:
                print(f"  [STEP 5.2] File not in vector DB, checking file.data...", flush=True)
                log.info(f"  [STEP 5.2] File not in vector DB, checking file.data...")
                file_content = file.data.get("content", "")
                print(f"    file.data.get('content') length: {len(file_content)} chars", flush=True)
                log.info(f"    file.data.get('content') length: {len(file_content)} chars")
                sys.stdout.flush()
                
                # If file.data has no content, extract from file system
                if not file_content or len(file_content.strip()) == 0:
                    print(f"  [STEP 5.2.1] file.data content is empty, extracting from file system...", flush=True)
                    log.info(f"  [STEP 5.2.1] file.data content is empty, extracting from file system...")
                    # Extract content from file system (same logic as the else branch)
                    file_path = file.path
                    if file_path:
                        print(f"    file.path={file_path}", flush=True)
                        log.info(f"    file.path={file_path}")
                        try:
                            file_path = Storage.get_file(file_path)
                            print(f"    Storage.get_file() returned: {file_path}", flush=True)
                            log.info(f"    Storage.get_file() returned: {file_path}")
                            if file_path and os.path.exists(file_path):
                                file_size = os.path.getsize(file_path)
                                print(f"    File exists: True, size: {file_size} bytes", flush=True)
                                log.info(f"    File exists: True, size: {file_size} bytes")
                                
                                # Extract using Loader
                                # Safely get config values with defaults
                                # Use hasattr() first because AppConfig.__getattr__ raises KeyError for missing keys
                                extraction_engine_val = (getattr(request.app.state.config, 'CONTENT_EXTRACTION_ENGINE', None) if hasattr(request.app.state.config, 'CONTENT_EXTRACTION_ENGINE') else None) or os.environ.get('CONTENT_EXTRACTION_ENGINE', '') or "default (PyPDF)"
                                
                                # Only access engine-specific config if that engine is actually being used
                                tika_url_val = None
                                doc_intel_endpoint_val = None
                                doc_intel_key_val = None
                                
                                if extraction_engine_val and extraction_engine_val.lower() == 'tika':
                                    tika_url_val = (getattr(request.app.state.config, 'TIKA_SERVER_URL', None) if hasattr(request.app.state.config, 'TIKA_SERVER_URL') else None) or os.environ.get('TIKA_SERVER_URL', '')
                                elif extraction_engine_val and extraction_engine_val.lower() == 'document_intelligence':
                                    doc_intel_endpoint_val = (getattr(request.app.state.config, 'DOCUMENT_INTELLIGENCE_ENDPOINT', None) if hasattr(request.app.state.config, 'DOCUMENT_INTELLIGENCE_ENDPOINT') else None) or os.environ.get('DOCUMENT_INTELLIGENCE_ENDPOINT', '')
                                    doc_intel_key_val = (getattr(request.app.state.config, 'DOCUMENT_INTELLIGENCE_KEY', None) if hasattr(request.app.state.config, 'DOCUMENT_INTELLIGENCE_KEY') else None) or os.environ.get('DOCUMENT_INTELLIGENCE_KEY', '')
                                
                                pdf_extract_images_val = getattr(request.app.state.config, 'PDF_EXTRACT_IMAGES', False) if hasattr(request.app.state.config, 'PDF_EXTRACT_IMAGES') else False
                                
                                print(f"    [STEP 5.2.1.1] Loader parameters:", flush=True)
                                print(f"      engine={extraction_engine_val}", flush=True)
                                print(f"      TIKA_SERVER_URL={tika_url_val if tika_url_val else 'None (PyPDF will be used)'}", flush=True)
                                print(f"      PDF_EXTRACT_IMAGES={pdf_extract_images_val}", flush=True)
                                print(f"      DOCUMENT_INTELLIGENCE_ENDPOINT={'SET' if doc_intel_endpoint_val else 'None'}", flush=True)
                                print(f"      DOCUMENT_INTELLIGENCE_KEY={'SET' if doc_intel_key_val else 'None'}", flush=True)
                                log.info(f"    [STEP 5.2.1.1] Loader parameters:")
                                log.info(f"      engine={extraction_engine_val}")
                                log.info(f"      TIKA_SERVER_URL={tika_url_val if tika_url_val else 'None (PyPDF will be used)'}")
                                log.info(f"      PDF_EXTRACT_IMAGES={pdf_extract_images_val}")
                                log.info(f"      DOCUMENT_INTELLIGENCE_ENDPOINT={'SET' if doc_intel_endpoint_val else 'None'}")
                                log.info(f"      DOCUMENT_INTELLIGENCE_KEY={'SET' if doc_intel_key_val else 'None'}")
                                sys.stdout.flush()
                                
                                loader = Loader(
                                    engine=extraction_engine_val,
                                    TIKA_SERVER_URL=tika_url_val if tika_url_val else None,
                                    PDF_EXTRACT_IMAGES=pdf_extract_images_val,
                                    DOCUMENT_INTELLIGENCE_ENDPOINT=doc_intel_endpoint_val if doc_intel_endpoint_val else None,
                                    DOCUMENT_INTELLIGENCE_KEY=doc_intel_key_val if doc_intel_key_val else None,
                                )
                                print(f"    Calling loader.load()...", flush=True)
                                log.info(f"    Calling loader.load()...")
                                docs = loader.load(
                                    file.filename, file.meta.get("content_type"), file_path
                                )
                                print(f"    loader.load() returned {len(docs)} document(s)", flush=True)
                                log.info(f"    loader.load() returned {len(docs)} document(s)")
                                
                                # Log extraction results
                                total_chars = sum(len(doc.page_content) for doc in docs)
                                non_empty_docs = [doc for doc in docs if doc.page_content.strip()]
                                print(f"    Extraction results: total_chars={total_chars}, non_empty_docs={len(non_empty_docs)}", flush=True)
                                log.info(f"    Extraction results: total_chars={total_chars}, non_empty_docs={len(non_empty_docs)}")
                                
                                # Add event for file extraction
                                add_span_event("job.file.extracted", {
                                    "content_length": total_chars,
                                    "document.count": len(docs),
                                })
                                
                                # Create documents with metadata
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
                                text_content = " ".join([doc.page_content for doc in docs])
                                print(f"    Created {len(docs)} document(s) from file extraction", flush=True)
                                log.info(f"    Created {len(docs)} document(s) from file extraction")
                            else:
                                print(f"    File path is None or does not exist, using empty content", flush=True)
                                log.warning(f"    File path is None or does not exist, using empty content")
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
                                text_content = ""
                        except Exception as storage_error:
                            print(f"    ❌ Failed to get file from storage: {storage_error}", flush=True)
                            log.error(f"    ❌ Failed to get file from storage: {storage_error}", exc_info=True)
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
                            text_content = ""
                    else:
                        print(f"    file.path is None, using empty content", flush=True)
                        log.warning(f"    file.path is None, using empty content")
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
                        text_content = ""
                    sys.stdout.flush()
                else:
                    # Use content from file.data
                    print(f"  [STEP 5.2.2] Using content from file.data ({len(file_content)} chars)", flush=True)
                    log.info(f"  [STEP 5.2.2] Using content from file.data ({len(file_content)} chars)")
                    docs = [
                        Document(
                            page_content=file_content,
                            metadata={
                                **file.meta,
                                "name": file.filename,
                                "created_by": file.user_id,
                                "file_id": file.id,
                                "source": file.filename,
                            },
                        )
                    ]
                    text_content = file_content
                    print(f"    Created {len(docs)} document(s) from file.data", flush=True)
                    log.info(f"    Created {len(docs)} document(s) from file.data")
                    sys.stdout.flush()

            if 'text_content' not in locals():
                text_content = file.data.get("content", "")
            print(f"  [STEP 5.3] text_content length: {len(text_content)} chars", flush=True)
            log.info(f"  [STEP 5.3] text_content length: {len(text_content)} chars")
            sys.stdout.flush()
            # Set collection_name for vector DB storage
            if not collection_name:
                collection_name = vector_collection_name
        else:
            # Direct upload via chat (no collection_name, no content) - extract from file system
            print(f"  [STEP 4.2] ✅ Taking path: else (direct upload, extract content from file)", flush=True)
            log.info(f"  [STEP 4.2] ✅ Taking path: else (direct upload, extract content from file)")
            # Set collection_name for vector DB storage
            collection_name = vector_collection_name
            # Process the file and save the content
            file_path = file.path
            print(f"[STEP 5] Extracting content from file...", flush=True)
            print(f"  [STEP 5.1] file.path={file_path}", flush=True)
            log.info(f"[STEP 5] Extracting content from file...")
            log.info(f"  [STEP 5.1] file.path={file_path}")
            sys.stdout.flush()
            if file_path:
                print(f"  [STEP 5.2] file_path is not None, retrieving from storage...", flush=True)
                log.info(f"  [STEP 5.2] file_path is not None, retrieving from storage...")
                try:
                    file_path = Storage.get_file(file_path)
                    print(f"  [STEP 5.2] ✅ Storage.get_file() returned: {file_path}", flush=True)
                    if file_path:
                        file_exists = os.path.exists(file_path) if file_path else False
                        file_size = os.path.getsize(file_path) if file_exists else 0
                        print(f"    File exists: {file_exists}", flush=True)
                        print(f"    File size: {file_size} bytes", flush=True)
                    log.info(f"  [STEP 5.2] ✅ Storage.get_file() returned: {file_path}")
                    if file_path and os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        log.info(f"    File exists: True")
                        log.info(f"    File size: {file_size} bytes")
                except Exception as storage_error:
                    print(f"  [STEP 5.2] ❌ Failed to get file from storage: {storage_error}", flush=True)
                    log.error(f"  [STEP 5.2] ❌ Failed to get file from storage: {storage_error}", exc_info=True)
                    file_path = None
                sys.stdout.flush()
                
                if file_path:
                    # Log extraction engine being used (safely get config)
                    # Use hasattr() first because AppConfig.__getattr__ raises KeyError for missing keys
                    extraction_engine = (getattr(request.app.state.config, 'CONTENT_EXTRACTION_ENGINE', None) if hasattr(request.app.state.config, 'CONTENT_EXTRACTION_ENGINE') else None) or os.environ.get('CONTENT_EXTRACTION_ENGINE', '') or "default (PyPDF)"
                    print(f"  [STEP 5.3] Initializing content extraction loader...", flush=True)
                    print(f"    extraction_engine={extraction_engine}", flush=True)
                    
                    # Only access engine-specific config if that engine is actually being used
                    # Default is PyPDF, which doesn't need any of these configs
                    tika_url = None
                    doc_intel_endpoint = None
                    doc_intel_key = None
                    
                    if extraction_engine and extraction_engine.lower() == 'tika':
                        # Only access Tika config if Tika is the extraction engine
                        tika_url = (getattr(request.app.state.config, 'TIKA_SERVER_URL', None) if hasattr(request.app.state.config, 'TIKA_SERVER_URL') else None) or os.environ.get('TIKA_SERVER_URL', '')
                    elif extraction_engine and extraction_engine.lower() == 'document_intelligence':
                        # Only access Document Intelligence config if that's the extraction engine
                        doc_intel_endpoint = (getattr(request.app.state.config, 'DOCUMENT_INTELLIGENCE_ENDPOINT', None) if hasattr(request.app.state.config, 'DOCUMENT_INTELLIGENCE_ENDPOINT') else None) or os.environ.get('DOCUMENT_INTELLIGENCE_ENDPOINT', '')
                        doc_intel_key = (getattr(request.app.state.config, 'DOCUMENT_INTELLIGENCE_KEY', None) if hasattr(request.app.state.config, 'DOCUMENT_INTELLIGENCE_KEY') else None) or os.environ.get('DOCUMENT_INTELLIGENCE_KEY', '')
                    
                    # PDF_EXTRACT_IMAGES can be used with any engine
                    pdf_extract_images = getattr(request.app.state.config, 'PDF_EXTRACT_IMAGES', False) if hasattr(request.app.state.config, 'PDF_EXTRACT_IMAGES') else False
                    print(f"    TIKA_SERVER_URL={tika_url if tika_url else 'None (not using Tika)'}", flush=True)
                    print(f"    PDF_EXTRACT_IMAGES={pdf_extract_images}", flush=True)
                    print(f"    DOCUMENT_INTELLIGENCE_ENDPOINT={'SET' if doc_intel_endpoint else 'None'}", flush=True)
                    print(f"    DOCUMENT_INTELLIGENCE_KEY={'SET' if doc_intel_key else 'None'}", flush=True)
                    print(f"    filename={file.filename}", flush=True)
                    print(f"    content_type={file.meta.get('content_type')}", flush=True)
                    print(f"    file_path={file_path}", flush=True)
                    log.info(
                        f"[Content Extraction] file_id={file.id} | filename={file.filename} | "
                        f"content_type={file.meta.get('content_type')} | engine={extraction_engine} | file_path={file_path}"
                    )
                    log.info(f"  [STEP 5.3] Initializing content extraction loader...")
                    log.info(f"    extraction_engine={extraction_engine}")
                    log.info(f"    TIKA_SERVER_URL={tika_url if tika_url else 'None (not using Tika)'}")
                    log.info(f"    PDF_EXTRACT_IMAGES={pdf_extract_images}")
                    log.info(f"    DOCUMENT_INTELLIGENCE_ENDPOINT={'SET' if doc_intel_endpoint else 'None'}")
                    log.info(f"    DOCUMENT_INTELLIGENCE_KEY={'SET' if doc_intel_key else 'None'}")
                    log.info(f"    filename={file.filename}")
                    log.info(f"    content_type={file.meta.get('content_type')}")
                    log.info(f"    file_path={file_path}")
                    sys.stdout.flush()
                
                    # Safely get config values with defaults
                    # Use hasattr() first because AppConfig.__getattr__ raises KeyError for missing keys
                    extraction_engine_val = (getattr(request.app.state.config, 'CONTENT_EXTRACTION_ENGINE', None) if hasattr(request.app.state.config, 'CONTENT_EXTRACTION_ENGINE') else None) or os.environ.get('CONTENT_EXTRACTION_ENGINE', '') or "default (PyPDF)"
                    
                    # Only access engine-specific config if that engine is actually being used
                    tika_url_val = None
                    doc_intel_endpoint_val = None
                    doc_intel_key_val = None
                    
                    if extraction_engine_val and extraction_engine_val.lower() == 'tika':
                        tika_url_val = (getattr(request.app.state.config, 'TIKA_SERVER_URL', None) if hasattr(request.app.state.config, 'TIKA_SERVER_URL') else None) or os.environ.get('TIKA_SERVER_URL', '')
                    elif extraction_engine_val and extraction_engine_val.lower() == 'document_intelligence':
                        doc_intel_endpoint_val = (getattr(request.app.state.config, 'DOCUMENT_INTELLIGENCE_ENDPOINT', None) if hasattr(request.app.state.config, 'DOCUMENT_INTELLIGENCE_ENDPOINT') else None) or os.environ.get('DOCUMENT_INTELLIGENCE_ENDPOINT', '')
                        doc_intel_key_val = (getattr(request.app.state.config, 'DOCUMENT_INTELLIGENCE_KEY', None) if hasattr(request.app.state.config, 'DOCUMENT_INTELLIGENCE_KEY') else None) or os.environ.get('DOCUMENT_INTELLIGENCE_KEY', '')
                    
                    pdf_extract_images_val = getattr(request.app.state.config, 'PDF_EXTRACT_IMAGES', False) if hasattr(request.app.state.config, 'PDF_EXTRACT_IMAGES') else False
                    
                    print(f"  [STEP 5.3.1] Loader parameters:", flush=True)
                    print(f"    engine={extraction_engine_val}", flush=True)
                    print(f"    TIKA_SERVER_URL={tika_url_val if tika_url_val else 'None (PyPDF will be used)'}", flush=True)
                    print(f"    PDF_EXTRACT_IMAGES={pdf_extract_images_val}", flush=True)
                    print(f"    DOCUMENT_INTELLIGENCE_ENDPOINT={'SET' if doc_intel_endpoint_val else 'None'}", flush=True)
                    print(f"    DOCUMENT_INTELLIGENCE_KEY={'SET' if doc_intel_key_val else 'None'}", flush=True)
                    log.info(f"  [STEP 5.3.1] Loader parameters:")
                    log.info(f"    engine={extraction_engine_val}")
                    log.info(f"    TIKA_SERVER_URL={tika_url_val if tika_url_val else 'None (PyPDF will be used)'}")
                    log.info(f"    PDF_EXTRACT_IMAGES={pdf_extract_images_val}")
                    log.info(f"    DOCUMENT_INTELLIGENCE_ENDPOINT={'SET' if doc_intel_endpoint_val else 'None'}")
                    log.info(f"    DOCUMENT_INTELLIGENCE_KEY={'SET' if doc_intel_key_val else 'None'}")
                    sys.stdout.flush()
                    
                    loader = Loader(
                        engine=extraction_engine_val,
                        TIKA_SERVER_URL=tika_url_val if tika_url_val else None,
                        PDF_EXTRACT_IMAGES=pdf_extract_images_val,
                        DOCUMENT_INTELLIGENCE_ENDPOINT=doc_intel_endpoint_val if doc_intel_endpoint_val else None,
                        DOCUMENT_INTELLIGENCE_KEY=doc_intel_key_val if doc_intel_key_val else None,
                    )
                    print(f"  [STEP 5.4] ✅ Loader created, calling loader.load()...", flush=True)
                    print(f"    filename={file.filename}", flush=True)
                    print(f"    content_type={file.meta.get('content_type')}", flush=True)
                    print(f"    file_path={file_path}", flush=True)
                    log.info(f"  [STEP 5.4] ✅ Loader created, calling loader.load()...")
                    log.info(f"    filename={file.filename}")
                    log.info(f"    content_type={file.meta.get('content_type')}")
                    log.info(f"    file_path={file_path}")
                    sys.stdout.flush()
                    try:
                        print(f"  [STEP 5.4.1] Calling loader.load(filename='{file.filename}', content_type='{file.meta.get('content_type')}', file_path='{file_path}')...", flush=True)
                        log.info(f"  [STEP 5.4.1] Calling loader.load()...")
                        docs = loader.load(
                            file.filename, file.meta.get("content_type"), file_path
                        )
                        print(f"  [STEP 5.4.2] ✅ loader.load() completed successfully", flush=True)
                        print(f"    Returned {len(docs)} document(s)", flush=True)
                        log.info(f"  [STEP 5.4.2] ✅ loader.load() completed successfully")
                        log.info(f"    Returned {len(docs)} document(s)")
                        if len(docs) > 0:
                            print(f"    First doc type: {type(docs[0])}", flush=True)
                            print(f"    First doc has page_content: {hasattr(docs[0], 'page_content')}", flush=True)
                            if hasattr(docs[0], 'page_content'):
                                first_doc_len = len(docs[0].page_content)
                                first_doc_preview = docs[0].page_content[:200] + "..." if first_doc_len > 200 else docs[0].page_content
                                print(f"    First doc page_content length: {first_doc_len} chars", flush=True)
                                print(f"    First doc preview: {first_doc_preview}", flush=True)
                                log.info(f"    First doc page_content length: {first_doc_len} chars")
                                log.info(f"    First doc preview: {first_doc_preview[:200]}...")
                    except Exception as load_error:
                        print(f"  [STEP 5.4.2] ❌ loader.load() failed with exception:", flush=True)
                        print(f"    Exception type: {type(load_error).__name__}", flush=True)
                        print(f"    Exception message: {str(load_error)}", flush=True)
                        log.error(f"  [STEP 5.4.2] ❌ loader.load() failed: {load_error}", exc_info=True)
                        docs = []
                    sys.stdout.flush()
                    
                    # Log extraction results for debugging
                    print(f"  [STEP 5.5] Analyzing extraction results...", flush=True)
                    log.info(f"  [STEP 5.5] Analyzing extraction results...")
                    total_chars = sum(len(doc.page_content) for doc in docs) if docs else 0
                    non_empty_docs = [doc for doc in docs if doc.page_content.strip()] if docs else []
                    print(f"  [STEP 5.5] Extraction results:", flush=True)
                    print(f"    Total documents: {len(docs)}", flush=True)
                    print(f"    Non-empty documents: {len(non_empty_docs)}", flush=True)
                    print(f"    Total characters: {total_chars}", flush=True)
                    if len(docs) > 0:
                        for idx, doc in enumerate(docs[:3]):  # Show first 3 docs
                            doc_len = len(doc.page_content) if hasattr(doc, 'page_content') else 0
                            doc_preview = doc.page_content[:150] + "..." if doc_len > 150 else (doc.page_content if hasattr(doc, 'page_content') else 'NO page_content')
                            print(f"    Doc[{idx}] length: {doc_len} chars", flush=True)
                            print(f"    Doc[{idx}] preview: {doc_preview}", flush=True)
                            log.info(f"    Doc[{idx}] length: {doc_len} chars")
                            log.info(f"    Doc[{idx}] preview: {doc_preview[:150]}...")
                    else:
                        print(f"    ⚠️  WARNING: No documents returned from loader.load()!", flush=True)
                        log.warning(f"    ⚠️  WARNING: No documents returned from loader.load()!")
                    log.info(
                        f"[Content Extraction Result] file_id={file.id} | "
                        f"pages_extracted={len(docs)} | non_empty_pages={len(non_empty_docs)} | "
                        f"total_chars={total_chars}"
                    )
                    sys.stdout.flush()
                
                    # BUG #15 fix: Fail early if extraction returned empty content
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
                            f"  - Current engine: {extraction_engine_val}"
                        )
                        print(f"  [STEP 5.5.1] ❌ {error_msg}", flush=True)
                        log.error(error_msg)
                        # Update file status to error
                        Files.update_file_metadata_by_id(
                            file.id,
                            {
                                "processing_status": "error",
                                "processing_error": error_msg,
                            },
                        )
                        raise ValueError(f"Content extraction returned empty text for file {file.filename}. {error_msg}")
                        print(f"      - Scanned image PDF (no OCR text layer)", flush=True)
                        print(f"      - Protected/encrypted file", flush=True)
                        print(f"      - Unsupported encoding", flush=True)
                        print(f"      - Loader failed silently", flush=True)
                        print(f"      - PyPDF extraction failed (check file format)", flush=True)
                        log.warning(
                            f"[Content Extraction WARNING] file_id={file.id} | filename={file.filename} | "
                            f"No text content extracted! Possible reasons:\n"
                            f"  - Scanned image PDF (no OCR text layer)\n"
                            f"  - Protected/encrypted file\n"
                            f"  - Unsupported encoding\n"
                            f"  - Loader failed silently\n"
                            f"  - PyPDF extraction failed (check file format)\n"
                            f"  Suggestions:\n"
                            f"  - For scanned PDFs: Enable Document Intelligence (Azure OCR) in Settings > Documents\n"
                            f"  - For better extraction: Configure Tika server\n"
                            f"  - Current engine: {extraction_engine_val}"
                        )
                        sys.stdout.flush()

                print(f"  [STEP 5.6] Creating Document objects with metadata...", flush=True)
                log.info(f"  [STEP 5.6] Creating Document objects with metadata...")
                print(f"    Input docs count: {len(docs)}", flush=True)
                log.info(f"    Input docs count: {len(docs)}")
                sys.stdout.flush()
                
                docs_with_metadata = []
                for idx, doc in enumerate(docs):
                    if not hasattr(doc, 'page_content'):
                        print(f"    ⚠️  Doc[{idx}] has no page_content attribute, skipping", flush=True)
                        log.warning(f"    ⚠️  Doc[{idx}] has no page_content attribute, skipping")
                        continue
                    doc_metadata = getattr(doc, 'metadata', {}) or {}
                    new_doc = Document(
                        page_content=doc.page_content,
                        metadata={
                            **doc_metadata,
                            "name": file.filename,
                            "created_by": file.user_id,
                            "file_id": file.id,
                            "source": file.filename,
                        },
                    )
                    docs_with_metadata.append(new_doc)
                    if idx < 3:  # Log first 3
                        print(f"    Doc[{idx}] created: page_content_len={len(doc.page_content)}, metadata_keys={list(new_doc.metadata.keys())}", flush=True)
                        log.info(f"    Doc[{idx}] created: page_content_len={len(doc.page_content)}, metadata_keys={list(new_doc.metadata.keys())}")
                
                docs = docs_with_metadata
                print(f"    Final docs count: {len(docs)}", flush=True)
                log.info(f"    Final docs count: {len(docs)}")
                sys.stdout.flush()
                
                text_content = " ".join([doc.page_content for doc in docs if hasattr(doc, 'page_content')])
                print(f"  [STEP 5.7] Combined text_content length: {len(text_content)} chars", flush=True)
                log.info(f"  [STEP 5.7] Combined text_content length: {len(text_content)} chars")
                sys.stdout.flush()
            else:
                # No file path - use empty content (should not happen normally)
                log.warning(f"[Content Extraction] file_id={file.id} | No file path available, using empty content")
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

        # Validate that we have content to process
        log.info(f"[STEP 6] Validating extracted content...")
        from open_webui.constants import ERROR_MESSAGES
        
        log.info(f"  [STEP 6.1] Checking docs list:")
        log.info(f"    docs is not None: {docs is not None}")
        log.info(f"    len(docs): {len(docs) if docs else 0}")
        
        if not docs or len(docs) == 0:
            error_msg = ERROR_MESSAGES.EMPTY_CONTENT
            log.error(f"  [STEP 6.1] ❌ No documents extracted for file_id={file.id} | filename={file.filename}")
            Files.update_file_metadata_by_id(
                file.id,
                {
                    "processing_status": "error",
                    "processing_error": error_msg,
                },
            )
            raise ValueError(error_msg)
        
        # Also check if all docs are empty (no actual content)
        log.info(f"  [STEP 6.2] Checking document content...")
        total_chars = sum(len(doc.page_content) for doc in docs)
        log.info(f"    total_chars: {total_chars}")
        for i, doc in enumerate(docs):
            log.info(f"    doc[{i}].page_content length: {len(doc.page_content)} chars")
        
        if total_chars == 0:
            error_msg = ERROR_MESSAGES.EMPTY_CONTENT
            log.error(f"  [STEP 6.2] ❌ All extracted content is empty for file_id={file.id} | filename={file.filename}")
            Files.update_file_metadata_by_id(
                file.id,
                {
                    "processing_status": "error",
                    "processing_error": error_msg,
                },
            )
            raise ValueError(error_msg)

        log.info(f"  [STEP 6.2] ✅ Content validation passed")
        log.info(f"    text_content length: {len(text_content)} chars")
        log.info(f"    docs count: {len(docs)}")
        
        log.info(f"[STEP 7] Saving content to file record...")
        Files.update_file_data_by_id(
            file.id,
            {"content": text_content},
        )
        log.info(f"  [STEP 7] ✅ Content saved to file record")

        log.info(f"[STEP 8] Calculating file hash...")
        hash = calculate_sha256_string(text_content)
        log.info(f"  [STEP 8] ✅ Hash calculated: {hash[:16]}...")
        Files.update_file_hash_by_id(file.id, hash)
        log.info(f"  [STEP 8] ✅ Hash saved to file record")

        log.info(f"[STEP 9] Saving documents to vector database...")
        # Safely access BYPASS_EMBEDDING_AND_RETRIEVAL - use hasattr() first because AppConfig.__getattr__ raises KeyError for missing keys
        bypass_embedding = getattr(request.app.state.config, 'BYPASS_EMBEDDING_AND_RETRIEVAL', False) if hasattr(request.app.state.config, 'BYPASS_EMBEDDING_AND_RETRIEVAL') else False
        log.info(f"  BYPASS_EMBEDDING_AND_RETRIEVAL={bypass_embedding}")
        
        if not bypass_embedding:
            try:
                # If knowledge_id is provided, we're adding to both collections at once
                if knowledge_id:
                    log.info(f"  [STEP 9.1] knowledge_id provided, saving to multiple collections...")
                    file_collection = f"file-{file.id}"
                    collections = [file_collection, knowledge_id]
                    log.info(f"    file_collection={file_collection}")
                    log.info(f"    knowledge_id={knowledge_id}")
                    log.info(f"    collections={collections}")
                    log.info(f"    docs count={len(docs)}")
                    log.info(f"    user={'SET (' + user.email + ')' if user else 'None'}")

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
                    log.info(f"  [STEP 9.1] save_docs_to_multiple_collections() returned: {result}")

                    # Use file collection name for file metadata
                    if result:
                        log.info(f"  [STEP 9.1] ✅ Successfully saved to vector DB")
                        add_span_event("job.embedding.completed", {"status": "success", "collection_name": file_collection})
                        Files.update_file_metadata_by_id(
                            file.id,
                            {
                                "collection_name": file_collection,
                                "processing_status": "completed",
                                "processing_completed_at": int(time.time()),
                            },
                        )
                        log.info(f"  [STEP 9.1] ✅ File metadata updated: status=completed")
                    else:
                        log.error(f"  [STEP 9.1] ❌ Failed to save to vector DB")
                        Files.update_file_metadata_by_id(
                            file.id,
                            {
                                "processing_status": "error",
                                "processing_error": "Failed to save to vector DB",
                            },
                        )
                else:
                    log.info(f"  [STEP 9.2] No knowledge_id, saving to single collection...")
                    log.info(f"    collection_name={collection_name}")
                    log.info(f"    docs count={len(docs)}")
                    log.info(f"    add={True if collection_name else False}")
                    log.info(f"    user={'SET (' + user.email + ')' if user else 'None'}")
                    
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
                    log.info(f"  [STEP 9.2] save_docs_to_vector_db() returned: {result}")

                    if result:
                        log.info(f"  [STEP 9.2] ✅ Successfully saved to vector DB")
                        Files.update_file_metadata_by_id(
                            file.id,
                            {
                                "collection_name": collection_name,
                                "processing_status": "completed",
                                "processing_completed_at": int(time.time()),
                            },
                        )
                        log.info(f"  [STEP 9.2] ✅ File metadata updated: status=completed, collection_name={collection_name}")
                    else:
                        log.error(f"  [STEP 9.2] ❌ Failed to save to vector DB")
                        Files.update_file_metadata_by_id(
                            file.id,
                            {
                                "processing_status": "error",
                                "processing_error": "Failed to save to vector DB",
                            },
                        )
            except Exception as e:
                error_msg = str(e)
                log.error(f"  [STEP 9] ❌ Exception during vector DB save: {error_msg}", exc_info=True)
                log.error(
                    f"Error saving file to vector DB: file_id={file.id}, "
                    f"filename={file.filename}, user_id={user_id}, error={error_msg}"
                )
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
                return {"status": "error", "error": error_msg}
        else:
            log.info(f"  [STEP 9] BYPASS_EMBEDDING_AND_RETRIEVAL=True, skipping vector DB save")
            Files.update_file_metadata_by_id(
                file.id,
                {
                    "processing_status": "completed",
                    "processing_completed_at": int(time.time()),
                },
            )
            log.info(f"  [STEP 9] ✅ File metadata updated: status=completed (bypassed embedding)")

            elapsed_time = time.time() - start_time
            log.info("=" * 80)
            log.info(f"[JOB SUCCESS] File processing completed successfully")
            log.info(f"  file_id={file_id}")
            log.info(f"  collection_name={collection_name}")
            log.info(f"  elapsed_time={elapsed_time:.2f}s")
            log.info(f"  END_TIME={time.time()}")
            log.info("=" * 80)
            
            add_span_event("job.completed", {
                "duration_ms": int(elapsed_time * 1000),
                "file_id": file_id,
            })
            if span:
                set_span_attribute("job.duration_ms", int(elapsed_time * 1000))

            return {
                "status": "success",
                "file_id": file_id,
                "collection_name": collection_name,
                "elapsed_time": elapsed_time,
            }

        except Exception as e:
            # Consolidated error handling - log and update status
            elapsed_time = time.time() - start_time
            error_msg = str(e)
            log.error("=" * 80)
            log.error(f"[JOB FAILED] Error in file processing job")
            log.error(f"  file_id={file_id}")
            log.error(f"  user_id={user_id}")
            log.error(f"  elapsed_time={elapsed_time:.2f}s")
            log.error(f"  error_type={type(e).__name__}")
            log.error(f"  error_message={error_msg}")
            log.error(f"  END_TIME={time.time()}")
            log.error("=" * 80)
            log.error(f"Full traceback:", exc_info=True)
            
            add_span_event("job.failed", {
                "error.type": type(e).__name__,
                "error.message": error_msg[:200],
                "duration_ms": int(elapsed_time * 1000),
            })
            
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
            
            # Re-raise the exception so RQ knows the job failed and can retry
            raise
        finally:
            # CRITICAL: Clean up resources to prevent leaks
            # This block executes regardless of whether the job succeeded or failed
            # 1. Clean up database session registry (scoped_session cleanup)
            try:
                Session.remove()
                log.debug("Cleaned up database session registry (Session.remove())")
            except Exception as session_cleanup_error:
                # Log but don't fail - cleanup errors shouldn't break the job result
                log.warning(f"Error cleaning up database session registry: {session_cleanup_error}")
            
            # 2. Clean up per-job embedding function to free resources
            # Note: ef and rf are reused across jobs, so we don't clean those up
            try:
                if request is not None and hasattr(request, 'app') and hasattr(request.app, 'state'):
                    if hasattr(request.app.state, 'EMBEDDING_FUNCTION'):
                        request.app.state.EMBEDDING_FUNCTION = None
                        log.debug("Cleaned up per-job EMBEDDING_FUNCTION")
            except Exception as embedding_cleanup_error:
                # Log but don't fail - cleanup errors shouldn't break the job result
                log.warning(f"Error cleaning up embedding function: {embedding_cleanup_error}")
            
            # Detach trace context if it was attached
            if context_token is not None:
                try:
                    from opentelemetry import context
                    context.detach(context_token)
                    log.debug(f"Detached trace context for job: file_id={file_id}")
                except Exception as detach_error:
                    log.debug(f"Failed to detach trace context: {detach_error}")

