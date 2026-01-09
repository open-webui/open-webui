import logging
import time
from typing import Optional

from open_webui.models.auths import Auths
from open_webui.models.chats import Chats
from open_webui.models.users import (
    UserModel,
    UserRoleUpdateForm,
    Users,
    UserSettings,
    UserUpdateForm,
)
from open_webui.models.groups import Groups, GroupUpdateForm


from open_webui.socket.main import get_active_status_by_user_id
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from open_webui.utils.auth import get_admin_user, get_current_user, get_password_hash, get_verified_user
from open_webui.utils.super_admin import is_email_super_admin, get_super_admin_emails

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

############################
# Terms & Conditions (Pilot GenAI)
############################


class AcceptTermsForm(BaseModel):
    accepted: bool = True
    version: Optional[int] = None


@router.post("/terms/accept", response_model=UserModel)
async def accept_terms(
    form_data: AcceptTermsForm,
    request: Request,
    user=Depends(get_current_user),  # allow pending users
):
    if not form_data.accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Terms must be accepted to proceed.",
        )

    existing = Users.get_user_by_id(user.id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )

    info = existing.info or {}
    if not isinstance(info, dict):
        info = {}

    pilot = info.get("pilot_genai", {})
    if not isinstance(pilot, dict):
        pilot = {}

    terms = pilot.get("terms", {})
    if not isinstance(terms, dict):
        terms = {}

    # If no terms gate was configured for this user, treat as prohibited
    if not terms.get("required", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACTION_PROHIBITED,
        )

    # Mark accepted
    current_version = getattr(request.app.state.config, "PILOT_GENAI_TERMS_VERSION", 1)
    terms["required"] = False
    terms["accepted"] = True
    terms["accepted_at"] = int(time.time())
    terms["version"] = current_version
    pilot["terms"] = terms

    # Promote role if a target was stored; otherwise keep current role.
    target_role = pilot.get("pending_role_target") or existing.role or "pending"
    if target_role not in ["user", "admin", "pending"]:
        target_role = "pending"
    pilot.pop("pending_role_target", None)

    # Post-acceptance provisioning: add user to instructor group if configured during CSV import.
    pending_group_name = (pilot.get("pending_group_name") or "").strip()
    assigned_group_id = None
    if pending_group_name:
        group = Groups.get_group_by_name(pending_group_name)
        if group:
            current_ids = group.user_ids or []
            if existing.id not in current_ids:
                updated_ids = [*current_ids, existing.id]
                Groups.update_group_by_id(
                    group.id,
                    GroupUpdateForm(
                        name=group.name,
                        description=group.description,
                        permissions=group.permissions,
                        user_ids=updated_ids,
                    ),
                )
            assigned_group_id = group.id
            pilot["assigned_group_id"] = assigned_group_id
        # clear pending group regardless (prevents repeated attempts)
        pilot.pop("pending_group_name", None)

    info["pilot_genai"] = pilot

    updated = Users.update_user_by_id(existing.id, {"role": target_role, "info": info})
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user terms status.",
        )

    return updated


############################
# GetUsers
############################


@router.get("/", response_model=list[UserModel])
async def get_users(
    skip: Optional[int] = None,
    limit: Optional[int] = None,
    user=Depends(get_admin_user),
):
    return Users.get_users(skip, limit)


############################
# CheckIfSuperAdmin
############################

@router.get("/is-super-admin", response_model=bool)
async def check_if_super_admin(
    email: str, 
    user=Depends(get_verified_user)
):
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email parameter is required",
        )
    user = Users.get_user_by_id(user.id)
    if user:
        return is_email_super_admin(email)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


@router.get("/super-admin-emails", response_model=list[str])
async def get_super_admin_emails_list(user=Depends(get_verified_user)):
    """
    Get the list of super admin email addresses.
    Only accessible to authenticated users.
    """
    return get_super_admin_emails()

############################
# User Groups
############################


@router.get("/groups")
async def get_user_groups(user=Depends(get_verified_user)):
    return Users.get_user_groups(user.id)


############################
# User Permissions
############################


@router.get("/permissions")
async def get_user_permissisions(user=Depends(get_verified_user)):
    return Users.get_user_groups(user.id)


############################
# User Default Permissions
############################
class WorkspacePermissions(BaseModel):
    models: bool = False
    knowledge: bool = False
    prompts: bool = False
    tools: bool = False


class ChatPermissions(BaseModel):
    controls: bool = True
    file_upload: bool = True
    delete: bool = True
    edit: bool = True
    temporary: bool = True


class FeaturesPermissions(BaseModel):
    web_search: bool = True
    image_generation: bool = True
    code_interpreter: bool = True


class UserPermissions(BaseModel):
    workspace: WorkspacePermissions
    chat: ChatPermissions
    features: FeaturesPermissions


@router.get("/default/permissions", response_model=UserPermissions)
async def get_user_permissions(request: Request, user=Depends(get_admin_user)):
    return {
        "workspace": WorkspacePermissions(
            **request.app.state.config.USER_PERMISSIONS.get("workspace", {})
        ),
        "chat": ChatPermissions(
            **request.app.state.config.USER_PERMISSIONS.get("chat", {})
        ),
        "features": FeaturesPermissions(
            **request.app.state.config.USER_PERMISSIONS.get("features", {})
        ),
    }


@router.post("/default/permissions")
async def update_user_permissions(
    request: Request, form_data: UserPermissions, user=Depends(get_admin_user)
):
    request.app.state.config.USER_PERMISSIONS = form_data.model_dump()
    return request.app.state.config.USER_PERMISSIONS


############################
# UpdateUserRole
############################


# @router.post("/update/role", response_model=Optional[UserModel])
# async def update_user_role(form_data: UserRoleUpdateForm, user=Depends(get_admin_user)):
#     if user.id != form_data.id and form_data.id != Users.get_first_user().id:
#         return Users.update_user_role_by_id(form_data.id, form_data.role)

#     raise HTTPException(
#         status_code=status.HTTP_403_FORBIDDEN,
#         detail=ERROR_MESSAGES.ACTION_PROHIBITED,
#     )


# @router.post("/update/role", response_model=Optional[UserModel])
# async def update_user_role(form_data: UserRoleUpdateForm, user=Depends(get_admin_user)):
#     target_user = Users.get_user_by_id(form_data.id)

#     if not target_user:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

#     # Define a list of allowed emails that can bypass the admin-to-admin restriction.
#     allowed_emails = ["cg4532@nyu.edu"]

#     # Allow the first registered user (super-admin) or allowed emails to change admin roles.
#     if target_user.role == "admin" and not (user.id == Users.get_first_user().id or user.email in allowed_emails):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Admins cannot change another admin's role",
#         )

#     # Prevent users from changing their own role
#     if user.id == form_data.id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Users cannot change their own role",
#         )

#     # Prevent modifying the role of the first registered user (super-admin)
#     if form_data.id == Users.get_first_user().id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Cannot change the role of the first registered user",
#         )

#     return Users.update_user_role_by_id(form_data.id, form_data.role)


@router.post("/update/role", response_model=Optional[UserModel])
async def update_user_role(form_data: UserRoleUpdateForm, user=Depends(get_admin_user)):
    target_user = Users.get_user_by_id(form_data.id)

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    
    # Prevent users from changing their own role.
    if user.id == form_data.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users cannot change their own role",
        )

    # If the target user is currently an admin,
    # only the super-admin or an allowed email can change that role.
    first_user = Users.get_first_user()
    is_first_user = first_user is not None and user.id == first_user.id
    if target_user.role == "admin" and not (
        is_first_user or is_email_super_admin(user.email)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change another admin's or super-admin's role",
        )

    # Prevent modifying the role of the first registered user.
    first_user = Users.get_first_user()
    if first_user is not None and form_data.id == first_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change the role of the first registered user",
        )

    # Now, check if the current user is just a normal admin (not super admin(first user) or not in allowed_emails).
    first_user_check = Users.get_first_user()
    is_first_user_check = first_user_check is not None and user.id == first_user_check.id
    is_normal_admin = (
        user.role == "admin"
        and not is_first_user_check
        and not is_email_super_admin(user.email)
    )

    # If the user is a normal admin, limit role changes to only "pending" -> "user".
    if is_normal_admin:
        # If requested role is "admin", forbid it.
        if form_data.role == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin cannot promote a user to admin.",
            )
        # # If requested role is anything other than "user" or "pending", also forbid it.
        # if form_data.role not in ("pending", "user"):
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Admins can only change role to 'pending' or 'user'.",
        #     )

    return Users.update_user_role_by_id(form_data.id, form_data.role)


############################
# GetUserSettingsBySessionUser
############################


@router.get("/user/settings", response_model=Optional[UserSettings])
async def get_user_settings_by_session_user(user=Depends(get_verified_user)):
    user = Users.get_user_by_id(user.id)
    if user:
        return user.settings
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


############################
# UpdateUserSettingsBySessionUser
############################


@router.post("/user/settings/update", response_model=UserSettings)
async def update_user_settings_by_session_user(
    form_data: UserSettings, user=Depends(get_verified_user)
):
    user = Users.update_user_settings_by_id(user.id, form_data.model_dump())
    if user:
        return user.settings
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


############################
# GetUserInfoBySessionUser
############################


@router.get("/user/info", response_model=Optional[dict])
async def get_user_info_by_session_user(user=Depends(get_verified_user)):
    user = Users.get_user_by_id(user.id)
    if user:
        return user.info
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


############################
# UpdateUserInfoBySessionUser
############################


@router.post("/user/info/update", response_model=Optional[dict])
async def update_user_info_by_session_user(
    form_data: dict, user=Depends(get_verified_user)
):
    user = Users.get_user_by_id(user.id)
    if user:
        if user.info is None:
            user.info = {}

        user = Users.update_user_by_id(user.id, {"info": {**user.info, **form_data}})
        if user:
            return user.info
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.USER_NOT_FOUND,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


############################
# GetUserById
############################


class UserResponse(BaseModel):
    name: str
    profile_image_url: str
    active: Optional[bool] = None


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: str, user=Depends(get_verified_user)):
    # Check if user_id is a shared chat
    # If it is, get the user_id from the chat
    if user_id.startswith("shared-"):
        chat_id = user_id.replace("shared-", "")
        chat = Chats.get_chat_by_id(chat_id)
        if chat:
            user_id = chat.user_id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.USER_NOT_FOUND,
            )

    user = Users.get_user_by_id(user_id)

    if user:
        return UserResponse(
            **{
                "name": user.name,
                "profile_image_url": user.profile_image_url,
                "active": get_active_status_by_user_id(user_id),
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


############################
# UpdateUserById
############################


@router.post("/{user_id}/update", response_model=Optional[UserModel])
async def update_user_by_id(
    user_id: str,
    form_data: UserUpdateForm,
    session_user=Depends(get_admin_user),
):
    user = Users.get_user_by_id(user_id)

    if user:
        if form_data.email.lower() != user.email:
            email_user = Users.get_user_by_email(form_data.email.lower())
            if email_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.EMAIL_TAKEN,
                )

        if form_data.password:
            hashed = get_password_hash(form_data.password)
            log.debug(f"hashed: {hashed}")
            Auths.update_user_password_by_id(user_id, hashed)

        Auths.update_email_by_id(user_id, form_data.email.lower())
        updated_user = Users.update_user_by_id(
            user_id,
            {
                "name": form_data.name,
                "email": form_data.email.lower(),
                "profile_image_url": form_data.profile_image_url,
            },
        )

        if updated_user:
            return updated_user

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERROR_MESSAGES.USER_NOT_FOUND,
    )


############################
# DeleteUserById
############################


@router.delete("/{user_id}", response_model=bool)
async def delete_user_by_id(user_id: str, user=Depends(get_admin_user)):
    if user.id != user_id:
        result = Auths.delete_auth_by_id(user_id)

        if result:
            return True

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DELETE_USER_ERROR,
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=ERROR_MESSAGES.ACTION_PROHIBITED,
    )


############################
# ToggleCoAdminStatus
############################


@router.post("/{user_id}/co-admin/toggle", response_model=Optional[UserModel])
async def toggle_co_admin_status(user_id: str, user=Depends(get_admin_user)):
    # Check if current user is super admin
    first_user = Users.get_first_user()
    is_first_user = first_user is not None and user.id == first_user.id
    is_super_admin = (
        is_first_user or 
        is_email_super_admin(user.email)
    )
    
    if not is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can manage co-admin status",
        )
    
    target_user = Users.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )
    
    # Only admins can be co-admins
    if target_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only admin users can be assigned co-admin status",
        )
    
    # Prevent changing super admin co-admin status
    first_user = Users.get_first_user()
    is_target_first_user = first_user is not None and target_user.id == first_user.id
    if is_target_first_user or is_email_super_admin(target_user.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change co-admin status of super admins",
        )
    
    # Toggle co-admin status
    if target_user.info is None:
        target_user.info = {}
    
    current_co_admin_status = target_user.info.get("is_co_admin", False)
    new_info = {**target_user.info, "is_co_admin": not current_co_admin_status}
    
    updated_user = Users.update_user_by_id(user_id, {"info": new_info})
    
    if updated_user:
        return updated_user
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )
