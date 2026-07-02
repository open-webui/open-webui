import asyncio
import json
import logging

from open_webui.config import WEBUI_FAVICON_URL
from open_webui.env import (
    AIOHTTP_CLIENT_ALLOW_REDIRECTS,
    AIOHTTP_CLIENT_SESSION_SSL,
    VERSION,
)
from open_webui.retrieval.web.utils import get_ssrf_safe_session, validate_url

log = logging.getLogger(__name__)


# Let this message reach those for whom it was written, and
# may no network partition deny the word its destination.
def _event_text(message: str, description: str | None = None, event_data: dict | None = None) -> str:
    lines = [message]
    if description and description != message:
        lines.append(description)

    event_name = (event_data or {}).get('event')
    if event_name:
        lines.append(f'Event: {event_name}')

    return '\n'.join(lines)


async def post_webhook(name: str, url: str, message: str, event_data: dict, description: str | None = None) -> bool:
    try:
        log.debug(f'post_webhook: {url}, {message}, {event_data}')
        # Block private-IP / loopback / cloud-metadata targets — the URL is
        # caller-controlled (user notification settings under
        # ENABLE_USER_WEBHOOKS, automation notification triggers).
        await asyncio.to_thread(validate_url, url)
        payload = {}

        # Slack and Google Chat Webhooks
        if 'https://hooks.slack.com' in url or 'https://chat.googleapis.com' in url:
            payload['text'] = _event_text(message, description, event_data)
        # Discord Webhooks
        elif 'https://discord.com/api/webhooks' in url:
            content = _event_text(message, description, event_data)
            payload['content'] = content if len(content) < 2000 else f'{content[: 2000 - 20]}... (truncated)'
        # Microsoft Teams Webhooks
        elif 'webhook.office.com' in url:
            action = event_data.get('action', 'undefined')
            user_data = event_data.get('user') or event_data.get('actor') or {}
            if isinstance(user_data, dict):
                user_dict = user_data
            else:
                user_dict = json.loads(user_data)
            facts = [{'name': key, 'value': value} for key, value in user_dict.items()]
            if event_data.get('event'):
                facts.insert(0, {'name': 'event', 'value': event_data.get('event')})
            if description:
                facts.insert(0, {'name': 'description', 'value': description})
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
                        'text': description,
                        'facts': facts,
                        'markdown': True,
                    }
                ],
            }
        # Default Payload
        else:
            payload = event_data

        log.debug(f'payload: {payload}')
        async with get_ssrf_safe_session() as session:
            async with session.post(
                url,
                json=payload,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
                allow_redirects=AIOHTTP_CLIENT_ALLOW_REDIRECTS,
            ) as r:
                r_text = await r.text()
                r.raise_for_status()
                log.debug(f'r.text: {r_text}')

        return True
    except Exception as e:
        log.exception(e)
        return False
