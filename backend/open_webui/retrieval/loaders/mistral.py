import requests
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

    def _upload_file(self) -> str:
        """Uploads the file to Mistral for OCR processing."""
        log.info("Uploading file to Mistral API")
        url = f"{self.BASE_API_URL}/files"
        file_name = os.path.basename(self.file_path)

        try:
            with open(self.file_path, "rb") as f:
                files = {"file": (file_name, f, "application/pdf")}
                data = {"purpose": "ocr"}

                upload_headers = self.headers.copy()  # Avoid modifying self.headers

                response = requests.post(
                    url, headers=upload_headers, files=files, data=data
                )

            response_data = self._handle_response(response)
            file_id = response_data.get("id")
            if not file_id:
                raise ValueError("File ID not found in upload response.")
            log.info(f"File uploaded successfully. File ID: {file_id}")
            return file_id
        except Exception as e:
            log.error(f"Failed to upload file: {e}")
            raise

    def _get_signed_url(self, file_id: str) -> str:
        """Retrieves a temporary signed URL for the uploaded file."""
        log.info(f"Getting signed URL for file ID: {file_id}")
        url = f"{self.BASE_API_URL}/files/{file_id}/url"
        params = {"expiry": 1}
        signed_url_headers = {**self.headers, "Accept": "application/json"}

        try:
            response = requests.get(url, headers=signed_url_headers, params=params)
            response_data = self._handle_response(response)
            signed_url = response_data.get("url")
            if not signed_url:
                raise ValueError("Signed URL not found in response.")
            log.info("Signed URL received.")
            return signed_url
        except Exception as e:
            log.error(f"Failed to get signed URL: {e}")
            raise

    def _process_ocr(self, signed_url: str) -> Dict[str, Any]:
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
            response = requests.post(url, headers=ocr_headers, json=payload)
            ocr_response = self._handle_response(response)
            log.info("OCR processing done.")
            log.debug("OCR response: %s", ocr_response)
            return ocr_response
        except Exception as e:
            log.error(f"Failed during OCR processing: {e}")
            raise

    def _delete_file(self, file_id: str) -> None:
        """Deletes the file from Mistral storage."""
        log.info(f"Deleting uploaded file ID: {file_id}")
        url = f"{self.BASE_API_URL}/files/{file_id}"
        # No specific Accept header needed, default or Authorization is usually sufficient

        try:
            response = requests.delete(url, headers=self.headers)
            delete_response = self._handle_response(
                response
            )  # Check status, ignore response body unless needed
            log.info(
                f"File deleted successfully: {delete_response}"
            )  # Log the response if available
        except Exception as e:
            # Log error but don't necessarily halt execution if deletion fails
            log.error(f"Failed to delete file ID {file_id}: {e}")
            # Depending on requirements, you might choose to raise the error here

    def load(self) -> List[Document]:
        """
        Executes the full OCR workflow: upload, get URL, process OCR, delete file.

        Returns:
            A list of Document objects, one for each page processed.
        """
        file_id = None
        try:
            # 1. Upload file
            file_id = self._upload_file()

            # 2. Get Signed URL
            signed_url = self._get_signed_url(file_id)

            # 3. Process OCR
            ocr_response = self._process_ocr(signed_url)

            # 4. Process results
            pages_data = ocr_response.get("pages")
            if not pages_data:
                log.warning("No pages found in OCR response.")
                return [Document(page_content="No text content found", metadata={})]

            documents = []
            total_pages = len(pages_data)
            for page_data in pages_data:
                page_content = page_data.get("markdown")
                page_index = page_data.get("index")  # API uses 0-based index

                if page_content is not None and page_index is not None:
                    documents.append(
                        Document(
                            page_content=page_content,
                            metadata={
                                "page": page_index,  # 0-based index from API
                                "page_label": page_index
                                + 1,  # 1-based label for convenience
                                "total_pages": total_pages,
                                # Add other relevant metadata from page_data if available/needed
                                # e.g., page_data.get('width'), page_data.get('height')
                            },
                        )
                    )
                else:
                    log.warning(
                        f"Skipping page due to missing 'markdown' or 'index'. Data: {page_data}"
                    )

            if not documents:
                # Case where pages existed but none had valid markdown/index
                log.warning(
                    "OCR response contained pages, but none had valid content/index."
                )
                return [
                    Document(
                        page_content="No text content found in valid pages", metadata={}
                    )
                ]

            return documents

        except Exception as e:
            log.error(f"An error occurred during the loading process: {e}")
            # Return an empty list or a specific error document on failure
            return [Document(page_content=f"Error during processing: {e}", metadata={})]
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
