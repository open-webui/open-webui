import requests
import logging
from typing import Iterator, List, Union

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

log = logging.getLogger(__name__)


class ExternalWebLoader(BaseLoader):
    def __init__(
        self,
        web_paths: Union[str, List[str]],
        external_url: str,
        external_api_key: str,
        continue_on_failure: bool = True,
        **kwargs,
    ) -> None:
        self.external_url = external_url
        self.external_api_key = external_api_key
        self.urls = web_paths if isinstance(web_paths, list) else [web_paths]
        self.continue_on_failure = continue_on_failure

    def lazy_load(self) -> Iterator[Document]:
        batch_size = 20
        for i in range(0, len(self.urls), batch_size):
            urls = self.urls[i : i + batch_size]
            try:
                response = requests.post(
                    self.external_url,
                    headers={
                        "User-Agent": "Open WebUI (https://github.com/open-webui/open-webui) External Web Loader",
                        "Authorization": f"Bearer {self.external_api_key}",
                    },
                    json={
                        "urls": urls,
                    },
                )
                response.raise_for_status()
                results = response.json()
                for result in results:
                    yield Document(
                        page_content=result.get("page_content", ""),
                        metadata=result.get("metadata", {}),
                    )
            except Exception as e:
                if self.continue_on_failure:
                    log.error(f"Error extracting content from batch {urls}: {e}")
                else:
                    raise e
