"""
Workbench sidebar entitlement fetcher.

Internal app-to-app: this OWUI deployment asks Workbench
`GET /v1/companies/<company_id>/sidebar?user_email=<email>` and returns
the granted feature keys + pre-rendered nav structure for the current
user. The embedded shell (static/loader.js) renders only what comes
back, so a user with limited grants in Workbench sees the same limited
shell here.

Config is via env (see env.py): WORKBENCH_URL + WORKBENCH_API_TOKEN +
WORKBENCH_COMPANY_ID. When any of those are unset the fetcher returns
None and the loader falls back to its built-in nav.

Cache: in-process dict keyed by lowercased user_email, 60s TTL. The
Workbench endpoint already sends `Cache-Control: private, max-age=60`;
this mirrors that window so we don't beat on it harder than needed.
On error we soft-fail (log + return last-known if any, else None) so
a brief Workbench outage doesn't break the OWUI config endpoint.
"""

import logging
import time
from typing import Optional

import httpx

from open_webui.env import (
    WORKBENCH_API_TOKEN,
    WORKBENCH_COMPANY_ID,
    WORKBENCH_URL,
)

log = logging.getLogger(__name__)

_TTL_SECONDS = 60
_TIMEOUT_SECONDS = 2.0
# Optional[dict] in the second slot: we cache `None` on 404 so unknown
# emails don't beat on Workbench every request within the TTL.
_CACHE: dict[str, tuple[float, Optional[dict]]] = {}


def _is_configured() -> bool:
    return bool(WORKBENCH_URL and WORKBENCH_API_TOKEN and WORKBENCH_COMPANY_ID)


def _prune_expired(now: float) -> None:
    """Drop expired entries. Called inline on every cache write so a
    long-running instance with many distinct user emails doesn't grow
    the dict unboundedly — without this the cache leaks roughly one
    entry per unique email forever. Cheap O(N) walk; N is bounded by
    "users active in this OWUI in the last TTL window," which is small."""
    expired = [k for k, (ts, _) in _CACHE.items() if now - ts >= _TTL_SECONDS]
    for k in expired:
        _CACHE.pop(k, None)


async def fetch_sidebar(user_email: Optional[str]) -> Optional[dict]:
    """
    Resolve the sidebar entitlement payload for the given user email.

    Returns the `data` object from Workbench (with `user`, `company`,
    `features`, and `sidebar` keys), or None if not configured / the
    user is unknown / a transient error occurred.
    """
    if not user_email or not _is_configured():
        return None

    key = user_email.lower()
    now = time.time()
    cached = _CACHE.get(key)
    if cached and now - cached[0] < _TTL_SECONDS:
        return cached[1]

    url = f'{WORKBENCH_URL}/v1/companies/{WORKBENCH_COMPANY_ID}/sidebar'
    headers = {'Authorization': f'Bearer {WORKBENCH_API_TOKEN}'}
    params = {'user_email': user_email}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.get(url, params=params, headers=headers)

        if response.status_code == 404:
            # Unknown user (or non-member of this Workbench company).
            # Don't keep retrying every request; cache `None` so the
            # next call within the TTL is a no-op.
            _prune_expired(now)
            _CACHE[key] = (now, None)
            return None

        response.raise_for_status()
        data = response.json().get('data')
        _prune_expired(now)
        _CACHE[key] = (now, data)
        return data
    except Exception as e:  # noqa: BLE001 — soft-fail, see docstring
        log.warning(
            'workbench sidebar fetch failed for %s: %s: %s',
            user_email,
            type(e).__name__,
            e,
        )
        # Return last-known value if any so a brief outage doesn't
        # blank the shell mid-session; otherwise None.
        #
        # Refresh the cache timestamp (or write a None entry) so
        # subsequent calls within the TTL window are served from the
        # cache instead of hammering Workbench with a 2s-timeout
        # network attempt each time. During an outage, this throttles
        # retries to one per TTL — config endpoint stays fast.
        last_known = cached[1] if cached else None
        _prune_expired(now)
        _CACHE[key] = (now, last_known)
        return last_known
