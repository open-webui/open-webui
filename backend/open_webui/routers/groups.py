from typing import Optional
import time

from open_webui.models.users import Users
from open_webui.models.groups import (
    Groups,
    GroupForm,
    GroupUpdateForm,
    GroupResponse,
)

from open_webui.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, status
from open_webui.utils.auth import get_admin_user, get_verified_user

router = APIRouter()

# Track groups currently being edited to prevent race conditions
# Format: {group_id: timestamp_when_editing_started}
GROUPS_BEING_EDITED = {}


def mark_group_being_edited(group_id: str):
    """Mark a group as currently being edited"""
    GROUPS_BEING_EDITED[group_id] = int(time.time())


def unmark_group_being_edited(group_id: str):
    """Remove a group from the being edited list"""
    GROUPS_BEING_EDITED.pop(group_id, None)


def is_group_being_edited(group_id: str) -> bool:
    """Check if a group is currently being edited (with 10-minute timeout)"""
    if group_id not in GROUPS_BEING_EDITED:
        return False

    # Auto-cleanup after 10 minutes to prevent permanent blocking
    edit_start_time = GROUPS_BEING_EDITED[group_id]
    if int(time.time()) - edit_start_time > 600:  # 10 minutes
        GROUPS_BEING_EDITED.pop(group_id, None)
        return False

    return True


############################
# GetFunctions
############################


@router.get("/", response_model=list[GroupResponse])
async def get_groups(user=Depends(get_verified_user)):
    if user.role == "admin":
        return Groups.get_groups()
    else:
        return Groups.get_groups_by_member_id(user.id)


############################
# CreateNewGroup
############################


@router.post("/create", response_model=Optional[GroupResponse])
async def create_new_function(form_data: GroupForm, user=Depends(get_admin_user)):
    try:
        group = Groups.insert_new_group(user.id, form_data)
        if group:
            return group
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error creating group"),
            )
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# GetGroupById
############################


@router.get("/id/{id}", response_model=Optional[GroupResponse])
async def get_group_by_id(id: str, user=Depends(get_admin_user)):
    group = Groups.get_group_by_id(id)
    if group:
        return group
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateGroupById
############################


@router.post("/id/{id}/update", response_model=Optional[GroupResponse])
async def update_group_by_id(
    id: str, form_data: GroupUpdateForm, user=Depends(get_admin_user)
):
    try:
        if form_data.user_ids:
            form_data.user_ids = Users.get_valid_user_ids(form_data.user_ids)

        # Get the current group state before update to compare domain changes
        current_group = Groups.get_group_by_id(id)

        # Update the group
        group = Groups.update_group_by_id(id, form_data)

        if group:
            # Handle immediate domain-based user removal if domains were changed
            if (
                hasattr(form_data, "allowed_domains")
                and form_data.allowed_domains is not None
            ):
                from open_webui.utils.domain_group_assignment import (
                    domain_assignment_service,
                )

                # If domains were removed or changed, immediately remove users who no longer match
                if (
                    current_group
                    and current_group.allowed_domains != group.allowed_domains
                ):
                    users_to_check = group.user_ids or []
                    users_removed = []

                    for user_id in users_to_check:
                        # Get user details
                        user_info = Users.get_user_by_id(user_id)
                        if user_info and user_info.email:
                            # Skip non-user roles - they should not be auto-removed even if domains don't match
                            # Only users with 'user' role are subject to automatic domain-based management
                            if user_info.role != "user":
                                continue

                            # Check if user's domain still matches any allowed domains
                            should_be_in_group = (
                                domain_assignment_service.should_user_be_in_group(
                                    user_info.email, group.allowed_domains or []
                                )
                            )

                            if not should_be_in_group:
                                # Remove user immediately
                                if domain_assignment_service.remove_user_from_group(
                                    group.id, user_id
                                ):
                                    users_removed.append(user_info.email)

                    if users_removed:
                        # Refresh the group to get the updated user list
                        group = Groups.get_group_by_id(id)
                        print(
                            f"Immediately removed {len(users_removed)} users from group '{group.name}' due to domain changes: {users_removed}"
                        )

            return group
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error updating group"),
            )
    except Exception as e:
        print(e)
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
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# Group Editing Lock Endpoints
############################


@router.post("/id/{id}/lock-editing", response_model=bool)
async def lock_group_for_editing(id: str, user=Depends(get_admin_user)):
    """Mark a group as being actively edited to prevent background processing race conditions"""
    try:
        mark_group_being_edited(id)
        return True
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.post("/id/{id}/unlock-editing", response_model=bool)
async def unlock_group_from_editing(id: str, user=Depends(get_admin_user)):
    """Remove a group from being actively edited, allowing background processing to resume"""
    try:
        unmark_group_being_edited(id)
        return True
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )
