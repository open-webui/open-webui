"""
RQ Worker Module

This module can be run as a script to start an RQ worker for file processing.

Usage:
    python -m open_webui.workers.start_worker
"""

import os
import sys
import socket

# Add backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Set timezone to NYC before any logging
os.environ["TZ"] = "America/New_York"

# Initialize proper logger (uses NYC timezone and proper formatting)
from open_webui.utils import logger
logger.start_logger()

import logging
log = logging.getLogger(__name__)

from rq import Worker, Queue, Connection
from redis import Redis
from redis.connection import ConnectionPool
from redis.sentinel import Sentinel
from open_webui.env import (
    REDIS_URL, 
    SRC_LOG_LEVELS, 
    ENABLE_JOB_QUEUE,
    REDIS_USE_SENTINEL,
    REDIS_SENTINEL_HOSTS,
    REDIS_SENTINEL_SERVICE_NAME,
)
from open_webui.utils.job_queue import FILE_PROCESSING_QUEUE_NAME

# Set log level from environment
log.setLevel(SRC_LOG_LEVELS.get("WORKER", SRC_LOG_LEVELS.get("MODELS", logging.INFO)))


def initialize_database():
    """
    Initialize database connections for worker process.
    
    This ensures that database connections are available when workers
    process jobs that require database access.
    """
    try:
        # Import database initialization code
        # This will create database engine and connection pools
        from open_webui.internal.db import engine, get_db
        from sqlalchemy import text
        
        # Test database connection
        with get_db() as db:
            db.execute(text("SELECT 1"))
            db.commit()
        
        log.info("Database connection initialized successfully")
        return True
    except Exception as e:
        log.error(
            f"Failed to initialize database connection: {e}. "
            "Worker may not be able to process jobs that require database access.",
            exc_info=True
        )
        # Don't fail startup - some jobs might not need database
        # But log as error so it's visible
        return False


def start_worker():
    """Start RQ worker for file processing queue"""
    try:
        log.info("=" * 80)
        log.info("RQ Worker Startup - Initializing file processing worker")
        log.info("=" * 80)
        
        # Check if job queue is enabled
        if not ENABLE_JOB_QUEUE:
            log.error(
                "ENABLE_JOB_QUEUE is False. Worker requires job queue to be enabled. "
                "Set ENABLE_JOB_QUEUE=True to start worker."
            )
            sys.exit(1)
        log.info("Job queue is enabled (ENABLE_JOB_QUEUE=True)")
        
        # Initialize database connections early
        # This ensures database is available when jobs are processed
        log.info("Initializing database connection...")
        db_initialized = initialize_database()
        
        if not db_initialized:
            log.warning(
                "Database initialization failed. Worker will continue but "
                "file processing jobs may fail if they require database access."
            )
        else:
            log.info("Database connection initialized successfully")
        
        # Validate Redis URL
        if not REDIS_URL:
            log.error("REDIS_URL not configured, cannot start worker")
            log.error("Please set REDIS_URL environment variable to start the worker")
            sys.exit(1)
        
        log.info(f"REDIS_URL configured: {REDIS_URL.split('@')[0]}@...")  # Hide password in logs
        
        # Get Redis connection
        import time
        redis_connect_start = time.time()
        log.info(f"Connecting to Redis... | timestamp={redis_connect_start:.3f}")
        try:
            # Check if Sentinel is configured
            if REDIS_USE_SENTINEL and REDIS_SENTINEL_HOSTS:
                sentinel_start = time.time()
                log.info(f"Using Redis Sentinel for high availability | timestamp={sentinel_start:.3f}")
                log.info(f"Sentinel hosts: {REDIS_SENTINEL_HOSTS}")
                log.info(f"Sentinel service name: {REDIS_SENTINEL_SERVICE_NAME}")
                
                # Parse Sentinel hosts (comma-separated list)
                sentinel_parse_start = time.time()
                sentinel_hosts = []
                for host_port in REDIS_SENTINEL_HOSTS.split(','):
                    host_port = host_port.strip()
                    if ':' in host_port:
                        host, port = host_port.rsplit(':', 1)
                        sentinel_hosts.append((host.strip(), int(port.strip())))
                    else:
                        # Default port 26379
                        sentinel_hosts.append((host_port.strip(), 26379))
                sentinel_parse_end = time.time()
                log.info(f"[REDIS] Sentinel hosts parsed | duration={sentinel_parse_end - sentinel_parse_start:.3f}s | timestamp={sentinel_parse_end:.3f}")
                
                # Extract password from REDIS_URL if present
                redis_password = None
                if REDIS_URL and '@' in REDIS_URL:
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(REDIS_URL)
                        if parsed.password:
                            redis_password = parsed.password
                    except Exception:
                        pass
                
                # Create Sentinel connection
                sentinel_create_start = time.time()
                sentinel = Sentinel(
                    sentinel_hosts,
                    socket_timeout=5,
                    socket_connect_timeout=10,
                )
                sentinel_create_end = time.time()
                log.info(f"[REDIS] Sentinel object created | duration={sentinel_create_end - sentinel_create_start:.3f}s | timestamp={sentinel_create_end:.3f}")
                
                # Get master connection from Sentinel
                master_lookup_start = time.time()
                # CRITICAL: decode_responses=False because RQ stores binary job data (pickled)
                # CRITICAL: socket_timeout=None for blocking operations (BRPOP)
                master_kwargs = {
                    'socket_timeout': None,  # CRITICAL: No timeout for blocking operations (BRPOP)
                    'socket_connect_timeout': 10,
                    'decode_responses': False,  # CRITICAL: RQ stores binary pickled job data
                }
                if redis_password:
                    master_kwargs['password'] = redis_password
                
                redis_conn = sentinel.master_for(
                    REDIS_SENTINEL_SERVICE_NAME,
                    **master_kwargs
                )
                master_lookup_end = time.time()
                log.info(f"[REDIS] Master lookup from Sentinel | duration={master_lookup_end - master_lookup_start:.3f}s | timestamp={master_lookup_end:.3f}")
                
                # Test connection
                ping_start = time.time()
                redis_conn.ping()
                ping_end = time.time()
                redis_connect_end = time.time()
                log.info(f"[REDIS] Ping test | duration={ping_end - ping_start:.3f}s | timestamp={ping_end:.3f}")
                log.info(f"[REDIS] Sentinel connection established | total_duration={redis_connect_end - redis_connect_start:.3f}s | master={REDIS_SENTINEL_SERVICE_NAME} | timestamp={redis_connect_end:.3f}")
            else:
                # Fallback to direct connection (for local development or non-Sentinel setups)
                direct_conn_start = time.time()
                log.info(f"Using direct Redis connection (Sentinel not configured) | timestamp={direct_conn_start:.3f}")
                
                # For RQ workers, we need a connection with NO timeout for blocking operations
                # RQ uses BRPOP which blocks indefinitely waiting for jobs
                # CRITICAL: decode_responses=False because RQ stores binary job data (pickled)
                # Using socket_timeout=None allows blocking operations to work properly
                pool_create_start = time.time()
                worker_pool = ConnectionPool.from_url(
                    REDIS_URL,
                    decode_responses=False,  # CRITICAL: RQ stores binary pickled job data
                    max_connections=10,  # Workers need fewer connections
                    retry_on_timeout=True,
                    socket_connect_timeout=10,  # Longer connect timeout
                    socket_timeout=None,  # CRITICAL: No timeout for blocking operations (BRPOP)
                    health_check_interval=30,
                )
                pool_create_end = time.time()
                log.info(f"[REDIS] Connection pool created | duration={pool_create_end - pool_create_start:.3f}s | timestamp={pool_create_end:.3f}")
                
                redis_conn = Redis(connection_pool=worker_pool)
                
                # Test Redis connection (ping works with decode_responses=False)
                ping_start = time.time()
                redis_conn.ping()
                ping_end = time.time()
                direct_conn_end = time.time()
                log.info(f"[REDIS] Ping test | duration={ping_end - ping_start:.3f}s | timestamp={ping_end:.3f}")
                log.info(f"[REDIS] Direct connection established | total_duration={direct_conn_end - direct_conn_start:.3f}s | timestamp={direct_conn_end:.3f}")
            
            # Test queue access (RQ handles binary data correctly)
            queue_test_start = time.time()
            test_queue = Queue(FILE_PROCESSING_QUEUE_NAME, connection=redis_conn)
            queue_length = len(test_queue)
            queue_test_end = time.time()
            log.info(f"[REDIS] Queue access test | queue='{FILE_PROCESSING_QUEUE_NAME}' | length={queue_length} | duration={queue_test_end - queue_test_start:.3f}s | timestamp={queue_test_end:.3f}")
        except Exception as redis_error:
            log.error(f"Failed to connect to Redis: {redis_error}", exc_info=True)
            log.error("Worker cannot start without Redis connection. Please check:")
            log.error("  1. REDIS_URL is correct")
            log.error("  2. Redis server is running and accessible")
            log.error("  3. Network connectivity to Redis")
            sys.exit(1)
        
        # Generate worker name with hostname and PID for better identification
        hostname = socket.gethostname()
        worker_name = f"file_processor_{hostname}_{os.getpid()}"
        
        log.info(f"Worker name: {worker_name}")
        log.info(f"Queue name: {FILE_PROCESSING_QUEUE_NAME}")
        
        # Clean up stale worker registrations before starting
        # This prevents "There exists an active worker named '...' already" errors
        # when pods restart (old worker registration still exists in Redis)
        cleanup_start = time.time()
        log.info(f"[REDIS] Starting worker cleanup check | timestamp={cleanup_start:.3f}")
        try:
            from rq.worker import Worker
            
            # Check if a worker with this name already exists (stale registration)
            # This can happen when a pod restarts - the old worker registration may still be in Redis
            try:
                worker_list_start = time.time()
                existing_workers = Worker.all(connection=redis_conn)
                worker_list_end = time.time()
                log.info(f"[REDIS] Worker list retrieved | count={len(existing_workers)} | duration={worker_list_end - worker_list_start:.3f}s | timestamp={worker_list_end:.3f}")
                
                for existing_worker in existing_workers:
                    if existing_worker.name == worker_name:
                        unregister_start = time.time()
                        log.warning(f"[REDIS] Found stale worker registration: {existing_worker.name}. Cleaning up... | timestamp={unregister_start:.3f}")
                        try:
                            # Unregister the stale worker to free up the name
                            existing_worker.unregister(death_penalty_class=None)
                            unregister_end = time.time()
                            log.info(f"[REDIS] Successfully cleaned up stale worker: {existing_worker.name} | duration={unregister_end - unregister_start:.3f}s | timestamp={unregister_end:.3f}")
                        except Exception as cleanup_error:
                            unregister_end = time.time()
                            log.warning(f"[REDIS] Could not clean up stale worker {existing_worker.name}: {cleanup_error} | duration={unregister_end - unregister_start:.3f}s. Will try to continue anyway.")
            except Exception as worker_list_error:
                worker_list_end = time.time()
                log.debug(f"[REDIS] Could not list existing workers (non-fatal): {worker_list_error} | duration={worker_list_end - cleanup_start:.3f}s")
        except Exception as cleanup_error:
            cleanup_end = time.time()
            log.warning(f"[REDIS] Error during worker cleanup (non-fatal): {cleanup_error} | duration={cleanup_end - cleanup_start:.3f}s")
            # Continue - cleanup failure shouldn't prevent worker from starting
        else:
            cleanup_end = time.time()
            log.info(f"[REDIS] Worker cleanup completed | total_duration={cleanup_end - cleanup_start:.3f}s | timestamp={cleanup_end:.3f}")
        
        # Create queue connection
        worker_init_start = time.time()
        log.info(f"[WORKER] Initializing worker | timestamp={worker_init_start:.3f}")
        with Connection(redis_conn):
            # Create queue
            queue_create_start = time.time()
            queue = Queue(FILE_PROCESSING_QUEUE_NAME)
            queue_create_end = time.time()
            log.info(f"[WORKER] Queue object created | duration={queue_create_end - queue_create_start:.3f}s | timestamp={queue_create_end:.3f}")
            
            # Create and start worker
            worker_create_start = time.time()
            worker = Worker([queue], name=worker_name)
            worker_create_end = time.time()
            log.info(f"[WORKER] Worker object created | duration={worker_create_end - worker_create_start:.3f}s | timestamp={worker_create_end:.3f}")
            
            worker_init_end = time.time()
            log.info("=" * 80)
            log.info(
                f"✅ RQ Worker '{worker_name}' starting for queue '{FILE_PROCESSING_QUEUE_NAME}' | init_duration={worker_init_end - worker_init_start:.3f}s"
            )
            log.info(f"   Redis: {REDIS_URL.split('@')[0]}@...")
            log.info(f"   Hostname: {hostname}")
            log.info(f"   PID: {os.getpid()}")
            log.info("=" * 80)
            log.info(f"Worker is ready to process jobs. Waiting for jobs... | timestamp={worker_init_end:.3f}")
            
            # Start worker (this blocks)
            worker_work_start = time.time()
            log.info(f"[WORKER] Starting worker.work() - will block waiting for jobs | timestamp={worker_work_start:.3f}")
            worker.work()
    except KeyboardInterrupt:
        log.info("Worker stopped by user (KeyboardInterrupt)")
        sys.exit(0)
    except Exception as e:
        log.error(f"Fatal worker error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    start_worker()

