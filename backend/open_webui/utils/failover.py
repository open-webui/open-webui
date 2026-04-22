"""Failover routing for OpenAI-compatible workspace models.

A workspace model may list an ordered set of providers in
`Model.meta.failover_providers`. At request time this module resolves
that list into concrete (URL, key, model name) candidates the chat
handler can try in order. Providers marked unhealthy in the app-state
cache are deprioritised, but never removed outright — if every provider
looks unhealthy we still try them rather than hard-failing.
"""

from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
import logging
import time
from typing import Optional

from fastapi import Request

log = logging.getLogger(__name__)


# Capability names that the resolver understands today.
CAPABILITY_TOOLS = 'tools'
CAPABILITY_VISION = 'vision'


class RetryableProviderError(Exception):
    """Signal from a single-provider attempt that the outer loop should try the next candidate.

    Raised when the request fails in a way that looks transient (connection
    error, 5xx, 429). The fields carry enough context for health-cache
    updates (retry_after) and, if every candidate fails, for the final
    HTTPException surfaced to the user.
    """

    def __init__(
        self,
        status_code: Optional[int] = None,
        detail: Optional[str] = None,
        retry_after: Optional[int] = None,
        provider_url: Optional[str] = None,
    ):
        self.status_code = status_code
        self.detail = detail
        self.retry_after = retry_after
        self.provider_url = provider_url
        super().__init__(f'Retryable provider error at {provider_url}: {status_code} {detail}')


@dataclass
class ProviderCandidate:
    url: str
    url_idx: int
    key: str
    model_name: str
    api_config: dict
    prefix_id: Optional[str] = None
    capabilities: list[str] = field(default_factory=list)
    # Position in the original failover list (0 = primary). Surfaced to the
    # frontend so the UI can say "answered by backup #2".
    position: int = 0


def required_capabilities_from_payload(payload: dict) -> list[str]:
    """Inspect an OpenAI-compatible chat payload to infer required capabilities."""
    required: set[str] = set()
    if payload.get('tools') or payload.get('functions'):
        required.add(CAPABILITY_TOOLS)
    for msg in payload.get('messages') or []:
        content = msg.get('content')
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get('type') in ('image_url', 'input_image'):
                    required.add(CAPABILITY_VISION)
                    break
    return sorted(required)


def _health_status(health_cache: Optional[dict], url: str) -> str:
    """Return 'healthy' | 'unhealthy' | 'unknown' for a given provider URL."""
    if not health_cache:
        return 'unknown'
    entry = health_cache.get(url)
    if not entry:
        return 'unknown'
    # An unhealthy_until timestamp overrides a stale healthy status.
    unhealthy_until = entry.get('unhealthy_until')
    if unhealthy_until and unhealthy_until > time.time():
        return 'unhealthy'
    return entry.get('status', 'unknown')


def resolve_failover_candidates(
    request: Request,
    model_info,
    payload: dict,
    skip_urls: Optional[list[str]] = None,
    health_cache: Optional[dict] = None,
) -> list[ProviderCandidate]:
    """Build the ordered candidate list for a chat completion.

    If `model_info.meta.failover_providers` is set, use that ordered list
    (filtered by skip_urls and required capabilities). Otherwise, fall back
    to legacy single-provider resolution via OPENAI_MODELS.

    Unhealthy-per-cache providers stay in the list but sink below healthy
    ones; if every candidate is unhealthy they are still tried in their
    configured order.
    """
    skip_set = set(skip_urls or [])
    required_caps = required_capabilities_from_payload(payload)

    base_urls = request.app.state.config.OPENAI_API_BASE_URLS
    keys = request.app.state.config.OPENAI_API_KEYS
    configs = request.app.state.config.OPENAI_API_CONFIGS

    failover = None
    if model_info and model_info.meta and getattr(model_info.meta, 'failover_providers', None):
        failover = model_info.meta.failover_providers

    candidates: list[ProviderCandidate] = []

    if failover:
        for position, entry in enumerate(failover):
            url = entry.connection_url
            if url in skip_set:
                continue
            # Capability filter: if required caps declared, provider must
            # list them. An empty capabilities list = "unknown, try it".
            if required_caps and entry.capabilities:
                if any(cap not in entry.capabilities for cap in required_caps):
                    continue
            if url not in base_urls:
                log.warning('Failover provider %s not found in OPENAI_API_BASE_URLS; skipping.', url)
                continue
            idx = base_urls.index(url)
            key = keys[idx] if idx < len(keys) else ''
            api_config = configs.get(str(idx), configs.get(url, {}))
            candidates.append(
                ProviderCandidate(
                    url=url,
                    url_idx=idx,
                    key=key,
                    model_name=entry.model_name,
                    api_config=api_config,
                    prefix_id=api_config.get('prefix_id'),
                    capabilities=list(entry.capabilities or []),
                    position=position,
                )
            )
    else:
        # Legacy path: single provider derived from OPENAI_MODELS cache.
        models_state = request.app.state.OPENAI_MODELS or {}
        model_id = payload.get('model')
        model_entry = models_state.get(model_id)
        if model_entry:
            idx = model_entry['urlIdx']
            if idx < len(base_urls):
                url = base_urls[idx]
                if url not in skip_set:
                    key = keys[idx] if idx < len(keys) else ''
                    api_config = configs.get(str(idx), configs.get(url, {}))
                    candidates.append(
                        ProviderCandidate(
                            url=url,
                            url_idx=idx,
                            key=key,
                            model_name=model_id,
                            api_config=api_config,
                            prefix_id=api_config.get('prefix_id'),
                            capabilities=[],
                            position=0,
                        )
                    )

    # Sink unhealthy providers to the end, but keep configured order among
    # equals so the primary still beats backup if both are healthy.
    def health_rank(c: ProviderCandidate) -> int:
        status = _health_status(health_cache, c.url)
        if status == 'healthy':
            return 0
        if status == 'unknown':
            return 1
        return 2

    # Stable sort preserves configured order within each health tier.
    candidates.sort(key=health_rank)
    return candidates


def is_retryable_error(status_code: Optional[int], exc: Optional[BaseException]) -> bool:
    """Does this failure mean we should try the next failover provider?"""
    if exc is not None:
        # Network-layer: aiohttp.ClientError, asyncio.TimeoutError, OSError, etc.
        return True
    if status_code is None:
        return True
    if status_code == 429:
        return True
    if 500 <= status_code < 600:
        return True
    return False


def parse_retry_after(header_value: Optional[str]) -> Optional[int]:
    """Parse a Retry-After HTTP header into seconds-from-now.

    Accepts either an integer delta ("60") or an HTTP date
    ("Wed, 21 Oct 2015 07:28:00 GMT"). Returns None if unparseable.
    """
    if not header_value:
        return None
    value = header_value.strip()
    try:
        return max(0, int(value))
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(value)
        if dt is None:
            return None
        delta = dt.timestamp() - time.time()
        return max(0, int(delta))
    except (TypeError, ValueError):
        return None
