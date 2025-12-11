"""
File Processing Worker for RQ Job Queue

This module contains the worker function that processes file jobs enqueued in Redis.
Workers run in separate processes and can be distributed across multiple pods.
"""

import logging
import os
import time
from typing import Optional

from langchain_core.documents import Document

from open_webui.models.files import FileModel, Files
from open_webui.models.users import Users
from open_webui.models.knowledge import Knowledges
from open_webui.storage.provider import Storage
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.retrieval.loaders.main import Loader
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
)
from open_webui.retrieval.utils import get_embedding_function

log = logging.getLogger(__name__)


class MockRequest:
    """
    Mock Request object for workers that need app.state.config.
    Workers run in separate processes and don't have access to the FastAPI Request object.
    """
    def __init__(self):
        self.app = MockApp()


class MockApp:
    """
    Mock app object that provides access to config and other app state.
    """
    def __init__(self):
        # Initialize config (this reads from environment and database)
        self.state = MockState()


class MockState:
    """
    Mock state object that provides access to configuration and embedding functions.
    """
    def __init__(self):
        # Initialize config with error handling
        # AppConfig may fail if database is not accessible or not initialized
        try:
            self.config = AppConfig()
        except Exception as config_error:
            log.error(
                f"Failed to initialize AppConfig in worker process: {config_error}. "
                "Using fallback configuration. This may cause issues with file processing.",
                exc_info=True
            )
            # Create a minimal fallback config object that has required attributes
            # This allows the worker to continue but with limited functionality
            self.config = _create_fallback_config()
        
        # Initialize embedding functions (ef, rf, EMBEDDING_FUNCTION)
        # These are required by save_docs_to_vector_db() and save_docs_to_multiple_collections()
        # Use same initialization logic as main.py
        try:
            # Initialize embedding function model (ef)
            self.ef = get_ef(
                self.config.RAG_EMBEDDING_ENGINE,
                self.config.RAG_EMBEDDING_MODEL,
                RAG_EMBEDDING_MODEL_AUTO_UPDATE,
            )
            
            # Initialize reranking function (rf)
            self.rf = get_rf(
                self.config.RAG_RERANKING_MODEL,
                RAG_RERANKING_MODEL_AUTO_UPDATE,
            )
            
            # Initialize embedding function for queries
            # Determine API URL and key based on engine type
            # Note: RAG_OPENAI_API_KEY is now a UserScopedConfig, use default at worker init
            # Per-user API keys are retrieved during actual document processing
            if self.config.RAG_EMBEDDING_ENGINE in ["openai", "portkey"]:
                api_url = self.config.RAG_OPENAI_API_BASE_URL
                # Use default API key from env var or empty string
                api_key = self.config.RAG_OPENAI_API_KEY.default
            else:
                api_url = self.config.RAG_OLLAMA_BASE_URL
                api_key = self.config.RAG_OLLAMA_API_KEY
            
            self.EMBEDDING_FUNCTION = get_embedding_function(
                self.config.RAG_EMBEDDING_ENGINE,
                self.config.RAG_EMBEDDING_MODEL,
                self.ef,
                api_url,
                api_key,
                self.config.RAG_EMBEDDING_BATCH_SIZE,
            )
            
            log.debug(
                f"Initialized embedding functions in worker: "
                f"engine={self.config.RAG_EMBEDDING_ENGINE}, "
                f"model={self.config.RAG_EMBEDDING_MODEL}"
            )
        except Exception as embedding_error:
            log.error(
                f"Failed to initialize embedding functions in worker process: {embedding_error}. "
                "File processing may fail if embeddings are required.",
                exc_info=True
            )
            # Set to None - functions that use these should handle None gracefully
            self.ef = None
            self.rf = None
            self.EMBEDDING_FUNCTION = None


class _FallbackConfig:
    """
    Fallback configuration object used when AppConfig initialization fails.
    Provides minimal required attributes with safe defaults.
    """
    def __init__(self):
        # Set minimal required attributes with safe defaults
        self.CONTENT_EXTRACTION_ENGINE = os.environ.get("CONTENT_EXTRACTION_ENGINE", "auto")
        self.TIKA_SERVER_URL = os.environ.get("TIKA_SERVER_URL", "")
        self.PDF_EXTRACT_IMAGES = os.environ.get("PDF_EXTRACT_IMAGES", "False").lower() == "true"
        self.DOCUMENT_INTELLIGENCE_ENDPOINT = os.environ.get("DOCUMENT_INTELLIGENCE_ENDPOINT", "")
        self.DOCUMENT_INTELLIGENCE_KEY = os.environ.get("DOCUMENT_INTELLIGENCE_KEY", "")
        self.BYPASS_EMBEDDING_AND_RETRIEVAL = os.environ.get("BYPASS_EMBEDDING_AND_RETRIEVAL", "False").lower() == "true"
    
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
) -> dict:
    """
    Process a file job. This function is called by RQ workers.
    
    Args:
        file_id: ID of the file to process
        content: Optional pre-extracted content (for text files)
        collection_name: Optional collection name for embeddings
        knowledge_id: Optional knowledge base ID
        user_id: User ID who initiated the processing
        
    Returns:
        Dictionary with processing result
    """
    # Create mock request object for compatibility with existing code
    request = MockRequest()
    
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
            except Exception as user_error:
                log.warning(
                    f"Error retrieving user {user_id} for file processing (file_id={file_id}): {user_error}, "
                    "processing without user context"
                )
        
        # Update status to processing
        Files.update_file_metadata_by_id(
            file_id,
            {
                "processing_status": "processing",
                "processing_started_at": int(time.time()),
            },
        )
        
        file = Files.get_file_by_id(file_id)
        if not file:
            error_msg = "File not found"
            log.error(f"File {file_id} not found for processing (user_id={user_id})")
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

        if collection_name is None:
            collection_name = f"file-{file.id}"

        if content:
            # Update the content in the file
            try:
                VECTOR_DB_CLIENT.delete_collection(collection_name=f"file-{file.id}")
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
        elif collection_name:
            # Check if the file has already been processed and save the content
            result = VECTOR_DB_CLIENT.query(
                collection_name=f"file-{file.id}", filter={"file_id": file.id}
            )

            if result is not None and result.ids and len(result.ids) > 0 and len(result.ids[0]) > 0:
                docs = [
                    Document(
                        page_content=result.documents[0][idx],
                        metadata=result.metadatas[0][idx],
                    )
                    for idx, id in enumerate(result.ids[0])
                ]
            else:
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

            text_content = file.data.get("content", "")
        else:
            # Process the file and save the content
            file_path = file.path
            if file_path:
                file_path = Storage.get_file(file_path)
                loader = Loader(
                    engine=request.app.state.config.CONTENT_EXTRACTION_ENGINE,
                    TIKA_SERVER_URL=request.app.state.config.TIKA_SERVER_URL,
                    PDF_EXTRACT_IMAGES=request.app.state.config.PDF_EXTRACT_IMAGES,
                    DOCUMENT_INTELLIGENCE_ENDPOINT=request.app.state.config.DOCUMENT_INTELLIGENCE_ENDPOINT,
                    DOCUMENT_INTELLIGENCE_KEY=request.app.state.config.DOCUMENT_INTELLIGENCE_KEY,
                )
                docs = loader.load(
                    file.filename, file.meta.get("content_type"), file_path
                )

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
            else:
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

        log.debug(f"text_content: {text_content}")
        Files.update_file_data_by_id(
            file.id,
            {"content": text_content},
        )

        hash = calculate_sha256_string(text_content)
        Files.update_file_hash_by_id(file.id, hash)

        if not request.app.state.config.BYPASS_EMBEDDING_AND_RETRIEVAL:
            try:
                # If knowledge_id is provided, we're adding to both collections at once
                if knowledge_id:
                    file_collection = f"file-{file.id}"
                    collections = [file_collection, knowledge_id]

                    log.info(
                        f"Processing file file_id={file.id}, filename={file.filename} "
                        f"for both file collection and knowledge base: collections={collections}, "
                        f"user_id={user_id}"
                    )

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

                    # Use file collection name for file metadata
                    if result:
                        Files.update_file_metadata_by_id(
                            file.id,
                            {
                                "collection_name": file_collection,
                                "processing_status": "completed",
                                "processing_completed_at": int(time.time()),
                            },
                        )
                    else:
                        Files.update_file_metadata_by_id(
                            file.id,
                            {
                                "processing_status": "error",
                                "processing_error": "Failed to save to vector DB",
                            },
                        )
                else:
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

                    if result:
                        Files.update_file_metadata_by_id(
                            file.id,
                            {
                                "collection_name": collection_name,
                                "processing_status": "completed",
                                "processing_completed_at": int(time.time()),
                            },
                        )
                    else:
                        Files.update_file_metadata_by_id(
                            file.id,
                            {
                                "processing_status": "error",
                                "processing_error": "Failed to save to vector DB",
                            },
                        )
            except Exception as e:
                error_msg = str(e)
                log.error(
                    f"Error saving file to vector DB: file_id={file.id}, "
                    f"filename={file.filename}, user_id={user_id}, error={error_msg}"
                )
                log.exception(e)
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
            # Bypass embedding, just mark as completed
            Files.update_file_metadata_by_id(
                file.id,
                {
                    "processing_status": "completed",
                    "processing_completed_at": int(time.time()),
                },
            )

        log.info(f"Successfully processed file: file_id={file_id}")
        return {
            "status": "completed",
            "file_id": file_id,
            "collection_name": collection_name,
        }

    except Exception as e:
        # Consolidated error handling - log and update status
        error_msg = str(e)
        log.error(
            f"Error in file processing job for file_id={file_id}, "
            f"user_id={user_id}, error={error_msg}"
        )
        log.exception(e)
        
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
        
        # Re-raise the exception so RQ knows the job failed
        raise

