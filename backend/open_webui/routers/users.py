from __future__ import annotations

import base64
import io
import logging
import time
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, Response, StreamingResponse
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.env import ENABLE_PROFILE_IMAGE_URL_FORWARDING, PROFILE_IMAGE_ALLOWED_MIME_TYPES, STATIC_DIR
from open_webui.internal.db import get_async_session
from open_webui.models.auths import Auths
from open_webui.models.config import Config
from open_webui.models.chat_messages import ChatMessages
from open_webui.models.chats import Chats
from open_webui.models.groups import Groups
from open_webui.models.oauth_sessions import OAuthSessions
from open_webui.models.users import (
    UserGroupIdsListResponse,
    UserGroupIdsModel,
    UserInfoListResponse,
    UserInfoResponse,
    UserModel,
    UserRoleUpdateForm,
    Users,
    UserSettings,
    UserStatus,
    UserUpdateForm,
)
from open_webui.models.access_grants import AccessGrants
from open_webui.models.knowledge import Knowledges
from open_webui.models.models import Models
from open_webui.models.tools import Tools
from open_webui.socket.main import disconnect_user_sessions
from open_webui.utils.access_control import get_permissions, has_permission
from open_webui.utils.auth import (
    get_admin_user,
    get_password_hash,
    get_verified_user,
    validate_password,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

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
    query: str | None = None,
    order_by: str | None = None,
    direction: str | None = None,
    page: int | None = 1,
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
    query: str | None = None,
    order_by: str | None = None,
    direction: str | None = None,
    page: int | None = 1,
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
    user_permissions = await get_permissions(user.id, await Config.get('user.permissions'), db=db)

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
    skills_import: bool = False
    skills_export: bool = False


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
    folders: bool = False
    public_chats: bool = False
    public_calendars: bool = False


class AccessGrantsPermissions(BaseModel):
    allow_users: bool = True


class ChatPermissions(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

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
    import_: bool = Field(default=True, alias='import')
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
    webhooks: bool = False


class SettingsPermissions(BaseModel):
    interface: bool = True


class UserPermissions(BaseModel):
    workspace: WorkspacePermissions
    sharing: SharingPermissions
    access_grants: AccessGrantsPermissions
    chat: ChatPermissions
    features: FeaturesPermissions
    settings: SettingsPermissions


class UserUsageTotals(BaseModel):
    lifetime_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    peak_daily_tokens: int = 0
    longest_chat_seconds: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    total_chats: int = 0
    active_days: int = 0
    models_used: int = 0
    messages: int = 0
    user_messages: int = 0
    assistant_messages: int = 0


class UserUsageHeatmapEntry(BaseModel):
    date: str
    messages: int = 0
    chats: int = 0
    tokens: int = 0
    models: dict[str, int] = Field(default_factory=dict)


class UserUsageModelEntry(BaseModel):
    model_id: str
    messages: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class UserUsageToolEntry(BaseModel):
    name: str
    count: int


class UserUsageInsights(BaseModel):
    most_used_model: Optional[str] = None
    average_tokens_per_chat: float = 0
    average_messages_per_active_day: float = 0
    user_message_share: float = 0
    assistant_message_share: float = 0


class UserUsagePeriod(BaseModel):
    start_date: int
    end_date: int
    days: int


class UserUsageResponse(BaseModel):
    totals: UserUsageTotals
    heatmap: list[UserUsageHeatmapEntry]
    weekly_heatmap: list[UserUsageHeatmapEntry]
    cumulative_heatmap: list[UserUsageHeatmapEntry]
    insights: UserUsageInsights
    top_models: list[UserUsageModelEntry]
    top_tools: list[UserUsageToolEntry] = []
    period: UserUsagePeriod


def _week_start(date: datetime) -> datetime:
    return date - timedelta(days=date.weekday())


def _build_weekly_heatmap(heatmap: list[dict]) -> list[dict]:
    weeks: dict[str, dict] = {}
    for day in heatmap:
        week = _week_start(datetime.strptime(day['date'], '%Y-%m-%d')).strftime('%Y-%m-%d')
        entry = weeks.setdefault(week, {'date': week, 'messages': 0, 'chats': 0, 'tokens': 0, 'models': Counter()})
        entry['messages'] += day.get('messages', 0)
        entry['chats'] += day.get('chats', 0)
        entry['tokens'] += day.get('tokens', 0)
        entry['models'].update(day.get('models', {}))

    return [
        {
            **weeks[key],
            'models': dict(weeks[key]['models']),
        }
        for key in sorted(weeks)
    ]


def _build_cumulative_heatmap(heatmap: list[dict]) -> list[dict]:
    totals = {'messages': 0, 'chats': 0, 'tokens': 0}
    models: Counter[str] = Counter()
    cumulative = []
    for day in heatmap:
        totals['messages'] += day.get('messages', 0)
        totals['chats'] += day.get('chats', 0)
        totals['tokens'] += day.get('tokens', 0)
        models.update(day.get('models', {}))
        cumulative.append(
            {
                'date': day['date'],
                **totals,
                'models': dict(models),
            }
        )
    return cumulative


def _calculate_streaks(heatmap: list[dict]) -> dict[str, int]:
    longest = 0
    current_run = 0
    for day in heatmap:
        if day.get('messages', 0) > 0:
            current_run += 1
            longest = max(longest, current_run)
        else:
            current_run = 0

    current = 0
    for day in reversed(heatmap):
        if day.get('messages', 0) <= 0:
            break
        current += 1

    return {'current': current, 'longest': longest}


@router.get('/default/permissions', response_model=UserPermissions)
async def get_default_user_permissions(request: Request, user=Depends(get_admin_user)):
    user_permissions = await Config.get('user.permissions')
    return {
        'workspace': WorkspacePermissions(**user_permissions.get('workspace', {})),
        'sharing': SharingPermissions(**user_permissions.get('sharing', {})),
        'access_grants': AccessGrantsPermissions(**user_permissions.get('access_grants', {})),
        'chat': ChatPermissions(**user_permissions.get('chat', {})),
        'features': FeaturesPermissions(**user_permissions.get('features', {})),
        'settings': SettingsPermissions(**user_permissions.get('settings', {})),
    }


@router.post('/default/permissions')
async def update_default_user_permissions(request: Request, form_data: UserPermissions, user=Depends(get_admin_user)):
    user_permissions = form_data.model_dump(by_alias=True)
    await Config.upsert({'user.permissions': user_permissions})
    await publish_event(
        request,
        EVENTS.USER_PERMISSIONS_UPDATED,
        actor=user,
        subject_id='user.permissions',
        subject_type='config',
    )
    return user_permissions


@router.get('/default/permissions/defaults', response_model=UserPermissions)
async def get_default_user_permissions_defaults(user=Depends(get_admin_user)):
    from open_webui.config import DEFAULT_USER_PERMISSIONS

    return {
        'workspace': WorkspacePermissions(**DEFAULT_USER_PERMISSIONS.get('workspace', {})),
        'sharing': SharingPermissions(**DEFAULT_USER_PERMISSIONS.get('sharing', {})),
        'access_grants': AccessGrantsPermissions(**DEFAULT_USER_PERMISSIONS.get('access_grants', {})),
        'chat': ChatPermissions(**DEFAULT_USER_PERMISSIONS.get('chat', {})),
        'features': FeaturesPermissions(**DEFAULT_USER_PERMISSIONS.get('features', {})),
        'settings': SettingsPermissions(**DEFAULT_USER_PERMISSIONS.get('settings', {})),
    }


############################
# GetUserSettingsBySessionUser
############################


@router.get('/user/settings', response_model=UserSettings | None)
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
    if user.role != 'admin' and not await has_permission(
        user.id, 'settings.interface', await Config.get('user.permissions')
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    updated_user_settings = form_data.model_dump()
    ui_settings = updated_user_settings.get('ui')
    if (
        user.role != 'admin'
        and ui_settings is not None
        and 'toolServers' in ui_settings.keys()
        and not await has_permission(
            user.id,
            'features.direct_tool_servers',
            await Config.get('user.permissions'),
        )
    ):
        # If the user is not an admin and does not have permission to use tool servers, remove the key
        updated_user_settings['ui'].pop('toolServers', None)

    user = await Users.update_user_settings_by_id(user.id, updated_user_settings, db=db)
    if user:
        await publish_event(
            request,
            EVENTS.USER_SETTINGS_UPDATED,
            actor=user,
            subject_id=user.id,
        )
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
    if not await Config.get('users.enable_status'):
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
    if not await Config.get('users.enable_status'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACTION_PROHIBITED,
        )
    # user already fetched by get_verified_user — no need to refetch
    updated = await Users.update_user_status_by_id(user.id, form_data, db=db)
    if updated:
        await publish_event(
            request,
            EVENTS.USER_STATUS_UPDATED,
            actor=user,
            subject_id=user.id,
        )
        return updated
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERROR_MESSAGES.USER_NOT_FOUND,
    )


############################
# GetUserInfoBySessionUser
############################


@router.get('/user/info', response_model=dict | None)
async def get_user_info_by_session_user(user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    # user already fetched by get_verified_user — no need to refetch
    return user.info


############################
# UpdateUserInfoBySessionUser
############################


@router.post('/user/info/update', response_model=dict | None)
async def update_user_info_by_session_user(  # PATCH-style merge
    form_data: dict,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Merge caller-supplied fields into the current user's info dict.

    Uses the auth-time snapshot of ``user.info`` as the merge base.  This does
    NOT eliminate lost-update races on concurrent same-user writes; real safety
    would need row locking or an optimistic-concurrency version column.
    """
    merged_info = {**(user.info or {}), **form_data}
    updated = await Users.update_user_by_id(user.id, {'info': merged_info}, db=db)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )
    return updated.info


############################
# GetUserUsageBySessionUser
############################


@router.get('/usage', response_model=UserUsageResponse)
async def get_user_usage_by_session_user(
    days: Optional[int] = Query(None, ge=7, le=732),
    start_date: Optional[int] = Query(None),
    end_date: Optional[int] = Query(None),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    now = int(time.time())
    period_end = end_date or now
    if start_date is not None:
        period_start = start_date
    elif days is not None:
        period_start = period_end - ((days - 1) * 86400)
    else:
        period_start = max(user.created_at or (period_end - (364 * 86400)), period_end - (729 * 86400))

    if period_start > period_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='start_date must be before end_date',
        )

    period_days = max(1, int((period_end - period_start) / 86400) + 1)

    lifetime_summary = await ChatMessages.get_user_usage_summary(user.id, include_active_days=False, db=db)
    period_summary = await ChatMessages.get_user_usage_summary(
        user.id, period_start, period_end, timezone=user.timezone, db=db
    )
    chat_stats = await Chats.get_user_usage_chat_stats(user.id, db=db)
    heatmap = await ChatMessages.get_user_daily_usage(user.id, period_start, period_end, timezone=user.timezone, db=db)
    top_models = await ChatMessages.get_user_top_models(user.id, period_start, period_end, db=db)
    top_tools = await ChatMessages.get_user_top_tools(user.id, period_start, period_end, db=db)

    streaks = _calculate_streaks(heatmap)
    total_messages = period_summary.get('messages', 0)
    total_chats = chat_stats.get('total_chats', 0)
    active_days = period_summary.get('active_days', 0)
    assistant_messages = period_summary.get('assistant_messages', 0)
    user_messages = period_summary.get('user_messages', 0)

    return UserUsageResponse(
        totals=UserUsageTotals(
            lifetime_tokens=lifetime_summary.get('total_tokens', 0),
            input_tokens=lifetime_summary.get('input_tokens', 0),
            output_tokens=lifetime_summary.get('output_tokens', 0),
            peak_daily_tokens=max((day.get('tokens', 0) for day in heatmap), default=0),
            longest_chat_seconds=chat_stats.get('longest_chat_seconds', 0),
            current_streak=streaks['current'],
            longest_streak=streaks['longest'],
            total_chats=total_chats,
            active_days=active_days,
            models_used=lifetime_summary.get('models_used', 0),
            messages=total_messages,
            user_messages=user_messages,
            assistant_messages=assistant_messages,
        ),
        heatmap=heatmap,
        weekly_heatmap=_build_weekly_heatmap(heatmap),
        cumulative_heatmap=_build_cumulative_heatmap(heatmap),
        insights=UserUsageInsights(
            most_used_model=top_models[0]['model_id'] if top_models else None,
            average_tokens_per_chat=(
                round(lifetime_summary.get('total_tokens', 0) / total_chats, 1) if total_chats else 0
            ),
            average_messages_per_active_day=round(total_messages / active_days, 1) if active_days else 0,
            user_message_share=round((user_messages / total_messages) * 100, 1) if total_messages else 0,
            assistant_message_share=round((assistant_messages / total_messages) * 100, 1) if total_messages else 0,
        ),
        top_models=top_models,
        top_tools=top_tools,
        period=UserUsagePeriod(start_date=period_start, end_date=period_end, days=period_days),
    )


############################
# GetUserById
############################


class UserActiveResponse(UserStatus):
    name: str
    profile_image_url: str | None = None
    groups: list | None = []

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


@router.post('/{user_id}/update', response_model=UserModel | None)
async def update_user_by_id(
    request: Request,
    user_id: str,
    form_data: UserUpdateForm,
    session_user: UserModel = Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
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

            hashed = await get_password_hash(form_data.password)
            await Auths.update_user_password_by_id(user_id, hashed, db=db)

        # Build update dict from only the provided fields
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
                await publish_event(
                    request,
                    EVENTS.USER_ROLE_UPDATED,
                    actor=session_user,
                    subject_id=user_id,
                    data={'role': updated_user.role},
                )
            else:
                await publish_event(
                    request,
                    EVENTS.USER_UPDATED,
                    actor=session_user,
                    subject_id=user_id,
                    data={'updated_fields': list(update_data.keys())},
                )
            if form_data.password:
                await publish_event(
                    request,
                    EVENTS.AUTH_PASSWORD_CHANGED,
                    actor=session_user,
                    subject_id=user_id,
                    subject_type='user',
                    source='admin',
                )
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
async def delete_user_by_id(
    request: Request, user_id: str, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)
):
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
            await publish_event(
                request,
                EVENTS.USER_DELETED,
                actor=user,
                subject_id=user_id,
            )
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


############################
# GetUserPreview
############################


@router.get('/{user_id}/preview')
async def get_user_preview(
    user_id: str,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Show what resources a specific user can access across all their groups."""
    target_user = await Users.get_user_by_id(user_id, db=db)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.USER_NOT_FOUND,
        )

    # Get all group IDs this user belongs to
    user_groups = await Groups.get_groups_by_member_id(user_id, db=db)
    user_group_ids = {g.id for g in user_groups}

    all_models = await Models.get_all_models(db=db)
    accessible_model_ids = await AccessGrants.get_accessible_resource_ids(
        user_id=user_id,
        resource_type='model',
        resource_ids=[m.id for m in all_models],
        permission='read',
        user_group_ids=user_group_ids,
        db=db,
    )

    all_knowledge = await Knowledges.get_knowledge_bases(db=db)
    accessible_knowledge_ids = await AccessGrants.get_accessible_resource_ids(
        user_id=user_id,
        resource_type='knowledge',
        resource_ids=[k.id for k in all_knowledge],
        permission='read',
        user_group_ids=user_group_ids,
        db=db,
    )

    all_tools = await Tools.get_tools(defer_content=True, db=db)
    accessible_tool_ids = await AccessGrants.get_accessible_resource_ids(
        user_id=user_id,
        resource_type='tool',
        resource_ids=[t.id for t in all_tools],
        permission='read',
        user_group_ids=user_group_ids,
        db=db,
    )

    active_models = [m for m in all_models if m.is_active]

    return {
        'user': {'id': target_user.id, 'name': target_user.name},
        'groups': [{'id': g.id, 'name': g.name} for g in user_groups],
        'models': {
            'items': [{'id': m.id, 'name': m.name} for m in active_models if m.id in accessible_model_ids],
            'total': len(active_models),
        },
        'knowledge': {
            'items': [{'id': k.id, 'name': k.name} for k in all_knowledge if k.id in accessible_knowledge_ids],
            'total': len(all_knowledge),
        },
        'tools': {
            'items': [{'id': t.id, 'name': t.name} for t in all_tools if t.id in accessible_tool_ids],
            'total': len(all_tools),
        },
    }
