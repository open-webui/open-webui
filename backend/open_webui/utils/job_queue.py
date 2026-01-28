"""
Distributed Job Queue for File Processing

This module provides a distributed job queue using RQ (Redis Queue) for processing files
in a multi-replica Kubernetes environment. It replaces FastAPI BackgroundTasks which
only work in-memory on a single pod.

Jobs are stored in Redis and can be processed by any worker pod, enabling:
- Distributed processing across replicas
- Job retry on failure
- Job status tracking
- Load balancing across pods
"""

import json
import logging
import threading
from typing import Optional, Dict, Any

from rq import Queue, Retry
from rq.job import Job, JobStatus
from redis import Redis
from redis.exceptions import ConnectionError, TimeoutError

from open_webui.env import (
    REDIS_URL,
    ENABLE_JOB_QUEUE,
    JOB_TIMEOUT,
    JOB_MAX_RETRIES,
    JOB_RETRY_DELAY,
    JOB_RESULT_TTL,
    JOB_FAILURE_TTL,
)
from open_webui.socket.utils import get_redis_pool

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

# Safe wrapper functions that NEVER fail - OTEL is monitoring only, must not affect task execution
def safe_add_span_event(event_name, attributes=None):
    """Safely add span event - never fails, even if OTEL is broken"""
    try:
        add_span_event(event_name, attributes)
    except Exception as e:
        log.debug(f"OTEL add_span_event failed (non-critical): {e}")

def safe_trace_span(*args, **kwargs):
    """Safely create trace span - never fails, even if OTEL is broken"""
    try:
        return trace_span(*args, **kwargs)
    except Exception as e:
        log.debug(f"OTEL trace_span failed (non-critical), using nullcontext: {e}")
        from contextlib import nullcontext
        return nullcontext(enter_result=None)

log = logging.getLogger(__name__)

# Queue name for file processing jobs
FILE_PROCESSING_QUEUE_NAME = "file_processing"

# Default job timeout (1 hour for large files)
DEFAULT_JOB_TIMEOUT = JOB_TIMEOUT

# Maximum number of retries for failed jobs
MAX_RETRIES = JOB_MAX_RETRIES

# Retry delay in seconds
RETRY_DELAY = JOB_RETRY_DELAY

# Cache for Queue instances (one per queue name, shared across application)
_queue_cache: Dict[str, Queue] = {}
_queue_cache_lock = threading.Lock()


class JobQueueError(Exception):
    """Exception raised for job queue errors"""
    pass


def get_job_queue(queue_name: str = FILE_PROCESSING_QUEUE_NAME) -> Optional[Queue]:
    """
    Get or create an RQ queue for job processing.
    
    Queue instances are cached per queue name to avoid recreating them.
    This improves efficiency by reusing Redis connections from the pool.
    
    Args:
        queue_name: Name of the queue (default: "file_processing")
        
    Returns:
        Queue instance or None if Redis is not available or job queue is disabled
    """
    try:
        # Check if job queue is enabled
        if not ENABLE_JOB_QUEUE:
            log.debug("Job queue is disabled via ENABLE_JOB_QUEUE environment variable")
            return None
        
        if not REDIS_URL:
            log.warning("REDIS_URL not configured, job queue unavailable")
            return None
        
        import time
        # Check cache first (thread-safe)
        cache_check_start = time.time()
        with _queue_cache_lock:
            if queue_name in _queue_cache:
                cached_queue = _queue_cache[queue_name]
                # Verify connection still works
                ping_start = time.time()
                try:
                    cached_queue.connection.ping()
                    ping_end = time.time()
                    cache_check_end = time.time()
                    log.debug(f"[JOB_QUEUE] Using cached queue | queue={queue_name} | ping_duration={ping_end - ping_start:.3f}s | total_duration={cache_check_end - cache_check_start:.3f}s | timestamp={cache_check_end:.3f}")
                    return cached_queue
                except Exception:
                    ping_end = time.time()
                    # Connection dead, remove from cache and create new one
                    log.warning(f"[JOB_QUEUE] Cached queue {queue_name} has dead connection, recreating | ping_duration={ping_end - ping_start:.3f}s")
                    del _queue_cache[queue_name]
        
        # Get Redis connection pool (shared across application)
        # Always use master for job queue (requires writes)
        pool_get_start = time.time()
        pool = get_redis_pool(REDIS_URL, use_master=True)
        pool_get_end = time.time()
        log.debug(f"[JOB_QUEUE] Redis pool retrieved | duration={pool_get_end - pool_get_start:.3f}s | timestamp={pool_get_end:.3f}")
        
        # Handle Sentinel connection wrapper
        conn_get_start = time.time()
        if hasattr(pool, '_conn'):
            redis_conn = pool._conn
        elif hasattr(pool, 'get_connection'):
            # For Sentinel connections, get master connection
            from open_webui.socket.utils import get_redis_master_connection
            redis_conn = get_redis_master_connection()
            if redis_conn is None:
                # Fallback to direct connection
                redis_conn = Redis(connection_pool=pool)
        else:
            # Standard connection pool
            redis_conn = Redis(connection_pool=pool)
        conn_get_end = time.time()
        log.debug(f"[JOB_QUEUE] Redis connection obtained | duration={conn_get_end - conn_get_start:.3f}s | timestamp={conn_get_end:.3f}")
        
        # Test connection
        ping_start = time.time()
        redis_conn.ping()
        ping_end = time.time()
        log.debug(f"[JOB_QUEUE] Connection ping test | duration={ping_end - ping_start:.3f}s | timestamp={ping_end:.3f}")
        
        # Create queue with the connection
        queue_create_start = time.time()
        queue = Queue(queue_name, connection=redis_conn)
        queue_create_end = time.time()
        log.debug(f"[JOB_QUEUE] Queue object created | queue={queue_name} | duration={queue_create_end - queue_create_start:.3f}s | timestamp={queue_create_end:.3f}")
        
        # Cache the queue instance for reuse
        cache_store_start = time.time()
        with _queue_cache_lock:
            _queue_cache[queue_name] = queue
        cache_store_end = time.time()
        log.debug(f"[JOB_QUEUE] Queue cached | queue={queue_name} | duration={cache_store_end - cache_store_start:.3f}s | timestamp={cache_store_end:.3f}")
        
        log.debug(f"Created and cached job queue: {queue_name}")
        return queue
    except (ConnectionError, TimeoutError, ValueError) as e:
        log.warning(f"Failed to connect to Redis for job queue: {e}")
        return None
    except Exception as e:
        log.error(f"Unexpected error creating job queue: {e}", exc_info=True)
        return None


def enqueue_file_processing_job(
    file_id: str,
    content: Optional[str] = None,
    collection_name: Optional[str] = None,
    knowledge_id: Optional[str] = None,
    user_id: Optional[str] = None,
    owner_email: Optional[str] = None,
    embedding_model: Optional[str] = None,
    embedding_api_key: Optional[str] = None,
    job_timeout: int = DEFAULT_JOB_TIMEOUT,
) -> Optional[str]:
    """
    Enqueue a file processing job to the distributed job queue.
    
    Args:
        file_id: ID of the file to process (must be non-empty string, typically UUID)
        content: Optional pre-extracted content (for text files, must be JSON-serializable)
        collection_name: Optional collection name for embeddings (must be JSON-serializable)
        knowledge_id: Optional knowledge base ID (must be JSON-serializable)
        user_id: User ID who initiated the processing (must be JSON-serializable)
        owner_email: Email of the admin who owns the KB/file (for RBAC - per-admin model/key lookup)
        embedding_model: Per-admin embedding model name (resolved at enqueue time for RBAC)
        embedding_api_key: API key for embedding service (per-user, from admin config)
        job_timeout: Job timeout in seconds (default: 1 hour)
        
    Returns:
        Job ID if successfully enqueued, None if queue unavailable or validation fails
        
    Raises:
        ValueError: If input validation fails
    """
    # Input validation
    if not file_id or not isinstance(file_id, str) or not file_id.strip():
        log.error(f"Invalid file_id: must be non-empty string, got {type(file_id).__name__}")
        return None
    
    # Validate that all arguments are JSON-serializable (basic check)
    try:
        json.dumps({
            "file_id": file_id,
            "content": content,
            "collection_name": collection_name,
            "knowledge_id": knowledge_id,
            "user_id": user_id,
            "owner_email": owner_email,
            "embedding_model": embedding_model,
            "embedding_api_key": embedding_api_key,
        })
    except (TypeError, ValueError) as e:
        log.error(f"Job arguments are not JSON-serializable for file_id={file_id}: {e}")
        return None
    
    import time
    enqueue_start = time.time()
    log.info(f"[JOB_QUEUE] Starting enqueue operation | file_id={file_id} | timestamp={enqueue_start:.3f}")
    try:
        queue_get_start = time.time()
        queue = get_job_queue()
        queue_get_end = time.time()
        log.info(f"[JOB_QUEUE] Queue retrieved | duration={queue_get_end - queue_get_start:.3f}s | timestamp={queue_get_end:.3f}")
        if queue is None:
            log.warning(f"[JOB_QUEUE] Job queue unavailable, cannot enqueue file processing for file_id={file_id}")
            return None
        
        # Generate unique job ID per file
        job_id_str = f"file_processing_{file_id}"
        
        # Check if a job with this ID already exists
        job_fetch_start = time.time()
        try:
            existing_job = Job.fetch(job_id_str, connection=queue.connection)
            job_fetch_end = time.time()
            log.info(f"[JOB_QUEUE] Job fetch check | duration={job_fetch_end - job_fetch_start:.3f}s | timestamp={job_fetch_end:.3f}")
            if existing_job:
                existing_status = existing_job.get_status()
                
                # If job is queued or started, file is already being processed
                if existing_status in [JobStatus.QUEUED, JobStatus.STARTED]:
                    enqueue_end = time.time()
                    log.info(
                        f"[JOB_QUEUE] Job {job_id_str} already exists with status {existing_status} "
                        f"for file_id={file_id}, returning existing job ID | total_duration={enqueue_end - enqueue_start:.3f}s | timestamp={enqueue_end:.3f}"
                    )
                    return existing_job.id
                
                # If job is finished or failed, we can create a new one
                # But log it for monitoring
                log.debug(
                    f"Job {job_id_str} exists but status is {existing_status} "
                    f"for file_id={file_id}, will create new job"
                )
        except Exception as fetch_error:
            # Job doesn't exist or fetch failed - this is fine, we'll create a new one
            log.debug(f"Job {job_id_str} does not exist or could not be fetched: {fetch_error}")
        
        # Extract trace context from current span for propagation to worker process
        trace_context = {}
        if OTEL_AVAILABLE and is_otel_enabled():
            try:
                from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
                from opentelemetry import trace
                
                # Get current span context
                current_span = trace.get_current_span()
                if current_span and current_span.get_span_context().is_valid:
                    # Extract trace context into a dictionary
                    propagator = TraceContextTextMapPropagator()
                    propagator.inject(trace_context)
                    log.debug(f"Extracted trace context for job enqueueing: {trace_context}")
            except Exception as trace_error:
                log.debug(f"Failed to extract trace context: {trace_error}")
                trace_context = {}
        
        # Prepare job arguments (serializable data only)
        # RBAC: Include owner_email and embedding_model for per-admin model/key resolution in worker
        job_kwargs = {
            "file_id": file_id,
            "content": content,
            "collection_name": collection_name,
            "knowledge_id": knowledge_id,
            "user_id": user_id,
            "owner_email": owner_email,  # KB owner or uploader (for RBAC)
            "embedding_model": embedding_model,  # Per-admin model name (resolved at enqueue time)
            "embedding_api_key": embedding_api_key,
        }
        
        # Add trace context to job metadata if available
        if trace_context:
            job_kwargs["_otel_trace_context"] = trace_context
        
        # Create OTEL span for job enqueueing
        # CRITICAL: Use safe_trace_span to ensure OTEL failures never prevent job enqueueing
        with safe_trace_span(
            name="job.enqueue",
            attributes={
                "job.id": job_id_str,
                "job.file_id": file_id,
                "job.queue_name": FILE_PROCESSING_QUEUE_NAME,
                "job.timeout": job_timeout,
                "job.has_trace_context": bool(trace_context),
            },
        ) as span:
            # Enqueue job with retry logic
            # Import here to avoid circular imports
            from open_webui.workers.file_processor import process_file_job
        
            # Try to enqueue the job
            # RQ may raise an exception if job_id already exists (race condition)
            enqueue_redis_start = time.time()
            try:
                job = queue.enqueue(
                    process_file_job,
                    **job_kwargs,
                    job_timeout=job_timeout,
                    retry=Retry(max=MAX_RETRIES, interval=RETRY_DELAY),
                    job_id=job_id_str,
                    result_ttl=JOB_RESULT_TTL,  # Configurable TTL for job results
                    failure_ttl=JOB_FAILURE_TTL,  # Configurable TTL for failed job info
                )
                enqueue_redis_end = time.time()
                enqueue_end = time.time()
                safe_add_span_event("job.enqueued", {"job_id": job.id, "file_id": file_id})
                log.info(
                    f"[JOB_QUEUE] Enqueued file processing job | job_id={job.id} | file_id={file_id} | "
                    f"queue={FILE_PROCESSING_QUEUE_NAME} | redis_duration={enqueue_redis_end - enqueue_redis_start:.3f}s | "
                    f"total_duration={enqueue_end - enqueue_start:.3f}s | timestamp={enqueue_end:.3f}"
                )
                return job.id
            except Exception as enqueue_error:
                # Handle case where job was created between our check and enqueue (race condition)
                error_str = str(enqueue_error).lower()
                if "already exists" in error_str or "duplicate" in error_str:
                    log.info(
                        f"Job {job_id_str} was created by another process (race condition) "
                        f"for file_id={file_id}, fetching existing job"
                    )
                    try:
                        existing_job = Job.fetch(job_id_str, connection=queue.connection)
                        if existing_job:
                            safe_add_span_event("job.enqueued", {"job_id": existing_job.id, "file_id": file_id, "note": "existing_job"})
                            return existing_job.id
                    except Exception as fetch_error:
                        log.warning(f"Failed to fetch existing job {job_id_str}: {fetch_error}")
                
                # Log error event
                safe_add_span_event("job.enqueue.failed", {
                    "error.type": type(enqueue_error).__name__,
                    "error.message": str(enqueue_error)[:200],
                })
                # Re-raise if it's not a duplicate job error
                raise
    except Exception as e:
        log.error(f"Failed to enqueue file processing job for file_id={file_id}: {e}", exc_info=True)
        return None


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the status of a job by ID.
    
    Args:
        job_id: Job ID to check
        
    Returns:
        Dictionary with job status information, or None if:
        - Job queue is unavailable
        - Job not found (NoSuchJobError)
        - Other errors occurred
    """
    try:
        queue = get_job_queue()
        if queue is None:
            log.debug(f"Job queue unavailable, cannot get status for job_id={job_id}")
            return None
        
        # Fetch job - this will raise NoSuchJobError if job doesn't exist
        try:
            job = Job.fetch(job_id, connection=queue.connection)
        except Exception as fetch_error:
            # Handle NoSuchJobError specifically (job doesn't exist)
            error_str = str(fetch_error).lower()
            if "no such job" in error_str or "not found" in error_str:
                log.debug(f"Job {job_id} not found in queue")
                return None
            # Re-raise other errors
            raise
        
        # Map RQ job status to our status format
        status_map = {
            JobStatus.QUEUED: "pending",
            JobStatus.STARTED: "processing",
            JobStatus.FINISHED: "completed",
            JobStatus.FAILED: "error",
            JobStatus.DEFERRED: "pending",
            JobStatus.SCHEDULED: "pending",
            JobStatus.CANCELED: "error",
        }
        
        job_status = job.get_status()
        status = status_map.get(job_status, "unknown")
        
        result = {
            "job_id": job_id,
            "status": status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        }
        
        # Add error information if job failed
        if status == "error" and job.exc_info:
            # Extract meaningful error message from exc_info if possible
            try:
                # exc_info might be a string or tuple, try to extract message
                if isinstance(job.exc_info, str):
                    result["error"] = job.exc_info
                elif isinstance(job.exc_info, (list, tuple)) and len(job.exc_info) > 1:
                    result["error"] = str(job.exc_info[1])
                else:
                    result["error"] = str(job.exc_info)
            except Exception:
                result["error"] = str(job.exc_info)
        
        # Add result if job completed successfully
        if status == "completed" and job.result:
            result["result"] = job.result
        
        return result
    except Exception as e:
        log.warning(f"Failed to get job status for job_id={job_id}: {e}", exc_info=True)
        return None


def cancel_job(job_id: str) -> bool:
    """
    Cancel a queued or running job.
    
    Args:
        job_id: Job ID to cancel
        
    Returns:
        True if job was cancelled, False otherwise
    """
    try:
        queue = get_job_queue()
        if queue is None:
            log.debug(f"Job queue unavailable, cannot cancel job_id={job_id}")
            return False
        
        try:
            job = Job.fetch(job_id, connection=queue.connection)
        except Exception as fetch_error:
            # Handle NoSuchJobError specifically
            error_str = str(fetch_error).lower()
            if "no such job" in error_str or "not found" in error_str:
                log.debug(f"Job {job_id} not found, cannot cancel")
                return False
            # Re-raise other errors
            raise
        
        job_status = job.get_status()
        
        # Only cancel if job is queued or started
        if job_status in [JobStatus.QUEUED, JobStatus.STARTED]:
            job.cancel()
            log.info(f"Cancelled job: job_id={job_id}")
            return True
        else:
            log.debug(f"Job {job_id} cannot be cancelled (status: {job_status})")
            return False
    except Exception as e:
        log.error(f"Failed to cancel job {job_id}: {e}", exc_info=True)
        return False


def is_job_queue_available() -> bool:
    """
    Check if the job queue is available (enabled and Redis connection works).
    
    Returns:
        True if job queue is enabled and available, False otherwise
    """
    if not ENABLE_JOB_QUEUE:
        return False
    return get_job_queue() is not None

