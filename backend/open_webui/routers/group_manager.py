"""Scoped group-manager router.

Additive endpoints under ``/api/v1/group-manager/groups`` and
``/api/v1/group-manager/groups/{group_id}/...`` that allow group managers
(custom-role holders with ``groups.manage_members``, ``groups.manage_assets``,
or ``groups.manage_skills``) to discover and operate on a single group.

Security contract:
- Every mutation uses ``group_manager_tx(db)`` then
  ``require_group_manager(user.id, group_id, capability, db)``.
- Admin / legacy roles are **denied** on these scoped endpoints.
- ``manage_members``: list / add / remove membership within the target group.
- ``manage_assets``: create / update / delete ``knowledge`` and ``prompt``
  rows with an authoritative ``group_owned_asset`` row.
- Scoped creation atomically creates resource + ownership row + owning-group
  read AccessGrant using flush-only primitives.
- Scoped update / delete lock on exact ``(group_id, type, id)`` ownership.
- ACL delta accepts only ``write: bool`` for the owning group.
- Events are published only after successful commit and omit content.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import (
    PRINCIPAL_TYPE_GROUP,
    AccessGrant,
)
from open_webui.models.groups import (
    SUPPORTED_OWNED_ASSET_TYPES,
    Group,
    GroupMember,
    GroupOwnedAsset,
    GroupOwnedAssets,
)
from open_webui.models.knowledge import Knowledge
from open_webui.models.prompts import Prompt
from open_webui.models.skills import Skill, SkillMeta
from open_webui.models.users import User
from open_webui.utils.access_control.group_manager import (
    GroupManagerError,
    group_manager_tx,
    require_group_manager,
)
from open_webui.utils.auth import get_verified_user
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()


# =====================================================================
# Forms / response schemas
# =====================================================================


class GroupManagerMemberIdsForm(BaseModel):
    user_ids: list[str]


class GroupManagerKnowledgeCreateForm(BaseModel):
    name: str
    description: str = ''


class GroupManagerPromptCreateForm(BaseModel):
    command: str
    name: str
    content: str
    data: dict | None = None
    meta: dict | None = None
    tags: list[str | None] | None = None


class GroupManagerKnowledgeUpdateForm(BaseModel):
    name: str | None = None
    description: str | None = None


class GroupManagerPromptUpdateForm(BaseModel):
    name: str | None = None
    content: str | None = None
    data: dict | None = None
    meta: dict | None = None
    tags: list[str | None] | None = None


class GroupManagerACLDeltaForm(BaseModel):
    write: bool


class GroupManagerAssetInfo(BaseModel):
    """Slim metadata for an owned asset — never includes content."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    resource_type: str
    resource_id: str
    group_id: str
    created_by: str
    created_at: int
    updated_at: int


class GroupManagerKnowledgeResponse(BaseModel):
    id: str
    name: str
    description: str
    created_at: int
    updated_at: int
    write_access: bool = False


class GroupManagerPromptResponse(BaseModel):
    id: str
    command: str
    name: str
    created_at: int
    updated_at: int
    write_access: bool = False


class GroupManagerACLResponse(BaseModel):
    resource_type: str
    resource_id: str
    write: bool


class GroupManagerMemberInfo(BaseModel):
    id: str
    user_id: str
    created_at: int | None = None


class GroupManagerGroupInfo(BaseModel):
    """Minimal group discovery contract for the manager workspace."""

    id: str
    name: str
    capabilities: list[str]


# =====================================================================
# Skill forms / response schemas (Phase 3: skills-only slice)
# =====================================================================


class GroupManagerSkillCreateForm(BaseModel):
    """Payload allowlist for scoped skill creation.

    Server controls id (group-namespaced slug), user_id, and access_grants.
    """
    model_config = ConfigDict(extra='forbid')

    slug: str
    name: str
    description: str = ''
    content: str = ''
    tags: list[str] = Field(default_factory=list)
    active: bool = True


class GroupManagerSkillUpdateForm(BaseModel):
    """Payload allowlist for scoped skill update.

    All fields optional; omitted fields preserve existing values.
    """
    model_config = ConfigDict(extra='forbid')

    name: str | None = None
    description: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    active: bool | None = None


class GroupManagerSkillResponse(BaseModel):
    """Response for scoped skill operations — never includes access_grants."""
    id: str
    slug: str
    name: str
    description: str
    content: str
    is_active: bool
    meta: SkillMeta
    created_at: int
    updated_at: int


# =====================================================================
# Flush-only primitives (non-committing)
# =====================================================================


async def _grant_access_flush(
    resource_type: str,
    resource_id: str,
    principal_type: str,
    principal_id: str,
    permission: str,
    db: AsyncSession,
) -> None:
    """Insert an AccessGrant row and flush — no commit.

    Idempotent: skips if the grant already exists.
    """
    result = await db.execute(
        select(AccessGrant).filter_by(
            resource_type=resource_type,
            resource_id=resource_id,
            principal_type=principal_type,
            principal_id=principal_id,
            permission=permission,
        )
    )
    if result.scalars().first() is not None:
        return  # idempotent

    grant = AccessGrant(
        id=str(uuid.uuid4()),
        resource_type=resource_type,
        resource_id=resource_id,
        principal_type=principal_type,
        principal_id=principal_id,
        permission=permission,
        created_at=int(time.time()),
    )
    db.add(grant)
    await db.flush()


async def _revoke_access_flush(
    resource_type: str,
    resource_id: str,
    principal_type: str,
    principal_id: str,
    permission: str,
    db: AsyncSession,
) -> None:
    """Delete an AccessGrant row and flush — no commit."""
    await db.execute(
        delete(AccessGrant).filter_by(
            resource_type=resource_type,
            resource_id=resource_id,
            principal_type=principal_type,
            principal_id=principal_id,
            permission=permission,
        )
    )
    await db.flush()


async def _revoke_all_access_flush(
    resource_type: str,
    resource_id: str,
    db: AsyncSession,
) -> None:
    """Delete all AccessGrant rows for a resource and flush — no commit."""
    await db.execute(
        delete(AccessGrant).filter_by(
            resource_type=resource_type,
            resource_id=resource_id,
        )
    )
    await db.flush()


async def _verify_ownership(
    group_id: str,
    resource_type: str,
    resource_id: str,
    db: AsyncSession,
) -> None:
    """Verify that ``(group_id, resource_type, resource_id)`` exists in
    ``group_owned_asset`` and lock the row.

    Raises ``HTTPException(404)`` if not found.
    """
    result = await db.execute(
        select(GroupOwnedAsset)
        .where(
            GroupOwnedAsset.group_id == group_id,
            GroupOwnedAsset.resource_type == resource_type,
            GroupOwnedAsset.resource_id == resource_id,
        )
        .with_for_update()
    )
    if result.scalars().first() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


# =====================================================================
# Membership management (manage_members)
# =====================================================================

GROUP_MANAGER_CAPABILITIES: tuple[str, ...] = (
    'groups.manage_members',
    'groups.manage_assets',
    'groups.manage_skills',
)


@router.get(
    '/groups',
    response_model=list[GroupManagerGroupInfo],
)
async def list_manageable_groups(
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List groups for which the caller currently has a manager capability.

    Membership is used only to enumerate candidates.  Each capability is
    re-authorized through ``require_group_manager`` inside the same transaction
    so custom-role activity, capability, and current membership remain the
    source of truth.  Creator IDs and access grants are deliberately ignored.
    """
    response: list[GroupManagerGroupInfo] = []

    async with group_manager_tx(db):
        result = await db.execute(
            select(Group)
            .join(GroupMember, GroupMember.group_id == Group.id)
            .where(GroupMember.user_id == user.id)
            .order_by(Group.updated_at.desc(), Group.id.asc())
        )
        groups = result.scalars().all()

        for group in groups:
            capabilities: list[str] = []
            for capability in GROUP_MANAGER_CAPABILITIES:
                try:
                    await require_group_manager(user.id, group.id, capability, db)
                except GroupManagerError:
                    continue
                capabilities.append(capability)

            if capabilities:
                response.append(
                    GroupManagerGroupInfo(
                        id=group.id,
                        name=group.name,
                        capabilities=capabilities,
                    )
                )

    return response


@router.get(
    '/groups/{group_id}/members',
    response_model=list[GroupManagerMemberInfo],
)
async def list_group_members(
    group_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List members of the target group."""
    async with group_manager_tx(db):
        await require_group_manager(
            user.id, group_id, 'groups.manage_members', db,
        )
        result = await db.execute(
            select(GroupMember)
            .where(GroupMember.group_id == group_id)
            .order_by(GroupMember.created_at.asc())
        )
        members = result.scalars().all()

    return [
        GroupManagerMemberInfo(
            id=m.id,
            user_id=m.user_id,
            created_at=m.created_at,
        )
        for m in members
    ]


@router.post(
    '/groups/{group_id}/members/add',
    response_model=list[GroupManagerMemberInfo],
)
async def add_group_members(
    request: Request,
    group_id: str,
    form_data: GroupManagerMemberIdsForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Add users to the target group. Only valid user IDs are accepted."""
    pending_events: list[dict[str, Any]] = []

    async with group_manager_tx(db):
        await require_group_manager(
            user.id, group_id, 'groups.manage_members', db,
        )

        now = int(time.time())
        added_user_ids: list[str] = []

        for uid in form_data.user_ids:
            # Verify user exists
            user_result = await db.execute(
                select(User).where(User.id == uid),
            )
            if user_result.scalars().first() is None:
                continue

            # Check for existing membership
            existing = await db.execute(
                select(GroupMember).where(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == uid,
                )
            )
            if existing.scalars().first() is not None:
                continue  # already a member — skip

            member = GroupMember(
                id=str(uuid.uuid4()),
                group_id=group_id,
                user_id=uid,
                created_at=now,
                updated_at=now,
            )
            db.add(member)
            await db.flush()
            added_user_ids.append(uid)

        if added_user_ids:
            pending_events.append({
                'event': EVENTS.GROUP_MEMBER_ADDED,
                'subject_id': group_id,
                'data': {'user_ids': added_user_ids},
            })

        # Return final member list
        result = await db.execute(
            select(GroupMember)
            .where(GroupMember.group_id == group_id)
            .order_by(GroupMember.created_at.asc())
        )
        members = result.scalars().all()

    # Publish events after successful commit
    for evt in pending_events:
        await publish_event(
            request,
            evt['event'],
            actor=user,
            subject_id=evt['subject_id'],
            data=evt.get('data'),
        )

    return [
        GroupManagerMemberInfo(
            id=m.id,
            user_id=m.user_id,
            created_at=m.created_at,
        )
        for m in members
    ]


@router.post(
    '/groups/{group_id}/members/remove',
    response_model=list[GroupManagerMemberInfo],
)
async def remove_group_members(
    request: Request,
    group_id: str,
    form_data: GroupManagerMemberIdsForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Remove users from the target group."""
    pending_events: list[dict[str, Any]] = []

    async with group_manager_tx(db):
        await require_group_manager(
            user.id, group_id, 'groups.manage_members', db,
        )

        if form_data.user_ids:
            await db.execute(
                delete(GroupMember).where(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id.in_(form_data.user_ids),
                )
            )
            await db.flush()
            pending_events.append({
                'event': EVENTS.GROUP_MEMBER_REMOVED,
                'subject_id': group_id,
                'data': {'user_ids': form_data.user_ids},
            })

        # Return final member list
        result = await db.execute(
            select(GroupMember)
            .where(GroupMember.group_id == group_id)
            .order_by(GroupMember.created_at.asc())
        )
        members = result.scalars().all()

    for evt in pending_events:
        await publish_event(
            request,
            evt['event'],
            actor=user,
            subject_id=evt['subject_id'],
            data=evt.get('data'),
        )

    return [
        GroupManagerMemberInfo(
            id=m.id,
            user_id=m.user_id,
            created_at=m.created_at,
        )
        for m in members
    ]


# =====================================================================
# Asset management (manage_assets)
# =====================================================================


@router.get(
    '/groups/{group_id}/assets',
    response_model=list[GroupManagerAssetInfo],
)
async def list_group_assets(
    group_id: str,
    resource_type: str | None = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List assets owned by the target group."""
    async with group_manager_tx(db):
        await require_group_manager(
            user.id, group_id, 'groups.manage_assets', db,
        )

        stmt = select(GroupOwnedAsset).where(
            GroupOwnedAsset.group_id == group_id,
        )
        if resource_type:
            if resource_type not in SUPPORTED_OWNED_ASSET_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f'Unsupported resource_type: {resource_type}',
                )
            stmt = stmt.where(GroupOwnedAsset.resource_type == resource_type)
        stmt = stmt.order_by(GroupOwnedAsset.created_at.desc())

        result = await db.execute(stmt)
        assets = result.scalars().all()

    return [
        GroupManagerAssetInfo.model_validate(a)
        for a in assets
    ]


@router.post(
    '/groups/{group_id}/assets/knowledge/create',
    response_model=GroupManagerKnowledgeResponse,
)
async def create_group_knowledge(
    request: Request,
    group_id: str,
    form_data: GroupManagerKnowledgeCreateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a knowledge base owned by the group.

    Atomically creates:
    1. Knowledge row (flush only)
    2. GroupOwnedAsset ownership row (flush only)
    3. Owning-group read AccessGrant (flush only)
    """
    pending_events: list[dict[str, Any]] = []

    async with group_manager_tx(db):
        await require_group_manager(
            user.id, group_id, 'groups.manage_assets', db,
        )

        now = int(time.time())
        knowledge_id = str(uuid.uuid4())

        # 1. Create Knowledge row
        knowledge = Knowledge(
            id=knowledge_id,
            user_id=user.id,
            name=form_data.name,
            description=form_data.description,
            meta=None,
            created_at=now,
            updated_at=now,
        )
        db.add(knowledge)
        await db.flush()

        # 2. Create ownership row
        await GroupOwnedAssets.insert_asset(
            resource_type='knowledge',
            resource_id=knowledge_id,
            group_id=group_id,
            created_by=user.id,
            db=db,
        )

        # 3. Owning-group read grant (baseline)
        await _grant_access_flush(
            'knowledge', knowledge_id,
            PRINCIPAL_TYPE_GROUP, group_id, 'read',
            db,
        )

        pending_events.append({
            'event': EVENTS.KNOWLEDGE_CREATED,
            'subject_id': knowledge_id,
            'data': {'name': form_data.name},
        })

    for evt in pending_events:
        await publish_event(
            request,
            evt['event'],
            actor=user,
            subject_id=evt['subject_id'],
            data=evt.get('data'),
        )

    return GroupManagerKnowledgeResponse(
        id=knowledge_id,
        name=form_data.name,
        description=form_data.description,
        created_at=now,
        updated_at=now,
        write_access=True,
    )


@router.post(
    '/groups/{group_id}/assets/prompts/create',
    response_model=GroupManagerPromptResponse,
)
async def create_group_prompt(
    request: Request,
    group_id: str,
    form_data: GroupManagerPromptCreateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a prompt owned by the group.

    Atomically creates:
    1. Prompt row (flush only)
    2. GroupOwnedAsset ownership row (flush only)
    3. Owning-group read AccessGrant (flush only)

    Rejects supplied ``access_grants`` — manager cannot set public /
    user / other-group grants.
    """
    pending_events: list[dict[str, Any]] = []

    async with group_manager_tx(db):
        await require_group_manager(
            user.id, group_id, 'groups.manage_assets', db,
        )

        # Check command uniqueness
        existing = await db.execute(
            select(Prompt).where(Prompt.command == form_data.command),
        )
        if existing.scalars().first() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.COMMAND_TAKEN,
            )

        now = int(time.time())
        prompt_id = str(uuid.uuid4())

        # 1. Create Prompt row
        prompt = Prompt(
            id=prompt_id,
            user_id=user.id,
            command=form_data.command,
            name=form_data.name,
            content=form_data.content,
            data=form_data.data or {},
            meta=form_data.meta or {},
            tags=form_data.tags or [],
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(prompt)
        await db.flush()

        # 2. Create ownership row
        await GroupOwnedAssets.insert_asset(
            resource_type='prompt',
            resource_id=prompt_id,
            group_id=group_id,
            created_by=user.id,
            db=db,
        )

        # 3. Owning-group read grant (baseline)
        await _grant_access_flush(
            'prompt', prompt_id,
            PRINCIPAL_TYPE_GROUP, group_id, 'read',
            db,
        )

        pending_events.append({
            'event': EVENTS.PROMPT_CREATED,
            'subject_id': prompt_id,
            'data': {'name': form_data.name, 'command': form_data.command},
        })

    for evt in pending_events:
        await publish_event(
            request,
            evt['event'],
            actor=user,
            subject_id=evt['subject_id'],
            data=evt.get('data'),
        )

    return GroupManagerPromptResponse(
        id=prompt_id,
        command=form_data.command,
        name=form_data.name,
        created_at=now,
        updated_at=now,
        write_access=True,
    )


@router.post(
    '/groups/{group_id}/assets/knowledge/{resource_id}/update',
    response_model=GroupManagerKnowledgeResponse,
)
async def update_group_knowledge(
    request: Request,
    group_id: str,
    resource_id: str,
    form_data: GroupManagerKnowledgeUpdateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Update a group-owned knowledge base.

    First verifies ownership, then updates the knowledge row.
    """
    pending_events: list[dict[str, Any]] = []

    async with group_manager_tx(db):
        await require_group_manager(
            user.id, group_id, 'groups.manage_assets', db,
        )
        await _verify_ownership(group_id, 'knowledge', resource_id, db)

        # Lock and fetch the knowledge row
        result = await db.execute(
            select(Knowledge)
            .where(Knowledge.id == resource_id)
            .with_for_update()
        )
        knowledge = result.scalars().first()
        if knowledge is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )

        now = int(time.time())
        update_data: dict[str, Any] = {}
        if form_data.name is not None:
            update_data['name'] = form_data.name
        if form_data.description is not None:
            update_data['description'] = form_data.description
        if update_data:
            update_data['updated_at'] = now
            await db.execute(
                select(Knowledge)
                .where(Knowledge.id == resource_id)
                .with_for_update()
            )
            for key, value in update_data.items():
                setattr(knowledge, key, value)
            await db.flush()

        updated_name = knowledge.name

        pending_events.append({
            'event': EVENTS.KNOWLEDGE_UPDATED,
            'subject_id': resource_id,
            'data': {'name': updated_name},
        })

    for evt in pending_events:
        await publish_event(
            request,
            evt['event'],
            actor=user,
            subject_id=evt['subject_id'],
            data=evt.get('data'),
        )

    return GroupManagerKnowledgeResponse(
        id=knowledge.id,
        name=knowledge.name,
        description=knowledge.description,
        created_at=knowledge.created_at,
        updated_at=knowledge.updated_at,
        write_access=True,
    )


@router.delete(
    '/groups/{group_id}/assets/knowledge/{resource_id}/delete',
    response_model=bool,
)
async def delete_group_knowledge(
    request: Request,
    group_id: str,
    resource_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Delete a group-owned knowledge base.

    In one transaction: delete ownership row, all grants, then the
    knowledge row itself.
    """
    pending_events: list[dict[str, Any]] = []

    async with group_manager_tx(db):
        await require_group_manager(
            user.id, group_id, 'groups.manage_assets', db,
        )
        await _verify_ownership(group_id, 'knowledge', resource_id, db)

        # Fetch knowledge name for event
        result = await db.execute(
            select(Knowledge)
            .where(Knowledge.id == resource_id)
            .with_for_update()
        )
        knowledge = result.scalars().first()
        knowledge_name = knowledge.name if knowledge else None

        # 1. Delete ownership row
        await GroupOwnedAssets.delete_asset_by_resource(
            'knowledge', resource_id, db=db,
        )

        # 2. Delete all access grants
        await _revoke_all_access_flush('knowledge', resource_id, db)

        # 3. Delete the knowledge row
        await db.execute(
            delete(Knowledge).where(Knowledge.id == resource_id)
        )
        await db.flush()

        pending_events.append({
            'event': EVENTS.KNOWLEDGE_DELETED,
            'subject_id': resource_id,
            'data': {'name': knowledge_name},
        })

    for evt in pending_events:
        await publish_event(
            request,
            evt['event'],
            actor=user,
            subject_id=evt['subject_id'],
            data=evt.get('data'),
        )

    return True


@router.post(
    '/groups/{group_id}/assets/prompts/{resource_id}/update',
    response_model=GroupManagerPromptResponse,
)
async def update_group_prompt(
    request: Request,
    group_id: str,
    resource_id: str,
    form_data: GroupManagerPromptUpdateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Update a group-owned prompt.

    First verifies ownership, then updates the prompt row.
    Rejects supplied ``access_grants``.
    """
    pending_events: list[dict[str, Any]] = []

    async with group_manager_tx(db):
        await require_group_manager(
            user.id, group_id, 'groups.manage_assets', db,
        )
        await _verify_ownership(group_id, 'prompt', resource_id, db)

        # Lock and fetch the prompt row
        result = await db.execute(
            select(Prompt)
            .where(Prompt.id == resource_id)
            .with_for_update()
        )
        prompt = result.scalars().first()
        if prompt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )

        now = int(time.time())
        update_data: dict[str, Any] = {}
        if form_data.name is not None:
            update_data['name'] = form_data.name
        if form_data.content is not None:
            update_data['content'] = form_data.content
        if form_data.data is not None:
            update_data['data'] = form_data.data
        if form_data.meta is not None:
            update_data['meta'] = form_data.meta
        if form_data.tags is not None:
            update_data['tags'] = form_data.tags
        if update_data:
            update_data['updated_at'] = now
            for key, value in update_data.items():
                setattr(prompt, key, value)
            await db.flush()

        pending_events.append({
            'event': EVENTS.PROMPT_UPDATED,
            'subject_id': resource_id,
            'data': {'name': prompt.name, 'command': prompt.command},
        })

    for evt in pending_events:
        await publish_event(
            request,
            evt['event'],
            actor=user,
            subject_id=evt['subject_id'],
            data=evt.get('data'),
        )

    return GroupManagerPromptResponse(
        id=prompt.id,
        command=prompt.command,
        name=prompt.name,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
        write_access=True,
    )


@router.delete(
    '/groups/{group_id}/assets/prompts/{resource_id}/delete',
    response_model=bool,
)
async def delete_group_prompt(
    request: Request,
    group_id: str,
    resource_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Delete a group-owned prompt.

    In one transaction: delete ownership row, all grants, then the
    prompt row itself.
    """
    pending_events: list[dict[str, Any]] = []

    async with group_manager_tx(db):
        await require_group_manager(
            user.id, group_id, 'groups.manage_assets', db,
        )
        await _verify_ownership(group_id, 'prompt', resource_id, db)

        # Fetch prompt name/command for event
        result = await db.execute(
            select(Prompt)
            .where(Prompt.id == resource_id)
            .with_for_update()
        )
        prompt = result.scalars().first()
        prompt_name = prompt.name if prompt else None
        prompt_command = prompt.command if prompt else None

        # 1. Delete ownership row
        await GroupOwnedAssets.delete_asset_by_resource(
            'prompt', resource_id, db=db,
        )

        # 2. Delete all access grants
        await _revoke_all_access_flush('prompt', resource_id, db)

        # 3. Delete the prompt row
        await db.execute(
            delete(Prompt).where(Prompt.id == resource_id)
        )
        await db.flush()

        pending_events.append({
            'event': EVENTS.PROMPT_DELETED,
            'subject_id': resource_id,
            'data': {'name': prompt_name, 'command': prompt_command},
        })

    for evt in pending_events:
        await publish_event(
            request,
            evt['event'],
            actor=user,
            subject_id=evt['subject_id'],
            data=evt.get('data'),
        )

    return True


# =====================================================================
# ACL delta
# =====================================================================


@router.post(
    '/groups/{group_id}/assets/{resource_type}/{resource_id}/access/update',
    response_model=GroupManagerACLResponse,
)
async def update_group_asset_acl(
    request: Request,
    group_id: str,
    resource_type: str,
    resource_id: str,
    form_data: GroupManagerACLDeltaForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Adjust the owning-group write permission on a group-owned asset.

    The read grant for the owning group is a permanent baseline and
    cannot be removed through this endpoint.

    Only ``write: bool`` is accepted — the endpoint rejects whole ACL
    replacement or any other principal type.

    Skills are excluded — they use ``groups.manage_skills`` and have
    no ACL-delta endpoint; only baseline group ``read`` is allowed.
    """
    if resource_type not in SUPPORTED_OWNED_ASSET_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Unsupported resource_type: {resource_type}',
        )

    if resource_type == 'skill':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                'Skills do not support ACL delta. '
                'Scoped skill endpoints grant baseline group read only.'
            ),
        )

    pending_events: list[dict[str, Any]] = []
    event_cls = (
        EVENTS.KNOWLEDGE_ACCESS_UPDATED
        if resource_type == 'knowledge'
        else EVENTS.PROMPT_ACCESS_UPDATED
    )

    async with group_manager_tx(db):
        await require_group_manager(
            user.id, group_id, 'groups.manage_assets', db,
        )
        await _verify_ownership(group_id, resource_type, resource_id, db)

        # Ensure the baseline read grant exists (idempotent)
        await _grant_access_flush(
            resource_type, resource_id,
            PRINCIPAL_TYPE_GROUP, group_id, 'read',
            db,
        )

        # Delta: add or remove the write grant
        if form_data.write:
            await _grant_access_flush(
                resource_type, resource_id,
                PRINCIPAL_TYPE_GROUP, group_id, 'write',
                db,
            )
        else:
            await _revoke_access_flush(
                resource_type, resource_id,
                PRINCIPAL_TYPE_GROUP, group_id, 'write',
                db,
            )

        pending_events.append({
            'event': event_cls,
            'subject_id': resource_id,
            'data': {},  # omit content
        })

    for evt in pending_events:
        await publish_event(
            request,
            evt['event'],
            actor=user,
            subject_id=evt['subject_id'],
            data=evt.get('data'),
        )

    return GroupManagerACLResponse(
        resource_type=resource_type,
        resource_id=resource_id,
        write=form_data.write,
    )


# =====================================================================
# Scoped skill management (manage_skills) — Phase 3 skills-only slice
# =====================================================================

_SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9_-]{0,127}$')


def _normalize_skill_meta(raw: Any) -> SkillMeta:
    """Safely convert raw ``skill.meta`` (dict / None / SkillMeta) to SkillMeta.

    SQLAlchemy returns a plain dict from JSON columns; SkillMeta is a
    Pydantic model.  We must handle both forms (and None) to avoid
    AttributeError on ``.tags`` access.
    """
    if raw is None:
        return SkillMeta(tags=[])
    if isinstance(raw, SkillMeta):
        return raw
    if isinstance(raw, dict):
        return SkillMeta(tags=raw.get('tags', []))
    # Unexpected type — degrade gracefully
    return SkillMeta(tags=[])


def _make_group_skill_id(group_id: str, slug: str) -> str:
    """Build a collision-safe, group-namespaced skill ID.

    Format: ``g-{sha256(group_id)}--{slug}`` (≤ 196 chars for valid slugs).
    The full SHA-256 digest prevents groups with shared ID prefixes from
    colliding; the slug is user-supplied but validated; and the composite is
    unique per-group because ``(resource_type, resource_id)`` in
    ``group_owned_asset`` is globally unique.
    """
    group_namespace = hashlib.sha256(group_id.encode('utf-8')).hexdigest()
    return f'g-{group_namespace}--{slug}'


def _validate_skill_slug(slug: str) -> str:
    """Normalize and validate a skill slug.

    Returns the normalized form or raises HTTPException 400.
    """
    normalized = slug.lower().strip().replace(' ', '-')
    if not _SLUG_RE.match(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(
                'Invalid skill slug. Use lowercase letters, digits, '
                'hyphens, and underscores (1-128 chars).'
            ),
        )
    return normalized


# --- Flush-only skill primitives (non-committing) ---------------------


async def _skill_insert_flush(
    skill_id: str,
    group_id: str,
    form: GroupManagerSkillCreateForm,
    acting_user_id: str,
    db: AsyncSession,
) -> Skill:
    """Insert a Skill row with ``user_id='group-asset:<group_id>'``.

    The acting manager's ID is audit metadata only — stored in
    ``created_by`` on the ownership row, NOT in ``skill.user_id``.
    Flushed but not committed.
    """
    now = int(time.time())
    meta_dict = {'tags': form.tags} if form.tags else {}
    skill = Skill(
        id=skill_id,
        user_id=f'group-asset:{group_id}',
        name=form.name,
        description=form.description,
        content=form.content,
        meta=meta_dict,
        is_active=form.active,
        created_at=now,
        updated_at=now,
    )
    db.add(skill)
    await db.flush()
    return skill


async def _skill_update_flush(
    skill: Skill,
    form: GroupManagerSkillUpdateForm,
    db: AsyncSession,
) -> Skill:
    """Update a locked Skill row with only allowed fields.

    Flushed but not committed.
    """
    now = int(time.time())
    if form.name is not None:
        skill.name = form.name
    if form.description is not None:
        skill.description = form.description
    if form.content is not None:
        skill.content = form.content
    if form.tags is not None:
        skill.meta = {'tags': form.tags}
    if form.active is not None:
        skill.is_active = form.active
    skill.updated_at = now
    await db.flush()
    return skill


async def _skill_delete_flush(skill_id: str, db: AsyncSession) -> None:
    """Delete a Skill row and flush — no commit."""
    await db.execute(delete(Skill).where(Skill.id == skill_id))
    await db.flush()


# --- Scoped skill endpoints (manage_skills) ---------------------------


@router.get(
    '/groups/{group_id}/skills',
    response_model=list[GroupManagerSkillResponse],
)
async def list_group_skills(
    request: Request,
    group_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List skills owned by the target group.

    Each mutation handler uses ``group_manager_tx(db)`` +
    ``require_group_manager(..., 'groups.manage_skills', ...)``.
    """
    async with group_manager_tx(db):
        await require_group_manager(
            user.id, group_id, 'groups.manage_skills', db,
        )

        stmt = (
            select(GroupOwnedAsset)
            .where(
                GroupOwnedAsset.group_id == group_id,
                GroupOwnedAsset.resource_type == 'skill',
            )
            .order_by(GroupOwnedAsset.created_at.desc())
        )
        result = await db.execute(stmt)
        ownership_rows = result.scalars().all()

        if not ownership_rows:
            return []

        skill_ids = [o.resource_id for o in ownership_rows]
        skill_result = await db.execute(
            select(Skill).where(Skill.id.in_(skill_ids))
        )
        skills_by_id = {s.id: s for s in skill_result.scalars().all()}

    response: list[GroupManagerSkillResponse] = []
    for ownership in ownership_rows:
        skill = skills_by_id.get(ownership.resource_id)
        if skill is None:
            continue
        response.append(
            GroupManagerSkillResponse(
                id=skill.id,
                slug=skill.id.split('--', 1)[1] if '--' in skill.id else skill.id,
                name=skill.name,
                description=skill.description or '',
                content=skill.content,
                is_active=skill.is_active,
                meta=_normalize_skill_meta(skill.meta),
                created_at=skill.created_at,
                updated_at=skill.updated_at,
            )
        )
    return response


@router.post(
    '/groups/{group_id}/skills/create',
    response_model=GroupManagerSkillResponse,
)
async def create_group_skill(
    request: Request,
    group_id: str,
    form_data: GroupManagerSkillCreateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a skill owned by the group.

    Atomically creates:
    1. Skill row with ``user_id='group-asset:<group_id>'`` (flush only)
    2. GroupOwnedAsset ownership row (flush only)
    3. Owning-group ``read`` AccessGrant (flush only)

    Server controls the skill ID (group-namespaced collision-safe slug).
    The acting manager's user_id is audit metadata on the ownership row.
    """
    slug = _validate_skill_slug(form_data.slug)
    skill_id = _make_group_skill_id(group_id, slug)
    pending_events: list[dict[str, Any]] = []

    async with group_manager_tx(db):
        await require_group_manager(
            user.id, group_id, 'groups.manage_skills', db,
        )

        # Check skill ID uniqueness
        existing = await db.execute(
            select(Skill).where(Skill.id == skill_id),
        )
        if existing.scalars().first() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('A skill with this slug already exists in this group.'),
            )

        # 1. Create Skill row
        skill = await _skill_insert_flush(skill_id, group_id, form_data, user.id, db)

        # 2. Create ownership row
        await GroupOwnedAssets.insert_asset(
            resource_type='skill',
            resource_id=skill_id,
            group_id=group_id,
            created_by=user.id,
            db=db,
        )

        # 3. Owning-group read grant (baseline — no write grant)
        await _grant_access_flush(
            'skill', skill_id,
            PRINCIPAL_TYPE_GROUP, group_id, 'read',
            db,
        )

        pending_events.append({
            'event': EVENTS.SKILL_CREATED,
            'subject_id': skill_id,
            'data': {'name': form_data.name},
        })

    for evt in pending_events:
        await publish_event(
            request,
            evt['event'],
            actor=user,
            subject_id=evt['subject_id'],
            data=evt.get('data'),
        )

    return GroupManagerSkillResponse(
        id=skill.id,
        slug=slug,
        name=skill.name,
        description=skill.description or '',
        content=skill.content,
        is_active=skill.is_active,
        meta=_normalize_skill_meta(skill.meta),
        created_at=skill.created_at,
        updated_at=skill.updated_at,
    )


@router.get(
    '/groups/{group_id}/skills/{skill_id}',
    response_model=GroupManagerSkillResponse,
)
async def get_group_skill(
    request: Request,
    group_id: str,
    skill_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Read a single group-owned skill.

    Verifies ownership before returning.
    """
    async with group_manager_tx(db):
        await require_group_manager(
            user.id, group_id, 'groups.manage_skills', db,
        )
        await _verify_ownership(group_id, 'skill', skill_id, db)

        result = await db.execute(
            select(Skill).where(Skill.id == skill_id),
        )
        skill = result.scalars().first()
        if skill is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )

    return GroupManagerSkillResponse(
        id=skill.id,
        slug=skill_id.split('--', 1)[1] if '--' in skill_id else skill_id,
        name=skill.name,
        description=skill.description or '',
        content=skill.content,
        is_active=skill.is_active,
        meta=_normalize_skill_meta(skill.meta),
        created_at=skill.created_at,
        updated_at=skill.updated_at,
    )


@router.post(
    '/groups/{group_id}/skills/{skill_id}/update',
    response_model=GroupManagerSkillResponse,
)
async def update_group_skill(
    request: Request,
    group_id: str,
    skill_id: str,
    form_data: GroupManagerSkillUpdateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Update a group-owned skill.

    First verifies ownership, then updates only allowed fields.
    Rejects any attempt to change user_id, id, or access_grants.
    """
    pending_events: list[dict[str, Any]] = []

    async with group_manager_tx(db):
        await require_group_manager(
            user.id, group_id, 'groups.manage_skills', db,
        )
        await _verify_ownership(group_id, 'skill', skill_id, db)

        # Lock and fetch the skill row
        result = await db.execute(
            select(Skill).where(Skill.id == skill_id).with_for_update(),
        )
        skill = result.scalars().first()
        if skill is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )

        # Update only allowed fields
        await _skill_update_flush(skill, form_data, db)

        pending_events.append({
            'event': EVENTS.SKILL_UPDATED,
            'subject_id': skill_id,
            'data': {'name': skill.name},
        })

    for evt in pending_events:
        await publish_event(
            request,
            evt['event'],
            actor=user,
            subject_id=evt['subject_id'],
            data=evt.get('data'),
        )

    return GroupManagerSkillResponse(
        id=skill.id,
        slug=skill_id.split('--', 1)[1] if '--' in skill_id else skill_id,
        name=skill.name,
        description=skill.description or '',
        content=skill.content,
        is_active=skill.is_active,
        meta=_normalize_skill_meta(skill.meta),
        created_at=skill.created_at,
        updated_at=skill.updated_at,
    )


@router.delete(
    '/groups/{group_id}/skills/{skill_id}/delete',
    response_model=bool,
)
async def delete_group_skill(
    request: Request,
    group_id: str,
    skill_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Delete a group-owned skill.

    In one transaction: delete ownership row, all grants, then the
    skill row itself.
    """
    pending_events: list[dict[str, Any]] = []

    async with group_manager_tx(db):
        await require_group_manager(
            user.id, group_id, 'groups.manage_skills', db,
        )
        await _verify_ownership(group_id, 'skill', skill_id, db)

        # Fetch skill name for event
        result = await db.execute(
            select(Skill).where(Skill.id == skill_id).with_for_update(),
        )
        skill = result.scalars().first()
        skill_name = skill.name if skill else None

        # 1. Delete ownership row
        await GroupOwnedAssets.delete_asset_by_resource(
            'skill', skill_id, db=db,
        )

        # 2. Delete all access grants
        await _revoke_all_access_flush('skill', skill_id, db)

        # 3. Delete the skill row
        await _skill_delete_flush(skill_id, db)

        pending_events.append({
            'event': EVENTS.SKILL_DELETED,
            'subject_id': skill_id,
            'data': {'name': skill_name},
        })

    for evt in pending_events:
        await publish_event(
            request,
            evt['event'],
            actor=user,
            subject_id=evt['subject_id'],
            data=evt.get('data'),
        )

    return True
