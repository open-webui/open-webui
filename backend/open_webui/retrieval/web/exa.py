import logging
from dataclasses import dataclass
from typing import Optional

import requests
from open_webui.env import SRC_LOG_LEVELS
from open_webui.retrieval.web.main import SearchResult, get_filtered_results

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

EXA_API_BASE = "https://api.exa.ai"


@dataclass
class ExaResult:
    url: str
    title: str
    text: str


def search_exa(
    api_key: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
    is_allowlist: Optional[bool] = None,
) -> list[SearchResult]:
    """Search using Exa Search API and return the results as a list of SearchResult objects.

    Args:
        api_key (str): A Exa Search API key
        query (str): The query to search for
        count (int): Number of results to return
        filter_list (Optional[list[str]]): List of domains to filter results by
    """
    log.info(f"Searching with Exa for query: {query}")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "query": query,
        "numResults": count or 5,
        # Only use includeDomains when allowlist mode is used
        "includeDomains": filter_list if (is_allowlist is None or is_allowlist) else None,
        "contents": {"text": True, "highlights": True},
        "type": "auto",  # Use the auto search type (keyword or neural)
    }

    try:
        response = requests.post(
            f"{EXA_API_BASE}/search", headers=headers, json=payload
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for result in data["results"]:
            results.append(
                ExaResult(
                    url=result["url"],
                    title=result["title"],
                    text=result["text"],
                )
            )

        log.info(f"Found {len(results)} results")
        # Apply post-filtering if needed (covers blocklist mode)
        if filter_list:
            # Convert to dicts to reuse common filter helper then re-map
            pre = [
                {"url": r.url, "title": r.title, "text": r.text} for r in results
            ]
            pre = get_filtered_results(
                pre,
                filter_list,
                True if is_allowlist is None else is_allowlist,
            )
            results = [
                ExaResult(url=item["url"], title=item.get("title", ""), text=item.get("text", ""))
                for item in pre
            ]

        return [
            SearchResult(
                link=result.url,
                title=result.title,
                snippet=result.text,
            )
            for result in results
        ]
    except Exception as e:
        log.error(f"Error searching Exa: {e}")
        return []
