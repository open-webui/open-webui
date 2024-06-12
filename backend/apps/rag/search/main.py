from typing import Optional
from urllib.parse import urlparse
from pydantic import BaseModel


def filter_by_whitelist(results, whitelist):
    if not whitelist:
        return results
    filtered_results = []
    for result in results:
        domain = urlparse(result["url"]).netloc
        if any(domain.endswith(whitelisted_domain) for whitelisted_domain in whitelist):
            filtered_results.append(result)
    return filtered_results

class SearchResult(BaseModel):
    link: str
    title: Optional[str]
    snippet: Optional[str]
