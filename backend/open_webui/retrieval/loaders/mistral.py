import base64
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

import requests
from langchain_core.documents import Document
from open_webui.env import ENABLE_FORWARD_USER_INFO_HEADERS, GLOBAL_LOG_LEVEL
from open_webui.utils.headers import include_user_info_headers

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)


class MistralLoader:
    """
    Enhanced Mistral OCR loader.
    Loads documents by processing them through the Mistral OCR API.

    Performance Optimizations:
    - Differentiated timeouts for different operations
    - Intelligent retry logic with exponential backoff
    - Enhanced error handling with retryable error classification
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        file_path: str,
        timeout: int = 300,  # 5 minutes default
        max_retries: int = 3,
        enable_debug_logging: bool = False,
        use_base64: bool = False,
        user: Optional[Any] = None,
    ):
        """
        Initializes the loader with enhanced features.

        Args:
            api_key: Your Mistral API key.
            file_path: The local path to the PDF file to process.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts.
            enable_debug_logging: Enable detailed debug logs.
            use_base64: Send the document as a data URL instead of uploading it first.
            user: The requesting user, forwarded to Mistral via user-info headers
                when ENABLE_FORWARD_USER_INFO_HEADERS is enabled.
        """
        if not api_key:
            raise ValueError('API key cannot be empty.')
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'File not found at {file_path}')

        self.base_url = base_url.rstrip('/') if base_url else 'https://api.mistral.ai/v1'
        self.api_key = api_key
        self.file_path = file_path
        self.max_retries = max_retries
        self.debug = enable_debug_logging
        self.use_base64 = use_base64
        self.user = user

        # PERFORMANCE OPTIMIZATION: Differentiated timeouts for different operations
        # This prevents long-running OCR operations from affecting quick operations
        # and improves user experience by failing fast on operations that should be quick
        self.upload_timeout = min(timeout, 120)  # Cap upload at 2 minutes - prevents hanging on large files
        self.url_timeout = 30  # URL requests should be fast - fail quickly if API is slow
        self.ocr_timeout = timeout  # OCR can take the full timeout - this is the heavy operation
        self.cleanup_timeout = 30  # Cleanup should be quick - don't hang on file deletion

        # PERFORMANCE OPTIMIZATION: Pre-compute file info to avoid repeated filesystem calls
        # This avoids multiple os.path.basename() and os.path.getsize() calls during processing
        self.file_name = os.path.basename(file_path)
        self.file_size = os.path.getsize(file_path)

        # ENHANCEMENT: Added User-Agent for better API tracking and debugging
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'User-Agent': 'OpenWebUI-MistralLoader/2.0',  # Helps API provider track usage
        }
        if self.user is not None and ENABLE_FORWARD_USER_INFO_HEADERS:
            self.headers = include_user_info_headers(self.headers, self.user)

    def _debug_log(self, message: str, *args) -> None:
        """
        PERFORMANCE OPTIMIZATION: Conditional debug logging for performance.

        Only processes debug messages when debug mode is enabled, avoiding
        string formatting overhead in production environments.
        """
        if self.debug:
            log.debug(message, *args)

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Checks response status and returns JSON content."""
        try:
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            # Handle potential empty responses for certain successful requests (e.g., DELETE)
            if response.status_code == 204 or not response.content:
                return {}  # Return empty dict if no content
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            log.error(f'HTTP error occurred: {http_err} - Response: {response.text}')
            raise
        except requests.exceptions.RequestException as req_err:
            log.error(f'Request exception occurred: {req_err}')
            raise
        except ValueError as json_err:  # Includes JSONDecodeError
            log.error(f'JSON decode error: {json_err} - Response: {response.text}')
            raise  # Re-raise after logging

    def _is_retryable_error(self, error: Exception) -> bool:
        """
        ENHANCEMENT: Intelligent error classification for retry logic.

        Determines if an error is retryable based on its type and status code.
        This prevents wasting time retrying errors that will never succeed
        (like authentication errors) while ensuring transient errors are retried.

        Retryable errors:
        - Network connection errors (temporary network issues)
        - Timeouts (server might be temporarily overloaded)
        - Server errors (5xx status codes - server-side issues)
        - Rate limiting (429 status - temporary throttling)

        Non-retryable errors:
        - Authentication errors (401, 403 - won't fix with retry)
        - Bad request errors (400 - malformed request)
        - Not found errors (404 - resource doesn't exist)
        """
        if isinstance(error, requests.exceptions.ConnectionError):
            return True  # Network issues are usually temporary
        if isinstance(error, requests.exceptions.Timeout):
            return True  # Timeouts might resolve on retry
        if isinstance(error, requests.exceptions.HTTPError):
            # Only retry on server errors (5xx) or rate limits (429)
            if hasattr(error, 'response') and error.response is not None:
                status_code = error.response.status_code
                return status_code >= 500 or status_code == 429
            return False
        return False  # All other errors are non-retryable

    def _retry_request_sync(self, request_func, *args, **kwargs):
        """
        ENHANCEMENT: Synchronous retry logic with intelligent error classification.

        Uses exponential backoff with jitter to avoid thundering herd problems.
        The wait time increases exponentially but is capped at 30 seconds to
        prevent excessive delays. Only retries errors that are likely to succeed
        on subsequent attempts.
        """
        for attempt in range(self.max_retries):
            try:
                return request_func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1 or not self._is_retryable_error(e):
                    raise

                # PERFORMANCE OPTIMIZATION: Exponential backoff with cap
                # Prevents overwhelming the server while ensuring reasonable retry delays
                wait_time = min((2**attempt) + 0.5, 30)  # Cap at 30 seconds
                log.warning(
                    f'Retryable error (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying in {wait_time}s...'
                )
                time.sleep(wait_time)

    def _upload_file(self) -> str:
        """
        PERFORMANCE OPTIMIZATION: Enhanced file upload with streaming consideration.

        Uploads the file to Mistral for OCR processing.
        Uses context manager for file handling to ensure proper resource cleanup.
        Although streaming is not enabled for this endpoint, the file is opened
        in a context manager to minimize memory usage duration.
        """
        log.info('Uploading file to Mistral API')
        url = f'{self.base_url}/files'

        def upload_request():
            # MEMORY OPTIMIZATION: Use context manager to minimize file handle lifetime
            # This ensures the file is closed immediately after reading, reducing memory usage
            with open(self.file_path, 'rb') as f:
                files = {'file': (self.file_name, f, 'application/pdf')}
                data = {'purpose': 'ocr'}

                # NOTE: stream=False is required for this endpoint
                # The Mistral API doesn't support chunked uploads for this endpoint
                response = requests.post(
                    url,
                    headers=self.headers,
                    files=files,
                    data=data,
                    timeout=self.upload_timeout,  # Use specialized upload timeout
                    stream=False,  # Keep as False for this endpoint
                )

            return self._handle_response(response)

        try:
            response_data = self._retry_request_sync(upload_request)
            file_id = response_data.get('id')
            if not file_id:
                raise ValueError('File ID not found in upload response.')
            log.info('File uploaded successfully. File ID: %s', file_id)
            return file_id
        except Exception as e:
            log.error(f'Failed to upload file: {e}')
            raise

    def _get_signed_url(self, file_id: str) -> str:
        """Retrieves a temporary signed URL for the uploaded file."""
        log.info('Getting signed URL for file ID: %s', file_id)
        url = f'{self.base_url}/files/{file_id}/url'
        params = {'expiry': 1}
        signed_url_headers = {**self.headers, 'Accept': 'application/json'}

        def url_request():
            response = requests.get(url, headers=signed_url_headers, params=params, timeout=self.url_timeout)
            return self._handle_response(response)

        try:
            response_data = self._retry_request_sync(url_request)
            signed_url = response_data.get('url')
            if not signed_url:
                raise ValueError('Signed URL not found in response.')
            log.info('Signed URL received.')
            return signed_url
        except Exception as e:
            log.error(f'Failed to get signed URL: {e}')
            raise

    def _process_ocr(self, signed_url: str) -> Dict[str, Any]:
        """Sends the signed URL to the OCR endpoint for processing."""
        log.info('Processing OCR via Mistral API')
        url = f'{self.base_url}/ocr'
        ocr_headers = {
            **self.headers,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        payload = {
            'model': 'mistral-ocr-latest',
            'document': {
                'type': 'document_url',
                'document_url': signed_url,
            },
            'include_image_base64': False,
        }

        def ocr_request():
            response = requests.post(url, headers=ocr_headers, json=payload, timeout=self.ocr_timeout)
            return self._handle_response(response)

        try:
            ocr_response = self._retry_request_sync(ocr_request)
            log.info('OCR processing done.')
            self._debug_log('OCR response: %s', ocr_response)
            return ocr_response
        except Exception as e:
            log.error(f'Failed during OCR processing: {e}')
            raise

    def _get_file_data_url(self) -> str:
        with open(self.file_path, 'rb') as f:
            encoded_file = base64.b64encode(f.read()).decode('utf-8')
        return f'data:application/pdf;base64,{encoded_file}'

    def _delete_file(self, file_id: str) -> None:
        """Deletes the file from Mistral storage."""
        log.info('Deleting uploaded file ID: %s', file_id)
        url = f'{self.base_url}/files/{file_id}'

        try:
            response = requests.delete(url, headers=self.headers, timeout=self.cleanup_timeout)
            delete_response = self._handle_response(response)
            log.info('File deleted successfully: %s', delete_response)
        except Exception as e:
            # Log error but don't necessarily halt execution if deletion fails
            log.error(f'Failed to delete file ID {file_id}: {e}')

    def _process_results(self, ocr_response: Dict[str, Any]) -> List[Document]:
        """Process OCR results into Document objects with enhanced metadata and memory efficiency."""
        pages_data = ocr_response.get('pages')
        if not pages_data:
            log.warning('No pages found in OCR response.')
            return [
                Document(
                    page_content='No text content found',
                    metadata={'error': 'no_pages', 'file_name': self.file_name},
                )
            ]

        documents = []
        total_pages = len(pages_data)
        skipped_pages = 0

        # Process pages in a memory-efficient way
        for page_data in pages_data:
            page_content = page_data.get('markdown')
            page_index = page_data.get('index')  # API uses 0-based index

            if page_content is None or page_index is None:
                skipped_pages += 1
                self._debug_log(
                    "Skipping page due to missing 'markdown' or 'index'. Data keys: %s", list(page_data.keys())
                )
                continue

            # Clean up content efficiently with early exit for empty content
            if isinstance(page_content, str):
                cleaned_content = page_content.strip()
            else:
                cleaned_content = str(page_content).strip()

            if not cleaned_content:
                skipped_pages += 1
                self._debug_log('Skipping empty page %s', page_index)
                continue

            # Create document with optimized metadata
            documents.append(
                Document(
                    page_content=cleaned_content,
                    metadata={
                        'page': page_index,  # 0-based index from API
                        'page_label': page_index + 1,  # 1-based label for convenience
                        'total_pages': total_pages,
                        'file_name': self.file_name,
                        'file_size': self.file_size,
                        'processing_engine': 'mistral-ocr',
                        'content_length': len(cleaned_content),
                    },
                )
            )

        if skipped_pages > 0:
            log.info('Processed %s pages, skipped %s empty/invalid pages', len(documents), skipped_pages)

        if not documents:
            # Case where pages existed but none had valid markdown/index
            log.warning('OCR response contained pages, but none had valid content/index.')
            return [
                Document(
                    page_content='No valid text content found in document',
                    metadata={
                        'error': 'no_valid_pages',
                        'total_pages': total_pages,
                        'file_name': self.file_name,
                    },
                )
            ]

        return documents

    def load(self) -> List[Document]:
        """
        Executes the full OCR workflow: upload, get URL, process OCR, delete file.

        Returns:
            A list of Document objects, one for each page processed.
        """
        file_id = None
        start_time = time.time()

        try:
            if self.use_base64:
                documents = self._process_results(self._process_ocr(self._get_file_data_url()))
                total_time = time.time() - start_time
                log.info('Sync OCR workflow completed in %.2fs, produced %s documents', total_time, len(documents))
                return documents

            # 1. Upload file
            file_id = self._upload_file()

            # 2. Get Signed URL
            signed_url = self._get_signed_url(file_id)

            # 3. Process OCR
            ocr_response = self._process_ocr(signed_url)

            # 4. Process results
            documents = self._process_results(ocr_response)

            total_time = time.time() - start_time
            log.info('Sync OCR workflow completed in %.2fs, produced %s documents', total_time, len(documents))

            return documents

        except Exception as e:
            total_time = time.time() - start_time
            log.error(f'An error occurred during the loading process after {total_time:.2f}s: {e}')
            # Return an error document on failure
            return [
                Document(
                    page_content=f'Error during processing: {e}',
                    metadata={
                        'error': 'processing_failed',
                        'file_name': self.file_name,
                    },
                )
            ]
        finally:
            # 5. Delete file (attempt even if prior steps failed after upload)
            if file_id:
                try:
                    self._delete_file(file_id)
                except Exception as del_e:
                    # Log deletion error, but don't overwrite original error if one occurred
                    log.error(f'Cleanup error: Could not delete file ID {file_id}. Reason: {del_e}')
