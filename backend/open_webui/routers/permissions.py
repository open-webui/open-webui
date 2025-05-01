import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_admin_user
from open_webui.models.roles import (
    RoleModel,
    Roles,
    RoleForm
)
from open_webui.models.permissions import (
    Permissions,
    PermissionModel,
    PermissionCategory,
    PermissionRoleForm
)


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


############################
# GetPermissions
############################


@router.get("/", response_model=list[PermissionModel])
async def get_permissions(user=Depends(get_admin_user)):
    return Permissions.get_all()

############################
# AddPermission
############################


@router.post("/", response_model=Optional[PermissionModel])
async def add_permissions(form_data: RoleForm, user=Depends(get_admin_user)):
    pass
    # perm = Permissions.add(permission=form_data, role_name=role_name)
    #
    # if perm:
    #     return True
    #
    # raise HTTPException(
    #     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #     detail='Something went wrong. Please try again.',
    # )


############################
# UpdatePermissionById
############################

@router.post("/{permission_id}", response_model=Optional[PermissionModel])
async def update_permission_name(role_id: int, form_data: RoleForm, user=Depends(get_admin_user)):
    pass


############################
# DeletePermissionById
############################


# TODO(jeskr): Check if role is used by any users before deleting it.
@router.delete("/{permission_id}", response_model=bool)
async def delete_permission_by_name(role_name: str, user=Depends(get_admin_user)):
    pass