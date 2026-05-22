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

import logging
import time

import httpx
from open_webui.env import (
    WORKBENCH_API_TOKEN,
    WORKBENCH_COMPANY_ID,
    WORKBENCH_INTERNAL_URL,
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


def is_configured() -> bool:
    """True iff this OWUI deployment has the Workbench-sidebar
    integration wired (all three env vars set). Used by /api/config to
    tell the frontend whether to expect entitlement data — when False,
    loader.js falls back to a hardcoded nav rather than an empty rail
    (which is the right state for "configured but no per-user data")."""
    return bool(WORKBENCH_INTERNAL_URL and WORKBENCH_API_TOKEN and WORKBENCH_COMPANY_ID)


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
    """
    if not user_email or not is_configured():
        return None

    normalized_email = user_email.lower()
    now = time.monotonic()
    cached = _CACHE.get(normalized_email)
    if cached and now - cached[0] < _TTL_SECONDS:
        return cached[1]

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
            'workbench sidebar fetch failed for %s: %s: %s',
            _redact_email_for_log(user_email),
            type(e).__name__,
            e,
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
