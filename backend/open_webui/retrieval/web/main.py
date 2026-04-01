from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel


def _validators():
    import validators

    return validators


def _resolve_hostname(hostname):
    from open_webui.retrieval.web.utils import resolve_hostname

    return resolve_hostname(hostname)


def _is_string_allowed(string, filter_list):
    from open_webui.utils.misc import is_string_allowed

    return is_string_allowed(string, filter_list)


def get_filtered_results(results, filter_list):
    if not filter_list:
        return results

    filtered_results = []
    validators = _validators()

    for result in results:
        url = result.get('url') or result.get('link', '') or result.get('href', '')
        if not validators.url(url):
            continue

        domain = urlparse(url).netloc
        if not domain:
            continue

        hostnames = [domain]

        try:
            ipv4_addresses, ipv6_addresses = _resolve_hostname(domain)
            hostnames.extend(ipv4_addresses)
            hostnames.extend(ipv6_addresses)
        except Exception:
            pass

        if _is_string_allowed(hostnames, filter_list):
            filtered_results.append(result)
            continue

    return filtered_results


class SearchResult(BaseModel):
    link: str
    title: Optional[str]
    snippet: Optional[str]
