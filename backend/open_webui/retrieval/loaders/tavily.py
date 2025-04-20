import requests
import logging
from typing import Iterator, List, Literal, Union

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from open_webui.env import SRC_LOG_LEVELS

import tavily

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


class TavilyLoader(BaseLoader):
    """Extract web page content from URLs using Tavily Extract API.

    This is a LangChain document loader that uses Tavily's Extract API to
    retrieve content from web pages and return it as Document objects.

    Args:
        urls: URL or list of URLs to extract content from.
        api_key: The Tavily API key.
        extract_depth: Depth of extraction, either "basic" or "advanced".
        continue_on_failure: Whether to continue if extraction of a URL fails.
    """

    def __init__(
        self,
        urls: Union[str, List[str]],
        api_key: str,
        extract_depth: Literal["basic", "advanced"] = "basic",
        continue_on_failure: bool = True,
    ) -> None:
        """Initialize Tavily Extract client.

        Args:
            urls: URL or list of URLs to extract content from.
            api_key: The Tavily API key.
            include_images: Whether to include images in the extraction.
            extract_depth: Depth of extraction, either "basic" or "advanced".
                advanced extraction retrieves more data, including tables and
                embedded content, with higher success but may increase latency.
                basic costs 1 credit per 5 successful URL extractions,
                advanced costs 2 credits per 5 successful URL extractions.
            continue_on_failure: Whether to continue if extraction of a URL fails.
        """
        if not urls:
            raise ValueError("At least one URL must be provided.")

        self.api_key = api_key
        self.urls = urls if isinstance(urls, list) else [urls]
        self.extract_depth = extract_depth
        self.continue_on_failure = continue_on_failure

    def lazy_load(self) -> Iterator[Document]:
        """Extract and yield documents from the URLs using Tavily Extract API."""
        tavily_client = tavily.TavilyClient(api_key=self.api_key)
        response = tavily_client.extract(self.urls, extract_depth=self.extract_depth)
        results = response.get("results", [])
        for result in results:
            yield Document(
                page_content=result["raw_content"],
                metadata={
                    "source": result["url"],
                },
            )
