import logging
from dataclasses import dataclass
from typing import Optional

import requests
from open_webui.env import SRC_LOG_LEVELS
from open_webui.retrieval.web.main import SearchResult

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
        "includeDomains": filter_list,
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
