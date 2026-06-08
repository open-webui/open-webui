"""
Company custom: Team Workspaces V1
New router — does not modify any existing router.
Mounted at /api/v1/workspaces in main.py.
"""

import logging
from typing import Optional
from uuid import uuid4

import time
import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.constants import ERROR_MESSAGES
from open_webui.internal.db import get_async_session
from open_webui.models.chats import ChatForm, ChatResponse, ChatTitleIdResponse, Chats
from open_webui.models.folders import (
    FolderForm,
    FolderModel,
    FolderNameIdResponse,
    FolderUpdateForm,
    Folders,
)
from open_webui.models.users import Users
from open_webui.models.workspaces import (
    WORKSPACE_MANAGE_ROLES,
    WORKSPACE_WRITE_ROLES,
    Workspace,
    WorkspaceMember,
    WorkspaceForm,
    WorkspaceDefaultModelForm,
    WorkspaceDefaultModelResponse,
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
from open_webui.utils.governance import (
    assert_workspace_create_allowed,
    can_access_all_workspaces,
)

log = logging.getLogger(__name__)

router = APIRouter()


class FolderParentIdForm(BaseModel):
    parent_id: Optional[str] = None


class FolderIsExpandedForm(BaseModel):
    is_expanded: bool


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

    NOTE: Workspace chat read/write requires explicit membership unless the
          user has CEO all-workspace access. Platform admins bypass only
          workspace management actions so they can create/update/delete
          workspaces and manage members operationally.
    """
    workspace = await Workspaces.get_by_id(workspace_id, db=db)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    member = await WorkspaceMembers.get(workspace_id, user.id, db=db)
    all_workspace_access = await can_access_all_workspaces(user, db=db)

    if required_action == "manage" and (getattr(user, "role", None) == "admin" or all_workspace_access):
        return member or WorkspaceMemberModel(
            id="governance",
            workspace_id=workspace_id,
            user_id=user.id,
            role=WORKSPACE_ROLE_MANAGER,
            created_at=0,
            updated_at=0,
        )

    if member is None:
        if all_workspace_access and required_action in {"read", "write"}:
            return WorkspaceMemberModel(
                id="governance",
                workspace_id=workspace_id,
                user_id=user.id,
                role=WORKSPACE_ROLE_MANAGER,
                created_at=0,
                updated_at=0,
            )
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


async def assert_workspace_folder_parent_valid(
    workspace_id: str,
    folder_id: Optional[str],
    parent_id: Optional[str],
    db: AsyncSession,
) -> None:
    if parent_id is None:
        return

    if folder_id is not None and folder_id == parent_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Folder cannot be its own parent")

    parent = await Folders.get_folder_by_id_and_workspace_id(parent_id, workspace_id, db=db)
    if parent is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent folder must be in the same workspace")

    seen = {folder_id} if folder_id else set()
    current = parent
    while current.parent_id:
        if current.parent_id in seen:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Circular folder nesting is not allowed")
        seen.add(current.parent_id)
        current = await Folders.get_folder_by_id_and_workspace_id(current.parent_id, workspace_id, db=db)
        if current is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent folder chain is invalid")


####################
# Workspace CRUD
####################


@router.post('/', response_model=WorkspaceResponse)
async def create_workspace(
    form_data: WorkspaceForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new workspace; admin-only; creator is automatically added as manager (atomic)."""
    await assert_workspace_create_allowed(user, db=db)

    try:
        now = int(time.time())
        ws_id = str(uuid_lib.uuid4())
        ws = Workspace(
            id=ws_id,
            user_id=user.id,
            name=form_data.name,
            description=form_data.description,
            meta=form_data.meta,
            created_at=now,
            updated_at=now,
        )
        member = WorkspaceMember(
            id=str(uuid_lib.uuid4()),
            workspace_id=ws_id,
            user_id=user.id,
            role=WORKSPACE_ROLE_MANAGER,
            created_at=now,
            updated_at=now,
        )
        db.add(ws)
        db.add(member)
        await db.commit()
        await db.refresh(ws)
        workspace = WorkspaceModel.model_validate(ws)
        return await _workspace_response(workspace, user.id, db)
    except Exception as e:
        await db.rollback()
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.get('/', response_model=list[WorkspaceResponse])
async def list_workspaces(
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List workspaces the current user is a member of, each with my_role populated."""
    try:
        if getattr(user, "role", None) == "admin" or await can_access_all_workspaces(user, db=db):
            workspace_list = await Workspaces.get_all(db=db)
        else:
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
    """List all members with display_name and email; accessible to members and admins."""
    if getattr(user, "role", None) == "admin" or await can_access_all_workspaces(user, db=db):
        workspace = await Workspaces.get_by_id(workspace_id, db=db)
        if workspace is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    else:
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

    # P0: prevent demoting the last manager
    if form_data.role != WORKSPACE_ROLE_MANAGER:
        current = await WorkspaceMembers.get(workspace_id, target_user_id, db=db)
        if current and current.role == WORKSPACE_ROLE_MANAGER:
            manager_count = await WorkspaceMembers.count_managers(workspace_id, db=db)
            if manager_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot demote the last manager. Promote another member first.",
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

    # P0: prevent removing the last manager
    current = await WorkspaceMembers.get(workspace_id, target_user_id, db=db)
    if current and current.role == WORKSPACE_ROLE_MANAGER:
        manager_count = await WorkspaceMembers.count_managers(workspace_id, db=db)
        if manager_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot remove the last manager. Promote another member first.",
            )

    ok = await WorkspaceMembers.remove(workspace_id, target_user_id, db=db)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return {'detail': 'Member removed'}


####################
# Workspace defaults
####################


@router.get('/{workspace_id}/default-model', response_model=WorkspaceDefaultModelResponse)
async def get_workspace_default_model(
    workspace_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Read workspace default model; accessible to workspace readers."""
    await assert_workspace_access(workspace_id, user, "read", db)
    workspace = await Workspaces.get_by_id(workspace_id, db=db)
    meta = workspace.meta or {}
    return WorkspaceDefaultModelResponse(model_id=meta.get("default_model_id"))


@router.put('/{workspace_id}/default-model', response_model=WorkspaceDefaultModelResponse)
async def set_workspace_default_model(
    workspace_id: str,
    form_data: WorkspaceDefaultModelForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Set workspace default model; manager only."""
    await assert_workspace_access(workspace_id, user, "manage", db)
    model_id = form_data.model_id.strip() if form_data.model_id else None
    workspace = await Workspaces.update_default_model_id(workspace_id, model_id, db=db)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    return WorkspaceDefaultModelResponse(model_id=(workspace.meta or {}).get("default_model_id"))


####################
# Workspace folders
####################


@router.get('/{workspace_id}/folders', response_model=list[FolderNameIdResponse])
async def list_workspace_folders(
    workspace_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await assert_workspace_access(workspace_id, user, "read", db)
    folders = await Folders.get_folders_by_workspace_id(workspace_id, db=db)

    folder_list = []
    for folder in folders:
        if folder.parent_id and not await Folders.get_folder_by_id_and_workspace_id(folder.parent_id, workspace_id, db=db):
            folder = await Folders.update_folder_parent_id_by_id_and_workspace_id(folder.id, workspace_id, None, db=db)
        folder_list.append(FolderNameIdResponse(**folder.model_dump()))

    return folder_list


@router.post('/{workspace_id}/folders', response_model=FolderModel)
async def create_workspace_folder(
    workspace_id: str,
    form_data: FolderForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await assert_workspace_access(workspace_id, user, "manage", db)
    await assert_workspace_folder_parent_valid(workspace_id, None, form_data.parent_id, db)

    folder = await Folders.get_folder_by_parent_id_and_workspace_id_and_name(
        form_data.parent_id, workspace_id, form_data.name, db=db
    )
    if folder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Folder already exists'),
        )

    form_data.workspace_id = workspace_id
    folder = await Folders.insert_new_folder(user.id, form_data, form_data.parent_id, db=db)
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Error creating folder'),
        )
    return folder


@router.get('/{workspace_id}/folders/{folder_id}', response_model=FolderModel)
async def get_workspace_folder(
    workspace_id: str,
    folder_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await assert_workspace_access(workspace_id, user, "read", db)
    folder = await Folders.get_folder_by_id_and_workspace_id(folder_id, workspace_id, db=db)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    return folder


@router.post('/{workspace_id}/folders/{folder_id}/update', response_model=FolderModel)
async def update_workspace_folder(
    workspace_id: str,
    folder_id: str,
    form_data: FolderUpdateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await assert_workspace_access(workspace_id, user, "manage", db)
    folder = await Folders.get_folder_by_id_and_workspace_id(folder_id, workspace_id, db=db)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if form_data.name is not None:
        existing_folder = await Folders.get_folder_by_parent_id_and_workspace_id_and_name(
            folder.parent_id, workspace_id, form_data.name, db=db
        )
        if existing_folder and existing_folder.id != folder_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Folder already exists'),
            )

    updated = await Folders.update_folder_by_id_and_workspace_id(folder_id, workspace_id, form_data, db=db)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Error updating folder'),
        )
    return updated


@router.post('/{workspace_id}/folders/{folder_id}/update/parent', response_model=FolderModel)
async def update_workspace_folder_parent(
    workspace_id: str,
    folder_id: str,
    form_data: FolderParentIdForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await assert_workspace_access(workspace_id, user, "manage", db)
    folder = await Folders.get_folder_by_id_and_workspace_id(folder_id, workspace_id, db=db)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    await assert_workspace_folder_parent_valid(workspace_id, folder_id, form_data.parent_id, db)
    existing_folder = await Folders.get_folder_by_parent_id_and_workspace_id_and_name(
        form_data.parent_id, workspace_id, folder.name, db=db
    )
    if existing_folder and existing_folder.id != folder_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Folder already exists'),
        )

    updated = await Folders.update_folder_parent_id_by_id_and_workspace_id(
        folder_id, workspace_id, form_data.parent_id, db=db
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Error updating folder'),
        )
    return updated


@router.post('/{workspace_id}/folders/{folder_id}/update/expanded', response_model=FolderModel)
async def update_workspace_folder_expanded(
    workspace_id: str,
    folder_id: str,
    form_data: FolderIsExpandedForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await assert_workspace_access(workspace_id, user, "manage", db)
    folder = await Folders.update_folder_is_expanded_by_id_and_workspace_id(
        folder_id, workspace_id, form_data.is_expanded, db=db
    )
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    return folder


@router.get('/{workspace_id}/folders/{folder_id}/chats', response_model=list[ChatTitleIdResponse])
async def list_workspace_folder_chats(
    workspace_id: str,
    folder_id: str,
    page: Optional[int] = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await assert_workspace_access(workspace_id, user, "read", db)
    folder = await Folders.get_folder_by_id_and_workspace_id(folder_id, workspace_id, db=db)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    skip = None
    limit = None
    if page is not None:
        limit = 60
        skip = (page - 1) * limit
    return await Chats.get_chat_title_id_list_by_workspace_id_and_folder_id(
        workspace_id, folder_id, skip=skip, limit=limit, db=db
    )


@router.delete('/{workspace_id}/folders/{folder_id}')
async def delete_workspace_folder(
    workspace_id: str,
    folder_id: str,
    delete_contents: Optional[bool] = True,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await assert_workspace_access(workspace_id, user, "manage", db)
    folder = await Folders.get_folder_by_id_and_workspace_id(folder_id, workspace_id, db=db)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    folder_ids = await Folders.delete_folder_by_id_and_workspace_id(folder_id, workspace_id, db=db)
    for deleted_folder_id in folder_ids:
        if delete_contents:
            await Chats.delete_chats_by_workspace_id_and_folder_id(workspace_id, deleted_folder_id, db=db)
        else:
            await Chats.move_chats_by_workspace_id_and_folder_id(workspace_id, deleted_folder_id, None, db=db)
    return True


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
    if form_data.folder_id:
        folder = await Folders.get_folder_by_id_and_workspace_id(form_data.folder_id, workspace_id, db=db)
        if folder is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Folder must be in the same workspace")

    try:
        form_data.workspace_id = workspace_id
        chat = await Chats.insert_new_chat(str(uuid4()), user.id, form_data, db=db)
        return ChatResponse(**chat.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())
