#!/usr/bin/env python3
"""
Kubernetes Vector Database Cleanup Script for CANChat
Runs comprehensive cleanup of orphaned vectors while preserving knowledge bases.
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# Add the current directory to Python path (we're in /app/scripts, backend is at /app)
sys.path.insert(0, "/app")


def setup_logging(verbose=False):
    """Configure logging for K8s environment."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="CANChat Vector DB Cleanup for Kubernetes"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned without making changes",
    )
    args = parser.parse_args()

    logger = setup_logging(args.verbose)

    logger.info("🧹 Starting CANChat Vector Database Cleanup")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info(f"Dry run mode: {args.dry_run}")

    # Detect database configuration
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgresql://") or database_url.startswith(
            "postgres://"
        ):
            db_type = "PostgreSQL"
            logger.info(
                f"🗄️  Database: {db_type} - {database_url.split('@')[1] if '@' in database_url else 'configured'}"
            )
        elif database_url.startswith("sqlite:///"):
            db_type = "SQLite"
            logger.info(f"🗄️  Database: {db_type} - {database_url}")
        else:
            db_type = "Unknown"
            logger.warning(f"⚠️  Unknown database type: {database_url}")
    else:
        db_type = "SQLite (default)"
        logger.info(f"🗄️  Database: {db_type} - Using default SQLite")

    try:
        # Validate environment configuration
        logger.info("🔧 Validating environment configuration...")

        # Check critical environment variables
        required_vars = ["QDRANT_URI"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {missing_vars}")
            return 1

        # Log vector database configuration
        qdrant_uri = os.getenv("QDRANT_URI")
        logger.info(f"🔍 Qdrant URI: {qdrant_uri}")

        # Log other relevant settings
        if os.getenv("QDRANT_API_KEY"):
            logger.info("🔐 Qdrant API key: Configured")

        data_dir = os.getenv("DATA_DIR", "/app/backend/data")
        upload_dir = os.getenv("UPLOAD_DIR", "/app/backend/data/uploads")
        logger.info(f"📁 Data directory: {data_dir}")
        logger.info(f"📁 Upload directory: {upload_dir}")

        # Log cleanup configuration
        web_search_expiry_days = int(os.getenv("VECTOR_DB_WEB_SEARCH_EXPIRY_DAYS", "7"))
        logger.info(f"⏰ Web search cleanup: {web_search_expiry_days} days retention")

        logger.info("✓ Environment validation completed")

        # Import cleanup functions
        from open_webui.routers.retrieval import (
            cleanup_orphaned_vectors,
            cleanup_expired_web_searches,
            cleanup_orphaned_chat_files,
            cleanup_orphaned_files_by_reference,
        )
        from open_webui.models.knowledge import Knowledges

        logger.info("✓ Successfully imported cleanup modules")

        # Test database connectivity
        logger.info("🔌 Testing database connectivity...")
        try:
            # Try to get knowledge bases as a connectivity test
            knowledge_bases = Knowledges.get_knowledge_bases()
            logger.info(f"✓ Database connection successful")
            logger.info(f"📊 Found {len(knowledge_bases)} knowledge bases to preserve")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            logger.error(
                "This could indicate database connectivity issues or missing credentials"
            )
            return 1

        # Run cleanup operations
        cleanup_results = {}

        # 1. Clean up orphaned standalone files
        logger.info("🔍 Cleaning orphaned standalone files...")
        if not args.dry_run:
            result = cleanup_orphaned_vectors()
            cleanup_results["orphaned_files"] = result
            logger.info(f"✓ Orphaned files cleanup: {result}")
        else:
            logger.info("✓ [DRY RUN] Would clean orphaned standalone files")

        # 2. Clean up files not referenced by any chats (safe for cloned chats)
        logger.info("🔍 Cleaning files not referenced by any chats...")
        if not args.dry_run:
            result = cleanup_orphaned_files_by_reference()
            cleanup_results["orphaned_files_by_reference"] = result
            logger.info(f"✓ Reference-based file cleanup: {result}")
        else:
            logger.info("✓ [DRY RUN] Would clean files not referenced by any chats")

        # 2b. Aggressive chat file cleanup (optional - only if explicitly enabled)
        # This is disabled by default to prevent issues with cloned chats
        # if getattr(args, 'aggressive_cleanup', False):
        #     logger.info("🔍 Aggressive chat files cleanup...")
        #     if not args.dry_run:
        #         result = cleanup_orphaned_chat_files()
        #         cleanup_results["chat_files"] = result
        #         logger.info(f"✓ Chat files cleanup: {result}")
        #     else:
        #         logger.info("✓ [DRY RUN] Would clean orphaned chat files")

        # 3. Clean up expired web search results
        logger.info(
            f"🔍 Cleaning web search results older than {web_search_expiry_days} days..."
        )
        if not args.dry_run:
            result = cleanup_expired_web_searches(max_age_days=web_search_expiry_days)
            cleanup_results["web_searches"] = result
            logger.info(f"✓ Web search cleanup: {result}")
        else:
            logger.info(
                f"✓ [DRY RUN] Would clean web searches older than {web_search_expiry_days} days"
            )

        # Summary
        if not args.dry_run:
            total_cleaned = sum(
                result.get("collections_cleaned", 0) + result.get("files_deleted", 0)
                for result in cleanup_results.values()
                if isinstance(result, dict)
            )
            logger.info(
                f"🎉 Cleanup completed successfully! Total items cleaned: {total_cleaned}"
            )

            # Log detailed results
            for operation, result in cleanup_results.items():
                if isinstance(result, dict) and result.get("status") != "error":
                    logger.info(f"   {operation}: {result}")
        else:
            logger.info("🎉 Dry run completed successfully!")

        return 0

    except ImportError as e:
        logger.error(f"❌ Failed to import required modules: {e}")
        logger.error(
            "Make sure the app is properly deployed and dependencies are available"
        )
        return 1

    except Exception as e:
        logger.error(f"❌ Cleanup failed with error: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
