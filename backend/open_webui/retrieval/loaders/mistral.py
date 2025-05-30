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

        # Pre-compute file info for performance
        self.file_name = os.path.basename(file_path)
        self.file_size = os.path.getsize(file_path)

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "OpenWebUI-MistralLoader/2.0",
        }

    def _debug_log(self, message: str, *args) -> None:
        """Conditional debug logging for performance."""
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

    def _retry_request_sync(self, request_func, *args, **kwargs):
        """Synchronous retry logic with exponential backoff."""
        for attempt in range(self.max_retries):
            try:
                return request_func(*args, **kwargs)
            except (requests.exceptions.RequestException, Exception) as e:
                if attempt == self.max_retries - 1:
                    raise

                wait_time = (2**attempt) + 0.5
                log.warning(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)

    async def _retry_request_async(self, request_func, *args, **kwargs):
        """Async retry logic with exponential backoff."""
        for attempt in range(self.max_retries):
            try:
                return await request_func(*args, **kwargs)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == self.max_retries - 1:
                    raise

                wait_time = (2**attempt) + 0.5
                log.warning(
                    f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)

    def _upload_file(self) -> str:
        """Uploads the file to Mistral for OCR processing (sync version)."""
        log.info("Uploading file to Mistral API")
        url = f"{self.BASE_API_URL}/files"
        file_name = os.path.basename(self.file_path)

        def upload_request():
            with open(self.file_path, "rb") as f:
                files = {"file": (file_name, f, "application/pdf")}
                data = {"purpose": "ocr"}

                response = requests.post(
                    url,
                    headers=self.headers,
                    files=files,
                    data=data,
                    timeout=self.timeout,
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
                timeout=aiohttp.ClientTimeout(total=self.timeout),
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
                url, headers=signed_url_headers, params=params, timeout=self.timeout
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
                timeout=aiohttp.ClientTimeout(total=self.timeout),
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
                url, headers=ocr_headers, json=payload, timeout=self.timeout
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
                timeout=aiohttp.ClientTimeout(total=self.timeout),
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
            response = requests.delete(url, headers=self.headers, timeout=30)
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
                        total=30
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
            limit=10,  # Total connection limit
            limit_per_host=5,  # Per-host connection limit
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
        )

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={"User-Agent": "OpenWebUI-MistralLoader/2.0"},
        ) as session:
            yield session

    def _process_results(self, ocr_response: Dict[str, Any]) -> List[Document]:
        """Process OCR results into Document objects with enhanced metadata."""
        pages_data = ocr_response.get("pages")
        if not pages_data:
            log.warning("No pages found in OCR response.")
            return [
                Document(
                    page_content="No text content found", metadata={"error": "no_pages"}
                )
            ]

        documents = []
        total_pages = len(pages_data)
        skipped_pages = 0

        for page_data in pages_data:
            page_content = page_data.get("markdown")
            page_index = page_data.get("index")  # API uses 0-based index

            if page_content is not None and page_index is not None:
                # Clean up content efficiently
                cleaned_content = (
                    page_content.strip()
                    if isinstance(page_content, str)
                    else str(page_content)
                )

                if cleaned_content:  # Only add non-empty pages
                    documents.append(
                        Document(
                            page_content=cleaned_content,
                            metadata={
                                "page": page_index,  # 0-based index from API
                                "page_label": page_index
                                + 1,  # 1-based label for convenience
                                "total_pages": total_pages,
                                "file_name": self.file_name,
                                "file_size": self.file_size,
                                "processing_engine": "mistral-ocr",
                            },
                        )
                    )
                else:
                    skipped_pages += 1
                    self._debug_log(f"Skipping empty page {page_index}")
            else:
                skipped_pages += 1
                self._debug_log(
                    f"Skipping page due to missing 'markdown' or 'index'. Data: {page_data}"
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
                    metadata={"error": "no_valid_pages", "total_pages": total_pages},
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
    ) -> List[List[Document]]:
        """
        Process multiple files concurrently for maximum performance.

        Args:
            loaders: List of MistralLoader instances

        Returns:
            List of document lists, one for each loader
        """
        if not loaders:
            return []

        log.info(f"Starting concurrent processing of {len(loaders)} files")
        start_time = time.time()

        # Process all files concurrently
        tasks = [loader.load_async() for loader in loaders]
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

        total_time = time.time() - start_time
        total_docs = sum(len(docs) for docs in processed_results)
        log.info(
            f"Batch processing completed in {total_time:.2f}s, produced {total_docs} total documents"
        )

        return processed_results
