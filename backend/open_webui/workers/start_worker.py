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
from open_webui.env import REDIS_URL, SRC_LOG_LEVELS, ENABLE_JOB_QUEUE
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
        
        # Get Redis connection pool
        log.info("Connecting to Redis...")
        try:
            # For RQ workers, we need a connection with NO timeout for blocking operations
            # RQ uses BRPOP which blocks indefinitely waiting for jobs
            # CRITICAL: decode_responses=False because RQ stores binary job data (pickled)
            # Using socket_timeout=None allows blocking operations to work properly
            worker_pool = ConnectionPool.from_url(
                REDIS_URL,
                decode_responses=False,  # CRITICAL: RQ stores binary pickled job data
                max_connections=10,  # Workers need fewer connections
                retry_on_timeout=True,
                socket_connect_timeout=10,  # Longer connect timeout
                socket_timeout=None,  # CRITICAL: No timeout for blocking operations (BRPOP)
                health_check_interval=30,
            )
            redis_conn = Redis(connection_pool=worker_pool)
            
            # Test Redis connection (ping works with decode_responses=False)
            redis_conn.ping()
            log.info("Redis connection established successfully")
            
            # Test queue access (RQ handles binary data correctly)
            test_queue = Queue(FILE_PROCESSING_QUEUE_NAME, connection=redis_conn)
            queue_length = len(test_queue)
            log.info(f"Queue '{FILE_PROCESSING_QUEUE_NAME}' accessible (current length: {queue_length})")
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
        
        # Create queue connection
        with Connection(redis_conn):
            # Create queue
            queue = Queue(FILE_PROCESSING_QUEUE_NAME)
            
            # Create and start worker
            worker = Worker([queue], name=worker_name)
            
            log.info("=" * 80)
            log.info(
                f"✅ RQ Worker '{worker_name}' starting for queue '{FILE_PROCESSING_QUEUE_NAME}'"
            )
            log.info(f"   Redis: {REDIS_URL.split('@')[0]}@...")
            log.info(f"   Hostname: {hostname}")
            log.info(f"   PID: {os.getpid()}")
            log.info("=" * 80)
            log.info("Worker is ready to process jobs. Waiting for jobs...")
            
            # Start worker (this blocks)
            worker.work()
    except KeyboardInterrupt:
        log.info("Worker stopped by user (KeyboardInterrupt)")
        sys.exit(0)
    except Exception as e:
        log.error(f"Fatal worker error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    start_worker()

