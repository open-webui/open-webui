"""
Jina Reader integration for Open WebUI web_fetch.

The model-facing `web_fetch` tool uses this module to retrieve full page
content through Jina Reader's JSON API. Search remains Exa-backed; Jina is only
used for URL content extraction.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import aiohttp

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

JINA_READER_API_BASE = "https://r.jina.ai/"


@dataclass
class JinaContentResult:
    """Normalized page content returned by Jina Reader."""

    url: str
    title: str
    text: str
    description: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[str] = None
    images: Dict[str, str] = field(default_factory=dict)
    usage_tokens: int = 0


def _extract_usage_tokens(payload: dict, data: dict) -> int:
    """Extract Jina token usage from either top-level meta or data usage."""
    usage = data.get("usage") or payload.get("usage") or {}
    meta_usage = payload.get("meta", {}).get("usage", {})

    tokens = usage.get("tokens") or meta_usage.get("tokens") or 0
    try:
        return max(0, int(tokens))
    except Exception:
        return 0


def _normalize_jina_response(payload: dict, requested_url: str) -> JinaContentResult:
    """Normalize Jina's JSON response into the shape web_fetch already formats."""
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    metadata = data.get("metadata") or {}

    title = (
        data.get("title")
        or metadata.get("og:title")
        or metadata.get("twitter:title")
        or requested_url
    )
    description = (
        data.get("description")
        or metadata.get("description")
        or metadata.get("og:description")
        or metadata.get("twitter:description")
    )

    published_date = (
        data.get("publishedDate")
        or data.get("published_date")
        or metadata.get("article:published_time")
        or metadata.get("date")
    )

    images = data.get("images") or {}
    if not isinstance(images, dict):
        images = {}

    return JinaContentResult(
        url=data.get("url") or requested_url,
        title=title or requested_url,
        text=data.get("content") or data.get("text") or "",
        description=description,
        author=data.get("author") or metadata.get("author"),
        published_date=published_date,
        images=images,
        usage_tokens=_extract_usage_tokens(payload, data),
    )


def _jina_headers(api_key: str, timeout_seconds: int) -> dict[str, str]:
    """Headers for the requested Jina Reader browser-mode JSON call."""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Engine": "browser",
        "X-Timeout": str(timeout_seconds),
        "X-Base": "final",
        "X-Remove-Overlay": "true",
        "X-Retain-Links": "all",
        "X-Retain-Images": "all_p",
        "X-With-Images-Summary": "true",
        "X-Retain-Media": "link",
        "X-Md-Heading-Style": "atx",
    }

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    return headers


async def _fetch_jina_content(
    session: aiohttp.ClientSession,
    api_key: str,
    url: str,
    viewport_width: int,
    viewport_height: int,
    timeout_seconds: int,
) -> JinaContentResult:
    payload = {
        "url": url,
        "viewport": {
            "width": viewport_width,
            "height": viewport_height,
        },
    }

    async with session.post(
        JINA_READER_API_BASE,
        headers=_jina_headers(api_key, timeout_seconds),
        json=payload,
    ) as response:
        response_text = await response.text()

        if response.status >= 400:
            raise Exception(
                f"Jina Reader failed for {url}: HTTP {response.status} {response_text[:500]}"
            )

        try:
            response_json = await response.json(content_type=None)
        except Exception as e:
            raise Exception(f"Jina Reader returned invalid JSON for {url}: {e}")

    code = response_json.get("code")
    status = response_json.get("status")
    if code not in (None, 200) or status not in (None, 20000):
        raise Exception(
            f"Jina Reader failed for {url}: code={code} status={status} "
            f"message={response_json.get('message') or response_json.get('detail') or ''}"
        )

    result = _normalize_jina_response(response_json, url)
    if not result.text.strip():
        log.warning("Jina Reader returned empty content for %s", url)

    return result


async def fetch_jina_contents(
    api_key: str,
    urls: List[str],
    viewport_width: int = 1280,
    viewport_height: int = 12000,
    timeout_seconds: int = 30,
    max_concurrency: int = 5,
) -> List[JinaContentResult]:
    """
    Fetch full content from URLs using Jina Reader's POST JSON API.

    Args:
        api_key: Jina API key. Used as `Authorization: Bearer <key>`.
        urls: URLs to fetch.
        viewport_width: Browser viewport width sent in the request body.
        viewport_height: Browser viewport height sent in the request body.
        timeout_seconds: Jina Reader timeout sent via `X-Timeout`.
        max_concurrency: Maximum concurrent Jina requests.

    Returns:
        JinaContentResult objects in the same order as the requested URLs, with
        failed URLs omitted after logging a warning.
    """
    if not urls:
        return []

    viewport_width = max(320, int(viewport_width or 1280))
    viewport_height = max(1000, int(viewport_height or 12000))
    timeout_seconds = max(1, int(timeout_seconds or 30))
    max_concurrency = max(1, min(int(max_concurrency or 1), len(urls)))

    log.info("Jina Reader fetch for %s URL(s)", len(urls))

    timeout = aiohttp.ClientTimeout(total=timeout_seconds + 10)
    connector = aiohttp.TCPConnector(limit=max_concurrency, ttl_dns_cache=300)
    semaphore = asyncio.Semaphore(max_concurrency)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:

        async def guarded_fetch(fetch_url: str):
            async with semaphore:
                try:
                    return await _fetch_jina_content(
                        session=session,
                        api_key=api_key,
                        url=fetch_url,
                        viewport_width=viewport_width,
                        viewport_height=viewport_height,
                        timeout_seconds=timeout_seconds,
                    )
                except Exception as e:
                    log.warning("Jina Reader fetch failed for %s: %s", fetch_url, e)
                    return None

        results = await asyncio.gather(*(guarded_fetch(url) for url in urls))

    successful_results = [result for result in results if result is not None]
    log.info("Jina Reader returned content for %s URL(s)", len(successful_results))
    return successful_results
