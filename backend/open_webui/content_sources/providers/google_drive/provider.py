"""
Google Drive Content Source Provider

Implements the ContentSourceProvider interface for Google Drive integration.
"""

import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import io

from .client import GoogleDriveService
from open_webui.content_sources.base import ContentSourceProvider

logger = logging.getLogger(__name__)


class GoogleDriveProvider(ContentSourceProvider):
    """
    Google Drive content source provider implementation.
    
    Uses the existing GoogleDriveService for API interactions and
    emits hooks for knowledge base integration.
    """
    
    def __init__(self):
        super().__init__()
        self.service = GoogleDriveService()
    
    def refresh_configuration(self) -> None:
        """Refresh the Google Drive service configuration."""
        self.service.refresh_configuration()
        
    async def list_files(self, path: str = "", recursive: bool = True) -> List[Dict[str, Any]]:
        """
        List files in a Google Drive folder.
        
        Args:
            path: The folder ID to list files from
            recursive: Whether to include files from nested folders
            
        Returns:
            List of file metadata dictionaries
        """
        if not self.service.is_configured():
            raise ValueError("Google Drive service is not configured")
            
        # Use the existing service method
        gdrive_files = self.service.list_folder_files(path, include_nested=recursive)
        
        # Convert to our standard format
        files = []
        for gdrive_file in gdrive_files:
            files.append({
                'id': gdrive_file['id'],
                'name': gdrive_file['name'],
                'mime_type': gdrive_file['mimeType'],
                'modified_time': gdrive_file['modifiedTime'],
                'size': gdrive_file.get('size'),
                'path': gdrive_file.get('path', ''),
                'provider': 'google_drive',
                'metadata': gdrive_file  # Keep original metadata
            })
            
        return files
        
    async def download_file(self, file_id: str, chunk_size: int = 1024 * 1024) -> AsyncGenerator[bytes, None]:
        """
        Download a file from Google Drive with chunked streaming.
        
        Args:
            file_id: Google Drive file ID
            chunk_size: Size of chunks to yield (default 1MB)
            
        Yields:
            File content in chunks
        """
        if not self.service.is_configured():
            raise ValueError("Google Drive service is not configured")
            
        try:
            # Use the existing service method to get file info with shared drive support
            file_info = self.service.service.files().get(
                fileId=file_id,
                supportsAllDrives=True
            ).execute()
            
            # Check if it's a Google Workspace file that needs export
            mime_type = file_info.get('mimeType', '')
            file_name = file_info.get('name', 'unknown')
            file_size = int(file_info.get('size', 0))
            
            # Log file info for debugging
            logger.info(f"Downloading file: {file_name} (ID: {file_id}, Type: {mime_type}, Size: {file_size} bytes)")
        except Exception as e:
            logger.error(f"Failed to get file info for {file_id}: {e}")
            raise
        
        # Define export formats for Google Workspace files
        # Prioritize text formats for knowledge base usage - text is searchable, PDF would be base64
        export_formats = {
            'application/vnd.google-apps.document': [
                'text/plain',       # Primary: Plain text for knowledge base search
                'application/pdf'   # Fallback: PDF if text export fails
            ],
            'application/vnd.google-apps.spreadsheet': [
                'text/csv'          # CSV is already a text format
            ],
            'application/vnd.google-apps.presentation': [
                'application/pdf',  # Keep PDF for presentations (no text export available)
                'text/plain'        # Fallback attempt (may not work for all slides)
            ],
        }
        
        if mime_type in export_formats:
            # Google Workspace files need to be exported
            async for chunk in self._download_workspace_file(file_id, file_name, export_formats[mime_type], chunk_size):
                yield chunk
        else:
            # Regular files can be streamed directly
            async for chunk in self._download_regular_file(file_id, file_name, chunk_size):
                yield chunk
    
    async def _download_workspace_file(self, file_id: str, file_name: str, export_mime_types: list, chunk_size: int) -> AsyncGenerator[bytes, None]:
        """
        Download and export a Google Workspace file with streaming.
        
        Args:
            file_id: Google Drive file ID
            file_name: Name of the file for logging
            export_mime_types: List of MIME types to try for export
            chunk_size: Size of chunks to yield
            
        Yields:
            File content in chunks
        """
        from googleapiclient.http import MediaIoBaseDownload
        
        last_error = None
        content_downloaded = False
        
        for export_mime_type in export_mime_types:
            try:
                request = self.service.service.files().export_media(
                    fileId=file_id,
                    mimeType=export_mime_type
                )
                logger.info(f"Attempting to export '{file_name}' (ID: {file_id}) as {export_mime_type}")
                
                # Use a custom IO stream that yields chunks
                class ChunkedDownloadStream:
                    def __init__(self, chunk_size):
                        self.chunks = []
                        self.chunk_size = chunk_size
                        self.position = 0
                        
                    def write(self, data):
                        self.chunks.append(data)
                        return len(data)
                    
                    def read_chunks(self):
                        """Read and yield accumulated chunks."""
                        if self.chunks:
                            data = b''.join(self.chunks)
                            self.chunks = []
                            
                            # Yield data in specified chunk sizes
                            for i in range(0, len(data), self.chunk_size):
                                yield data[i:i + self.chunk_size]
                
                stream = ChunkedDownloadStream(chunk_size)
                downloader = MediaIoBaseDownload(stream, request, chunksize=chunk_size)
                
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        logger.debug(f"Export progress for '{file_name}': {int(status.progress() * 100)}%")
                    
                    # Yield accumulated chunks
                    for chunk in stream.read_chunks():
                        yield chunk
                
                # Yield any remaining data
                for chunk in stream.read_chunks():
                    yield chunk
                
                logger.info(f"Successfully exported '{file_name}' as {export_mime_type}")
                content_downloaded = True
                break
                
            except Exception as e:
                last_error = e
                # Check if it's a size limit error
                if hasattr(e, 'resp') and e.resp.status == 403:
                    error_content = e.content.decode('utf-8') if hasattr(e, 'content') else str(e)
                    if 'exportSizeLimitExceeded' in error_content:
                        logger.warning(f"File '{file_name}' too large for {export_mime_type} export (limit ~10MB), trying next format...")
                        continue
                # For other errors, log but try next format
                logger.warning(f"Failed to export '{file_name}' as {export_mime_type}: {e}")
                
        if not content_downloaded:
            # All formats failed
            error_msg = f"Failed to export '{file_name}' in any format"
            if last_error:
                error_msg += f": {last_error}"
            raise ValueError(error_msg)
    
    async def _download_regular_file(self, file_id: str, file_name: str, chunk_size: int) -> AsyncGenerator[bytes, None]:
        """
        Download a regular (non-Workspace) file from Google Drive with streaming.
        
        Args:
            file_id: Google Drive file ID
            file_name: Name of the file for logging
            chunk_size: Size of chunks to yield
            
        Yields:
            File content in chunks
        """
        from googleapiclient.http import MediaIoBaseDownload
        
        request = self.service.service.files().get_media(fileId=file_id)
        
        # Use chunked download for memory efficiency
        class ChunkedDownloadStream:
            def __init__(self, chunk_size):
                self.buffer = bytearray()
                self.chunk_size = chunk_size
                
            def write(self, data):
                self.buffer.extend(data)
                return len(data)
            
            def read_chunks(self):
                """Read and yield accumulated chunks."""
                while len(self.buffer) >= self.chunk_size:
                    chunk = bytes(self.buffer[:self.chunk_size])
                    del self.buffer[:self.chunk_size]
                    yield chunk
            
            def read_remaining(self):
                """Read any remaining data."""
                if self.buffer:
                    yield bytes(self.buffer)
                    self.buffer.clear()
        
        stream = ChunkedDownloadStream(chunk_size)
        downloader = MediaIoBaseDownload(stream, request, chunksize=chunk_size)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                logger.debug(f"Download progress for '{file_name}': {int(status.progress() * 100)}%")
            
            # Yield accumulated chunks
            for chunk in stream.read_chunks():
                yield chunk
        
        # Yield any remaining data
        for chunk in stream.read_remaining():
            yield chunk
        
        logger.info(f"Successfully downloaded '{file_name}' (ID: {file_id})")
        
    async def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the Google Drive service.
        
        Returns:
            Dictionary with service information
        """
        if not self.service.is_configured():
            return {
                'configured': False,
                'error': 'Google Drive service is not configured'
            }
            
        email = self.service.get_service_account_email()
        
        return {
            'configured': True,
            'provider': 'google_drive',
            'service_account_email': email,
            'scopes': ['https://www.googleapis.com/auth/drive.readonly']
        }
        
    async def sync_folder_with_metadata(
        self, 
        folder_id: str, 
        existing_files: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Sync a Google Drive folder with change detection.
        
        This method extends the base sync_folder to handle:
        - Change detection based on modification times
        - File updates and removals
        - Progress tracking
        
        Args:
            folder_id: Google Drive folder ID
            existing_files: Map of Google Drive file IDs to local file metadata
            context: Optional context to pass through hooks
        """
        context = context or {}
        
        # Emit sync started event
        await self.emit_hook('sync_started', {
            'folder_id': folder_id,
            'context': context
        })
        
        try:
            # List files in the folder
            gdrive_files = await self.list_files(folder_id, recursive=context.get('include_nested', True))
            
            logger.info(f"Google Drive sync: Found {len(gdrive_files)} files in folder {folder_id}")
            
            # Track files to process
            gdrive_file_ids = set()
            files_to_process = []
            
            for file_info in gdrive_files:
                gdrive_id = file_info['id']
                gdrive_file_ids.add(gdrive_id)
                
                # Check if file exists and needs updating
                if gdrive_id in existing_files:
                    existing_file = existing_files[gdrive_id]
                    local_modified = existing_file.get('modified_time')
                    gdrive_modified = file_info['modified_time']
                    
                    if local_modified != gdrive_modified:
                        # File was modified, mark for update
                        await self.emit_hook('file_updated', {
                            'file_info': file_info,
                            'old_file': existing_file,
                            'context': context
                        })
                        files_to_process.append(file_info)
                    else:
                        # File is up to date
                        await self.emit_hook('file_unchanged', {
                            'file_info': file_info,
                            'context': context
                        })
                else:
                    # New file
                    await self.emit_hook('file_new', {
                        'file_info': file_info,
                        'context': context
                    })
                    files_to_process.append(file_info)
                    
            # Identify removed files
            existing_gdrive_ids = set(existing_files.keys())
            removed_file_ids = existing_gdrive_ids - gdrive_file_ids
            
            for removed_id in removed_file_ids:
                await self.emit_hook('file_removed', {
                    'file_id': removed_id,
                    'file_info': existing_files[removed_id],
                    'context': context
                })
                
            # Process new and updated files
            for i, file_info in enumerate(files_to_process):
                try:
                    # Emit progress
                    await self.emit_hook('sync_progress', {
                        'current': i + 1,
                        'total': len(files_to_process),
                        'file_name': file_info['name'],
                        'context': context
                    })
                    
                    # Skip Google Workspace files that can't be processed
                    mime_type = file_info['mime_type']
                    if mime_type in [
                        'application/vnd.google-apps.site',
                        'application/vnd.google-apps.form',
                        'application/vnd.google-apps.map',
                        'application/vnd.google-apps.drawing'
                    ]:
                        logger.warning(f"Skipping unsupported Google Workspace file: {file_info['name']}")
                        await self.emit_hook('file_skipped', {
                            'file_info': file_info,
                            'reason': 'Unsupported Google Workspace file type',
                            'context': context
                        })
                        continue
                        
                    # Download file content
                    content_chunks = []
                    async for chunk in self.download_file(file_info['id']):
                        content_chunks.append(chunk)
                    content = b''.join(content_chunks)
                    
                    original_mime = file_info.get('mime_type', '')
                    if original_mime == 'application/vnd.google-apps.document':
                        # Google Docs are exported as text for knowledge base
                        file_info['mime_type'] = 'text/plain'
                        file_info['export_format'] = 'text'
                    elif original_mime == 'application/vnd.google-apps.spreadsheet':
                        # Sheets are exported as CSV
                        file_info['mime_type'] = 'text/csv'
                        file_info['export_format'] = 'csv'
                    elif original_mime == 'application/vnd.google-apps.presentation':
                        # Presentations are still exported as PDF (no text export available)
                        file_info['mime_type'] = 'application/pdf'
                        file_info['export_format'] = 'pdf'
                    
                    # Log content info for debugging
                    logger.info(f"Downloaded {file_info['name']}: {len(content)} bytes, original_mime: {original_mime}, final_mime: {file_info.get('mime_type', 'unknown')}")
                    
                    # Skip if content is empty
                    if not content:
                        logger.warning(f"File {file_info['name']} has no content, skipping")
                        await self.emit_hook('file_skipped', {
                            'file_info': file_info,
                            'reason': 'Empty content',
                            'context': context
                        })
                        continue

                    # Emit file ready event
                    await self.emit_hook('file_ready', {
                        'file_info': file_info,
                        'content': content,
                        'context': context
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing file {file_info['name']}: {e}")
                    await self.emit_hook('file_error', {
                        'file_info': file_info,
                        'error': str(e),
                        'context': context
                    })
                    
            # Emit sync completed event
            await self.emit_hook('sync_completed', {
                'folder_id': folder_id,
                'total_files': len(gdrive_files),
                'processed_files': len(files_to_process),
                'removed_files': len(removed_file_ids),
                'context': context
            })
            
        except Exception as e:
            logger.error(f"Error during sync: {e}")
            await self.emit_hook('sync_error', {
                'folder_id': folder_id,
                'error': str(e),
                'context': context
            })
            raise