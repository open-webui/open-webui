import os
from pathlib import Path
from typing import Optional
import logging

from open_webui.models.users import Users
from open_webui.models.groups import (
    Groups,
    GroupForm,
    GroupUpdateForm,
    GroupResponse,
    UserIdsForm,
)

from open_webui.config import CACHE_DIR
from open_webui.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, Request, status

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.env import SRC_LOG_LEVELS


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


############################
# Helper Functions
############################


def get_group_response(group) -> GroupResponse:
    """Helper to build GroupResponse with member_count and manager_ids."""
    return GroupResponse(
        **group.model_dump(),
        member_count=Groups.get_group_member_count_by_id(group.id),
        manager_ids=Groups.get_group_manager_ids_by_id(group.id),
    )


def is_admin_or_group_manager(user, group_id: str) -> bool:
    """Check if user is an admin or a manager of the specified group."""
    if user.role == "admin":
        return True
    return Groups.is_group_manager(user.id, group_id)


def require_admin_or_group_manager(user, group_id: str):
    """Raise 403 if user is not admin or group manager."""
    if not is_admin_or_group_manager(user, group_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or group managers can perform this action",
        )


############################
# GetGroups
############################


@router.get("/", response_model=list[GroupResponse])
async def get_groups(share: Optional[bool] = None, user=Depends(get_verified_user)):
    if user.role == "admin":
        groups = Groups.get_groups()
    else:
        groups = Groups.get_groups_by_member_id(user.id)

    group_list = []

    for group in groups:
        if share is not None:
            # Check if the group has data and a config with share key
            if (
                group.data
                and "share" in group.data.get("config", {})
                and group.data["config"]["share"] != share
            ):
                continue

        group_list.append(get_group_response(group))

    return group_list


############################
# GetManagedGroups
############################


@router.get("/user/managed", response_model=list[GroupResponse])
async def get_managed_groups(user=Depends(get_verified_user)):
    """Get all groups where the current user is a manager."""
    groups = Groups.get_groups_by_manager_id(user.id)
    return [get_group_response(group) for group in groups]


############################
# CreateNewGroup
############################


@router.post("/create", response_model=Optional[GroupResponse])
async def create_new_group(form_data: GroupForm, user=Depends(get_admin_user)):
    try:
        group = Groups.insert_new_group(user.id, form_data)
        if group:
            return get_group_response(group)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error creating group"),
            )
    except Exception as e:
        log.exception(f"Error creating a new group: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# GetGroupById
############################


@router.get("/id/{id}", response_model=Optional[GroupResponse])
async def get_group_by_id(id: str, user=Depends(get_verified_user)):
    # Allow admins and group managers to view group details
    require_admin_or_group_manager(user, id)

    group = Groups.get_group_by_id(id)
    if group:
        return get_group_response(group)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateGroupById
############################


@router.post("/id/{id}/update", response_model=Optional[GroupResponse])
async def update_group_by_id(
    id: str, form_data: GroupUpdateForm, user=Depends(get_verified_user)
):
    require_admin_or_group_manager(user, id)

    # If user is not admin, they cannot modify permissions
    if user.role != "admin":
        # Get current group to compare permissions
        current_group = Groups.get_group_by_id(id)
        if current_group and form_data.permissions != current_group.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can modify group permissions",
            )

    try:
        group = Groups.update_group_by_id(id, form_data)
        if group:
            return get_group_response(group)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error updating group"),
            )
    except Exception as e:
        log.exception(f"Error updating group {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# AddUserToGroupByUserIdAndGroupId
############################


@router.post("/id/{id}/users/add", response_model=Optional[GroupResponse])
async def add_user_to_group(
    id: str, form_data: UserIdsForm, user=Depends(get_verified_user)
):
    require_admin_or_group_manager(user, id)

    try:
        if form_data.user_ids:
            form_data.user_ids = Users.get_valid_user_ids(form_data.user_ids)

        group = Groups.add_users_to_group(id, form_data.user_ids)
        if group:
            return get_group_response(group)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error adding users to group"),
            )
    except Exception as e:
        log.exception(f"Error adding users to group {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# RemoveUsersFromGroup
############################


@router.post("/id/{id}/users/remove", response_model=Optional[GroupResponse])
async def remove_users_from_group(
    id: str, form_data: UserIdsForm, user=Depends(get_verified_user)
):
    require_admin_or_group_manager(user, id)

    # Managers cannot remove themselves
    if user.role != "admin" and form_data.user_ids and user.id in form_data.user_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Group managers cannot remove themselves from the group",
        )

    try:
        group = Groups.remove_users_from_group(id, form_data.user_ids)
        if group:
            return get_group_response(group)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error removing users from group"),
            )
    except Exception as e:
        log.exception(f"Error removing users from group {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# GetGroupManagers
############################


@router.get("/id/{id}/managers", response_model=list[str])
async def get_group_managers(id: str, user=Depends(get_verified_user)):
    """Get the list of manager user IDs for a group."""
    require_admin_or_group_manager(user, id)

    group = Groups.get_group_by_id(id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    return Groups.get_group_manager_ids_by_id(id)


############################
# UpdateGroupManagers
############################


@router.post("/id/{id}/managers/update", response_model=Optional[GroupResponse])
async def update_group_managers(
    id: str, form_data: UserIdsForm, user=Depends(get_admin_user)
):
    """Update the managers for a group. Admin only."""
    try:
        # Validate manager IDs
        manager_ids = form_data.user_ids or []
        if manager_ids:
            manager_ids = Users.get_valid_user_ids(manager_ids)

        group = Groups.set_group_managers_by_id(id, manager_ids)
        if group:
            return get_group_response(group)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error updating group managers"),
            )
    except Exception as e:
        log.exception(f"Error updating managers for group {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# DeleteGroupById
############################


@router.delete("/id/{id}/delete", response_model=bool)
async def delete_group_by_id(id: str, user=Depends(get_admin_user)):
    try:
        result = Groups.delete_group_by_id(id)
        if result:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error deleting group"),
            )
    except Exception as e:
        log.exception(f"Error deleting group {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )
