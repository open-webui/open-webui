import requests
import logging, os
from typing import Iterator, List, Union
from urllib.parse import quote

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from open_webui.utils.headers import include_user_info_headers

log = logging.getLogger(__name__)


def _extract_error_message(value) -> str:
    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts = []
        for item in value:
            message = _extract_error_message(item)
            if message:
                parts.append(message)
        return ' '.join(parts)

    if isinstance(value, dict):
        for key in ('detail', 'message', 'msg'):
            if key in value:
                message = _extract_error_message(value[key])
                if message:
                    return message

        parts = []
        for item in value.values():
            message = _extract_error_message(item)
            if message:
                parts.append(message)
        return ' '.join(parts)

    return ''


class ExternalDocumentLoader(BaseLoader):
    def __init__(
        self,
        file_path,
        url: str,
        api_key: str,
        mime_type=None,
        user=None,
        timeout=30,
        **kwargs,
    ) -> None:
        self.url = url
        self.api_key = api_key

        self.file_path = file_path
        self.mime_type = mime_type
        try:
            timeout_value = int(timeout)
            self.timeout = timeout_value if timeout_value > 0 else 30
        except (TypeError, ValueError):
            self.timeout = 30

        self.user = user

    def load(self) -> List[Document]:
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
            response = requests.put(f'{url}/process', data=data, headers=headers, timeout=self.timeout)
        except requests.Timeout as e:
            log.error(f'External document loader timed out after {self.timeout}s: {e}')
            raise Exception(f'Error connecting to endpoint: timed out after {self.timeout}s')
        except Exception as e:
            log.error(f'Error connecting to endpoint: {e}')
            raise Exception(f'Error connecting to endpoint: {e}')

        if response.ok:
            response_data = response.json()
            if response_data:
                if isinstance(response_data, dict):
                    return [
                        Document(
                            page_content=response_data.get('page_content'),
                            metadata=response_data.get('metadata'),
                        )
                    ]
                elif isinstance(response_data, list):
                    documents = []
                    for document in response_data:
                        documents.append(
                            Document(
                                page_content=document.get('page_content'),
                                metadata=document.get('metadata'),
                            )
                        )
                    return documents
                else:
                    raise Exception('Error loading document: Unable to parse content')

            else:
                raise Exception('Error loading document: No content returned')
        else:
            detail = ''
            if response.status_code == 422:
                try:
                    error_data = response.json()
                    detail = _extract_error_message(error_data)
                except Exception:
                    detail = response.text or ''

                if 'No extractable text' in detail:
                    log.debug(
                        'AUTOFALLBACK: External document loader returned 422 No extractable text for %s; signaling upstream loader to fallback to native parsing.',
                        self.file_path,
                    )

            if not detail:
                try:
                    error_data = response.json()
                    detail = _extract_error_message(error_data)
                except Exception:
                    detail = response.text or response.reason or ''

            safe_detail = ' '.join(detail.split())
            if len(safe_detail) > 500:
                safe_detail = f'{safe_detail[:500]}...'

            if safe_detail:
                raise Exception(f'Error loading document: {response.status_code} {safe_detail}')

            raise Exception(f'Error loading document: {response.status_code}')
