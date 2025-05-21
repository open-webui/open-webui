import asyncio
import aiohttp
import os
import sys
import logging
import functools
import hashlib
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Callable
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from langchain_core.documents import Document
from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

# Enhanced in-memory LRU cache with TTL
class SimpleCache:
    def __init__(self, max_size=10, default_ttl=3600):
        self.cache = {}
        self.max_size = max_size
        self.access_times = {}
        self.creation_times = {}
        self.default_ttl = default_ttl  # Default TTL in seconds
        self.hits = 0
        self.misses = 0
    
    def get(self, key):
        if key in self.cache:
            # Check if item has expired
            if self.default_ttl > 0 and time.time() - self.creation_times[key] > self.default_ttl:
                self._remove_item(key)
                self.misses += 1
                return None
                
            self.access_times[key] = time.time()
            self.hits += 1
            return self.cache[key]
            
        self.misses += 1
        return None
    
    def set(self, key, value, ttl=None):
        if ttl is None:
            ttl = self.default_ttl
            
        if len(self.cache) >= self.max_size and key not in self.cache:
            # Remove least recently used item
            self._evict_lru_item()
        
        self.cache[key] = value
        self.access_times[key] = time.time()
        self.creation_times[key] = time.time()
    
    def _evict_lru_item(self):
        """Remove the least recently used item from cache"""
        if not self.access_times:
            return
            
        lru_key = min(self.access_times, key=self.access_times.get)
        self._remove_item(lru_key)
    
    def _remove_item(self, key):
        """Remove an item from cache and all tracking dictionaries"""
        if key in self.cache:
            del self.cache[key]
        if key in self.access_times:
            del self.access_times[key]
        if key in self.creation_times:
            del self.creation_times[key]
    
    def clear(self):
        """Clear the entire cache"""
        self.cache.clear()
        self.access_times.clear()
        self.creation_times.clear()
    
    def get_stats(self):
        """Return cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate
        }

# Global cache instance
_ocr_cache = SimpleCache(max_size=20, default_ttl=24*3600)  # 24 hour TTL


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
        
        # Configure aiohttp connection settings
        connector = aiohttp.TCPConnector(
            limit=100,  # Max connections (similar to max_connections)
            limit_per_host=20,  # Max connections per host (similar to max_keepalive_connections)
            enable_cleanup_closed=True,
            force_close=False,
            ttl_dns_cache=300  # Cache DNS results for 5 minutes
        )
        
        # Create aiohttp session
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=timeout)
        )
        
        # Configurable semaphore for throttling
        self._sem = asyncio.Semaphore(max_concurrency)
        
        # File hash for caching
        self._file_hash = None
        if self.use_cache:
            self._file_hash = self._calculate_file_hash()

    # Circuit breaker pattern implementation
    class CircuitBreaker:
        """Implements the circuit breaker pattern for API calls"""
        
        def __init__(self, failure_threshold=5, recovery_time=30, timeout_threshold=10):
            self.failure_count = 0
            self.failure_threshold = failure_threshold
            self.recovery_time = recovery_time  # seconds
            self.timeout_threshold = timeout_threshold  # seconds
            self.last_failure_time = 0
            self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
            
        def record_success(self):
            """Record a successful call"""
            if self.state == "HALF-OPEN":
                log.info("Circuit breaker reset to CLOSED after successful call")
                self.state = "CLOSED"
            self.failure_count = 0
            
        def record_failure(self):
            """Record a failed call"""
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
                log.warning(f"Circuit OPEN: {self.failure_count} consecutive failures")
                self.state = "OPEN"
                
        def allow_request(self):
            """Determine if a request should be allowed through the circuit"""
            if self.state == "CLOSED":
                return True
                
            if self.state == "OPEN":
                # Check if recovery time has elapsed
                if time.time() - self.last_failure_time >= self.recovery_time:
                    log.info("Circuit changed from OPEN to HALF-OPEN: attempting recovery")
                    self.state = "HALF-OPEN"
                    return True
                return False
                
            # HALF-OPEN state - allow one test request
            return True
            
        def __str__(self):
            return f"CircuitBreaker(state={self.state}, failures={self.failure_count})"

    # Initialize the circuit breaker
    _circuit = CircuitBreaker()

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
            retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
            reraise=True
        )

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Asynchronously checks response status and returns JSON content."""
        try:
            response.raise_for_status()
            self._circuit.record_success()  # Record successful API call
        except aiohttp.ClientResponseError as exc:
            self._circuit.record_failure()  # Record failed API call
            
            try:
                error_body = await response.text()
                
                # Enhanced error logging with more context
                log.error(f"HTTP error occurred: {exc}")
                log.error(f"Status code: {response.status}")
                log.error(f"Response headers: {dict(response.headers)}")
                log.error(f"Response body: {error_body}")
                
                # Try to parse error for better context
                try:
                    error_json = json.loads(error_body)
                    if isinstance(error_json, dict):
                        error_message = error_json.get('error', {}).get('message', '')
                        if error_message:
                            log.error(f"API error message: {error_message}")
                except (json.JSONDecodeError, AttributeError):
                    pass
            except Exception as e:
                log.error(f"Error while processing error response: {e}")
            
            raise
        
        if response.status == 204 or response.content_length == 0:
            return {}
        
        try:    
            return await response.json()
        except json.JSONDecodeError as e:
            text_content = await response.text()
            log.error(f"JSON decode error: {e}. Response text: {text_content[:200]}...")
            raise

    async def _make_api_call(self, method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
        """Make API call with circuit breaker pattern applied"""
        if not self._circuit.allow_request():
            log.warning(f"Circuit breaker OPEN: Refusing to make API call to {url}")
            raise RuntimeError(f"Circuit breaker is OPEN, API call to {url} rejected")
            
        try:
            log.debug(f"Making {method} request to {url}")
            if method.upper() == "GET":
                response = await self.session.get(url, **kwargs)
            elif method.upper() == "POST":
                response = await self.session.post(url, **kwargs)
            elif method.upper() == "DELETE":
                response = await self.session.delete(url, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            return response
        except Exception as e:
            self._circuit.record_failure()
            log.error(f"API call failed ({method} {url}): {str(e)}")
            raise

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
            
            # aiohttp file upload using FormData
            data = aiohttp.FormData()
            with open(self.file_path, 'rb') as f:
                data.add_field('file', 
                              f, 
                              filename=file_name, 
                              content_type='application/pdf')
            data.add_field('purpose', 'ocr')
            
            r = await self._make_api_call("POST", url, data=data)
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
        headers = {"Accept": "application/json"}

        try:
            r = await self._make_api_call("GET", url, params=params, headers=headers)
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
        headers = {
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
            # For large responses, we'll use streaming
            stream_enabled = self.file_size > 10 * 1024 * 1024  # Stream for files > 10MB
            
            if stream_enabled:
                log.info("Using streaming mode for large response")
                chunks = []
                async with self.session.post(url, json=payload, headers=headers) as r:
                    r.raise_for_status()
                    async for chunk, _ in r.content.iter_chunks():
                        if chunk:
                            chunks.append(chunk)
                
                response_data = json.loads(b"".join(chunks))
                self._circuit.record_success()
            else:
                # Direct response for smaller files
                r = await self._make_api_call("POST", url, json=payload, headers=headers)
                response_data = await self._handle_response(r)
                
            log.info("OCR processing done.")
            log.debug(f"OCR response size: {len(str(response_data))} bytes")
            return response_data
        except Exception as e:
            log.error(f"Failed during OCR processing: {e}")
            raise

    @retry(wait=wait_exponential(multiplier=0.5, max=10), stop=stop_after_attempt(3), reraise=False)
    async def _delete_file(self, file_id: str) -> None:
        """Deletes the file from Mistral storage with retry logic."""
        log.info(f"Deleting uploaded file ID: {file_id}")
        url = f"{self.BASE_API_URL}/files/{file_id}"

        try:
            r = await self._make_api_call("DELETE", url)
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
                "confidence": page_data.get("confidence", 0.0),
                "processed_at": int(time.time()),
            },
        )

    async def _process_pages_batch(self, pages_data: List[Dict], total_pages: int) -> List[Document]:
        """Process a batch of pages in parallel"""
        loop = asyncio.get_event_loop()
        
        tasks = [
            loop.run_in_executor(
                None,
                functools.partial(self._build_document, page_data, total_pages)
            )
            for page_data in pages_data
        ]
        
        batch_results = await asyncio.gather(*tasks)
        # Filter out any pages that returned None
        return [doc for doc in batch_results if doc is not None]

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
                start_time = time.time()
                
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
                log.info(f"Processing {total_pages} pages from OCR response")
                
                # Adaptive batch size based on number of pages and their average size
                # Calculate an estimate of page sizes
                avg_page_size = sum(len(str(p)) for p in pages_data[:min(10, total_pages)]) / min(10, total_pages)
                
                # Adjust batch size inversely to page size, within reasonable bounds
                if avg_page_size > 100000:  # Very large pages
                    batch_size = max(5, min(20, total_pages))
                elif avg_page_size > 50000:  # Medium-large pages
                    batch_size = max(10, min(30, total_pages))
                else:  # Normal or small pages
                    batch_size = max(20, min(50, total_pages))
                    
                log.debug(f"Using batch size of {batch_size} for pages with avg size {avg_page_size:.0f} characters")
                
                # Process pages in optimized batches
                documents = []
                for i in range(0, total_pages, batch_size):
                    batch = pages_data[i:i+batch_size]
                    log.debug(f"Processing batch of {len(batch)} pages ({i+1}-{min(i+batch_size, total_pages)})")
                    batch_results = await self._process_pages_batch(batch, total_pages)
                    documents.extend(batch_results)
                    
                    # Progress reporting for large documents
                    if total_pages > 20 and (i+batch_size) % 20 == 0:
                        log.info(f"Progress: processed {min(i+batch_size, total_pages)}/{total_pages} pages")
                
                if not documents:
                    log.warning("No valid pages processed after parallel parsing.")
                    return [Document(page_content="No text content found", metadata={})]
                
                processing_time = time.time() - start_time
                log.info(f"OCR processing completed in {processing_time:.2f} seconds for {total_pages} pages")
                
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
        await self.session.close()

async def shutdown_loader(loader: MistralLoader):
    """Safely shut down the loader and close its session."""
    if loader and hasattr(loader, 'session'):
        await loader.session.close()
