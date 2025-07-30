"""
Utilities for handling re-indexing operations in query contexts.
Separated to reduce cyclomatic complexity and provide cleaner interfaces.
"""

import logging
from typing import Optional, Dict, Any
from open_webui.models.files import Files
from open_webui.models.users import Users
from open_webui.constants import VECTOR_COLLECTION_PREFIXES

log = logging.getLogger(__name__)


def get_file_and_user_for_reindex(file_id: str):
    """Get file and user objects needed for re-indexing."""
    file = Files.get_file_by_id(file_id)
    if not file:
        return None, None

    user = Users.get_user_by_id(file.user_id) if file.user_id else None
    return file, user


def collection_not_found_error(error_str: str) -> bool:
    """Check if the error indicates a missing collection."""
    return "doesn't exist" in error_str or "not found" in error_str.lower()


def extract_file_id_from_collection(collection_name: str) -> Optional[str]:
    """Extract file ID from collection name if it's a file collection."""
    if collection_name.startswith(VECTOR_COLLECTION_PREFIXES.FILE):
        return collection_name.replace(VECTOR_COLLECTION_PREFIXES.FILE, "")
    return None


def attempt_reindex_and_retry(
    collection_name: str, k: int, query_embedding, file_id: str
) -> Optional[Dict[str, Any]]:
    """
    Attempt to re-index a file and retry the query.
    Returns the query result if successful, None otherwise.
    """
    try:
        from open_webui.routers.retrieval import reindex_file_on_demand
        from open_webui.retrieval.utils import query_doc

        # Get file and user
        file, user = get_file_and_user_for_reindex(file_id)
        if not file:
            log.error(f"File {file_id} not found in database for re-indexing")
            return None

        # Try to get the main app's configuration directly
        try:
            from open_webui.main import app as main_app

            # Create a mock request object that has the app structure expected by reindex_file_on_demand
            class MockRequest:
                def __init__(self, app):
                    self.app = app

            mock_request = MockRequest(main_app)

            # Use the mock request for reindexing
            if reindex_file_on_demand(file_id, mock_request, user):
                log.info(f"Re-indexing successful for {file_id}, retrying query...")

                # Retry the query after successful re-indexing
                try:
                    result = query_doc(
                        collection_name=collection_name,
                        query_embedding=query_embedding,
                        k=k,
                    )
                    return result.model_dump() if result else None
                except Exception as retry_e:
                    log.error(f"Query failed even after re-indexing: {retry_e}")
                    return None
            else:
                log.error(f"Re-indexing failed for {file_id}")
                return None
        except ImportError:
            # If we can't import the main app, skip re-indexing
            log.error(
                "Cannot import main app for re-indexing, skipping reindex attempt"
            )
            return None

    except Exception as e:
        log.error(f"Re-indexing failed for {file_id}: {e}")
        return None


def handle_collection_query_with_reindex(
    collection_name: str, k: int, query_embedding
) -> Optional[Dict[str, Any]]:
    """
    Handle querying a collection with automatic re-indexing on collection not found errors.
    This is the main interface that replaces the complex inline logic.
    """
    try:
        from open_webui.retrieval.utils import query_doc

        # First, try the normal query
        result = query_doc(
            collection_name=collection_name,
            query_embedding=query_embedding,
            k=k,
        )

        if result is not None:
            return result.model_dump()

    except Exception as e:
        error_str = str(e)

        # Check if this is a "collection not found" error
        if collection_not_found_error(error_str):
            log.info(
                f"Collection {collection_name} not found, attempting re-indexing..."
            )

            # Extract file ID from collection name
            file_id = extract_file_id_from_collection(collection_name)
            if file_id:
                # Attempt re-indexing and retry
                result = attempt_reindex_and_retry(
                    collection_name, k, query_embedding, file_id
                )
                if result:
                    return result

        # Log the original error if re-indexing wasn't attempted or failed
        log.exception(f"Error when querying the collection: {e}")

    return None
