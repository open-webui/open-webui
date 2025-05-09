import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_admin_user
from open_webui.models.roles import RoleForm
from open_webui.models.permissions import (
    Permissions,
    PermissionModel,
    PermissionCreateModel,
    PermissionEmptyModel,
    PermissionCategory,
    PermissionAddForm,
)


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


############################
# GetPermissions
############################


@router.get("/", response_model=list[PermissionEmptyModel])
async def get_permissions(user=Depends(get_admin_user)):
    return Permissions.get_all()


############################
# AddPermission
############################


@router.post("/", response_model=Optional[PermissionEmptyModel])
async def add_permissions(form_data: PermissionAddForm, user=Depends(get_admin_user)):
    permission = Permissions.add(permission=form_data)
    if permission:
        return permission

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Something went wrong. Please try again.",
    )
