from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List, Optional

from langchain_core.documents import Document

if TYPE_CHECKING:
    from open_webui.retrieval.web.main import SearchResult

log = logging.getLogger(__name__)

DEFAULT_FIRECRAWL_LOADER_ONLY_MAIN_CONTENT = True
DEFAULT_FIRECRAWL_LOADER_PARSE_PDF = True
DEFAULT_FIRECRAWL_LOADER_PROXY_MODE = 'basic'
DEFAULT_FIRECRAWL_LOADER_MAX_AGE_MS = 3600000
FIRECRAWL_PROXY_MODES = {'basic', 'auto', 'enhanced'}


def _parse_positive_float(value: Any) -> Optional[float]:
    """Parse timeout-like values and ignore empty or non-positive inputs."""
    if value in (None, ''):
        return None

    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None

    return parsed if parsed > 0 else None


def _parse_positive_int(value: Any) -> Optional[int]:
    """Parse integer values that must stay strictly positive."""
    parsed = _parse_positive_float(value)
    return int(parsed) if parsed is not None else None


def get_firecrawl_request_timeout_seconds(timeout: Any) -> Optional[float]:
    """
    Firecrawl client instances expect their transport timeout in seconds.

    The admin setting is stored as a string in Open WebUI, so we normalize it
    once here and reuse it everywhere.
    """
    return _parse_positive_float(timeout)


def get_firecrawl_scrape_timeout_ms(timeout: Any) -> Optional[int]:
    """
    Firecrawl scrape/search operations expect request timeout values in milliseconds.

    We keep the admin input in seconds for UI compatibility and convert only at
    the SDK boundary.
    """
    seconds = get_firecrawl_request_timeout_seconds(timeout)
    return int(seconds * 1000) if seconds is not None else None


def get_firecrawl_wait_timeout_seconds(timeout: Any, url_count: int = 1) -> int:
    """
    Batch scraping uses a separate wait timeout while polling the Firecrawl job.

    If the admin already configured a timeout, reuse it. Otherwise keep a small
    but safe default that scales with the batch size.
    """
    seconds = get_firecrawl_request_timeout_seconds(timeout)
    if seconds is not None:
        return max(1, int(seconds))

    return max(30, url_count * 3)


def normalize_firecrawl_proxy_mode(proxy_mode: Any) -> str:
    """Keep proxy mode aligned with the Firecrawl SDK enum and app defaults."""
    if isinstance(proxy_mode, str):
        normalized = proxy_mode.strip().lower()
        if normalized in FIRECRAWL_PROXY_MODES:
            return normalized

    return DEFAULT_FIRECRAWL_LOADER_PROXY_MODE


def normalize_firecrawl_max_age_ms(max_age_ms: Any) -> int:
    """
    Normalize Firecrawl cache maxAge while preserving explicit zero values.

    `0` is meaningful because it disables cache reuse, so we must not collapse it
    to the default.
    """
    if max_age_ms in (None, ''):
        return DEFAULT_FIRECRAWL_LOADER_MAX_AGE_MS

    try:
        max_age = int(max_age_ms)
    except (TypeError, ValueError):
        return DEFAULT_FIRECRAWL_LOADER_MAX_AGE_MS

    return max_age if max_age >= 0 else DEFAULT_FIRECRAWL_LOADER_MAX_AGE_MS


def create_firecrawl_client(
    api_key: Optional[str],
    api_url: Optional[str],
    timeout: Any = None,
):
    """Create the synchronous Firecrawl client with Open WebUI timeout semantics."""
    from firecrawl import Firecrawl

    return Firecrawl(
        api_key=api_key,
        api_url=api_url,
        timeout=get_firecrawl_request_timeout_seconds(timeout),
    )


def create_async_firecrawl_client(
    api_key: Optional[str],
    api_url: Optional[str],
    timeout: Any = None,
):
    """Create the async Firecrawl client with the same timeout normalization."""
    from firecrawl import AsyncFirecrawl

    return AsyncFirecrawl(
        api_key=api_key,
        api_url=api_url,
        timeout=get_firecrawl_request_timeout_seconds(timeout),
    )


def build_firecrawl_scrape_kwargs(
    *,
    verify_ssl: bool,
    timeout: Any,
    only_main_content: bool = DEFAULT_FIRECRAWL_LOADER_ONLY_MAIN_CONTENT,
    parse_pdf: bool = DEFAULT_FIRECRAWL_LOADER_PARSE_PDF,
    proxy_mode: str = DEFAULT_FIRECRAWL_LOADER_PROXY_MODE,
    max_age_ms: Any = DEFAULT_FIRECRAWL_LOADER_MAX_AGE_MS,
    formats: Optional[list[str]] = None,
    remove_base64_images: bool = True,
) -> dict[str, Any]:
    """
    Build a single source of truth for Firecrawl scrape options.

    Keeping this translation in one place avoids divergence between:
    - the direct loader path (`scrape` / `batch_scrape`)
    - the native search path (`search(..., scrape_options=...)`)
    """
    kwargs: dict[str, Any] = {
        'formats': formats or ['markdown'],
        'only_main_content': only_main_content,
        'parsers': ['pdf'] if parse_pdf else [],
        'proxy': normalize_firecrawl_proxy_mode(proxy_mode),
        'max_age': normalize_firecrawl_max_age_ms(max_age_ms),
        'skip_tls_verification': not verify_ssl,
        'remove_base64_images': remove_base64_images,
    }

    scrape_timeout_ms = get_firecrawl_scrape_timeout_ms(timeout)
    if scrape_timeout_ms is not None:
        kwargs['timeout'] = scrape_timeout_ms

    return kwargs


def build_firecrawl_search_scrape_options(
    *,
    verify_ssl: bool,
    timeout: Any,
    only_main_content: bool = DEFAULT_FIRECRAWL_LOADER_ONLY_MAIN_CONTENT,
    parse_pdf: bool = DEFAULT_FIRECRAWL_LOADER_PARSE_PDF,
    proxy_mode: str = DEFAULT_FIRECRAWL_LOADER_PROXY_MODE,
    max_age_ms: Any = DEFAULT_FIRECRAWL_LOADER_MAX_AGE_MS,
):
    """Convert loader options to the `ScrapeOptions` object expected by search."""
    from firecrawl.v2.types import ScrapeOptions

    return ScrapeOptions(
        **build_firecrawl_scrape_kwargs(
            verify_ssl=verify_ssl,
            timeout=timeout,
            only_main_content=only_main_content,
            parse_pdf=parse_pdf,
            proxy_mode=proxy_mode,
            max_age_ms=max_age_ms,
        )
    )


def _get_result_metadata(result: Any) -> dict:
    """Extract result metadata from the different Firecrawl response shapes."""
    metadata_dict = getattr(result, 'metadata_dict', None)
    if isinstance(metadata_dict, dict):
        return metadata_dict

    metadata = getattr(result, 'metadata', None)
    if isinstance(metadata, dict):
        return {k: v for k, v in metadata.items() if v is not None}

    if metadata is not None and hasattr(metadata, 'model_dump'):
        return metadata.model_dump(exclude_none=True)

    return {}


def _get_result_url(result: Any) -> Optional[str]:
    """Read the canonical source URL from a search or scrape result."""
    metadata = _get_result_metadata(result)
    return (
        getattr(result, 'url', None)
        or getattr(result, 'link', None)
        or metadata.get('url')
        or metadata.get('source_url')
    )


def _get_result_title(result: Any) -> Optional[str]:
    """Read the best available title field from a Firecrawl result."""
    metadata = _get_result_metadata(result)
    return getattr(result, 'title', None) or metadata.get('title')


def _get_result_description(result: Any) -> Optional[str]:
    """Read the short summary/snippet field from a Firecrawl result."""
    metadata = _get_result_metadata(result)
    return (
        getattr(result, 'description', None)
        or getattr(result, 'snippet', None)
        or metadata.get('description')
    )


def _filter_results(results: List[Any], filter_list: Optional[List[str]]) -> List[Any]:
    """
    Reuse the existing Open WebUI domain filtering logic for Firecrawl results.

    This import stays local on purpose to avoid a circular dependency:
    `utils -> firecrawl -> main -> utils`.
    """
    if not filter_list:
        return results

    from open_webui.retrieval.web.main import get_filtered_results

    candidates = [{'url': _get_result_url(result)} for result in results if _get_result_url(result)]
    allowed_urls = {item.get('url') for item in get_filtered_results(candidates, filter_list)}

    return [result for result in results if _get_result_url(result) in allowed_urls]


def _to_search_result(result: Any) -> Optional[SearchResult]:
    """
    Convert Firecrawl results into the SearchResult structure used by the API.

    The model import is local to keep this module import-safe when `utils.py`
    imports Firecrawl helpers during application startup.
    """
    url = _get_result_url(result)
    if not url:
        return None

    from open_webui.retrieval.web.main import SearchResult

    return SearchResult(
        link=url,
        title=_get_result_title(result),
        snippet=_get_result_description(result),
    )


def _to_langchain_document(result: Any) -> Optional[Document]:
    """
    Convert Firecrawl markdown results into LangChain documents.

    Empty markdown must be ignored so disabled PDF parsing or partial responses do
    not inject unusable documents into retrieval.
    """
    content = getattr(result, 'markdown', None) or ''
    if not isinstance(content, str) or content.strip() == '':
        return None

    source = _get_result_url(result)
    metadata = {'source': source or ''}
    title = _get_result_title(result)
    description = _get_result_description(result)

    if title:
        metadata['title'] = title
    if description:
        metadata['snippet'] = description
        metadata['description'] = description
    if source:
        metadata['link'] = source

    return Document(page_content=content, metadata=metadata)


def search_firecrawl(
    firecrawl_url: str,
    firecrawl_api_key: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
    timeout: Any = None,
) -> List[SearchResult]:
    """Run Firecrawl search in result-only mode without fetching page markdown."""
    try:
        firecrawl = create_firecrawl_client(
            api_key=firecrawl_api_key,
            api_url=firecrawl_url,
            timeout=timeout,
        )
        response = firecrawl.search(
            query=query,
            limit=count,
            ignore_invalid_urls=True,
            timeout=get_firecrawl_scrape_timeout_ms(timeout),
        )
        results = _filter_results(list(response.web or []), filter_list)

        search_results = []
        for result in results[:count]:
            item = _to_search_result(result)
            if item is not None:
                search_results.append(item)

        log.info(f'External search results: {search_results}')
        return search_results
    except Exception as e:
        log.error(f'Error in External search: {e}')
        return []


async def search_firecrawl_with_scrape(
    firecrawl_url: str,
    firecrawl_api_key: str,
    query: str,
    count: int,
    filter_list: Optional[List[str]] = None,
    timeout: Any = None,
    verify_ssl: bool = True,
    only_main_content: bool = True,
    parse_pdf: bool = True,
    proxy_mode: str = 'basic',
    max_age_ms: Any = None,
) -> tuple[List[SearchResult], List[Document]]:
    """
    Run Firecrawl search with native scrape options enabled.

    This path returns both lightweight search metadata and fully scraped markdown
    so retrieval can skip a second fetch round-trip when Firecrawl is the search
    engine and the loader is not bypassed.
    """
    firecrawl = create_async_firecrawl_client(
        api_key=firecrawl_api_key,
        api_url=firecrawl_url,
        timeout=timeout,
    )

    response = await firecrawl.search(
        query=query,
        limit=count,
        ignore_invalid_urls=True,
        timeout=get_firecrawl_scrape_timeout_ms(timeout),
        scrape_options=build_firecrawl_search_scrape_options(
            verify_ssl=verify_ssl,
            timeout=timeout,
            only_main_content=only_main_content,
            parse_pdf=parse_pdf,
            proxy_mode=proxy_mode,
            max_age_ms=max_age_ms,
        ),
    )

    results = _filter_results(list(response.web or []), filter_list)

    search_results: List[SearchResult] = []
    docs: List[Document] = []

    for result in results[:count]:
        item = _to_search_result(result)
        if item is not None:
            search_results.append(item)

        doc = _to_langchain_document(result)
        if doc is not None:
            docs.append(doc)

    return search_results, docs
