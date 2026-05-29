"""
Company custom: Team Workspaces V1
New router — does not modify any existing router.
Mounted at /api/v1/workspaces in main.py.
"""

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.constants import ERROR_MESSAGES
from open_webui.internal.db import get_async_session
from open_webui.models.chats import ChatForm, ChatResponse, ChatTitleIdResponse, Chats
from open_webui.models.users import Users
from open_webui.models.workspaces import (
    WORKSPACE_MANAGE_ROLES,
    WORKSPACE_WRITE_ROLES,
    WorkspaceForm,
    WorkspaceMemberForm,
    WorkspaceMemberModel,
    WorkspaceMemberResponse,
    WorkspaceMemberUpdateForm,
    WorkspaceMembers,
    WorkspaceModel,
    WorkspaceResponse,
    WorkspaceUpdateForm,
    Workspaces,
    WORKSPACE_ROLE_MANAGER,
)
from open_webui.utils.auth import get_verified_user

log = logging.getLogger(__name__)

router = APIRouter()


####################
# Permission helper
####################


async def assert_workspace_access(
    workspace_id: str,
    user,
    required_action: str,  # "read" | "write" | "manage"
    db: AsyncSession,
) -> WorkspaceMemberModel:
    """
    Raise 403/404 if the user does not have the required access level.
    Returns the membership row on success.

    NOTE: Admin platform role does NOT bypass workspace membership in V1.
          CEOs/admins must be explicitly added as members. If the deploying
          team later decides admins should see all workspaces, add
          ``user.role == 'admin'`` bypass here and document it.
    """
    workspace = await Workspaces.get_by_id(workspace_id, db=db)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    member = await WorkspaceMembers.get(workspace_id, user.id, db=db)
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    if required_action == "write" and member.role not in WORKSPACE_WRITE_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    if required_action == "manage" and member.role not in WORKSPACE_MANAGE_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    return member


####################
# Response builders
####################


async def _workspace_response(ws: WorkspaceModel, user_id: str, db: AsyncSession) -> WorkspaceResponse:
    """Build WorkspaceResponse enriched with the requesting user's role."""
    member = await WorkspaceMembers.get(ws.id, user_id, db=db)
    return WorkspaceResponse(**ws.model_dump(), my_role=member.role if member else None)


async def _member_response(m: WorkspaceMemberModel, db: AsyncSession) -> WorkspaceMemberResponse:
    """Build WorkspaceMemberResponse enriched with the user's display_name and email."""
    display_name: Optional[str] = None
    email: Optional[str] = None
    user_obj = await Users.get_user_by_id(m.user_id, db=db)
    if user_obj:
        display_name = user_obj.name
        email = user_obj.email
    return WorkspaceMemberResponse(**m.model_dump(), display_name=display_name, email=email)


####################
# Workspace CRUD
####################


@router.post('/', response_model=WorkspaceResponse)
async def create_workspace(
    form_data: WorkspaceForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new workspace; creator is automatically added as manager."""
    try:
        workspace = await Workspaces.create(user.id, form_data, db=db)
        # Auto-add creator as manager
        await WorkspaceMembers.add(workspace.id, user.id, WORKSPACE_ROLE_MANAGER, db=db)
        return await _workspace_response(workspace, user.id, db)
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.get('/', response_model=list[WorkspaceResponse])
async def list_workspaces(
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List workspaces the current user is a member of, each with my_role populated."""
    try:
        workspace_list = await Workspaces.get_for_user(user.id, db=db)
        return [await _workspace_response(ws, user.id, db) for ws in workspace_list]
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.get('/{workspace_id}', response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get workspace details; only accessible to members."""
    await assert_workspace_access(workspace_id, user, "read", db)
    workspace = await Workspaces.get_by_id(workspace_id, db=db)
    return await _workspace_response(workspace, user.id, db)


@router.patch('/{workspace_id}', response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    form_data: WorkspaceUpdateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Update workspace name/description/meta; manager only."""
    await assert_workspace_access(workspace_id, user, "manage", db)
    workspace = await Workspaces.update(workspace_id, form_data, db=db)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    return await _workspace_response(workspace, user.id, db)


@router.delete('/{workspace_id}')
async def delete_workspace(
    workspace_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Soft-delete workspace; manager only."""
    await assert_workspace_access(workspace_id, user, "manage", db)
    ok = await Workspaces.soft_delete(workspace_id, db=db)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    return {'detail': 'Workspace deleted'}


####################
# Members
####################


@router.get('/{workspace_id}/members', response_model=list[WorkspaceMemberResponse])
async def list_workspace_members(
    workspace_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List all members with display_name and email; accessible to all workspace members."""
    await assert_workspace_access(workspace_id, user, "read", db)
    members = await WorkspaceMembers.list_members(workspace_id, db=db)
    return [await _member_response(m, db) for m in members]


@router.post('/{workspace_id}/members', response_model=WorkspaceMemberResponse)
async def add_workspace_member(
    workspace_id: str,
    form_data: WorkspaceMemberForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Add a member by user_id; manager only."""
    await assert_workspace_access(workspace_id, user, "manage", db)

    if form_data.role not in ("manager", "member", "viewer"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be one of: manager, member, viewer",
        )

    # Verify the target user exists
    target_user = await Users.get_user_by_id(form_data.user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent duplicate membership
    existing = await WorkspaceMembers.get(workspace_id, form_data.user_id, db=db)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User is already a member"
        )

    try:
        member = await WorkspaceMembers.add(workspace_id, form_data.user_id, form_data.role, db=db)
        return await _member_response(member, db)
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.patch('/{workspace_id}/members/{target_user_id}', response_model=WorkspaceMemberResponse)
async def update_workspace_member(
    workspace_id: str,
    target_user_id: str,
    form_data: WorkspaceMemberUpdateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Update a member's role; manager only."""
    await assert_workspace_access(workspace_id, user, "manage", db)

    if form_data.role not in ("manager", "member", "viewer"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be one of: manager, member, viewer",
        )

    updated = await WorkspaceMembers.update_role(workspace_id, target_user_id, form_data.role, db=db)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return await _member_response(updated, db)


@router.delete('/{workspace_id}/members/{target_user_id}')
async def remove_workspace_member(
    workspace_id: str,
    target_user_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Remove a member; manager only."""
    await assert_workspace_access(workspace_id, user, "manage", db)

    ok = await WorkspaceMembers.remove(workspace_id, target_user_id, db=db)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return {'detail': 'Member removed'}


####################
# Workspace chats
####################


@router.get('/{workspace_id}/chats', response_model=list[ChatTitleIdResponse])
async def list_workspace_chats(
    workspace_id: str,
    page: Optional[int] = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List chats inside a workspace; member/viewer/manager access."""
    await assert_workspace_access(workspace_id, user, "read", db)

    skip = None
    limit = None
    if page is not None:
        limit = 60
        skip = (page - 1) * limit

    try:
        return await Chats.get_chat_title_id_list_by_workspace_id(
            workspace_id, skip=skip, limit=limit, db=db
        )
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.post('/{workspace_id}/chats', response_model=ChatResponse)
async def create_workspace_chat(
    workspace_id: str,
    form_data: ChatForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new chat inside the workspace; member or manager access."""
    await assert_workspace_access(workspace_id, user, "write", db)

    try:
        form_data.workspace_id = workspace_id
        # Ensure no folder_id bleeds into workspace chats in V1
        form_data.folder_id = None
        chat = await Chats.insert_new_chat(str(uuid4()), user.id, form_data, db=db)
        return ChatResponse(**chat.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())
