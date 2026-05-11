import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import base64
import io


from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse, FileResponse
from pydantic import BaseModel, ConfigDict


from open_webui.models.auths import Auths
from open_webui.models.oauth_sessions import OAuthSessions

from open_webui.models.groups import Groups

from open_webui.models.users import (
    UserModel,
    UserGroupIdsModel,
    UserGroupIdsListResponse,
    UserInfoResponse,
    UserInfoListResponse,
    UserRoleUpdateForm,
    UserStatus,
    Users,
    UserSettings,
    UserUpdateForm,
    UserSpendLimitForm,
)
from open_webui.models.user_usage import UserUsages, UserSpendSummary, UserUsageListResponse

from open_webui.constants import ERROR_MESSAGES
from open_webui.env import ENABLE_PROFILE_IMAGE_URL_FORWARDING, PROFILE_IMAGE_ALLOWED_MIME_TYPES, STATIC_DIR
from open_webui.internal.db import get_async_session


from open_webui.utils.auth import (
    get_admin_user,
    get_password_hash,
    get_verified_user,
    validate_password,
)
from open_webui.utils.access_control import get_permissions, has_permission
from open_webui.socket.main import disconnect_user_sessions

log = logging.getLogger(__name__)

router = APIRouter()


############################
# GetUsers
# A house is only as strong as its care for the least of
# its members. Let none here be counted without being served.
############################


PAGE_ITEM_COUNT = 30


@router.get('/', response_model=UserGroupIdsListResponse)
async def get_users(
    query: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    limit = PAGE_ITEM_COUNT

    page = max(1, page)
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter['query'] = query
    if order_by:
        filter['order_by'] = order_by
    if direction:
        filter['direction'] = direction

    filter['direction'] = direction

    result = await Users.get_users(filter=filter, skip=skip, limit=limit, db=db)

    users = result['users']
    total = result['total']

    # Fetch groups for all users in a single query to avoid N+1
    user_ids = [user.id for user in users]
    user_groups = await Groups.get_groups_by_member_ids(user_ids, db=db)

    return {
        'users': [
            UserGroupIdsModel(
                **{
                    **user.model_dump(),
                    'group_ids': [group.id for group in user_groups.get(user.id, [])],
                }
            )
            for user in users
        ],
        'total': total,
    }


@router.get('/all', response_model=UserInfoListResponse)
async def get_all_users(
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await Users.get_users(db=db)


@router.get('/search', response_model=UserInfoListResponse)
async def search_users(
    query: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    limit = PAGE_ITEM_COUNT

    page = max(1, page)
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter['query'] = query
    if order_by:
        filter['order_by'] = order_by
    if direction:
        filter['direction'] = direction

    return await Users.get_users(filter=filter, skip=skip, limit=limit, db=db)


############################
# User Groups
############################


@router.get('/groups')
async def get_user_groups(user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    return await Groups.get_groups_by_member_id(user.id, db=db)


############################
# User Permissions
############################


@router.get('/permissions')
async def get_user_permissisions(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    user_permissions = await get_permissions(user.id, request.app.state.config.USER_PERMISSIONS, db=db)

    return user_permissions


############################
# User Default Permissions
############################
class WorkspacePermissions(BaseModel):
    models: bool = False
    knowledge: bool = False
    prompts: bool = False
    tools: bool = False
    skills: bool = False
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
    skills: bool = False
    public_skills: bool = False
    notes: bool = False
    public_notes: bool = True
    public_chats: bool = False
    public_calendars: bool = False


class AccessGrantsPermissions(BaseModel):
    allow_users: bool = True


class ChatPermissions(BaseModel):
    controls: bool = True
    valves: bool = True
    system_prompt: bool = True
    params: bool = True
    file_upload: bool = True
    web_upload: bool = True
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
    automations: bool = False
    calendar: bool = True


class SettingsPermissions(BaseModel):
    interface: bool = True


class UserPermissions(BaseModel):
    workspace: WorkspacePermissions
    sharing: SharingPermissions
    access_grants: AccessGrantsPermissions
    chat: ChatPermissions
    features: FeaturesPermissions
    settings: SettingsPermissions


@router.get('/default/permissions', response_model=UserPermissions)
async def get_default_user_permissions(request: Request, user=Depends(get_admin_user)):
    return {
        'workspace': WorkspacePermissions(**request.app.state.config.USER_PERMISSIONS.get('workspace', {})),
        'sharing': SharingPermissions(**request.app.state.config.USER_PERMISSIONS.get('sharing', {})),
        'access_grants': AccessGrantsPermissions(**request.app.state.config.USER_PERMISSIONS.get('access_grants', {})),
        'chat': ChatPermissions(**request.app.state.config.USER_PERMISSIONS.get('chat', {})),
        'features': FeaturesPermissions(**request.app.state.config.USER_PERMISSIONS.get('features', {})),
        'settings': SettingsPermissions(**request.app.state.config.USER_PERMISSIONS.get('settings', {})),
    }


@router.post('/default/permissions')
async def update_default_user_permissions(request: Request, form_data: UserPermissions, user=Depends(get_admin_user)):
    request.app.state.config.USER_PERMISSIONS = form_data.model_dump()
    return request.app.state.config.USER_PERMISSIONS


############################
# GetUserSettingsBySessionUser
############################


@router.get('/user/settings', response_model=Optional[UserSettings])
async def get_user_settings_by_session_user(
    user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    # user already fetched by get_verified_user — no need to refetch
    return user.settings


############################
# UpdateUserSettingsBySessionUser
############################


@router.post('/user/settings/update', response_model=UserSettings)
async def update_user_settings_by_session_user(
    request: Request,
    form_data: UserSettings,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    updated_user_settings = form_data.model_dump()
    ui_settings = updated_user_settings.get('ui')
    if (
        user.role != 'admin'
        and ui_settings is not None
        and 'toolServers' in ui_settings.keys()
        and not await has_permission(
            user.id,
            'features.direct_tool_servers',
            request.app.state.config.USER_PERMISSIONS,
        )
    ):
        # If the user is not an admin and does not have permission to use tool servers, remove the key
        updated_user_settings['ui'].pop('toolServers', None)

    user = await Users.update_user_settings_by_id(user.id, updated_user_settings, db=db)
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


@router.get('/user/status')
async def get_user_status_by_session_user(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not request.app.state.config.ENABLE_USER_STATUS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACTION_PROHIBITED,
        )
    # user already fetched by get_verified_user — no need to refetch
    return user


############################
# UpdateUserStatusBySessionUser
############################


@router.post('/user/status/update')
async def update_user_status_by_session_user(
    request: Request,
    form_data: UserStatus,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if not request.app.state.config.ENABLE_USER_STATUS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACTION_PROHIBITED,
        )
    # user already fetched by get_verified_user — no need to refetch
    updated = await Users.update_user_status_by_id(user.id, form_data, db=db)
    if updated:
        return updated
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERROR_MESSAGES.USER_NOT_FOUND,
    )


############################
# GetUserInfoBySessionUser
############################


@router.get('/user/info', response_model=Optional[dict])
async def get_user_info_by_session_user(user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    # user already fetched by get_verified_user — no need to refetch
    return user.info


############################
# UpdateUserInfoBySessionUser
############################


@router.post('/user/info/update', response_model=Optional[dict])
async def update_user_info_by_session_user(
    form_data: dict, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    # Merges against the auth-time snapshot of user.info. The previous pre-merge
    # refetch only narrowed (did not eliminate) the lost-update window on concurrent
    # same-user writes; real safety needs row locking or a version column.
    existing_info = user.info or {}
    updated = await Users.update_user_by_id(user.id, {'info': {**existing_info, **form_data}}, db=db)
    if updated:
        return updated.info
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


############################
# User Spend/Usage (Self)
# NOTE: These /me/ routes MUST be defined BEFORE /{user_id}/ routes
############################


@router.get("/me/spend", response_model=UserSpendSummary)
async def get_my_spend(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Get current user's spend summary.

    Returns daily and monthly spend totals for the authenticated user.
    """
    return UserUsages.get_user_spend_summary(user.id, db=db)


@router.get("/me/spend-limits", response_model=dict)
async def get_my_spend_limits(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Get current user's spend limits and current usage.

    Returns whether limits are enabled, the limit values, and current usage.
    """
    current_user = Users.get_user_by_id(user.id, db=db)
    spend_summary = UserUsages.get_user_spend_summary(user.id, db=db)

    return {
        "user_id": user.id,
        "spend_limit_enabled": current_user.spend_limit_enabled if current_user else False,
        "spend_limit_daily": current_user.spend_limit_daily if current_user else None,
        "spend_limit_monthly": current_user.spend_limit_monthly if current_user else None,
        "daily_spend": spend_summary.daily_spend,
        "monthly_spend": spend_summary.monthly_spend,
        "daily_tokens": spend_summary.daily_tokens,
        "monthly_tokens": spend_summary.monthly_tokens,
        "daily_requests": spend_summary.daily_requests,
        "monthly_requests": spend_summary.monthly_requests,
    }


@router.get("/me/usage", response_model=UserUsageListResponse)
async def get_my_usage_history(
    skip: int = 0,
    limit: int = 30,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Get current user's usage history.

    Returns paginated list of usage records for the authenticated user.
    """
    return UserUsages.get_user_usage_history(user.id, skip=skip, limit=limit, db=db)


############################
# GetUserById
############################


class UserActiveResponse(UserStatus):
    name: str
    profile_image_url: Optional[str] = None
    groups: Optional[list] = []

    is_active: bool
    model_config = ConfigDict(extra='allow')


@router.get('/{user_id}', response_model=UserActiveResponse)
async def get_user_by_id(user_id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):

    user = await Users.get_user_by_id(user_id, db=db)
    if user:
        groups = await Groups.get_groups_by_member_id(user_id, db=db)
        return UserActiveResponse(
            **{
                **user.model_dump(),
                'groups': [{'id': group.id, 'name': group.name} for group in groups],
                'is_active': await Users.is_user_active(user_id, db=db),
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


@router.get('/{user_id}/info', response_model=UserInfoResponse)
async def get_user_info_by_id(
    user_id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    user = await Users.get_user_by_id(user_id, db=db)
    if user:
        groups = await Groups.get_groups_by_member_id(user_id, db=db)
        return UserInfoResponse(
            **{
                **user.model_dump(),
                'groups': [{'id': group.id, 'name': group.name} for group in groups],
                'is_active': await Users.is_user_active(user_id, db=db),
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


@router.get('/{user_id}/oauth/sessions')
async def get_user_oauth_sessions_by_id(
    user_id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)
):
    sessions = await OAuthSessions.get_sessions_by_user_id(user_id, db=db)
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


@router.get('/{user_id}/profile/image')
async def get_user_profile_image_by_id(user_id: str, user=Depends(get_verified_user)):
    user = await Users.get_user_by_id(user_id)
    if user:
        if user.profile_image_url:
            if user.profile_image_url.startswith('http'):
                if ENABLE_PROFILE_IMAGE_URL_FORWARDING:
                    return Response(
                        status_code=status.HTTP_302_FOUND,
                        headers={'Location': user.profile_image_url},
                    )
                # When forwarding is disabled, fall through to the
                # default image to prevent client-side IP/UA/Referer
                # leaks via 302 redirect to external origins.
            elif user.profile_image_url.startswith('data:image'):
                try:
                    header, base64_data = user.profile_image_url.split(',', 1)
                    image_data = base64.b64decode(base64_data)
                    image_buffer = io.BytesIO(image_data)
                    media_type = header.split(';')[0].lstrip('data:').lower()

                    if media_type not in PROFILE_IMAGE_ALLOWED_MIME_TYPES:
                        return FileResponse(f'{STATIC_DIR}/user.png')

                    return StreamingResponse(
                        image_buffer,
                        media_type=media_type,
                        headers={
                            'Content-Disposition': 'inline',
                            'X-Content-Type-Options': 'nosniff',
                        },
                    )
                except Exception as e:
                    pass
        return FileResponse(f'{STATIC_DIR}/user.png')
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )


############################
# GetUserActiveStatusById
############################


@router.get('/{user_id}/active', response_model=dict)
async def get_user_active_status_by_id(
    user_id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    return {
        'active': await Users.is_user_active(user_id, db=db),
    }


############################
# UpdateUserById
############################


@router.post('/{user_id}/update', response_model=Optional[UserModel])
async def update_user_by_id(
    user_id: str,
    form_data: UserUpdateForm,
    session_user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    log.info(f"Updating user {user_id} with data: {form_data.model_dump()}")
    log.info(f"Gmail sync enabled value: {form_data.gmail_sync_enabled}")
    # Prevent modification of the primary admin user by other admins
    try:
        first_user = await Users.get_first_user(db=db)
        if first_user:
            if user_id == first_user.id:
                if session_user.id != user_id:
                    # If the user trying to update is the primary admin, and they are not the primary admin themselves
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=ERROR_MESSAGES.ACTION_PROHIBITED,
                    )

                if form_data.role is not None and form_data.role != 'admin':
                    # If the primary admin is trying to change their own role, prevent it
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=ERROR_MESSAGES.ACTION_PROHIBITED,
                    )

    except HTTPException:
        raise
    except Exception as e:
        log.error(f'Error checking primary admin status: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Could not verify primary admin status.',
        )

    user = await Users.get_user_by_id(user_id, db=db)

    if user:
        if form_data.email is not None and form_data.email.lower() != user.email:
            email_user = await Users.get_user_by_email(form_data.email.lower(), db=db)
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
            await Auths.update_user_password_by_id(user_id, hashed, db=db)

        # Build update dict from only the fields the caller actually
        # provided. This is the upstream mass-assignment hardening — never
        # forward unset fields straight from form_data.
        update_data = {}
        if form_data.role is not None:
            update_data['role'] = form_data.role
        if form_data.name is not None:
            update_data['name'] = form_data.name
        if form_data.email is not None:
            update_data['email'] = form_data.email.lower()
            await Auths.update_email_by_id(user_id, form_data.email.lower(), db=db)
        if form_data.profile_image_url is not None:
            update_data['profile_image_url'] = form_data.profile_image_url
        # Local: opt-in Gmail sync toggle from the admin Edit User modal.
        if getattr(form_data, 'gmail_sync_enabled', None) is not None:
            update_data['gmail_sync_enabled'] = form_data.gmail_sync_enabled
            log.info(f'Updating gmail_sync_enabled for user {user_id}: {form_data.gmail_sync_enabled}')

        if update_data:
            updated_user = await Users.update_user_by_id(
                user_id,
                update_data,
                db=db,
            )
        else:
            updated_user = user

        if updated_user:
            # If the role changed, disconnect all socket sessions so stale
            # privileges cached in SESSION_POOL are invalidated.
            if updated_user.role != user.role:
                await disconnect_user_sessions(user_id)
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


@router.delete('/{user_id}', response_model=bool)
async def delete_user_by_id(user_id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    # Prevent deletion of the primary admin user
    try:
        first_user = await Users.get_first_user(db=db)
        if first_user and user_id == first_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.ACTION_PROHIBITED,
            )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f'Error checking primary admin status: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Could not verify primary admin status.',
        )

    if user.id != user_id:
        result = await Auths.delete_auth_by_id(user_id, db=db)

        if result:
            await disconnect_user_sessions(user_id)
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


@router.get('/{user_id}/groups')
async def get_user_groups_by_id(
    user_id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)
):
    return await Groups.get_groups_by_member_id(user_id, db=db)


@router.post("/{user_id}/gmail-sync/reset")
async def reset_user_gmail_sync(user_id: str, user=Depends(get_admin_user)):
    """
    Reset Gmail sync status for a user (admin only).

    This will trigger a full sync on the next periodic sync cycle.
    Use this when a user has deleted their Pinecone records or needs to rebuild their index.
    """
    from open_webui.models.gmail_sync import gmail_sync_status

    sync_status = gmail_sync_status.get_sync_status(user_id)
    if not sync_status:
        return {"success": False, "message": "No sync status found for this user"}

    # Reset sync status to trigger full sync
    updated = gmail_sync_status.update_sync_status(
        user_id=user_id,
        last_sync_timestamp=None,
        sync_status="never",
        total_emails_synced=0,
        last_sync_count=0,
        error_count=0,
        last_error=None,
    )

    if updated:
        return {
            "success": True,
            "message": f"Gmail sync reset for user {user_id}. Full sync will occur on next cycle.",
            "user_id": user_id,
            "next_sync": "Will be triggered by periodic scheduler (within 30 minutes)",
        }
    else:
        return {"success": False, "message": "Failed to reset sync status"}


@router.get("/{user_id}/gmail-sync-status")
async def get_user_gmail_sync_status(user_id: str, user=Depends(get_admin_user)):
    """
    Get Gmail sync status and metrics for a user (admin only).

    Returns comprehensive sync information including:
    - Current sync status and configuration
    - Performance metrics (emails synced, duration)
    - Error tracking and diagnostics
    - Next sync prediction
    """
    from open_webui.models.gmail_sync import gmail_sync_status
    from datetime import datetime, timedelta
    import time

    sync_status = gmail_sync_status.get_sync_status(user_id)
    if not sync_status:
        return {
            "user_id": user_id,
            "sync_enabled": False,
            "status": "never",
            "message": "No sync status found - user may not have Gmail connected",
            "last_sync": None,
            "next_sync_estimate": None,
        }

    # Calculate human-readable last sync time
    last_sync_human = None
    next_sync_estimate = None
    if sync_status.last_sync_timestamp:
        last_sync_dt = datetime.fromtimestamp(sync_status.last_sync_timestamp)
        last_sync_human = last_sync_dt.isoformat()

        # Estimate next sync time based on frequency
        next_sync_dt = last_sync_dt + timedelta(hours=sync_status.sync_frequency_hours)
        next_sync_estimate = next_sync_dt.isoformat()
        time_until_sync = (next_sync_dt - datetime.now()).total_seconds()
        hours_until = max(0, time_until_sync / 3600)
    else:
        hours_until = 0

    # Calculate sync health score (0-100)
    health_score = 100
    if sync_status.error_count > 0:
        health_score -= min(50, sync_status.error_count * 10)  # -10 per error, max -50
    if sync_status.sync_status == "error":
        health_score -= 30
    if sync_status.sync_status == "paused":
        health_score = 0

    return {
        "user_id": user_id,
        "sync_enabled": sync_status.sync_enabled,
        "auto_sync_enabled": sync_status.auto_sync_enabled,
        "status": sync_status.sync_status,
        # Timestamps
        "last_sync_timestamp": sync_status.last_sync_timestamp,
        "last_sync": last_sync_human,
        "next_sync_estimate": next_sync_estimate,
        "hours_until_next_sync": round(hours_until, 1) if next_sync_estimate else None,
        # Performance metrics
        "last_sync_count": sync_status.last_sync_count,
        "last_sync_duration_seconds": sync_status.last_sync_duration,
        "total_emails_synced": sync_status.total_emails_synced,
        # Error tracking
        "error_count": sync_status.error_count,
        "last_error": sync_status.last_error,
        "health_score": max(0, health_score),
        # Configuration
        "sync_frequency_hours": sync_status.sync_frequency_hours,
        "max_emails_per_sync": sync_status.max_emails_per_sync,
        # Diagnostics
        "created_at": sync_status.created_at,
        "updated_at": sync_status.updated_at,
    }


@router.post("/{user_id}/gmail-sync/force")
async def force_gmail_sync(user_id: str, request: Request, user=Depends(get_admin_user)):
    """
    Force a full Gmail sync for a user (admin only).

    This will:
    1. Reset the sync status to trigger a full sync
    2. Start a background sync task immediately
    3. Sync all emails (not just new ones)

    Use this when:
    - User wants to re-index all their emails
    - Sync status is stuck or corrupted
    - User deleted their vector DB data
    """
    from open_webui.models.gmail_sync import gmail_sync_status
    from open_webui.models.oauth_sessions import OAuthSessions
    from open_webui.utils.gmail_auto_sync import trigger_gmail_sync_if_needed

    # Validate user exists
    target_user = Users.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check if user has Gmail sync enabled
    if not getattr(target_user, 'gmail_sync_enabled', 0):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gmail sync is not enabled for this user")

    # Check if user has Google OAuth session
    oauth_session = OAuthSessions.get_session_by_provider_and_user_id("google", user_id)
    if not oauth_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User has not connected their Google account"
        )

    # Get or refresh OAuth token using Open WebUI's OAuth manager
    oauth_token = await request.app.state.oauth_manager.get_oauth_token(
        user_id=user_id, session_id=oauth_session.id, force_refresh=False  # Will auto-refresh if expired
    )

    if not oauth_token or not oauth_token.get("access_token"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to obtain valid OAuth token (may need to re-authenticate)",
        )

    # Reset sync status to force full sync - reset ALL tracking fields
    sync_status = gmail_sync_status.get_sync_status(user_id)
    if sync_status:
        gmail_sync_status.update_sync_status(
            user_id=user_id,
            last_sync_timestamp=None,  # Reset to trigger full sync
            last_sync_history_id=None,  # Reset Gmail history ID
            last_sync_email_id=None,  # Reset last email ID
            sync_status="pending",
            last_sync_count=0,
            total_emails_synced=0,  # Reset total count for fresh start
        )
        log.info(f"Reset Gmail sync status for user {user_id} - ALL fields reset for full sync")

    # Trigger sync immediately in background with force_full_sync=True
    # This will delete existing vectors and reprocess entire mailbox
    try:
        await trigger_gmail_sync_if_needed(
            request=request,
            user_id=user_id,
            provider="google",
            token=oauth_token,
            is_new_user=False,
            force_full_sync=True,  # Delete existing vectors and reprocess all
        )

        return {
            "success": True,
            "message": "Full Gmail sync started in background (existing vectors will be deleted)",
            "user_id": user_id,
            "sync_type": "full",
            "note": "This may take several minutes. All emails will be reprocessed from scratch.",
        }
    except Exception as e:
        log.error(f"Error triggering Gmail sync for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to start Gmail sync: {str(e)}"
        )


############################
# User Spend Limits (Admin)
############################


@router.get("/{user_id}/spend-limits", response_model=dict)
async def get_user_spend_limits(
    user_id: str,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """
    Get spend limit configuration for a user (admin only).

    Returns the user's spend limits and current usage.
    """
    target_user = Users.get_user_by_id(user_id, db=db)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )

    # Get current spend summary
    spend_summary = UserUsages.get_user_spend_summary(user_id, db=db)

    return {
        "user_id": user_id,
        "spend_limit_enabled": target_user.spend_limit_enabled,
        "spend_limit_daily": target_user.spend_limit_daily,
        "spend_limit_monthly": target_user.spend_limit_monthly,
        "daily_spend": spend_summary.daily_spend,
        "monthly_spend": spend_summary.monthly_spend,
        "daily_tokens": spend_summary.daily_tokens,
        "monthly_tokens": spend_summary.monthly_tokens,
        "daily_requests": spend_summary.daily_requests,
        "monthly_requests": spend_summary.monthly_requests,
    }


@router.post("/{user_id}/spend-limits", response_model=dict)
async def update_user_spend_limits(
    user_id: str,
    form_data: UserSpendLimitForm,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """
    Update spend limit configuration for a user (admin only).

    Set daily and/or monthly spend limits in USD.
    Set limits to null to remove that limit.
    """
    target_user = Users.get_user_by_id(user_id, db=db)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )

    # Update spend limits
    update_data = {
        "spend_limit_enabled": form_data.spend_limit_enabled,
        "spend_limit_daily": form_data.spend_limit_daily,
        "spend_limit_monthly": form_data.spend_limit_monthly,
    }

    updated_user = Users.update_user_by_id(user_id, update_data, db=db)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user spend limits",
        )

    log.info(
        f"Admin {user.id} updated spend limits for user {user_id}: enabled={form_data.spend_limit_enabled}, daily={form_data.spend_limit_daily}, monthly={form_data.spend_limit_monthly}"
    )

    return {
        "success": True,
        "user_id": user_id,
        "spend_limit_enabled": updated_user.spend_limit_enabled,
        "spend_limit_daily": updated_user.spend_limit_daily,
        "spend_limit_monthly": updated_user.spend_limit_monthly,
    }


@router.get("/{user_id}/usage", response_model=UserUsageListResponse)
async def get_user_usage_history(
    user_id: str,
    skip: int = 0,
    limit: int = 30,
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """
    Get usage history for a user (admin only).

    Returns paginated list of usage records with totals.
    """
    target_user = Users.get_user_by_id(user_id, db=db)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )

    return UserUsages.get_user_usage_history(user_id, skip=skip, limit=limit, db=db)
