import os
import time
import requests
import logging
import tempfile
import zipfile
from typing import List, Optional
from langchain_core.documents import Document
from fastapi import HTTPException, status

log = logging.getLogger(__name__)


class MinerULoader:
    """
    MinerU document parser loader supporting both Cloud API and Local API modes.

    Cloud API: Uses MinerU managed service with async task-based processing
    Local API: Uses self-hosted MinerU API with synchronous processing
    """

    def __init__(
        self,
        file_path: str,
        api_mode: str = "local",
        api_url: str = "http://localhost:8000",
        api_key: str = "",
        params: dict = None,
        timeout: Optional[int] = 300,
    ):
        self.file_path = file_path
        self.api_mode = api_mode.lower()
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

        # Parse params dict with defaults
        self.params = params or {}
        self.enable_ocr = params.get("enable_ocr", False)
        self.enable_formula = params.get("enable_formula", True)
        self.enable_table = params.get("enable_table", True)
        self.language = params.get("language", "en")
        self.model_version = params.get("model_version", "pipeline")

        self.page_ranges = self.params.pop("page_ranges", "")

        # Validate API mode
        if self.api_mode not in ["local", "cloud"]:
            raise ValueError(
                f"Invalid API mode: {self.api_mode}. Must be 'local' or 'cloud'"
            )

        # Validate Cloud API requirements
        if self.api_mode == "cloud" and not self.api_key:
            raise ValueError("API key is required for Cloud API mode")

    def load(self) -> List[Document]:
        """
        Main entry point for loading and parsing the document.
        Routes to Cloud or Local API based on api_mode.
        """
        try:
            if self.api_mode == "cloud":
                return self._load_cloud_api()
            else:
                return self._load_local_api()
        except Exception as e:
            log.error(f"Error loading document with MinerU: {e}")
            raise

    def _load_local_api(self) -> List[Document]:
        """
        Load document using Local API (synchronous).
        Posts file to /file_parse endpoint and gets immediate response.
        """
        log.info(f"Using MinerU Local API at {self.api_url}")

        filename = os.path.basename(self.file_path)

        # Build form data for Local API
        form_data = {
            **self.params,
            "return_md": "true",
        }

        # Page ranges (Local API uses start_page_id and end_page_id)
        if self.page_ranges:
            # For simplicity, if page_ranges is specified, log a warning
            # Full page range parsing would require parsing the string
            log.warning(
                f"Page ranges '{self.page_ranges}' specified but Local API uses different format. "
                "Consider using start_page_id/end_page_id parameters if needed."
            )

        try:
            with open(self.file_path, "rb") as f:
                files = {"files": (filename, f, "application/octet-stream")}

                log.info(f"Sending file to MinerU Local API: {filename}")
                log.debug(f"Local API parameters: {form_data}")

                response = requests.post(
                    f"{self.api_url}/file_parse",
                    data=form_data,
                    files=files,
                    timeout=self.timeout,
                )
                response.raise_for_status()

        except FileNotFoundError:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail=f"File not found: {self.file_path}"
            )
        except requests.Timeout:
            raise HTTPException(
                status.HTTP_504_GATEWAY_TIMEOUT,
                detail="MinerU Local API request timed out",
            )
        except requests.HTTPError as e:
            error_detail = f"MinerU Local API request failed: {e}"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_detail += f" - {error_data}"
                except:
                    error_detail += f" - {e.response.text}"
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_detail)
        except Exception as e:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error calling MinerU Local API: {str(e)}",
            )

        # Parse response
        try:
            result = response.json()
        except ValueError as e:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail=f"Invalid JSON response from MinerU Local API: {e}",
            )

        # Extract markdown content from response
        if "results" not in result:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="MinerU Local API response missing 'results' field",
            )

        results = result["results"]
        if not results:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="MinerU returned empty results",
            )

        # Get the first (and typically only) result
        file_result = list(results.values())[0]
        markdown_content = file_result.get("md_content", "")

        if not markdown_content:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="MinerU returned empty markdown content",
            )

        log.info(f"Successfully parsed document with MinerU Local API: {filename}")

        # Create metadata
        metadata = {
            "source": filename,
            "api_mode": "local",
            "backend": result.get("backend", "unknown"),
            "version": result.get("version", "unknown"),
        }

        return [Document(page_content=markdown_content, metadata=metadata)]

    def _load_cloud_api(self) -> List[Document]:
        """
        Load document using Cloud API (asynchronous).
        Uses batch upload endpoint to avoid need for public file URLs.
        """
        log.info(f"Using MinerU Cloud API at {self.api_url}")

        filename = os.path.basename(self.file_path)

        # Step 1: Request presigned upload URL
        batch_id, upload_url = self._request_upload_url(filename)

        # Step 2: Upload file to presigned URL
        self._upload_to_presigned_url(upload_url)

        # Step 3: Poll for results
        result = self._poll_batch_status(batch_id, filename)

        # Step 4: Download and extract markdown from ZIP
        markdown_content = self._download_and_extract_zip(
            result["full_zip_url"], filename
        )

        log.info(f"Successfully parsed document with MinerU Cloud API: {filename}")

        # Create metadata
        metadata = {
            "source": filename,
            "api_mode": "cloud",
            "batch_id": batch_id,
        }

        return [Document(page_content=markdown_content, metadata=metadata)]

    def _request_upload_url(self, filename: str) -> tuple:
        """
        Request presigned upload URL from Cloud API.
        Returns (batch_id, upload_url).
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Build request body
        request_body = {
            **self.params,
            "files": [
                {
                    "name": filename,
                    "is_ocr": self.enable_ocr,
                }
            ],
        }

        # Add page ranges if specified
        if self.page_ranges:
            request_body["files"][0]["page_ranges"] = self.page_ranges

        log.info(f"Requesting upload URL for: {filename}")
        log.debug(f"Cloud API request body: {request_body}")

        try:
            response = requests.post(
                f"{self.api_url}/file-urls/batch",
                headers=headers,
                json=request_body,
                timeout=30,
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            error_detail = f"Failed to request upload URL: {e}"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_detail += f" - {error_data.get('msg', error_data)}"
                except:
                    error_detail += f" - {e.response.text}"
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_detail)
        except Exception as e:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error requesting upload URL: {str(e)}",
            )

        try:
            result = response.json()
        except ValueError as e:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail=f"Invalid JSON response: {e}",
            )

        # Check for API error response
        if result.get("code") != 0:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"MinerU Cloud API error: {result.get('msg', 'Unknown error')}",
            )

        data = result.get("data", {})
        batch_id = data.get("batch_id")
        file_urls = data.get("file_urls", [])

        if not batch_id or not file_urls:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="MinerU Cloud API response missing batch_id or file_urls",
            )

        upload_url = file_urls[0]
        log.info(f"Received upload URL for batch: {batch_id}")

        return batch_id, upload_url

    def _upload_to_presigned_url(self, upload_url: str) -> None:
        """
        Upload file to presigned URL (no authentication needed).
        """
        log.info(f"Uploading file to presigned URL")

        try:
            with open(self.file_path, "rb") as f:
                response = requests.put(
                    upload_url,
                    data=f,
                    timeout=self.timeout,
                )
                response.raise_for_status()
        except FileNotFoundError:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail=f"File not found: {self.file_path}"
            )
        except requests.Timeout:
            raise HTTPException(
                status.HTTP_504_GATEWAY_TIMEOUT,
                detail="File upload to presigned URL timed out",
            )
        except requests.HTTPError as e:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to upload file to presigned URL: {e}",
            )
        except Exception as e:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error uploading file: {str(e)}",
            )

        log.info("File uploaded successfully")

    def _poll_batch_status(self, batch_id: str, filename: str) -> dict:
        """
        Poll batch status until completion.
        Returns the result dict for the file.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        max_iterations = 300  # 10 minutes max (2 seconds per iteration)
        poll_interval = 2  # seconds

        log.info(f"Polling batch status: {batch_id}")

        for iteration in range(max_iterations):
            try:
                response = requests.get(
                    f"{self.api_url}/extract-results/batch/{batch_id}",
                    headers=headers,
                    timeout=30,
                )
                response.raise_for_status()
            except requests.HTTPError as e:
                error_detail = f"Failed to poll batch status: {e}"
                if e.response is not None:
                    try:
                        error_data = e.response.json()
                        error_detail += f" - {error_data.get('msg', error_data)}"
                    except:
                        error_detail += f" - {e.response.text}"
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=error_detail)
            except Exception as e:
                raise HTTPException(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error polling batch status: {str(e)}",
                )

            try:
                result = response.json()
            except ValueError as e:
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    detail=f"Invalid JSON response while polling: {e}",
                )

            # Check for API error response
            if result.get("code") != 0:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=f"MinerU Cloud API error: {result.get('msg', 'Unknown error')}",
                )

            data = result.get("data", {})
            extract_result = data.get("extract_result", [])

            # Find our file in the batch results
            file_result = None
            for item in extract_result:
                if item.get("file_name") == filename:
                    file_result = item
                    break

            if not file_result:
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    detail=f"File {filename} not found in batch results",
                )

            state = file_result.get("state")

            if state == "done":
                log.info(f"Processing complete for {filename}")
                return file_result
            elif state == "failed":
                error_msg = file_result.get("err_msg", "Unknown error")
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=f"MinerU processing failed: {error_msg}",
                )
            elif state in ["waiting-file", "pending", "running", "converting"]:
                # Still processing
                if iteration % 10 == 0:  # Log every 20 seconds
                    log.info(
                        f"Processing status: {state} (iteration {iteration + 1}/{max_iterations})"
                    )
                time.sleep(poll_interval)
            else:
                log.warning(f"Unknown state: {state}")
                time.sleep(poll_interval)

        # Timeout
        raise HTTPException(
            status.HTTP_504_GATEWAY_TIMEOUT,
            detail="MinerU processing timed out after 10 minutes",
        )

    def _download_and_extract_zip(self, zip_url: str, filename: str) -> str:
        """
        Download ZIP file from CDN and extract markdown content.
        Returns the markdown content as a string.
        """
        log.info(f"Downloading results from: {zip_url}")

        try:
            response = requests.get(zip_url, timeout=60)
            response.raise_for_status()
        except requests.HTTPError as e:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to download results ZIP: {e}",
            )
        except Exception as e:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error downloading results: {str(e)}",
            )

        # Save ZIP to temporary file and extract
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
                tmp_zip.write(response.content)
                tmp_zip_path = tmp_zip.name

            with tempfile.TemporaryDirectory() as tmp_dir:
                # Extract ZIP
                with zipfile.ZipFile(tmp_zip_path, "r") as zip_ref:
                    zip_ref.extractall(tmp_dir)

                # Find markdown file - search recursively for any .md file
                markdown_content = None
                found_md_path = None

                # First, list all files in the ZIP for debugging
                all_files = []
                for root, dirs, files in os.walk(tmp_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        all_files.append(full_path)
                        # Look for any .md file
                        if file.endswith(".md"):
                            found_md_path = full_path
                            log.info(f"Found markdown file at: {full_path}")
                            try:
                                with open(full_path, "r", encoding="utf-8") as f:
                                    markdown_content = f.read()
                                if (
                                    markdown_content
                                ):  # Use the first non-empty markdown file
                                    break
                            except Exception as e:
                                log.warning(f"Failed to read {full_path}: {e}")
                    if markdown_content:
                        break

                if markdown_content is None:
                    log.error(f"Available files in ZIP: {all_files}")
                    # Try to provide more helpful error message
                    md_files = [f for f in all_files if f.endswith(".md")]
                    if md_files:
                        error_msg = (
                            f"Found .md files but couldn't read them: {md_files}"
                        )
                    else:
                        error_msg = (
                            f"No .md files found in ZIP. Available files: {all_files}"
                        )
                    raise HTTPException(
                        status.HTTP_502_BAD_GATEWAY,
                        detail=error_msg,
                    )

            # Clean up temporary ZIP file
            os.unlink(tmp_zip_path)

        except zipfile.BadZipFile as e:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail=f"Invalid ZIP file received: {e}",
            )
        except Exception as e:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error extracting ZIP: {str(e)}",
            )

        if not markdown_content:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Extracted markdown content is empty",
            )

        log.info(
            f"Successfully extracted markdown content ({len(markdown_content)} characters)"
        )
        return markdown_content
