#!/usr/bin/env python3
"""
Vector Database Cleanup Service for Kubernetes

This script is designed to work both locally and in Kubernetes environments.
It handles PostgreSQL and SQLite databases and respects Helm-driven environment variables.

Environment Variables (Helm/K8s):
- VECTOR_DB: Database type (qdrant, chroma, etc.)
- QDRANT_URL: Qdrant connection URL
- DATABASE_URL: PostgreSQL connection string (K8s) or SQLite path (local)
- VECTOR_DB_CLEANUP_INTERVAL_HOURS: Cleanup interval (default: 24)
- WEB_SEARCH_CACHE_MAX_AGE_DAYS: Web search cache retention (default: 7)
- WEB_SEARCH_CLEANUP_MAX_AGE_DAYS: Web search cleanup threshold (default: 30)

Usage:
    # Local development
    python scripts/k8s_vector_cleanup.py --config .env

    # Kubernetes CronJob
    python scripts/k8s_vector_cleanup.py --k8s-mode

Example Kubernetes CronJob manifest:
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: vector-cleanup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: vector-cleanup
            image: your-registry/open-webui:latest
            command: ["python", "scripts/k8s_vector_cleanup.py", "--k8s-mode"]
            env:
            - name: VECTOR_DB
              value: "qdrant"
            - name: QDRANT_URL
              value: "http://qdrant-service:6333"
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: connection-string
          restartPolicy: OnFailure
```
"""

import os
import sys
import logging
import argparse
import traceback
from pathlib import Path
from datetime import datetime, timedelta

# Add the backend path to sys.path
script_dir = Path(__file__).parent
backend_path = script_dir.parent / "backend"
sys.path.insert(0, str(backend_path))

def setup_logging(verbose=False, k8s_mode=False):
    """Setup logging configuration for both local and K8s environments"""
    level = logging.DEBUG if verbose else logging.INFO
    
    # In K8s, logs go to stdout/stderr for container log collection
    handlers = [logging.StreamHandler()]
    
    # Only add file handler in local mode
    if not k8s_mode:
        try:
            handlers.append(logging.FileHandler('vector_cleanup.log'))
        except Exception:
            pass  # Ignore if we can't write to file (e.g., in K8s)
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def load_env_file(env_file_path):
    """Load environment variables from .env file (local development only)"""
    if os.path.exists(env_file_path):
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove quotes if present
                    value = value.strip('\'"')
                    os.environ[key] = value

def get_database_type():
    """Determine if we're using PostgreSQL or SQLite"""
    database_url = os.environ.get('DATABASE_URL', '')
    if database_url.startswith('postgresql://') or database_url.startswith('postgres://'):
        return 'postgresql'
    else:
        return 'sqlite'

def wait_for_dependencies(max_wait_seconds=60):
    """Wait for dependencies (Qdrant, Database) to be available"""
    logger = logging.getLogger(__name__)
    
    # Test Qdrant connection
    qdrant_url = os.environ.get('QDRANT_URL', 'http://localhost:6333')
    logger.info(f"Waiting for Qdrant at {qdrant_url}")
    
    start_time = datetime.now()
    while (datetime.now() - start_time).seconds < max_wait_seconds:
        try:
            import requests
            response = requests.get(f"{qdrant_url}/collections", timeout=5)
            if response.status_code == 200:
                logger.info("Qdrant is available")
                break
        except Exception as e:
            logger.debug(f"Qdrant not ready: {e}")
            import time
            time.sleep(5)
    else:
        raise Exception(f"Qdrant not available after {max_wait_seconds} seconds")

def cleanup_with_db_context():
    """Run cleanup operations with proper database context handling"""
    logger = logging.getLogger(__name__)
    
    try:
        # Import after environment is set up
        from open_webui.routers.retrieval import (
            cleanup_orphaned_vectors,
            cleanup_expired_web_searches,
        )
        from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT
        
        logger.info("Starting vector database cleanup")
        
        # Get initial statistics
        initial_stats = get_vector_stats(VECTOR_DB_CLIENT, logger)
        logger.info(f"Initial stats: {initial_stats}")
        
        # Clean up orphaned vectors
        logger.info("Cleaning up orphaned vectors...")
        try:
            orphaned_result = cleanup_orphaned_vectors()
            logger.info(f"Orphaned cleanup completed: {orphaned_result}")
        except Exception as e:
            logger.error(f"Error during orphaned cleanup: {e}")
            logger.debug(traceback.format_exc())
        
        # Clean up expired web searches
        max_age = int(os.environ.get('WEB_SEARCH_CLEANUP_MAX_AGE_DAYS', '30'))
        logger.info(f"Cleaning up web searches older than {max_age} days...")
        try:
            web_search_result = cleanup_expired_web_searches(max_age)
            logger.info(f"Web search cleanup completed: {web_search_result}")
        except Exception as e:
            logger.error(f"Error during web search cleanup: {e}")
            logger.debug(traceback.format_exc())
        
        # Get final statistics
        final_stats = get_vector_stats(VECTOR_DB_CLIENT, logger)
        logger.info(f"Final stats: {final_stats}")
        
        # Log the difference
        if initial_stats:
            diff = {k: final_stats.get(k, 0) - initial_stats.get(k, 0) for k in initial_stats.keys()}
            logger.info(f"Collections removed: {diff}")
        
        logger.info("Vector database cleanup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        logger.debug(traceback.format_exc())
        return False

def get_vector_stats(vector_client, logger):
    """Get vector database statistics safely"""
    try:
        collections_response = vector_client.client.get_collections()
        collections = [col.name for col in collections_response.collections]
        
        return {
            "total_collections": len(collections),
            "file_collections": len([c for c in collections if c.startswith("file-")]),
            "web_search_collections": len([c for c in collections if c.startswith("web-search-")]),
            "other_collections": len([c for c in collections if not c.startswith(("file-", "web-search-"))])
        }
    except Exception as e:
        logger.warning(f"Could not get vector stats: {e}")
        return {}

def main():
    parser = argparse.ArgumentParser(description='Vector Database Cleanup Service for Kubernetes')
    parser.add_argument('--config', default='.env', help='Path to .env configuration file (local only)')
    parser.add_argument('--k8s-mode', action='store_true', help='Run in Kubernetes mode (no .env file)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be cleaned without making changes')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--max-wait', type=int, default=60, help='Maximum wait time for dependencies (seconds)')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose, args.k8s_mode)
    logger = logging.getLogger(__name__)
    
    try:
        # Load environment configuration (only in local mode)
        if not args.k8s_mode:
            env_file = Path(args.config)
            if env_file.exists():
                load_env_file(str(env_file))
                logger.info(f"Loaded configuration from {env_file}")
            else:
                logger.warning(f"Configuration file not found: {env_file}")
        
        # Log environment info
        db_type = get_database_type()
        vector_db = os.environ.get('VECTOR_DB', 'chroma')
        qdrant_url = os.environ.get('QDRANT_URL', 'http://localhost:6333')
        
        logger.info(f"Environment: {'Kubernetes' if args.k8s_mode else 'Local'}")
        logger.info(f"Database type: {db_type}")
        logger.info(f"Vector DB: {vector_db}")
        logger.info(f"Qdrant URL: {qdrant_url}")
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
            return 0
        
        # Wait for dependencies to be ready (important in K8s)
        if args.k8s_mode:
            wait_for_dependencies(args.max_wait)
        
        # Run cleanup operations
        success = cleanup_with_db_context()
        
        if success:
            logger.info("Vector cleanup completed successfully")
            return 0
        else:
            logger.error("Vector cleanup failed")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Cleanup interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
