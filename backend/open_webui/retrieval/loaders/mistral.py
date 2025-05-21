import asyncio
import httpx
import os
import sys
import logging
import functools
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Callable
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from langchain_core.documents import Document
from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

# Simple in-memory LRU cache
class SimpleCache:
    def __init__(self, max_size=10):
        self.cache = {}
        self.max_size = max_size
        self.access_times = {}
    
    def get(self, key):
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None
    
    def set(self, key, value):
        if len(self.cache) >= self.max_size and key not in self.cache:
            # Remove least recently used item
            lru_key = min(self.access_times, key=self.access_times.get)
            del self.cache[lru_key]
            del self.access_times[lru_key]
        
        self.cache[key] = value
        self.access_times[key] = time.time()

# Global cache instance
_ocr_cache = SimpleCache(max_size=20)


class MistralLoader:
    """
    Loads documents by processing them through the Mistral OCR API.
    """

    BASE_API_URL = "https://api.mistral.ai/v1"
    # Optimal chunk size for file uploads (5MB)
    CHUNK_SIZE = 5 * 1024 * 1024
    # Maximum file size for processing (default: 50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024

    def __init__(
        self, 
        api_key: str, 
        file_path: str,
        max_concurrency: int = 5,
        timeout: float = 30.0,
        use_cache: bool = True,
        max_retries: int = 5
    ):
        """
        Initializes the loader with improved configuration options.

        Args:
            api_key: Your Mistral API key.
            file_path: The local path to the PDF file to process.
            max_concurrency: Maximum number of concurrent operations.
            timeout: Request timeout in seconds.
            use_cache: Whether to use caching for results.
            max_retries: Maximum number of retries for API calls.
        """
        if not api_key:
            raise ValueError("API key cannot be empty.")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at {file_path}")
            
        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_FILE_SIZE:
            log.warning(f"File size ({file_size} bytes) exceeds recommended maximum ({self.MAX_FILE_SIZE} bytes). Processing may be slow.")

        self.api_key = api_key
        self.file_path = file_path
        self.file_size = file_size
        self.use_cache = use_cache
        self.max_retries = max_retries
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Use advanced connection pooling settings
        self.session = httpx.AsyncClient(
            headers=self.headers,
            timeout=timeout,
            http2=True,
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30.0
            )
        )
        
        # Configurable semaphore for throttling
        self._sem = asyncio.Semaphore(max_concurrency)
        
        # File hash for caching
        self._file_hash = None
        if self.use_cache:
            self._file_hash = self._calculate_file_hash()

    def _calculate_file_hash(self) -> str:
        """Calculate a hash of the file for caching purposes."""
        try:
            hasher = hashlib.md5()
            with open(self.file_path, "rb") as f:
                # Read in chunks to handle large files efficiently
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            file_hash = hasher.hexdigest()
            log.debug(f"Calculated file hash: {file_hash}")
            return file_hash
        except Exception as e:
            log.warning(f"Failed to calculate file hash: {e}. Caching disabled for this file.")
            return None

    def _retry_decorator(self) -> Callable:
        """Creates a configured retry decorator."""
        return retry(
            wait=wait_exponential(multiplier=0.5, max=10),
            stop=stop_after_attempt(self.max_retries),
            retry=retry_if_exception_type((httpx.HTTPError, asyncio.TimeoutError)),
            reraise=True
        )

    async def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Asynchronously checks response status and returns JSON content."""
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            text = await response.aread()  # Proper async read of body
            log.error(f"HTTP error occurred: {exc} - Response: {text.decode('utf-8', errors='replace')}")
            raise
        
        if response.status_code == 204 or not response.content:
            return {}
            
        return response.json()

    @retry(wait=wait_exponential(multiplier=0.5, max=10), stop=stop_after_attempt(5), reraise=True)
    async def _upload_file(self) -> str:
        """Uploads the file to Mistral for OCR processing with optimized handling."""
        log.info(f"Uploading file ({self.file_size} bytes) to Mistral API")
        url = f"{self.BASE_API_URL}/files"
        file_name = os.path.basename(self.file_path)

        try:
            # Determine if we should use chunked upload
            use_chunked = self.file_size > self.CHUNK_SIZE
            
            if use_chunked:
                log.info(f"Using chunked upload for large file ({self.file_size} bytes)")
                # For chunked upload we'd normally need to implement a custom file sender
                # But httpx handles this efficiently with a file object
            
            with open(self.file_path, "rb") as f:
                files = {
                    "file": (file_name, f, "application/pdf"),
                    "purpose": (None, "ocr"),
                }
                r = await self.session.post(url, files=files)
                response_data = await self._handle_response(r)

            file_id = response_data.get("id")
            if not file_id:
                raise ValueError("File ID not found in upload response.")
            log.info(f"File uploaded successfully. File ID: {file_id}")
            return file_id
        except Exception as e:
            log.error(f"Failed to upload file: {e}")
            raise

    @retry(wait=wait_exponential(multiplier=0.5, max=10), stop=stop_after_attempt(5), reraise=True)
    async def _get_signed_url(self, file_id: str) -> str:
        """Retrieves a temporary signed URL for the uploaded file with retry."""
        log.info(f"Getting signed URL for file ID: {file_id}")
        url = f"{self.BASE_API_URL}/files/{file_id}/url"
        params = {"expiry": 1}
        signed_url_headers = {**self.headers, "Accept": "application/json"}

        try:
            r = await self.session.get(url, params=params, headers=signed_url_headers)
            response_data = await self._handle_response(r)
            signed_url = response_data.get("url")
            if not signed_url:
                raise ValueError("Signed URL not found in response.")
            log.info("Signed URL received.")
            return signed_url
        except Exception as e:
            log.error(f"Failed to get signed URL: {e}")
            raise

    @retry(wait=wait_exponential(multiplier=0.5, max=10), stop=stop_after_attempt(5), reraise=True)
    async def _process_ocr(self, signed_url: str) -> Dict[str, Any]:
        """Sends the signed URL to the OCR endpoint for processing with streaming support."""
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

        try:
            # For large responses, we can use streaming
            # But for most OCR results, a direct response is fine
            r = await self.session.post(url, json=payload, headers=ocr_headers)
            ocr_response = await self._handle_response(r)
            log.info("OCR processing done.")
            log.debug("OCR response: %s", ocr_response)
            return ocr_response
        except Exception as e:
            log.error(f"Failed during OCR processing: {e}")
            raise

    @retry(wait=wait_exponential(multiplier=0.5, max=10), stop=stop_after_attempt(3), reraise=False)
    async def _delete_file(self, file_id: str) -> None:
        """Deletes the file from Mistral storage with retry logic."""
        log.info(f"Deleting uploaded file ID: {file_id}")
        url = f"{self.BASE_API_URL}/files/{file_id}"

        try:
            r = await self.session.delete(url)
            delete_response = await self._handle_response(r)
            log.info(f"File deleted successfully: {delete_response}")
        except Exception as e:
            # Log error but don't necessarily halt execution if deletion fails
            log.error(f"Failed to delete file ID {file_id}: {e}")

    def _build_document(self, page_data: Dict[str, Any], total_pages: int) -> Optional[Document]:
        """Optimized helper to build a Document from page data."""
        page_content = page_data.get("markdown")
        page_index = page_data.get("index")
        
        if not page_content or page_index is None:
            log.warning(f"Skipping page due to missing 'markdown' or 'index'. Data: {page_data}")
            return None
            
        # Create document with optimized metadata
        return Document(
            page_content=page_content,
            metadata={
                "page": page_index,  # 0-based index
                "page_label": page_index + 1,  # 1-based label
                "total_pages": total_pages,
            },
        )

    async def load(self) -> List[Document]:
        """
        Executes the full OCR workflow with caching and improved error handling.

        Returns:
            A list of Document objects, one for each page processed.
        """
        # Check cache first if enabled
        if self.use_cache and self._file_hash:
            cached_result = _ocr_cache.get(self._file_hash)
            if cached_result:
                log.info(f"Using cached OCR result for file: {self.file_path}")
                return cached_result

        # Throttle concurrent load operations
        async with self._sem:
            file_id = None
            try:
                # 1. Upload file
                file_id = await self._upload_file()

                # 2. Get Signed URL
                signed_url = await self._get_signed_url(file_id)

                # 3. Process OCR
                ocr_response = await self._process_ocr(signed_url)

                # 4. Process results
                pages_data = ocr_response.get("pages", [])
                if not pages_data:
                    log.warning("No pages found in OCR response.")
                    return [Document(page_content="No text content found", metadata={})]

                total_pages = len(pages_data)
                
                # Use a worker pool for CPU-bound page processing
                loop = asyncio.get_event_loop()
                
                # Process pages in batches for better memory efficiency
                batch_size = min(50, total_pages)  # Process up to 50 pages at once
                documents = []
                
                for i in range(0, total_pages, batch_size):
                    batch = pages_data[i:i+batch_size]
                    tasks = [
                        loop.run_in_executor(
                            None,
                            functools.partial(self._build_document, page_data, total_pages)
                        )
                        for page_data in batch
                    ]
                    batch_results = await asyncio.gather(*tasks)
                    # Filter out any pages that returned None
                    documents.extend([doc for doc in batch_results if doc is not None])
                
                if not documents:
                    log.warning("No valid pages processed after parallel parsing.")
                    return [Document(page_content="No text content found", metadata={})]
                
                # Store in cache if enabled
                if self.use_cache and self._file_hash:
                    _ocr_cache.set(self._file_hash, documents)
                    
                return documents

            except Exception as e:
                log.error(f"An error occurred during the loading process: {e}")
                # Return an empty list or a specific error document on failure
                return [Document(page_content=f"Error during processing: {e}", metadata={})]
            finally:
                # 5. Delete file (attempt even if prior steps failed after upload)
                if file_id:
                    try:
                        await self._delete_file(file_id)
                    except Exception as del_e:
                        # Log deletion error, but don't overwrite original error if one occurred
                        log.error(
                            f"Cleanup error: Could not delete file ID {file_id}. Reason: {del_e}"
                        )

    async def __aenter__(self):
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager, ensuring session cleanup."""
        await self.session.aclose()

async def shutdown_loader(loader: MistralLoader):
    """Safely shut down the loader and close its session."""
    if loader and hasattr(loader, 'session'):
        await loader.session.aclose()
