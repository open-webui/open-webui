"""External Document Loader for Open WebUI.

This module provides a flexible document loader that can integrate with any external
HTTP API for document processing. It supports multiple request/response formats and
is designed to work with various document processing services.

Configuration:
    The loader is configured via environment variables or database settings:

    EXTERNAL_DOCUMENT_LOADER_URL: Base URL of the external API (required)
    EXTERNAL_DOCUMENT_LOADER_API_KEY: API key for authentication (optional)

    Request Configuration:
        EXTERNAL_DOCUMENT_LOADER_HTTP_METHOD: HTTP method (PUT, POST, PATCH)
        EXTERNAL_DOCUMENT_LOADER_ENDPOINT: API endpoint path (e.g., /process, /api/extract)
        EXTERNAL_DOCUMENT_LOADER_REQUEST_FORMAT: Format (binary, form-data, json-base64)
        EXTERNAL_DOCUMENT_LOADER_FILE_FIELD_NAME: Field name for file in request
        EXTERNAL_DOCUMENT_LOADER_FILENAME_FIELD_NAME: Field name for filename (optional)
        EXTERNAL_DOCUMENT_LOADER_PARAMS: Additional parameters as JSON object
        EXTERNAL_DOCUMENT_LOADER_QUERY_PARAMS: Query parameters as JSON object
        EXTERNAL_DOCUMENT_LOADER_HEADERS: Custom headers as JSON object

    Response Configuration:
        EXTERNAL_DOCUMENT_LOADER_RESPONSE_CONTENT_PATH: Path to content in response (dot notation)
        EXTERNAL_DOCUMENT_LOADER_RESPONSE_METADATA_PATH: Path to metadata in response
        EXTERNAL_DOCUMENT_LOADER_RESPONSE_TYPE: Response type (object, array, text)

Examples:
    DocStrange API configuration:
        URL: http://localhost:8000
        HTTP_METHOD: POST
        ENDPOINT: /api/extract
        REQUEST_FORMAT: form-data
        PARAMS: {"output_format": "markdown"}
        RESPONSE_CONTENT_PATH: content
        RESPONSE_METADATA_PATH: metadata
        RESPONSE_TYPE: object

    Generic binary API:
        URL: http://api.example.com
        HTTP_METHOD: PUT
        ENDPOINT: /process
        REQUEST_FORMAT: binary
        RESPONSE_CONTENT_PATH: page_content
        RESPONSE_METADATA_PATH: metadata
        RESPONSE_TYPE: object

Backward Compatibility:
    All configuration options have sensible defaults that maintain compatibility
    with the original external loader implementation (PUT to /process with binary data).
"""
import requests
import logging
import os
import json
import base64
from typing import Iterator, List, Union, Dict, Any
from urllib.parse import quote, urlencode

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from open_webui.utils.headers import include_user_info_headers
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class ExternalDocumentLoader(BaseLoader):
    def __init__(
        self,
        file_path,
        url: str,
        api_key: str = None,
        mime_type=None,
        user=None,
        http_method: str = "PUT",
        endpoint: str = "/process",
        request_format: str = "binary",
        file_field_name: str = "file",
        filename_field_name: str = None,
        params: Dict[str, Any] = None,
        query_params: Dict[str, Any] = None,
        custom_headers: Dict[str, str] = None,
        response_content_path: str = "page_content",
        response_metadata_path: str = "metadata",
        response_type: str = "object",
        **kwargs,
    ) -> None:
        """Initialize the external document loader.

        Args:
            file_path: Path to the file to process
            url: Base URL of the external API
            api_key: API key for authentication (optional)
            mime_type: MIME type of the file (optional)
            http_method: HTTP method to use (PUT, POST, PATCH)
            endpoint: API endpoint path
            request_format: Format for sending the file (binary, form-data, json-base64)
            file_field_name: Name of the file field in form-data or JSON
            filename_field_name: Name of the filename field (optional)
            params: Additional parameters to send with the request
            query_params: Query parameters to append to URL
            custom_headers: Custom headers to include in request
            response_content_path: Dot notation path to content in response
            response_metadata_path: Dot notation path to metadata in response
            response_type: Type of response (object, array, text)
        """
        self.url = url
        self.api_key = api_key
        self.user = user
        self.file_path = file_path
        self.mime_type = mime_type

        # Request configuration
        self.http_method = http_method.upper()
        self.endpoint = endpoint
        self.request_format = request_format
        self.file_field_name = file_field_name
        self.filename_field_name = filename_field_name
        self.params = params or {}
        self.query_params = query_params or {}
        self.custom_headers = custom_headers or {}

        # Response configuration
        self.response_content_path = response_content_path
        self.response_metadata_path = response_metadata_path
        self.response_type = response_type

    def _get_nested_value(self, data: Any, path: str, default: Any = None) -> Any:
        """Extract value from nested dict using dot notation or array index.

        Examples:
            data = {"result": {"text": "hello"}}
            _get_nested_value(data, "result.text") -> "hello"

            data = [{"text": "hello"}]
            _get_nested_value(data, "[0].text") -> "hello"
        """
        if not path or data is None:
            return data if data is not None else default

        keys = path.split('.')
        current = data

        for key in keys:
            if not key:
                continue

            # Handle array index notation [0]
            if key.startswith('[') and key.endswith(']'):
                try:
                    index = int(key[1:-1])
                    if isinstance(current, list) and 0 <= index < len(current):
                        current = current[index]
                    else:
                        return default
                except (ValueError, TypeError):
                    return default
            # Handle dict key
            elif isinstance(current, dict):
                current = current.get(key, default)
                if current is default:
                    return default
            else:
                return default

        return current

    def load(self) -> List[Document]:
        """Load and process the document using the external API."""
        # Read file data
        with open(self.file_path, "rb") as f:
            file_data = f.read()

        filename = os.path.basename(self.file_path)

        # Build URL with endpoint and query params
        # Strip whitespace to prevent issues with concatenation
        url = self.url.strip().rstrip('/')
        endpoint = self.endpoint.strip()
        full_url = f"{url}{endpoint}"

        if self.query_params:
            query_string = urlencode(self.query_params)
            full_url = f"{full_url}?{query_string}"

        # Build headers
        headers = {}

        # Add authentication
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # Add custom headers
        headers.update(self.custom_headers)

        if self.user is not None:
            headers = include_user_info_headers(headers, self.user)

        # Prepare request based on format
        files = None
        data = None
        json_payload = None

        if self.request_format == "binary":
            # Raw binary data in body
            data = file_data
            if self.mime_type:
                headers["Content-Type"] = self.mime_type
            # Add filename in header
            try:
                headers["X-Filename"] = quote(filename)
            except:
                pass

        elif self.request_format == "form-data":
            # Multipart form-data
            files = {
                self.file_field_name: (filename, file_data, self.mime_type or 'application/octet-stream')
            }
            # Add additional parameters as form fields
            data = self.params.copy()
            # Add filename as separate field if specified
            if self.filename_field_name:
                data[self.filename_field_name] = filename

        elif self.request_format == "json-base64":
            # JSON body with base64-encoded file
            json_payload = {
                self.file_field_name: base64.b64encode(file_data).decode('utf-8'),
            }
            # Add filename if specified
            if self.filename_field_name:
                json_payload[self.filename_field_name] = filename
            # Add mime type if specified
            if self.mime_type:
                json_payload['mime_type'] = self.mime_type
            # Merge with additional params
            json_payload.update(self.params)
            headers["Content-Type"] = "application/json"

        else:
            raise ValueError(f"Unsupported request format: {self.request_format}")

        # Make the request
        try:
            log.debug(f"Sending {self.http_method} request to {full_url}")

            if self.http_method == "POST":
                response = requests.post(
                    full_url,
                    data=data,
                    files=files,
                    json=json_payload,
                    headers=headers,
                    timeout=300  # 5 minute timeout for large files
                )
            elif self.http_method == "PUT":
                response = requests.put(
                    full_url,
                    data=data,
                    files=files,
                    json=json_payload,
                    headers=headers,
                    timeout=300
                )
            elif self.http_method == "PATCH":
                response = requests.patch(
                    full_url,
                    data=data,
                    files=files,
                    json=json_payload,
                    headers=headers,
                    timeout=300
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {self.http_method}")

        except requests.exceptions.Timeout:
            log.error(f"Request timeout connecting to {full_url}")
            raise Exception(f"Request timeout: External API took too long to respond")
        except requests.exceptions.ConnectionError as e:
            log.error(f"Connection error to {full_url}: {e}")
            raise Exception(f"Connection error: Unable to reach external API at {full_url}")
        except Exception as e:
            log.error(f"Error connecting to endpoint: {e}")
            raise Exception(f"Error connecting to endpoint: {e}")

        # Process response
        if not response.ok:
            log.error(f"API error {response.status_code}: {response.text}")
            raise Exception(
                f"External API error: {response.status_code} {response.text[:200]}"
            )

        # Parse response based on type
        try:
            if self.response_type == "text":
                # Plain text response - entire body is content
                return [
                    Document(
                        page_content=response.text,
                        metadata={"source": filename}
                    )
                ]

            # Parse JSON response
            response_data = response.json()

            if not response_data:
                raise Exception("Error loading document: No content returned")

            if self.response_type == "array":
                # Array of documents
                if not isinstance(response_data, list):
                    raise Exception(f"Expected array response, got {type(response_data)}")

                documents = []
                for item in response_data:
                    content = self._get_nested_value(item, self.response_content_path, "")
                    metadata = self._get_nested_value(item, self.response_metadata_path, {})

                    if not isinstance(metadata, dict):
                        metadata = {"data": metadata}

                    documents.append(
                        Document(
                            page_content=str(content) if content else "",
                            metadata=metadata
                        )
                    )
                return documents

            else:  # response_type == "object"
                # Single document object
                if isinstance(response_data, list):
                    # Legacy support: if response is a list, treat each item as a document
                    documents = []
                    for item in response_data:
                        content = self._get_nested_value(item, self.response_content_path, "")
                        metadata = self._get_nested_value(item, self.response_metadata_path, {})

                        if not isinstance(metadata, dict):
                            metadata = {"data": metadata}

                        documents.append(
                            Document(
                                page_content=str(content) if content else "",
                                metadata=metadata
                            )
                        )
                    return documents

                elif isinstance(response_data, dict):
                    # Extract content and metadata from object
                    content = self._get_nested_value(response_data, self.response_content_path)
                    metadata = self._get_nested_value(response_data, self.response_metadata_path, {})

                    if content is None:
                        raise Exception(f"Content not found at path '{self.response_content_path}'")

                    if not isinstance(metadata, dict):
                        metadata = {"data": metadata}

                    # Add source to metadata if not present
                    if "source" not in metadata:
                        metadata["source"] = filename

                    return [
                        Document(
                            page_content=str(content),
                            metadata=metadata
                        )
                    ]
                else:
                    raise Exception(f"Unexpected response type: {type(response_data)}")

        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON response: {e}")
            raise Exception(f"Invalid JSON response from external API: {e}")
        except Exception as e:
            log.error(f"Error processing response: {e}")
            raise
