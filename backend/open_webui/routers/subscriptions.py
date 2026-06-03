import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.models.subscriptions import (
    SubscriptionOrders,
    SubscriptionTierForm,
    SubscriptionTiers,
    UserSubscriptions,
)
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.subscription import (
    create_subscription_order,
    get_subscription_state,
    seed_default_tiers,
    sync_order,
)

log = logging.getLogger(__name__)

router = APIRouter()


class SubscribeForm(BaseModel):
    tier_id: str
    chain_id: str


############################
# User-facing endpoints
############################


@router.get('/tiers')
async def get_tiers(user=Depends(get_verified_user)):
    """Enabled tiers for the subscription page."""
    return await SubscriptionTiers.list_tiers(enabled_only=True)


@router.get('/chains')
async def get_chains(request: Request, user=Depends(get_verified_user)):
    return request.app.state.config.SUBSCRIPTION_CHAINS or []


@router.get('/me')
async def get_me(user=Depends(get_verified_user)):
    """Current effective tier + today's usage + active subscription."""
    return await get_subscription_state(user.id, is_admin=(user.role == 'admin'))


@router.post('/subscribe')
async def subscribe(request: Request, form_data: SubscribeForm, user=Depends(get_verified_user)):
    """Create a USDT payment order for a tier; returns the checkout payload (address + QR)."""
    if not getattr(request.app.state.config, 'ENABLE_SUBSCRIPTIONS', True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Subscriptions are disabled')
    return await create_subscription_order(request, user, form_data.tier_id, form_data.chain_id)


@router.get('/order/{order_id}')
async def get_order(request: Request, order_id: str, user=Depends(get_verified_user)):
    """Poll order status; activates the subscription on first PAID."""
    return await sync_order(request, user, order_id)


@router.get('/orders')
async def list_my_orders(user=Depends(get_verified_user)):
    return await SubscriptionOrders.list_for_user(user.id)


############################
# Admin endpoints
############################


@router.get('/admin/tiers')
async def admin_list_tiers(user=Depends(get_admin_user)):
    return await SubscriptionTiers.list_tiers(enabled_only=False)


@router.post('/admin/tiers')
async def admin_upsert_tier(form_data: SubscriptionTierForm, user=Depends(get_admin_user)):
    tier_id = (form_data.id or '').strip().lower()
    if not tier_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Tier id is required')
    form_data.id = tier_id
    tier = await SubscriptionTiers.upsert_tier(form_data)
    if tier is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Failed to save tier')
    return tier


@router.delete('/admin/tiers/{tier_id}')
async def admin_delete_tier(tier_id: str, user=Depends(get_admin_user)):
    from open_webui.utils.subscription import DEFAULT_TIER_ID

    if tier_id == DEFAULT_TIER_ID:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='The default free tier cannot be deleted')
    ok = await SubscriptionTiers.delete_tier(tier_id)
    return {'success': ok}


@router.post('/admin/seed')
async def admin_seed_tiers(user=Depends(get_admin_user)):
    """Seed the default tiers (no-op if any tier already exists)."""
    await seed_default_tiers()
    return await SubscriptionTiers.list_tiers(enabled_only=False)


@router.get('/admin/subscriptions')
async def admin_list_subscriptions(user=Depends(get_admin_user)):
    return await UserSubscriptions.list_all()
