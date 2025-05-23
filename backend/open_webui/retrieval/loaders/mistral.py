import aiohttp
import asyncio
import logging
import os
import sys
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
import time

from langchain_core.documents import Document
from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class OptimizedMistralLoader:
    """
    High-performance Mistral OCR loader with async operations, connection pooling,
    retry logic, and memory optimization.
    """

    BASE_API_URL = "https://api.mistral.ai/v1"
    
    def __init__(
        self, 
        api_key: str, 
        file_path: str,
        timeout: int = 300,  # 5 minutes default
        max_retries: int = 3,
        chunk_size: int = 8192,  # 8KB chunks for streaming
        enable_debug_logging: bool = False
    ):
        """
        Initializes the optimized loader.

        Args:
            api_key: Your Mistral API key.
            file_path: The local path to the PDF file to process.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts.
            chunk_size: Chunk size for file streaming (bytes).
            enable_debug_logging: Enable detailed debug logs.
        """
        if not api_key:
            raise ValueError("API key cannot be empty.")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at {file_path}")

        self.api_key = api_key
        self.file_path = file_path
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.chunk_size = chunk_size
        self.debug = enable_debug_logging
        
        # Pre-compute file info
        self.file_name = os.path.basename(file_path)
        self.file_size = os.path.getsize(file_path)
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "OpenWebUI-MistralLoader/1.0"
        }

    def _debug_log(self, message: str, *args) -> None:
        """Conditional debug logging for performance."""
        if self.debug:
            log.debug(message, *args)

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Optimized response handling with better error info."""
        try:
            response.raise_for_status()
            
            # Check content type and length
            content_type = response.headers.get('content-type', '')
            if 'application/json' not in content_type:
                if response.status == 204:
                    return {}
                text = await response.text()
                raise ValueError(f"Unexpected content type: {content_type}, body: {text[:200]}...")
            
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

    async def _retry_request(self, request_func, *args, **kwargs) -> Any:
        """Exponential backoff retry logic."""
        for attempt in range(self.max_retries):
            try:
                return await request_func(*args, **kwargs)
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == self.max_retries - 1:
                    raise
                
                wait_time = (2 ** attempt) + 0.5  # Exponential backoff with jitter
                log.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

    async def _upload_file_optimized(self, session: aiohttp.ClientSession) -> str:
        """Memory-efficient file upload with streaming."""
        url = f"{self.BASE_API_URL}/files"
        
        async def upload_request():
            # Create multipart writer for streaming upload
            writer = aiohttp.MultipartWriter('form-data')
            
            # Add purpose field
            purpose_part = writer.append('ocr')
            purpose_part.set_content_disposition('form-data', name='purpose')
            
            # Add file part with streaming
            file_part = writer.append_payload(aiohttp.streams.FilePayload(
                self.file_path,
                filename=self.file_name,
                content_type='application/pdf'
            ))
            file_part.set_content_disposition('form-data', name='file', filename=self.file_name)
            
            self._debug_log(f"Uploading file: {self.file_name} ({self.file_size:,} bytes)")
            
            async with session.post(
                url, 
                data=writer, 
                headers=self.headers,
                timeout=self.timeout
            ) as response:
                response_data = await self._handle_response(response)
                
        response_data = await self._retry_request(upload_request)
        
        file_id = response_data.get("id")
        if not file_id:
            raise ValueError("File ID not found in upload response.")
        
        log.info(f"File uploaded successfully. File ID: {file_id}")
        return file_id

    async def _get_signed_url_optimized(self, session: aiohttp.ClientSession, file_id: str) -> str:
        """Optimized signed URL retrieval."""
        url = f"{self.BASE_API_URL}/files/{file_id}/url"
        params = {"expiry": 1}
        
        headers = {
            **self.headers,
            "Accept": "application/json"
        }
        
        async def url_request():
            self._debug_log(f"Getting signed URL for file ID: {file_id}")
            async with session.get(
                url, 
                headers=headers, 
                params=params,
                timeout=self.timeout
            ) as response:
                return await self._handle_response(response)
        
        response_data = await self._retry_request(url_request)
        
        signed_url = response_data.get("url")
        if not signed_url:
            raise ValueError("Signed URL not found in response.")
        
        self._debug_log("Signed URL received successfully")
        return signed_url

    async def _process_ocr_optimized(self, session: aiohttp.ClientSession, signed_url: str) -> Dict[str, Any]:
        """Optimized OCR processing with better payload handling."""
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
                timeout=self.timeout
            ) as response:
                ocr_response = await self._handle_response(response)
                
            processing_time = time.time() - start_time
            log.info(f"OCR processing completed in {processing_time:.2f}s")
            
            return ocr_response
        
        return await self._retry_request(ocr_request)

    async def _delete_file_optimized(self, session: aiohttp.ClientSession, file_id: str) -> None:
        """Optimized file deletion with error tolerance."""
        url = f"{self.BASE_API_URL}/files/{file_id}"
        
        try:
            async def delete_request():
                self._debug_log(f"Deleting file ID: {file_id}")
                async with session.delete(
                    url, 
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=30)  # Shorter timeout for cleanup
                ) as response:
                    return await self._handle_response(response)
            
            await self._retry_request(delete_request)
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
            enable_cleanup_closed=True
        )
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers={"User-Agent": "OpenWebUI-MistralLoader/1.0"}
        ) as session:
            yield session

    def _process_ocr_results(self, ocr_response: Dict[str, Any]) -> List[Document]:
        """Optimized result processing with better error handling."""
        pages_data = ocr_response.get("pages")
        if not pages_data:
            log.warning("No pages found in OCR response.")
            return [Document(page_content="No text content found", metadata={"error": "no_pages"})]

        documents = []
        total_pages = len(pages_data)
        skipped_pages = 0
        
        for page_data in pages_data:
            page_content = page_data.get("markdown")
            page_index = page_data.get("index")

            if page_content is not None and page_index is not None:
                # Clean up content efficiently
                cleaned_content = page_content.strip() if isinstance(page_content, str) else str(page_content)
                
                if cleaned_content:  # Only add non-empty pages
                    documents.append(
                        Document(
                            page_content=cleaned_content,
                            metadata={
                                "page": page_index,
                                "page_label": page_index + 1,
                                "total_pages": total_pages,
                                "file_name": self.file_name,
                                "file_size": self.file_size,
                                "processing_engine": "mistral-ocr"
                            },
                        )
                    )
                else:
                    skipped_pages += 1
                    self._debug_log(f"Skipping empty page {page_index}")
            else:
                skipped_pages += 1
                self._debug_log(f"Skipping page due to missing data: {page_data}")

        if skipped_pages > 0:
            log.info(f"Processed {len(documents)} pages, skipped {skipped_pages} empty/invalid pages")

        if not documents:
            log.warning("No valid pages found after processing OCR response")
            return [
                Document(
                    page_content="No valid text content found in document",
                    metadata={"error": "no_valid_pages", "total_pages": total_pages}
                )
            ]

        return documents

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
                file_id = await self._upload_file_optimized(session)

                # 2. Get signed URL
                signed_url = await self._get_signed_url_optimized(session, file_id)

                # 3. Process OCR
                ocr_response = await self._process_ocr_optimized(session, signed_url)

                # 4. Process results
                documents = self._process_ocr_results(ocr_response)
                
                total_time = time.time() - start_time
                log.info(f"Complete OCR workflow finished in {total_time:.2f}s, produced {len(documents)} documents")
                
                return documents

        except Exception as e:
            total_time = time.time() - start_time
            log.error(f"OCR workflow failed after {total_time:.2f}s: {e}")
            return [Document(
                page_content=f"Error during OCR processing: {e}",
                metadata={"error": "processing_failed", "file_name": self.file_name}
            )]
        finally:
            # 5. Cleanup - always attempt file deletion
            if file_id:
                try:
                    async with self._get_session() as session:
                        await self._delete_file_optimized(session, file_id)
                except Exception as cleanup_error:
                    log.error(f"Cleanup failed for file ID {file_id}: {cleanup_error}")

    def load(self) -> List[Document]:
        """
        Synchronous wrapper for backward compatibility.
        
        Returns:
            A list of Document objects, one for each page processed.
        """
        try:
            # Check if we're already in an async context
            loop = asyncio.get_running_loop()
            # If we're in an async context, we need to use a different approach
            log.warning("Running async loader in sync context - consider using load_async() for better performance")
            
            # Create a new event loop in a thread for true async execution
            import concurrent.futures
            import threading
            
            def run_async():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(self.load_async())
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_async)
                return future.result()
                
        except RuntimeError:
            # No event loop running, we can use asyncio.run directly
            return asyncio.run(self.load_async())


# Backward compatibility alias
MistralLoader = OptimizedMistralLoader 
