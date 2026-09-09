from __future__ import annotations

from urllib.parse import urlparse

import validators
from open_webui.retrieval.web.utils import resolve_hostname
from open_webui.utils.misc import as_network, get_allow_block_lists, is_host_allowed
from pydantic import BaseModel


def get_filtered_results(results, filter_list):
    if not filter_list:
        return results

    allow_list, block_list = get_allow_block_lists(filter_list)
    # Only worth a lookup when an entry names an address, since a hostname entry matches by name.
    resolve_ips = any(as_network(entry) is not None for entry in allow_list + block_list)

    filtered_results = []

    for result in results:
        url = result.get('url') or result.get('link', '') or result.get('href', '')
        if not validators.url(url):
            continue

        domain = urlparse(url).hostname
        if not domain:
            continue

        hostnames = [domain]

        if resolve_ips:
            try:
                ipv4_addresses, ipv6_addresses = resolve_hostname(domain)
                hostnames.extend(ipv4_addresses)
                hostnames.extend(ipv6_addresses)
            except Exception:
                pass

        if is_host_allowed(hostnames, filter_list):
            filtered_results.append(result)
            continue

    return filtered_results


class SearchResult(BaseModel):
    link: str
    title: str | None
    snippet: str | None
