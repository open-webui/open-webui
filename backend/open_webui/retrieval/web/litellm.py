import logging
from typing import Optional, List
from urllib.parse import quote

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.env import SRC_LOG_LEVELS, ENABLE_FORWARD_USER_INFO_HEADERS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def search_litellm(
    litellm_url: str,
    litellm_api_key: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
    user: Optional[object] = None,
    chat_id: Optional[str] = None,
) -> List[SearchResult]:
    try:
        headers = {
            "User-Agent": "Open WebUI (https://github.com/open-webui/open-webui) RAG Bot",
            "Authorization": f"Bearer {litellm_api_key}",
        }

        if ENABLE_FORWARD_USER_INFO_HEADERS and user:
            headers.update(
                {
                    "X-OpenWebUI-User-Email": user.email,
                    "X-OpenWebUI-User-Name": quote(user.name, safe=" "),
                    "X-OpenWebUI-User-Role": user.role,
                    "X-OpenWebUI-User-Id": user.id,
                }
            )
            if chat_id:
                headers["X-OpenWebUI-Chat-Id"] = chat_id

        response = requests.post(
            litellm_url,
            headers=headers,
            json={
                "query": query,
                "count": count,
            },
        )
        response.raise_for_status()
        results = response.json()
        if filter_list:
            results = get_filtered_results(results, filter_list)
        results = [
            SearchResult(
                link=result.get("link"),
                title=result.get("title"),
                snippet=result.get("snippet"),
            )
            for result in results[:count]
        ]
        log.info(f"LiteLLM search results: {results}")
        return results
    except Exception as e:
        log.error(f"Error in LiteLLM search: {e}")
        return []
