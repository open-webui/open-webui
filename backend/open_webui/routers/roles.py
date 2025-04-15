import logging
from typing import Optional

from pprint import pprint

from open_webui.models.auths import Auths
from open_webui.models.groups import Groups
from open_webui.models.chats import Chats
from open_webui.models.roles import (
    RoleModel,
    Roles,
    RoleAddForm,
)


from open_webui.socket.main import get_active_status_by_user_id
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.utils.auth import get_admin_user, get_password_hash, get_verified_user
from open_webui.utils.access_control import get_permissions


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

############################
# GetRoles
############################


@router.get("/", response_model=list[RoleModel])
async def get_roles(
    skip: Optional[int] = None,
    limit: Optional[int] = None,
    user=Depends(get_admin_user),
):
    return Roles.get_roles(skip, limit)

############################
# AddRole
############################


@router.post("/", response_model=Optional[RoleModel])
async def add_role(form_data: RoleAddForm, user=Depends(get_admin_user)):
    # Check if role already exists
    existing_role = Roles.get_role_by_name(name=form_data.role)
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role with name '{form_data.role}' already exists"
        )

    return Roles.insert_new_role(name=form_data.role)


############################
# DeleteRoleById
############################

# TODO(jeskr): Check if role is used by any users before deleting it.
@router.delete("/{role_id}", response_model=bool)
async def delete_role_by_id(role_id: str, user=Depends(get_admin_user)):
    result = Roles.delete_by_id(role_id)
    if result:
        return True

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=ERROR_MESSAGES.DELETE_ROLE_ERROR,
    )
