import logging
from typing import Iterator, List, Union

import requests
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from open_webui.retrieval.web.custom import render_payload

log = logging.getLogger(__name__)


class CustomWebLoader(BaseLoader):
    def __init__(
        self,
        web_paths: Union[str, List[str]],
        custom_url: str,
        custom_method: str,
        custom_payload: dict,
        custom_api_key: str = '',
        continue_on_failure: bool = True,
        **kwargs,
    ) -> None:
        self.custom_url = custom_url
        self.custom_method = custom_method
        self.custom_payload = custom_payload if isinstance(custom_payload, dict) else {}
        self.custom_api_key = custom_api_key
        self.urls = web_paths if isinstance(web_paths, list) else [web_paths]
        self.continue_on_failure = continue_on_failure

    def lazy_load(self) -> Iterator[Document]:
        if not self.custom_url:
            raise ValueError('Custom web loader URL is not configured')

        method = (self.custom_method or 'POST').strip().upper()
        if method not in ('GET', 'POST'):
            raise ValueError(f'Unsupported HTTP method: {self.custom_method}')

        batch_size = 20
        for i in range(0, len(self.urls), batch_size):
            urls = self.urls[i : i + batch_size]
            try:
                rendered_payload = render_payload(self.custom_payload, {'urls': urls})

                # Keep the default external-loader behavior when no payload is configured.
                if not rendered_payload:
                    rendered_payload = {'urls': urls}

                headers = {
                    # LICENSE covers this Open WebUI user-agent identifier.
                    # Do not alter, remove, obscure, or replace it except as LICENSE permits:
                    # https://docs.openwebui.com/license.
                    'User-Agent': 'Open WebUI (https://github.com/open-webui/open-webui) Custom Web Loader',
                }
                if self.custom_api_key:
                    headers['Authorization'] = f'Bearer {self.custom_api_key}'

                if method == 'GET':
                    response = requests.get(self.custom_url, headers=headers, params=rendered_payload)
                else:
                    response = requests.post(self.custom_url, headers=headers, json=rendered_payload)

                response.raise_for_status()
                results = response.json()
                if isinstance(results, dict):
                    results = [results]

                for result in results:
                    if isinstance(result, str):
                        yield Document(page_content=result)
                    else:
                        yield Document(
                            page_content=result.get('page_content', ''),
                            metadata=result.get('metadata', {}),
                        )
            except Exception as e:
                if self.continue_on_failure:
                    log.error(f'Error extracting content from batch {urls}: {e}')
                else:
                    raise e
