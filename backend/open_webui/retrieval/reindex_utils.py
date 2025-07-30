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


def create_config_from_fallback() -> Dict[str, Any]:
    """
    Create configuration object from environment/database when main app config is unavailable.
    This handles the circular import issue cleanly.
    """
    try:
        from open_webui.config import (
            RAG_EMBEDDING_ENGINE,
            RAG_EMBEDDING_MODEL,
            RAG_TEXT_SPLITTER,
            CHUNK_SIZE,
            CHUNK_OVERLAP,
            RAG_RERANKING_MODEL,
            RAG_EMBEDDING_BATCH_SIZE,
            DEFAULT_RAG_TEMPLATE,
        )

        return {
            "RAG_EMBEDDING_ENGINE": RAG_EMBEDDING_ENGINE.value,
            "RAG_EMBEDDING_MODEL": RAG_EMBEDDING_MODEL.value,
            "TEXT_SPLITTER": RAG_TEXT_SPLITTER.value,
            "CHUNK_SIZE": CHUNK_SIZE.value,
            "CHUNK_OVERLAP": CHUNK_OVERLAP.value,
            "RAG_TEMPLATE": DEFAULT_RAG_TEMPLATE,
            "RAG_RERANKING_MODEL": RAG_RERANKING_MODEL.value,
            "RAG_EMBEDDING_BATCH_SIZE": RAG_EMBEDDING_BATCH_SIZE.value,
            "RAG_OPENAI_API_BASE_URL": "",
            "RAG_OPENAI_API_KEY": "",
            "RAG_OLLAMA_BASE_URL": "",
            "RAG_OLLAMA_API_KEY": "",
        }
    except ImportError:
        # Critical error: Cannot import required configuration modules
        error_msg = (
            "Critical configuration error: Unable to import required config modules. "
            "This will likely cause re-indexing and querying to fail due to potentially "
            "incorrect embedding model configuration."
        )
        log.error(error_msg)

        # Instead of silently falling back, raise an error to indicate the serious issue
        raise RuntimeError(
            "Configuration system unavailable. Cannot safely proceed with re-indexing "
            "operations as embedding model compatibility cannot be guaranteed."
        )


def create_mock_request_from_config(config: Dict[str, Any], ef=None):
    """Create a mock request object with the given configuration."""

    class MockRequest:
        def __init__(self, config_dict, embedding_function):
            # Create mock app state structure
            config_obj = type("Config", (), config_dict)()
            state_obj = type(
                "State", (), {"config": config_obj, "ef": embedding_function}
            )()
            app_obj = type("App", (), {"state": state_obj})()
            self.app = app_obj

    return MockRequest(config, ef)


def get_file_and_user_for_reindex(file_id: str):
    """Get file and user objects needed for re-indexing."""
    file = Files.get_file_by_id(file_id)
    if not file:
        return None, None

    user = Users.get_user_by_id(file.user_id) if file.user_id else None
    return file, user


def get_current_config_and_ef():
    """
    Get current configuration and embedding function, trying main app first,
    then falling back to database/environment.
    """
    try:
        from open_webui.main import app as main_app

        return main_app.state.config, getattr(main_app.state, "ef", None)
    except ImportError:
        # Fallback to creating config from environment/database
        config_dict = create_config_from_fallback()
        config_obj = type("Config", (), config_dict)()
        return config_obj, None


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

        # Get current configuration
        current_config, current_ef = get_current_config_and_ef()

        # Create mock request
        mock_request = create_mock_request_from_config(
            (
                current_config.__dict__
                if hasattr(current_config, "__dict__")
                else current_config
            ),
            current_ef,
        )

        # Attempt re-indexing
        if reindex_file_on_demand(file_id, mock_request, user):
            log.info(f"Re-indexing successful for {file_id}, retrying query...")

            # Retry the query after successful re-indexing
            try:
                result = query_doc(
                    collection_name=collection_name,
                    k=k,
                    query_embedding=query_embedding,
                )
                if result is not None:
                    log.info(
                        f"Query successful after re-indexing for {collection_name}"
                    )
                    return result.model_dump()

            except Exception as retry_e:
                log.error(
                    f"Query failed even after re-indexing {collection_name}: {retry_e}"
                )

        else:
            log.error(f"Re-indexing failed for {file_id}")

    except Exception as reindex_e:
        log.error(f"Error during re-indexing attempt for {file_id}: {reindex_e}")

    return None


def handle_collection_query_with_reindex(
    collection_name: str, k: int, query_embedding
) -> Optional[Dict[str, Any]]:
    """
    Handle querying a collection with automatic re-indexing on collection not found errors.
    This is the main interface that replaces the complex inline logic.
    """
    from open_webui.retrieval.utils import query_doc

    try:
        # First attempt at querying
        result = query_doc(
            collection_name=collection_name,
            k=k,
            query_embedding=query_embedding,
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
