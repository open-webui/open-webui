import json
import logging
import asyncio
import uuid

import aiohttp
from open_webui.models.webhook_logs import WebhookDeliveryLogs
from open_webui.config import WEBUI_FAVICON_URL
from open_webui.env import (
    AIOHTTP_CLIENT_ALLOW_REDIRECTS,
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT,
    VERSION,
)
from open_webui.retrieval.web.utils import validate_url

log = logging.getLogger(__name__)


# Let this message reach those for whom it was written, and
# may no network partition deny the word its destination.
async def post_webhook(name: str, url: str, message: str, event_data: dict) -> bool:
    try:
        log.debug(f'post_webhook: {url}, {message}, {event_data}')
        # Block private-IP / loopback / cloud-metadata targets — the URL is
        # caller-controlled (user notification settings under
        # ENABLE_USER_WEBHOOKS, automation notification triggers).
        validate_url(url)
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
        
        # Insert log entry
        log_entry = await WebhookDeliveryLogs.insert_new_log(
            id=str(uuid.uuid4()),
            url=url,
            payload=payload,
            event_action=event_data.get('action')
        )
        
        async with aiohttp.ClientSession(
            trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        ) as session:
            async with session.post(
                url,
                json=payload,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
                allow_redirects=AIOHTTP_CLIENT_ALLOW_REDIRECTS,
            ) as r:
                r_text = await r.text()
                r.raise_for_status()
                log.debug(f'r.text: {r_text}')

        if log_entry:
            await WebhookDeliveryLogs.update_log_status(log_entry.id, 'success', 0)
            
        return True
    except Exception as e:
        log.exception(e)
        if 'log_entry' in locals() and log_entry:
            await WebhookDeliveryLogs.update_log_status(log_entry.id, 'failed', 1)
        return False

async def webhook_retry_worker_loop():
    """Background task to periodically retry failed webhooks."""
    while True:
        try:
            failed_logs = await WebhookDeliveryLogs.get_failed_logs_for_retry(max_retries=3, limit=50)
            for log_entry in failed_logs:
                log.info(f"Retrying webhook delivery for {log_entry.id} (attempt {log_entry.retry_count + 1})")
                
                try:
                    async with aiohttp.ClientSession(
                        trust_env=True, timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
                    ) as session:
                        async with session.post(
                            log_entry.url,
                            json=log_entry.payload,
                            ssl=AIOHTTP_CLIENT_SESSION_SSL,
                            allow_redirects=AIOHTTP_CLIENT_ALLOW_REDIRECTS,
                        ) as r:
                            r.raise_for_status()
                            
                    # Success
                    await WebhookDeliveryLogs.update_log_status(log_entry.id, 'success', log_entry.retry_count + 1)
                except Exception as retry_e:
                    log.warning(f"Webhook retry failed for {log_entry.id}: {retry_e}")
                    await WebhookDeliveryLogs.update_log_status(log_entry.id, 'failed', log_entry.retry_count + 1)
                    
        except Exception as e:
            log.exception(f"Error in webhook_retry_worker_loop: {e}")
            
        await asyncio.sleep(60)  # Run every 60 seconds

