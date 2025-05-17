import requests
import logging
from typing import Iterator, List, Union

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class ExternalDocumentLoader(BaseLoader):
    def __init__(
        self,
        file_path,
        url: str,
        api_key: str,
        mime_type=None,
        **kwargs,
    ) -> None:
        self.url = url
        self.api_key = api_key

        self.file_path = file_path
        self.mime_type = mime_type

    def load(self) -> list[Document]:
        with open(self.file_path, "rb") as f:
            data = f.read()

        headers = {}
        if self.mime_type is not None:
            headers["Content-Type"] = self.mime_type

        if self.api_key is not None:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = self.url
        if url.endswith("/"):
            url = url[:-1]

        r = requests.put(f"{url}/process", data=data, headers=headers)

        if r.ok:
            res = r.json()

            if res:
                return [
                    Document(
                        page_content=res.get("page_content"),
                        metadata=res.get("metadata"),
                    )
                ]
            else:
                raise Exception("Error loading document: No content returned")
        else:
            raise Exception(f"Error loading document: {r.status_code} {r.text}")
