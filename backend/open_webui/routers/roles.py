import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_admin_user
from open_webui.models.roles import RoleModel, Roles, RoleForm
from open_webui.models.permissions import (
    Permissions,
    PermissionModel,
    PermissionCategory,
    PermissionRoleForm,
)


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
async def add_role(form_data: RoleForm, user=Depends(get_admin_user)):
    # Check if the role already exists
    existing_role = Roles.get_role_by_name(name=form_data.role)
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERROR_MESSAGES.ROLE_ALREADY_EXISTS(role=form_data.role),
        )

    return Roles.insert_new_role(name=form_data.role)


############################
# UpdateRoleById
############################


@router.post("/{role_id}", response_model=Optional[RoleModel])
async def update_role_name(
    role_id: int, form_data: RoleForm, user=Depends(get_admin_user)
):
    # Check if the role already exists
    existing_role = Roles.get_role_by_id(role_id)
    if not existing_role:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERROR_MESSAGES.ROLE_DO_NOT_EXISTS,
        )

    return Roles.update_name_by_id(role_id, form_data.role)


############################
# DeleteRoleById
############################


@router.delete("/{role_name}", response_model=bool)
async def delete_role_by_id(role_name: str, user=Depends(get_admin_user)):
    role = Roles.get_role_by_name(role_name)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.ROLE_DO_NOT_EXISTS,
        )

    result = Roles.delete_by_id(role.id)
    if result:
        return True

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=ERROR_MESSAGES.ROLE_DELETE_ERROR,
    )


############################
# GetPermissionForRole
############################


@router.get("/{role_name}/permissions")
async def get_default_permissions_by_role_name(
    role_name: str, user=Depends(get_admin_user)
):
    if not Roles.exists(role_name):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.ROLE_NOT_FOUND,
        )

    permissions = Permissions.get_ordre_by_category(role_name)

    if permissions:
        return permissions

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=ERROR_MESSAGES.PERMISSION_FETCH_FAILED,
    )


############################
# LinkPermissionToRole
###########################


@router.post("/{role_name}/permission/link")
async def link_default_permission_to_role(
    role_name: str, form_data: PermissionRoleForm, user=Depends(get_admin_user)
):
    permission = Permissions.get(form_data.permission_name, form_data.category)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.PERMISSION_NOT_FOUND(
                name=form_data.permission_name, category=form_data.category.value
            ),
        )

    role = Roles.get_role_by_name(role_name)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.ROLE_NOT_FOUND,
        )

    result = Permissions.link(
        permission_id=permission.id, role_id=role.id, value=form_data.value
    )
    if result:
        return True

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=ERROR_MESSAGES.ROLE_ERROR,
    )


############################
# UnlinkPermissionToRole
###########################


@router.delete("/{role_name}/permission/{permission_category}/{permission_name}")
async def unlink_default_permission_from_role(
    role_name: str,
    permission_name: str,
    category: PermissionCategory,
    user=Depends(get_admin_user),
):

    role = Roles.get_role_by_name(role_name)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.ROLE_NOT_FOUND,
        )

    permission = Permissions.get(permission_name, category)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.PERMISSION_NOT_FOUND(
                name=permission_name, category=category
            ),
        )

    result = Permissions.unlink(permission_id=permission.id, role_id=role.id)
    if result:
        return True

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=ERROR_MESSAGES.ROLE_ERROR,
    )
