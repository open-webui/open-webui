import logging
import os
from urllib.parse import quote

import requests
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from open_webui.utils.headers import include_user_info_headers

log = logging.getLogger(__name__)


class ExternalDocumentLoader(BaseLoader):
    def __init__(
        self,
        file_path,
        url: str,
        api_key: str,
        mime_type=None,
        user=None,
        **kwargs,
    ) -> None:
        self.url = url
        self.api_key = api_key

        self.file_path = file_path
        self.mime_type = mime_type

        self.user = user

    def _parse_response_data(self, response_data) -> list[Document]:
        if isinstance(response_data, dict):
            return [
                Document(
                    page_content=response_data.get('page_content') or '',
                    metadata=response_data.get('metadata') or {},
                )
            ]

        if isinstance(response_data, list):
            return [
                Document(
                    page_content=document.get('page_content') or '',
                    metadata=document.get('metadata') or {},
                )
                for document in response_data
            ]

        raise Exception('Error loading document: Unable to parse content')

    def load(self) -> list[Document]:
        with open(self.file_path, 'rb') as f:
            data = f.read()

        headers = {}
        if self.mime_type is not None:
            headers['Content-Type'] = self.mime_type

        if self.api_key is not None:
            headers['Authorization'] = f'Bearer {self.api_key}'

        try:
            headers['X-Filename'] = quote(os.path.basename(self.file_path))
        except Exception:
            pass

        if self.user is not None:
            headers = include_user_info_headers(headers, self.user)

        url = self.url
        if url.endswith('/'):
            url = url[:-1]

        try:
            response = requests.put(f'{url}/process', data=data, headers=headers)
        except Exception as e:
            log.error(f'Error connecting to endpoint: {e}')
            raise Exception(f'Error connecting to endpoint: {e}')

        if response.ok:
            response_data = response.json()
            if response_data:
                return self._parse_response_data(response_data)

            raise Exception('Error loading document: No content returned')

        raise Exception(f'Error loading document: {response.status_code} {response.text}')
