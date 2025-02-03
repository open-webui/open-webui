import logging
from typing import Optional

from exa_py import Exa
from open_webui.env import SRC_LOG_LEVELS
from open_webui.retrieval.web.main import SearchResult

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_exa(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
) -> list[SearchResult]:
    """Search using Exa Search API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A Exa Search API key
        query (str): The query to search for
    """
    log.info(f"Searching with Exa for query: {query}")
    client = Exa(api_key=api_key)
    results = client.search_and_contents(
        query=query,
        num_results=count or 5,
        include_domains=filter_list,
        # start_published_date=START_DATE,
        # end_published_date=END_DATE,
        # start_crawl_date=START_DATE,
        # end_crawl_date=END_DATE,
        text=True,
        highlights=True,
        type="auto",  # Use the auto search type (keyword or neural)
    )
    log.info(f"Found {len(results.results)} results")
    return [
        SearchResult(
            link=result.url,
            title=result.title,
            snippet=result.text,
        )
        for result in results.results
    ]
