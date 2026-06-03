"""Subscription business logic: tier resolution, enforcement, payment_service client,
activation and default-tier seeding. See SUBSCRIPTION.md."""

import logging
import time
import uuid
from typing import Optional

import aiohttp
from fastapi import HTTPException, Request, status

from open_webui.models.subscriptions import (
    SubscriptionOrders,
    SubscriptionTierForm,
    SubscriptionTierModel,
    SubscriptionTiers,
    SubscriptionUsage,
    UserSubscriptionModel,
    UserSubscriptions,
)

log = logging.getLogger(__name__)

DEFAULT_TIER_ID = 'free'
ORDER_TTL_SECONDS = 24 * 60 * 60  # payment_service orders expire after 24h


def utc_date() -> str:
    return time.strftime('%Y-%m-%d', time.gmtime())


def _fmt_amount(value: float) -> str:
    s = f'{value:.6f}'.rstrip('0').rstrip('.')
    return s or '0'


####################
# Tier resolution
####################


async def get_user_tier(user_id: str) -> tuple[Optional[SubscriptionTierModel], Optional[UserSubscriptionModel]]:
    """Resolve a user's effective tier. Returns (tier, active_subscription).
    Falls back to the default 'free' tier when there's no active paid subscription."""
    sub = await UserSubscriptions.get_active_for_user(user_id)
    if sub:
        tier = await SubscriptionTiers.get_tier(sub.tier_id)
        if tier and tier.enabled:
            return tier, sub
    tier = await SubscriptionTiers.get_tier(DEFAULT_TIER_ID)
    return tier, None


async def get_subscription_state(user_id: str, is_admin: bool = False) -> dict:
    """State for the /me endpoint: effective tier, today's usage, remaining, expiry."""
    tier, sub = await get_user_tier(user_id)
    limit = None if (is_admin or tier is None) else tier.daily_message_limit
    used = 0
    if limit is not None:
        used = await SubscriptionUsage.get_count(user_id, utc_date())
    return {
        'tier': tier.model_dump() if tier else None,
        'subscription': sub.model_dump() if sub else None,
        'expires_at': sub.expires_at if sub else None,
        'usage': {
            'date': utc_date(),
            'used': used,
            'limit': limit,
            'remaining': (None if limit is None else max(0, limit - used)),
        },
        'is_admin': is_admin,
    }


####################
# Enforcement (called from main.py chat_completion)
####################


async def enforce_subscription_access(request: Request, user, model_id: str) -> None:
    """Raise HTTP 403 (model not in tier) or 429 (daily quota reached) for a
    non-admin user's managed chat completion. Increments the daily counter when a
    finite limit applies. Admins and disabled subscriptions are no-ops."""
    if not getattr(request.app.state.config, 'ENABLE_SUBSCRIPTIONS', True):
        return
    if getattr(user, 'role', None) == 'admin':
        return

    tier, _ = await get_user_tier(user.id)
    if tier is None:
        # Subscriptions enabled but no tiers configured/seeded yet → don't block.
        return

    # 1) Model allow-list (empty / None = all models allowed)
    allowed = tier.allowed_model_ids
    if allowed and model_id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"The model '{model_id}' isn't included in your {tier.name} plan. Upgrade to use it.",
        )

    # 2) Daily message quota
    limit = tier.daily_message_limit
    if limit is not None:
        date = utc_date()
        used = await SubscriptionUsage.get_count(user.id, date)
        if used >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"You've reached your daily limit of {limit} messages on the {tier.name} plan. "
                    'Upgrade your subscription for more.'
                ),
            )
        await SubscriptionUsage.increment(user.id, date)


def filter_models_by_tier(models: list, tier: Optional[SubscriptionTierModel]) -> list:
    """Drop models not permitted by the tier (used to shape the visible model list).
    Each item is a model dict with an 'id'. Empty/None allow-list = no filtering."""
    if tier is None:
        return models
    allowed = tier.allowed_model_ids
    if not allowed:
        return models
    allowed_set = set(allowed)
    return [m for m in models if (m.get('id') if isinstance(m, dict) else getattr(m, 'id', None)) in allowed_set]


####################
# payment_service client
####################


def _payment_base(request: Request) -> str:
    return str(request.app.state.config.PAYMENT_SERVICE_URL).rstrip('/')


def _is_payment_error(data) -> Optional[str]:
    """payment_service returns OrderResponseDTO on success and a ResultDTO
    ({code, message}) on error (both HTTP 200). Return an error message if this
    looks like an error envelope, else None."""
    if not isinstance(data, dict):
        return 'Invalid response from payment service'
    if 'address' in data or 'status' in data:
        return None
    if 'message' in data:
        return str(data.get('message'))
    if 'code' in data:
        return f"payment service error (code {data.get('code')})"
    return 'Unexpected response from payment service'


async def _payment_create(request: Request, order_id: str, chain_id: str, amount: str) -> dict:
    url = f'{_payment_base(request)}/payment/create'
    payload = {'orderId': order_id, 'chainId': chain_id, 'amount': amount}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25)) as session:
        async with session.post(url, json=payload) as resp:
            return await resp.json(content_type=None)


async def _payment_status(request: Request, order_id: str) -> dict:
    url = f'{_payment_base(request)}/payment/status/{order_id}'
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        async with session.get(url) as resp:
            return await resp.json(content_type=None)


####################
# Subscription flow
####################


async def create_subscription_order(request: Request, user, tier_id: str, chain_id: str) -> dict:
    """Create a payment intent for `tier_id` on `chain_id`, register it with the
    Java payment_service, persist it, and return the checkout payload for the UI."""
    tier = await SubscriptionTiers.get_tier(tier_id)
    if tier is None or not tier.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Subscription plan not found')
    if tier.price_usd <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='This plan is free and cannot be purchased')

    valid_chains = {c.get('id') for c in (request.app.state.config.SUBSCRIPTION_CHAINS or [])}
    if valid_chains and chain_id not in valid_chains:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unsupported payment chain')

    logical_id = f'owui-{uuid.uuid4().hex}'
    amount = _fmt_amount(tier.price_usd)

    try:
        data = await _payment_create(request, logical_id, chain_id, amount)
    except Exception as e:
        log.exception('payment_service create failed')
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'Could not reach payment service: {e}',
        )

    err = _is_payment_error(data)
    if err:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=err)

    composite_id = data.get('orderId') or f'{logical_id}_{chain_id}'
    address = data.get('address')
    if not address:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail='Payment service did not return an address')

    qr = data.get('qrCodeImage')
    order_status = data.get('status', 'PENDING')
    expires_at = int(time.time()) + ORDER_TTL_SECONDS

    await SubscriptionOrders.insert(
        order_id=composite_id,
        logical_order_id=logical_id,
        user_id=user.id,
        tier_id=tier_id,
        chain_id=chain_id,
        amount=amount,
        address=address,
        status=order_status,
        expires_at=expires_at,
    )

    return {
        'order_id': composite_id,
        'tier_id': tier_id,
        'tier_name': tier.name,
        'chain_id': chain_id,
        'amount': amount,
        'address': address,
        'qr_code_image': qr,
        'status': order_status,
        'expires_at': expires_at,
    }


async def sync_order(request: Request, user, order_id: str) -> dict:
    """Poll the payment_service for `order_id`; on first PAID, grant/extend the
    subscription (idempotent). Returns order status + current subscription state."""
    order = await SubscriptionOrders.get(order_id)
    if order is None or order.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')

    activated_now = False
    current_status = order.status
    tx_hash = order.tx_hash

    if not order.activated:
        try:
            data = await _payment_status(request, order_id)
            err = _is_payment_error(data)
            if not err:
                current_status = data.get('status', order.status)
                tx_hash = data.get('txHash', tx_hash)
        except Exception:
            log.exception('payment_service status check failed for %s', order_id)
            current_status = order.status

        if current_status != order.status or tx_hash != order.tx_hash:
            await SubscriptionOrders.update_status(order_id, current_status, tx_hash=tx_hash)

        if current_status == 'PAID':
            tier = await SubscriptionTiers.get_tier(order.tier_id)
            duration = tier.duration_days if tier else 30
            await UserSubscriptions.create_or_extend(user.id, order.tier_id, duration, order_id=order_id)
            await SubscriptionOrders.update_status(order_id, 'PAID', tx_hash=tx_hash, activated=True)
            activated_now = True

    state = await get_subscription_state(user.id, is_admin=(getattr(user, 'role', None) == 'admin'))
    return {
        'order_id': order_id,
        'status': current_status if not order.activated else 'PAID',
        'tx_hash': tx_hash,
        'activated': activated_now or order.activated,
        'subscription_state': state,
    }


####################
# Seeding
####################

DEFAULT_TIERS = [
    SubscriptionTierForm(
        id='free', name='Free', description='Get started — limited daily messages.',
        price_usd=0.0, duration_days=36500, daily_message_limit=10,
        allowed_model_ids=[], enabled=True, sort_order=0,
    ),
    SubscriptionTierForm(
        id='pro', name='Pro', description='For regular use.',
        price_usd=9.99, duration_days=30, daily_message_limit=100,
        allowed_model_ids=[], enabled=True, sort_order=1,
    ),
    SubscriptionTierForm(
        id='max', name='Max', description='For power users.',
        price_usd=29.99, duration_days=30, daily_message_limit=500,
        allowed_model_ids=[], enabled=True, sort_order=2,
    ),
    SubscriptionTierForm(
        id='ultra', name='Ultra', description='Unlimited messages.',
        price_usd=99.99, duration_days=30, daily_message_limit=None,
        allowed_model_ids=[], enabled=True, sort_order=3,
    ),
]


async def seed_default_tiers() -> None:
    """Create the default Free/Pro/Max/Ultra tiers if none exist. Admin-editable afterwards."""
    try:
        if await SubscriptionTiers.count() > 0:
            return
        for form in DEFAULT_TIERS:
            await SubscriptionTiers.upsert_tier(form)
        log.info('Seeded %d default subscription tiers', len(DEFAULT_TIERS))
    except Exception:
        log.exception('Failed to seed default subscription tiers')
