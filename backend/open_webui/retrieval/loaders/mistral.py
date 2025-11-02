import requests
import aiohttp
import asyncio
import logging
import os
import sys
import time
import base64
from typing import List, Dict, Any
from contextlib import asynccontextmanager
import re

import aiofiles

from langchain_core.documents import Document
from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

DEFAULT_MISTRAL_OCR_MODEL = "mistral-ocr-latest"
DEFAULT_MISTRAL_OCR_ENDPOINT = "https://api.mistral.ai/v1"

# Connection pool configuration constants
DEFAULT_CONNECTION_LIMIT = 20
DEFAULT_PER_HOST_LIMIT = 10
DEFAULT_DNS_CACHE_TTL = 600  # 10 minutes
DEFAULT_KEEPALIVE_TIMEOUT = 60
DEFAULT_CONNECT_TIMEOUT = 30
DEFAULT_SOCK_READ_TIMEOUT = 60

# Memory optimization threshold for chunked encoding
CHUNKED_ENCODING_THRESHOLD = 10 * 1024 * 1024  # 10MB
ENCODING_CHUNK_SIZE = 8192 * 1024  # 8MB chunks


# ============================================================================
# MISTRAL LOADER CLASS
# ============================================================================

class MistralLoader:
    """
    Universal OCR loader with both sync and async support.
    Loads documents by processing them through OCR APIs (primarily Mistral OCR API).
    
    Supports two processing workflows:
    1. Base64 encoding (default): Encodes PDF to base64 and sends directly to OCR endpoint
    2. Upload workflow: Uploads file, gets signed URL, processes OCR, then deletes file

    Performance Optimizations:
    - Async file I/O (non-blocking)
    - CPU-intensive encoding offloaded to thread pool (base64 workflow)
    - Streaming file upload for better memory efficiency (upload workflow)
    - Intelligent retry logic with exponential backoff
    - Dynamic timeout calculation based on file size
    - Connection pooling and keepalive optimization
    - Semaphore-based concurrency control for batch processing
    - Enhanced error handling with retryable error classification
    """

    # ============================================================================
    # INITIALIZATION
    # ============================================================================

    def __init__(
        self,
        api_key: str,
        file_path: str,
        base_url: str = DEFAULT_MISTRAL_OCR_ENDPOINT,
        model: str = DEFAULT_MISTRAL_OCR_MODEL,
        timeout: int = 300,  # 5 minutes default
        max_retries: int = 3,
        enable_debug_logging: bool = False,
        use_base64: bool = True,  # If True, use base64 encoding method; if False, use upload workflow
    ):
        """
        Initializes the loader with validation and optimization.

        Args:
            api_key: Your API key for the OCR service.
            file_path: The local path to the PDF file to process.
            base_url: Base URL for the API endpoint.
            model: Model name to use for OCR processing.
            timeout: Request timeout in seconds (overridden by dynamic calculation).
            max_retries: Maximum number of retry attempts.
            enable_debug_logging: Enable detailed debug logs.
            use_base64: If True, use base64 encoding method. If False, use upload + signed URL workflow.

        Raises:
            ValueError: If API key is empty.
            FileNotFoundError: If file doesn't exist.
        """
        if not api_key:
            raise ValueError("API key cannot be empty.")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at {file_path}")

        self.api_key = api_key
        self.file_path = file_path
        
        # Fallback to default values if base_url or model are empty or whitespace
        self.base_url = (base_url.strip() if base_url and base_url.strip() else DEFAULT_MISTRAL_OCR_ENDPOINT).rstrip('/')
        self.model = model.strip() if model and model.strip() else DEFAULT_MISTRAL_OCR_MODEL
        self.max_retries = max_retries
        self.debug = enable_debug_logging
        self.use_base64 = use_base64  # Store the workflow choice

        # Pre-compute file info to avoid repeated filesystem calls
        # Single file stat call to get all file metadata
        file_stat = os.stat(file_path)
        self.file_name = os.path.basename(file_path)
        self.file_size = file_stat.st_size
        self.file_mtime = file_stat.st_mtime  # Useful for caching/debugging

        # PERFORMANCE OPTIMIZATION: Dynamic timeout based on file size
        # Estimate: 1 second per MB + 60s base processing time
        # This ensures large files don't timeout prematurely
        file_size_mb = self.file_size / (1024 * 1024)
        estimated_time = 60 + int(file_size_mb * 1)
        self.timeout = max(min(estimated_time, 600), timeout)  # Between user timeout and 10 min
        self.ocr_timeout = self.timeout
        
        # PERFORMANCE OPTIMIZATION: Differentiated timeouts for upload workflow
        # These are only used when use_base64=False
        self.upload_timeout = min(timeout, 120)  # Cap upload at 2 minutes
        self.url_timeout = 30  # URL requests should be fast
        self.cleanup_timeout = 30  # Cleanup should be quick

        self._debug_log(f"Initialized with timeout: {self.timeout}s for {file_size_mb:.2f}MB file, using {'base64' if self.use_base64 else 'upload'} workflow")

        # Added User-Agent for better API tracking and debugging
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "OpenWebUI-MistralLoader/3.0",
        }

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def _debug_log(self, message: str, *args) -> None:
        """
        PERFORMANCE OPTIMIZATION: Conditional debug logging for performance.

        Only processes debug messages when debug mode is enabled, avoiding
        string formatting overhead in production environments.
        """
        if self.debug:
            log.debug(message, *args)

    def _sanitize_error_response(self, text: str, max_length: int = 500) -> str:
        """Remove sensitive data from error responses before logging."""
        # Truncate long responses
        truncated = text[:max_length] + ("..." if len(text) > max_length else "")
        
        # Redact potential API keys or tokens (basic pattern matching)
        sanitized = re.sub(r'Bearer\s+[A-Za-z0-9\-_\.]+', 'Bearer [REDACTED]', truncated)
        sanitized = re.sub(r'"api_key"\s*:\s*"[^"]+"', '"api_key": "[REDACTED]"', sanitized)
        
        return sanitized

    # ============================================================================
    # HTTP RESPONSE HANDLING
    # ============================================================================

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Checks response status and returns JSON content."""
        try:
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            # Handle potential empty responses for certain successful requests (e.g., DELETE)
            if response.status_code == 204 or not response.content:
                return {}  # Return empty dict if no content
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            safe_response = self._sanitize_error_response(response.text)
            log.error(f"HTTP error occurred: {http_err} - Status: {response.status_code} - Response: {safe_response}")
            raise
        except requests.exceptions.RequestException as req_err:
            log.error(f"Request exception occurred: {req_err}")
            raise
        except ValueError as json_err:  # Includes JSONDecodeError
            safe_response = self._sanitize_error_response(response.text)
            log.error(f"JSON decode error: {json_err} - Response: {safe_response}")
            raise  # Re-raise after logging

    async def _handle_response_async(
        self, response: aiohttp.ClientResponse
    ) -> Dict[str, Any]:
        """Async version of response handling with better error info."""
        try:
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type:
                if response.status == 204:
                    return {}
                text = await response.text()
                safe_text = self._sanitize_error_response(text)
                raise ValueError(
                    f"Unexpected content type: {content_type}, body: {safe_text}"
                )

            return await response.json()

        except aiohttp.ClientResponseError as e:
            error_text = await response.text() if response else "No response"
            safe_response = self._sanitize_error_response(error_text)
            log.error(f"HTTP {e.status}: {e.message} - Response: {safe_response}")
            raise
        except aiohttp.ClientError as e:
            log.error(f"Client error: {e}")
            raise
        except Exception as e:
            log.error(f"Unexpected error processing response: {e}")
            raise

    # ============================================================================
    # RETRY LOGIC AND ERROR CLASSIFICATION
    # ============================================================================

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
            if hasattr(error, "response") and error.response is not None:
                status_code = error.response.status_code
                return status_code >= 500 or status_code == 429
            return False
        if isinstance(
            error, (aiohttp.ClientConnectionError, aiohttp.ServerTimeoutError)
        ):
            return True  # Async network/timeout errors are retryable
        if isinstance(error, aiohttp.ClientResponseError):
            return error.status >= 500 or error.status == 429
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
                    f"Retryable error (attempt {attempt + 1}/{self.max_retries}): {e}. "
                    f"Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)

    async def _retry_request_async(self, request_func, *args, **kwargs):
        """
        ENHANCEMENT: Async retry logic with intelligent error classification.

        Async version of retry logic that doesn't block the event loop during
        wait periods. Uses the same exponential backoff strategy as sync version.
        """
        for attempt in range(self.max_retries):
            try:
                return await request_func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1 or not self._is_retryable_error(e):
                    raise

                # PERFORMANCE OPTIMIZATION: Non-blocking exponential backoff
                wait_time = min((2**attempt) + 0.5, 30)  # Cap at 30 seconds
                log.warning(
                    f"Retryable error (attempt {attempt + 1}/{self.max_retries}): {e}. "
                    f"Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)  # Non-blocking wait

    # ============================================================================
    # FILE ENCODING (BASE64)
    # ============================================================================

    def _encode_file_to_base64(self) -> str:
        """
        Encode PDF file to base64 string (sync version).
        Uses memory-efficient chunked approach for large files.
        
        Returns:
            Base64-encoded string of the PDF file.
            
        Raises:
            MemoryError: If file is too large to encode in available memory.
        """
        try:
            # For files under 10MB, use simple approach
            if self.file_size < CHUNKED_ENCODING_THRESHOLD:
                with open(self.file_path, "rb") as f:
                    return base64.b64encode(f.read()).decode('utf-8')
            
            # For larger files, read in chunks but encode once
            # (encoding each chunk separately breaks base64 padding)
            chunks = []
            with open(self.file_path, "rb") as f:
                while True:
                    chunk = f.read(ENCODING_CHUNK_SIZE)
                    if not chunk:
                        break
                    chunks.append(chunk)
            
            # Concatenate all chunks and encode once
            file_data = b''.join(chunks)
            return base64.b64encode(file_data).decode('utf-8')
        except MemoryError as e:
            log.error(f"Insufficient memory to encode file of size {self.file_size:,} bytes")
            raise ValueError(f"File too large to encode in available memory: {e}")

    async def _encode_file_to_base64_async(self) -> str:
        """
        Encode PDF file to base64 string (async version).
        Uses non-blocking file I/O and offloads encoding to thread pool.
        
        Returns:
            Base64-encoded string of the PDF file.
            
        Raises:
            MemoryError: If file is too large to encode in available memory.
        """
        try:
            # For files under 10MB, use simple approach
            if self.file_size < CHUNKED_ENCODING_THRESHOLD:
                async with aiofiles.open(self.file_path, "rb") as f:
                    file_data = await f.read()
                
                # Run CPU-intensive encoding in thread pool to avoid blocking event loop
                return await asyncio.to_thread(
                    lambda: base64.b64encode(file_data).decode('utf-8')
                )
            
            # For larger files, read in chunks but encode once
            # (encoding each chunk separately breaks base64 padding)
            async with aiofiles.open(self.file_path, "rb") as f:
                chunks = []
                while True:
                    chunk = await f.read(ENCODING_CHUNK_SIZE)
                    if not chunk:
                        break
                    chunks.append(chunk)
            
            # Concatenate all chunks and encode once
            file_data = b''.join(chunks)
            return await asyncio.to_thread(
                lambda: base64.b64encode(file_data).decode('utf-8')
            )
        except MemoryError as e:
            log.error(f"Insufficient memory to encode file of size {self.file_size:,} bytes")
            raise ValueError(f"File too large to encode in available memory: {e}")

    # ============================================================================
    # FILE UPLOAD WORKFLOW
    # ============================================================================

    def _upload_file(self) -> str:
        """
        PERFORMANCE OPTIMIZATION: Enhanced file upload with streaming consideration.

        Uploads the file to Mistral for OCR processing (sync version).
        Uses context manager for file handling to ensure proper resource cleanup.
        Although streaming is not enabled for this endpoint, the file is opened
        in a context manager to minimize memory usage duration.
        
        Returns:
            File ID from the upload response.
            
        Raises:
            ValueError: If file ID not found in response.
        """
        log.info("Uploading file to Mistral API")
        url = f"{self.base_url}/files"

        def upload_request():
            # MEMORY OPTIMIZATION: Use context manager to minimize file handle lifetime
            # This ensures the file is closed immediately after reading, reducing memory usage
            with open(self.file_path, "rb") as f:
                files = {"file": (self.file_name, f, "application/pdf")}
                data = {"purpose": "ocr"}

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
            file_id = response_data.get("id")
            if not file_id:
                raise ValueError("File ID not found in upload response.")
            log.info(f"File uploaded successfully. File ID: {file_id}")
            return file_id
        except Exception as e:
            log.error(f"Failed to upload file: {e}")
            raise

    async def _upload_file_async(self, session: aiohttp.ClientSession) -> str:
        """
        Async file upload with streaming for better memory efficiency.
        
        Returns:
            File ID from the upload response.
            
        Raises:
            ValueError: If file ID not found in response.
        """
        url = f"{self.base_url}/files"

        async def upload_request():
            # Create multipart writer for streaming upload
            writer = aiohttp.MultipartWriter("form-data")

            # Add purpose field
            purpose_part = writer.append("ocr")
            purpose_part.set_content_disposition("form-data", name="purpose")

            # Add file part with streaming
            file_part = writer.append_payload(
                aiohttp.streams.FilePayload(
                    self.file_path,
                    filename=self.file_name,
                    content_type="application/pdf",
                )
            )
            file_part.set_content_disposition(
                "form-data", name="file", filename=self.file_name
            )

            self._debug_log(
                f"Uploading file: {self.file_name} ({self.file_size:,} bytes)"
            )

            async with session.post(
                url,
                data=writer,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=self.upload_timeout),
            ) as response:
                return await self._handle_response_async(response)

        response_data = await self._retry_request_async(upload_request)

        file_id = response_data.get("id")
        if not file_id:
            raise ValueError("File ID not found in upload response.")

        log.info(f"File uploaded successfully. File ID: {file_id}")
        return file_id

    def _get_signed_url(self, file_id: str) -> str:
        """
        Retrieves a temporary signed URL for the uploaded file (sync version).
        
        Args:
            file_id: The ID of the uploaded file.
            
        Returns:
            Signed URL for accessing the file.
            
        Raises:
            ValueError: If signed URL not found in response.
        """
        log.info(f"Getting signed URL for file ID: {file_id}")
        url = f"{self.base_url}/files/{file_id}/url"
        params = {"expiry": 1}
        signed_url_headers = {**self.headers, "Accept": "application/json"}

        def url_request():
            response = requests.get(
                url, headers=signed_url_headers, params=params, timeout=self.url_timeout
            )
            return self._handle_response(response)

        try:
            response_data = self._retry_request_sync(url_request)
            signed_url = response_data.get("url")
            if not signed_url:
                raise ValueError("Signed URL not found in response.")
            log.info("Signed URL received.")
            return signed_url
        except Exception as e:
            log.error(f"Failed to get signed URL: {e}")
            raise

    async def _get_signed_url_async(
        self, session: aiohttp.ClientSession, file_id: str
    ) -> str:
        """
        Async signed URL retrieval.
        
        Args:
            session: aiohttp client session.
            file_id: The ID of the uploaded file.
            
        Returns:
            Signed URL for accessing the file.
            
        Raises:
            ValueError: If signed URL not found in response.
        """
        url = f"{self.base_url}/files/{file_id}/url"
        params = {"expiry": 1}

        headers = {**self.headers, "Accept": "application/json"}

        async def url_request():
            self._debug_log(f"Getting signed URL for file ID: {file_id}")
            async with session.get(
                url,
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=self.url_timeout),
            ) as response:
                return await self._handle_response_async(response)

        response_data = await self._retry_request_async(url_request)

        signed_url = response_data.get("url")
        if not signed_url:
            raise ValueError("Signed URL not found in response.")

        self._debug_log("Signed URL received successfully")
        return signed_url

    def _process_ocr_with_url(self, signed_url: str) -> Dict[str, Any]:
        """
        Process OCR using signed URL from uploaded file (sync version).
        
        Args:
            signed_url: Signed URL pointing to the uploaded file.
            
        Returns:
            OCR response dictionary containing pages with markdown content.
        """
        log.info("Processing OCR via Mistral API using signed URL")
        url = f"{self.base_url}/ocr"
        ocr_headers = {
            **self.headers,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "model": self.model,
            "document": {
                "type": "document_url",
                "document_url": signed_url,
            },
            "include_image_base64": False,
        }

        def ocr_request():
            response = requests.post(
                url, headers=ocr_headers, json=payload, timeout=self.ocr_timeout
            )
            return self._handle_response(response)

        try:
            ocr_response = self._retry_request_sync(ocr_request)
            log.info("OCR processing completed")
            self._debug_log("OCR response: %s", ocr_response)
            return ocr_response
        except Exception as e:
            log.error(f"Failed during OCR processing: {e}")
            raise

    async def _process_ocr_with_url_async(
        self, session: aiohttp.ClientSession, signed_url: str
    ) -> Dict[str, Any]:
        """
        Process OCR using signed URL from uploaded file (async version).
        
        Args:
            session: aiohttp client session.
            signed_url: Signed URL pointing to the uploaded file.
            
        Returns:
            OCR response dictionary containing pages with markdown content.
        """
        url = f"{self.base_url}/ocr"

        headers = {
            **self.headers,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "model": self.model,
            "document": {
                "type": "document_url",
                "document_url": signed_url,
            },
            "include_image_base64": False,
        }

        async def ocr_request():
            log.info("Starting OCR processing via Mistral API (upload method)")
            start_time = time.time()

            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.ocr_timeout),
            ) as response:
                ocr_response = await self._handle_response_async(response)

            processing_time = time.time() - start_time
            log.info(f"OCR processing completed in {processing_time:.2f}s")

            return ocr_response

        return await self._retry_request_async(ocr_request)

    def _delete_file(self, file_id: str) -> None:
        """
        Deletes the file from Mistral storage (sync version).
        
        Args:
            file_id: The ID of the file to delete.
        """
        log.info(f"Deleting uploaded file ID: {file_id}")
        url = f"{self.base_url}/files/{file_id}"

        try:
            response = requests.delete(
                url, headers=self.headers, timeout=self.cleanup_timeout
            )
            delete_response = self._handle_response(response)
            log.info(f"File deleted successfully: {delete_response}")
        except Exception as e:
            # Log error but don't necessarily halt execution if deletion fails
            log.error(f"Failed to delete file ID {file_id}: {e}")

    async def _delete_file_async(
        self, session: aiohttp.ClientSession, file_id: str
    ) -> None:
        """
        Async file deletion with error tolerance.
        
        Args:
            session: aiohttp client session.
            file_id: The ID of the file to delete.
        """
        try:

            async def delete_request():
                self._debug_log(f"Deleting file ID: {file_id}")
                async with session.delete(
                    url=f"{self.base_url}/files/{file_id}",
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(
                        total=self.cleanup_timeout
                    ),  # Shorter timeout for cleanup
                ) as response:
                    return await self._handle_response_async(response)

            await self._retry_request_async(delete_request)
            self._debug_log(f"File {file_id} deleted successfully")

        except Exception as e:
            # Don't fail the entire process if cleanup fails
            log.warning(f"Failed to delete file ID {file_id}: {e}")

    # ============================================================================
    # OCR PROCESSING
    # ============================================================================

    def _process_ocr(self, base64_pdf: str) -> Dict[str, Any]:
        """
        Process OCR using base64 encoded PDF (sync version).
        
        Args:
            base64_pdf: Base64-encoded PDF string.
            
        Returns:
            OCR response dictionary containing pages with markdown content.
        """
        log.info("Processing OCR via Mistral API using base64 encoded PDF")
        url = f"{self.base_url}/ocr"
        ocr_headers = {
            **self.headers,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "model": self.model,
            "document": {
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{base64_pdf}",
            },
            "include_image_base64": False,
        }

        def ocr_request():
            response = requests.post(
                url, headers=ocr_headers, json=payload, timeout=self.ocr_timeout
            )
            return self._handle_response(response)

        try:
            ocr_response = self._retry_request_sync(ocr_request)
            log.info("OCR processing completed")
            self._debug_log("OCR response: %s", ocr_response)
            return ocr_response
        except Exception as e:
            log.error(f"Failed during OCR processing: {e}")
            raise

    async def _process_ocr_async(
        self, session: aiohttp.ClientSession, base64_pdf: str
    ) -> Dict[str, Any]:
        """
        Process OCR using base64 encoded PDF (async version).
        
        Args:
            session: aiohttp client session.
            base64_pdf: Base64-encoded PDF string.
            
        Returns:
            OCR response dictionary containing pages with markdown content.
        """
        url = f"{self.base_url}/ocr"

        headers = {
            **self.headers,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "model": self.model,
            "document": {
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{base64_pdf}",
            },
            "include_image_base64": False,
        }

        async def ocr_request():
            log.info("Starting OCR processing via Mistral API (base64 method)")
            start_time = time.time()

            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.ocr_timeout),
            ) as response:
                ocr_response = await self._handle_response_async(response)

            processing_time = time.time() - start_time
            log.info(f"OCR processing completed in {processing_time:.2f}s")

            return ocr_response

        return await self._retry_request_async(ocr_request)

    # ============================================================================
    # SESSION MANAGEMENT
    # ============================================================================

    @asynccontextmanager
    async def _get_session(self):
        """Context manager for HTTP session with optimized settings."""
        connector = aiohttp.TCPConnector(
            limit=DEFAULT_CONNECTION_LIMIT,
            limit_per_host=DEFAULT_PER_HOST_LIMIT,
            ttl_dns_cache=DEFAULT_DNS_CACHE_TTL,
            use_dns_cache=True,
            keepalive_timeout=DEFAULT_KEEPALIVE_TIMEOUT,
            enable_cleanup_closed=True,
            force_close=False,  # Allow connection reuse
            resolver=aiohttp.AsyncResolver(),  # Use async DNS resolver
        )

        timeout = aiohttp.ClientTimeout(
            total=self.timeout,
            connect=DEFAULT_CONNECT_TIMEOUT,
            sock_read=DEFAULT_SOCK_READ_TIMEOUT,
        )

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": "OpenWebUI-MistralLoader/2.0"},
            raise_for_status=False,  # We handle status codes manually
            trust_env=True,
        ) as session:
            yield session

    # ============================================================================
    # RESULT PROCESSING
    # ============================================================================

    def _create_error_document(self, error_msg: str, processing_time: float = 0) -> List[Document]:
        """
        Creates a standardized error document for consistent error reporting.
        
        Args:
            error_msg: The error message to include
            processing_time: Time spent processing before error occurred
            
        Returns:
            List containing a single error Document
        """
        return [
            Document(
                page_content=f"Error during OCR processing: {error_msg}",
                metadata={
                    "error": "processing_failed",
                    "file_name": self.file_name,
                    "file_size": self.file_size,
                    "processing_time": processing_time,
                },
            )
        ]

    def _process_results(self, ocr_response: Dict[str, Any]) -> List[Document]:
        """Process OCR results into Document objects with enhanced metadata and memory efficiency."""
        # Validate response structure
        if not isinstance(ocr_response, dict):
            log.error(f"Invalid OCR response type: expected dict, got {type(ocr_response)}")
            return [
                Document(
                    page_content="Invalid API response format",
                    metadata={"error": "invalid_response_type", "file_name": self.file_name}
                )
            ]
        
        pages_data = ocr_response.get("pages")
        if not pages_data:
            log.warning("No pages found in OCR response.")
            return [
                Document(
                    page_content="No text content found",
                    metadata={"error": "no_pages", "file_name": self.file_name},
                )
            ]

        # Validate pages_data is a list
        if not isinstance(pages_data, list):
            log.error(f"Invalid pages format: expected list, got {type(pages_data)}")
            return [
                Document(
                    page_content="Invalid pages format in API response",
                    metadata={"error": "invalid_pages_format", "file_name": self.file_name}
                )
            ]

        documents = []
        total_pages = len(pages_data)
        skipped_pages = 0

        # Process pages in a memory-efficient way
        for page_data in pages_data:
            page_content = page_data.get("markdown")
            page_index = page_data.get("index")  # API uses 0-based index

            if page_content is None or page_index is None:
                skipped_pages += 1
                self._debug_log(
                    f"Skipping page due to missing 'markdown' or 'index'. Data keys: {list(page_data.keys())}"
                )
                continue

            # Clean up content efficiently with early exit for empty content
            if isinstance(page_content, str):
                cleaned_content = page_content.strip()
            else:
                cleaned_content = str(page_content).strip()

            if not cleaned_content:
                skipped_pages += 1
                self._debug_log(f"Skipping empty page {page_index}")
                continue

            # Create document with optimized metadata
            documents.append(
                Document(
                    page_content=cleaned_content,
                    metadata={
                        "page": page_index,  # 0-based index from API
                        "page_label": page_index + 1,  # 1-based label for convenience
                        "total_pages": total_pages,
                        "file_name": self.file_name,
                        "file_size": self.file_size,
                        "processing_engine": "mistral-ocr",
                        "content_length": len(cleaned_content),
                    },
                )
            )

        if skipped_pages > 0:
            log.info(
                f"Processed {len(documents)} pages, skipped {skipped_pages} empty/invalid pages"
            )

        if not documents:
            # Case where pages existed but none had valid markdown/index
            log.warning(
                "OCR response contained pages, but none had valid content/index."
            )
            return [
                Document(
                    page_content="No valid text content found in document",
                    metadata={
                        "error": "no_valid_pages",
                        "total_pages": total_pages,
                        "file_name": self.file_name,
                    },
                )
            ]

        return documents

    # ============================================================================
    # MAIN ENTRY POINTS - SYNC
    # ============================================================================

    def load(self) -> List[Document]:
        """
        Executes the OCR workflow based on the selected method (base64 or upload).

        Returns:
            A list of Document objects, one for each page processed.
            Returns error document if processing fails.
        """
        start_time = time.time()
        file_id = None

        try:
            if self.use_base64:
                # Base64 workflow
                log.info("Using base64 encoding workflow")
                
                # Encode PDF to base64
                base64_pdf = self._encode_file_to_base64()
                
                # Process OCR
                ocr_response = self._process_ocr(base64_pdf)
            else:
                # Upload workflow
                log.info("Using upload + signed URL workflow")
                
                # 1. Upload file
                file_id = self._upload_file()

                # 2. Get Signed URL
                signed_url = self._get_signed_url(file_id)

                # 3. Process OCR
                ocr_response = self._process_ocr_with_url(signed_url)
            
            # Process results (common for both workflows)
            documents = self._process_results(ocr_response)

            total_time = time.time() - start_time
            log.info(
                f"OCR workflow completed in {total_time:.2f}s, produced {len(documents)} documents"
            )

            return documents

        except Exception as e:
            total_time = time.time() - start_time
            log.error(f"OCR workflow failed after {total_time:.2f}s: {e}")
            return self._create_error_document(str(e), total_time)
        finally:
            # Cleanup - only needed for upload workflow
            if not self.use_base64 and file_id:
                try:
                    self._delete_file(file_id)
                except Exception as cleanup_error:
                    log.error(f"Cleanup failed for file ID {file_id}: {cleanup_error}")

    # ============================================================================
    # MAIN ENTRY POINTS - ASYNC
    # ============================================================================

    async def load_async(self) -> List[Document]:
        """
        Asynchronous OCR workflow based on the selected method (base64 or upload).

        Returns:
            A list of Document objects, one for each page processed.
            Returns error document if processing fails.
        """
        start_time = time.time()
        file_id = None

        try:
            async with self._get_session() as session:
                if self.use_base64:
                    # Base64 workflow
                    log.info("Using base64 encoding workflow (async)")
                    
                    # Encode PDF to base64 (non-blocking)
                    base64_pdf = await self._encode_file_to_base64_async()
                    
                    # Process OCR
                    ocr_response = await self._process_ocr_async(session, base64_pdf)
                else:
                    # Upload workflow
                    log.info("Using upload + signed URL workflow (async)")
                    
                    # 1. Upload file with streaming
                    file_id = await self._upload_file_async(session)

                    # 2. Get signed URL
                    signed_url = await self._get_signed_url_async(session, file_id)

                    # 3. Process OCR
                    ocr_response = await self._process_ocr_with_url_async(session, signed_url)
                
                # Process results (common for both workflows)
                documents = self._process_results(ocr_response)

            total_time = time.time() - start_time
            log.info(
                f"Async OCR workflow completed in {total_time:.2f}s, produced {len(documents)} documents"
            )

            return documents

        except Exception as e:
            total_time = time.time() - start_time
            log.error(f"Async OCR workflow failed after {total_time:.2f}s: {e}")
            return self._create_error_document(str(e), total_time)
        finally:
            # Cleanup - only needed for upload workflow
            if not self.use_base64 and file_id:
                try:
                    async with self._get_session() as session:
                        await self._delete_file_async(session, file_id)
                except Exception as cleanup_error:
                    log.error(f"Cleanup failed for file ID {file_id}: {cleanup_error}")

    # ============================================================================
    # BATCH PROCESSING - ASYNC
    # ============================================================================

    @staticmethod
    async def load_multiple_async(
        loaders: List["MistralLoader"],
        max_concurrent: int = 5,  # Limit concurrent requests
    ) -> List[List[Document]]:
        """
        Process multiple files concurrently with controlled concurrency.

        Args:
            loaders: List of MistralLoader instances
            max_concurrent: Maximum number of concurrent requests

        Returns:
            List of document lists, one for each loader
            
        Raises:
            ValueError: If loaders list is empty or max_concurrent < 1
        """
        if not loaders:
            return []

        if max_concurrent < 1:
            raise ValueError(f"max_concurrent must be >= 1, got {max_concurrent}")

        # Ensure semaphore doesn't exceed number of loaders
        effective_concurrent = min(max_concurrent, len(loaders))
        semaphore = asyncio.Semaphore(effective_concurrent)

        log.info(
            f"Starting concurrent processing of {len(loaders)} files with "
            f"max {effective_concurrent} concurrent"
        )
        start_time = time.time()

        # Use semaphore to control concurrency
        async def process_with_semaphore(
            index: int, loader: "MistralLoader"
        ) -> tuple:
            """Process with index to maintain order in error reporting."""
            async with semaphore:
                try:
                    result = await loader.load_async()
                    return (index, result)
                except Exception as e:
                    log.error(f"File {index} ({loader.file_name}) failed: {e}")
                    return (index, [
                        Document(
                            page_content=f"Error processing file: {e}",
                            metadata={
                                "error": "batch_processing_failed",
                                "file_index": index,
                                "file_name": loader.file_name,
                            },
                        )
                    ])

        # Process with index tracking
        tasks = [process_with_semaphore(i, loader) for i, loader in enumerate(loaders)]
        indexed_results = await asyncio.gather(*tasks, return_exceptions=False)

        # Sort by index to maintain input order
        indexed_results.sort(key=lambda x: x[0])
        results = [result for _, result in indexed_results]

        # MONITORING: Log comprehensive batch processing statistics
        total_time = time.time() - start_time
        total_docs = sum(len(docs) for docs in results)
        
        # Count successes vs failures based on error metadata
        success_count = sum(
            1 for docs in results 
            if not any(doc.metadata.get("error") == "batch_processing_failed" for doc in docs)
        )
        failure_count = len(results) - success_count

        log.info(
            f"Batch processing completed in {total_time:.2f}s: "
            f"{success_count} files succeeded, {failure_count} files failed, "
            f"produced {total_docs} total documents"
        )

        return results
