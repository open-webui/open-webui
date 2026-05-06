"""
File Processing Worker for RQ Job Queue

This module contains the worker function that processes file jobs enqueued in Redis.
Workers run in separate processes and can be distributed across multiple pods.
"""

import logging
import os
import sys
import time
from typing import Optional

# Ensure logging is configured for worker process
# The worker process redirects stdout/stderr to /tmp/rq-worker.log
# So we need to ensure logs go to stdout/stderr
# Check if Loguru's InterceptHandler is already configured (from start_logger())
has_loguru_handler = any(
    'InterceptHandler' in str(type(h)) for h in logging.root.handlers
)

if not logging.root.handlers or not has_loguru_handler:
    # Configure basic logging only if Loguru is not active
    # This provides fallback logging for tests or standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
        stream=sys.stdout,
        force=True
    )

# Import os early for environment variable access in fallback config

from langchain_core.documents import Document

from open_webui.models.files import Files
from open_webui.models.users import Users
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
    RAG_EMBEDDING_MODEL_USER,  # RBAC: Per-admin model name
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
    # Additional UserScopedConfig objects used in worker code paths
    RAG_TEMPLATE,  # Used in _get_user_chunk_settings
    RAG_TOP_K,  # Used in retrieval queries (aliased as TOP_K)
    ENABLE_RAG_HYBRID_SEARCH,  # Used in retrieval queries
    RAG_FULL_CONTEXT,  # Used in config endpoints
    RAG_RELEVANCE_THRESHOLD,  # PersistentConfig, used in retrieval
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
        from contextlib import nullcontext
        # Use nullcontext which properly handles exceptions
        return nullcontext(enter_result=None)
    def add_span_event(*args, **kwargs):
        pass
    def set_span_attribute(*args, **kwargs):
        pass
    def is_otel_enabled():
        return False

# Initialize logger early (before safe wrapper functions that may use it)
log = logging.getLogger(__name__)
# Ensure logger is configured for worker process - use INFO level to capture all detailed logs
log.setLevel(logging.INFO)

# Check if Loguru's InterceptHandler is active (from start_logger())
# This prevents duplicate logging: if Loguru is active, use propagation only
# If Loguru is not active (e.g., in tests), add a fallback handler
has_loguru_handler = any(
    'InterceptHandler' in str(type(h)) for h in logging.root.handlers
)

if has_loguru_handler:
    # Loguru is active - use propagation only to avoid duplicate logs
    # Logs will go: module logger → root logger → InterceptHandler → Loguru
    log.propagate = True
else:
    # Loguru is not active (e.g., in tests or standalone execution)
    # Add a direct handler as fallback to ensure logs are visible
    log.propagate = False
if not any(isinstance(h, logging.StreamHandler) for h in log.handlers):
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(logging.Formatter('%(levelname)s [%(name)s] %(message)s'))
    log.addHandler(stdout_handler)

# Safe wrapper functions that NEVER fail - OTEL is monitoring only, must not affect task execution
def safe_add_span_event(event_name, attributes=None):
    """Safely add span event - never fails, even if OTEL is broken"""
    try:
        add_span_event(event_name, attributes)
    except Exception as e:
        log.debug(f"OTEL add_span_event failed (non-critical): {e}")

def safe_set_span_attribute(span, key, value):
    """Safely set span attribute - never fails, even if OTEL is broken"""
    try:
        if span:
            set_span_attribute(span, key, value)
    except Exception as e:
        log.debug(f"OTEL set_span_attribute failed (non-critical): {e}")

def safe_trace_span(*args, **kwargs):
    """Safely create trace span - never fails, even if OTEL is broken"""
    try:
        return trace_span(*args, **kwargs)
    except Exception as e:
        log.debug(f"OTEL trace_span failed (non-critical), using nullcontext: {e}")
        from contextlib import nullcontext
        return nullcontext(enter_result=None)

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
            _worker_config.RAG_EMBEDDING_MODEL_USER = RAG_EMBEDDING_MODEL_USER  # RBAC: Per-admin model name
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
            # Additional UserScopedConfig objects used in worker code paths
            _worker_config.RAG_TEMPLATE = RAG_TEMPLATE  # Used in _get_user_chunk_settings
            _worker_config.TOP_K = RAG_TOP_K  # Used in retrieval queries (aliased as TOP_K in main.py)
            _worker_config.RAG_TOP_K = RAG_TOP_K  # Also set alias for compatibility
            _worker_config.ENABLE_RAG_HYBRID_SEARCH = ENABLE_RAG_HYBRID_SEARCH  # Used in retrieval queries
            _worker_config.RAG_FULL_CONTEXT = RAG_FULL_CONTEXT  # Used in config endpoints
            _worker_config.RELEVANCE_THRESHOLD = RAG_RELEVANCE_THRESHOLD  # PersistentConfig, used in retrieval
            # CRITICAL: Force PDF_EXTRACT_IMAGES to False to prevent hangs (image extraction causes 2+ minute slowdowns)
            # First assign the PersistentConfig object (like main.py does), then override its value
            PDF_EXTRACT_IMAGES.value = False
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
    
    def initialize_embedding_function(self, embedding_api_key: Optional[str] = None, embedding_model: Optional[str] = None):
        """
        Initialize EMBEDDING_FUNCTION with the correct per-user/per-admin API key and model.
        This is called per-job to ensure RBAC-protected API keys and models are used.
        
        Args:
            embedding_api_key: Per-user/per-admin API key from job (RBAC-protected)
            embedding_model: Per-user/per-admin model name from job (RBAC-protected)
        """
        # Use the passed API key (from job) or the one stored during initialization
        api_key = embedding_api_key or self._embedding_api_key
        
        try:
            # Determine API URL and key based on engine type
            if self.config.RAG_EMBEDDING_ENGINE in ["openai", "portkey"]:
                base_url_config = self.config.RAG_OPENAI_API_BASE_URL
                api_url = (
                    base_url_config.value
                    if hasattr(base_url_config, 'value')
                    else str(base_url_config)
                )
                
                # Fallback to default if empty (from config.py default)
                if not api_url or api_url.strip() == "" or api_url == "None":
                    api_url = "https://ai-gateway.apps.cloud.rt.nyu.edu/v1"
                    log.warning(f"Base URL was empty/None, using default: {api_url}")
                
                # CRITICAL: Use per-user/per-admin API key from job (RBAC-protected)
                # Do NOT fall back to env var - that would break RBAC
                if not api_key or not api_key.strip():
                    error_msg = (
                        "No embedding API key provided in job! "
                        "Embedding will fail. This key should come from admin config (RBAC-protected). "
                        "Please ensure the admin has configured an API key in Settings > Documents > Embedding."
                    )
                    log.error(error_msg)
                    raise ValueError(error_msg)
            else:
                base_url_config = self.config.RAG_OLLAMA_BASE_URL
                api_url = (
                    base_url_config.value
                    if hasattr(base_url_config, 'value')
                    else str(base_url_config)
                )
                api_key = self.config.RAG_OLLAMA_API_KEY
                
                # For local engines (sentence-transformers), ef must not be None
                if self.ef is None:
                    error_msg = "Cannot initialize EMBEDDING_FUNCTION: ef (embedding function model) is None for local engine"
                    log.error(error_msg)
                    raise ValueError(error_msg)
            
            # CRITICAL RBAC: Use embedding_model from job parameter, not config
            # Config may have fallback/env var values that break RBAC
            model_to_use = embedding_model if embedding_model else self.config.RAG_EMBEDDING_MODEL
            if not model_to_use or not model_to_use.strip():
                error_msg = (
                    "No embedding model provided! "
                    "Embedding will fail. This model should come from admin config (RBAC-protected). "
                    "Please ensure the admin has configured a model in Settings > Documents > Embedding."
                )
                log.error(error_msg)
                raise ValueError(error_msg)
            
            log.info(f"[RBAC] Using embedding model from job: {model_to_use} (RBAC-protected)")
            
            self.EMBEDDING_FUNCTION = get_embedding_function(
                self.config.RAG_EMBEDDING_ENGINE,
                model_to_use,  # Use job parameter, not config (RBAC-protected)
                self.ef,  # Can be None for API-based engines
                api_url,
                api_key,
                self.config.RAG_EMBEDDING_BATCH_SIZE,
            )
            
            if self.EMBEDDING_FUNCTION is None:
                error_msg = "Failed to create embedding function - get_embedding_function returned None"
                log.error(error_msg)
                raise ValueError(error_msg)
            
        except Exception as embedding_error:
            error_msg = f"Failed to initialize EMBEDDING_FUNCTION per-job: {embedding_error}"
            log.error(error_msg, exc_info=True)
            self.EMBEDDING_FUNCTION = None
            raise  # Re-raise to fail fast


# Mock UserScopedConfig class for fallback config compatibility
# Must be defined before _FallbackConfig uses it
class MockUserScopedConfig:
    """
    Mock UserScopedConfig for compatibility when AppConfig fails.
    Provides .get() and .set() methods that return/accept values but don't persist them.
    """
    def __init__(self, default_value):
        self.default = default_value
    
    def get(self, email: str = None):
        """
        Mock get() method for compatibility with UserScopedConfig.get().
        In workers, we don't have user-specific configs, so always return the default value.
        """
        return self.default
    
    def set(self, email: str, value):
        """
        Mock set() method for compatibility with UserScopedConfig.set().
        In workers, we don't persist user-specific configs, so this is a no-op.
        """
        # No-op: workers don't persist configs, they use job parameters
        pass


class _FallbackConfig:
    """
    Fallback configuration object used when AppConfig initialization fails.
    Provides minimal required attributes with safe defaults.
    
    NOTE: This should rarely be used. If AppConfig fails, it's usually a critical error.
    Model names and API keys come from job parameters (RBAC-protected), not from env vars.
    """
    def __init__(self):
        # Set minimal required attributes with safe defaults from environment
        # NOTE: RAG_EMBEDDING_MODEL should NOT be used - jobs pass embedding_model parameter (RBAC-protected)
        self.RAG_EMBEDDING_ENGINE = os.environ.get("RAG_EMBEDDING_ENGINE", "portkey")
        # WARNING: This is a fallback only - actual model comes from job parameter (embedding_model)
        # Do NOT use this for embeddings - it breaks RBAC!
        self.RAG_EMBEDDING_MODEL = os.environ.get("RAG_EMBEDDING_MODEL", "@openai-embedding/text-embedding-3-small")
        # RAG_EMBEDDING_MODEL_USER is a UserScopedConfig - create mock for compatibility
        # NOTE: This should NOT be used - jobs pass embedding_model parameter (RBAC-protected)
        self.RAG_EMBEDDING_MODEL_USER = MockUserScopedConfig(os.environ.get("RAG_EMBEDDING_MODEL", "@openai-embedding/text-embedding-3-small"))
        self.RAG_EMBEDDING_BATCH_SIZE = int(os.environ.get("RAG_EMBEDDING_BATCH_SIZE", "1"))
        self.RAG_RERANKING_MODEL = os.environ.get("RAG_RERANKING_MODEL", "")
        self.RAG_OPENAI_API_BASE_URL = os.environ.get("RAG_OPENAI_API_BASE_URL", "")
        # UserScopedConfig objects - use MockUserScopedConfig for compatibility
        self.RAG_OPENAI_API_KEY = MockUserScopedConfig(os.environ.get("RAG_OPENAI_API_KEY", ""))
        self.RAG_OLLAMA_BASE_URL = os.environ.get("RAG_OLLAMA_BASE_URL", "")
        self.RAG_OLLAMA_API_KEY = os.environ.get("RAG_OLLAMA_API_KEY", "")
        self.CONTENT_EXTRACTION_ENGINE = os.environ.get("CONTENT_EXTRACTION_ENGINE", "auto")
        self.TIKA_SERVER_URL = os.environ.get("TIKA_SERVER_URL", "")
        # CRITICAL: Force extract_images=False to prevent hangs (image extraction causes 2+ minute slowdowns)
        self.PDF_EXTRACT_IMAGES = False
        self.TEXT_SPLITTER = os.environ.get("RAG_TEXT_SPLITTER", "recursive")
        # UserScopedConfig objects - use MockUserScopedConfig for compatibility
        # These are used in save_docs_to_vector_db and other worker code paths
        self.CHUNK_SIZE = MockUserScopedConfig(int(os.environ.get("CHUNK_SIZE", "1000")))
        self.CHUNK_OVERLAP = MockUserScopedConfig(int(os.environ.get("CHUNK_OVERLAP", "200")))
        # RAG_TEMPLATE is used in _get_user_chunk_settings (called from save_docs_to_vector_db)
        from open_webui.config import DEFAULT_RAG_TEMPLATE
        self.RAG_TEMPLATE = MockUserScopedConfig(os.environ.get("RAG_TEMPLATE", DEFAULT_RAG_TEMPLATE))
        # TOP_K is used in retrieval queries (aliased as RAG_TOP_K in config.py)
        self.TOP_K = MockUserScopedConfig(int(os.environ.get("RAG_TOP_K", "10")))
        self.RAG_TOP_K = self.TOP_K  # Alias for compatibility
        # ENABLE_RAG_HYBRID_SEARCH is used in retrieval queries
        self.ENABLE_RAG_HYBRID_SEARCH = MockUserScopedConfig(os.environ.get("ENABLE_RAG_HYBRID_SEARCH", "False").lower() == "true")
        # RAG_FULL_CONTEXT is used in config endpoints
        self.RAG_FULL_CONTEXT = MockUserScopedConfig(os.environ.get("RAG_FULL_CONTEXT", "False").lower() == "true")
        # RELEVANCE_THRESHOLD is a PersistentConfig, not UserScopedConfig
        self.RELEVANCE_THRESHOLD = float(os.environ.get("RAG_RELEVANCE_THRESHOLD", "1"))
        
        # Other non-UserScopedConfig attributes
        self.DOCUMENT_INTELLIGENCE_ENDPOINT = os.environ.get("DOCUMENT_INTELLIGENCE_ENDPOINT", "")
        self.DOCUMENT_INTELLIGENCE_KEY = os.environ.get("DOCUMENT_INTELLIGENCE_KEY", "")
        self.BYPASS_EMBEDDING_AND_RETRIEVAL = os.environ.get("BYPASS_EMBEDDING_AND_RETRIEVAL", "False").lower() == "true"
        # Add TIKA_SERVER_URL for fallback (even though we don't use it, it might be accessed)
        self.TIKA_SERVER_URL = os.environ.get("TIKA_SERVER_URL", "")
        # Add missing config attributes that might be accessed (duplicates removed)
        self.RAG_OLLAMA_BASE_URL = os.environ.get("RAG_OLLAMA_BASE_URL", "")
        self.RAG_OLLAMA_API_KEY = os.environ.get("RAG_OLLAMA_API_KEY", "")
    
    def __getattr__(self, name):
        # Return None for any other attributes to prevent AttributeError
        log.warning(f"FallbackConfig: Attribute '{name}' not available, returning None")
        return None


def _create_fallback_config():
    """Create a fallback configuration object."""
    return _FallbackConfig()


# Log when module is fully loaded (after all imports and class definitions)
log.debug("file_processor.py module loaded successfully")


def process_file_job(
    file_id: str,
    content: Optional[str] = None,
    collection_name: Optional[str] = None,
    knowledge_id: Optional[str] = None,
    user_id: Optional[str] = None,
    owner_email: Optional[str] = None,
    embedding_model: Optional[str] = None,
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
        owner_email: Email of the admin who owns the KB/file (for RBAC - per-admin model/key lookup)
        embedding_model: Per-admin embedding model name (resolved at enqueue time for RBAC)
        embedding_api_key: API key for embedding service (per-user, from admin config)
        _otel_trace_context: Optional trace context for distributed tracing (internal use)
        
    Returns:
        Dictionary with processing result
    """
    # Log at the very start of job processing
    log.debug("=" * 80)
    log.debug("process_file_job ENTERED")
    log.debug(f"  file_id: {file_id}")
    log.debug(f"  user_id: {user_id}")
    log.debug(f"  knowledge_id: {knowledge_id}")
    log.debug(f"  collection_name: {collection_name}")
    log.debug(f"  content provided: {bool(content)}")
    log.debug(f"  owner_email: {owner_email}")
    log.debug(f"  embedding_model: {embedding_model}")
    log.debug(f"  embedding_api_key provided: {bool(embedding_api_key)}")
    log.debug("=" * 80)
    
    start_time = time.time()
    log.info(f"[JOB] START | file_id={file_id} | user_id={user_id} | knowledge_id={knowledge_id} | timestamp={start_time:.3f}")
    
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
        # CRITICAL: Use safe_trace_span to ensure OTEL failures never prevent task completion
        with safe_trace_span(
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
                safe_add_span_event("job.started", {"file_id": file_id})
                
                # Initialize request to None so it's accessible in finally block for cleanup
                request = None
                
                # Create mock request object for compatibility with existing code
                # Pass the embedding_api_key so it can initialize the embedding function per-job
                try:
                    request = MockRequest(embedding_api_key=embedding_api_key)
                    
                    # RBAC: Validate owner_email, embedding_model, and API key BEFORE initialization
                    if not owner_email or not owner_email.strip():
                        error_msg = (
                            f"No owner_email provided in job for file_id={file_id}! "
                            f"This is required for RBAC (per-admin model/key lookup)."
                        )
                        log.error(error_msg)
                        raise ValueError(error_msg)
                    
                    if not embedding_model or not embedding_model.strip():
                        error_msg = (
                            f"No embedding_model provided in job for file_id={file_id}! "
                            f"This is required for RBAC (per-admin model). "
                            f"Owner: {owner_email}"
                        )
                        log.error(error_msg)
                        raise ValueError(error_msg)
                    
                    if not embedding_api_key or not embedding_api_key.strip():
                        error_msg = (
                            f"No embedding API key provided in job for file_id={file_id}! "
                            f"This will cause embedding generation to fail. "
                            f"The API key should have been retrieved from admin config and passed to the job. "
                            f"Owner: {owner_email}"
                        )
                        log.error(error_msg)
                        raise ValueError(error_msg)
                    
                    log.info(
                        f"[JOB] RBAC Config: owner_email={owner_email}, "
                        f"embedding_model={embedding_model}, "
                        f"api_key_length={len(embedding_api_key) if embedding_api_key else 0}"
                    )
                    
                    # CRITICAL: Initialize EMBEDDING_FUNCTION per-job with the correct per-user/per-admin API key and model
                    # This ensures RBAC-protected API keys and models are used (each admin has their own key/model)
                    try:
                        request.app.state.initialize_embedding_function(
                            embedding_api_key=embedding_api_key,
                            embedding_model=embedding_model  # Pass job parameter (RBAC-protected)
                        )
                        
                        if request.app.state.EMBEDDING_FUNCTION is None:
                            error_msg = (
                                f"EMBEDDING_FUNCTION is None after initialization for file_id={file_id}. "
                                f"This will cause embedding generation to fail. "
                                f"Check: 1) API key is valid, 2) Base URL is correct, 3) Embedding model is configured"
                            )
                            log.error(error_msg)
                            raise ValueError(error_msg)
                    except ValueError as ve:
                        # Re-raise validation errors
                        raise
                    except Exception as init_error:
                        error_msg = f"Failed to initialize EMBEDDING_FUNCTION: {init_error}"
                        log.error(error_msg, exc_info=True)
                        raise
                except Exception as init_error:
                    log.error(f"Failed to initialize MockRequest for file_id={file_id}: {init_error}", exc_info=True)
                    raise
                
                try:
                    # Get user object if user_id is provided
                    user = None
                    if user_id:
                        try:
                            user = Users.get_user_by_id(user_id)
                            if not user:
                                log.warning(
                                    f"User {user_id} not found for file processing (file_id={file_id}), "
                                    "processing without user context"
                                )
                            else:
                                # RBAC: Set the owner's model and API key in the config for save_docs_to_vector_db
                                # This ensures RBAC-protected model/key are used (each admin has their own)
                                # Users inherit from their group admin's model/key
                                if owner_email and embedding_model and embedding_api_key:
                                    try:
                                        # Update the config with the owner's model and key to ensure consistency
                                        # This is important because save_docs_to_vector_db retrieves from config
                                        if request.app.state.config.RAG_EMBEDDING_ENGINE in ["openai", "portkey"]:
                                            # Set the owner's model and API key in the config (RBAC-protected)
                                            request.app.state.config.RAG_EMBEDDING_MODEL_USER.set(owner_email, embedding_model)
                                            request.app.state.config.RAG_OPENAI_API_KEY.set(owner_email, embedding_api_key)
                                            log.info(
                                                f"***** BACKGROUND JOB SETTING API KEY ***** "
                                                f"The file processor background job is setting API key for owner '{owner_email}'. "
                                                f"Model = '{embedding_model}', API Key = '{embedding_api_key}'. "
                                                f"This happens during file embedding in the background queue."
                                            )
                                    except Exception as config_update_error:
                                        # Critical - model/key must be set for RBAC
                                        log.error(f"Could not update config with owner model/key: {config_update_error}")
                                        raise
                        except Exception as user_error:
                            log.warning(
                                f"Error retrieving user {user_id} for file processing (file_id={file_id}): {user_error}, "
                                "processing without user context", exc_info=True
                            )
                    
                    # Update status to processing
                    processing_start_time = int(time.time())
                    Files.update_file_metadata_by_id(
                        file_id,
                        {
                            "processing_status": "processing",
                            "processing_started_at": processing_start_time,
                        },
                    )
                    
                    file = Files.get_file_by_id(file_id)
                    if not file:
                        error_msg = "File not found"
                        log.error(f"File {file_id} not found for processing (user_id={user_id})")
                        safe_add_span_event("job.file.not_found", {"file_id": file_id})
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

                    # Determine the collection name for vector DB storage (always needed for saving)
                    # But don't use it to determine processing path - that depends on how file was uploaded
                    vector_collection_name = collection_name if collection_name else f"file-{file.id}"
                    
                    if content:
                        # Update the content in the file
                        try:
                            VECTOR_DB_CLIENT.delete_collection(collection_name=vector_collection_name)
                        except Exception:
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
                        log.info(f"[JOB] KNOWLEDGE_COLLECTION | file_id={file.id} | collection={collection_name} | checking if already processed")
                        result = VECTOR_DB_CLIENT.query(
                            collection_name=vector_collection_name, filter={"file_id": file.id}
                        )

                        if result is not None and result.ids and len(result.ids) > 0 and len(result.ids[0]) > 0:
                            log.info(f"[JOB] ALREADY_PROCESSED | file_id={file.id} | found {len(result.ids[0])} existing documents")
                            # File already processed - extract from vector DB
                            try:
                                # Safely access result structure
                                if (hasattr(result, 'documents') and result.documents and 
                                    hasattr(result, 'metadatas') and result.metadatas and
                                    len(result.documents) > 0 and len(result.metadatas) > 0 and
                                    len(result.documents[0]) == len(result.metadatas[0]) == len(result.ids[0])):
                                    docs = [
                                        Document(
                                            page_content=result.documents[0][idx],
                                            metadata=result.metadatas[0][idx],
                                        )
                                        for idx, id in enumerate(result.ids[0])
                                    ]
                                    # CRITICAL: Set text_content from extracted documents
                                    text_content = " ".join([doc.page_content for doc in docs])
                                else:
                                    # Result structure is invalid - fall through to extraction
                                    log.warning(f"Invalid result structure for file_id={file.id}, falling back to extraction")
                                    docs = None
                                    text_content = None
                            except (IndexError, AttributeError, TypeError) as result_error:
                                log.warning(f"Error accessing result structure for file_id={file.id}: {result_error}, falling back to extraction", exc_info=True)
                                docs = None
                                text_content = None
                            
                            # If extraction from vector DB failed, fall through to file extraction
                            if docs is None:
                                file_content = file.data.get("content", "") if file.data else ""
                                
                                # If file.data has no content, extract from file system
                                if not file_content or len(file_content.strip()) == 0:
                                    # Extract content from file system (same logic as the else branch)
                                    file_path = file.path
                                    if file_path:
                                        try:
                                            file_path = Storage.get_file(file_path)
                                            if file_path and os.path.exists(file_path):
                                                file_size = os.path.getsize(file_path)
                                                log.info(f"[FILE] id={file.id} | name={file.filename} | size={file_size}B | path={file_path}")
                                                extraction_engine_val = ""  # Force PyPDF for PDFs (OpenShift requirement)
                                                # CRITICAL: Force extract_images=False to prevent hangs (image extraction causes 2+ minute slowdowns)
                                                pdf_extract_images_val = False
                                                log.info(f"[EXTRACT] START | file_id={file.id} | engine=PyPDF (forced) | extract_images={pdf_extract_images_val} (FORCED TO FALSE)")
                                                loader = Loader(engine=extraction_engine_val, PDF_EXTRACT_IMAGES=pdf_extract_images_val)
                                                try:
                                                    print(f"[DEBUG] About to call loader.load() for file_id={file.id} | extract_images={pdf_extract_images_val}", flush=True)
                                                    log.info(f"[DEBUG] About to call loader.load() for file_id={file.id} | extract_images={pdf_extract_images_val}")
                                                    docs = loader.load(file.filename, file.meta.get("content_type"), file_path)
                                                    print(f"[DEBUG] loader.load() completed for file_id={file.id} | docs_count={len(docs) if docs else 0}", flush=True)
                                                    log.info(f"[DEBUG] loader.load() completed for file_id={file.id} | docs_count={len(docs) if docs else 0}")
                                                    total_chars = sum(len(doc.page_content) for doc in docs) if docs else 0
                                                    non_empty = sum(1 for doc in docs if doc.page_content and doc.page_content.strip()) if docs else 0
                                                    log.info(f"[EXTRACT] SUCCESS | file_id={file.id} | docs={len(docs) if docs else 0} | chars={total_chars} | non_empty={non_empty}")
                                                except Exception as load_error:
                                                    log.error(f"[EXTRACT] FAILED | file_id={file.id} | error={type(load_error).__name__}: {load_error}", exc_info=True)
                                                    docs = []
                                                
                                                # Log extraction results
                                                total_chars = sum(len(doc.page_content) for doc in docs) if docs else 0
                                                non_empty_docs = [doc for doc in docs if doc.page_content.strip()] if docs else []
                                                
                                                # Add event for file extraction
                                                safe_add_span_event("job.file.extracted", {
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
                                            else:
                                                log.warning(f"File path is None or does not exist, using empty content")
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
                                        log.error(f"[JOB] FILE_PATH_MISSING | file_id={file.id} | filename={file.filename} | file.path is None - cannot extract content")
                                        error_msg = "File path is missing. Cannot extract content from file system."
                                        Files.update_file_metadata_by_id(file.id, {"processing_status": "error", "processing_error": error_msg})
                                        raise ValueError(error_msg)
                                else:
                                    # Use content from file.data
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
                        else:
                            # File not found in vector DB - extract from file system
                            file_content = file.data.get("content", "") if file.data else ""
                            
                            # If file.data has no content, extract from file system
                            if not file_content or len(file_content.strip()) == 0:
                                # Extract content from file system
                                file_path = file.path
                                if file_path:
                                    try:
                                        file_path = Storage.get_file(file_path)
                                        if file_path and os.path.exists(file_path):
                                            file_size = os.path.getsize(file_path)
                                            log.info(f"[FILE] id={file.id} | name={file.filename} | size={file_size}B | path={file_path}")
                                            extraction_engine_val = ""  # Force PyPDF for PDFs (OpenShift requirement)
                                            # CRITICAL: Force extract_images=False to prevent hangs (image extraction causes 2+ minute slowdowns)
                                            pdf_extract_images_val = False
                                            log.info(f"[EXTRACT] START | file_id={file.id} | engine=PyPDF (forced) | extract_images={pdf_extract_images_val} (FORCED TO FALSE)")
                                            loader = Loader(engine=extraction_engine_val, PDF_EXTRACT_IMAGES=pdf_extract_images_val)
                                            try:
                                                print(f"[DEBUG] About to call loader.load() for file_id={file.id} | extract_images={pdf_extract_images_val}", flush=True)
                                                log.info(f"[DEBUG] About to call loader.load() for file_id={file.id} | extract_images={pdf_extract_images_val}")
                                                docs = loader.load(file.filename, file.meta.get("content_type"), file_path)
                                                print(f"[DEBUG] loader.load() completed for file_id={file.id} | docs_count={len(docs) if docs else 0}", flush=True)
                                                log.info(f"[DEBUG] loader.load() completed for file_id={file.id} | docs_count={len(docs) if docs else 0}")
                                                total_chars = sum(len(doc.page_content) for doc in docs) if docs else 0
                                                non_empty = sum(1 for doc in docs if doc.page_content and doc.page_content.strip()) if docs else 0
                                                log.info(f"[EXTRACT] SUCCESS | file_id={file.id} | docs={len(docs) if docs else 0} | chars={total_chars} | non_empty={non_empty}")
                                                safe_add_span_event("job.file.extracted", {"content_length": total_chars, "document.count": len(docs)})
                                                docs = [Document(page_content=doc.page_content, metadata={**doc.metadata, "name": file.filename, "created_by": file.user_id, "file_id": file.id, "source": file.filename}) for doc in docs]
                                                text_content = " ".join([doc.page_content for doc in docs])
                                            except Exception as load_error:
                                                log.error(f"[EXTRACT] FAILED | file_id={file.id} | error={type(load_error).__name__}: {load_error}", exc_info=True)
                                                docs = []
                                        else:
                                            log.warning(f"File path is None or does not exist, using empty content")
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
                                    log.error(f"[JOB] FILE_PATH_MISSING | file_id={file.id} | filename={file.filename} | file.path is None - cannot extract content")
                                    error_msg = "File path is missing. Cannot extract content from file system."
                                    Files.update_file_metadata_by_id(file.id, {"processing_status": "error", "processing_error": error_msg})
                                    raise ValueError(error_msg)
                            else:
                                # Use content from file.data
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
                        sys.stdout.flush()
                    else:
                        # Regular file upload (not from knowledge collection) - extract from file system
                        log.info(f"[JOB] REGULAR_UPLOAD | file_id={file.id} | filename={file.filename} | file.path={file.path}")
                        file_content = file.data.get("content", "") if file.data else ""
                        
                        # If file.data has no content, extract from file system
                        if not file_content or len(file_content.strip()) == 0:
                            file_path = file.path
                            if file_path:
                                log.info(f"[JOB] FILE_PATH_EXISTS | file_id={file.id} | path={file_path}")
                                try:
                                    file_path = Storage.get_file(file_path)
                                    if file_path and os.path.exists(file_path):
                                        file_size = os.path.getsize(file_path)
                                        log.info(f"[FILE] id={file.id} | name={file.filename} | size={file_size}B | path={file_path}")
                                        extraction_engine_val = ""  # Force PyPDF for PDFs (OpenShift requirement)
                                        # CRITICAL: Force extract_images=False to prevent hangs (image extraction causes 2+ minute slowdowns)
                                        pdf_extract_images_val = False
                                        extract_start = time.time()
                                        log.info(f"[EXTRACT] START | file_id={file.id} | engine=PyPDF (forced) | extract_images={pdf_extract_images_val} (FORCED TO FALSE) | timestamp={extract_start:.3f}")
                                        loader = Loader(engine=extraction_engine_val, PDF_EXTRACT_IMAGES=pdf_extract_images_val)
                                        try:
                                            print(f"[DEBUG] About to call loader.load() for file_id={file.id} | extract_images={pdf_extract_images_val} | timestamp={extract_start:.3f}", flush=True)
                                            log.info(f"[DEBUG] About to call loader.load() for file_id={file.id} | extract_images={pdf_extract_images_val}")
                                            docs = loader.load(file.filename, file.meta.get("content_type"), file_path)
                                            extract_end = time.time()
                                            extract_duration = extract_end - extract_start
                                            print(f"[DEBUG] loader.load() completed for file_id={file.id} | docs_count={len(docs) if docs else 0} | duration={extract_duration:.2f}s", flush=True)
                                            log.info(f"[DEBUG] loader.load() completed for file_id={file.id} | docs_count={len(docs) if docs else 0} | duration={extract_duration:.2f}s")
                                            total_chars = sum(len(doc.page_content) for doc in docs) if docs else 0
                                            non_empty = sum(1 for doc in docs if doc.page_content and doc.page_content.strip()) if docs else 0
                                            log.info(f"[EXTRACT] SUCCESS | file_id={file.id} | docs={len(docs) if docs else 0} | chars={total_chars} | non_empty={non_empty} | duration={extract_duration:.2f}s | timestamp={extract_end:.3f}")
                                            log.debug(f"EXTRACT SUCCESS | docs={len(docs) if docs else 0} | chars={total_chars}")
                                            safe_add_span_event("job.file.extracted", {"content_length": total_chars, "document.count": len(docs)})
                                            docs = [Document(page_content=doc.page_content, metadata={**doc.metadata, "name": file.filename, "created_by": file.user_id, "file_id": file.id, "source": file.filename}) for doc in docs]
                                            text_content = " ".join([doc.page_content for doc in docs])
                                            log.debug(f"After metadata addition | docs={len(docs)} | text_content_len={len(text_content)}")
                                        except Exception as load_error:
                                            log.error(f"[EXTRACT] FAILED | file_id={file.id} | error={type(load_error).__name__}: {load_error}", exc_info=True)
                                            log.debug(f"EXTRACT FAILED | error={load_error}")
                                            docs = []
                                    else:
                                        log.error(f"[JOB] FILE_NOT_FOUND | file_id={file.id} | resolved_path={file_path} | file does not exist")
                                        error_msg = f"File not found at path: {file_path}"
                                        Files.update_file_metadata_by_id(file.id, {"processing_status": "error", "processing_error": error_msg})
                                        raise ValueError(error_msg)
                                except Exception as storage_error:
                                    log.error(f"[JOB] STORAGE_ERROR | file_id={file.id} | error={type(storage_error).__name__}: {storage_error}", exc_info=True)
                                    error_msg = f"Failed to retrieve file from storage: {storage_error}"
                                    Files.update_file_metadata_by_id(file.id, {"processing_status": "error", "processing_error": error_msg})
                                    raise ValueError(error_msg)
                            else:
                                log.error(f"[JOB] FILE_PATH_MISSING | file_id={file.id} | filename={file.filename} | file.path is None - cannot extract content")
                                error_msg = "File path is missing. Cannot extract content from file system."
                                Files.update_file_metadata_by_id(file.id, {"processing_status": "error", "processing_error": error_msg})
                                raise ValueError(error_msg)
                        else:
                            # Use content from file.data
                            log.info(f"[JOB] USING_FILE_DATA | file_id={file.id} | content_length={len(file_content)}")
                            log.debug(f"USING_FILE_DATA branch | file_content_len={len(file_content)}")
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
                            log.debug(f"After USING_FILE_DATA | docs={len(docs)} | text_content_len={len(text_content)}")

                    # Log state after if/else block with timestamp
                    current_time = time.time()
                    log.debug(f"After REGULAR_UPLOAD if/else block | timestamp={current_time:.3f} | elapsed={current_time - start_time:.2f}s")
                    log.debug(f"  'docs' in locals: {'docs' in locals()}")
                    log.debug(f"  docs count: {len(docs) if 'docs' in locals() and docs else 'UNDEFINED or None'}")
                    log.debug(f"  'text_content' in locals: {'text_content' in locals()}")
                    
                    # Ensure text_content is defined (defensive check)
                    if 'text_content' not in locals() or text_content is None:
                        text_content = file.data.get("content", "") if file.data else ""
                    
                    # Set collection_name for vector DB storage (ensure it's always set)
                    if not collection_name:
                        collection_name = vector_collection_name
                except Exception as e:
                    # Consolidated error handling - log and update status
                    error_time = time.time()
                    elapsed_time = error_time - start_time
                    error_msg = str(e)
                    log.error(f"[JOB] FAILED | file_id={file_id} | user_id={user_id} | elapsed={elapsed_time:.2f}s | timestamp={error_time:.3f} | error={type(e).__name__}: {error_msg}", exc_info=True)
                    
                    safe_add_span_event("job.failed", {
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
                
                # Validate that we have content to process
                from open_webui.constants import ERROR_MESSAGES
                
                # Log docs state before validation
                log.debug(f"PRE-VALIDATION | file_id={file.id}")
                log.debug(f"  'docs' defined: {'docs' in dir()}")
                try:
                    log.debug(f"  docs type: {type(docs)}")
                    log.debug(f"  docs length: {len(docs) if docs else 'None/empty'}")
                    if docs and len(docs) > 0:
                        log.debug(f"  first doc page_content length: {len(docs[0].page_content) if docs[0].page_content else 0}")
                except Exception as debug_error:
                    log.debug(f"  ERROR accessing docs: {debug_error}")
                
                validate_start = time.time()
                total_chars = sum(len(doc.page_content) for doc in docs) if docs else 0
                non_empty = sum(1 for doc in docs if doc.page_content and doc.page_content.strip()) if docs else 0
                log.info(f"[VALIDATE] START | file_id={file.id} | docs={len(docs) if docs else 0} | chars={total_chars} | non_empty={non_empty} | timestamp={validate_start:.3f} | elapsed={validate_start - start_time:.2f}s")
                log.debug(f"VALIDATION | docs={len(docs) if docs else 0} | chars={total_chars} | non_empty={non_empty}")
                
                if not docs or len(docs) == 0:
                    error_msg = ERROR_MESSAGES.EMPTY_CONTENT
                    log.error(f"[VALIDATE] FAILED | file_id={file.id} | reason=NO_DOCS | loader returned empty list")
                    Files.update_file_metadata_by_id(file.id, {"processing_status": "error", "processing_error": error_msg})
                    raise ValueError(error_msg)
                
                if total_chars == 0:
                    error_msg = ERROR_MESSAGES.EMPTY_CONTENT
                    log.error(f"[VALIDATE] FAILED | file_id={file.id} | reason=EMPTY_CONTENT | docs={len(docs)} but all page_content empty")
                    log.error(f"[VALIDATE] DIAGNOSIS | Possible: image-only PDF, corrupted file, extraction failed silently")
                    Files.update_file_metadata_by_id(file.id, {"processing_status": "error", "processing_error": error_msg})
                    raise ValueError(error_msg)
                
                validate_end = time.time()
                validate_duration = validate_end - validate_start
                log.info(f"[VALIDATE] PASSED | file_id={file.id} | docs={len(docs)} | chars={total_chars} | non_empty={non_empty} | duration={validate_duration:.2f}s | timestamp={validate_end:.3f} | elapsed={validate_end - start_time:.2f}s")

                Files.update_file_data_by_id(
                    file.id,
                    {"content": text_content},
                )

                hash = calculate_sha256_string(text_content)
                Files.update_file_hash_by_id(file.id, hash)

                # Safely access BYPASS_EMBEDDING_AND_RETRIEVAL - use hasattr() first because AppConfig.__getattr__ raises KeyError for missing keys
                bypass_embedding = getattr(request.app.state.config, 'BYPASS_EMBEDDING_AND_RETRIEVAL', False) if hasattr(request.app.state.config, 'BYPASS_EMBEDDING_AND_RETRIEVAL') else False
                
                if not bypass_embedding:
                    embed_start = time.time()
                    filename = getattr(file, "filename", "") or ""
                    log.info(f"[RAG File] file_id={file.id} | filename={filename} | docs_pre_split={len(docs)} (chunking and embedding next)")
                    log.info(f"[EMBED] START | file_id={file.id} | filename={filename} | docs_pre_split={len(docs)} | timestamp={embed_start:.3f}")
                    try:
                        # If knowledge_id is provided, we're adding to both collections at once
                        if knowledge_id:
                            file_collection = f"file-{file.id}"
                            collections = [file_collection, knowledge_id]

                            # RBAC: Pass owner_email so save_docs_to_multiple_collections uses per-admin model/key
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
                                owner_email=owner_email,  # RBAC: Per-admin model/key lookup
                            )

                            # Use file collection name for file metadata
                            if result:
                                embed_end = time.time()
                                embed_duration = embed_end - embed_start
                                log.info(f"[EMBED] SUCCESS | file_id={file.id} | filename={filename} | collections={collections} | docs_pre_split={len(docs)} | duration={embed_duration:.2f}s | timestamp={embed_end:.3f}")
                                safe_add_span_event("job.embedding.completed", {"status": "success", "collection_name": file_collection})
                                Files.update_file_metadata_by_id(
                                    file.id,
                                    {
                                        "collection_name": file_collection,
                                        "processing_status": "completed",
                                        "processing_completed_at": int(time.time()),
                                    },
                                )
                            else:
                                log.error(f"[EMBED] FAILED | file_id={file.id} | filename={filename} | reason=SAVE_TO_VDB_FAILED")
                                Files.update_file_metadata_by_id(
                                    file.id,
                                    {
                                        "processing_status": "error",
                                        "processing_error": "Failed to save to vector DB",
                                    },
                                )
                        else:
                            file_collection = f"file-{file.id}"
                            log.info(f"[EMBED] SINGLE_COLLECTION | file_id={file.id} | filename={filename} | collection={file_collection} | docs_pre_split={len(docs)} | timestamp={time.time():.3f}")
                            # RBAC: Pass owner_email so save_docs_to_vector_db uses per-admin model/key
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
                                owner_email=owner_email,  # RBAC: Per-admin model/key lookup
                            )

                            if result:
                                embed_end = time.time()
                                embed_duration = embed_end - embed_start
                                log.info(f"[EMBED] SUCCESS | file_id={file.id} | filename={filename} | collection={collection_name} | docs_pre_split={len(docs)} | duration={embed_duration:.2f}s | timestamp={embed_end:.3f}")
                                Files.update_file_metadata_by_id(
                                    file.id,
                                    {
                                        "collection_name": collection_name,
                                        "processing_status": "completed",
                                        "processing_completed_at": int(time.time()),
                                    },
                                )
                            else:
                                log.error(f"[EMBED] FAILED | file_id={file.id} | filename={filename} | reason=SAVE_TO_VDB_FAILED")
                                Files.update_file_metadata_by_id(
                                    file.id,
                                    {
                                        "processing_status": "error",
                                        "processing_error": "Failed to save to vector DB",
                                    },
                                )
                    except Exception as e:
                        error_msg = str(e)
                        log.error(f"[EMBED] FAILED | file_id={file.id} | filename={filename} | error={type(e).__name__}: {error_msg}", exc_info=True)
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
                    Files.update_file_metadata_by_id(
                        file.id,
                        {
                            "processing_status": "completed",
                            "processing_completed_at": int(time.time()),
                        },
                    )

                elapsed_time = time.time() - start_time
                safe_add_span_event("job.completed", {
                    "duration_ms": int(elapsed_time * 1000),
                    "file_id": file_id,
                })
                safe_set_span_attribute(span, "job.duration_ms", int(elapsed_time * 1000))

                return {
                    "status": "success",
                    "file_id": file_id,
                    "collection_name": collection_name,
                    "elapsed_time": elapsed_time,
                }
            except Exception as e:
                # Re-raise to outer try block for consolidated error handling
                raise

    except Exception as e:
        # Consolidated error handling - log and update status
        elapsed_time = time.time() - start_time
        error_msg = str(e)
        log.error(f"[JOB] FAILED | file_id={file_id} | user_id={user_id} | elapsed={elapsed_time:.2f}s | error={type(e).__name__}: {error_msg}", exc_info=True)
        
        safe_add_span_event("job.failed", {
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

