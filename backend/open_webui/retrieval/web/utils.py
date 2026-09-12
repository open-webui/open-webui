import asyncio
import http.cookiejar
import ipaddress
import logging
import socket
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import (
    Any,
    AsyncIterator,
    Dict,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import aiohttp
import certifi
import requests
import urllib3.connection
import urllib3.connectionpool
import validators
from requests.adapters import HTTPAdapter
from fastapi.concurrency import run_in_threadpool
from langchain_community.document_loaders import PlaywrightURLLoader, WebBaseLoader
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document
from open_webui.config import (
    ENABLE_LOCAL_WEB_FETCH,
    EXTERNAL_WEB_LOADER_API_KEY,
    EXTERNAL_WEB_LOADER_URL,
    FIRECRAWL_API_BASE_URL,
    FIRECRAWL_API_KEY,
    FIRECRAWL_TIMEOUT,
    MICROSOFT_WEB_IQ_API_BASE_URL,
    MICROSOFT_WEB_IQ_API_KEY,
    MICROSOFT_WEB_IQ_LANGUAGE,
    PLAYWRIGHT_TIMEOUT,
    PLAYWRIGHT_WS_URL,
    TAVILY_API_KEY,
    TAVILY_EXTRACT_DEPTH,
    WEB_FETCH_FILTER_LIST,
    WEB_LOADER_ENGINE,
    WEB_LOADER_TIMEOUT,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import (
    AIOHTTP_CLIENT_ALLOW_REDIRECTS,
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_SSL_CERT_FILE,
    AIOHTTP_CLIENT_TIMEOUT,
    USER_AGENT,
)
from open_webui.retrieval.loaders.external_web import ExternalWebLoader
from open_webui.retrieval.loaders.microsoft_web_iq import MicrosoftWebIQLoader
from open_webui.retrieval.loaders.tavily import TavilyLoader
from open_webui.retrieval.web.firecrawl import scrape_firecrawl_url
from open_webui.utils.misc import is_host_allowed, is_host_blocked

log = logging.getLogger(__name__)


def resolve_hostname(hostname):
    # Get address information
    addr_info = socket.getaddrinfo(hostname, None)

    # Extract IP addresses from address information
    ipv4_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET]
    ipv6_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET6]

    return ipv4_addresses, ipv6_addresses


def _embedded_ipv4(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> list[ipaddress.IPv4Address]:
    """The IPv4 addresses an IPv6 address carries: mapped, compatible, 6to4, teredo and NAT64."""
    if not isinstance(addr, ipaddress.IPv6Address):
        return []

    embedded = []
    if addr.ipv4_mapped:
        embedded.append(addr.ipv4_mapped)
    if addr.sixtofour:
        embedded.append(addr.sixtofour)
    if addr.teredo:
        embedded.extend(addr.teredo)

    b = addr.packed
    # Prefixes that put the address in the last four bytes: v4-compatible and NAT64 /96.
    if b[:12] in (b'\x00' * 12, b'\x00\x64\xff\x9b' + b'\x00' * 8):
        embedded.append(ipaddress.IPv4Address(b[12:]))
    elif b[:6] == b'\x00\x64\xff\x9b\x00\x01':
        embedded.append(ipaddress.IPv4Address(bytes((b[6], b[7], b[9], b[10]))))

    return embedded


def _assert_host_allowed(host: str | None) -> None:
    if WEB_FETCH_FILTER_LIST and not is_host_allowed(host, WEB_FETCH_FILTER_LIST):
        log.warning(f'Blocked by filter list: {host}')
        raise ValueError(ERROR_MESSAGES.INVALID_URL)


def _assert_addresses_allowed(addresses: Sequence[str]) -> None:
    # An IPv6 address can carry a blocked IPv4 address inside it, so judge both spellings.
    parsed = [ipaddress.ip_address(address) for address in addresses]
    candidates = [*parsed, *(ipv4 for address in parsed for ipv4 in _embedded_ipv4(address))]

    # Block entries only: an allow entry names a host, so judging a resolved address against one
    # would reject every allow-listed host.
    if is_host_blocked([str(address) for address in candidates], WEB_FETCH_FILTER_LIST):
        log.warning(f'Blocked by filter list: {", ".join(str(address) for address in candidates)}')
        raise ValueError(ERROR_MESSAGES.INVALID_URL)

    if not ENABLE_LOCAL_WEB_FETCH:
        for address in candidates:
            if not address.is_global:
                log.warning(f'Blocked non-global address: {address}')
                raise ValueError(ERROR_MESSAGES.INVALID_URL)


def validate_url(url: Union[str, Sequence[str]]):
    if isinstance(url, str):
        if isinstance(validators.url(url), validators.ValidationError):
            raise ValueError(ERROR_MESSAGES.INVALID_URL)

        # Reject parser-confusing chars: urlparse and requests/aiohttp split
        # on these differently, e.g. http://127.0.0.1\@1.1.1.1 → urlparse
        # extracts 1.1.1.1 (public, passes filter) while requests connects
        # to 127.0.0.1 (internal). Same shape with tab/CR/LF.
        if any(ch in url for ch in ('\\', '\t', '\n', '\r')):
            log.warning(f'Blocked URL with parser-confusing char: {url!r}')
            raise ValueError(ERROR_MESSAGES.INVALID_URL)

        parsed_url = urllib.parse.urlparse(url)

        # Protocol validation - only allow http/https
        if parsed_url.scheme not in ['http', 'https']:
            log.warning(f'Blocked non-HTTP(S) protocol: {parsed_url.scheme} in URL: {url}')
            raise ValueError(ERROR_MESSAGES.INVALID_URL)

        # Match on the parsed hostname, not the full URL: a path component would
        # otherwise let any URL slip past a hostname-based block/allow entry.
        _assert_host_allowed(parsed_url.hostname)

        try:
            ipv4_addresses, ipv6_addresses = resolve_hostname(parsed_url.hostname)
        except (socket.gaierror, UnicodeError) as e:
            # With local fetch on, a proxied deployment can carry names only the proxy resolves.
            if not ENABLE_LOCAL_WEB_FETCH:
                log.warning(f'Could not resolve host {parsed_url.hostname}: {e}')
                raise ValueError(ERROR_MESSAGES.INVALID_URL) from None
            ipv4_addresses, ipv6_addresses = [], []

        # A hostname match alone lets a DNS record point at a blocked address.
        # DNS rebinding is mitigated at the connection layer; see _SSRFSafeConnector / _SSRFSafeAdapter
        _assert_addresses_allowed(ipv4_addresses + ipv6_addresses)
        return True
    elif isinstance(url, Sequence):
        return all(validate_url(u) for u in url)
    else:
        return False


def safe_validate_urls(url: Sequence[str]) -> Sequence[str]:
    valid_urls = []
    for u in url:
        try:
            if validate_url(u):
                valid_urls.append(u)
        except Exception as e:
            log.debug('Invalid URL %s: %s', u, e)
            continue
    return valid_urls


def _ssrf_safe_new_conn(self):
    """Resolve DNS, screen every resolved address, connect to one of them.

    Replaces urllib3's _new_conn so the DNS lookup that feeds the actual TCP
    connect is the same one we validate — no second resolution, no rebinding
    window.
    """
    host = getattr(self, '_dns_host', self.host)
    port = self.port
    infos = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
    if not infos:
        raise OSError(f'getaddrinfo for {host!r} returned empty list')
    _assert_addresses_allowed([sa[0] for _, _, _, _, sa in infos])
    err = None
    for fam, typ, proto, _, sa in infos:
        sock = None
        try:
            sock = socket.socket(fam, typ, proto)
            if self.timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(self.timeout)
            if getattr(self, 'source_address', None):
                sock.bind(self.source_address)
            for opt in getattr(self, 'socket_options', None) or ():
                if len(opt) == 4 and isinstance(opt[3], str):
                    # urllib3-future per-protocol form: (level, optname, value, "tcp"/"udp")
                    if opt[3].lower() == 'tcp':
                        sock.setsockopt(*opt[:3])
                    continue
                sock.setsockopt(*opt)
            sock.connect(sa)
            return sock
        except OSError as exc:
            err = exc
            if sock is not None:
                sock.close()
    raise err or OSError(f'connect to {host!r}:{port} failed')


class _SafeHTTPConn(urllib3.connection.HTTPConnection):
    _new_conn = _ssrf_safe_new_conn


class _SafeHTTPSConn(urllib3.connection.HTTPSConnection):
    _new_conn = _ssrf_safe_new_conn


class _SafeHTTPPool(urllib3.connectionpool.HTTPConnectionPool):
    ConnectionCls = _SafeHTTPConn


class _SafeHTTPSPool(urllib3.connectionpool.HTTPSConnectionPool):
    ConnectionCls = _SafeHTTPSConn


class _SSRFSafeAdapter(HTTPAdapter):
    """requests adapter that rejects filter-listed request targets and non-global IPs at connect time."""

    def init_poolmanager(self, *args, **kwargs):
        super().init_poolmanager(*args, **kwargs)
        self.poolmanager.pool_classes_by_scheme = {
            'http': _SafeHTTPPool,
            'https': _SafeHTTPSPool,
        }

    def send(self, request, *args, **kwargs):
        # Per request, not per connection: the connection layer sees the proxy.
        _assert_host_allowed(urllib.parse.urlparse(request.url).hostname)
        return super().send(request, *args, **kwargs)


class _SSRFSafeConnector(aiohttp.TCPConnector):
    """Rejects filter-listed request targets, and non-global IPs on each new connection."""

    async def connect(self, req, traces, timeout):
        # Per request, not per connection: _resolve_host sees the proxy and pooled reuse skips it.
        _assert_host_allowed(req.url.host)
        return await super().connect(req, traces, timeout)

    async def _resolve_host(self, host, port, traces=None):
        # aiohttp answers IP-literal hosts itself without consulting a resolver.
        results = await super()._resolve_host(host, port, traces=traces)
        _assert_addresses_allowed([entry['host'] for entry in results])
        return results


def get_ssrf_safe_session(trust_env: bool = True, store_cookies: bool = True) -> aiohttp.ClientSession:
    """A one-off aiohttp session that re-validates every connection via _SSRFSafeConnector,
    defeating DNS rebinding. Use for validate_url-gated fetches of user-supplied URLs that must
    not use the shared (rebinding-vulnerable) pool. Use as a context manager so it is closed:
    ``async with get_ssrf_safe_session() as session: ...``.

    trust_env also enables environment proxies, and proxied traffic bypasses the connect-time
    IP check, because the proxy resolves the hostname instead.
    """
    return aiohttp.ClientSession(
        connector=_SSRFSafeConnector(),
        timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT),
        trust_env=trust_env,
        cookie_jar=None if store_cookies else aiohttp.DummyCookieJar(),
    )


def get_ssrf_safe_requests_session(trust_env: bool = True, store_cookies: bool = True) -> requests.Session:
    """The requests counterpart of get_ssrf_safe_session, with the same proxy caveat."""
    session = requests.Session()
    session.trust_env = trust_env
    if not store_cookies:
        session.cookies.set_policy(http.cookiejar.DefaultCookiePolicy(allowed_domains=[]))
    session.mount('http://', _SSRFSafeAdapter())
    session.mount('https://', _SSRFSafeAdapter())
    return session


# accept-encoding goes because the client must advertise only codecs it can decode, the rest
# because the client derives them from the URL and body it is actually given. content-encoding
# stays: the browser's body is forwarded byte for byte, so its own labelling still applies.
_DROPPED_REQUEST_HEADERS = {'accept-encoding', 'connection', 'content-length', 'host', 'transfer-encoding'}

# The clients hand us a decoded body, so the sender's framing no longer describes it.
_DROPPED_RESPONSE_HEADERS = {'connection', 'content-encoding', 'content-length', 'transfer-encoding'}


def _forwardable_request_headers(headers: Dict[str, str]) -> Dict[str, str]:
    return {name: value for name, value in headers.items() if name.lower() not in _DROPPED_REQUEST_HEADERS}


def _fulfillable_response_headers(header_pairs: Iterable[Tuple[str, str]]) -> Dict[str, str]:
    """Collapse repeated headers the way route.fulfill expects: set-cookie by newline, rest by comma.

    Takes pairs rather than a mapping because reading either client's headers as a mapping loses
    duplicate Set-Cookie values, leaving one malformed cookie or one of the two.
    """
    collected: Dict[str, List[str]] = {}
    for name, value in header_pairs:
        name = name.lower()  # grouping by the sender's case would split a repeated header
        if name not in _DROPPED_RESPONSE_HEADERS:
            collected.setdefault(name, []).append(value)
    return {name: ('\n' if name == 'set-cookie' else ', ').join(values) for name, values in collected.items()}


def extract_metadata(soup, url):
    metadata = {'source': url}
    if title := soup.find('title'):
        metadata['title'] = title.get_text()
    if description := soup.find('meta', attrs={'name': 'description'}):
        metadata['description'] = description.get('content', 'No description found.')
    if html := soup.find('html'):
        metadata['language'] = html.get('lang', 'No language found.')
    return metadata


def verify_ssl_cert(url: str) -> bool:
    """Verify SSL certificate for the given URL."""
    if not url.startswith('https://'):
        return True

    try:
        hostname = url.split('://')[-1].split('/')[0]
        context = ssl.create_default_context(cafile=certifi.where())
        with context.wrap_socket(ssl.socket(), server_hostname=hostname) as s:
            s.connect((hostname, 443))
        return True
    except ssl.SSLError:
        return False
    except Exception as e:
        log.warning(f'SSL verification failed for {url}: {str(e)}')
        return False


class RateLimitMixin:
    async def _wait_for_rate_limit(self):
        """Wait to respect the rate limit if specified."""
        if self.requests_per_second and self.last_request_time:
            min_interval = timedelta(seconds=1.0 / self.requests_per_second)
            time_since_last = datetime.now() - self.last_request_time
            if time_since_last < min_interval:
                await asyncio.sleep((min_interval - time_since_last).total_seconds())
        self.last_request_time = datetime.now()

    def _sync_wait_for_rate_limit(self):
        """Synchronous version of rate limit wait."""
        if self.requests_per_second and self.last_request_time:
            min_interval = timedelta(seconds=1.0 / self.requests_per_second)
            time_since_last = datetime.now() - self.last_request_time
            if time_since_last < min_interval:
                time.sleep((min_interval - time_since_last).total_seconds())
        self.last_request_time = datetime.now()


class URLProcessingMixin:
    async def _verify_ssl_cert(self, url: str) -> bool:
        """Verify SSL certificate for a URL."""
        return await run_in_threadpool(verify_ssl_cert, url)

    async def _safe_process_url(self, url: str) -> bool:
        """Perform safety checks before processing a URL."""
        if self.verify_ssl and not await self._verify_ssl_cert(url):
            raise ValueError(f'SSL certificate verification failed for {url}')
        await self._wait_for_rate_limit()
        return True

    def _safe_process_url_sync(self, url: str) -> bool:
        """Synchronous version of safety checks."""
        if self.verify_ssl and not verify_ssl_cert(url):
            raise ValueError(f'SSL certificate verification failed for {url}')
        self._sync_wait_for_rate_limit()
        return True


class SafeFireCrawlLoader(BaseLoader, RateLimitMixin, URLProcessingMixin):
    def __init__(
        self,
        web_paths,
        verify_ssl: bool = True,
        trust_env: bool = False,
        requests_per_second: Optional[float] = None,
        continue_on_failure: bool = True,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        timeout: Optional[int] = None,
        mode: Literal['crawl', 'scrape', 'map'] = 'scrape',
        proxy: Optional[Dict[str, str]] = None,
        params: Optional[Dict] = None,
    ):
        proxy_server = proxy.get('server') if proxy else None
        if trust_env and not proxy_server:
            env_proxies = urllib.request.getproxies()
            env_proxy_server = env_proxies.get('https') or env_proxies.get('http')
            if env_proxy_server:
                if proxy:
                    proxy['server'] = env_proxy_server
                else:
                    proxy = {'server': env_proxy_server}
        self.web_paths = web_paths
        self.verify_ssl = verify_ssl
        self.requests_per_second = requests_per_second
        self.last_request_time = None
        self.trust_env = trust_env
        self.continue_on_failure = continue_on_failure
        self.api_key = api_key
        self.api_url = (api_url or 'https://api.firecrawl.dev').rstrip('/')
        self.timeout = timeout
        self.mode = mode
        self.params = params or {}

    def lazy_load(self) -> Iterator[Document]:
        for url in self.web_paths:
            try:
                self._sync_wait_for_rate_limit()
                doc = scrape_firecrawl_url(
                    self.api_url,
                    self.api_key,
                    url,
                    verify_ssl=self.verify_ssl,
                    timeout=self.timeout,
                    params=self.params,
                )
                if doc is not None:
                    yield doc
            except Exception as e:
                if self.continue_on_failure:
                    log.warning(f'Error extracting content from {url} with Firecrawl: {e}')
                    continue
                raise

    async def alazy_load(self):
        for url in self.web_paths:
            try:
                await self._wait_for_rate_limit()
                doc = await run_in_threadpool(
                    scrape_firecrawl_url,
                    self.api_url,
                    self.api_key,
                    url,
                    verify_ssl=self.verify_ssl,
                    timeout=self.timeout,
                    params=self.params,
                )
                if doc is not None:
                    yield doc
            except Exception as e:
                if self.continue_on_failure:
                    log.warning(f'Error extracting content from {url} with Firecrawl: {e}')
                    continue
                raise


class SafeTavilyLoader(BaseLoader, RateLimitMixin, URLProcessingMixin):
    def __init__(
        self,
        web_paths: Union[str, List[str]],
        api_key: str,
        extract_depth: Literal['basic', 'advanced'] = 'basic',
        continue_on_failure: bool = True,
        requests_per_second: Optional[float] = None,
        verify_ssl: bool = True,
        trust_env: bool = False,
        proxy: Optional[Dict[str, str]] = None,
    ):
        """Initialize SafeTavilyLoader with rate limiting and SSL verification support.

        Args:
            web_paths: List of URLs/paths to process.
            api_key: The Tavily API key.
            extract_depth: Depth of extraction ("basic" or "advanced").
            continue_on_failure: Whether to continue if extraction of a URL fails.
            requests_per_second: Number of requests per second to limit to.
            verify_ssl: If True, verify SSL certificates.
            trust_env: If True, use proxy settings from environment variables.
            proxy: Optional proxy configuration.
        """
        # Initialize proxy configuration if using environment variables
        proxy_server = proxy.get('server') if proxy else None
        if trust_env and not proxy_server:
            env_proxies = urllib.request.getproxies()
            env_proxy_server = env_proxies.get('https') or env_proxies.get('http')
            if env_proxy_server:
                if proxy:
                    proxy['server'] = env_proxy_server
                else:
                    proxy = {'server': env_proxy_server}

        # Store parameters for creating TavilyLoader instances
        self.web_paths = web_paths if isinstance(web_paths, list) else [web_paths]
        self.api_key = api_key
        self.extract_depth = extract_depth
        self.continue_on_failure = continue_on_failure
        self.verify_ssl = verify_ssl
        self.trust_env = trust_env
        self.proxy = proxy

        # Add rate limiting
        self.requests_per_second = requests_per_second
        self.last_request_time = None

    def lazy_load(self) -> Iterator[Document]:
        """Load documents with rate limiting support, delegating to TavilyLoader."""
        valid_urls = []
        for url in self.web_paths:
            try:
                self._safe_process_url_sync(url)
                valid_urls.append(url)
            except Exception as e:
                log.warning(f'SSL verification failed for {url}: {str(e)}')
                if not self.continue_on_failure:
                    raise e
        if not valid_urls:
            if self.continue_on_failure:
                log.warning('No valid URLs to process after SSL verification')
                return
            raise ValueError('No valid URLs to process after SSL verification')
        try:
            loader = TavilyLoader(
                urls=valid_urls,
                api_key=self.api_key,
                extract_depth=self.extract_depth,
                continue_on_failure=self.continue_on_failure,
            )
            yield from loader.lazy_load()
        except Exception as e:
            if self.continue_on_failure:
                log.exception(f'Error extracting content from URLs: {e}')
            else:
                raise e

    async def alazy_load(self) -> AsyncIterator[Document]:
        """Async version with rate limiting and SSL verification."""
        valid_urls = []
        for url in self.web_paths:
            try:
                await self._safe_process_url(url)
                valid_urls.append(url)
            except Exception as e:
                log.warning(f'SSL verification failed for {url}: {str(e)}')
                if not self.continue_on_failure:
                    raise e

        if not valid_urls:
            if self.continue_on_failure:
                log.warning('No valid URLs to process after SSL verification')
                return
            raise ValueError('No valid URLs to process after SSL verification')

        try:
            loader = TavilyLoader(
                urls=valid_urls,
                api_key=self.api_key,
                extract_depth=self.extract_depth,
                continue_on_failure=self.continue_on_failure,
            )
            async for document in loader.alazy_load():
                yield document
        except Exception as e:
            if self.continue_on_failure:
                log.exception(f'Error loading URLs: {e}')
            else:
                raise e


class SafeMicrosoftWebIQLoader(BaseLoader, RateLimitMixin, URLProcessingMixin):
    def __init__(
        self,
        web_paths: Union[str, List[str]],
        api_key: str,
        api_base_url: str = MICROSOFT_WEB_IQ_API_BASE_URL,
        language: str = 'en',
        verify_ssl: bool = True,
        trust_env: bool = False,
        requests_per_second: Optional[float] = None,
        continue_on_failure: bool = True,
        timeout: Optional[int] = None,
    ):
        self.web_paths = web_paths if isinstance(web_paths, list) else [web_paths]
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.language = language
        self.verify_ssl = verify_ssl
        self.trust_env = trust_env
        self.requests_per_second = requests_per_second
        self.last_request_time = None
        self.continue_on_failure = continue_on_failure
        self.timeout = timeout

    def lazy_load(self) -> Iterator[Document]:
        valid_urls = []
        for url in self.web_paths:
            try:
                self._safe_process_url_sync(url)
                valid_urls.append(url)
            except Exception as e:
                log.warning(f'SSL verification failed for {url}: {str(e)}')
                if not self.continue_on_failure:
                    raise e
        if not valid_urls:
            if self.continue_on_failure:
                log.warning('No valid URLs to process after SSL verification')
                return
            raise ValueError('No valid URLs to process after SSL verification')

        loader = MicrosoftWebIQLoader(
            urls=valid_urls,
            api_base_url=self.api_base_url,
            api_key=self.api_key,
            language=self.language,
            verify_ssl=self.verify_ssl,
            timeout=self.timeout,
            continue_on_failure=self.continue_on_failure,
        )
        yield from loader.lazy_load()

    async def alazy_load(self) -> AsyncIterator[Document]:
        try:
            docs = await run_in_threadpool(lambda: list(self.lazy_load()))
            for doc in docs:
                yield doc
        except Exception as e:
            if self.continue_on_failure:
                log.warning(f'Error browsing URLs with Microsoft Web IQ: {e}')
            else:
                raise e


class SafePlaywrightURLLoader(PlaywrightURLLoader, RateLimitMixin, URLProcessingMixin):
    """Load HTML pages safely with Playwright, supporting SSL verification, rate limiting, and remote browser connection.

    Attributes:
        web_paths (List[str]): List of URLs to load.
        verify_ssl (bool): If True, verify SSL certificates.
        trust_env (bool): If True, use proxy settings from environment variables.
        requests_per_second (Optional[float]): Number of requests per second to limit to.
        continue_on_failure (bool): If True, continue loading other URLs on failure.
        headless (bool): If True, the browser will run in headless mode.
        proxy (dict): Proxy override settings for the Playwright session. Page requests are
            issued outside the browser, so they follow the environment proxy via trust_env
            rather than this setting.
        playwright_ws_url (Optional[str]): WebSocket endpoint URI for remote browser connection.
        playwright_timeout (Optional[int]): Maximum operation time in milliseconds.
    """

    def __init__(
        self,
        web_paths: List[str],
        verify_ssl: bool = True,
        trust_env: bool = False,
        requests_per_second: Optional[float] = None,
        continue_on_failure: bool = True,
        headless: bool = True,
        remove_selectors: Optional[List[str]] = None,
        proxy: Optional[Dict[str, str]] = None,
        playwright_ws_url: Optional[str] = None,
        playwright_timeout: Optional[int] = 10000,
    ):
        """Initialize with additional safety parameters and remote browser support."""

        proxy_server = proxy.get('server') if proxy else None
        if trust_env and not proxy_server:
            env_proxies = urllib.request.getproxies()
            env_proxy_server = env_proxies.get('https') or env_proxies.get('http')
            if env_proxy_server:
                if proxy:
                    proxy['server'] = env_proxy_server
                else:
                    proxy = {'server': env_proxy_server}

        # We'll set headless to False if using playwright_ws_url since it's handled by the remote browser
        super().__init__(
            urls=web_paths,
            continue_on_failure=continue_on_failure,
            headless=headless if playwright_ws_url is None else False,
            remove_selectors=remove_selectors,
            proxy=proxy,
        )
        self.verify_ssl = verify_ssl
        self.requests_per_second = requests_per_second
        self.last_request_time = None
        self.playwright_ws_url = playwright_ws_url
        self.trust_env = trust_env
        self.playwright_timeout = playwright_timeout

    def _request_timeout(self) -> float:
        # per-hop budget, since page.goto's timeout cannot reach into our own fetch and 0 disables
        # it. aiohttp treats it as a total where requests only caps each read, so sync runs looser.
        return (self.playwright_timeout or 30000) / 1000

    def _requests_verify(self) -> Union[bool, str]:
        """requests takes a CA path where aiohttp takes the parsed SSLContext.

        A bundle named directly in AIOHTTP_CLIENT_SESSION_SSL reaches us already parsed and
        cannot be expressed here, so that form falls back to the global bundle or certifi.
        """
        if not self.verify_ssl or AIOHTTP_CLIENT_SESSION_SSL is False:
            return False
        if AIOHTTP_CLIENT_SESSION_SSL is True:
            return True  # no usable global CA bundle, so both clients land on certifi
        return AIOHTTP_CLIENT_SSL_CERT_FILE or True

    def _intercept_navigation_sync(self, route, session):
        req = route.request

        hop_cookies: List[Tuple[str, str]] = []

        try:
            headers = _forwardable_request_headers(req.all_headers())
            post_data = req.post_data_buffer
            verify, timeout = self._requests_verify(), self._request_timeout()

            # The browser would resolve the hostname again, after the check; fetch it ourselves.
            def fetch(url):
                validate_url(url)
                return session.request(
                    req.method,
                    url,
                    headers=headers,
                    data=post_data,
                    allow_redirects=False,
                    verify=verify,
                    timeout=timeout,
                )

            resp = fetch(req.url)

            if 300 <= resp.status_code < 400:
                for _ in range(20):
                    if not AIOHTTP_CLIENT_ALLOW_REDIRECTS:
                        route.abort()
                        return

                    location = resp.headers.get('location')
                    if not location:
                        break

                    # only the last hop is fulfilled, so carry each hop's cookies to the browser
                    hop_cookies += [('set-cookie', v) for v in resp.raw.headers.getlist('set-cookie')]
                    resp = fetch(urllib.parse.urljoin(resp.url, location))
                    if not 300 <= resp.status_code < 400:
                        break
                else:
                    route.abort()
                    return
        except Exception as e:
            log.debug('Playwright loader could not fetch %s: %s', req.url, e)
            route.abort()
            return

        route.fulfill(
            status=resp.status_code,
            headers=_fulfillable_response_headers(hop_cookies + list(resp.raw.headers.items())),
            body=resp.content,
        )

    async def _intercept_navigation(self, route, session):
        req = route.request

        hop_cookies: List[Tuple[str, str]] = []

        try:
            headers = _forwardable_request_headers(await req.all_headers())
            post_data = req.post_data_buffer

            # The browser would resolve the hostname again, after the check; fetch it ourselves.
            async def fetch(url):
                await run_in_threadpool(validate_url, url)
                response = await session.request(
                    req.method,
                    url,
                    headers=headers,
                    data=post_data,
                    allow_redirects=False,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL if self.verify_ssl else False,
                    timeout=aiohttp.ClientTimeout(total=self._request_timeout()),
                )
                # aiohttp only returns the connection to the pool once the body is buffered
                return response, await response.read()

            resp, body = await fetch(req.url)

            if 300 <= resp.status < 400:
                for _ in range(20):
                    if not AIOHTTP_CLIENT_ALLOW_REDIRECTS:
                        await route.abort()
                        return

                    location = resp.headers.get('location')
                    if not location:
                        break

                    # only the last hop is fulfilled, so carry each hop's cookies to the browser
                    hop_cookies += [('set-cookie', v) for v in resp.headers.getall('Set-Cookie', [])]
                    resp, body = await fetch(urllib.parse.urljoin(str(resp.url), location))
                    if not 300 <= resp.status < 400:
                        break
                else:
                    await route.abort()
                    return
        except Exception as e:
            log.debug('Playwright loader could not fetch %s: %s', req.url, e)
            await route.abort()
            return

        await route.fulfill(
            status=resp.status,
            headers=_fulfillable_response_headers(hop_cookies + list(resp.headers.items())),
            body=body,
        )

    def lazy_load(self) -> Iterator[Document]:
        """Safely load URLs synchronously with support for remote browser."""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # Use remote browser if ws_endpoint is provided, otherwise use local browser
            if self.playwright_ws_url:
                browser = p.chromium.connect(self.playwright_ws_url)
            else:
                browser = p.chromium.launch(headless=self.headless, proxy=self.proxy)

            with browser:
                for url in self.urls:
                    try:
                        self._safe_process_url_sync(url)
                        # opened before the page so it outlives any route still in flight at teardown
                        with (
                            get_ssrf_safe_requests_session(self.trust_env, store_cookies=False) as session,
                            browser.new_page(service_workers='block') as page,
                        ):
                            page.route('**/*', lambda route: self._intercept_navigation_sync(route, session))
                            page.route_web_socket('**/*', lambda ws_route: ws_route.close())
                            response = page.goto(url, timeout=self.playwright_timeout)
                            if response is None:
                                raise ValueError(f'page.goto() returned None for url {url}')

                            text = self.evaluator.evaluate(page, browser, response)
                            metadata = {'source': url}
                            yield Document(page_content=text, metadata=metadata)
                    except Exception as e:
                        if self.continue_on_failure:
                            log.exception(f'Error loading {url}: {e}')
                            continue
                        raise e

    async def alazy_load(self) -> AsyncIterator[Document]:
        """Safely load URLs asynchronously with support for remote browser."""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            # Use remote browser if ws_endpoint is provided, otherwise use local browser
            if self.playwright_ws_url:
                browser = await p.chromium.connect(self.playwright_ws_url)
            else:
                browser = await p.chromium.launch(headless=self.headless, proxy=self.proxy)

            async with browser:
                for url in self.urls:
                    try:
                        await self._safe_process_url(url)
                        # opened before the page so it outlives any route still in flight at teardown
                        async with (
                            get_ssrf_safe_session(self.trust_env, store_cookies=False) as session,
                            await browser.new_page(service_workers='block') as page,
                        ):
                            await page.route('**/*', lambda route: self._intercept_navigation(route, session))
                            await page.route_web_socket('**/*', lambda ws_route: ws_route.close())
                            response = await page.goto(url, timeout=self.playwright_timeout)
                            if response is None:
                                raise ValueError(f'page.goto() returned None for url {url}')

                            text = await self.evaluator.evaluate_async(page, browser, response)
                            metadata = {'source': url}
                            yield Document(page_content=text, metadata=metadata)
                    except Exception as e:
                        if self.continue_on_failure:
                            log.exception(f'Error loading {url}: {e}')
                            continue
                        raise e


class SafeWebBaseLoader(WebBaseLoader):
    """WebBaseLoader with enhanced error handling for URLs."""

    def __init__(self, trust_env: bool = False, *args, **kwargs):
        """Initialize SafeWebBaseLoader
        Args:
            trust_env (bool, optional): set to True if using proxy to make web requests, for example
                using http(s)_proxy environment variables. Defaults to False.
        """
        # lxml parses scraped pages far faster than the html.parser default
        kwargs.setdefault('default_parser', 'lxml')
        super().__init__(*args, **kwargs)
        self.trust_env = trust_env

        # Propagate USER_AGENT env var so that both the sync _scrape() and
        # async _fetch() paths present a real UA instead of python-requests/2.x
        # which gets blocked by Cloudflare, Wikipedia, and similar bot-detection.
        # _fetch() forwards self.session.headers to the aiohttp session, so
        # setting it here covers both code-paths.
        if USER_AGENT:
            self.session.headers['User-Agent'] = USER_AGENT

        # Prevent redirect-based SSRF on the synchronous _scrape() path.
        # validate_url() is called once on the originally-submitted URL, but the
        # parent WebBaseLoader's _scrape() invokes self.session.get(url, **self.requests_kwargs)
        # which by default follows redirects. Without the override below, an attacker
        # can submit a public URL that 302-redirects to an internal address (RFC1918,
        # 127.0.0.1, 169.254.169.254, etc.) and the redirected target is fetched without
        # re-validation. Matches the policy enforced on the async _fetch() path below.
        self.requests_kwargs = {
            **(self.requests_kwargs or {}),
            'allow_redirects': AIOHTTP_CLIENT_ALLOW_REDIRECTS,
        }

        self.session.mount('http://', _SSRFSafeAdapter())
        self.session.mount('https://', _SSRFSafeAdapter())

    async def _fetch(self, url: str, retries: int = 3, cooldown: int = 2, backoff: float = 1.5) -> str:
        connector = _SSRFSafeConnector()
        async with aiohttp.ClientSession(trust_env=self.trust_env, connector=connector) as session:
            for i in range(retries):
                try:
                    kwargs: Dict = dict(
                        headers=self.session.headers,
                        cookies=self.session.cookies.get_dict(),
                    )
                    if not self.session.verify:
                        kwargs['ssl'] = False
                    else:
                        kwargs['ssl'] = AIOHTTP_CLIENT_SESSION_SSL

                    async with session.get(
                        url,
                        **(self.requests_kwargs | kwargs),
                    ) as response:
                        if self.raise_for_status:
                            response.raise_for_status()
                        return await response.text()
                except aiohttp.ClientConnectionError as e:
                    if i == retries - 1:
                        raise
                    else:
                        log.warning(f'Error fetching {url} with attempt {i + 1}/{retries}: {e}. Retrying...')
                        await asyncio.sleep(cooldown * backoff**i)
        raise ValueError('retry count exceeded')

    def _unpack_fetch_results(self, results: Any, urls: List[str], parser: Union[str, None] = None) -> List[Any]:
        """Unpack fetch results into BeautifulSoup objects."""
        from bs4 import BeautifulSoup

        final_results = []
        for i, result in enumerate(results):
            url = urls[i]
            url_parser = parser
            if url_parser is None:
                url_parser = 'xml' if url.endswith('.xml') else self.default_parser
                self._check_parser(url_parser)
            final_results.append(BeautifulSoup(result, url_parser, **self.bs_kwargs))
        return final_results

    def lazy_load(self) -> Iterator[Document]:
        """Lazy load text from the url(s) in web_path with error handling."""
        for path in self.web_paths:
            try:
                soup = self._scrape(path, bs_kwargs=self.bs_kwargs)
                text = soup.get_text(**self.bs_get_text_kwargs)

                # Build metadata
                metadata = extract_metadata(soup, path)

                yield Document(page_content=text, metadata=metadata)
            except Exception as e:
                # Log the error and continue with the next URL
                log.exception(f'Error loading {path}: {e}')

    def _document_from_html(self, html: str, url: str) -> Document:
        """Build one Document."""
        soup = self._unpack_fetch_results([html], [url])[0]
        return Document(
            page_content=soup.get_text(**self.bs_get_text_kwargs),
            metadata=extract_metadata(soup, url),
        )

    async def alazy_load(self) -> AsyncIterator[Document]:
        """Async lazy load text from the url(s) in web_path."""
        results = await self.fetch_all(self.web_paths)
        for path, html in zip(self.web_paths, results):
            # parsing a large page costs hundreds of ms, keep it off the event loop
            yield await asyncio.to_thread(self._document_from_html, html, path)

    async def aload(self) -> list[Document]:
        """Load data into Document objects."""
        return [document async for document in self.alazy_load()]


def get_web_loader(
    urls: Union[str, Sequence[str]],
    verify_ssl: bool = True,
    requests_per_second: int = 2,
    trust_env: bool = False,
    loader_config: Optional[dict] = None,
):
    # Check if the URLs are valid
    safe_urls = safe_validate_urls([urls] if isinstance(urls, str) else urls)

    if not safe_urls:
        log.warning(f'All provided URLs were blocked or invalid: {urls}')
        raise ValueError(ERROR_MESSAGES.INVALID_URL)

    loader_config = loader_config or {}

    def cfg(key, env_value):
        # Admin-saved DB value wins; env constant covers keys never saved.
        value = loader_config.get(key)
        return env_value if value is None else value

    engine = cfg('web_loader_engine', WEB_LOADER_ENGINE)
    web_loader_timeout = cfg('web_loader_timeout', WEB_LOADER_TIMEOUT)

    web_loader_args = {
        'web_paths': safe_urls,
        'verify_ssl': verify_ssl,
        'requests_per_second': requests_per_second,
        'continue_on_failure': True,
        'trust_env': trust_env,
    }

    WebLoaderClass = None

    if engine == '' or engine == 'safe_web':
        WebLoaderClass = SafeWebBaseLoader

        request_kwargs = {}
        if web_loader_timeout:
            try:
                timeout_value = float(web_loader_timeout)
            except ValueError:
                timeout_value = None

            if timeout_value:
                request_kwargs['timeout'] = timeout_value

        if request_kwargs:
            web_loader_args['requests_kwargs'] = request_kwargs

    if engine == 'playwright':
        WebLoaderClass = SafePlaywrightURLLoader
        web_loader_args['playwright_timeout'] = cfg('playwright_timeout', PLAYWRIGHT_TIMEOUT)
        playwright_ws_url = cfg('playwright_ws_url', PLAYWRIGHT_WS_URL)
        if playwright_ws_url:
            web_loader_args['playwright_ws_url'] = playwright_ws_url

    if engine == 'firecrawl':
        WebLoaderClass = SafeFireCrawlLoader
        web_loader_args['api_key'] = cfg('firecrawl_api_key', FIRECRAWL_API_KEY)
        web_loader_args['api_url'] = cfg('firecrawl_api_url', FIRECRAWL_API_BASE_URL)
        firecrawl_timeout = cfg('firecrawl_timeout', FIRECRAWL_TIMEOUT)
        if firecrawl_timeout:
            try:
                web_loader_args['timeout'] = int(firecrawl_timeout)
            except ValueError:
                pass

    if engine == 'tavily':
        WebLoaderClass = SafeTavilyLoader
        web_loader_args['api_key'] = cfg('tavily_api_key', TAVILY_API_KEY)
        web_loader_args['extract_depth'] = cfg('tavily_extract_depth', TAVILY_EXTRACT_DEPTH)

    if engine == 'microsoft_web_iq':
        WebLoaderClass = SafeMicrosoftWebIQLoader
        web_loader_args['api_base_url'] = cfg('microsoft_web_iq_api_base_url', MICROSOFT_WEB_IQ_API_BASE_URL)
        web_loader_args['api_key'] = cfg('microsoft_web_iq_api_key', MICROSOFT_WEB_IQ_API_KEY)
        web_loader_args['language'] = cfg('microsoft_web_iq_language', MICROSOFT_WEB_IQ_LANGUAGE)
        if web_loader_timeout:
            try:
                web_loader_args['timeout'] = int(web_loader_timeout)
            except ValueError:
                pass

    if engine == 'external':
        WebLoaderClass = ExternalWebLoader
        web_loader_args['external_url'] = cfg('external_web_loader_url', EXTERNAL_WEB_LOADER_URL)
        web_loader_args['external_api_key'] = cfg('external_web_loader_api_key', EXTERNAL_WEB_LOADER_API_KEY)

    if WebLoaderClass:
        web_loader = WebLoaderClass(**web_loader_args)

        log.debug(
            'Using WEB_LOADER_ENGINE %s for %s URLs',
            web_loader.__class__.__name__,
            len(safe_urls),
        )

        return web_loader
    else:
        raise ValueError(
            f'Invalid WEB_LOADER_ENGINE: {engine}. '
            "Please set it to 'safe_web', 'playwright', 'firecrawl', 'tavily', 'external', or 'microsoft_web_iq'."
        )
