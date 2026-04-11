import logging
from typing import Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from open_webui.internal.db import get_session
from open_webui.models.groups import Groups
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.usage_limits import (
    check_usage_limit,
    get_period_start,
    get_user_usage_limit,
)

log = logging.getLogger(__name__)

router = APIRouter()


############################
# Pydantic Forms
############################


class UsageLimitForm(BaseModel):
    token_limit: int  # max total tokens per period
    limit_period: str = 'daily'  # "daily" or "monthly"
    soft_limit: Optional[int] = None  # warn at this threshold
    priority: int = 100  # lower = higher priority


############################
# Get current user's usage status
############################


@router.get('/status')
async def get_usage_status(user=Depends(get_verified_user)):
    """Get the current user's usage status against their limits."""
    return check_usage_limit(user.id)


############################
# Get a specific user's usage status (admin only)
############################


@router.get('/users/{user_id}/status')
async def get_user_usage_status(user_id: str, user=Depends(get_admin_user)):
    """Get a specific user's usage status (admin only)."""
    return check_usage_limit(user_id)


############################
# Get usage limits for a group (admin only)
############################


@router.get('/groups/{group_id}')
async def get_group_usage_limits(
    group_id: str,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get the usage limits configured for a group."""
    group = Groups.get_group_by_id(group_id, db=db)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Group not found',
        )

    permissions = group.permissions or {}
    return permissions.get('usage_limits') or {}


############################
# Set usage limits for a group (admin only)
############################


@router.post('/groups/{group_id}')
async def set_group_usage_limits(
    group_id: str,
    form_data: UsageLimitForm,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Set usage limits for a group."""
    group = Groups.get_group_by_id(group_id, db=db)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Group not found',
        )

    if form_data.limit_period not in ('daily', 'monthly'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='limit_period must be "daily" or "monthly"',
        )

    if form_data.soft_limit and form_data.soft_limit >= form_data.token_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='soft_limit must be less than token_limit',
        )

    permissions = group.permissions or {}
    permissions['usage_limits'] = form_data.model_dump()

    if not Groups.update_group_permissions_by_id(group_id, permissions, db=db):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to update group permissions',
        )

    return permissions['usage_limits']


############################
# Delete usage limits for a group (admin only)
############################


@router.delete('/groups/{group_id}')
async def delete_group_usage_limits(
    group_id: str,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Remove usage limits from a group."""
    group = Groups.get_group_by_id(group_id, db=db)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Group not found',
        )

    permissions = group.permissions or {}
    permissions.pop('usage_limits', None)

    if not Groups.update_group_permissions_by_id(group_id, permissions, db=db):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Failed to update group permissions',
        )

    return {'status': True}
