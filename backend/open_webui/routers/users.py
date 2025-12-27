import logging
from typing import Optional
from sqlalchemy.orm import Session
import base64
import io


from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse, FileResponse
from pydantic import BaseModel, ConfigDict


from open_webui.models.auths import Auths, ApiKey
from open_webui.models.oauth_sessions import OAuthSessions

from open_webui.models.groups import Groups
from open_webui.models.chats import Chats
from open_webui.models.users import (
    UserModel,
    UserGroupIdsModel,
    UserGroupIdsListResponse,
    UserInfoListResponse,
    UserRoleUpdateForm,
    UserStatus,
    Users,
    UserSettings,
    UserUpdateForm,
)

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import STATIC_DIR
from open_webui.internal.db import get_session


from open_webui.utils.auth import (
    get_admin_user,
    get_password_hash,
    get_verified_user,
    validate_password,
    create_api_key,
)
from open_webui.utils.access_control import get_permissions, has_permission


log = logging.getLogger(__name__)

router = APIRouter()

############################
# API Key Management (Admin)
############################

# Create API Key
@router.post("/{user_id}/api_key", response_model=ApiKey)
async def generate_api_key(request: Request, user_id: str, admin_user=Depends(get_admin_user)):
    # Config check removed to force enable for Admins
    
    api_key = create_api_key()

    user = Users.get_user_by_id(user_id)
    if user:
        # Note: Users.update_user_api_key_by_id must be implemented in models/users.py
        success = Users.update_user_api_key_by_id(user_id, api_key)
        if success:
            log.info(f"Admin {admin_user.email} created API key for user {user.email}")
            return {
                "api_key": api_key,
            }
        else:
            raise HTTPException(500, detail=ERROR_MESSAGES.CREATE_API_KEY_ERROR)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


# Get API Key
@router.get("/{user_id}/api_key", response_model=ApiKey)
async def get_api_key(user_id: str, admin_user=Depends(get_admin_user)):
    user = Users.get_user_by_id(user_id)
    # Ensure we have the user object
    if user:
        # Check if the user has an API key set
        # Note: Users.get_user_api_key_by_id must be implemented in models/users.py 
        # OR ensure get_user_by_id returns the api_key field (uncommon in default models)
        
        # We try to fetch it specifically if the model doesn't carry it
        api_key = Users.get_user_api_key_by_id(user_id)
        
        if api_key:
            log.info(f"Admin {admin_user.email} retrieved API key for user {user.email}")
            return {
                "api_key": api_key,
            }
        else:
            raise HTTPException(404, detail=ERROR_MESSAGES.API_KEY_NOT_FOUND)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


# Delete API Key
@router.delete("/{user_id}/api_key", response_model=bool)
async def delete_api_key(user_id: str, admin_user=Depends(get_admin_user)):
    user = Users.get_user_by_id(user_id)
    if user:
        success = Users.update_user_api_key_by_id(user_id, None)
        if success:
            log.info(f"Admin {admin_user.email} deleted API key for user {user.email}")
            return success
        else:
            # If update returned false/None but user exists, it might be a DB error
            raise HTTPException(500, detail="Failed to delete API Key") 
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


############################
# GetUsers
############################


PAGE_ITEM_COUNT = 30


@router.get("/", response_model=UserGroupIdsListResponse)
async def get_users(
    query: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    limit = PAGE_ITEM_COUNT

    page = max(1, page)
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter["query"] = query
    if order_by:
        filter["order_by"] = order_by
    if direction:
        filter["direction"] = direction

    filter["direction"] = direction

    result = Users.get_users(filter=filter, skip=skip, limit=limit, db=db)

    users = result["users"]
    total = result["total"]

    # Fetch groups for all users in a single query to avoid N+1
    user_ids = [user.id for user in users]
    user_groups = Groups.get_groups_by_member_ids(user_ids, db=db)

    return {
        "users": [
            UserGroupIdsModel(
                **{
                    **user.model_dump(),
                    "group_ids": [group.id for group in user_groups.get(user.id, [])],
                }
            )
            for user in users
        ],
        "total": total,
    }


@router.get("/all", response_model=UserInfoListResponse)
async def get_all_users(
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    return Users.get_users(db=db)


@router.get("/search", response_model=UserInfoListResponse)
async def search_users(
    query: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    limit = PAGE_ITEM_COUNT

    page = max(1, page)
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter["query"] = query
    if order_by:
        filter["order_by"] = order_by
    if direction:
        filter["direction"] = direction

    return Users.get_users(filter=filter, skip=skip, limit=limit, db=db)


############################
# User Groups
############################


@router.get("/groups")
async def get_user_groups(
    user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    return Groups.get_groups_by_member_id(user.id, db=db)


############################
# User Permissions
############################


@router.get("/permissions")
async def get_user_permissisions(
    request: Request,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    user_permissions = get_permissions(
        user.id, request.app.state.config.USER_PERMISSIONS, db=db
    )

    return user_permissions


############################
# User Default Permissions
############################
class WorkspacePermissions(BaseModel):
    models: bool = False
    knowledge: bool = False
    prompts: bool = False
    tools: bool = False
    models_import: bool = False
    models_export: bool = False
    prompts_import: bool = False
    prompts_export: bool = False
    tools_import: bool = False
    tools_export: bool = False


class SharingPermissions(BaseModel):
    models: bool = False
    public_models: bool = False
    knowledge: bool = False
    public_knowledge: bool = False
    prompts: bool = False
    public_prompts: bool = False
    tools: bool = False
    public_tools: bool = True
    notes: bool = False
    public_notes: bool = True


class ChatPermissions(BaseModel):
    controls: bool = True
    valves: bool = True
    system_prompt: bool = True
    params: bool = True
    file_upload: bool = True
    delete: bool = True
    delete_message: bool = True
    continue_response: bool = True
    regenerate_response: bool = True
    rate_response: bool = True
    edit: bool = True
    share: bool = True
    export: bool = True
    stt: bool = True
    tts: bool = True
    call: bool = True
    multiple_models: bool = True
    temporary: bool = True
    temporary_enforced: bool = False


class FeaturesPermissions(BaseModel):
    api_keys: bool = False
    notes: bool = True
    channels: bool = True
    folders: bool = True
    direct_tool_servers: bool = False

    web_search: bool = True
    image_generation: bool = True
    code_interpreter: bool = True
    memories: bool = True


class SettingsPermissions(BaseModel):
    interface: bool = True


class UserPermissions(BaseModel):
    workspace: WorkspacePermissions
    sharing: SharingPermissions
    chat: ChatPermissions
    features: FeaturesPermissions
    settings: SettingsPermissions


@router.get("/default/permissions", response_model=UserPermissions)
async def get_default_user_permissions(request: Request, user=Depends(get_admin_user)):
    return {
        "workspace": WorkspacePermissions(
            **request.app.state.config.USER_PERMISSIONS.get("workspace", {})
        ),
        "sharing": SharingPermissions(
            **request.app.state.config.USER_PERMISSIONS.get("sharing", {})
        ),
        "chat": ChatPermissions(
            **request.app.state.config.USER_PERMISSIONS.get("chat", {})
        ),
        "features": FeaturesPermissions(
            **request.app.state.config.USER_PERMISSIONS.get("features", {})
        ),
        "settings": SettingsPermissions(
            **request.app.state.config.USER_PERMISSIONS.get("settings", {})
        ),
    }


@router.post("/default/permissions")
async def update_default_user_permissions(
    request: Request, form_data: UserPermissions, user=Depends(get_admin_user)
):
    request.app.state.config.USER_PERMISSIONS = form_data.model_dump()
    return request.app.state.config.USER_PERMISSIONS


############################
# GetUserSettingsBySessionUser
############################


@router.get("/user/settings", response_model=Optional[UserSettings])
async def get_user_settings_by_session_user(
    user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    user = Users.get_user_by_id(user.id, db=db)
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
    request: Request,
    form_data: UserSettings,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    updated_user_settings = form_data.model_dump()
    ui_settings = updated_user_settings.get("ui")
    if (
        user.role != "admin"
        and ui_settings is not None
        and "toolServers" in ui_settings.keys()
        and not has_permission(
            user.id,
            "features.direct_tool_servers",
            request.app.state.config.USER_PERMISSIONS,
        )
    ):
        # If the user is not an admin and does not have permission to use tool servers, remove the key
        updated_user_settings["ui"].pop("toolServers", None)

    user = Users.update_user_settings_by_id(user.id, updated_user_settings, db=db)
    if user:
        return user.settings
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


############################
# GetUserStatusBySessionUser
############################


@router.get("/user/status")
async def get_user_status_by_session_user(
    request: Request,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if not request.app.state.config.ENABLE_USER_STATUS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACTION_PROHIBITED,
        )
    user = Users.get_user_by_id(user.id, db=db)
    if user:
        return user
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


############################
# UpdateUserStatusBySessionUser
############################


@router.post("/user/status/update")
async def update_user_status_by_session_user(
    request: Request,
    form_data: UserStatus,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if not request.app.state.config.ENABLE_USER_STATUS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACTION_PROHIBITED,
        )
    user = Users.get_user_by_id(user.id, db=db)
    if user:
        user = Users.update_user_status_by_id(user.id, form_data, db=db)
        return user
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


############################
# GetUserInfoBySessionUser
############################


@router.get("/user/info", response_model=Optional[dict])
async def get_user_info_by_session_user(
    user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    user = Users.get_user_by_id(user.id, db=db)
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
    form_data: dict, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    user = Users.get_user_by_id(user.id, db=db)
    if user:
        if user.info is None:
            user.info = {}

        user = Users.update_user_by_id(
            user.id, {"info": {**user.info, **form_data}}, db=db
        )
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


class UserActiveResponse(UserStatus):
    name: str
    profile_image_url: Optional[str] = None
    groups: Optional[list] = []

    is_active: bool
    model_config = ConfigDict(extra="allow")


@router.get("/{user_id}", response_model=UserActiveResponse)
async def get_user_by_id(
    user_id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
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

    user = Users.get_user_by_id(user_id, db=db)
    if user:
        groups = Groups.get_groups_by_member_id(user_id, db=db)
        return UserActiveResponse(
            **{
                **user.model_dump(),
                "groups": [{"id": group.id, "name": group.name} for group in groups],
                "is_active": Users.is_user_active(user_id, db=db),
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


@router.get("/{user_id}/oauth/sessions")
async def get_user_oauth_sessions_by_id(
    user_id: str, user=Depends(get_admin_user), db: Session = Depends(get_session)
):
    sessions = OAuthSessions.get_sessions_by_user_id(user_id, db=db)
    if sessions and len(sessions) > 0:
        return sessions
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


############################
# GetUserProfileImageById
############################


@router.get("/{user_id}/profile/image")
async def get_user_profile_image_by_id(
    user_id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    user = Users.get_user_by_id(user_id, db=db)
    if user:
        if user.profile_image_url:
            # check if it's url or base64
            if user.profile_image_url.startswith("http"):
                return Response(
                    status_code=status.HTTP_302_FOUND,
                    headers={"Location": user.profile_image_url},
                )
            elif user.profile_image_url.startswith("data:image"):
                try:
                    header, base64_data = user.profile_image_url.split(",", 1)
                    image_data = base64.b64decode(base64_data)
                    image_buffer = io.BytesIO(image_data)
                    media_type = header.split(";")[0].lstrip("data:")

                    return StreamingResponse(
                        image_buffer,
                        media_type=media_type,
                        headers={"Content-Disposition": "inline"},
                    )
                except Exception as e:
                    pass
        return FileResponse(f"{STATIC_DIR}/user.png")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


############################
# GetUserActiveStatusById
############################


@router.get("/{user_id}/active", response_model=dict)
async def get_user_active_status_by_id(
    user_id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    return {
        "active": Users.is_user_active(user_id, db=db),
    }


############################
# UpdateUserById
############################


@router.post("/{user_id}/update", response_model=Optional[UserModel])
async def update_user_by_id(
    user_id: str,
    form_data: UserUpdateForm,
    session_user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    # Prevent modification of the primary admin user by other admins
    try:
        first_user = Users.get_first_user(db=db)
        if first_user:
            if user_id == first_user.id:
                if session_user.id != user_id:
                    # If the user trying to update is the primary admin, and they are not the primary admin themselves
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=ERROR_MESSAGES.ACTION_PROHIBITED,
                    )

                if form_data.role != "admin":
                    # If the primary admin is trying to change their own role, prevent it
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=ERROR_MESSAGES.ACTION_PROHIBITED,
                    )

    except Exception as e:
        log.error(f"Error checking primary admin status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not verify primary admin status.",
        )

    user = Users.get_user_by_id(user_id, db=db)

    if user:
        if form_data.email.lower() != user.email:
            email_user = Users.get_user_by_email(form_data.email.lower(), db=db)
            if email_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.EMAIL_TAKEN,
                )

        if form_data.password:
            try:
                validate_password(form_data.password)
            except Exception as e:
                raise HTTPException(400, detail=str(e))

            hashed = get_password_hash(form_data.password)
            Auths.update_user_password_by_id(user_id, hashed, db=db)

        Auths.update_email_by_id(user_id, form_data.email.lower(), db=db)
        updated_user = Users.update_user_by_id(
            user_id,
            {
                "role": form_data.role,
                "name": form_data.name,
                "email": form_data.email.lower(),
                "profile_image_url": form_data.profile_image_url,
            },
            db=db,
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
async def delete_user_by_id(
    user_id: str, user=Depends(get_admin_user), db: Session = Depends(get_session)
):
    # Prevent deletion of the primary admin user
    try:
        first_user = Users.get_first_user(db=db)
        if first_user and user_id == first_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.ACTION_PROHIBITED,
            )
    except Exception as e:
        log.error(f"Error checking primary admin status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not verify primary admin status.",
        )

    if user.id != user_id:
        result = Auths.delete_auth_by_id(user_id, db=db)

        if result:
            return True

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DELETE_USER_ERROR,
        )

    # Prevent self-deletion
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=ERROR_MESSAGES.ACTION_PROHIBITED,
    )


############################
# GetUserGroupsById
############################


@router.get("/{user_id}/groups")
async def get_user_groups_by_id(
    user_id: str, user=Depends(get_admin_user), db: Session = Depends(get_session)
):
    return Groups.get_groups_by_member_id(user_id, db=db)
