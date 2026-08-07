from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from typing import Any
from urllib.parse import urlparse

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy.exc import IntegrityError

from open_webui.internal.db import get_async_db
from open_webui.models.config import Config

log = logging.getLogger(__name__)

VAPID_PUBLIC_KEY_CONFIG = 'webpush.vapid_public_key'
VAPID_PRIVATE_KEY_CONFIG = 'webpush.vapid_private_key'

_generation_lock = asyncio.Lock()
_warned_default_subject = False


class WebPushSubscriptionGone(Exception):
    """The push service reports the subscription no longer exists."""


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip('=')


async def get_vapid_keys() -> tuple[str, str]:
    """Return (public_key, private_key), generating and persisting them on first use."""
    public_key = await Config.get(VAPID_PUBLIC_KEY_CONFIG)
    private_key = await Config.get(VAPID_PRIVATE_KEY_CONFIG)
    if public_key and private_key:
        return public_key, private_key

    async with _generation_lock:
        return await _generate_vapid_keys()


async def _generate_vapid_keys() -> tuple[str, str]:
    # Re-check under the lock; another caller may have generated meanwhile
    public_key = await Config.get(VAPID_PUBLIC_KEY_CONFIG)
    private_key = await Config.get(VAPID_PRIVATE_KEY_CONFIG)
    if public_key and private_key:
        return public_key, private_key

    key = ec.generate_private_key(ec.SECP256R1())
    private_key = _b64url(key.private_numbers().private_value.to_bytes(32, 'big'))
    public_key = _b64url(
        key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    )

    if Config.persistent_enabled_for(VAPID_PRIVATE_KEY_CONFIG):
        # Insert-if-absent so concurrent workers can never overwrite a pair a
        # client may already have subscribed against
        now = int(time.time())
        async with get_async_db() as db:
            db.add(Config(key=VAPID_PUBLIC_KEY_CONFIG, value=public_key, updated_at=now))
            db.add(Config(key=VAPID_PRIVATE_KEY_CONFIG, value=private_key, updated_at=now))
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
    else:
        await Config.upsert({VAPID_PUBLIC_KEY_CONFIG: public_key, VAPID_PRIVATE_KEY_CONFIG: private_key})

    stored_public = await Config.get(VAPID_PUBLIC_KEY_CONFIG)
    stored_private = await Config.get(VAPID_PRIVATE_KEY_CONFIG)
    if not (stored_public and stored_private):
        # A half-present pair (e.g. from a partial config import) is unusable; overwrite it
        await Config.upsert({VAPID_PUBLIC_KEY_CONFIG: public_key, VAPID_PRIVATE_KEY_CONFIG: private_key})
        return public_key, private_key
    return stored_public, stored_private


async def send_web_push(subscription: dict[str, Any], payload: dict[str, Any]) -> None:
    import requests

    from pywebpush import WebPushException, webpush

    from open_webui.retrieval.web.utils import _SSRFSafeAdapter, validate_url

    endpoint = str(subscription.get('endpoint') or '')
    if not endpoint.startswith('https://'):
        raise ValueError('Push subscription endpoint must be an https URL')

    _, private_key = await get_vapid_keys()

    # VAPID sub must be an https origin or a mailto address
    webui_url = urlparse(str(await Config.get('webui.url') or ''))
    if webui_url.scheme == 'https' and webui_url.hostname:
        subject = f'https://{webui_url.hostname}' + (f':{webui_url.port}' if webui_url.port else '')
    else:
        admin_email = str(await Config.get('auth.admin.email') or '').strip()
        subject = f'mailto:{admin_email or "admin@localhost"}'
        if not admin_email:
            global _warned_default_subject
            if not _warned_default_subject:
                _warned_default_subject = True
                log.warning(
                    'WEBUI_URL is not https and no admin email is set; using %s as the VAPID subject, which some push services reject',
                    subject,
                )

    def _send():
        # Validate in the worker thread (blocking DNS) and send through the
        # connect-time SSRF guard; bare requests re-resolves (DNS-rebinding gap)
        validate_url(endpoint)
        with requests.Session() as session:
            session.mount('http://', _SSRFSafeAdapter())
            session.mount('https://', _SSRFSafeAdapter())
            webpush(
                subscription_info=subscription,
                data=json.dumps(payload),
                vapid_private_key=private_key,
                vapid_claims={'sub': subject},
                ttl=24 * 60 * 60,
                timeout=10,
                requests_session=session,
            )

    try:
        await asyncio.to_thread(_send)
    except WebPushException as e:
        status_code = getattr(getattr(e, 'response', None), 'status_code', None)
        # 401/403 mean the VAPID keys no longer match; the subscription can never work again
        if status_code in (401, 403, 404, 410):
            raise WebPushSubscriptionGone('Push subscription expired') from e
        log.warning('Web push delivery failed: %s', e)
        raise ValueError('Web push delivery failed') from e
    except Exception as e:
        # Network errors and encryption failures from pywebpush arrive untyped
        log.warning('Web push delivery failed: %s', e)
        raise ValueError('Web push delivery failed') from e
