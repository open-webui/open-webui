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
            # Use the embedding_api_key passed from the job if available
            if self.config.RAG_EMBEDDING_ENGINE in ["openai", "portkey"]:
                api_url = self.config.RAG_OPENAI_API_BASE_URL
                # Use passed API key (from admin config) or fall back to env default
                api_key = embedding_api_key or self.config.RAG_OPENAI_API_KEY.default
                if embedding_api_key:
                    log.info(f"Using per-user embedding API key for Portkey (key length: {len(embedding_api_key)})")
                elif not api_key:
                    log.warning("No embedding API key provided - embedding may fail!")
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
    embedding_api_key: Optional[str] = None,
) -> dict:
    """
    Process a file job. This function is called by RQ workers.
    
    Args:
        file_id: ID of the file to process
        content: Optional pre-extracted content (for text files)
        collection_name: Optional collection name for embeddings
        knowledge_id: Optional knowledge base ID
        user_id: User ID who initiated the processing
        embedding_api_key: API key for embedding service (per-user, from admin config)
        
    Returns:
        Dictionary with processing result
    """
    start_time = time.time()
    
    log.info("=" * 80)
    log.info(f"[JOB START] Processing file job: file_id={file_id}")
    log.info(f"  user_id={user_id} | collection_name={collection_name} | knowledge_id={knowledge_id}")
    log.info(f"  content_provided={content is not None} | embedding_api_key_provided={embedding_api_key is not None}")
    
    # Create mock request object for compatibility with existing code
    # Pass the embedding_api_key so it can re-initialize the embedding function
    try:
        request = MockRequest(embedding_api_key=embedding_api_key)
        log.debug(f"MockRequest initialized successfully for file_id={file_id}")
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
                    log.debug(f"[JOB PROGRESS] Retrieved user: email={user.email} | id={user.id}")
                    
                    # CRITICAL: Ensure the user's API key is set in the config if it wasn't already
                    # This ensures save_docs_to_vector_db can retrieve it via config.get(user.email)
                    # The embedding_api_key passed to the job is used as fallback if config retrieval fails
                    if embedding_api_key and user.email:
                        try:
                            # Update the config with the user's API key to ensure consistency
                            # This is important because save_docs_to_vector_db retrieves the key from config
                            if request.app.state.config.RAG_EMBEDDING_ENGINE in ["openai", "portkey"]:
                                # Set the user's API key in the config cache
                                request.app.state.config.RAG_OPENAI_API_KEY.set(user.email, embedding_api_key)
                                log.debug(f"[JOB PROGRESS] Set user's API key in config for {user.email}")
                        except Exception as config_update_error:
                            # Non-critical - the key is already passed and will be used as fallback
                            log.debug(f"Could not update config with user API key: {config_update_error}")
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
            log.error(f"[JOB ERROR] File {file_id} not found for processing (user_id={user_id})")
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

        log.info(f"[JOB PROGRESS] File found: filename={file.filename} | content_type={file.meta.get('content_type')}")

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
                
                # Log extraction engine being used
                extraction_engine = request.app.state.config.CONTENT_EXTRACTION_ENGINE or "default (PyPDF)"
                log.info(
                    f"[Content Extraction] file_id={file.id} | filename={file.filename} | "
                    f"content_type={file.meta.get('content_type')} | engine={extraction_engine}"
                )
                
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
                
                # Log extraction results for debugging
                total_chars = sum(len(doc.page_content) for doc in docs)
                non_empty_docs = [doc for doc in docs if doc.page_content.strip()]
                log.info(
                    f"[Content Extraction Result] file_id={file.id} | "
                    f"pages_extracted={len(docs)} | non_empty_pages={len(non_empty_docs)} | "
                    f"total_chars={total_chars}"
                )
                
                # Warn if extraction returned empty content
                if total_chars == 0:
                    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else "unknown"
                    log.warning(
                        f"[Content Extraction WARNING] file_id={file.id} | filename={file.filename} | "
                        f"No text content extracted! Possible reasons:\n"
                        f"  - Scanned image PDF (no OCR text layer)\n"
                        f"  - Protected/encrypted file\n"
                        f"  - Unsupported encoding\n"
                        f"  Suggestions:\n"
                        f"  - For scanned PDFs: Enable Document Intelligence (Azure OCR) in Settings > Documents\n"
                        f"  - For better extraction: Configure Tika server\n"
                        f"  - Current engine: {extraction_engine}"
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
                text_content = " ".join([doc.page_content for doc in docs])
            else:
                # No file path - use empty content (should not happen normally)
                log.warning(f"[Content Extraction] file_id={file.id} | No file path available, using empty content")
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

        # Validate that we have content to process
        from open_webui.constants import ERROR_MESSAGES
        
        if not docs or len(docs) == 0:
            error_msg = ERROR_MESSAGES.EMPTY_CONTENT
            log.error(
                f"[JOB ERROR] No content extracted for file_id={file.id} | filename={file.filename}"
            )
            Files.update_file_metadata_by_id(
                file.id,
                {
                    "processing_status": "error",
                    "processing_error": error_msg,
                },
            )
            raise ValueError(error_msg)
        
        # Also check if all docs are empty (no actual content)
        total_chars = sum(len(doc.page_content) for doc in docs)
        if total_chars == 0:
            error_msg = ERROR_MESSAGES.EMPTY_CONTENT
            log.error(
                f"[JOB ERROR] All extracted content is empty for file_id={file.id} | filename={file.filename}"
            )
            Files.update_file_metadata_by_id(
                file.id,
                {
                    "processing_status": "error",
                    "processing_error": error_msg,
                },
            )
            raise ValueError(error_msg)

        log.debug(f"text_content length: {len(text_content)} chars, docs count: {len(docs)}")
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

        elapsed_time = time.time() - start_time
        log.info(f"[JOB SUCCESS] Successfully processed file: file_id={file_id} | elapsed_time={elapsed_time:.2f}s")
        log.info("=" * 80)
        return {
            "status": "completed",
            "file_id": file_id,
            "collection_name": collection_name,
            "elapsed_time": elapsed_time,
        }

    except Exception as e:
        # Consolidated error handling - log and update status
        elapsed_time = time.time() - start_time
        error_msg = str(e)
        log.error("=" * 80)
        log.error(
            f"[JOB FAILED] Error in file processing job: file_id={file_id} | "
            f"user_id={user_id} | elapsed_time={elapsed_time:.2f}s"
        )
        log.error(f"Error message: {error_msg}")
        log.exception(e)
        log.error("=" * 80)
        
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

