"""Background health probes for configured OpenAI-compatible connections.

Runs as a FastAPI lifespan task and writes per-URL status into
``app.state.PROVIDER_HEALTH``. The failover resolver consults this cache to
deprioritise providers we've recently observed as unhealthy, and the UI
polls an endpoint that surfaces the same data as status dots.

The probe is a plain ``GET /models`` with a short timeout — cheap, and the
same endpoint the model-list cache already hits, so providers that don't
expose anything fancier still work. A probe failure here is advisory; we
still *try* a provider on the request path (the failover loop owns the
real retry decision).
"""

import asyncio
import logging
import time
from typing import Optional

import aiohttp

from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL
from open_webui.utils.session_pool import get_session

log = logging.getLogger(__name__)

# How often to re-probe every configured connection.
HEALTH_CHECK_INTERVAL_SECONDS = 30
# Hard timeout per probe — if a provider needs >5s just to acknowledge a
# model-list request, it's effectively down for our purposes.
HEALTH_CHECK_TIMEOUT_SECONDS = 5


async def check_connection_health(url: str, key: str, api_config: dict) -> dict:
    """Issue one ``GET /models`` probe and classify the result.

    Returns a dict ready to be stored in ``app.state.PROVIDER_HEALTH[url]``.
    Never raises — network failures are folded into an ``unhealthy`` entry.
    """
    headers = {'Content-Type': 'application/json'}
    if key:
        # Bearer covers OpenAI/OpenRouter/Groq/etc. Azure Entra ID connections
        # will answer with an auth error on a bearer request — that's fine,
        # it still tells us the socket is alive, but we sidestep false
        # negatives by skipping Azure AD entries entirely below.
        headers['Authorization'] = f'Bearer {key}'

    probe_url = f'{url.rstrip("/")}/models'
    start = time.time()

    try:
        session = await get_session()
        async with session.get(
            probe_url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=HEALTH_CHECK_TIMEOUT_SECONDS),
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as r:
            latency_ms = int((time.time() - start) * 1000)
            if 200 <= r.status < 300:
                return {
                    'status': 'healthy',
                    'last_success_at': time.time(),
                    'last_check_at': time.time(),
                    'latency_ms': latency_ms,
                }
            body = (await r.text())[:200]
            return {
                'status': 'unhealthy',
                'last_check_at': time.time(),
                'last_error_at': time.time(),
                'last_error_status': r.status,
                'last_error': body,
                'latency_ms': latency_ms,
            }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'last_check_at': time.time(),
            'last_error_at': time.time(),
            'last_error': str(e)[:200],
            'latency_ms': int((time.time() - start) * 1000),
        }


async def _run_health_checks(app) -> None:
    state = app.state
    base_urls = list(getattr(state.config, 'OPENAI_API_BASE_URLS', None) or [])
    keys = list(getattr(state.config, 'OPENAI_API_KEYS', None) or [])
    configs = dict(getattr(state.config, 'OPENAI_API_CONFIGS', None) or {})

    if getattr(state, 'PROVIDER_HEALTH', None) is None:
        state.PROVIDER_HEALTH = {}

    # Prune stale entries for connections that were removed from config.
    configured = set(base_urls)
    for url in list(state.PROVIDER_HEALTH.keys()):
        if url not in configured:
            state.PROVIDER_HEALTH.pop(url, None)

    probes: list[tuple[str, asyncio.Future]] = []
    for i, url in enumerate(base_urls):
        key = keys[i] if i < len(keys) else ''
        api_config = configs.get(str(i), configs.get(url, {}))

        # Respect the admin's "enable" toggle.
        if api_config.get('enable') is False:
            state.PROVIDER_HEALTH[url] = {
                'status': 'disabled',
                'last_check_at': time.time(),
            }
            continue

        # Skip Azure Entra ID endpoints — they require a different auth path
        # than bearer, and probing them produces false-negatives.
        auth_type = api_config.get('auth_type', 'bearer')
        if api_config.get('azure') and auth_type in ('azure_ad', 'microsoft_entra_id'):
            state.PROVIDER_HEALTH[url] = {
                'status': 'unknown',
                'last_check_at': time.time(),
                'note': 'azure-entra auth (probe skipped)',
            }
            continue

        probes.append((url, check_connection_health(url, key, api_config)))

    if not probes:
        return

    results = await asyncio.gather(*(p[1] for p in probes), return_exceptions=True)
    for (url, _), result in zip(probes, results):
        if isinstance(result, BaseException):
            result = {
                'status': 'unhealthy',
                'last_check_at': time.time(),
                'last_error': str(result)[:200],
            }

        # Preserve a request-path unhealthy_until (set from Retry-After). A
        # probe success shouldn't un-block a provider the server told us to
        # back off from.
        existing = state.PROVIDER_HEALTH.get(url, {})
        prior_cooldown = existing.get('unhealthy_until')
        if prior_cooldown and prior_cooldown > time.time():
            result['unhealthy_until'] = prior_cooldown

        state.PROVIDER_HEALTH[url] = result


async def health_check_loop(app) -> None:
    """FastAPI lifespan task: run probes on a fixed interval."""
    log.info(
        'OpenAI provider health-check loop started (interval=%ds, timeout=%ds)',
        HEALTH_CHECK_INTERVAL_SECONDS,
        HEALTH_CHECK_TIMEOUT_SECONDS,
    )
    while True:
        try:
            await _run_health_checks(app)
        except asyncio.CancelledError:
            log.info('Provider health-check loop cancelled')
            raise
        except Exception:
            # We never want a transient failure to kill the loop.
            log.exception('Health-check iteration failed')
        try:
            await asyncio.sleep(HEALTH_CHECK_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            log.info('Provider health-check loop cancelled (during sleep)')
            raise


def snapshot_provider_health(app) -> dict:
    """Return a plain dict of the current PROVIDER_HEALTH state.

    Frontend-facing: status dots poll this. We return a shallow copy with a
    derived ``effective_status`` that collapses ``unhealthy_until`` + status
    into a single field the UI can render without re-implementing the logic.
    """
    health: Optional[dict] = getattr(app.state, 'PROVIDER_HEALTH', None) or {}
    now = time.time()
    out = {}
    for url, entry in health.items():
        effective = entry.get('status', 'unknown')
        unhealthy_until = entry.get('unhealthy_until')
        if unhealthy_until and unhealthy_until > now:
            effective = 'unhealthy'
        out[url] = {
            **entry,
            'effective_status': effective,
            'seconds_until_retry': int(unhealthy_until - now) if unhealthy_until and unhealthy_until > now else None,
        }
    return out
