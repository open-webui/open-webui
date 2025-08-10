"""
Syncs content from external providers (Google Drive, OneDrive, etc.)

Handles:
- Downloading files from providers with retry logic
- Creating/updating files with deterministic IDs
- Batch operations with rollback on failure
- Simple duplicate detection via file hashes
- Knowledge base synchronization
"""

import logging
import time
import hashlib
import io
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass
from enum import Enum
from contextlib import asynccontextmanager
from fastapi import HTTPException, Request, status

from open_webui.models.files import Files, FileModel, FileForm
from open_webui.models.knowledge import Knowledges
from open_webui.storage.provider import Storage
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
from open_webui.routers.retrieval import process_file, ProcessFileForm
from open_webui.utils.misc import calculate_sha256_string
from open_webui.constants import ERROR_MESSAGES
from open_webui.content_sources import content_source_registry, content_source_factory

# Import PDF text extraction capability
try:
    from langchain_community.document_loaders import PyPDFLoader
    import tempfile
    PDF_EXTRACTION_AVAILABLE = True
except ImportError:
    PDF_EXTRACTION_AVAILABLE = False

# Configure logging
log = logging.getLogger(__name__)


class SyncAction(Enum):
    """Enumeration of possible sync actions."""
    CREATED = "created"
    UPDATED = "updated"  
    UNCHANGED = "unchanged"
    SKIPPED = "skipped"
    FAILED = "failed"


class SyncStatus(Enum):
    """Enumeration of sync operation statuses."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class SyncResult:
    """Result of a single file sync operation."""
    file_id: Optional[str]
    action: SyncAction
    error: Optional[str] = None
    warnings: List[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class BatchSyncResult:
    """Result of a batch sync operation."""
    status: SyncStatus
    added_files: List[str]
    updated_files: List[str]
    unchanged_files: List[str]
    removed_files: List[str]  # Track files that were removed
    duplicate_files: List[Dict[str, Any]]
    failed_files: List[Dict[str, Any]]
    errors: List[Dict[str, str]]
    warnings: List[str]
    total_processed: int
    changes: bool
    rollback_performed: bool = False

    @property
    def successful_files(self) -> List[str]:
        """Get list of all successfully processed files."""
        return self.added_files + self.updated_files + self.unchanged_files


@dataclass
class KnowledgeSyncResult:
    """Result of a knowledge base sync operation."""
    knowledge_base_id: str
    sync_results: BatchSyncResult
    file_ids_updated: List[str]
    metadata_updated: bool
    sync_timestamp: int


@dataclass
class DuplicateCheckResult:
    """Result of duplicate content checking."""
    is_duplicate: bool
    existing_file_ids: List[str]
    hash_checked: Optional[str] = None
    collection_name: Optional[str] = None


class ContentSourceSyncer:
    """
    Central service for content synchronization operations.
    
    This service handles:
    - File creation and updates from various content sources
    - Knowledge base synchronization with providers
    - Duplicate detection and prevention
    - Rollback capabilities for failed operations
    - Comprehensive error handling and logging
    """

    def __init__(self):
        self.storage = Storage
        self._active_operations: Set[str] = set()
    
    def _extract_text_from_pdf(self, pdf_content: bytes) -> Optional[str]:
        """
        Extract text from PDF content using PyPDFLoader.
        
        Args:
            pdf_content: Binary PDF content
            
        Returns:
            Extracted text as string, or None if extraction fails
        """
        if not PDF_EXTRACTION_AVAILABLE:
            log.warning("PDF text extraction not available - PyPDFLoader not installed")
            return None
            
        try:
            # Create a temporary file to store PDF content
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(pdf_content)
                tmp_file_path = tmp_file.name
            
            try:
                # Use PyPDFLoader to extract text
                loader = PyPDFLoader(tmp_file_path)
                documents = loader.load()
                
                # Combine all pages into single text
                text_content = "\n\n".join([doc.page_content for doc in documents])
                
                # Clean up empty lines and excessive whitespace
                text_content = "\n".join(line for line in text_content.split("\n") if line.strip())
                
                if text_content.strip():
                    log.info(f"Successfully extracted {len(text_content)} characters from PDF")
                    return text_content
                else:
                    log.warning("PDF text extraction produced empty content")
                    return None
                    
            finally:
                # Clean up temporary file
                import os
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
                    
        except Exception as e:
            log.error(f"Failed to extract text from PDF: {e}")
            return None

    async def sync_file(self, file_id: str, request: Request, user_id: str) -> SyncResult:
        """
        Synchronize a single file by re-processing it into the vector database.
        
        Args:
            file_id: The ID of the file to sync
            request: FastAPI request object for processing context
            user_id: ID of the user performing the sync
            
        Returns:
            SyncResult containing the outcome of the sync operation
            
        Raises:
            HTTPException: If file not found or sync fails
        """
        operation_id = f"sync_file_{file_id}_{int(time.time())}"
        
        try:
            # Prevent concurrent operations on the same file
            if file_id in self._active_operations:
                log.warning(f"Sync already in progress for file {file_id}")
                return SyncResult(
                    file_id=file_id,
                    action=SyncAction.SKIPPED,
                    error="Sync already in progress"
                )
            
            self._active_operations.add(file_id)
            log.info(f"Starting sync for file {file_id} (operation: {operation_id})")
            
            # Get the file
            file = Files.get_file_by_id(file_id)
            if not file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )
            
            # Check if file has content to process
            if not file.data or not file.data.get("content"):
                log.warning(f"File {file_id} has no content to process")
                return SyncResult(
                    file_id=file_id,
                    action=SyncAction.SKIPPED,
                    warnings=["File has no content to process"]
                )
            
            # Process the file into vector database
            try:
                collection_name = f"file-{file_id}"
                process_file(
                    request,
                    ProcessFileForm(file_id=file_id, collection_name=collection_name),
                    user=type('User', (), {'id': user_id})()
                )
                
                log.info(f"Successfully synced file {file_id}")
                return SyncResult(
                    file_id=file_id,
                    action=SyncAction.UPDATED,
                    metadata={"collection_name": collection_name}
                )
                
            except Exception as e:
                error_msg = str(e)
                log.error(f"Failed to process file {file_id}: {error_msg}")
                return SyncResult(
                    file_id=file_id,
                    action=SyncAction.FAILED,
                    error=error_msg
                )
        
        except HTTPException:
            raise
        except Exception as e:
            error_context = {
                'file_id': file_id,
                'operation': 'sync_file',
                'user_id': user_id,
                'error_type': type(e).__name__,
                'error_details': str(e)
            }
            log.error(f"Unexpected error syncing file {file_id}: {error_context}", exc_info=True)
            return SyncResult(
                file_id=file_id,
                action=SyncAction.FAILED,
                error=f"Sync failed ({type(e).__name__}): {str(e)}",
                metadata={'error_context': error_context}
            )
        finally:
            self._active_operations.discard(file_id)

    async def sync_provider_files(
        self, 
        provider_name: str, 
        source_id: str, 
        options: Dict[str, Any],
        request: Request,
        user_id: str,
        knowledge_base_id: Optional[str] = None
    ) -> BatchSyncResult:
        """
        Synchronize files from a content provider.
        
        Args:
            provider_name: Name of the content provider (e.g., 'google_drive')
            source_id: Provider-specific source identifier (e.g., folder ID)
            options: Sync options and configuration
            request: FastAPI request object
            user_id: ID of the user performing the sync
            knowledge_base_id: Optional knowledge base ID for direct sync
            
        Returns:
            BatchSyncResult containing detailed sync results
            
        Raises:
            HTTPException: If provider not found or not configured
        """
        operation_id = f"sync_provider_{provider_name}_{source_id}_{int(time.time())}"
        log.info(f"Starting provider sync (operation: {operation_id})")
        
        # Initialize result tracking
        result = BatchSyncResult(
            status=SyncStatus.SUCCESS,
            added_files=[],
            updated_files=[],
            unchanged_files=[],
            removed_files=[],
            duplicate_files=[],
            failed_files=[],
            errors=[],
            warnings=[],
            total_processed=0,
            changes=False
        )
        
        processed_files = []  # Track for potential rollback
        
        try:
            # Get and validate provider with enhanced error context
            try:
                provider = await self._get_configured_provider(provider_name)
            except Exception as e:
                error_msg = f"Provider '{provider_name}' initialization failed: {str(e)}"
                log.error(error_msg, extra={
                    'provider': provider_name,
                    'source_id': source_id,
                    'operation_id': operation_id
                })
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=error_msg
                )
            
            # Track existing files in knowledge base if provided
            existing_provider_files = {}
            if knowledge_base_id:
                knowledge = Knowledges.get_knowledge_by_id(id=knowledge_base_id)
                if knowledge and knowledge.data:
                    file_ids = knowledge.data.get("file_ids", [])
                    # Get files that belong to this provider
                    existing_files = Files.get_files_by_ids(file_ids)
                    for file in existing_files:
                        if file.provider == provider_name:
                            existing_provider_files[file.provider_file_id] = file.id
            
            # List files from provider with enhanced logging
            log.info(f"Listing files from {provider_name} source {source_id}", extra={
                'provider': provider_name,
                'source_id': source_id,
                'options': options,
                'operation_id': operation_id
            })
            
            try:
                files = await provider.list_files(source_id, recursive=True)
                result.total_processed = len(files)
                
                log.info(f"Found {len(files)} files to process from {provider_name}", extra={
                    'file_count': len(files),
                    'provider': provider_name,
                    'source_id': source_id
                })
            except Exception as e:
                provider_error = f"{provider_name} list_files failed"
                if hasattr(e, 'resp') and hasattr(e.resp, 'status'):
                    provider_error += f" (HTTP {e.resp.status})"
                provider_error += f": {str(e)}"
                
                log.error(provider_error, extra={
                    'provider': provider_name,
                    'source_id': source_id,
                    'error_type': type(e).__name__
                })
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=provider_error
                )
            
            # Track current provider file IDs
            current_provider_file_ids = set()
            
            # Process each file
            for file_info in files:
                # Track this file as still existing
                current_provider_file_ids.add(file_info['id'])
                try:
                    sync_result = await self._process_single_provider_file(
                        provider, provider_name, file_info, options, user_id
                    )
                    
                    # Track the result
                    if sync_result.file_id:
                        processed_files.append(sync_result.file_id)
                    
                    # Update batch result based on individual result
                    if sync_result.action == SyncAction.CREATED:
                        result.added_files.append(sync_result.file_id)
                        result.changes = True
                    elif sync_result.action == SyncAction.UPDATED:
                        result.updated_files.append(sync_result.file_id)
                        result.changes = True
                    elif sync_result.action == SyncAction.UNCHANGED:
                        result.unchanged_files.append(sync_result.file_id)
                    elif sync_result.action == SyncAction.SKIPPED:
                        if "duplicate" in sync_result.error.lower() if sync_result.error else False:
                            result.duplicate_files.append({
                                'file_id': sync_result.file_id,
                                'name': file_info.get('name', 'unknown'),
                                'reason': sync_result.error
                            })
                        else:
                            result.warnings.extend(sync_result.warnings)
                    else:  # FAILED
                        result.failed_files.append({
                            'file_id': sync_result.file_id,
                            'name': file_info.get('name', 'unknown'),
                            'error': sync_result.error
                        })
                        result.errors.append({
                            'file': file_info.get('name', 'unknown'),
                            'error': sync_result.error
                        })
                        
                except Exception as e:
                    file_name = file_info.get('name', 'unknown')
                    file_id = file_info.get('id', 'unknown')
                    
                    # Enhanced error with provider context and error codes
                    error_details = {
                        'provider': provider_name,
                        'file_name': file_name,
                        'file_id': file_id,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    }
                    
                    # Check for specific provider error codes
                    if hasattr(e, 'resp') and hasattr(e.resp, 'status'):
                        error_details['http_status'] = e.resp.status
                        if e.resp.status == 403:
                            error_details['error_category'] = 'permission_denied'
                        elif e.resp.status == 404:
                            error_details['error_category'] = 'not_found'
                        elif e.resp.status == 429:
                            error_details['error_category'] = 'rate_limited'
                        elif e.resp.status >= 500:
                            error_details['error_category'] = 'provider_error'
                    
                    log.error(f"Error processing {provider_name} file '{file_name}': {error_details}", 
                             extra=error_details)
                    
                    result.failed_files.append({
                        'file_id': file_id,
                        'name': file_name,
                        'error': str(e),
                        'error_details': error_details
                    })
                    result.errors.append({
                        'file': file_name,
                        'error': str(e),
                        'provider': provider_name,
                        'error_category': error_details.get('error_category', 'unknown')
                    })
            
            # Detect and handle removed files
            if knowledge_base_id and existing_provider_files:
                # Find files that exist in knowledge base but not in provider anymore
                removed_provider_file_ids = set(existing_provider_files.keys()) - current_provider_file_ids
                
                for provider_file_id in removed_provider_file_ids:
                    file_id = existing_provider_files[provider_file_id]
                    try:
                        # Remove file from storage and database
                        file = Files.get_file_by_id(file_id)
                        if file:
                            # Delete from vector database
                            try:
                                VECTOR_DB_CLIENT.delete_collection(collection_name=f"file-{file_id}")
                            except Exception as e:
                                log.warning(f"Failed to delete vector collection for file {file_id}: {e}")
                            
                            # Delete file record
                            if Files.delete_file_by_id(file_id):
                                result.removed_files.append(file_id)
                                result.changes = True
                                log.info(f"Removed file {file_id} (provider file {provider_file_id}) - no longer in source")
                            else:
                                log.warning(f"Failed to delete file record {file_id}")
                    except Exception as e:
                        log.error(f"Error removing file {file_id}: {e}")
                        result.errors.append({
                            'file': file_id,
                            'error': f"Failed to remove: {str(e)}",
                            'provider': provider_name
                        })
            
            # Determine overall status
            if result.failed_files and not (result.added_files or result.updated_files or result.removed_files):
                result.status = SyncStatus.FAILED
            elif result.failed_files:
                result.status = SyncStatus.PARTIAL_SUCCESS
            else:
                result.status = SyncStatus.SUCCESS
                
            log.info(f"Provider sync completed: {result.status.value}, "
                    f"added: {len(result.added_files)}, "
                    f"updated: {len(result.updated_files)}, "
                    f"removed: {len(result.removed_files)}, "
                    f"failed: {len(result.failed_files)}")
            
            return result
            
        except Exception as e:
            # Enhanced batch operation error with full context
            batch_error = {
                'provider': provider_name,
                'source_id': source_id,
                'operation_id': operation_id,
                'files_processed': len(processed_files),
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
            
            log.error(f"Provider sync batch operation failed: {batch_error}", 
                     exc_info=True, extra=batch_error)
            
            # Perform rollback if configured and we have processed files
            if options.get('rollback_on_error', True) and processed_files:
                log.info(f"Initiating rollback for {len(processed_files)} processed files", extra={
                    'operation_id': operation_id,
                    'rollback_count': len(processed_files)
                })
                rollback_success = await self._rollback_files(processed_files)
                result.rollback_performed = rollback_success
                
                if rollback_success:
                    log.info(f"Rollback completed successfully", extra={'operation_id': operation_id})
                else:
                    log.error(f"Rollback failed or partially completed", extra={'operation_id': operation_id})
            
            result.status = SyncStatus.FAILED
            result.errors.append({
                'file': 'batch_operation',
                'error': str(e),
                'provider': provider_name,
                'error_details': batch_error
            })
            
            return result

    async def sync_knowledge_base(
        self, 
        kb_id: str, 
        request: Request, 
        user_id: str,
        provider_configs: Optional[List[Dict[str, Any]]] = None
    ) -> KnowledgeSyncResult:
        """
        Synchronize an entire knowledge base, either reprocessing existing files
        or syncing from configured providers.
        
        Args:
            kb_id: Knowledge base ID
            request: FastAPI request object
            user_id: ID of the user performing the sync
            provider_configs: Optional list of provider configurations for sync
            
        Returns:
            KnowledgeSyncResult containing sync results and metadata
            
        Raises:
            HTTPException: If knowledge base not found or access denied
        """
        log.info(f"Starting knowledge base sync for {kb_id}")
        
        # Get knowledge base
        knowledge = Knowledges.get_knowledge_by_id(kb_id)
        if not knowledge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found"
            )
        
        # Get existing file IDs
        data = knowledge.data or {}
        existing_file_ids = data.get("file_ids", [])
        
        sync_timestamp = int(time.time())
        
        if provider_configs:
            # Sync from providers
            all_results = []
            all_new_file_ids = set(existing_file_ids)
            
            for provider_config in provider_configs:
                provider_result = await self.sync_provider_files(
                    provider_name=provider_config['provider'],
                    source_id=provider_config['source_id'],
                    options=provider_config.get('options', {}),
                    request=request,
                    user_id=user_id,
                    knowledge_base_id=kb_id
                )
                all_results.append(provider_result)
                all_new_file_ids.update(provider_result.successful_files)
            
            # Combine all results
            combined_result = self._combine_batch_results(all_results)
            
            # Update knowledge base file IDs
            updated_file_ids = list(all_new_file_ids)
            data["file_ids"] = updated_file_ids
            
            # Update sync metadata
            data.setdefault("sync_metadata", {})
            for i, provider_config in enumerate(provider_configs):
                provider_name = provider_config['provider']
                data["sync_metadata"][provider_name] = {
                    "source_id": provider_config['source_id'],
                    "last_sync": sync_timestamp,
                    "options": provider_config.get('options', {}),
                    "results": {
                        "added": all_results[i].added_files,
                        "updated": all_results[i].updated_files,
                        "errors": len(all_results[i].errors)
                    }
                }
            
            # Update knowledge base
            knowledge = Knowledges.update_knowledge_data_by_id(kb_id, data)
            
            return KnowledgeSyncResult(
                knowledge_base_id=kb_id,
                sync_results=combined_result,
                file_ids_updated=updated_file_ids,
                metadata_updated=True,
                sync_timestamp=sync_timestamp
            )
        
        else:
            # Reprocess existing files
            log.info(f"Reprocessing {len(existing_file_ids)} existing files in knowledge base {kb_id}")
            
            results = []
            for file_id in existing_file_ids:
                sync_result = await self.sync_file(file_id, request, user_id)
                results.append(sync_result)
            
            # Convert to batch result format
            batch_result = self._convert_sync_results_to_batch(results)
            
            return KnowledgeSyncResult(
                knowledge_base_id=kb_id,
                sync_results=batch_result,
                file_ids_updated=existing_file_ids,
                metadata_updated=False,
                sync_timestamp=sync_timestamp
            )

    def check_duplicate(self, file_hash: str, collection_name: str) -> DuplicateCheckResult:
        """
        Check if a file with the given hash already exists in the vector database.
        
        Args:
            file_hash: SHA256 hash of the file content
            collection_name: Vector database collection name to check
            
        Returns:
            DuplicateCheckResult with duplicate status and details
        """
        if not file_hash or not collection_name:
            return DuplicateCheckResult(
                is_duplicate=False,
                existing_file_ids=[],
                hash_checked=file_hash,
                collection_name=collection_name
            )
        
        try:
            result = VECTOR_DB_CLIENT.query(
                collection_name=collection_name,
                filter={"hash": file_hash},
            )
            
            existing_ids = []
            if result is not None and result.ids and result.ids[0]:
                existing_ids = result.ids[0]
                
            return DuplicateCheckResult(
                is_duplicate=len(existing_ids) > 0,
                existing_file_ids=existing_ids,
                hash_checked=file_hash,
                collection_name=collection_name
            )
            
        except Exception as e:
            log.error(f"Error checking duplicate in vector DB: {e}")
            return DuplicateCheckResult(
                is_duplicate=False,
                existing_file_ids=[],
                hash_checked=file_hash,
                collection_name=collection_name
            )

    # Private helper methods

    async def _get_configured_provider(self, provider_name: str):
        """Get and validate a content source provider."""
        # Check if provider exists
        available_providers = content_source_factory.get_available_providers()
        if provider_name not in available_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown provider: {provider_name}. Available: {', '.join(available_providers.keys())}"
            )
        
        # Get or create provider instance
        provider = content_source_registry.get_provider(provider_name)
        if not provider:
            provider = content_source_factory.get_provider(provider_name)
            content_source_registry.register_provider(provider_name, provider)
        
        # Verify provider is configured
        try:
            service_info = await provider.get_service_info()
            if not service_info.get('configured', False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Provider '{provider_name}' is not configured"
                )
        except Exception as e:
            log.error(f"Failed to check provider configuration: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to check provider configuration: {str(e)}"
            )
        
        return provider

    async def _process_single_provider_file(
        self, 
        provider, 
        provider_name: str, 
        file_info: Dict[str, Any], 
        sync_options: Dict[str, Any],
        user_id: str
    ) -> SyncResult:
        """Process a single file from a content provider with retry logic."""
        try:
            # Download file content with exponential backoff retry
            max_retries = 3
            retry_delay = 1.0  # Initial delay in seconds
            
            content = None
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    content_chunks = []
                    async for chunk in provider.download_file(file_info['id']):
                        content_chunks.append(chunk)
                    content = b''.join(content_chunks)
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        # Exponential backoff: 1s, 2s, 4s
                        delay = retry_delay * (2 ** attempt)
                        log.warning(f"Download failed for {provider_name}/{file_info.get('name', 'unknown')} "
                                  f"(attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                    else:
                        log.error(f"Download failed after {max_retries} attempts for "
                                f"{provider_name}/{file_info.get('name', 'unknown')}: {e}")
                        raise
            
            if content is None:
                raise last_error or Exception("Failed to download file content")
            
            # Create or update file
            file_id, action = await self._create_or_update_file(
                user_id, provider_name, file_info, content, sync_options
            )
            
            if not file_id:
                if action == 'skipped':
                    return SyncResult(
                        file_id=None,
                        action=SyncAction.SKIPPED,
                        error="Binary file skipped - cannot extract text for knowledge base"
                    )
                else:
                    return SyncResult(
                        file_id=None,
                        action=SyncAction.FAILED,
                        error="Failed to create file record"
                    )
            
            
            # Convert action string to enum
            if action == 'created':
                sync_action = SyncAction.CREATED
            elif action == 'updated':
                sync_action = SyncAction.UPDATED
            elif action == 'unchanged':
                sync_action = SyncAction.UNCHANGED
            else:
                sync_action = SyncAction.FAILED
                
            return SyncResult(
                file_id=file_id,
                action=sync_action,
                metadata={
                    'provider': provider_name,
                    'provider_file_id': file_info['id'],
                    'name': file_info.get('name', 'unknown')
                }
            )
            
        except Exception as e:
            return SyncResult(
                file_id=None,
                action=SyncAction.FAILED,
                error=str(e)
            )

    async def _create_or_update_file(
        self, 
        user_id: str, 
        provider_name: str, 
        file_info: Dict[str, Any], 
        content: bytes,
        sync_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[str], str]:
        """
        Create or update a file with provider metadata using existing file model.
        
        Returns:
            tuple: (file_id, action) where action is 'created', 'updated', or 'unchanged'
        """
        # Generate consistent file ID based on provider and file ID
        base_id = f"{provider_name}_{file_info['id']}"
        file_id = hashlib.sha256(base_id.encode()).hexdigest()[:16]
        
        # Check if file already exists
        existing_file = Files.get_file_by_id(file_id)
        if existing_file:
            # Check if update is needed
            provider_info = existing_file.provider_info
            if provider_info and provider_info.get('provider_modified_time') == file_info.get('modified_time'):
                return existing_file.id, 'unchanged'
                
            # Update file content and metadata
            file_obj = io.BytesIO(content)
            _, file_path = self.storage.upload_file(file_obj, existing_file.filename, {})
            
            # Update file data - only save text content for knowledge base
            try:
                text_content = content.decode("utf-8") if isinstance(content, bytes) else str(content)
            except UnicodeDecodeError:
                # Binary content - try to extract text if it's a PDF
                extracted_text = None
                if file_info and file_info.get('mime_type') == 'application/pdf':
                    extracted_text = self._extract_text_from_pdf(content)
                
                if extracted_text:
                    # Successfully extracted text from PDF
                    text_content = extracted_text
                    log.info(f"Extracted text from PDF for file {file_id}")
                else:
                    # Skip binary files that we can't extract text from
                    log.warning(f"Skipping binary file {file_id} - cannot extract text for knowledge base")
                    return existing_file.id, 'unchanged'  # Don't update with unusable content
            
            updated_data = {
                **existing_file.data,
                "content": text_content
            }
            Files.update_file_data_by_id(file_id, updated_data)
            
            # Calculate and update hash
            content_hash = calculate_sha256_string(text_content)
            Files.update_file_hash_by_id(file_id, content_hash)
            
            # Update provider info
            Files.update_file_provider_info_by_id(
                file_id,
                provider_modified_time=file_info.get('modified_time'),
                provider_metadata=file_info.get('metadata', {})
            )
            
            return file_id, 'updated'
        
        # Create new file
        filename = f"{provider_name}_{file_info['name']}"
        
        # Store file
        file_obj = io.BytesIO(content)
        _, file_path = self.storage.upload_file(file_obj, filename, {})
        
        # Convert content for storage - only save text content for knowledge base
        try:
            text_content = content.decode("utf-8") if isinstance(content, bytes) else str(content)
        except UnicodeDecodeError:
            # Binary content - try to extract text if it's a PDF
            extracted_text = None
            if file_info and file_info.get('mime_type') == 'application/pdf':
                extracted_text = self._extract_text_from_pdf(content)
            
            if extracted_text:
                # Successfully extracted text from PDF
                text_content = extracted_text
                log.info(f"Extracted text from PDF for new file {filename}")
            else:
                # Skip binary files that we can't extract text from
                log.warning(f"Skipping binary file {filename} - cannot extract text for knowledge base")
                return None, 'skipped'  # Don't create file with unusable content
        
        # Determine if sync should be enabled
        enable_sync = sync_options.get('auto_sync', False) if sync_options else False
        
        # Create FileForm with provider fields
        file_form = FileForm(
            id=file_id,
            filename=filename,
            path=file_path,
            data={"content": text_content},
            meta={
                "name": file_info['name'],
                "content_type": file_info.get('mime_type', 'application/octet-stream'),
                "size": len(content)
            },
            provider=provider_name,
            provider_file_id=file_info['id'],
            provider_modified_time=file_info.get('modified_time'),
            provider_sync_enabled=enable_sync,
            provider_metadata=file_info.get('metadata', {})
        )
        
        file_model = Files.insert_new_file(user_id=user_id, form_data=file_form)
        
        # Calculate and update hash immediately after creation
        if file_model:
            content_hash = calculate_sha256_string(text_content)
            Files.update_file_hash_by_id(file_model.id, content_hash)
        
        return (file_model.id, 'created') if file_model else (None, None)

    async def _rollback_files(self, file_ids: List[str]) -> bool:
        """
        Rollback file changes by removing them from the system.
        
        Args:
            file_ids: List of file IDs to rollback
            
        Returns:
            bool: True if rollback was successful, False otherwise
        """
        try:
            log.info(f"Rolling back {len(file_ids)} files")
            
            for file_id in file_ids:
                try:
                    # Remove from vector database
                    collection_name = f"file-{file_id}"
                    if VECTOR_DB_CLIENT.has_collection(collection_name):
                        VECTOR_DB_CLIENT.delete_collection(collection_name)
                    
                    # Remove file record
                    Files.delete_file_by_id(file_id)
                    log.debug(f"Rolled back file {file_id}")
                    
                except Exception as e:
                    log.error(f"Failed to rollback file {file_id}: {e}")
                    # Continue with other files
            
            log.info("Rollback completed")
            return True
            
        except Exception as e:
            log.error(f"Rollback operation failed: {e}")
            return False

    def _combine_batch_results(self, results: List[BatchSyncResult]) -> BatchSyncResult:
        """Combine multiple batch sync results into a single result."""
        combined = BatchSyncResult(
            status=SyncStatus.SUCCESS,
            added_files=[],
            updated_files=[],
            unchanged_files=[],
            removed_files=[],
            duplicate_files=[],
            failed_files=[],
            errors=[],
            warnings=[],
            total_processed=0,
            changes=False
        )
        
        has_failures = False
        has_successes = False
        
        for result in results:
            combined.added_files.extend(result.added_files)
            combined.updated_files.extend(result.updated_files)
            combined.unchanged_files.extend(result.unchanged_files)
            combined.removed_files.extend(result.removed_files)
            combined.duplicate_files.extend(result.duplicate_files)
            combined.failed_files.extend(result.failed_files)
            combined.errors.extend(result.errors)
            combined.warnings.extend(result.warnings)
            combined.total_processed += result.total_processed
            
            if result.changes:
                combined.changes = True
                
            if result.status == SyncStatus.FAILED:
                has_failures = True
            else:
                has_successes = True
        
        # Determine combined status
        if has_failures and has_successes:
            combined.status = SyncStatus.PARTIAL_SUCCESS
        elif has_failures:
            combined.status = SyncStatus.FAILED
        else:
            combined.status = SyncStatus.SUCCESS
        
        return combined

    def _convert_sync_results_to_batch(self, sync_results: List[SyncResult]) -> BatchSyncResult:
        """Convert individual sync results to a batch result format."""
        batch_result = BatchSyncResult(
            status=SyncStatus.SUCCESS,
            added_files=[],
            updated_files=[],
            unchanged_files=[],
            removed_files=[],
            duplicate_files=[],
            failed_files=[],
            errors=[],
            warnings=[],
            total_processed=len(sync_results),
            changes=False
        )
        
        has_failures = False
        
        for result in sync_results:
            if result.action == SyncAction.CREATED:
                batch_result.added_files.append(result.file_id)
                batch_result.changes = True
            elif result.action == SyncAction.UPDATED:
                batch_result.updated_files.append(result.file_id)
                batch_result.changes = True
            elif result.action == SyncAction.UNCHANGED:
                batch_result.unchanged_files.append(result.file_id)
            elif result.action == SyncAction.FAILED:
                batch_result.failed_files.append({
                    'file_id': result.file_id,
                    'name': result.metadata.get('name', 'unknown') if result.metadata else 'unknown',
                    'error': result.error
                })
                batch_result.errors.append({
                    'file': result.metadata.get('name', 'unknown') if result.metadata else 'unknown',
                    'error': result.error
                })
                has_failures = True
            
            if result.warnings:
                batch_result.warnings.extend(result.warnings)
        
        # Set overall status
        if has_failures and (batch_result.added_files or batch_result.updated_files):
            batch_result.status = SyncStatus.PARTIAL_SUCCESS
        elif has_failures:
            batch_result.status = SyncStatus.FAILED
        
        return batch_result

    async def sync_file_from_provider(
        self,
        file_id: str,
        request: Request,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Sync a single file from its configured content source provider.
        
        This method:
        1. Validates the file has provider information
        2. Downloads latest content from the provider
        3. Updates local file if content changed
        4. Re-processes the file for vector database
        
        Args:
            file_id: ID of the file to sync
            request: FastAPI request object
            user_id: ID of the user performing the sync
            
        Returns:
            Dict containing sync result with success status, messages, and metadata
        """
        log.info(f"Starting provider sync for file {file_id}")
        
        # Get the file
        file = Files.get_file_by_id(file_id)
        if not file:
            return {
                "success": False,
                "file_id": file_id,
                "filename": "unknown",
                "message": "File not found",
                "error": "File not found"
            }
        
        # Check if file has provider info
        provider_info = file.provider_info
        if not provider_info or not provider_info.get("provider"):
            return {
                "success": False,
                "file_id": file_id,
                "filename": file.filename,
                "message": "File does not have provider information",
                "error": "No provider configured for this file"
            }
        
        provider_name = provider_info.get("provider")
        provider_file_id = provider_info.get("provider_file_id")
        
        if not provider_file_id:
            return {
                "success": False,
                "file_id": file_id,
                "filename": file.filename,
                "message": "File does not have provider file ID",
                "error": "No provider file ID found"
            }
        
        try:
            # Get the content source provider
            provider = await self._get_configured_provider(provider_name)
            
            # Get file metadata from provider to check if sync needed
            files = await provider.list_files("", recursive=False)
            provider_file = None
            for f in files:
                if f.get("id") == provider_file_id:
                    provider_file = f
                    break
            
            # Check if file needs sync (if we found metadata)
            if provider_file:
                provider_modified_time = provider_file.get("modified_time")
                local_modified_time = provider_info.get("provider_modified_time")
                
                if provider_modified_time == local_modified_time:
                    return {
                        "success": True,
                        "file_id": file_id,
                        "filename": file.filename,
                        "message": "File is already up to date",
                        "updated": False,
                        "content_changed": False,
                        "provider_modified_time": provider_modified_time
                    }
            
            # Download the file content
            content_chunks = []
            async for chunk in provider.download_file(provider_file_id):
                content_chunks.append(chunk)
            
            if not content_chunks:
                return {
                    "success": False,
                    "file_id": file_id,
                    "filename": file.filename,
                    "message": "No content received from provider",
                    "error": "Empty file download"
                }
            
            # Combine chunks
            new_content = b''.join(content_chunks)
            
            # Save the new content to storage
            user = type('User', (), {
                'id': user_id,
                'email': f'user_{user_id}@example.com',
                'name': f'User {user_id}'
            })()
            
            tags = {
                "OpenWebUI-User-Email": user.email,
                "OpenWebUI-User-Id": user.id,
                "OpenWebUI-User-Name": user.name,
                "OpenWebUI-File-Id": file_id,
            }
            
            # Upload the new content (this will overwrite the existing file)
            filename = f"{file_id}_{file.filename}"
            try:
                _, file_path = Storage.upload_file(
                    file=io.BytesIO(new_content),
                    filename=filename,
                    tags=tags
                )
            except Exception as e:
                log.error(f"Failed to upload synced file to storage: {e}")
                return {
                    "success": False,
                    "file_id": file_id,
                    "filename": file.filename,
                    "message": "Failed to save synced content",
                    "error": str(e)
                }
            
            # Update file metadata with new provider info
            updated_provider_info = {
                "provider": provider_name,
                "provider_file_id": provider_file_id,
                "provider_modified_time": provider_file.get("modified_time") if provider_file else None,
                "provider_sync_enabled": provider_info.get("provider_sync_enabled", False),
                "provider_metadata": provider_file.get("metadata") if provider_file else provider_info.get("provider_metadata")
            }
            
            # Update the file's provider info
            updated_file = Files.update_file_provider_info_by_id(
                id=file_id,
                **updated_provider_info
            )
            
            if not updated_file:
                log.warning(f"Failed to update file provider info for file {file_id}")
            
            # Re-process the file to update embeddings
            content_changed = False
            try:
                # Process the file with new content
                process_file(
                    request,
                    ProcessFileForm(file_id=file_id),
                    user=user
                )
                content_changed = True
            except Exception as e:
                log.error(f"Error processing synced file: {e}")
                # Don't fail the sync if processing fails
                content_changed = False
            
            return {
                "success": True,
                "file_id": file_id,
                "filename": file.filename,
                "message": "File synced successfully",
                "updated": True,
                "content_changed": content_changed,
                "provider_modified_time": updated_provider_info.get("provider_modified_time")
            }
        
        except Exception as e:
            log.exception(f"Error syncing file {file_id}: {e}")
            return {
                "success": False,
                "file_id": file_id,
                "filename": file.filename,
                "message": "Failed to sync file",
                "error": str(e)
            }

    async def sync_files_by_provider_batch(
        self,
        provider_name: str,
        force_sync: bool,
        user_id: str,
        user_role: str,
        request: Request,
        permission_check_fn=None
    ) -> Dict[str, Any]:
        """
        Sync all files from a specific provider in batch.
        
        Args:
            provider_name: Name of the provider to sync files from
            force_sync: Whether to force sync even if sync is disabled
            user_id: ID of the user performing the sync
            user_role: Role of the user (admin, user, etc.)
            request: FastAPI request object
            permission_check_fn: Optional function to check file permissions
            
        Returns:
            Dict containing batch sync results
        """
        log.info(f"Starting batch sync for provider {provider_name}")
        
        try:
            # Validate provider exists
            provider = content_source_factory.get_provider(provider_name)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid provider: {str(e)}"
            )
        
        # Get all files from this provider
        if user_role == "admin":
            files = Files.get_files_by_provider(provider_name)
        else:
            files = Files.get_files_by_provider(provider_name, user_id=user_id)
        
        # Track results
        results = []
        errors = []
        synced_count = 0
        failed_count = 0
        skipped_count = 0
        
        for file in files:
            # Check if file has sync enabled (unless force sync)
            if not force_sync and not file.provider_sync_enabled:
                skipped_count += 1
                results.append({
                    "success": True,
                    "file_id": file.id,
                    "filename": file.filename,
                    "message": "Sync not enabled for this file",
                    "updated": False
                })
                continue
            
            # Check permissions for each file if permission function provided
            if permission_check_fn and not permission_check_fn(file.id, user_id, user_role):
                skipped_count += 1
                results.append({
                    "success": False,
                    "file_id": file.id,
                    "filename": file.filename,
                    "message": "No permission to sync this file",
                    "error": "Unauthorized"
                })
                continue
            
            # Sync the file
            try:
                sync_result = await self.sync_file_from_provider(file.id, request, user_id)
                results.append(sync_result)
                
                if sync_result["success"]:
                    if sync_result.get("updated", False):
                        synced_count += 1
                    else:
                        skipped_count += 1
                else:
                    failed_count += 1
                    if sync_result.get("error"):
                        errors.append(f"File {file.filename}: {sync_result['error']}")
            except Exception as e:
                failed_count += 1
                error_msg = f"Failed to sync file {file.filename}: {str(e)}"
                errors.append(error_msg)
                results.append({
                    "success": False,
                    "file_id": file.id,
                    "filename": file.filename,
                    "message": "Sync failed",
                    "error": str(e)
                })
        
        return {
            "success": failed_count == 0,
            "provider": provider_name,
            "total_files": len(files),
            "synced_files": synced_count,
            "failed_files": failed_count,
            "skipped_files": skipped_count,
            "results": results,
            "errors": errors
        }


# Global service instance
content_syncer = ContentSourceSyncer()