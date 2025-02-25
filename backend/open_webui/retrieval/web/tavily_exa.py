import logging
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from open_webui.retrieval.web.tavily import search_tavily
from open_webui.retrieval.web.exa import search_exa
from open_webui.retrieval.web.main import SearchResult
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

def search_tavily_and_exa(
    tavily_api_key: str,
    exa_api_key: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
) -> List[SearchResult]:
    log.debug(f"Searching Tavily and Exa for: {query}")
    """Search using both Tavily and Exa APIs in parallel, combine and deduplicate results"""
    tavily_results = []
    exa_results = []
    
    def tavily_search():
        try:
            return search_tavily(tavily_api_key, query, count / 2 + 1, filter_list)
        except Exception as e:
            log.error(f"Tavily search failed: {str(e)}")
            return []
            
    def exa_search():
        try:
            return search_exa(exa_api_key, query, count / 2, filter_list)
        except Exception as e:
            log.error(f"Exa search failed: {str(e)}")
            return []
    
    # Execute searches in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_search = {
            executor.submit(tavily_search): "tavily",
            executor.submit(exa_search): "exa"
        }
        
        for future in as_completed(future_to_search):
            search_type = future_to_search[future]
            try:
                results = future.result()
                if search_type == "tavily":
                    tavily_results = results
                else:
                    exa_results = results
            except Exception as e:
                log.error(f"{search_type} search failed in thread: {str(e)}")

    # Merge and deduplicate results
    seen_urls = set()
    combined = []
    
    for result in tavily_results + exa_results:
        if result.link not in seen_urls:
            seen_urls.add(result.link)
            combined.append(result)

    log.debug(f"Combined results: {len(combined)}")
    
    return combined[:count]
