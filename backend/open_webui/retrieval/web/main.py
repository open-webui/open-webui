import validators

from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel

from open_webui.retrieval.web.utils import resolve_hostname
from open_webui.utils.misc import is_string_allowed


def get_filtered_results(results, filter_list):
    if not filter_list:
        return results

    filtered_results = []

    for result in results:
        url = result.get("url") or result.get("link", "") or result.get("href", "")
        if not validators.url(url):
            continue

        domain = urlparse(url).netloc
        if not domain:
            continue

        hostnames = [domain]

        try:
            ipv4_addresses, ipv6_addresses = resolve_hostname(domain)
            hostnames.extend(ipv4_addresses)
            hostnames.extend(ipv6_addresses)
        except Exception:
            pass

        if is_string_allowed(hostnames, filter_list):
            filtered_results.append(result)
            continue

    return filtered_results


class SearchResult(BaseModel):
    link: str
    title: Optional[str]
    snippet: Optional[str]
