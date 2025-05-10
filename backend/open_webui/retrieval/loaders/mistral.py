import asyncio
import aiohttp
from tenacity import retry, wait_exponential, stop_after_attempt
import logging
import os
import sys
from typing import List, Dict, Any

from langchain_core.documents import Document
from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class MistralLoader:
    """
    Loads documents by processing them through the Mistral OCR API.
    """

    BASE_API_URL = "https://api.mistral.ai/v1"

    def __init__(self, api_key: str, file_path: str):
        """
        Initializes the loader.

        Args:
            api_key: Your Mistral API key.
            file_path: The local path to the PDF file to process.
        """
        if not api_key:
            raise ValueError("API key cannot be empty.")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at {file_path}")

        self.api_key = api_key
        self.file_path = file_path
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        # Use an aiohttp session for async I/O
        self.session = aiohttp.ClientSession(headers=self.headers)
        # Semaphore to throttle concurrent loads
        self._sem = asyncio.Semaphore(5)

    async def _handle_response(self, response):
        """Checks response status and returns JSON content."""
        if response.status >= 400:
            text = await response.text()
            raise aiohttp.ClientResponseError(
                request_info=response.request_info,
                history=response.history,
                status=response.status,
                message=text,
                headers=response.headers,
            )
        # Handle potential empty responses for certain successful requests (e.g., DELETE)
        if response.status == 204 or response.content_length == 0:
            return {}  # Return empty dict if no content
        return await response.json()

    async def _upload_file(self) -> str:
        """Uploads the file to Mistral for OCR processing."""
        log.info("Uploading file to Mistral API")
        url = f"{self.BASE_API_URL}/files"
        file_name = os.path.basename(self.file_path)

        try:
            f = open(self.file_path, "rb")
            data = aiohttp.FormData()
            data.add_field('file', f, filename=file_name, content_type='application/pdf')
            data.add_field('purpose', 'ocr')

            upload_headers = self.headers.copy()  # Avoid modifying self.headers

            async with self.session.post(url, headers=upload_headers, data=data) as resp:
                response_data = await self._handle_response(resp)

            f.close()

            file_id = response_data.get("id")
            if not file_id:
                raise ValueError("File ID not found in upload response.")
            log.info(f"File uploaded successfully. File ID: {file_id}")
            return file_id
        except Exception as e:
            log.error(f"Failed to upload file: {e}")
            raise

    async def _get_signed_url(self, file_id: str) -> str:
        """Retrieves a temporary signed URL for the uploaded file."""
        log.info(f"Getting signed URL for file ID: {file_id}")
        url = f"{self.BASE_API_URL}/files/{file_id}/url"
        params = {"expiry": 1}
        signed_url_headers = {**self.headers, "Accept": "application/json"}

        try:
            async with self.session.get(url, headers=signed_url_headers, params=params) as resp:
                response_data = await self._handle_response(resp)
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
        """Sends the signed URL to the OCR endpoint for processing."""
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
            async with self.session.post(url, headers=ocr_headers, json=payload) as resp:
                ocr_response = await self._handle_response(resp)
            log.info("OCR processing done.")
            log.debug("OCR response: %s", ocr_response)
            return ocr_response
        except Exception as e:
            log.error(f"Failed during OCR processing: {e}")
            raise

    async def _delete_file(self, file_id: str) -> None:
        """Deletes the file from Mistral storage."""
        log.info(f"Deleting uploaded file ID: {file_id}")
        url = f"{self.BASE_API_URL}/files/{file_id}"
        # No specific Accept header needed, default or Authorization is usually sufficient

        try:
            async with self.session.delete(url, headers=self.headers) as resp:
                delete_response = await self._handle_response(resp)
            log.info(
                f"File deleted successfully: {delete_response}"
            )  # Log the response if available
        except Exception as e:
            # Log error but don't necessarily halt execution if deletion fails
            log.error(f"Failed to delete file ID {file_id}: {e}")
            # Depending on requirements, you might choose to raise the error here

    def _build_document(self, page_data: Dict[str, Any], total_pages: int) -> Document:
        """Helper to build a Document from page data."""
        page_content = page_data.get("markdown")
        page_index = page_data.get("index")
        if page_content is not None and page_index is not None:
            return Document(
                page_content=page_content,
                metadata={
                    "page": page_index,  # 0-based index
                    "page_label": page_index + 1,  # 1-based label
                    "total_pages": total_pages,
                },
            )
        else:
            log.warning(
                f"Skipping page due to missing 'markdown' or 'index'. Data: {page_data}"
            )
            return None

    async def load(self) -> List[Document]:
        """
        Executes the full OCR workflow: upload, get URL, process OCR, delete file.

        Returns:
            A list of Document objects, one for each page processed.
        """
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
                pages_data = ocr_response.get("pages")
                if not pages_data:
                    log.warning("No pages found in OCR response.")
                    return [Document(page_content="No text content found", metadata={})]

                total_pages = len(pages_data)
                # Parallelize page-to-Document conversion
                loop = asyncio.get_event_loop()
                tasks = [
                    loop.run_in_executor(
                        None,
                        self._build_document,
                        page_data,
                        total_pages,
                    )
                    for page_data in pages_data
                ]
                results = await asyncio.gather(*tasks)
                # Filter out any pages that returned None
                documents = [doc for doc in results if doc is not None]
                if not documents:
                    log.warning(
                        "No valid pages processed after parallel parsing."
                    )
                    return [Document(page_content="No text content found", metadata={})]
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

async def shutdown_loader(loader: MistralLoader):
    await loader.session.close()
