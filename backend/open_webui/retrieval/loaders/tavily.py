import requests
import logging
from typing import Iterator, List, Literal, Union

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

log = logging.getLogger(__name__)


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
        self.api_url = "https://api.tavily.com/extract"

    def lazy_load(self) -> Iterator[Document]:
        """Extract and yield documents from the URLs using Tavily Extract API."""
        batch_size = 20
        for i in range(0, len(self.urls), batch_size):
            batch_urls = self.urls[i : i + batch_size]
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }
                # Use string for single URL, array for multiple URLs
                urls_param = batch_urls[0] if len(batch_urls) == 1 else batch_urls
                payload = {"urls": urls_param, "extract_depth": self.extract_depth}
                # Make the API call
                response = requests.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                response_data = response.json()
                # Process successful results
                for result in response_data.get("results", []):
                    url = result.get("url", "")
                    content = result.get("raw_content", "")
                    if not content:
                        log.warning(f"No content extracted from {url}")
                        continue
                    # Add URLs as metadata
                    metadata = {"source": url}
                    yield Document(
                        page_content=content,
                        metadata=metadata,
                    )
                for failed in response_data.get("failed_results", []):
                    url = failed.get("url", "")
                    error = failed.get("error", "Unknown error")
                    log.error(f"Failed to extract content from {url}: {error}")
            except Exception as e:
                if self.continue_on_failure:
                    log.error(f"Error extracting content from batch {batch_urls}: {e}")
                else:
                    raise e
