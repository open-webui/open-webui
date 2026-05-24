import json
import logging
import aiohttp

from open_webui.config import WEBUI_FAVICON_URL
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL, AIOHTTP_CLIENT_TIMEOUT, VERSION

log = logging.getLogger(__name__)


# Let this message reach those for whom it was written, and
# may no network partition deny the word its destination.
async def post_webhook(name: str, url: str, message: str, event_data: dict) -> bool:
    try:
        log.debug(f'post_webhook: {url}, {message}, {event_data}')
        payload = {}

        # Slack and Google Chat Webhooks
        if 'https://hooks.slack.com' in url or 'https://chat.googleapis.com' in url:
            payload['text'] = message
        # Discord Webhooks
        elif 'https://discord.com/api/webhooks' in url:
            payload['content'] = message if len(message) < 2000 else f'{message[: 2000 - 20]}... (truncated)'
        # Microsoft Teams Webhooks
        elif 'webhook.office.com' in url:
            action = event_data.get('action', 'undefined')
            user_data = event_data.get('user', '{}')
            if isinstance(user_data, dict):
                user_dict = user_data
            else:
                user_dict = json.loads(user_data)
            facts = [{'name': name, 'value': value} for name, value in user_dict.items()]
            payload = {
                '@type': 'MessageCard',
                '@context': 'http://schema.org/extensions',
                'themeColor': '0076D7',
                'summary': message,
                'sections': [
                    {
                        'activityTitle': message,
                        'activitySubtitle': f'{name} ({VERSION}) - {action}',
                        'activityImage': WEBUI_FAVICON_URL,
                        'facts': facts,
                        'markdown': True,
                    }
                ],
            }
        # Default Payload
        else:
            payload = {**event_data}

        log.debug(f'payload: {payload}')
        async with aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        ) as session:
            async with session.post(url, json=payload, ssl=AIOHTTP_CLIENT_SESSION_SSL) as r:
                r_text = await r.text()
                r.raise_for_status()
                log.debug(f'r.text: {r_text}')

        return True
    except Exception as e:
        log.exception(e)
        return False


# ---------------------------------------------------------------------------
# Multi-webhook / event-scope helpers
# ---------------------------------------------------------------------------

# Canonical event names used across the codebase.
WEBHOOK_EVENTS = {
    'signup',            # new user registered via password form
    'oauth_signup',      # new user created through OAuth / OIDC / SAML flow
    'signin',            # existing user signed in (optional, disabled by default)
    'signout',           # user signed out
    'user_deleted',      # admin deleted a user
    'user_role_changed', # admin changed a user's role
}


def _parse_webhook_config(raw: str) -> list[dict]:
    """Parse the WEBHOOK_URL config value.

    Accepts two formats:

    1. **Legacy / simple** – a single URL string (no event filtering):
       ``https://hooks.slack.com/services/xxx``

    2. **Extended** – a newline-separated or comma-separated list of JSON
       objects, each with a ``url`` key and an optional ``events`` list::

           {"url": "https://hooks.slack.com/...", "events": ["signup"]}
           {"url": "https://discord.com/api/webhooks/...", "events": ["signin", "signout"]}

       Or as a JSON array::

           [
             {"url": "https://...", "events": ["signup", "oauth_signup"]},
             {"url": "https://...", "events": null}
           ]

    Returns a list of dicts: ``[{"url": str, "events": set[str] | None}]``.
    ``events=None`` means "fire for every event" (legacy / catch-all behaviour).
    """
    if not raw or not raw.strip():
        return []

    raw = raw.strip()

    # Attempt to treat the whole value as a JSON array first.
    if raw.startswith('['):
        try:
            entries = json.loads(raw)
            result = []
            for entry in entries:
                if isinstance(entry, str):
                    result.append({'url': entry, 'events': None})
                elif isinstance(entry, dict) and entry.get('url'):
                    events = entry.get('events')
                    result.append({
                        'url': entry['url'],
                        'events': set(events) if events else None,
                    })
            return result
        except json.JSONDecodeError:
            pass

    # Try splitting by newline then comma.
    parts = [p.strip() for line in raw.splitlines() for p in line.split(',') if p.strip()]
    result = []
    for part in parts:
        if part.startswith('{'):
            try:
                entry = json.loads(part)
                if entry.get('url'):
                    events = entry.get('events')
                    result.append({
                        'url': entry['url'],
                        'events': set(events) if events else None,
                    })
                continue
            except json.JSONDecodeError:
                pass
        # Plain URL – no event filter (legacy behaviour).
        result.append({'url': part, 'events': None})

    return result


async def post_webhook_event(
    name: str,
    webhook_url_config: str,
    message: str,
    event_data: dict,
    event: str | None = None,
) -> list[bool]:
    """Dispatch a webhook for a specific *event* to all matching configured URLs.

    Parameters
    ----------
    name:
        Display name of the Open WebUI instance (``request.app.state.WEBUI_NAME``).
    webhook_url_config:
        The raw value of ``WEBHOOK_URL`` from app config (string, possibly
        containing multiple URLs / JSON entries).
    message:
        Human-readable summary line.
    event_data:
        Arbitrary dict of event metadata; passed through to ``post_webhook``.
    event:
        One of :data:`WEBHOOK_EVENTS`.  If *None*, the payload is sent to every
        configured URL (backwards-compatible behaviour for callers that have not
        been updated yet).
    """
    if not webhook_url_config:
        return []

    # Attach event name to the payload so downstream systems can filter.
    if event:
        event_data = {**event_data, 'event': event}

    entries = _parse_webhook_config(webhook_url_config)
    results = []
    for entry in entries:
        allowed = entry.get('events')
        # None means "all events"; otherwise check membership.
        if allowed is not None and event not in allowed:
            log.debug(f'Skipping webhook {entry["url"]} for event {event!r} (not in {allowed})')
            continue
        ok = await post_webhook(name, entry['url'], message, event_data)
        results.append(ok)

    return results
