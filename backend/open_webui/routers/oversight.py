import logging
from typing import Optional

from open_webui.models.users import Users, UserInfoResponse
from open_webui.models.groups import Groups, GroupResponse
from open_webui.models.group_oversight import (
    OversightExclusions,
    GroupOversightExclusionModel,
    GroupOversightExclusionForm,
)
from open_webui.models.chats import Chats, ChatTitleIdResponse

from open_webui.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, Request, status

from open_webui.internal.db import get_session
from sqlalchemy.orm import Session

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import (
    can_read_group_member_chats,
    get_oversight_target_user_ids,
    can_read_user_chats_in_group,
    has_capability,
)

from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter()


############################
# Response Models
############################


class OversightUserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    groups: list[dict] = []


class OversightGroupResponse(BaseModel):
    id: str
    name: str
    description: str
    member_count: int = 0


############################
# GetOversightUsers
############################


@router.get("/users", response_model=list[OversightUserResponse])
async def get_oversight_users(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    List all users whose chats the requesting user can oversee.
    Requires audit.read_group_chats capability.
    """
    if not can_read_group_member_chats(user.id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    target_user_ids = get_oversight_target_user_ids(user.id, db=db)
    if not target_user_ids:
        return []

    # Get user info for all target users
    target_user_id_list = list(target_user_ids)
    users = Users.get_users_by_user_ids(target_user_id_list, db=db)

    # Batch-fetch groups for all target users
    user_groups_map = Groups.get_groups_by_member_ids(target_user_id_list, db=db)

    result = []
    for u in users:
        groups_for_user = user_groups_map.get(u.id, [])
        result.append(
            OversightUserResponse(
                id=u.id,
                name=u.name,
                email=u.email,
                role=u.role,
                groups=[{"id": g.id, "name": g.name} for g in groups_for_user],
            )
        )

    return result


############################
# GetOversightUserChats
############################


@router.get("/users/{user_id}/chats", response_model=list[ChatTitleIdResponse])
async def get_oversight_user_chats(
    user_id: str,
    skip: int = 0,
    limit: int = 50,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Get paginated chat list for a specific overseen user.
    Verifies the requesting user can oversee the target via group admin oversight.
    """
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
# GetOversightGroups
############################


@router.get("/groups", response_model=list[OversightGroupResponse])
async def get_oversight_groups(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    List groups where the requesting user is admin, with member counts.
    """
    if not can_read_group_member_chats(user.id, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    admin_groups = Groups.get_groups_where_admin(user.id, db=db)
    if not admin_groups:
        return []

    # Batch-fetch member counts
    group_ids = [g.id for g in admin_groups]
    member_counts = Groups.get_group_member_counts_by_ids(group_ids, db=db)

    return [
        OversightGroupResponse(
            id=g.id,
            name=g.name,
            description=g.description,
            member_count=member_counts.get(g.id, 0),
        )
        for g in admin_groups
    ]


############################
# Group Oversight Exclusions
############################


@router.get(
    "/groups/id/{group_id}/exclusions",
    response_model=list[GroupOversightExclusionModel],
)
async def get_group_exclusions(
    group_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    List oversight exclusions for a group.
    Requires system admin OR group admin of the specified group.
    """
    _verify_group_admin_access(user, group_id, db)

    return OversightExclusions.get_exclusions_by_group(group_id, db=db)


@router.post(
    "/groups/id/{group_id}/exclusions",
    response_model=Optional[GroupOversightExclusionModel],
)
async def add_group_exclusion(
    group_id: str,
    form_data: GroupOversightExclusionForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Add a user to the oversight exclusion list for a group.
    Requires system admin OR group admin of the specified group.
    """
    _verify_group_admin_access(user, group_id, db)

    exclusion = OversightExclusions.add_exclusion(group_id, form_data.user_id, db=db)
    if exclusion:
        return exclusion
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error adding exclusion"),
        )


@router.delete(
    "/groups/id/{group_id}/exclusions/{user_id}",
    response_model=bool,
)
async def remove_group_exclusion(
    group_id: str,
    user_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Remove a user from the oversight exclusion list for a group.
    Requires system admin OR group admin of the specified group.
    """
    _verify_group_admin_access(user, group_id, db)

    result = OversightExclusions.remove_exclusion(group_id, user_id, db=db)
    if result:
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Helpers
############################


def _verify_group_admin_access(user, group_id: str, db: Session):
    """
    Verify the user is a system admin or a group admin of the specified group.
    Raises HTTPException if access is denied.
    """
    if user.role == "admin":
        return

    member_role = Groups.get_member_role(group_id, user.id, db=db)
    if member_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
