import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_admin_user
from open_webui.models.roles import (
    RoleModel,
    Roles,
    RoleAddForm
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
# GetRoles
############################


@router.get("/", response_model=list[RoleModel])
async def get_roles(skip: Optional[int] = None, limit: Optional[int] = None, user=Depends(get_admin_user)):
    return Roles.get_roles(skip, limit)


############################
# AddRole
############################


@router.post("/", response_model=Optional[RoleModel])
async def add_role(form_data: RoleAddForm, user=Depends(get_admin_user)):
    # Check if the role already exists
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
@router.delete("/{role_name}", response_model=bool)
async def delete_role_by_id(role_name: str, user=Depends(get_admin_user)):
    role = Roles.get_role_by_name(role_name)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with name '{role_name}' not found.",
        )

    result = Roles.delete_by_id(role.id)
    if result:
        return True

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=ERROR_MESSAGES.DELETE_ROLE_ERROR,
    )


############################
# GetPermissionForRole
############################


@router.get("/{role_name}/permissions")
async def get_default_permissions_by_role_name(role_name: str, user=Depends(get_admin_user)):
    if not Roles.exists(role_name):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Role do not exists. Please check the role name and try again.',
        )

    permissions = Permissions.get_ordre_by_category(role_name)

    if permissions:
        return permissions

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail='Permissions fetch failed. Please try again later.',
    )


############################
# AddNewPermissionToRole
############################

@router.post("/{role_name}/permission")
async def add_new_default_permission_with_role(role_name: str, form_data: PermissionModel,
                                               user=Depends(get_admin_user)):
    perm = Permissions.add(permission=form_data, role_name=role_name)

    if perm:
        return True

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail='Something went wrong. Please try again.',
    )


############################
# DeletePermissionFromRole
###########################

@router.post("/{role_name}/permission/link")
async def link_default_permission_to_role(role_name: str, form_data: PermissionRoleForm, user=Depends(get_admin_user)):
    permission = Permissions.get(form_data.permission_name, form_data.category)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission with name '{form_data.permission_name}' and category '{form_data.category}' not found.",
        )

    role = Roles.get_role_by_name(role_name)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with name '{role_name}' not found.",
        )

    result = Permissions.link(permission_id=permission.id, role_id=role.id, value=form_data.value)
    if result:
        return True

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail='Something went wrong. Please try again.',
    )


@router.delete("/{role_name}/permission/{permission_category}/{permission_name}")
async def unlink_default_permission_from_role(
        role_name: str,
        permission_name: str,
        category: PermissionCategory,
        user=Depends(get_admin_user)
    ):

    role = Roles.get_role_by_name(role_name)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with name '{role_name}' not found.",
        )

    permission = Permissions.get(permission_name, category)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission with name '{permission_name}' and category '{category}' not found.",
        )

    result = Permissions.unlink(permission_id=permission.id, role_id=role.id)
    if result:
        return True

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail='Something went wrong. Please try again.',
    )
