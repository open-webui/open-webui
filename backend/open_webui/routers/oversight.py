import logging
from typing import Optional

from open_webui.models.users import Users
from open_webui.models.groups import Groups
from open_webui.models.oversight_assignment import (
    OversightAssignments,
    OversightAssignmentModel,
    OversightAssignmentForm,
    BulkAssignForm,
)
from open_webui.models.chats import Chats, ChatTitleIdResponse

from open_webui.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, Request, status

from open_webui.internal.db import get_session
from sqlalchemy.orm import Session

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import (
    can_read_group_member_chats,
    can_read_user_chats_in_group,
)

from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter()


############################
# Response Models
############################


class OversightTargetResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    groups: list[dict] = []


############################
# GetOversightTargets
############################


@router.get("/targets", response_model=list[OversightTargetResponse])
async def get_oversight_targets(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if not can_read_group_member_chats(user.id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    target_ids = OversightAssignments.get_target_ids_for_overseer(user.id, db=db)
    if not target_ids:
        return []

    target_id_list = list(target_ids)
    users = Users.get_users_by_user_ids(target_id_list, db=db)

    user_groups_map = Groups.get_groups_by_member_ids(target_id_list, db=db)

    return [
        OversightTargetResponse(
            id=u.id,
            name=u.name,
            email=u.email,
            role=u.role,
            groups=[
                {"id": g.id, "name": g.name} for g in user_groups_map.get(u.id, [])
            ],
        )
        for u in users
    ]


############################
# GetTargetChats
############################


@router.get("/targets/{user_id}/chats", response_model=list[ChatTitleIdResponse])
async def get_target_chats(
    user_id: str,
    skip: int = 0,
    limit: int = 50,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if not can_read_user_chats_in_group(user.id, user_id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    chats = Chats.get_chat_list_by_user_id(
        user_id,
        include_archived=True,
        skip=skip,
        limit=limit,
        db=db,
    )

    return [
        ChatTitleIdResponse(
            id=chat.id,
            title=chat.title,
            updated_at=chat.updated_at,
            created_at=chat.created_at,
        )
        for chat in chats
    ]


############################
# Assignments CRUD
############################


@router.get("/assignments", response_model=list[OversightAssignmentModel])
async def get_assignments(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role == "admin":
        return OversightAssignments.get_all_assignments(db=db)
    return OversightAssignments.get_targets_for_overseer(user.id, db=db)


@router.post("/assignments", response_model=Optional[OversightAssignmentModel])
async def create_assignment(
    form_data: OversightAssignmentForm,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    effective_overseer = form_data.overseer_id if form_data.overseer_id else user.id

    assignment = OversightAssignments.add_assignment(
        overseer_id=effective_overseer,
        target_id=form_data.target_id,
        created_by=user.id,
        source=form_data.source,
        db=db,
    )
    if assignment:
        return assignment

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERROR_MESSAGES.DEFAULT("Error creating assignment"),
    )


@router.delete("/assignments/{overseer_id}/{target_id}", response_model=bool)
async def delete_assignment(
    overseer_id: str,
    target_id: str,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    result = OversightAssignments.remove_assignment(overseer_id, target_id, db=db)
    if result:
        return result

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ERROR_MESSAGES.NOT_FOUND,
    )


@router.post("/assignments/bulk", response_model=list[OversightAssignmentModel])
async def bulk_assign_from_group(
    form_data: BulkAssignForm,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    group = Groups.get_group_by_id(form_data.group_id, db=db)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    member_ids = Groups.get_group_user_ids_by_id(form_data.group_id, db=db)
    source = f"group:{group.name}"

    created = []
    for member_id in member_ids:
        if member_id == form_data.overseer_id:
            continue

        assignment = OversightAssignments.add_assignment(
            overseer_id=form_data.overseer_id,
            target_id=member_id,
            created_by=user.id,
            source=source,
            db=db,
        )
        if assignment:
            created.append(assignment)

    return created
