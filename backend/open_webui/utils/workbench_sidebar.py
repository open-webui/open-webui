"""
Workbench sidebar entitlement fetcher.

Internal app-to-app: this OWUI deployment asks Workbench
`GET /v1/companies/<company_id>/sidebar?user_email=<email>` and returns
the granted feature keys + pre-rendered nav structure for the current
user. The embedded shell (static/loader.js) renders only what comes
back, so a user with limited grants in Workbench sees the same limited
shell here.

Config is via env (see env.py): WORKBENCH_INTERNAL_URL (or its
WORKBENCH_URL fallback) + WORKBENCH_API_TOKEN + WORKBENCH_COMPANY_ID.
When any of those are unset the fetcher returns None and the loader
falls back to its built-in nav.

The fetcher uses WORKBENCH_INTERNAL_URL (container-internal) for the
backend-to-backend call, separate from the browser-facing WORKBENCH_URL
that /api/config exposes for loader.js to use as its safeHref allowlist
and for link rendering. In production both URLs are typically the same;
the split exists for local Docker dev where the browser uses
http://localhost:<port> and this container uses http://host.docker.internal:<port>.

Cache: in-process dict keyed by lowercased user_email, 60s TTL. The
Workbench endpoint already sends `Cache-Control: private, max-age=60`;
this mirrors that window so we don't beat on it harder than needed.
On error we soft-fail (log + return last-known if any, else None) so
a brief Workbench outage doesn't break the OWUI config endpoint.
"""

import asyncio
import logging
import time

import httpx
from open_webui.env import (
    WORKBENCH_API_TOKEN,
    WORKBENCH_COMPANY_ID,
    WORKBENCH_INTERNAL_URL,
    WORKBENCH_URL,
)

log = logging.getLogger(__name__)

_TTL_SECONDS = 60
# Tight enough that a slow/unreachable Workbench doesn't materially
# delay /api/config (which awaits this on cache miss), generous enough
# to absorb normal Workbench-side variance (DB query + serializer
# typically <100ms). The exception branch caches `None` with a fresh
# timestamp so repeat misses inside the TTL window short-circuit.
_TIMEOUT_SECONDS = 1.0
# Optional[dict] in the second slot: we cache `None` on 404 so unknown
# emails don't beat on Workbench every request within the TTL.
# Timestamps come from time.monotonic(), not time.time() — NTP/DST
# adjustments on the host would otherwise let cache entries appear
# to age into the past or future.
_CACHE: dict[str, tuple[float, dict | None]] = {}

# In-flight Tasks keyed by normalized email. When N concurrent
# /api/config calls arrive for the same user on a cold cache (e.g.
# user opens N tabs in quick succession), only the first one runs the
# network fetch; the rest await its result. Without this, all N race
# past the cache miss and fire upstream in parallel, defeating the
# TTL cache for exactly the case it most needs to be effective.
_INFLIGHT: dict[str, asyncio.Task] = {}


def is_configured() -> bool:
    """True iff this OWUI deployment has the Workbench-sidebar
    integration wired. Used by /api/config to tell the frontend
    whether to expect entitlement data — when False, loader.js
    falls back to a hardcoded nav rather than an empty rail
    (which is the right state for "configured but no per-user data").

    All four signals must be set:
      * WORKBENCH_URL — browser-facing host; loader.js short-circuits
        and never mounts the shell when this is empty, so reporting
        the integration as enabled here without it would have
        /api/config awaiting fetch_sidebar for a UI that never renders
      * WORKBENCH_INTERNAL_URL — container-internal host used for the
        actual backend fetch (defaults to WORKBENCH_URL when unset)
      * WORKBENCH_API_TOKEN — bearer token for Workbench's V1 API
      * WORKBENCH_COMPANY_ID — which company's entitlement to fetch
    """
    return bool(WORKBENCH_URL and WORKBENCH_INTERNAL_URL and WORKBENCH_API_TOKEN and WORKBENCH_COMPANY_ID)


def _redact_email_for_log(email: str | None) -> str:
    """Mask the local-part of an email so warning logs don't leak full
    PII during upstream outages (where these warnings can fire per
    request). Keeps the first two characters and the domain so
    operators can still correlate "is this affecting all users or
    just one" — `peter@swept.ai` becomes `pe***@swept.ai`."""
    if not email or '@' not in email:
        return '***'
    local, _, domain = email.partition('@')
    return f'{local[:2]}***@{domain}'


def _safe_exception_repr(e: BaseException) -> str:
    """Stringify an exception for logging without re-leaking PII.

    httpx.HTTPStatusError formats `str(e)` as something like
    `Client error '404 Not Found' for url '<full URL>'`, and our
    request URL carries `user_email=` as a query param — which would
    undo the email redaction in the surrounding log line. To avoid
    that, return only the exception class name plus, when available,
    the HTTP status code from `e.response.status_code`. Operators
    still get enough signal to distinguish 4xx/5xx/timeout/connect
    failures without any URL or message content surfacing."""
    status = getattr(getattr(e, 'response', None), 'status_code', None)
    if status is not None:
        return f'{type(e).__name__}(HTTP {status})'
    return type(e).__name__


def _prune_expired(now: float) -> None:
    """Drop expired entries. Called inline on every cache write so a
    long-running instance with many distinct user emails doesn't grow
    the dict unboundedly — without this the cache leaks roughly one
    entry per unique email forever. Cheap O(N) walk; N is bounded by
    "users active in this OWUI in the last TTL window," which is small."""
    expired = [k for k, (ts, _) in _CACHE.items() if now - ts >= _TTL_SECONDS]
    for k in expired:
        _CACHE.pop(k, None)


async def fetch_sidebar(user_email: str | None) -> dict | None:
    """
    Resolve the sidebar entitlement payload for the given user email.

    Returns the `sidebar` subtree from Workbench (`{main: [...], bottom: [...]}`),
    or None if not configured / the user is unknown / a transient error
    occurred. Workbench's response envelope also includes `user`,
    `company`, and `features` siblings, but the OWUI shell only renders
    `sidebar`, so we cache + forward just that to keep the /api/config
    payload minimal and avoid exposing extra identity data.

    Concurrent callers for the same email share a single upstream
    fetch: the first one starts the network call and registers a Task
    in _INFLIGHT; the rest await that Task instead of racing past the
    cache miss in parallel. This keeps the TTL cache effective on cold
    starts (e.g. user opens several tabs in quick succession).
    """
    if not user_email or not is_configured():
        return None

    normalized_email = user_email.lower()
    cached = _CACHE.get(normalized_email)
    if cached and time.monotonic() - cached[0] < _TTL_SECONDS:
        return cached[1]

    # Coalesce concurrent cold-cache calls for the same email onto one
    # Task. The first caller becomes the "leader" and runs _do_fetch;
    # everyone else awaits the same Task. asyncio.shield isn't needed
    # here — if the leader's request times out, the failure propagates
    # to all awaiters, which is the desired soft-fail behavior.
    inflight = _INFLIGHT.get(normalized_email)
    if inflight is not None:
        return await inflight

    task = asyncio.create_task(_do_fetch(normalized_email, cached))
    _INFLIGHT[normalized_email] = task
    try:
        return await task
    finally:
        # Drop the Task reference regardless of outcome so the next
        # cache-miss can start a fresh fetch.
        _INFLIGHT.pop(normalized_email, None)


async def _do_fetch(normalized_email: str, cached: tuple[float, dict | None] | None) -> dict | None:
    """The actual upstream call + cache write. Factored out so
    fetch_sidebar can dedup concurrent callers via _INFLIGHT without
    duplicating the try/except/cache-update flow.

    `cached` is the pre-call cache entry (may be None) — passed in so
    the exception path can preserve the last-known value without
    re-reading the cache (which could have been updated by another
    coroutine between the read and the exception)."""
    now = time.monotonic()
    url = f'{WORKBENCH_INTERNAL_URL}/v1/companies/{WORKBENCH_COMPANY_ID}/sidebar'
    headers = {'Authorization': f'Bearer {WORKBENCH_API_TOKEN}'}
    # Send the normalized lowercase email so the request and the cache
    # key are symmetric. Workbench downcases on its end too, so this is
    # the same semantically — but it avoids the edge case where two
    # callers spell the same email differently and one hits cache while
    # the other doesn't see the same response.
    params = {'user_email': normalized_email}

    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT_SECONDS,
            # Follow benign redirects (proxy normalization, trailing-slash
            # rewrites). Without this httpx returns the 3xx as-is and
            # raise_for_status() ignores it, so a misconfigured proxy
            # would surface as a JSON parse error rather than a clear
            # request failure.
            follow_redirects=True,
        ) as client:
            response = await client.get(url, params=params, headers=headers)

        if response.status_code == 404:
            # Unknown user (or non-member of this Workbench company).
            # Don't keep retrying every request; cache `None` so the
            # next call within the TTL is a no-op.
            _prune_expired(now)
            _CACHE[normalized_email] = (now, None)
            return None

        response.raise_for_status()
        sidebar = (response.json().get('data') or {}).get('sidebar')
        _prune_expired(now)
        _CACHE[normalized_email] = (now, sidebar)
        return sidebar
    except Exception as e:  # noqa: BLE001 — soft-fail, see docstring
        log.warning(
            'workbench sidebar fetch failed for %s: %s',
            _redact_email_for_log(normalized_email),
            _safe_exception_repr(e),
        )
        # Return last-known value if any so a brief outage doesn't
        # blank the shell mid-session; otherwise None.
        #
        # Refresh the cache timestamp (or write a None entry) so
        # subsequent calls within the TTL window are served from the
        # cache instead of hammering Workbench with another
        # _TIMEOUT_SECONDS-bounded network attempt each time. During
        # an outage, this throttles retries to one per TTL — config
        # endpoint stays fast.
        last_known = cached[1] if cached else None
        _prune_expired(now)
        _CACHE[normalized_email] = (now, last_known)
        return last_known
