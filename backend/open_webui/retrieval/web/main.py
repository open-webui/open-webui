import logging
import socket
import validators

from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel

log = logging.getLogger(__name__)


def resolve_hostname(hostname):
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        ipv4_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET]
        ipv6_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET6]
        return ipv4_addresses, ipv6_addresses
    except Exception as e:
        log.debug(f"Failed to resolve hostname {hostname}: {e}")
        return [], []


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

        if not domain:
            continue

        # Resolve hostname to IPs for comprehensive checking
        ipv4_addresses, ipv6_addresses = resolve_hostname(domain)
        resolved_ips = ipv4_addresses + ipv6_addresses

        # Check all identifiers (hostname + resolved IPs)
        identifiers = [domain] + resolved_ips

        # If allow list is non-empty, require at least one identifier to match
        if allow_list:
            allowed = any(
                identifier == allowed_entry or identifier.endswith("." + allowed_entry)
                for identifier in identifiers
                for allowed_entry in allow_list
            )
            if not allowed:
                continue

        # Block list always blocks matching identifiers
        blocked = any(
            identifier == blocked_entry or identifier.endswith("." + blocked_entry)
            for identifier in identifiers
            for blocked_entry in block_list
        )
        if blocked:
            continue

        filtered_results.append(result)

    return filtered_results


class SearchResult(BaseModel):
    link: str
    title: Optional[str]
    snippet: Optional[str]
