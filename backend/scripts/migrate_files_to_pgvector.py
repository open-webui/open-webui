#!/usr/bin/env python
"""
Re-process all files from the uploads directory and embed them into pgvector.
Uses PostgreSQL tables (knowledge, file) to determine collection structure.
This ensures all embeddings are created with the current embedding model and processing pipeline.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Set, Any, Tuple
import hashlib
from datetime import datetime

if "WEBUI_SECRET_KEY" not in os.environ or os.environ.get("WEBUI_SECRET_KEY") == "":
    os.environ["WEBUI_SECRET_KEY"] = "test-script-temporary-key"
if "WEBUI_AUTH" not in os.environ:
    os.environ["WEBUI_AUTH"] = "False"

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from open_webui.models.knowledge import Knowledges
from open_webui.models.files import Files, FileModel
from open_webui.models.users import Users
from open_webui.storage.provider import Storage
from open_webui.retrieval.loaders.main import Loader
from open_webui.retrieval.vector.dbs.pgvector import PgvectorClient
from open_webui.retrieval.utils import get_single_batch_embedding_function
from sqlalchemy import text
from open_webui.config import (
    RAG_EMBEDDING_ENGINE,
    RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_BATCH_SIZE,
    RAG_OPENAI_API_BASE_URL,
    RAG_OPENAI_API_KEY,
    RAG_OLLAMA_BASE_URL,
    RAG_OLLAMA_API_KEY,
    CONTENT_EXTRACTION_ENGINE,
    TIKA_SERVER_URL,
    PDF_EXTRACT_IMAGES,
    DOCUMENT_INTELLIGENCE_ENDPOINT,
    DOCUMENT_INTELLIGENCE_KEY,
    RAG_TEXT_SPLITTER,
    TIKTOKEN_ENCODING_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter, TokenTextSplitter
from langchain_core.documents import Document
import tiktoken
import json
import uuid
import time
import requests
from requests.exceptions import HTTPError


# Set up logging with explicit name (after open_webui imports may have configured logging)
log = logging.getLogger("migrate_files_to_pgvector")
log.setLevel(logging.INFO)
# Ensure basic config is set (force=True to override any previous config)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-process files from uploads directory and embed into pgvector"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - don't actually insert into pgvector",
    )
    parser.add_argument(
        "--knowledge-id",
        type=str,
        help="Only process files for a specific knowledge base ID",
    )
    parser.add_argument(
        "--file-id",
        type=str,
        help="Only process a specific file ID",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing embeddings - re-process all files even if already complete (default: skip complete files)",
    )
    parser.add_argument(
        "--knowledge-only",
        action="store_true",
        help="Only process files that are part of knowledge bases (skip standalone files)",
    )
    return parser.parse_args()


def calculate_sha256_string(text: str) -> str:
    """Calculate SHA256 hash of a string."""
    return hashlib.sha256(text.encode()).hexdigest()


def load_and_split_file(
    file: FileModel,
    user_email: str,
    config: Dict,
) -> List[Document]:
    """
    Load a file and split it into documents using the same process as normal uploads.
    """
    try:
        # Get file path
        if not file.path:
            log.warning(f"File {file.id} ({file.filename}) has no path, skipping")
            return []
        
        file_path = Storage.get_file(file.path)
        if not os.path.exists(file_path):
            log.warning(f"File {file.id} ({file.filename}) not found at {file_path}, skipping")
            return []
        
        # Load file using Loader (same as normal uploads)
        loader = Loader(
            engine=CONTENT_EXTRACTION_ENGINE.value,
            TIKA_SERVER_URL=TIKA_SERVER_URL.value if TIKA_SERVER_URL.value else None,
            PDF_EXTRACT_IMAGES=PDF_EXTRACT_IMAGES.value if PDF_EXTRACT_IMAGES.value else False,
            DOCUMENT_INTELLIGENCE_ENDPOINT=DOCUMENT_INTELLIGENCE_ENDPOINT.value if DOCUMENT_INTELLIGENCE_ENDPOINT.value else None,
            DOCUMENT_INTELLIGENCE_KEY=DOCUMENT_INTELLIGENCE_KEY.value if DOCUMENT_INTELLIGENCE_KEY.value else None,
        )
        
        content_type = file.meta.get("content_type", "") if file.meta else ""
        
        # Check if file is an image that might not be processable
        file_ext = os.path.splitext(file.filename)[1].lower().lstrip('.')
        image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico', 'tiff', 'tif']
        is_image = file_ext in image_extensions or (content_type and content_type.startswith('image/'))
        
        try:
            docs = loader.load(file.filename, content_type, file_path)
        except TimeoutError as e:
            if is_image:
                log.warning(f"File {file.id} ({file.filename}) is an image file that cannot be processed as text. "
                           f"Image files require OCR/image processing (Tika or Document Intelligence). Skipping.")
            else:
                log.warning(f"Timeout while loading file {file.id} ({file.filename}): {e}. Skipping.")
            return []
        except UnicodeDecodeError as e:
            if is_image:
                log.warning(f"File {file.id} ({file.filename}) is an image file that cannot be decoded as text. "
                           f"Image files require OCR/image processing. Skipping.")
            else:
                log.warning(f"Unicode decode error for file {file.id} ({file.filename}): {e}. "
                           f"File may be binary or have unsupported encoding. Skipping.")
            return []
        except Exception as e:
            error_msg = str(e).lower()
            if 'timeout' in error_msg or 'encoding' in error_msg:
                if is_image:
                    log.warning(f"File {file.id} ({file.filename}) is an image file that cannot be processed. "
                               f"Image files require OCR/image processing (Tika or Document Intelligence). Skipping.")
                else:
                    log.warning(f"Error loading file {file.id} ({file.filename}): {e}. Skipping.")
            else:
                log.warning(f"Error loading file {file.id} ({file.filename}): {e}. Skipping.")
            return []
        
        if not docs:
            log.warning(f"No documents extracted from file {file.id} ({file.filename}). Skipping.")
            return []
        
        # Add metadata (same as normal uploads)
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
        
        # Split documents (same as normal uploads)
        chunk_size = CHUNK_SIZE.get(user_email) if hasattr(CHUNK_SIZE, 'get') else CHUNK_SIZE.value
        chunk_overlap = CHUNK_OVERLAP.get(user_email) if hasattr(CHUNK_OVERLAP, 'get') else CHUNK_OVERLAP.value
        
        text_splitter_value = RAG_TEXT_SPLITTER.value if hasattr(RAG_TEXT_SPLITTER, 'value') else str(RAG_TEXT_SPLITTER)
        if text_splitter_value in ["", "character"]:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                add_start_index=True,
            )
        elif text_splitter_value == "token":
            tiktoken_encoding = TIKTOKEN_ENCODING_NAME.value if hasattr(TIKTOKEN_ENCODING_NAME, 'value') else str(TIKTOKEN_ENCODING_NAME)
            tiktoken.get_encoding(tiktoken_encoding)
            text_splitter = TokenTextSplitter(
                encoding_name=tiktoken_encoding,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                add_start_index=True,
            )
        else:
            raise ValueError(f"Invalid text splitter: {text_splitter_value}")
        
        docs = text_splitter.split_documents(docs)
        
        return docs
        
    except Exception as e:
        log.warning(f"Unexpected error loading file {file.id} ({file.filename}): {e}. Skipping.")
        return []


def generate_embeddings_with_retry_and_split(
    texts: List[str],
    embedding_function,
    min_batch_size: int = 1,
    max_batch_size: int = 500,
    user=None,
    progress_bar=None,
) -> List:
    """
    Generate embeddings with retry logic and automatic batch splitting on failures.
    
    If retries fail, splits the batch in half and recursively processes smaller batches.
    This handles timeouts and network errors for large batches.
    
    Args:
        texts: List of text chunks to embed
        embedding_function: Function to generate embeddings
        min_batch_size: Minimum batch size before giving up (default: 1)
        max_batch_size: Maximum batch size before proactively splitting (default: 500)
        user: User object for embedding generation (optional)
        progress_bar: tqdm progress bar to update (optional)
    
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    # Proactively split very large batches to avoid rate limits
    if len(texts) > max_batch_size:
        log.info(f"Batch size ({len(texts)}) exceeds max_batch_size ({max_batch_size}). Splitting proactively...")
        mid = len(texts) // 2
        embeddings_first = generate_embeddings_with_retry_and_split(
            texts[:mid],
            embedding_function,
            min_batch_size,
            max_batch_size,
            user=user,
            progress_bar=progress_bar
        )
        embeddings_second = generate_embeddings_with_retry_and_split(
            texts[mid:],
            embedding_function,
            min_batch_size,
            max_batch_size,
            user=user,
            progress_bar=progress_bar
        )
        return embeddings_first + embeddings_second
    
    processed_texts = [text.replace("\n", " ") for text in texts]
    
    # Retry logic for network errors
    max_retries = 3
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            # Pass user parameter to match normal upload behavior
            # The embedding function signature is: lambda query, user=None
            embeddings = embedding_function(processed_texts, user=user)
            # Update progress bar if provided
            if progress_bar is not None:
                progress_bar.update(len(texts))
            return embeddings
        except Exception as e:
            # Check if it's a rate limit error (429)
            is_rate_limit = False
            if isinstance(e, HTTPError):
                is_rate_limit = e.response is not None and e.response.status_code == 429
            
            # Check if it's a network/connection/timeout error that we should retry
            error_str = str(e).lower()
            is_network_error = (
                isinstance(e, (requests.exceptions.ChunkedEncodingError,
                               requests.exceptions.ConnectionError,
                               requests.exceptions.Timeout)) or
                "connection" in error_str or
                "incompleteread" in error_str or
                "protocol" in error_str or
                "broken" in error_str or
                "timeout" in error_str or
                "429" in error_str or
                "too many requests" in error_str
            )
            
            # Rate limit errors should be retried with longer backoff
            is_retryable = is_network_error or is_rate_limit
            
            if is_retryable and retry_count < max_retries:
                retry_count += 1
                # Use longer backoff for rate limits (5, 10, 20 seconds)
                # Regular network errors use shorter backoff (2, 4, 8 seconds)
                if is_rate_limit:
                    wait_time = 5 * retry_count  # 5, 10, 15 seconds for rate limits
                    log.warning(f"Rate limit (429) error generating embeddings for {len(texts)} chunks (attempt {retry_count}/{max_retries})")
                else:
                    wait_time = 2 ** retry_count  # Exponential backoff: 2, 4, 8 seconds
                    log.warning(f"Network error generating embeddings for {len(texts)} chunks (attempt {retry_count}/{max_retries}): {type(e).__name__}")
                log.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                # Not a retryable error or max retries reached
                # If batch is large enough, try splitting it in half
                if len(texts) > min_batch_size and (is_retryable or "timeout" in error_str or "429" in error_str):
                    log.warning(f"Failed to generate embeddings for {len(texts)} chunks after {retry_count} retries. Splitting batch in half...")
                    mid = len(texts) // 2
                    
                    # Recursively process each half
                    # Pass original texts (not processed) - the function will process them internally
                    embeddings_first = generate_embeddings_with_retry_and_split(
                        texts[:mid],
                        embedding_function,
                        min_batch_size,
                        max_batch_size,
                        user=user,
                        progress_bar=progress_bar
                    )
                    embeddings_second = generate_embeddings_with_retry_and_split(
                        texts[mid:],
                        embedding_function,
                        min_batch_size,
                        max_batch_size,
                        user=user,
                        progress_bar=progress_bar
                    )
                    
                    # Combine results
                    return embeddings_first + embeddings_second
                else:
                    # Batch too small to split or non-retryable error
                    log.error(f"Failed to generate embeddings for {len(texts)} chunks: {e}")
                    raise
    
    raise ValueError("Failed to generate embeddings after all retries")


def check_file_completeness(
    file: FileModel,
    collections: List[str],
    expected_chunk_count: int,
    pg_client: PgvectorClient,
) -> Dict[str, Dict[str, Any]]:
    """
    Check if a file is already fully inserted in all its collections.
    
    Returns a dict mapping collection_name to status info:
    {
        "collection_name": {
            "exists": bool,
            "chunk_count": int,
            "is_complete": bool,
            "needs_processing": bool
        }
    }
    """
    status = {}
    
    for collection_name in collections:
        try:
            existing_chunks = pg_client.query(
                collection_name=collection_name,
                filter={"file_id": file.id}
            )
            
            if existing_chunks and existing_chunks.ids and existing_chunks.ids[0]:
                existing_count = len(existing_chunks.ids[0])
                is_complete = existing_count == expected_chunk_count
                status[collection_name] = {
                    "exists": True,
                    "chunk_count": existing_count,
                    "is_complete": is_complete,
                    "needs_processing": not is_complete,  # Process if incomplete
                }
            else:
                status[collection_name] = {
                    "exists": False,
                    "chunk_count": 0,
                    "is_complete": False,
                    "needs_processing": True,  # Process if missing
                }
        except Exception as e:
            # If query fails, assume collection doesn't exist or has issues
            log.debug(f"Error checking collection {collection_name} for file {file.id}: {e}")
            status[collection_name] = {
                "exists": False,
                "chunk_count": 0,
                "is_complete": False,
                "needs_processing": True,
            }
    
    return status


def process_file_to_collections(
    file: FileModel,
    collections: List[str],
    user_email: str,
    pg_client: PgvectorClient,
    embedding_function,
    user=None,
    overwrite: bool = False,
    dry_run: bool = False,
    skip_complete: bool = True,
) -> Tuple[bool, bool]:
    """
    Process a file and save to multiple collections.
    
    Returns:
        (success: bool, was_complete: bool) - success indicates if processing succeeded,
        was_complete indicates if the file was already complete and skipped
    """
    """
    Process a file and save to multiple collections.
    """
    try:
        # Load and split file
        docs = load_and_split_file(file, user_email, {})
        
        if not docs:
            # Error already logged in load_and_split_file with specific details
            return (False, False)
        
        # Prepare texts and metadatas
        texts = [doc.page_content for doc in docs]
        expected_chunk_count = len(texts)
        
        # Check completeness if skip_complete is enabled
        if skip_complete and not overwrite:
            completeness_status = check_file_completeness(
                file=file,
                collections=collections,
                expected_chunk_count=expected_chunk_count,
                pg_client=pg_client,
            )
            
            # Filter to only collections that need processing
            collections_to_process = [
                coll for coll in collections
                if completeness_status.get(coll, {}).get("needs_processing", True)
            ]
            
            # Check if all collections are complete
            if not collections_to_process:
                log.info(f"   ✅ File {file.id} ({file.filename}) is already complete in all {len(collections)} collections. Skipping.")
                return (True, True)  # Successfully skipped because complete
            
            # Log status for incomplete collections
            for coll in collections:
                status = completeness_status.get(coll, {})
                if status.get("exists") and not status.get("is_complete"):
                    log.info(f"   ⚠️  Collection {coll}: partial insert detected ({status['chunk_count']}/{expected_chunk_count} chunks). Will re-process.")
                elif status.get("is_complete"):
                    log.info(f"   ✅ Collection {coll}: already complete ({status['chunk_count']} chunks). Skipping.")
            
            collections = collections_to_process
        
        # Calculate hash from full document content (same as normal upload)
        # This matches the behavior in retrieval.py where hash is calculated from text_content
        # and the same hash is used for all chunks from the same file
        text_content = " ".join(texts)
        file_hash = calculate_sha256_string(text_content)
        
        metadatas = [
            {
                **doc.metadata,
                "hash": file_hash,  # Use same hash for all chunks (matches normal upload)
                "embedding_config": json.dumps({
                    "engine": RAG_EMBEDDING_ENGINE.value,
                    "model": RAG_EMBEDDING_MODEL.value,
                }),
            }
            for doc in docs
        ]
        
        # Convert datetime/list/dict to string (ChromaDB compatibility)
        # This matches the normal upload process in retrieval.py
        for metadata in metadatas:
            for key, value in metadata.items():
                if (
                    isinstance(value, datetime)
                    or isinstance(value, list)
                    or isinstance(value, dict)
                ):
                    if isinstance(value, datetime):
                        metadata[key] = str(value)
                    else:
                        metadata[key] = json.dumps(value)
        
        # Generate embeddings with retry and automatic batch splitting
        # Use a conservative max batch size to avoid rate limits (500 chunks per batch)
        # This is larger than typical RAG_EMBEDDING_BATCH_SIZE to allow batching, but small enough to avoid rate limits
        max_batch_size = 500
        log.info(f"Generating embeddings for {len(texts)} chunks from file {file.id} (max batch size: {max_batch_size})")
        
        embeddings = generate_embeddings_with_retry_and_split(
            texts, 
            embedding_function, 
            max_batch_size=max_batch_size, 
            user=user,
            progress_bar=None
        )
        
        if dry_run:
            log.info(f"[DRY RUN] Would insert {len(texts)} chunks into collections: {collections}")
            return (True, False)
        
        # Delete existing chunks for this file if overwrite
        if overwrite:
            for collection_name in collections:
                try:
                    log.info(f"Deleting existing chunks for file {file.id} from collection {collection_name}")
                    pg_client.delete(
                        collection_name=collection_name,
                        filter={"file_id": file.id}
                    )
                except Exception as e:
                    log.debug(f"Could not delete chunks from {collection_name} (may not exist): {e}")
                    # Fallback: delete entire collection if filter doesn't work
                    if pg_client.has_collection(collection_name=collection_name):
                        log.info(f"Deleting entire collection {collection_name} as fallback")
                        pg_client.delete_collection(collection_name=collection_name)
        
        # Insert into all collections
        # IMPORTANT: Since id is the primary key (not composite with collection_name),
        # we must generate unique IDs for each collection to avoid duplicate key errors
        for collection_name in collections:
            # Delete any existing chunks for this file in this collection BEFORE inserting
            # This prevents duplicates when:
            # - Handling partial inserts (some chunks inserted, some not)
            # - Using --overwrite flag (processing complete files)
            # - Re-processing files after errors
            # Note: If skip_complete is enabled, complete collections were already filtered out above,
            # but we still delete here as a safety measure for partial inserts
            try:
                existing_chunks = pg_client.query(
                    collection_name=collection_name,
                    filter={"file_id": file.id}
                )
                
                if existing_chunks and existing_chunks.ids and existing_chunks.ids[0]:
                    existing_count = len(existing_chunks.ids[0])
                    if existing_count > 0:
                        log.info(f"   Deleting {existing_count} existing chunks from {collection_name} before inserting (prevents duplicates)")
                        pg_client.delete(
                            collection_name=collection_name,
                            filter={"file_id": file.id}
                        )
            except Exception as e:
                log.debug(f"Error checking/deleting existing chunks in {collection_name}: {e}")
                # Continue anyway - if chunks exist, we'll get duplicate key errors and handle them below

            log.info(f"Inserting {len(texts)} chunks into collection {collection_name}")
            
            # Generate unique items for this collection with unique IDs
            collection_items = [
                {
                    "id": str(uuid.uuid4()),  # Unique ID per collection
                    "text": text,
                    "vector": embeddings[idx],
                    "metadata": metadatas[idx],
                }
                for idx, text in enumerate(texts)
            ]
            
            try:
                pg_client.insert(
                    collection_name=collection_name,
                    items=collection_items,
                )
            except Exception as e:
                # If duplicate key error, try to delete by file_id and retry
                if "duplicate key" in str(e).lower() or "unique" in str(e).lower():
                    log.warning(f"Duplicate key error for {collection_name}, deleting chunks by file_id and retrying")
                    try:
                        pg_client.delete(
                            collection_name=collection_name,
                            filter={"file_id": file.id}
                        )
                        # Regenerate items with new UUIDs
                        collection_items = [
                            {
                                "id": str(uuid.uuid4()),
                                "text": text,
                                "vector": embeddings[idx],
                                "metadata": metadatas[idx],
                            }
                            for idx, text in enumerate(texts)
                        ]
                        pg_client.insert(
                            collection_name=collection_name,
                            items=collection_items,
                        )
                    except Exception as e2:
                        log.exception(f"Error after cleanup: {e2}")
                        raise
                else:
                    log.exception(f"Error inserting into {collection_name}: {e}")
                    raise
        
        return (True, False)  # Successfully processed, was not complete
        
    except Exception as e:
        log.exception(f"Error processing file {file.id}: {e}")
        return (False, False)  # Failed, was not complete


def main() -> None:
    args = parse_args()
    
    # Force logging level (in case open_webui imports changed it)
    log.setLevel(logging.INFO)
    
    # Use print with flush to ensure output appears immediately
    print("=" * 80, flush=True)
    print("RE-PROCESSING FILES FROM UPLOADS TO PGVECTOR", flush=True)
    print("=" * 80, flush=True)
    
    log.info("=" * 80)
    log.info("RE-PROCESSING FILES FROM UPLOADS TO PGVECTOR")
    log.info("=" * 80)
    
    # Initialize pgvector client
    pg_client = PgvectorClient()
    
    # Initialize embedding function
    embedding_url = (
        RAG_OPENAI_API_BASE_URL.value
        if RAG_EMBEDDING_ENGINE.value in ["openai", "portkey"]
        else RAG_OLLAMA_BASE_URL.value
    )
    embedding_key = (
        RAG_OPENAI_API_KEY.value
        if RAG_EMBEDDING_ENGINE.value in ["openai", "portkey"]
        else RAG_OLLAMA_API_KEY.value
    )
    
    embedding_function = get_single_batch_embedding_function(
        RAG_EMBEDDING_ENGINE.value,
        RAG_EMBEDDING_MODEL.value,
        None,
        embedding_url,
        embedding_key,
        RAG_EMBEDDING_BATCH_SIZE.value,
        backoff=True,
    )
    
    # Build file-to-collections mapping
    file_to_collections: Dict[str, Set[str]] = {}
    
    # 1. Get all knowledge bases first (to build complete mapping)
    print("\n📚 Building collection mapping from knowledge bases...", flush=True)
    knowledge_bases = Knowledges.get_knowledge_bases()
    
    # Build mapping of file_id -> knowledge base IDs
    for kb in knowledge_bases:
        if args.knowledge_id and kb.id != args.knowledge_id:
            continue
        
        file_ids = kb.data.get("file_ids", []) if kb.data else []
        print(f"   Knowledge base '{kb.name}' (id: {kb.id}): {len(file_ids)} files", flush=True)
        
        for file_id in file_ids:
            if file_id not in file_to_collections:
                file_to_collections[file_id] = set()
            file_to_collections[file_id].add(kb.id)  # Add to knowledge base collection
    
    # 2. Get all files and ensure they're in the mapping
    print("\n📄 Processing files...", flush=True)
    all_files = Files.get_files()
    
    # Build complete list of files to process
    files_to_process = []
    if args.file_id:
        file = Files.get_file_by_id(args.file_id)
        if file:
            files_to_process.append(file)
        else:
            log.error(f"File {args.file_id} not found")
            return
    elif args.knowledge_id:
        # If processing a specific knowledge base, only process files in that KB
        kb = Knowledges.get_knowledge_by_id(args.knowledge_id)
        if not kb:
            log.error(f"Knowledge base {args.knowledge_id} not found")
            return
        file_ids = kb.data.get("file_ids", []) if kb.data else []
        for file_id in file_ids:
            file = Files.get_file_by_id(file_id)
            if file:
                files_to_process.append(file)
            else:
                log.warning(f"File {file_id} listed in knowledge base but not found in database")
    else:
        if args.knowledge_only:
            # Only process files that are in knowledge bases
            all_kb_file_ids = set()
            for kb in knowledge_bases:
                file_ids = kb.data.get("file_ids", []) if kb.data else []
                all_kb_file_ids.update(file_ids)
            
            files_to_process = []
            for file_id in all_kb_file_ids:
                file = Files.get_file_by_id(file_id)
                if file:
                    files_to_process.append(file)
                else:
                    log.warning(f"File {file_id} listed in knowledge base but not found in database")
            
            print(f"   Processing {len(files_to_process)} files from knowledge bases only", flush=True)
        else:
            # Process all files that are either:
            # 1. In any knowledge base, OR
            # 2. All files (to ensure file-{file.id} collections exist)
            files_to_process = all_files
            print(f"   Processing all {len(files_to_process)} files in database", flush=True)
    
    # Check if there are any files to process
    if not files_to_process:
        log.warning("No files to process! Exiting.")
        print("WARNING: No files found to process!", flush=True)
        return
    
    # Ensure all files have their file collection
    for file in files_to_process:
        if file.id not in file_to_collections:
            file_to_collections[file.id] = set()
        file_to_collections[file.id].add(f"file-{file.id}")  # Always add to file collection
    
    # Verify mapping completeness
    print(f"\n📊 Collection mapping summary:", flush=True)
    print(f"   Files to process: {len(files_to_process)}", flush=True)
    print(f"   Files with collections mapped: {len(file_to_collections)}", flush=True)
    
    # Check for files in knowledge bases that aren't in files_to_process
    all_kb_file_ids = set()
    for kb in knowledge_bases:
        if args.knowledge_id and kb.id != args.knowledge_id:
            continue
        file_ids = kb.data.get("file_ids", []) if kb.data else []
        all_kb_file_ids.update(file_ids)
    
    missing_files = all_kb_file_ids - {f.id for f in files_to_process}
    if missing_files:
        print(f"   ⚠️  {len(missing_files)} file(s) in knowledge bases but not in files_to_process:", flush=True)
        for file_id in missing_files:
            file = Files.get_file_by_id(file_id)
            if file:
                print(f"      - {file.filename} (id: {file_id}) - will be added to processing list", flush=True)
                files_to_process.append(file)
                if file.id not in file_to_collections:
                    file_to_collections[file.id] = set()
                file_to_collections[file.id].add(f"file-{file.id}")
            else:
                print(f"      - File not found (id: {file_id})", flush=True)
    
    # 3. Process each file
    print(f"\n🔄 Starting processing of {len(files_to_process)} files...", flush=True)
    print("=" * 80, flush=True)
    
    processed_count = 0
    failed_count = 0
    skipped_count = 0
    complete_count = 0  # Files that were already complete
    
    total_files = len(files_to_process)
    
    for i, file in enumerate(files_to_process):
        current_num = i + 1
        print(f"\n[{current_num}/{total_files}] 📄 Processing: {file.filename}", flush=True)
        
        collections = list(file_to_collections.get(file.id, set()))
        if not collections:
            log.warning(f"File {file.id} ({file.filename}) has no collections, skipping")
            skipped_count += 1
            continue
        
        # Get user email for chunk size/overlap
        user = Users.get_user_by_id(file.user_id)
        user_email = user.email if user else "default"
        
        # log.info(f"\n📄 Processing file: {file.filename} (id: {file.id})")
        # log.info(f"   Collections: {collections}")
        
        # Verify file exists
        if not file.path:
            log.warning(f"   ⚠️  File {file.id} has no path, skipping")
            skipped_count += 1
            continue
        
        file_path = Storage.get_file(file.path)
        if not os.path.exists(file_path):
            log.warning(f"   ⚠️  File not found at {file_path}, skipping")
            skipped_count += 1
            continue
        
        success, was_complete = process_file_to_collections(
            file=file,
            collections=collections,
            user_email=user_email,
            pg_client=pg_client,
            embedding_function=embedding_function,
            user=user,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            skip_complete=not args.overwrite,  # Skip complete files unless --overwrite is used
        )
        
        if was_complete:
            complete_count += 1
            # Already logged in process_file_to_collections
        elif success:
            processed_count += 1
            print(f"   ✅ Successfully processed file {file.id}", flush=True)
        else:
            failed_count += 1
            print(f"   ❌ Failed to process file {file.id}", flush=True)
        
    
    print("\n" + "=" * 80, flush=True)
    print("✅ PROCESSING COMPLETE", flush=True)
    print("-" * 80, flush=True)
    print(f"   Processed:              {processed_count}", flush=True)
    print(f"   Already complete:       {complete_count}", flush=True)
    print(f"   Failed:                 {failed_count}", flush=True)
    print(f"   Skipped:                {skipped_count}", flush=True)
    print("=" * 80, flush=True)
    
    # Rebuild pgvector index for optimal retrieval performance
    # IVFFlat indexes work best when built on the actual data distribution
    # This is critical for good retrieval performance after bulk inserts
    if not args.dry_run:
        log.info("\n🔧 Rebuilding pgvector index for optimal retrieval performance...")
        try:
            # Get approximate row count to calculate optimal lists parameter
            # lists should be approximately rows / 1000 for IVFFlat
            result = pg_client.session.execute(
                text("SELECT COUNT(*) FROM document_chunk")
            ).scalar()
            row_count = result if result else 0
            
            # Calculate optimal lists parameter (min 10, max 1000)
            optimal_lists = max(10, min(1000, row_count // 1000)) if row_count > 0 else 100
            
            log.info(f"   Total chunks: {row_count}")
            log.info(f"   Optimal lists parameter: {optimal_lists}")
            
            # Drop existing index
            pg_client.session.execute(
                text("DROP INDEX IF EXISTS idx_document_chunk_vector")
            )
            
            # Recreate index with optimal parameters
            pg_client.session.execute(
                text(
                    f"CREATE INDEX idx_document_chunk_vector "
                    f"ON document_chunk USING ivfflat (vector vector_cosine_ops) "
                    f"WITH (lists = {optimal_lists});"
                )
            )
            pg_client.session.commit()
            log.info("   ✅ Index rebuilt successfully")
        except Exception as e:
            log.warning(f"   ⚠️  Could not rebuild index: {e}")
            log.warning("   Index may need manual rebuilding for optimal performance")
            pg_client.session.rollback()
    


if __name__ == "__main__":
    print("Starting migration script...", flush=True)
    try:
        main()
        print("Migration script completed successfully.", flush=True)
    except Exception as e:
        log.exception(f"Fatal error in migration script: {e}")
        print(f"Script failed with error: {e}", flush=True)
        raise
