import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from loguru import logger as loguru_logger

from open_webui.models.roles import (
    Roles,
    RoleCapabilities,
    RoleModel,
    RoleResponse,
    RoleListResponse,
    RoleForm,
    RoleUpdateForm,
    CapabilityForm,
    SYSTEM_CAPABILITIES,
)
from open_webui.models.users import Users

from open_webui.constants import ERROR_MESSAGES
from open_webui.internal.db import get_session
from open_webui.utils.auth import get_admin_user
from open_webui.utils.access_control import has_capability
from open_webui.utils.audit import AuditLogger, AuditLogEntry

log = logging.getLogger(__name__)
audit_logger = AuditLogger(loguru_logger)

router = APIRouter()


def _audit_role_change(
    user, action: str, role_name: str, request: Optional[Request] = None, **kwargs
):
    entry = AuditLogEntry(
        id=str(uuid.uuid4()),
        user={"id": user.id, "name": user.name, "email": user.email, "role": user.role},
        audit_level="METADATA",
        verb=action,
        request_uri=f"/api/v1/roles",
        user_agent=request.headers.get("user-agent") if request else None,
        source_ip=request.client.host if request and request.client else None,
        request_object={"role_name": role_name, **kwargs},
    )
    audit_logger.write(entry)


############################
# Get All Roles
############################


@router.get("/", response_model=RoleListResponse)
async def get_roles(
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    roles = Roles.get_all_roles(db=db)

    role_responses = []
    for role in roles:
        capabilities = RoleCapabilities.get_capabilities_by_role_id(role.id, db=db)
        role_responses.append(
            RoleResponse(
                **role.model_dump(),
                capabilities=capabilities,
            )
        )

    return RoleListResponse(items=role_responses, total=len(role_responses))


############################
# Get Available Capabilities
############################


@router.get("/capabilities")
async def get_available_capabilities(
    user=Depends(get_admin_user),
):
    return {
        "capabilities": [
            {"key": key, "description": desc}
            for key, desc in SYSTEM_CAPABILITIES.items()
        ]
    }


############################
# Get Role by ID
############################


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role_by_id(
    role_id: str,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    role = Roles.get_role_by_id(role_id, db=db)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    capabilities = RoleCapabilities.get_capabilities_by_role_id(role_id, db=db)
    return RoleResponse(**role.model_dump(), capabilities=capabilities)


############################
# Create Role
############################


@router.post("/", response_model=RoleResponse)
async def create_role(
    form_data: RoleForm,
    request: Request,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    existing = Roles.get_role_by_name(form_data.name, db=db)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists",
        )

    role = Roles.insert_new_role(form_data, db=db)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    _audit_role_change(user, "CREATE_ROLE", role.name, request, role_id=role.id)
    return RoleResponse(**role.model_dump(), capabilities=[])


############################
# Update Role
############################


@router.post("/{role_id}/update", response_model=RoleResponse)
async def update_role(
    role_id: str,
    form_data: RoleUpdateForm,
    request: Request,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    role = Roles.get_role_by_id(role_id, db=db)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if form_data.name and form_data.name != role.name:
        existing = Roles.get_role_by_name(form_data.name, db=db)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role with this name already exists",
            )

    updated_role = Roles.update_role_by_id(role_id, form_data, db=db)
    if not updated_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    _audit_role_change(
        user,
        "UPDATE_ROLE",
        updated_role.name,
        request,
        role_id=role_id,
        changes=form_data.model_dump(exclude_none=True),
    )
    capabilities = RoleCapabilities.get_capabilities_by_role_id(role_id, db=db)
    return RoleResponse(**updated_role.model_dump(), capabilities=capabilities)


############################
# Delete Role
############################


@router.delete("/{role_id}")
async def delete_role(
    role_id: str,
    request: Request,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    role = Roles.get_role_by_id(role_id, db=db)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete system roles",
        )

    role_name = role.name
    success = Roles.delete_role_by_id(role_id, db=db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    _audit_role_change(user, "DELETE_ROLE", role_name, request, role_id=role_id)
    return {"success": True}


############################
# Set Role Capabilities
############################


@router.post("/{role_id}/capabilities", response_model=RoleResponse)
async def set_role_capabilities(
    role_id: str,
    form_data: CapabilityForm,
    request: Request,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    role = Roles.get_role_by_id(role_id, db=db)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    invalid_caps = [c for c in form_data.capabilities if c not in SYSTEM_CAPABILITIES]
    if invalid_caps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid capabilities: {', '.join(invalid_caps)}",
        )

    RoleCapabilities.set_capabilities(role_id, form_data.capabilities, db=db)

    _audit_role_change(
        user,
        "SET_CAPABILITIES",
        role.name,
        request,
        role_id=role_id,
        capabilities=form_data.capabilities,
    )
    capabilities = RoleCapabilities.get_capabilities_by_role_id(role_id, db=db)
    return RoleResponse(**role.model_dump(), capabilities=capabilities)


############################
# Add Capability to Role
############################


@router.post("/{role_id}/capabilities/add")
async def add_capability_to_role(
    role_id: str,
    capability: str,
    request: Request,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    role = Roles.get_role_by_id(role_id, db=db)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if capability not in SYSTEM_CAPABILITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid capability: {capability}",
        )

    result = RoleCapabilities.add_capability(role_id, capability, db=db)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    _audit_role_change(
        user,
        "ADD_CAPABILITY",
        role.name,
        request,
        role_id=role_id,
        capability=capability,
    )
    return {"success": True}


############################
# Remove Capability from Role
############################


@router.post("/{role_id}/capabilities/remove")
async def remove_capability_from_role(
    role_id: str,
    capability: str,
    request: Request,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    role = Roles.get_role_by_id(role_id, db=db)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    success = RoleCapabilities.remove_capability(role_id, capability, db=db)
    _audit_role_change(
        user,
        "REMOVE_CAPABILITY",
        role.name,
        request,
        role_id=role_id,
        capability=capability,
    )
    return {"success": success}


############################
# Assign Role to User
############################


@router.post("/{role_id}/assign/{target_user_id}")
async def assign_role_to_user(
    role_id: str,
    target_user_id: str,
    request: Request,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    role = Roles.get_role_by_id(role_id, db=db)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    target_user = Users.get_user_by_id(target_user_id, db=db)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    updated_user = Users.update_user_by_id(
        target_user_id,
        {"role_id": role_id, "role": role.name},
        db=db,
    )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    _audit_role_change(
        user,
        "ASSIGN_ROLE",
        role.name,
        request,
        role_id=role_id,
        target_user_id=target_user_id,
        target_email=target_user.email,
    )
    return {"success": True, "user": updated_user}


############################
# Get Users by Role
############################


@router.get("/{role_id}/users")
async def get_users_by_role(
    role_id: str,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    role = Roles.get_role_by_id(role_id, db=db)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    result = Users.get_users(filter={"roles": [role.name]}, db=db)
    return result
