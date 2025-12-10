"""
RQ Worker Module

This module can be run as a script to start an RQ worker for file processing.

Usage:
    python -m open_webui.workers.start_worker
"""

import os
import sys
import logging
import socket

# Add backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Configure logging before importing other modules
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

log = logging.getLogger(__name__)

from rq import Worker, Queue, Connection
from redis import Redis
from open_webui.env import REDIS_URL, SRC_LOG_LEVELS
from open_webui.socket.utils import get_redis_pool
from open_webui.utils.job_queue import FILE_PROCESSING_QUEUE_NAME

# Set log level from environment
log.setLevel(SRC_LOG_LEVELS.get("MODELS", logging.INFO))


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
        # Initialize database connections early
        # This ensures database is available when jobs are processed
        db_initialized = initialize_database()
        
        if not db_initialized:
            log.warning(
                "Database initialization failed. Worker will continue but "
                "file processing jobs may fail if they require database access."
            )
        
        if not REDIS_URL:
            log.error("REDIS_URL not configured, cannot start worker")
            sys.exit(1)
        
        # Get Redis connection pool
        try:
            pool = get_redis_pool(REDIS_URL)
            redis_conn = Redis(connection_pool=pool)
            
            # Test Redis connection
            redis_conn.ping()
            log.info(f"Redis connection established: {REDIS_URL}")
        except Exception as redis_error:
            log.error(f"Failed to connect to Redis: {redis_error}", exc_info=True)
            sys.exit(1)
        
        # Generate worker name with hostname and PID for better identification
        hostname = socket.gethostname()
        worker_name = f"file_processor_{hostname}_{os.getpid()}"
        
        # Create queue connection
        with Connection(redis_conn):
            # Create queue
            queue = Queue(FILE_PROCESSING_QUEUE_NAME)
            
            # Create and start worker
            worker = Worker([queue], name=worker_name)
            
            log.info(
                f"Starting RQ worker '{worker_name}' for queue '{FILE_PROCESSING_QUEUE_NAME}' "
                f"on Redis: {REDIS_URL}"
            )
            
            # Start worker (this blocks)
            worker.work()
    except KeyboardInterrupt:
        log.info("Worker stopped by user")
        sys.exit(0)
    except Exception as e:
        log.error(f"Worker error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    start_worker()

