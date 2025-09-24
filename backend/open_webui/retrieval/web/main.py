import validators

from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel


def get_filtered_results(results, filter_list):
    if not filter_list:
        return results
    filtered_results = []
    for result in results:
        url = result.get("url") or result.get("link", "")
        if not validators.url(url):
            continue
        domain = urlparse(url).netloc
        if any(domain.endswith(filtered_domain) for filtered_domain in filter_list):
            filtered_results.append(result)
    return filtered_results


def apply_blocklist(results, blocklist):
    """Apply blocklist to filter out specific URLs"""
    if not blocklist:
        return results
    filtered_results = []
    for result in results:
        url = result.get("url") or result.get("link", "")
        if not validators.url(url):
            continue
        # Check if URL starts with any blocked URL
        is_blocked = any(url.startswith(blocked_url) for blocked_url in blocklist)
        if not is_blocked:
            filtered_results.append(result)
    return filtered_results


class SearchResult(BaseModel):
    link: str
    title: Optional[str]
    snippet: Optional[str]
    score: Optional[float] = 0.1
