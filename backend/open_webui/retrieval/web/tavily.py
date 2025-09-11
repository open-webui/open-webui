import logging
from typing import Optional

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_tavily(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
    # **kwargs,
) -> list[SearchResult]:
    """Search using Tavily's Search API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A Tavily Search API key
        query (str): The query to search for
        count (int): The number of results to return
        filter_list (Optional[list[str]]): List of allowed domains to search within

    Returns:
        list[SearchResult]: A list of search results
    """
    url = "https://api.tavily.com/search"
    all_results = []
    
    try:
        if filter_list:
            # Search within specific domains using site: syntax
            results_per_domain = max(1, count // len(filter_list))
            
            for domain in filter_list:
                site_query = f"site:{domain} {query}"
                data = {
                    "query": site_query,
                    "api_key": api_key,
                    "search_depth": "advanced",
                    "max_results": results_per_domain
                }
                
                response = requests.post(url, json=data)
                response.raise_for_status()
                json_response = response.json()
                
                domain_results = json_response.get("results", [])
                all_results.extend(domain_results)
        else:
            # Standard search without domain restrictions
            data = {"query": query, "api_key": api_key}
            response = requests.post(url, json=data)
            response.raise_for_status()
            json_response = response.json()
            all_results = json_response.get("results", [])

        # Apply additional filtering as backup (in case site: syntax doesn't work)
        if filter_list:
            all_results = get_filtered_results(all_results, filter_list)

        # Sort by relevance 
        if all_results and "score" in all_results[0]:
            all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

        return [
            SearchResult(
                link=result["url"],
                title=result.get("title", ""),
                snippet=result.get("content"),
                score=result.get("score", 0.1),  # Include real score from Tavily
            )
            for result in all_results[:count]
        ]
        
    except Exception as e:
        log.error(f"Tavily search failed: {e}")
        return []
