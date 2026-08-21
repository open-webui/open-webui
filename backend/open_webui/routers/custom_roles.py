"""Admin-only API for managing custom roles.

All endpoints in this router require exact ``admin`` role (via ``get_admin_user``).
Custom roles are stored as ``custom:<uuid>`` references in ``User.role``.

Endpoints:
- POST /create       — create a new custom role
- GET /              — list all custom roles (paginated)
- GET /{role_id}     — get a single custom role by ID
- POST /{role_id}/update — update display_name, active, or permissions
- POST /{role_id}/deactivate — soft-deactivate (set active=False)
- POST /assign       — assign a custom role to a user
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_session
from open_webui.models.custom_roles import (
    CustomRoleAssignForm,
    CustomRoleCreateForm,
    CustomRoleListResponse,
    CustomRoleResponse,
    CustomRoles,
    CustomRoleUpdateForm,
    make_custom_role_ref,
)
from open_webui.models.users import Users
from open_webui.utils.auth import get_admin_user
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _role_response(role) -> CustomRoleResponse:
    """Build an API response from a CustomRoleModel."""
    return CustomRoleResponse(
        id=role.id,
        name=role.name,
        display_name=role.display_name,
        active=role.active,
        permissions=role.permissions,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@router.post('/create', response_model=CustomRoleResponse)
async def create_custom_role(
    request: Request,
    form_data: CustomRoleCreateForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new custom role.

    The role name must be unique, not reserved, and meet format constraints.
    """
    try:
        role = await CustomRoles.create_role(form_data, db=db)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    await publish_event(
        request,
        EVENTS.CUSTOM_ROLE_CREATED,
        actor=user,
        subject_id=role.id,
        data={'name': role.name, 'display_name': role.display_name},
    )

    return _role_response(role)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@router.get('/', response_model=CustomRoleListResponse)
async def list_custom_roles(
    include_inactive: bool = False,
    page: int = 1,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List custom roles with pagination."""
    limit = 100
    skip = max(0, (max(1, page) - 1) * limit)

    result = await CustomRoles.list_roles(
        include_inactive=include_inactive,
        skip=skip,
        limit=limit,
        db=db,
    )

    return CustomRoleListResponse(
        items=[_role_response(r) for r in result['items']],
        total=result['total'],
    )


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


@router.get('/{role_id}', response_model=CustomRoleResponse)
async def get_custom_role(
    role_id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get a single custom role by ID."""
    role = await CustomRoles.get_role_by_id(role_id, db=db)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.CUSTOM_ROLE_NOT_FOUND,
        )
    return _role_response(role)


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


@router.post('/{role_id}/update', response_model=CustomRoleResponse)
async def update_custom_role(
    request: Request,
    role_id: str,
    form_data: CustomRoleUpdateForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Update display_name, active flag, or permissions of a custom role.

    The role name and ID are immutable.
    """
    role = await CustomRoles.update_role(role_id, form_data, db=db)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.CUSTOM_ROLE_NOT_FOUND,
        )

    await publish_event(
        request,
        EVENTS.CUSTOM_ROLE_UPDATED,
        actor=user,
        subject_id=role.id,
        data={'name': role.name, 'display_name': role.display_name, 'active': role.active},
    )

    return _role_response(role)


# ---------------------------------------------------------------------------
# Deactivate (soft-delete)
# ---------------------------------------------------------------------------


@router.post('/{role_id}/deactivate', response_model=CustomRoleResponse)
async def deactivate_custom_role(
    request: Request,
    role_id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Soft-deactivate a custom role (set active=False).

    Users currently assigned this role will fail-closed on the next request
    because the role is no longer active.
    """
    role = await CustomRoles.deactivate_role(role_id, db=db)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.CUSTOM_ROLE_NOT_FOUND,
        )

    await publish_event(
        request,
        EVENTS.CUSTOM_ROLE_DEACTIVATED,
        actor=user,
        subject_id=role.id,
        data={'name': role.name},
    )

    return _role_response(role)


# ---------------------------------------------------------------------------
# Assign / Unassign
# ---------------------------------------------------------------------------


@router.post('/assign')
async def assign_custom_role(
    request: Request,
    form_data: CustomRoleAssignForm,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Assign a custom role to a user.

    Validates:
    - The target role exists, is active, and is not a reserved role.
    - The target user exists.
    - The caller cannot assign roles to themselves via this endpoint.
    """
    # Validate that the role_id is a real, active custom role
    role = await CustomRoles.get_active_role_by_id(form_data.role_id, db=db)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.CUSTOM_ROLE_INACTIVE,
        )

    # Look up target user
    target_user = await Users.get_user_by_id(form_data.user_id, db=db)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )

    # Cannot demote the first admin user
    first_user = await Users.get_first_user(db=db)
    if first_user and target_user.id == first_user.id and target_user.role == 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACTION_PROHIBITED,
        )

    # Assign the role
    role_ref = make_custom_role_ref(role.id)
    updated = await Users.update_user_role_by_id(target_user.id, role_ref, db=db)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.CUSTOM_ROLE_ASSIGN_FAILED,
        )

    await publish_event(
        request,
        EVENTS.CUSTOM_ROLE_ASSIGNED,
        actor=user,
        subject_id=target_user.id,
        data={
            'role_id': role.id,
            'role_name': role.name,
            'old_role': target_user.role,
            'new_role': role_ref,
        },
    )

    await publish_event(
        request,
        EVENTS.USER_ROLE_UPDATED,
        actor=user,
        subject_id=target_user.id,
        data={'role': role_ref},
    )

    return {'status': True, 'role': role_ref}


@router.post('/{role_id}/unassign')
async def unassign_custom_role(
    request: Request,
    role_id: str,
    user_id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Remove a custom role assignment, reverting the user to ``pending``.

    Validates:
    - The target user currently has ``custom:<role_id>`` as their role.
    """
    target_user = await Users.get_user_by_id(user_id, db=db)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )

    expected_ref = make_custom_role_ref(role_id)
    if target_user.role != expected_ref:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.CUSTOM_ROLE_UNASSIGN_FAILED,
        )

    # Cannot demote the first admin
    first_user = await Users.get_first_user(db=db)
    if first_user and target_user.id == first_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACTION_PROHIBITED,
        )

    # Revert to pending (legacy default)
    updated = await Users.update_user_role_by_id(target_user.id, 'pending', db=db)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.CUSTOM_ROLE_UNASSIGN_FAILED,
        )

    await publish_event(
        request,
        EVENTS.USER_ROLE_UPDATED,
        actor=user,
        subject_id=user_id,
        data={'role': 'pending'},
    )

    return {'status': True, 'role': 'pending'}
