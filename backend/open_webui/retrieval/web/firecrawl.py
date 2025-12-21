import logging
from typing import Optional, List, Dict, Any, Union

from open_webui.retrieval.web.main import SearchResult, get_filtered_results


log = logging.getLogger(__name__)


def search_firecrawl(
    firecrawl_url: str,
    firecrawl_api_key: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
    timeout: Optional[Union[str, int]] = None,
    search_args: Dict[str, Any] = {},
) -> List[SearchResult]:
    try:
        from firecrawl import FirecrawlApp

        if timeout is not None and timeout != "" and timeout != " ":
            try:
                timeout = int(timeout)
            except ValueError:
                log.exception(
                    f"Cannot parse into integer FIRECRAWL_TIMEOUT : {timeout}"
                )
                timeout = None
        else:
            timeout = None

        search_args = {"timeout": timeout}

        firecrawl = FirecrawlApp(api_key=firecrawl_api_key, api_url=firecrawl_url)
        response = firecrawl.search(
            query=query,
            limit=count,
            ignore_invalid_urls=True,
            **search_args,
        )
        results = response.web
        if filter_list:
            results = get_filtered_results(results, filter_list)
        results = [
            SearchResult(
                link=result.url,
                title=result.title,
                snippet=result.description,
            )
            for result in results[:count]
        ]
        log.info(f"External search results: {results}")
        return results
    except Exception as e:
        log.error(f"Error in External search: {e}")
        return []
