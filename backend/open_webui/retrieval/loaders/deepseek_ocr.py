import os
import sys
import logging
import time
import base64
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_core.documents import Document
from open_webui.env import SRC_LOG_LEVELS, GLOBAL_LOG_LEVEL

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class DeepSeekOCRLoader:
    """
    DeepSeek OCR loader using vLLM server with OpenAI-compatible API.

    The vLLM server should be running DeepSeek-OCR model and exposing
    an OpenAI Vision API compatible endpoint.

    Operational Modes (configured on vLLM server side):
    - tiny: 512x512, ~64 tokens - Fast preview
    - small: 640x640, ~100 tokens - Standard docs
    - base: 1024x1024, ~256 tokens - High quality
    - large: 1280x1280, ~400 tokens - Very high res
    - gundam: 1024 base + 640 crops, variable - Adaptive (recommended)
    """

    def __init__(
        self,
        file_path: str,
        api_base_url: str,
        api_key: str = "",
        model_name: str = "deepseek-ocr",
        prompt: str = "<image>\n<|grounding|>Convert the document to markdown. ",
        timeout: int = 300,
        max_retries: int = 3,
        enable_debug_logging: bool = False,
    ):
        """
        Initialize DeepSeek OCR loader with API client.

        Args:
            file_path: Path to image file
            api_base_url: Base URL of vLLM server (e.g., http://gpu-server:8000/v1)
            api_key: API key for authentication
            model_name: Model identifier on vLLM server
            prompt: OCR prompt template
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            enable_debug_logging: Enable detailed logging
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if not api_base_url:
            raise ValueError("api_base_url is required")

        self.file_path = file_path
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.prompt = prompt
        self.timeout = timeout
        self.max_retries = max_retries
        self.debug = enable_debug_logging

        # Pre-compute file info
        self.file_name = os.path.basename(file_path)
        self.file_size = os.path.getsize(file_path)
        self.file_ext = self.file_name.split(".")[-1].lower()

        # Setup headers
        self.headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    def _debug_log(self, message: str, *args) -> None:
        """Conditional debug logging."""
        if self.debug:
            log.debug(message, *args)

    def _encode_image_base64(self, image_path: str) -> str:
        """Encode image to base64 string."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _convert_pdf_to_images(self) -> List[str]:
        """
        Convert PDF to images using pdf2image.

        Returns:
            List of temporary image file paths
        """
        try:
            from pdf2image import convert_from_path
            import tempfile

            log.info(f"Converting PDF to images: {self.file_name}")

            # Convert PDF to images
            images = convert_from_path(self.file_path, dpi=200)

            # Save to temporary files
            temp_files = []
            temp_dir = tempfile.mkdtemp(prefix="deepseek_ocr_")

            for i, image in enumerate(images):
                temp_path = os.path.join(temp_dir, f"page_{i:04d}.png")
                image.save(temp_path, "PNG")
                temp_files.append(temp_path)

            log.info(f"Converted {len(temp_files)} pages from PDF")
            return temp_files

        except ImportError:
            raise ImportError(
                "pdf2image is required for PDF processing. "
                "Install with: pip install pdf2image"
            )
        except Exception as e:
            log.error(f"Failed to convert PDF: {e}")
            raise

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if error is retryable."""
        if isinstance(error, requests.exceptions.ConnectionError):
            return True
        if isinstance(error, requests.exceptions.Timeout):
            return True
        if isinstance(error, requests.exceptions.HTTPError):
            if hasattr(error, "response") and error.response is not None:
                status_code = error.response.status_code
                # Retry on server errors (5xx) or rate limits (429)
                return status_code >= 500 or status_code == 429
        return False

    def _call_vision_api(
        self, image_path: str, page_index: int = 0, total_pages: int = 1
    ) -> Document:
        """
        Call vLLM server using OpenAI Vision API format.

        Args:
            image_path: Path to image file
            page_index: Page number (0-indexed)
            total_pages: Total number of pages

        Returns:
            Document object with OCR results
        """
        start_time = time.time()

        try:
            self._debug_log(
                f"Processing via API: {os.path.basename(image_path)} "
                f"(page {page_index + 1}/{total_pages})"
            )

            # Encode image to base64
            image_base64 = self._encode_image_base64(image_path)

            # Construct OpenAI Vision API compatible request
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self.prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                },
                            },
                        ],
                    }
                ],
                "max_tokens": 4096,
                "temperature": 0,  # Deterministic for OCR
            }

            # Make request with retry logic
            for attempt in range(self.max_retries):
                try:
                    response = requests.post(
                        f"{self.api_base_url}/chat/completions",
                        headers=self.headers,
                        json=payload,
                        timeout=self.timeout,
                    )
                    response.raise_for_status()
                    break
                except Exception as e:
                    if attempt == self.max_retries - 1 or not self._is_retryable_error(
                        e
                    ):
                        raise

                    wait_time = min((2**attempt) + 0.5, 30)
                    log.warning(
                        f"Retryable error (attempt {attempt + 1}/{self.max_retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)

            # Parse response
            result = response.json()

            self._debug_log(f"API Response: {result}")

            # Extract content from OpenAI format
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
            else:
                raise ValueError(f"Unexpected API response format: {result}")

            processing_time = time.time() - start_time

            # Clean content
            cleaned_content = content.strip()

            if not cleaned_content:
                log.warning(f"Empty OCR result for page {page_index + 1}")
                cleaned_content = "[Empty page - no text extracted]"

            self._debug_log(
                f"Page {page_index + 1} processed in {processing_time:.2f}s "
                f"({len(cleaned_content)} chars)"
            )

            # Extract usage stats if available
            usage = result.get("usage", {})

            # Create Document with rich metadata
            return Document(
                page_content=cleaned_content,
                metadata={
                    "page": page_index,
                    "page_label": page_index + 1,
                    "total_pages": total_pages,
                    "file_name": self.file_name,
                    "file_size": self.file_size,
                    "processing_engine": "deepseek-ocr",
                    "model_name": self.model_name,
                    "api_base_url": self.api_base_url,
                    "processing_time": round(processing_time, 2),
                    "content_length": len(cleaned_content),
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
            )

        except Exception as e:
            processing_time = time.time() - start_time
            log.error(
                f"Failed to process page {page_index + 1} via API after "
                f"{processing_time:.2f}s: {e}"
            )

            # Return error document
            return Document(
                page_content=f"Error processing page {page_index + 1}: {e}",
                metadata={
                    "error": "api_call_failed",
                    "page": page_index,
                    "page_label": page_index + 1,
                    "total_pages": total_pages,
                    "file_name": self.file_name,
                },
            )

    def _cleanup_temp_files(self, temp_files: List[str]) -> None:
        """Clean up temporary image files."""
        if not temp_files:
            return

        try:
            import shutil

            # Get parent directory
            temp_dir = os.path.dirname(temp_files[0])

            # Remove entire temp directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                self._debug_log(f"Cleaned up temp directory: {temp_dir}")

        except Exception as e:
            log.warning(f"Failed to cleanup temp files: {e}")

    def load(self) -> List[Document]:
        """
        Execute OCR workflow via API.

        Returns:
            List of Document objects (one per page for PDFs, one for images)
        """
        start_time = time.time()
        temp_files = []

        try:
            # Determine if we need to convert PDF to images
            if self.file_ext == "pdf":
                image_paths = self._convert_pdf_to_images()
                temp_files = image_paths  # Track for cleanup
            elif self.file_ext in ["png", "jpg", "jpeg", "webp", "tiff", "gif", "bmp"]:
                image_paths = [self.file_path]
            else:
                raise ValueError(
                    f"Unsupported file type: {self.file_ext}. "
                    f"Supported: pdf, png, jpg, jpeg, webp, tiff, gif, bmp"
                )

            total_pages = len(image_paths)
            log.info(
                f"Processing {total_pages} page(s) via DeepSeek OCR API "
                f"from {self.file_name}"
            )

            # Process each image/page
            documents = []
            for i, image_path in enumerate(image_paths):
                doc = self._call_vision_api(
                    image_path, page_index=i, total_pages=total_pages
                )
                documents.append(doc)

            # Filter out error documents if there are successful ones
            successful_docs = [d for d in documents if "error" not in d.metadata]
            if successful_docs:
                documents = successful_docs

            total_time = time.time() - start_time
            total_chars = sum(len(d.page_content) for d in documents)
            total_tokens = sum(d.metadata.get("total_tokens", 0) for d in documents)

            log.info(
                f"OCR completed in {total_time:.2f}s: "
                f"{len(documents)} pages, {total_chars} characters, "
                f"{total_tokens} tokens"
            )

            return documents

        except Exception as e:
            total_time = time.time() - start_time
            log.error(f"OCR workflow failed after {total_time:.2f}s: {e}")

            # Return error document
            return [
                Document(
                    page_content=f"Error during OCR processing: {e}",
                    metadata={
                        "error": "processing_failed",
                        "file_name": self.file_name,
                        "processing_engine": "deepseek-ocr",
                    },
                )
            ]
        finally:
            # Cleanup temporary files
            if temp_files:
                self._cleanup_temp_files(temp_files)
