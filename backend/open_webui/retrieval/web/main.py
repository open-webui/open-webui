from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

import validators
from open_webui.retrieval.web.utils import resolve_hostname
from open_webui.utils.misc import as_network, get_allow_block_lists, is_host_allowed
from pydantic import BaseModel, Field, model_validator


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
    title: str | None = None
    snippet: str | None = None
    name: str | None = None
    publisher: list[str] = Field(default_factory=list)
    display_name: str | None = None

    @model_validator(mode='after')
    def normalize_citation_fields(self):
        self.title = _clean_string(self.title)
        self.name = _clean_string(self.name) or self.title
        self.publisher = normalize_publishers(self.publisher)
        if not self.publisher:
            hostname = get_public_site_identity(self.link)
            if hostname:
                self.publisher = [hostname]
        self.display_name = (
            _clean_string(self.display_name)
            or (self.publisher[0] if self.publisher else None)
            or self.name
            or self.title
        )
        return self

    @classmethod
    def from_provider_result(cls, result: dict) -> SearchResult:
        """Normalize common provider result schemas into the web citation contract."""
        link = result.get('link') or result.get('url') or result.get('href') or ''
        title = result.get('title') or result.get('name')
        snippet = (
            result.get('snippet')
            or result.get('body')
            or result.get('content')
            or result.get('description')
            or result.get('summary')
        )
        publisher = next(
            (
                result.get(key)
                for key in ('publisher', 'siteName', 'site_name', 'source_name')
                if result.get(key) is not None
            ),
            None,
        )
        if publisher is None:
            source = result.get('source')
            if isinstance(source, dict):
                publisher = source
            elif isinstance(source, str) and not _looks_like_url(source) and len(source) <= 200:
                publisher = source

        return cls(
            link=link,
            title=title,
            snippet=snippet,
            name=title,
            publisher=normalize_publishers(publisher),
        )


def _clean_string(value) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _looks_like_url(value: str) -> bool:
    try:
        return urlparse(value).scheme in ('http', 'https')
    except (TypeError, ValueError):
        return False


def normalize_publishers(value) -> list[str]:
    """Use the same normalized publisher shape as MCP citations: list[str]."""
    values = value if isinstance(value, list) else [value]
    publishers = []
    for item in values:
        name = item.get('name') if isinstance(item, dict) else item
        name = _clean_string(name)
        if name and name not in publishers:
            publishers.append(name)
    return publishers


def get_public_site_identity(url: str) -> str | None:
    """Return a conservative site label for a public HTTP(S) hostname."""
    try:
        parsed = urlparse(url)
        hostname = (parsed.hostname or '').rstrip('.').lower()
        if parsed.scheme not in ('http', 'https') or not hostname:
            return None
        if hostname == 'localhost' or hostname.endswith(('.local', '.internal', '.localdomain', '.home.arpa')):
            return None
        try:
            ipaddress.ip_address(hostname)
            return None
        except ValueError:
            pass
        if '.' not in hostname:
            return None
        return hostname.removeprefix('www.')
    except (TypeError, ValueError):
        return None


def web_search_result_metadata(result: SearchResult, metadata: dict | None = None) -> dict:
    """Merge normalized citation fields without changing the source matching key."""
    metadata = dict(metadata or {})
    title = result.title or _clean_string(metadata.get('title'))
    name = result.name or title or _clean_string(metadata.get('name'))
    publisher = result.publisher or normalize_publishers(metadata.get('publisher'))
    display_name = (publisher[0] if publisher else None) or name or title

    return {
        **metadata,
        'source': metadata.get('source') or result.link,
        'link': result.link,
        'url': result.link,
        'title': title,
        'name': name,
        'publisher': publisher,
        'display_name': display_name,
        **({'snippet': result.snippet} if result.snippet is not None else {}),
    }
