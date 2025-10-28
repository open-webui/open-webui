import requests
import logging
from typing import Iterator, List, Union

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class JinaLoader(BaseLoader):
    """Extract web page content from URLs using Jina Reader API.

    This is a LangChain document loader that uses Jina's Reader API to
    retrieve content from web pages as markdown and return it as Document objects.

    Args:
        urls: URL or list of URLs to extract content from.
        api_key: The Jina API key (optional, for higher rate limits).
        continue_on_failure: Whether to continue if extraction of a URL fails.
    """

    def __init__(
        self,
        urls: Union[str, List[str]],
        api_key: str = "",
        continue_on_failure: bool = True,
    ) -> None:
        """Initialize Jina Reader client.

        Args:
            urls: URL or list of URLs to extract content from.
            api_key: The Jina API key (optional).
            continue_on_failure: Whether to continue if extraction of a URL fails.
        """
        if not urls:
            raise ValueError("At least one URL must be provided.")

        self.api_key = api_key
        self.urls = urls if isinstance(urls, list) else [urls]
        self.continue_on_failure = continue_on_failure

    def lazy_load(self) -> Iterator[Document]:
        """Extract and yield documents from the URLs using Jina Reader API."""
        for url in self.urls:
            try:
                # Jina Reader URL format: https://r.jina.ai/{target_url}
                jina_url = f"https://r.jina.ai/{url}"

                headers = {
                    "X-With-Generated-Alt": "true",
                }

                # Add authorization header if API key is provided
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                # Make the API call
                response = requests.get(jina_url, headers=headers, timeout=30)
                response.raise_for_status()

                content = response.text

                if not content or content.strip() == "":
                    log.warning(f"No content extracted from {url}")
                    continue

                # Add URL as metadata
                metadata = {"source": url}
                yield Document(
                    page_content=content,
                    metadata=metadata,
                )

            except Exception as e:
                if self.continue_on_failure:
                    log.error(f"Error extracting content from {url}: {e}")
                else:
                    raise e
