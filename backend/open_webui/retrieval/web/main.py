from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import validators
from open_webui.utils.misc import is_host_allowed
from pydantic import BaseModel


def resolve_hostname(hostname):
    addr_info = socket.getaddrinfo(hostname, None)
    ipv4_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET]
    ipv6_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET6]
    return ipv4_addresses, ipv6_addresses


def _filter_list_has_ip_literal(filter_list):
    for entry in filter_list or []:
        value = (entry or '').removeprefix('!').strip()
        try:
            ipaddress.ip_address(value)
        except ValueError:
            continue
        return True
    return False


def get_filtered_results(results, filter_list):
    if not filter_list:
        return results

    filtered_results = []
    should_resolve_hostnames = _filter_list_has_ip_literal(filter_list)

    for result in results:
        url = result.get('url') or result.get('link', '') or result.get('href', '')
        if not validators.url(url):
            continue

        domain = urlparse(url).hostname
        if not domain:
            continue

        hostnames = [domain]

        if should_resolve_hostnames:
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
