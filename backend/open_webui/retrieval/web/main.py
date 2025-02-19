import logging
import validators

from typing import Optional, List
from urllib.parse import urlparse
from open_webui.env import SRC_LOG_LEVELS

from pydantic import BaseModel, Extra

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

class SearchParameters(BaseModel, extra=Extra.allow):
    query: str
    count : int
    domains_allow : Optional[list] = None
    domains_block : Optional[list] = None


def get_filtered_results(results, params : SearchParameters):
    if not params.domains_allow and not params.domains_block:
        return results
    filtered_results = []
    for result in results:
        url = result.get("url") or result.get("link", "")
        if not validators.url(url):
            continue
        domain = urlparse(url).netloc
        if ((
                not params.domains_allow or
                any(domain.endswith(filtered_domain) for filtered_domain in params.domains_allow)
            )
            and 
            (
                not params.domains_block or
                not any(domain.endswith(filtered_domain) for filtered_domain in params.domains_block)
            )
        ):
            filtered_results.append(result)
            log.debug(f"Adding search result {url}")
        else:
            log.debug(f"Skipping search result {url}")
    diff_results = len(results) - len(filtered_results)
    if diff_results > 0:        
        left_results = len(results)
        log.info(f"Filtered out {diff_results} search results. {left_results} results left")
    return filtered_results


class SearchResult(BaseModel):
    link: str
    title: Optional[str]
    snippet: Optional[str]
