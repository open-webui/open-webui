"""Admin endpoints for user spending limits, cost analytics, and client management.

Routes:
  GET  /api/spending           — admin view of all users' spending
  GET  /api/spending/me        — current user's spending
  PUT  /api/spending/{user_id} — admin sets a user's monthly limit
  GET  /api/spending/models    — cost breakdown by model
  POST /api/spending/clients   — admin creates a client user (simplified UI, fixed model, fixed prompt)
"""

from __future__ import annotations

import logging
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.cost_tracker import (
    DEFAULT_MONTHLY_LIMIT_USD,
    get_all_user_spending,
    get_current_ist_month,
    get_user_spending,
    record_spend,
    set_user_limit,
)
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter()


class LimitUpdateRequest(BaseModel):
    monthly_limit_usd: float


class LimitUpdateResponse(BaseModel):
    user_id: str
    monthly_limit_usd: float
    message: str


class SpendingResponse(BaseModel):
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    month: str
    spent: float
    limit: float
    remaining: float


class ModelCostEntry(BaseModel):
    model_id: str
    tier: str
    description: str
    input_price: float
    output_price: float


@router.get('/')
async def get_all_spending(
    month: Optional[str] = Query(None, description='YYYY-MM (IST). Defaults to current month.'),
    user=Depends(get_admin_user),
):
    """Admin: get spending for all users."""
    month = month or get_current_ist_month()
    data = await get_all_user_spending(month)
    return {'month': month, 'users': data, 'total_spent': round(sum(u['spent'] for u in data), 4)}


@router.get('/me')
async def get_my_spending(user=Depends(get_verified_user)):
    """Get current user's own spending."""
    data = await get_user_spending(user.id)
    return {
        'user_id': user.id,
        'name': user.name,
        'month': data['month'],
        'spent': data['spent'],
        'limit': data['limit'],
        'remaining': data['remaining'],
        'usage_percent': round(data['spent'] / data['limit'] * 100, 1) if data['limit'] > 0 else 0,
    }


@router.put('/{user_id}', response_model=LimitUpdateResponse)
async def update_user_limit(
    user_id: str,
    body: LimitUpdateRequest,
    admin=Depends(get_admin_user),
):
    """Admin: set a user's monthly spending limit."""
    if body.monthly_limit_usd < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Limit must be >= 0',
        )

    result = await set_user_limit(user_id, body.monthly_limit_usd)
    return LimitUpdateResponse(
        user_id=user_id,
        monthly_limit_usd=result['monthly_limit_usd'],
        message=f'Limit set to ${body.monthly_limit_usd:.2f}/month for user {user_id}',
    )


@router.get('/models')
async def get_model_costs(user=Depends(get_verified_user)):
    """Get curated model list with pricing (visible to all users)."""
    from open_webui.utils.cost_tracker import _load_model_prices
    prices = _load_model_prices()
    models = []
    for model_id, info in prices.items():
        if not isinstance(info, dict):
            continue
        entry = {
            'model_id': model_id,
            'tier': info.get('tier', 'Unknown'),
            'description': info.get('description', ''),
            'provider': info.get('provider', 'unknown'),
            'color': _get_tier_color(info.get('tier', '')),
        }
        # Token-based pricing (LLMs)
        if 'input' in info and 'output' in info:
            entry['input_price_per_1m'] = info.get('input', 0)
            entry['output_price_per_1m'] = info.get('output', 0)
            entry['price_type'] = 'per_1m_tokens'
        # Image generation
        elif info.get('image_per_1024x1024'):
            entry['price_per_image'] = info.get('image_per_1024x1024', 0)
            entry['price_type'] = 'per_image'
        # TTS
        elif info.get('tts_per_1m_chars'):
            entry['price_per_1m_chars'] = info.get('tts_per_1m_chars', 0)
            entry['price_type'] = 'per_1m_chars'
        # STT
        elif info.get('stt_per_minute'):
            entry['price_per_minute'] = info.get('stt_per_minute', 0)
            entry['price_type'] = 'per_minute'
        else:
            continue
        models.append(entry)
    return {'models': sorted(models, key=lambda x: x.get('input_price_per_1m', x.get('price_per_image', x.get('price_per_1m_chars', x.get('price_per_minute', 0)))))}


def _get_tier_color(tier: str) -> str:
    colors = {
        'Nano': '#22c55e',
        'Medium': '#3b82f6',
        'Standard': '#f59e0b',
        'Reasoning': '#8b5cf6',
        'Vision': '#06b6d4',
        'Flagship': '#ef4444',
        'ImageGen': '#ec4899',
        'ImageEdit': '#d946ef',
        'TTS': '#f97316',
        'STT': '#a855f7',
        'Embedding': '#6b7280',
    }
    return colors.get(tier, '#6b7280')


@router.get('/trends')
async def get_spending_trends(
    months: int = Query(6, ge=2, le=12, description='Number of months to include (2-12)'),
    user=Depends(get_admin_user),
):
    """Get spending trends over multiple months for chart visualization."""
    from open_webui.models.users import Users
    from open_webui.utils.cost_tracker import get_current_ist_month

    # Generate list of months (YYYY-MM) going backwards from current
    current_month_str = get_current_ist_month()
    current_year = int(current_month_str.split('-')[0])
    current_month = int(current_month_str.split('-')[1])

    month_labels = []
    for i in range(months - 1, -1, -1):
        year = current_year
        month = current_month - i
        while month <= 0:
            month += 12
            year -= 1
        month_labels.append(f'{year}-{month:02d}')

    # Get all users
    all_users = await Users.get_users()
    users_data = []

    for u in all_users.get('users', []):
        info = u.info or {}
        spending_by_month = info.get('spending', {})

        monthly_spending = []
        for m in month_labels:
            month_data = spending_by_month.get(m, {'spent': 0.0, 'limit': 0.0})
            monthly_spending.append({
                'month': m,
                'spent': round(month_data.get('spent', 0.0), 4),
                'limit': round(month_data.get('limit', info.get('monthly_limit_usd', DEFAULT_MONTHLY_LIMIT_USD)), 2),
            })

        users_data.append({
            'user_id': u.id,
            'name': u.name,
            'email': u.email,
            'role': u.role,
            'monthly_data': monthly_spending,
        })

    # Calculate totals per month across all users
    totals = []
    for i, m in enumerate(month_labels):
        total_spent = sum(u['monthly_data'][i]['spent'] for u in users_data)
        total_limit = sum(u['monthly_data'][i]['limit'] for u in users_data)
        totals.append({
            'month': m,
            'total_spent': round(total_spent, 2),
            'total_limit': round(total_limit, 2),
        })

    return {
        'months': month_labels,
        'users': users_data,
        'totals': totals,
    }


# ---------------------------------------------------------------------------
# Client Management — Admin-only client user creation (simplified UI)
# ---------------------------------------------------------------------------

class CreateClientRequest(BaseModel):
    email: str
    name: str
    fixed_model_id: str
    fixed_system_prompt: str
    assigned_kb_ids: list[str] = []
    kb_rag_query: str = ''
    monthly_limit_usd: Optional[float] = None


class CreateClientResponse(BaseModel):
    user_id: str
    email: str
    temp_password: str
    message: str


@router.post('/clients', response_model=CreateClientResponse)
async def create_client_user(
    request_body: CreateClientRequest,
    admin=Depends(get_admin_user),
):
    """Admin creates a simplified client user.

    Client users get:
      - locked to a single model (fixed_model_id)
      - a fixed system prompt injected into every chat
      - access only to assigned knowledge bases
      - a simplified UI (no model picker, no folders, no settings)

    Returns a temporary password the admin must share with the client.
    """
    from open_webui.models.auths import Auths
    from open_webui.models.users import Users
    from open_webui.utils.misc import validate_email_format

    email = request_body.email.lower().strip()
    if not validate_email_format(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid email format',
        )

    existing = await Users.get_user_by_email(email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Email already registered',
        )

    temp_password = secrets.token_urlsafe(12)

    from open_webui.utils.auth import get_password_hash
    hashed = await get_password_hash(temp_password)

    user = await Auths.insert_new_auth(
        email=email,
        password=hashed,
        name=request_body.name,
        role='user',
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to create client user',
        )

    # Store client config in user.info (no schema migration needed)
    client_info = {
        'user_type': 'client',
        'fixed_model_id': request_body.fixed_model_id,
        'fixed_system_prompt': request_body.fixed_system_prompt.strip(),
        'assigned_kb_ids': request_body.assigned_kb_ids,
        'kb_rag_query': request_body.kb_rag_query.strip(),
    }
    await Users.update_user_by_id(user.id, {'info': client_info})

    # Set custom monthly limit if provided
    if request_body.monthly_limit_usd is not None and request_body.monthly_limit_usd >= 0:
        await set_user_limit(user.id, request_body.monthly_limit_usd)

    log.info(f'Admin {admin.id} created client user {user.id} ({email}) with model {request_body.fixed_model_id}')

    return CreateClientResponse(
        user_id=user.id,
        email=email,
        temp_password=temp_password,
        message=f'Client user created. Share the temporary password securely with {email}.',
    )



class ClientUserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    fixed_model_id: str
    fixed_system_prompt: str
    assigned_kb_ids: list[str]
    kb_rag_query: str
    monthly_limit_usd: float
    created_at: Optional[int] = None


@router.get('/clients', response_model=list[ClientUserResponse])
async def list_client_users(admin=Depends(get_admin_user)):
    """List all client users with their configuration."""
    from open_webui.models.users import Users
    all_users = await Users.get_users()
    clients = []
    for u in all_users.get('users', []):
        info = u.info or {}
        if info.get('user_type') == 'client':
            spending = info.get('spending', {})
            current_month = get_current_ist_month()
            month_data = spending.get(current_month, {})
            clients.append({
                'user_id': u.id,
                'email': u.email,
                'name': u.name,
                'fixed_model_id': info.get('fixed_model_id', ''),
                'fixed_system_prompt': info.get('fixed_system_prompt', ''),
                'assigned_kb_ids': info.get('assigned_kb_ids', []),
                'kb_rag_query': info.get('kb_rag_query', ''),
                'monthly_limit_usd': info.get('monthly_limit_usd', DEFAULT_MONTHLY_LIMIT_USD),
                'created_at': getattr(u, 'created_at', None),
            })
    return clients


class UpdateClientRequest(BaseModel):
    name: Optional[str] = None
    fixed_model_id: Optional[str] = None
    fixed_system_prompt: Optional[str] = None
    assigned_kb_ids: Optional[list[str]] = None
    kb_rag_query: Optional[str] = None
    monthly_limit_usd: Optional[float] = None


@router.put('/clients/{user_id}')
async def update_client_user(
    user_id: str,
    request_body: UpdateClientRequest,
    admin=Depends(get_admin_user),
):
    """Update a client user's configuration."""
    from open_webui.models.users import Users
    user = await Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    info = user.info or {}
    if info.get('user_type') != 'client':
        raise HTTPException(status_code=400, detail='User is not a client')

    if request_body.name is not None:
        await Users.update_user_by_id(user_id, {'name': request_body.name})

    updates = {}
    if request_body.fixed_model_id is not None:
        updates['fixed_model_id'] = request_body.fixed_model_id
    if request_body.fixed_system_prompt is not None:
        updates['fixed_system_prompt'] = request_body.fixed_system_prompt.strip()
    if request_body.assigned_kb_ids is not None:
        updates['assigned_kb_ids'] = request_body.assigned_kb_ids
    if request_body.kb_rag_query is not None:
        updates['kb_rag_query'] = request_body.kb_rag_query.strip()

    if updates:
        info.update(updates)
        await Users.update_user_by_id(user_id, {'info': info})

    if request_body.monthly_limit_usd is not None and request_body.monthly_limit_usd >= 0:
        await set_user_limit(user_id, request_body.monthly_limit_usd)

    return {'message': f'Client {user_id} updated successfully'}


@router.delete('/clients/{user_id}')
async def delete_client_user(user_id: str, admin=Depends(get_admin_user)):
    """Delete a client user permanently."""
    from open_webui.models.users import Users
    user = await Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    info = user.info or {}
    if info.get('user_type') != 'client':
        raise HTTPException(status_code=400, detail='User is not a client')

    await Users.delete_user_by_id(user_id)
    log.info(f'Admin {admin.id} deleted client user {user_id}')
    return {'message': f'Client {user_id} deleted successfully'}


@router.post('/clients/{user_id}/reset-password')
async def reset_client_password(user_id: str, admin=Depends(get_admin_user)):
    """Generate a new temporary password for a client user."""
    from open_webui.models.users import Users
    from open_webui.models.auths import Auths

    user = await Users.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    info = user.info or {}
    if info.get('user_type') != 'client':
        raise HTTPException(status_code=400, detail='User is not a client')

    temp_password = secrets.token_urlsafe(12)
    from open_webui.utils.auth import get_password_hash
    hashed = await get_password_hash(temp_password)

    await Auths.update_user_password_by_id(user.id, hashed)
    log.info(f'Admin {admin.id} reset password for client user {user_id}')

    return {
        'user_id': user_id,
        'temp_password': temp_password,
        'message': f'Password reset for {user.email}. Share the temporary password securely.',
    }
