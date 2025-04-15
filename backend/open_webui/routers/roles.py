import logging
from typing import Optional

from open_webui.models.auths import Auths
from open_webui.models.groups import Groups
from open_webui.models.chats import Chats
from open_webui.models.roles import (
    RoleModel,
    Roles
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
# UpdateUserRole
############################


# @router.post("/", response_model=Optional[RoleModel])
# async def update_user_role(form_data: UserRoleUpdateForm, user=Depends(get_admin_user)):
#     if user.id != form_data.id and form_data.id != Users.get_first_user().id:
#         return Users.update_user_role_by_id(form_data.id, form_data.role)
#
#     raise HTTPException(
#         status_code=status.HTTP_403_FORBIDDEN,
#         detail=ERROR_MESSAGES.ACTION_PROHIBITED,
#     )
#
#
# ############################
# # DeleteUserById
# ############################
#
#
# @router.delete("/{user_id}", response_model=bool)
# async def delete_user_by_id(user_id: str, user=Depends(get_admin_user)):
#     if user.id != user_id:
#         result = Auths.delete_auth_by_id(user_id)
#
#         if result:
#             return True
#
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=ERROR_MESSAGES.DELETE_USER_ERROR,
#         )
#
#     raise HTTPException(
#         status_code=status.HTTP_403_FORBIDDEN,
#         detail=ERROR_MESSAGES.ACTION_PROHIBITED,
#     )
