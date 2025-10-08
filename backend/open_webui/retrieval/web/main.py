import validators

from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel


def get_filtered_results(results, filter_list, block_list=None):
    if not filter_list and not block_list:
        return results
    filtered_results = []
    for result in results:
        url = result.get("url") or result.get("link", "") or result.get("href", "")
        if not validators.url(url):
            continue
        domain = urlparse(url).netloc
        
        # Check if domain is in block list (exclude if found)
        if block_list and any(domain.endswith(blocked_domain) for blocked_domain in block_list):
            continue
            
        # Check if filter list is provided (include only if found)
        if filter_list:
            if any(domain.endswith(filtered_domain) for filtered_domain in filter_list):
                filtered_results.append(result)
        else:
            # No filter list, so include all results not in block list
            filtered_results.append(result)
    return filtered_results


class SearchResult(BaseModel):
    link: str
    title: Optional[str]
    snippet: Optional[str]
