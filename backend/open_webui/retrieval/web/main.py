import validators

from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel


def get_filtered_results(results, filter_list):
    if not filter_list:
        return results

    # Domains starting without "!" → allowed
    allow_list = [d for d in filter_list if not d.startswith("!")]
    # Domains starting with "!" → blocked
    block_list = [d[1:] for d in filter_list if d.startswith("!")]

    filtered_results = []

    for result in results:
        url = result.get("url") or result.get("link", "") or result.get("href", "")
        if not validators.url(url):
            continue

        domain = urlparse(url).netloc

        # If allow list is non-empty, require domain to match one of them
        if allow_list:
            if not any(domain.endswith(allowed) for allowed in allow_list):
                continue

        # Block list always removes matches
        if any(domain.endswith(blocked) for blocked in block_list):
            continue

        filtered_results.append(result)

    return filtered_results


class SearchResult(BaseModel):
    link: str
    title: Optional[str]
    snippet: Optional[str]
