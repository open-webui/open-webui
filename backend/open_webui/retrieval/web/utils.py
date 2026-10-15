import socket
import urllib.parse
import validators
from typing import Union, Sequence, Iterator, Optional, Any
import requests

from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document


from open_webui.constants import ERROR_MESSAGES
from open_webui.config import ENABLE_RAG_LOCAL_WEB_FETCH, RAG_WEB_SEARCH_REQUEST_TIMEOUT
from open_webui.env import SRC_LOG_LEVELS

import logging

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def request_json_with_timeout(
    method: str,
    url: str,
    *,
    provider_name: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    data: Any = None,
    json: Any = None,
    timeout_seconds: Optional[int] = None,
) -> dict[str, Any]:
    """Perform a provider API request with shared timeout/error handling and return parsed JSON."""
    timeout = timeout_seconds or RAG_WEB_SEARCH_REQUEST_TIMEOUT.value
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        log.error("%s timeout after %ss", provider_name, timeout)
        raise
    except requests.exceptions.RequestException as e:
        # Exception text and error bodies can echo the request URL (query, API key).
        status_code = e.response.status_code if e.response is not None else None
        log.error(
            "%s request failed: %s (status=%s)",
            provider_name,
            type(e).__name__,
            status_code,
        )
        raise
    except ValueError as e:
        status_code = response.status_code if "response" in locals() else "unknown"
        log.error(
            "%s returned invalid JSON (status=%s): %s",
            provider_name,
            status_code,
            e,
        )
        raise requests.exceptions.RequestException(
            f"{provider_name} returned invalid JSON"
        ) from e


def get_json_with_timeout(
    url: str,
    *,
    provider_name: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout_seconds: Optional[int] = None,
) -> dict[str, Any]:
    """Perform a provider API GET call with shared timeout/error handling and return parsed JSON."""
    return request_json_with_timeout(
        "GET",
        url,
        provider_name=provider_name,
        headers=headers,
        params=params,
        timeout_seconds=timeout_seconds,
    )


def validate_url(url: Union[str, Sequence[str]]):
    if isinstance(url, str):
        if isinstance(validators.url(url), validators.ValidationError):
            raise ValueError(ERROR_MESSAGES.INVALID_URL)
        if not ENABLE_RAG_LOCAL_WEB_FETCH:
            # Local web fetch is disabled, filter out any URLs that resolve to private IP addresses
            parsed_url = urllib.parse.urlparse(url)
            # Get IPv4 and IPv6 addresses
            ipv4_addresses, ipv6_addresses = resolve_hostname(parsed_url.hostname)
            # Check if any of the resolved addresses are private
            # This is technically still vulnerable to DNS rebinding attacks, as we don't control WebBaseLoader
            for ip in ipv4_addresses:
                if validators.ipv4(ip, private=True):
                    raise ValueError(ERROR_MESSAGES.INVALID_URL)
            for ip in ipv6_addresses:
                if validators.ipv6(ip, private=True):
                    raise ValueError(ERROR_MESSAGES.INVALID_URL)
        return True
    elif isinstance(url, Sequence):
        return all(validate_url(u) for u in url)
    else:
        return False


def resolve_hostname(hostname):
    # Get address information
    addr_info = socket.getaddrinfo(hostname, None)

    # Extract IP addresses from address information
    ipv4_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET]
    ipv6_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET6]

    return ipv4_addresses, ipv6_addresses


class SafeWebBaseLoader(WebBaseLoader):
    """WebBaseLoader with enhanced error handling and timeouts for URLs."""

    def __init__(self, *args, request_timeout: Optional[int] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_timeout = request_timeout

    def _scrape(self, url: str, parser: str = None, bs_kwargs: dict = None):
        """Scrape a URL with timeout handling."""
        from bs4 import BeautifulSoup
        import time

        start = time.time()
        timeout = self.request_timeout or RAG_WEB_SEARCH_REQUEST_TIMEOUT.value
        try:
            # Override to add timeout to prevent hanging
            html_doc = self.session.get(url, timeout=timeout)
            elapsed = time.time() - start
            content_length = len(html_doc.content) if html_doc.content else 0
            log.info(
                f"Fetched {url} in {elapsed:.2f}s ({content_length} bytes, status={html_doc.status_code})"
            )
            html_doc.raise_for_status()
        except requests.exceptions.Timeout:
            elapsed = time.time() - start
            log.error(f"Timeout fetching {url} after {elapsed:.2f} seconds")
            raise
        except Exception as e:
            elapsed = time.time() - start
            log.error(f"Error fetching {url} after {elapsed:.2f}s: {e}")
            raise

        return BeautifulSoup(
            html_doc.text, parser or self.default_parser, **(bs_kwargs or {})
        )

    def lazy_load(self) -> Iterator[Document]:
        """Lazy load text from the url(s) in web_path with error handling."""
        for path in self.web_paths:
            try:
                soup = self._scrape(path, bs_kwargs=self.bs_kwargs)
                text = soup.get_text(**self.bs_get_text_kwargs)

                # Build metadata
                metadata = {"source": path}
                if title := soup.find("title"):
                    metadata["title"] = title.get_text()
                if description := soup.find("meta", attrs={"name": "description"}):
                    metadata["description"] = description.get(
                        "content", "No description found."
                    )
                if html := soup.find("html"):
                    metadata["language"] = html.get("lang", "No language found.")

                yield Document(page_content=text, metadata=metadata)
            except requests.exceptions.Timeout:
                log.error(f"Timeout loading content from {path}")
            except Exception as e:
                # Log the error and continue with the next URL
                log.error(f"Error loading {path}: {e}")


def get_web_loader(
    urls: Union[str, Sequence[str]],
    verify_ssl: bool = True,
    requests_per_second: int = 2,
    request_timeout: Optional[int] = None,
):
    # Check if the URL is valid
    if not validate_url(urls):
        raise ValueError(ERROR_MESSAGES.INVALID_URL)
    return SafeWebBaseLoader(
        urls,
        verify_ssl=verify_ssl,
        requests_per_second=requests_per_second,
        continue_on_failure=True,
        request_timeout=request_timeout,
    )
