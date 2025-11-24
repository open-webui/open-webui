import asyncio
import logging
import socket
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, time, timedelta
from typing import (
    Any,
    AsyncIterator,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Union,
    Literal,
)

from fastapi.concurrency import run_in_threadpool
import aiohttp
import certifi
import validators
from langchain_community.document_loaders import PlaywrightURLLoader, WebBaseLoader
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document

from open_webui.retrieval.loaders.tavily import TavilyLoader
from open_webui.retrieval.loaders.external_web import ExternalWebLoader
from open_webui.constants import ERROR_MESSAGES
from open_webui.config import (
    ENABLE_RAG_LOCAL_WEB_FETCH,
    PLAYWRIGHT_WS_URL,
    PLAYWRIGHT_TIMEOUT,
    WEB_LOADER_ENGINE,
    FIRECRAWL_API_BASE_URL,
    FIRECRAWL_API_KEY,
    TAVILY_API_KEY,
    TAVILY_EXTRACT_DEPTH,
    EXTERNAL_WEB_LOADER_URL,
    EXTERNAL_WEB_LOADER_API_KEY,
    WEB_FETCH_FILTER_LIST,
)
from open_webui.env import SRC_LOG_LEVELS


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def resolve_hostname(hostname):
    # Get address information
    addr_info = socket.getaddrinfo(hostname, None)

    # Extract IP addresses from address information
    ipv4_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET]
    ipv6_addresses = [info[4][0] for info in addr_info if info[0] == socket.AF_INET6]

    return ipv4_addresses, ipv6_addresses


def get_allow_block_lists(filter_list):
    allow_list = []
    block_list = []

    if filter_list:
        for d in filter_list:
            if d.startswith("!"):
                # Domains starting with "!" → blocked
                block_list.append(d[1:])
            else:
                # Domains starting without "!" → allowed
                allow_list.append(d)

    return allow_list, block_list


def is_string_allowed(string: str, filter_list: Optional[list[str]] = None) -> bool:
    if not filter_list:
        return True

    allow_list, block_list = get_allow_block_lists(filter_list)
    # If allow list is non-empty, require domain to match one of them
    if allow_list:
        if not any(string.endswith(allowed) for allowed in allow_list):
            return False

    # Block list always removes matches
    if any(string.endswith(blocked) for blocked in block_list):
        return False

    return True


def validate_url(url: Union[str, Sequence[str]]):
    if isinstance(url, str):
        if isinstance(validators.url(url), validators.ValidationError):
            raise ValueError(ERROR_MESSAGES.INVALID_URL)

        parsed_url = urllib.parse.urlparse(url)

        # Protocol validation - only allow http/https
        if parsed_url.scheme not in ["http", "https"]:
            log.warning(
                f"Blocked non-HTTP(S) protocol: {parsed_url.scheme} in URL: {url}"
            )
            raise ValueError(ERROR_MESSAGES.INVALID_URL)

        # Blocklist check using unified filtering logic
        if WEB_FETCH_FILTER_LIST:
            if not is_string_allowed(url, WEB_FETCH_FILTER_LIST):
                log.warning(f"URL blocked by filter list: {url}")
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


def safe_validate_urls(url: Sequence[str]) -> Sequence[str]:
    valid_urls = []
    for u in url:
        try:
            if validate_url(u):
                valid_urls.append(u)
        except Exception as e:
            log.debug(f"Invalid URL {u}: {str(e)}")
            continue
    return valid_urls


def extract_metadata(soup, url):
    metadata = {"source": url}
    if title := soup.find("title"):
        metadata["title"] = title.get_text()
    if description := soup.find("meta", attrs={"name": "description"}):
        metadata["description"] = description.get("content", "No description found.")
    if html := soup.find("html"):
        metadata["language"] = html.get("lang", "No language found.")
    return metadata


def verify_ssl_cert(url: str) -> bool:
    """Verify SSL certificate for the given URL."""
    if not url.startswith("https://"):
        return True

    try:
        hostname = url.split("://")[-1].split("/")[0]
        context = ssl.create_default_context(cafile=certifi.where())
        with context.wrap_socket(ssl.socket(), server_hostname=hostname) as s:
            s.connect((hostname, 443))
        return True
    except ssl.SSLError:
        return False
    except Exception as e:
        log.warning(f"SSL verification failed for {url}: {str(e)}")
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
            raise ValueError(f"SSL certificate verification failed for {url}")
        await self._wait_for_rate_limit()
        return True

    def _safe_process_url_sync(self, url: str) -> bool:
        """Synchronous version of safety checks."""
        if self.verify_ssl and not self._verify_ssl_cert(url):
            raise ValueError(f"SSL certificate verification failed for {url}")
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
        mode: Literal["crawl", "scrape", "map"] = "scrape",
        proxy: Optional[Dict[str, str]] = None,
        params: Optional[Dict] = None,
    ):
        """Concurrent document loader for FireCrawl operations.

        Executes multiple FireCrawlLoader instances concurrently using thread pooling
        to improve bulk processing efficiency.
        Args:
            web_paths: List of URLs/paths to process.
            verify_ssl: If True, verify SSL certificates.
            trust_env: If True, use proxy settings from environment variables.
            requests_per_second: Number of requests per second to limit to.
            continue_on_failure (bool): If True, continue loading other URLs on failure.
            api_key: API key for FireCrawl service. Defaults to None
                (uses FIRE_CRAWL_API_KEY environment variable if not provided).
            api_url: Base URL for FireCrawl API. Defaults to official API endpoint.
            mode: Operation mode selection:
                - 'crawl': Website crawling mode
                - 'scrape': Direct page scraping (default)
                - 'map': Site map generation
            proxy: Proxy override settings for the FireCrawl API.
            params: The parameters to pass to the Firecrawl API.
                For more details, visit: https://docs.firecrawl.dev/sdks/python#batch-scrape
        """
        proxy_server = proxy.get("server") if proxy else None
        if trust_env and not proxy_server:
            env_proxies = urllib.request.getproxies()
            env_proxy_server = env_proxies.get("https") or env_proxies.get("http")
            if env_proxy_server:
                if proxy:
                    proxy["server"] = env_proxy_server
                else:
                    proxy = {"server": env_proxy_server}
        self.web_paths = web_paths
        self.verify_ssl = verify_ssl
        self.requests_per_second = requests_per_second
        self.last_request_time = None
        self.trust_env = trust_env
        self.continue_on_failure = continue_on_failure
        self.api_key = api_key
        self.api_url = api_url
        self.mode = mode
        self.params = params or {}

    def lazy_load(self) -> Iterator[Document]:
        """Load documents using FireCrawl batch_scrape."""
        log.debug(
            "Starting FireCrawl batch scrape for %d URLs, mode: %s, params: %s",
            len(self.web_paths),
            self.mode,
            self.params,
        )
        try:
            from firecrawl import FirecrawlApp

            firecrawl = FirecrawlApp(api_key=self.api_key, api_url=self.api_url)
            result = firecrawl.batch_scrape(
                self.web_paths,
                formats=["markdown"],
                skip_tls_verification=not self.verify_ssl,
                ignore_invalid_urls=True,
                remove_base64_images=True,
                max_age=300000,  # 5 minutes https://docs.firecrawl.dev/features/fast-scraping#common-maxage-values
                wait_timeout=len(self.web_paths) * 3,
                **self.params,
            )

            if result.status != "completed":
                raise RuntimeError(
                    f"FireCrawl batch scrape did not complete successfully. result: {result}"
                )

            for data in result.data:
                metadata = data.metadata or {}
                yield Document(
                    page_content=data.markdown or "",
                    metadata={"source": metadata.url or metadata.source_url or ""},
                )

        except Exception as e:
            if self.continue_on_failure:
                log.exception(f"Error extracting content from URLs: {e}")
            else:
                raise e

    async def alazy_load(self):
        """Async version of lazy_load."""
        log.debug(
            "Starting FireCrawl batch scrape for %d URLs, mode: %s, params: %s",
            len(self.web_paths),
            self.mode,
            self.params,
        )
        try:
            from firecrawl import FirecrawlApp

            firecrawl = FirecrawlApp(api_key=self.api_key, api_url=self.api_url)
            result = firecrawl.batch_scrape(
                self.web_paths,
                formats=["markdown"],
                skip_tls_verification=not self.verify_ssl,
                ignore_invalid_urls=True,
                remove_base64_images=True,
                max_age=300000,  # 5 minutes https://docs.firecrawl.dev/features/fast-scraping#common-maxage-values
                wait_timeout=len(self.web_paths) * 3,
                **self.params,
            )

            if result.status != "completed":
                raise RuntimeError(
                    f"FireCrawl batch scrape did not complete successfully. result: {result}"
                )

            for data in result.data:
                metadata = data.metadata or {}
                yield Document(
                    page_content=data.markdown or "",
                    metadata={"source": metadata.url or metadata.source_url or ""},
                )

        except Exception as e:
            if self.continue_on_failure:
                log.exception(f"Error extracting content from URLs: {e}")
            else:
                raise e


class SafeTavilyLoader(BaseLoader, RateLimitMixin, URLProcessingMixin):
    def __init__(
        self,
        web_paths: Union[str, List[str]],
        api_key: str,
        extract_depth: Literal["basic", "advanced"] = "basic",
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
        proxy_server = proxy.get("server") if proxy else None
        if trust_env and not proxy_server:
            env_proxies = urllib.request.getproxies()
            env_proxy_server = env_proxies.get("https") or env_proxies.get("http")
            if env_proxy_server:
                if proxy:
                    proxy["server"] = env_proxy_server
                else:
                    proxy = {"server": env_proxy_server}

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
                log.warning(f"SSL verification failed for {url}: {str(e)}")
                if not self.continue_on_failure:
                    raise e
        if not valid_urls:
            if self.continue_on_failure:
                log.warning("No valid URLs to process after SSL verification")
                return
            raise ValueError("No valid URLs to process after SSL verification")
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
                log.exception(f"Error extracting content from URLs: {e}")
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
                log.warning(f"SSL verification failed for {url}: {str(e)}")
                if not self.continue_on_failure:
                    raise e

        if not valid_urls:
            if self.continue_on_failure:
                log.warning("No valid URLs to process after SSL verification")
                return
            raise ValueError("No valid URLs to process after SSL verification")

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
                log.exception(f"Error loading URLs: {e}")
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
        proxy (dict): Proxy override settings for the Playwright session.
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

        proxy_server = proxy.get("server") if proxy else None
        if trust_env and not proxy_server:
            env_proxies = urllib.request.getproxies()
            env_proxy_server = env_proxies.get("https") or env_proxies.get("http")
            if env_proxy_server:
                if proxy:
                    proxy["server"] = env_proxy_server
                else:
                    proxy = {"server": env_proxy_server}

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

    def lazy_load(self) -> Iterator[Document]:
        """Safely load URLs synchronously with support for remote browser."""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # Use remote browser if ws_endpoint is provided, otherwise use local browser
            if self.playwright_ws_url:
                browser = p.chromium.connect(self.playwright_ws_url)
            else:
                browser = p.chromium.launch(headless=self.headless, proxy=self.proxy)

            for url in self.urls:
                try:
                    self._safe_process_url_sync(url)
                    page = browser.new_page()
                    response = page.goto(url, timeout=self.playwright_timeout)
                    if response is None:
                        raise ValueError(f"page.goto() returned None for url {url}")

                    text = self.evaluator.evaluate(page, browser, response)
                    metadata = {"source": url}
                    yield Document(page_content=text, metadata=metadata)
                except Exception as e:
                    if self.continue_on_failure:
                        log.exception(f"Error loading {url}: {e}")
                        continue
                    raise e
            browser.close()

    async def alazy_load(self) -> AsyncIterator[Document]:
        """Safely load URLs asynchronously with support for remote browser."""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            # Use remote browser if ws_endpoint is provided, otherwise use local browser
            if self.playwright_ws_url:
                browser = await p.chromium.connect(self.playwright_ws_url)
            else:
                browser = await p.chromium.launch(
                    headless=self.headless, proxy=self.proxy
                )

            for url in self.urls:
                try:
                    await self._safe_process_url(url)
                    page = await browser.new_page()
                    response = await page.goto(url, timeout=self.playwright_timeout)
                    if response is None:
                        raise ValueError(f"page.goto() returned None for url {url}")

                    text = await self.evaluator.evaluate_async(page, browser, response)
                    metadata = {"source": url}
                    yield Document(page_content=text, metadata=metadata)
                except Exception as e:
                    if self.continue_on_failure:
                        log.exception(f"Error loading {url}: {e}")
                        continue
                    raise e
            await browser.close()


class SafeWebBaseLoader(WebBaseLoader):
    """WebBaseLoader with enhanced error handling for URLs."""

    def __init__(self, trust_env: bool = False, *args, **kwargs):
        """Initialize SafeWebBaseLoader
        Args:
            trust_env (bool, optional): set to True if using proxy to make web requests, for example
                using http(s)_proxy environment variables. Defaults to False.
        """
        super().__init__(*args, **kwargs)
        self.trust_env = trust_env

    async def _fetch(
        self, url: str, retries: int = 3, cooldown: int = 2, backoff: float = 1.5
    ) -> str:
        async with aiohttp.ClientSession(trust_env=self.trust_env) as session:
            for i in range(retries):
                try:
                    kwargs: Dict = dict(
                        headers=self.session.headers,
                        cookies=self.session.cookies.get_dict(),
                    )
                    if not self.session.verify:
                        kwargs["ssl"] = False

                    async with session.get(
                        url,
                        **(self.requests_kwargs | kwargs),
                        allow_redirects=False,
                    ) as response:
                        if self.raise_for_status:
                            response.raise_for_status()
                        return await response.text()
                except aiohttp.ClientConnectionError as e:
                    if i == retries - 1:
                        raise
                    else:
                        log.warning(
                            f"Error fetching {url} with attempt "
                            f"{i + 1}/{retries}: {e}. Retrying..."
                        )
                        await asyncio.sleep(cooldown * backoff**i)
        raise ValueError("retry count exceeded")

    def _unpack_fetch_results(
        self, results: Any, urls: List[str], parser: Union[str, None] = None
    ) -> List[Any]:
        """Unpack fetch results into BeautifulSoup objects."""
        from bs4 import BeautifulSoup

        final_results = []
        for i, result in enumerate(results):
            url = urls[i]
            if parser is None:
                if url.endswith(".xml"):
                    parser = "xml"
                else:
                    parser = self.default_parser
                self._check_parser(parser)
            final_results.append(BeautifulSoup(result, parser, **self.bs_kwargs))
        return final_results

    async def ascrape_all(
        self, urls: List[str], parser: Union[str, None] = None
    ) -> List[Any]:
        """Async fetch all urls, then return soups for all results."""
        results = await self.fetch_all(urls)
        return self._unpack_fetch_results(results, urls, parser=parser)

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
                log.exception(f"Error loading {path}: {e}")

    async def alazy_load(self) -> AsyncIterator[Document]:
        """Async lazy load text from the url(s) in web_path."""
        results = await self.ascrape_all(self.web_paths)
        for path, soup in zip(self.web_paths, results):
            text = soup.get_text(**self.bs_get_text_kwargs)
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

    async def aload(self) -> list[Document]:
        """Load data into Document objects."""
        return [document async for document in self.alazy_load()]


def get_web_loader(
    urls: Union[str, Sequence[str]],
    verify_ssl: bool = True,
    requests_per_second: int = 2,
    trust_env: bool = False,
):
    # Check if the URLs are valid
    safe_urls = safe_validate_urls([urls] if isinstance(urls, str) else urls)

    if not safe_urls:
        log.warning(f"All provided URLs were blocked or invalid: {urls}")
        raise ValueError(ERROR_MESSAGES.INVALID_URL)

    web_loader_args = {
        "web_paths": safe_urls,
        "verify_ssl": verify_ssl,
        "requests_per_second": requests_per_second,
        "continue_on_failure": True,
        "trust_env": trust_env,
    }

    if WEB_LOADER_ENGINE.value == "" or WEB_LOADER_ENGINE.value == "safe_web":
        WebLoaderClass = SafeWebBaseLoader
    if WEB_LOADER_ENGINE.value == "playwright":
        WebLoaderClass = SafePlaywrightURLLoader
        web_loader_args["playwright_timeout"] = PLAYWRIGHT_TIMEOUT.value
        if PLAYWRIGHT_WS_URL.value:
            web_loader_args["playwright_ws_url"] = PLAYWRIGHT_WS_URL.value

    if WEB_LOADER_ENGINE.value == "firecrawl":
        WebLoaderClass = SafeFireCrawlLoader
        web_loader_args["api_key"] = FIRECRAWL_API_KEY.value
        web_loader_args["api_url"] = FIRECRAWL_API_BASE_URL.value

    if WEB_LOADER_ENGINE.value == "tavily":
        WebLoaderClass = SafeTavilyLoader
        web_loader_args["api_key"] = TAVILY_API_KEY.value
        web_loader_args["extract_depth"] = TAVILY_EXTRACT_DEPTH.value

    if WEB_LOADER_ENGINE.value == "external":
        WebLoaderClass = ExternalWebLoader
        web_loader_args["external_url"] = EXTERNAL_WEB_LOADER_URL.value
        web_loader_args["external_api_key"] = EXTERNAL_WEB_LOADER_API_KEY.value

    if WebLoaderClass:
        web_loader = WebLoaderClass(**web_loader_args)

        log.debug(
            "Using WEB_LOADER_ENGINE %s for %s URLs",
            web_loader.__class__.__name__,
            len(safe_urls),
        )

        return web_loader
    else:
        raise ValueError(
            f"Invalid WEB_LOADER_ENGINE: {WEB_LOADER_ENGINE.value}. "
            "Please set it to 'safe_web', 'playwright', 'firecrawl', or 'tavily'."
        )
