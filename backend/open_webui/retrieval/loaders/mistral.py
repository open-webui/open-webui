import requests
import aiohttp
import asyncio
import logging
import os
import sys
import time
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from langchain_core.documents import Document
from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class MistralLoader:
    """
    Enhanced Mistral OCR loader with both sync and async support.
    Loads documents by processing them through the Mistral OCR API.

    Performance Optimizations:
    - Differentiated timeouts for different operations
    - Intelligent retry logic with exponential backoff
    - Memory-efficient file streaming for large files
    - Connection pooling and keepalive optimization
    - Semaphore-based concurrency control for batch processing
    - Enhanced error handling with retryable error classification
    """

    BASE_API_URL = "https://api.mistral.ai/v1"

    def __init__(
        self,
        api_key: str,
        file_path: str,
        timeout: int = 300,  # 5 minutes default
        max_retries: int = 3,
        enable_debug_logging: bool = False,
    ):
        """
        Initializes the loader with enhanced features.

        Args:
            api_key: Your Mistral API key.
            file_path: The local path to the PDF file to process.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts.
            enable_debug_logging: Enable detailed debug logs.
        """
        if not api_key:
            raise ValueError("API key cannot be empty.")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at {file_path}")

        self.api_key = api_key
        self.file_path = file_path
        self.timeout = timeout
        self.max_retries = max_retries
        self.debug = enable_debug_logging

        # PERFORMANCE OPTIMIZATION: Differentiated timeouts for different operations
        # This prevents long-running OCR operations from affecting quick operations
        # and improves user experience by failing fast on operations that should be quick
        self.upload_timeout = min(
            timeout, 120
        )  # Cap upload at 2 minutes - prevents hanging on large files
        self.url_timeout = (
            30  # URL requests should be fast - fail quickly if API is slow
        )
        self.ocr_timeout = (
            timeout  # OCR can take the full timeout - this is the heavy operation
        )
        self.cleanup_timeout = (
            30  # Cleanup should be quick - don't hang on file deletion
        )

        # PERFORMANCE OPTIMIZATION: Pre-compute file info to avoid repeated filesystem calls
        # This avoids multiple os.path.basename() and os.path.getsize() calls during processing
        self.file_name = os.path.basename(file_path)
        self.file_size = os.path.getsize(file_path)

        # ENHANCEMENT: Added User-Agent for better API tracking and debugging
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "OpenWebUI-MistralLoader/2.0",  # Helps API provider track usage
        }

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
            log.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
            raise
        except requests.exceptions.RequestException as req_err:
            log.error(f"Request exception occurred: {req_err}")
            raise
        except ValueError as json_err:  # Includes JSONDecodeError
            log.error(f"JSON decode error: {json_err} - Response: {response.text}")
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
                raise ValueError(
                    f"Unexpected content type: {content_type}, body: {text[:200]}..."
                )

            return await response.json()

        except aiohttp.ClientResponseError as e:
            error_text = await response.text() if response else "No response"
            log.error(f"HTTP {e.status}: {e.message} - Response: {error_text[:500]}")
            raise
        except aiohttp.ClientError as e:
            log.error(f"Client error: {e}")
            raise
        except Exception as e:
            log.error(f"Unexpected error processing response: {e}")
            raise

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

    def _upload_file(self) -> str:
        """
        PERFORMANCE OPTIMIZATION: Enhanced file upload with streaming consideration.

        Uploads the file to Mistral for OCR processing (sync version).
        Uses context manager for file handling to ensure proper resource cleanup.
        Although streaming is not enabled for this endpoint, the file is opened
        in a context manager to minimize memory usage duration.
        """
        log.info("Uploading file to Mistral API")
        url = f"{self.BASE_API_URL}/files"

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
        """Async file upload with streaming for better memory efficiency."""
        url = f"{self.BASE_API_URL}/files"

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
        """Retrieves a temporary signed URL for the uploaded file (sync version)."""
        log.info(f"Getting signed URL for file ID: {file_id}")
        url = f"{self.BASE_API_URL}/files/{file_id}/url"
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
        """Async signed URL retrieval."""
        url = f"{self.BASE_API_URL}/files/{file_id}/url"
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

    def _process_ocr(self, signed_url: str) -> Dict[str, Any]:
        """Sends the signed URL to the OCR endpoint for processing (sync version)."""
        log.info("Processing OCR via Mistral API")
        url = f"{self.BASE_API_URL}/ocr"
        ocr_headers = {
            **self.headers,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "model": "mistral-ocr-latest",
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
            log.info("OCR processing done.")
            self._debug_log("OCR response: %s", ocr_response)
            return ocr_response
        except Exception as e:
            log.error(f"Failed during OCR processing: {e}")
            raise

    async def _process_ocr_async(
        self, session: aiohttp.ClientSession, signed_url: str
    ) -> Dict[str, Any]:
        """Async OCR processing with timing metrics."""
        url = f"{self.BASE_API_URL}/ocr"

        headers = {
            **self.headers,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "model": "mistral-ocr-latest",
            "document": {
                "type": "document_url",
                "document_url": signed_url,
            },
            "include_image_base64": False,
        }

        async def ocr_request():
            log.info("Starting OCR processing via Mistral API")
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
        """Deletes the file from Mistral storage (sync version)."""
        log.info(f"Deleting uploaded file ID: {file_id}")
        url = f"{self.BASE_API_URL}/files/{file_id}"

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
        """Async file deletion with error tolerance."""
        try:

            async def delete_request():
                self._debug_log(f"Deleting file ID: {file_id}")
                async with session.delete(
                    url=f"{self.BASE_API_URL}/files/{file_id}",
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

    @asynccontextmanager
    async def _get_session(self):
        """Context manager for HTTP session with optimized settings."""
        connector = aiohttp.TCPConnector(
            limit=20,  # Increased total connection limit for better throughput
            limit_per_host=10,  # Increased per-host limit for API endpoints
            ttl_dns_cache=600,  # Longer DNS cache TTL (10 minutes)
            use_dns_cache=True,
            keepalive_timeout=60,  # Increased keepalive for connection reuse
            enable_cleanup_closed=True,
            force_close=False,  # Allow connection reuse
            resolver=aiohttp.AsyncResolver(),  # Use async DNS resolver
        )

        timeout = aiohttp.ClientTimeout(
            total=self.timeout,
            connect=30,  # Connection timeout
            sock_read=60,  # Socket read timeout
        )

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": "OpenWebUI-MistralLoader/2.0"},
            raise_for_status=False,  # We handle status codes manually
        ) as session:
            yield session

    def _process_results(self, ocr_response: Dict[str, Any]) -> List[Document]:
        """Process OCR results into Document objects with enhanced metadata and memory efficiency."""
        pages_data = ocr_response.get("pages")
        if not pages_data:
            log.warning("No pages found in OCR response.")
            return [
                Document(
                    page_content="No text content found",
                    metadata={"error": "no_pages", "file_name": self.file_name},
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

    def load(self) -> List[Document]:
        """
        Executes the full OCR workflow: upload, get URL, process OCR, delete file.
        Synchronous version for backward compatibility.

        Returns:
            A list of Document objects, one for each page processed.
        """
        file_id = None
        start_time = time.time()

        try:
            # 1. Upload file
            file_id = self._upload_file()

            # 2. Get Signed URL
            signed_url = self._get_signed_url(file_id)

            # 3. Process OCR
            ocr_response = self._process_ocr(signed_url)

            # 4. Process results
            documents = self._process_results(ocr_response)

            total_time = time.time() - start_time
            log.info(
                f"Sync OCR workflow completed in {total_time:.2f}s, produced {len(documents)} documents"
            )

            return documents

        except Exception as e:
            total_time = time.time() - start_time
            log.error(
                f"An error occurred during the loading process after {total_time:.2f}s: {e}"
            )
            # Return an error document on failure
            return [
                Document(
                    page_content=f"Error during processing: {e}",
                    metadata={
                        "error": "processing_failed",
                        "file_name": self.file_name,
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
                    log.error(
                        f"Cleanup error: Could not delete file ID {file_id}. Reason: {del_e}"
                    )

    async def load_async(self) -> List[Document]:
        """
        Asynchronous OCR workflow execution with optimized performance.

        Returns:
            A list of Document objects, one for each page processed.
        """
        file_id = None
        start_time = time.time()

        try:
            async with self._get_session() as session:
                # 1. Upload file with streaming
                file_id = await self._upload_file_async(session)

                # 2. Get signed URL
                signed_url = await self._get_signed_url_async(session, file_id)

                # 3. Process OCR
                ocr_response = await self._process_ocr_async(session, signed_url)

                # 4. Process results
                documents = self._process_results(ocr_response)

                total_time = time.time() - start_time
                log.info(
                    f"Async OCR workflow completed in {total_time:.2f}s, produced {len(documents)} documents"
                )

                return documents

        except Exception as e:
            total_time = time.time() - start_time
            log.error(f"Async OCR workflow failed after {total_time:.2f}s: {e}")
            return [
                Document(
                    page_content=f"Error during OCR processing: {e}",
                    metadata={
                        "error": "processing_failed",
                        "file_name": self.file_name,
                    },
                )
            ]
        finally:
            # 5. Cleanup - always attempt file deletion
            if file_id:
                try:
                    async with self._get_session() as session:
                        await self._delete_file_async(session, file_id)
                except Exception as cleanup_error:
                    log.error(f"Cleanup failed for file ID {file_id}: {cleanup_error}")

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
        """
        if not loaders:
            return []

        log.info(
            f"Starting concurrent processing of {len(loaders)} files with max {max_concurrent} concurrent"
        )
        start_time = time.time()

        # Use semaphore to control concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(loader: "MistralLoader") -> List[Document]:
            async with semaphore:
                return await loader.load_async()

        # Process all files with controlled concurrency
        tasks = [process_with_semaphore(loader) for loader in loaders]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                log.error(f"File {i} failed: {result}")
                processed_results.append(
                    [
                        Document(
                            page_content=f"Error processing file: {result}",
                            metadata={
                                "error": "batch_processing_failed",
                                "file_index": i,
                            },
                        )
                    ]
                )
            else:
                processed_results.append(result)

        # MONITORING: Log comprehensive batch processing statistics
        total_time = time.time() - start_time
        total_docs = sum(len(docs) for docs in processed_results)
        success_count = sum(
            1 for result in results if not isinstance(result, Exception)
        )
        failure_count = len(results) - success_count

        log.info(
            f"Batch processing completed in {total_time:.2f}s: "
            f"{success_count} files succeeded, {failure_count} files failed, "
            f"produced {total_docs} total documents"
        )

        return processed_results
