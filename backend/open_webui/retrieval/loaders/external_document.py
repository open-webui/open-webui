import requests
import logging, os
import base64
import uuid
from pathlib import Path
from typing import List

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from open_webui.env import SRC_LOG_LEVELS
from open_webui.config import PDF_EXTRACT_IMAGES_DIR

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class ExternalDocumentLoader(BaseLoader):
    def __init__(
        self,
        file_path,
        url: str,
        api_key: str,
        mime_type=None,
        extract_images=False,
        **kwargs,
    ) -> None:
        self.url = url
        self.api_key = api_key
        self.file_path = file_path
        self.mime_type = mime_type
        self.extract_images = extract_images

    def load(self) -> tuple[List[Document], List[str]]:
        with open(self.file_path, "rb") as f:
            data = f.read()

        headers = {}
        if self.mime_type is not None:
            headers["Content-Type"] = self.mime_type

        if self.api_key is not None:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            headers["X-Filename"] = os.path.basename(self.file_path)
        except:
            pass

        if self.extract_images:
            headers["X-Extract-Images"] = "true"

        url = self.url.rstrip("/")

        try:
            response = requests.put(f"{url}/process", data=data, headers=headers)
        except Exception as e:
            log.error(f"Error connecting to endpoint: {e}")
            raise Exception(f"Error connecting to endpoint: {e}")

        if response.ok:
            response_data = response.json()
            if not response_data:
                raise Exception("Error loading document: No content returned")
            
            all_image_refs = []

            def process_doc_data(doc_data):
                metadata = doc_data.get("metadata", {}) or {}

                if self.extract_images and "images" in doc_data:
                    images_data = doc_data.get("images", [])
                    for b64_image in images_data:
                        try:
                            img_format = "png"
                            if b64_image.startswith("data:image/jpeg;base64,"):
                                img_format = "jpeg"
                                _, b64_image = b64_image.split(",", 1)
                            elif b64_image.startswith("data:image/png;base64,"):
                                img_format = "png"
                                _, b64_image = b64_image.split(",", 1)

                            image_data = base64.b64decode(b64_image)
                            image_filename = f"{uuid.uuid4()}.{img_format}"
                            image_path = Path(PDF_EXTRACT_IMAGES_DIR) / image_filename

                            with open(image_path, "wb") as img_file:
                                img_file.write(image_data)

                            relative_path = f"images/{image_filename}"
                            all_image_refs.append(relative_path)
                            log.info(f"Saved image to {image_path}, ref: {relative_path}")
                        except Exception as e:
                            log.error(f"Could not save extracted image: {e}")

                return Document(
                    page_content=doc_data.get("page_content"),
                    metadata=metadata
                )

            docs = []
            if isinstance(response_data, dict):
                docs = [process_doc_data(response_data)]
            elif isinstance(response_data, list):
                docs = [process_doc_data(doc) for doc in response_data]
            else:
                raise Exception("Error loading document: Unable to parse content")
            
            log.info(f"Returning {len(docs)} documents and {len(all_image_refs)} image refs")
            return docs, all_image_refs
        
        else:
            raise Exception(
                f"Error loading document: {response.status_code} {response.text}"
            )