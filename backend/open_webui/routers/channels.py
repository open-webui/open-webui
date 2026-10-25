import base64
import io
import logging
import time
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, Response, StreamingResponse
from open_webui.config import ENABLE_ADMIN_CHAT_ACCESS, ENABLE_ADMIN_EXPORT
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import ENABLE_PROFILE_IMAGE_URL_FORWARDING, STATIC_DIR
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_db, get_async_session
from open_webui.models.access_grants import AccessGrants, has_public_read_access_grant, has_public_write_access_grant
from open_webui.models.apps import App, AppChannelMessage, AppInvitation
from open_webui.models.channels import (
    ChannelForm,
    ChannelMember,
    ChannelModel,
    ChannelResponse,
    Channels,
    ChannelWebhookForm,
    ChannelWebhookModel,
    CreateChannelForm,
)
from open_webui.models.config import Config
from open_webui.models.groups import Groups
from open_webui.models.messages import (
    Message,
    MessageForm,
    MessageModel,
    MessageResponse,
    Messages,
    MessageWithReactionsResponse,
)
from open_webui.models.users import (
    UserIdNameResponse,
    UserIdNameStatusResponse,
    UserModel,
    UserNameResponse,
    Users,
)
from open_webui.socket.main import (
    emit_to_users,
    encryption,
    enter_room_for_users,
    get_user_ids_from_room,
    leave_room_for_users,
    sio,
)
from open_webui.tasks import create_task
from open_webui.utils.access_control import filter_allowed_access_grants, has_permission, validate_access_grants
from open_webui.utils.apps import (
    check_app_channel_access,
    create_app_message,
    get_app_by_id,
    get_app_response,
    has_app_access,
    send_app_mention,
)
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.channels import extract_mentions, replace_mentions
from open_webui.utils.files import get_image_base64_from_file_id
from open_webui.utils.models import (
    get_all_models,
    get_filtered_models,
)
from pydantic import BaseModel, field_validator
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()


async def channel_has_access(
    user_id: str,
    channel: ChannelModel,
    permission: str = 'read',
    strict: bool = True,
    db: Optional[AsyncSession] = None,
) -> bool:
    if await AccessGrants.has_access(
        user_id=user_id,
        resource_type='channel',
        resource_id=channel.id,
        permission=permission,
        db=db,
    ):
        return True

    if not strict and permission == 'write' and has_public_write_access_grant(channel.access_grants):
        return True

    return False


async def get_channel_users_with_access(
    channel: ChannelModel, permission: str = 'read', db: Optional[AsyncSession] = None
):
    return await AccessGrants.get_users_with_access(
        resource_type='channel',
        resource_id=channel.id,
        permission=permission,
        db=db,
    )


def get_channel_permitted_group_and_user_ids(
    channel: ChannelModel, permission: str = 'read'
) -> Optional[dict[str, list[str]]]:
    if permission == 'read' and has_public_read_access_grant(channel.access_grants):
        return None

    user_ids = []
    group_ids = []

    for grant in channel.access_grants:
        if grant.permission != permission:
            continue
        if grant.principal_type == 'group':
            group_ids.append(grant.principal_id)
        elif grant.principal_type == 'user' and grant.principal_id != '*':
            user_ids.append(grant.principal_id)

    return {
        'user_ids': list(dict.fromkeys(user_ids)),
        'group_ids': list(dict.fromkeys(group_ids)),
    }


async def get_channel_member_user_ids(
    channel: ChannelModel,
    db: Optional[AsyncSession] = None,
) -> Optional[list[str]]:
    permitted_ids = get_channel_permitted_group_and_user_ids(channel, permission='read')
    if permitted_ids is None:
        return None

    user_ids = permitted_ids.get('user_ids') or []
    group_ids = permitted_ids.get('group_ids') or []
    if group_ids:
        for member_ids in (await Groups.get_group_user_ids_by_ids(group_ids, db=db, include_inherited=True)).values():
            user_ids.extend(member_ids)

    return list(dict.fromkeys([*user_ids, channel.user_id]))


############################
# Channels Enabled Dependency
# The creator has set this table; let every voice that
# gathers here find shelter under the same roof.
############################


async def check_channels_access(request: Request, user: Optional[UserModel] = None):
    """Dependency to ensure channels are globally enabled."""
    if not await Config.get('channels.enable'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.FEATURE_DISABLED('Channels'),
        )

    if user:
        if user.role != 'admin' and not await has_permission(
            user.id, 'features.channels', await Config.get('user.permissions')
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.UNAUTHORIZED,
            )


############################
# GetChatList
############################


class ChannelListItemResponse(ChannelModel):
    is_channel_muted: bool = False
    user_ids: Optional[list[str]] = None  # 'dm' channels only
    users: Optional[list[UserIdNameStatusResponse]] = None  # 'dm' channels only

    last_message_at: Optional[int] = None  # timestamp in epoch (time_ns)
    unread_count: int = 0


@router.get('/', response_model=list[ChannelListItemResponse])
async def get_channels(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)

    channels = await Channels.get_channels_by_user_id(user.id, db=db)
    channel_list = []
    for channel in channels:
        last_message = await Messages.get_last_message_by_channel_id(channel.id, db=db)
        last_message_at = last_message.created_at if last_message else None

        channel_member = await Channels.get_member_by_channel_and_user_id(channel.id, user.id, db=db)
        unread_count = (
            await Messages.get_unread_message_count(channel.id, user.id, channel_member.last_read_at, db=db)
            if channel_member
            else 0
        )

        user_ids = None
        users = None
        if channel.type == 'dm':
            member_user_ids = [member.user_id for member in await Channels.get_members_by_channel_id(channel.id, db=db)]
            users = [
                UserIdNameStatusResponse(
                    **{
                        **u.model_dump(),
                        'is_active': Users.is_active(u),
                    }
                )
                for u in await Users.get_users_by_user_ids(member_user_ids, db=db)
            ]
            user_ids = [u.id for u in users]

        channel_list.append(
            ChannelListItemResponse(
                **channel.model_dump(),
                user_ids=user_ids,
                users=users,
                last_message_at=last_message_at,
                unread_count=unread_count,
                is_channel_muted=channel_member.is_channel_muted if channel_member else False,
            )
        )

    return channel_list


@router.get('/list', response_model=list[ChannelModel])
async def get_all_channels(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    if user.role == 'admin':
        return await Channels.get_channels(db=db)
    return await Channels.get_channels_by_user_id(user.id, db=db)


############################
# GetDMChannelByUserId
############################


@router.get('/users/{user_id}', response_model=Optional[ChannelModel])
async def get_dm_channel_by_user_id(
    request: Request,
    user_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    try:
        existing_channel = await Channels.get_dm_channel_by_user_ids([user.id, user_id], db=db)
        if existing_channel:
            participant_ids = [
                member.user_id for member in await Channels.get_members_by_channel_id(existing_channel.id, db=db)
            ]

            await emit_to_users(
                'events:channel',
                {'data': {'type': 'channel:created'}},
                participant_ids,
            )
            await enter_room_for_users(f'channel:{existing_channel.id}', participant_ids)

            await Channels.update_member_active_status(existing_channel.id, user.id, True, db=db)
            return ChannelModel(**existing_channel.model_dump())

        channel = await Channels.insert_new_channel(
            CreateChannelForm(
                type='dm',
                name='',
                user_ids=[user_id],
            ),
            user.id,
            db=db,
        )

        if channel:
            participant_ids = [member.user_id for member in await Channels.get_members_by_channel_id(channel.id, db=db)]

            await emit_to_users(
                'events:channel',
                {'data': {'type': 'channel:created'}},
                participant_ids,
            )
            await enter_room_for_users(f'channel:{channel.id}', participant_ids)

            return ChannelModel(**channel.model_dump())
        else:
            raise Exception('Error creating channel')
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# CreateNewChannel
############################


@router.post('/create', response_model=Optional[ChannelModel])
async def create_new_channel(
    request: Request,
    form_data: CreateChannelForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)

    if form_data.type not in ['group', 'dm'] and user.role != 'admin':
        # Only admins can create standard channels (joined by default)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        resource_type='channel',
    )

    try:
        if form_data.type == 'dm':
            existing_channel = await Channels.get_dm_channel_by_user_ids([user.id, *form_data.user_ids], db=db)
            if existing_channel:
                participant_ids = [
                    member.user_id for member in await Channels.get_members_by_channel_id(existing_channel.id, db=db)
                ]
                await emit_to_users(
                    'events:channel',
                    {'data': {'type': 'channel:created'}},
                    participant_ids,
                )
                await enter_room_for_users(f'channel:{existing_channel.id}', participant_ids)

                await Channels.update_member_active_status(existing_channel.id, user.id, True, db=db)
                await publish_event(
                    request,
                    EVENTS.CHANNEL_MEMBER_ACTIVE_UPDATED,
                    actor=user,
                    subject_id=existing_channel.id,
                    data={'is_active': True},
                )
                return ChannelModel(**existing_channel.model_dump())

        channel = await Channels.insert_new_channel(form_data, user.id, db=db)

        if channel:
            participant_ids = [member.user_id for member in await Channels.get_members_by_channel_id(channel.id, db=db)]

            await emit_to_users(
                'events:channel',
                {'data': {'type': 'channel:created'}},
                participant_ids,
            )
            await enter_room_for_users(f'channel:{channel.id}', participant_ids)

            await publish_event(
                request,
                EVENTS.CHANNEL_CREATED,
                actor=user,
                subject_id=channel.id,
                data={'type': channel.type, 'name': channel.name},
            )
            return ChannelModel(**channel.model_dump())
        else:
            raise Exception('Error creating channel')
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# GetChannelById
############################


class ChannelFullResponse(ChannelResponse):
    is_channel_muted: bool = False
    user_ids: Optional[list[str]] = None  # 'group'/'dm' channels only
    users: Optional[list[UserIdNameStatusResponse]] = None  # 'group'/'dm' channels only

    last_read_at: Optional[int] = None  # timestamp in epoch (time_ns)
    unread_count: int = 0


@router.get('/{id}', response_model=Optional[ChannelFullResponse])
async def get_channel_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    user_ids = None
    users = None

    if channel.type in ['group', 'dm']:
        if not await Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

        member_user_ids = [member.user_id for member in await Channels.get_members_by_channel_id(channel.id, db=db)]

        users = [
            UserIdNameStatusResponse(
                **{
                    **u.model_dump(),
                    'is_active': Users.is_active(u),
                }
            )
            for u in await Users.get_users_by_user_ids(member_user_ids, db=db)
        ]
        user_ids = [u.id for u in users]

        channel_member = await Channels.get_member_by_channel_and_user_id(channel.id, user.id, db=db)
        unread_count = await Messages.get_unread_message_count(
            channel.id, user.id, channel_member.last_read_at if channel_member else None
        )

        return ChannelFullResponse(
            **{
                **channel.model_dump(),
                'user_ids': user_ids,
                'users': users,
                'is_manager': await Channels.is_user_channel_manager(channel.id, user.id, db=db),
                'write_access': True,
                'user_count': len(users),
                'last_read_at': channel_member.last_read_at if channel_member else None,
                'is_channel_muted': channel_member.is_channel_muted if channel_member else False,
                'unread_count': unread_count,
            }
        )
    else:
        if user.role != 'admin' and not await channel_has_access(user.id, channel, permission='read', db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

        write_access = await channel_has_access(
            user.id,
            channel,
            permission='write',
            strict=False,
            db=db,
        )

        filter = {'roles': ['!pending']}
        member_user_ids = await get_channel_member_user_ids(channel, db=db)
        if member_user_ids is not None:
            filter['user_ids'] = member_user_ids

        user_result = await Users.get_users(filter=filter, limit=0, db=db)
        user_count = user_result['total']

        channel_member = await Channels.get_member_by_channel_and_user_id(channel.id, user.id, db=db)
        unread_count = await Messages.get_unread_message_count(
            channel.id, user.id, channel_member.last_read_at if channel_member else None
        )

        return ChannelFullResponse(
            **{
                **channel.model_dump(),
                'user_ids': user_ids,
                'users': users,
                'is_manager': await Channels.is_user_channel_manager(channel.id, user.id, db=db),
                'write_access': write_access or user.role == 'admin',
                'user_count': user_count,
                'last_read_at': channel_member.last_read_at if channel_member else None,
                'is_channel_muted': channel_member.is_channel_muted if channel_member else False,
                'unread_count': unread_count,
            }
        )


############################
# GetChannelMembersById
############################


PAGE_ITEM_COUNT = 30


class ChannelMemberResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    profile_image_url: str | None = None
    presence_state: str | None = None
    status_emoji: str | None = None
    status_message: str | None = None
    status_expires_at: int | None = None
    is_active: bool = False


class ChannelMemberListResponse(BaseModel):
    users: list[ChannelMemberResponse]
    total: int


def serialize_channel_member(user: UserModel) -> ChannelMemberResponse:
    return ChannelMemberResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        profile_image_url=user.profile_image_url,
        presence_state=user.presence_state,
        status_emoji=user.status_emoji,
        status_message=user.status_message,
        status_expires_at=user.status_expires_at,
        is_active=Users.is_active(user),
    )


@router.get('/{id}/members', response_model=ChannelMemberListResponse)
async def get_channel_members_by_id(
    request: Request,
    id: str,
    query: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)

    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    limit = PAGE_ITEM_COUNT

    page = max(1, page)
    skip = (page - 1) * limit

    if channel.type in ['group', 'dm']:
        if not await Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
    else:
        if user.role != 'admin' and not await channel_has_access(user.id, channel, permission='read', db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    if channel.type == 'dm':
        user_ids = [member.user_id for member in await Channels.get_members_by_channel_id(channel.id, db=db)]
        fetched_users = await Users.get_users_by_user_ids(user_ids, db=db)
        total = len(fetched_users)

        return {
            'users': [serialize_channel_member(u) for u in fetched_users],
            'total': total,
        }
    else:
        filter = {}

        if query:
            filter['query'] = query

        if channel.type == 'group':
            filter['channel_id'] = channel.id
        else:
            filter['roles'] = ['!pending']
            member_user_ids = await get_channel_member_user_ids(channel, db=db)
            if member_user_ids is not None:
                filter['user_ids'] = member_user_ids

        result = await Users.get_users(
            filter=filter,
            sort={'order_by': order_by, 'direction': direction},
            skip=skip,
            limit=limit,
            db=db,
        )

        fetched_users = result['users']
        total = result['total']

        return {
            'users': [serialize_channel_member(u) for u in fetched_users],
            'total': total,
        }


#################################################
# UpdateIsActiveMemberByIdAndUserId
#################################################


class UpdateActiveMemberForm(BaseModel):
    is_active: bool


class UpdateMutedMemberForm(BaseModel):
    is_channel_muted: bool


@router.post('/{id}/members/mute', response_model=UpdateMutedMemberForm)
async def update_member_mute_status(
    request: Request,
    id: str,
    form_data: UpdateMutedMemberForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if channel.type in ['group', 'dm']:
        if not await Channels.is_user_channel_member(id, user.id, db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
    elif user.role != 'admin' and not await channel_has_access(user.id, channel, permission='read', db=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    is_channel_muted = await Channels.update_member_mute_status(id, user.id, form_data.is_channel_muted, db=db)
    await emit_to_users(
        'events:channel',
        {'channel_id': id, 'data': {'type': 'channel:mute', 'data': {'is_channel_muted': is_channel_muted}}},
        [user.id],
    )
    return {'is_channel_muted': is_channel_muted}


@router.post('/{id}/members/active', response_model=bool)
async def update_is_active_member_by_id_and_user_id(
    request: Request,
    id: str,
    form_data: UpdateActiveMemberForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if not await Channels.is_user_channel_member(channel.id, user.id, db=db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    await encryption.invalidate(id)
    await Channels.update_member_active_status(channel.id, user.id, form_data.is_active, db=db)
    await publish_event(
        request,
        EVENTS.CHANNEL_MEMBER_ACTIVE_UPDATED,
        actor=user,
        subject_id=channel.id,
        data={'is_active': form_data.is_active},
    )
    return True


#################################################
# AddMembersById
#################################################


class UpdateMembersForm(BaseModel):
    user_ids: list[str] = []
    group_ids: list[str] = []


@router.post('/{id}/update/members/add')
async def add_members_by_id(
    request: Request,
    id: str,
    form_data: UpdateMembersForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if channel.user_id != user.id and user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    if channel.type == 'dm':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    try:
        memberships = await Channels.add_members_to_channel(
            channel.id, user.id, form_data.user_ids, form_data.group_ids, db=db
        )
        if channel.type in ['group', 'dm']:
            participant_ids = [member.user_id for member in memberships]
            await emit_to_users(
                'events:channel',
                {'data': {'type': 'channel:created'}},
                participant_ids,
            )
            await enter_room_for_users(f'channel:{channel.id}', participant_ids)

        await publish_event(
            request,
            EVENTS.CHANNEL_MEMBER_ADDED,
            actor=user,
            subject_id=channel.id,
            data={'user_ids': form_data.user_ids, 'group_ids': form_data.group_ids},
        )
        return memberships
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


#################################################
#
#################################################


class RemoveMembersForm(BaseModel):
    user_ids: list[str] = []


@router.post('/{id}/update/members/remove')
async def remove_members_by_id(
    request: Request,
    id: str,
    form_data: RemoveMembersForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)

    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if channel.user_id != user.id and user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    if channel.type == 'dm':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    try:
        await encryption.invalidate(id)
        deleted = await Channels.remove_members_from_channel(channel.id, form_data.user_ids, db=db)
        if channel.type == 'group':
            await leave_room_for_users(f'channel:{channel.id}', form_data.user_ids)

        await publish_event(
            request,
            EVENTS.CHANNEL_MEMBER_REMOVED,
            actor=user,
            subject_id=channel.id,
            data={'user_ids': form_data.user_ids},
        )
        return deleted
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# UpdateChannelById
############################


@router.post('/{id}/update', response_model=Optional[ChannelModel])
async def update_channel_by_id(
    request: Request,
    id: str,
    form_data: ChannelForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)

    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if channel.user_id != user.id and user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    try:
        await encryption.invalidate(id)
        channel = await Channels.update_channel_by_id(id, form_data, db=db)
        await publish_event(
            request,
            EVENTS.CHANNEL_UPDATED,
            actor=user,
            subject_id=id,
            data={'name': channel.name, 'type': channel.type},
        )
        return ChannelModel(**channel.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


class ChannelAccessGrantsForm(BaseModel):
    access_grants: list[dict]


@router.post('/{id}/access/update', response_model=ChannelModel)
async def update_channel_access_by_id(
    request: Request,
    id: str,
    form_data: ChannelAccessGrantsForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=404, detail=ERROR_MESSAGES.NOT_FOUND)
    if channel.user_id != user.id and user.role != 'admin':
        raise HTTPException(status_code=403, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)
    # Group and DM channels manage access through membership instead.
    if channel.type in ['group', 'dm']:
        raise HTTPException(status_code=403, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    grants = await validate_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        resource_type='channel',
        db=db,
    )
    previous_access_grants = channel.access_grants
    await encryption.invalidate(id)
    channel.access_grants = await AccessGrants.set_access_grants('channel', id, grants, db=db)
    revoked_user_ids = await AccessGrants.get_revoked_user_ids_by_resource('channel', id, previous_access_grants, db=db)
    revoked_user_ids.discard(channel.user_id)
    await leave_room_for_users(f'channel:{id}', list(revoked_user_ids))
    await publish_event(
        request, EVENTS.CHANNEL_UPDATED, actor=user, subject_id=id, data={'name': channel.name, 'type': channel.type}
    )
    return channel


############################
# DeleteChannelById
############################


@router.delete('/{id}/delete', response_model=bool)
async def delete_channel_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)

    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if channel.user_id != user.id and user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    try:
        await encryption.invalidate(id)
        await Channels.delete_channel_by_id(id, db=db)
        await sio.close_room(f'channel:{id}')
        await publish_event(
            request,
            EVENTS.CHANNEL_DELETED,
            actor=user,
            subject_id=id,
            data={'name': channel.name, 'type': channel.type},
        )
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# GetChannelMessages
############################


@router.get('/{channel_id}/apps')
async def get_channel_apps(
    channel_id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    await check_app_channel_access(channel_id, user=user, db=db)
    apps = (
        await db.scalars(
            select(App)
            .join(ChannelMember, ChannelMember.app_id == App.id)
            .where(
                ChannelMember.channel_id == channel_id,
                ChannelMember.is_active.is_(True),
            )
        )
    ).all()
    return [get_app_response(app) for app in apps]


@router.post('/{channel_id}/apps')
async def invite_app(
    channel_id: str, form: AppInvitation, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    await check_app_channel_access(channel_id, require_manager=True, user=user, db=db)
    app = await get_app_by_id(form.app_id, require_active=True, db=db)
    if not await has_app_access(app, user, db=db):
        raise HTTPException(403, 'App invocation denied')
    member = await db.scalar(
        select(ChannelMember).where(ChannelMember.channel_id == channel_id, ChannelMember.app_id == app.id)
    )
    now = time.time_ns()
    if member:
        member.is_active, member.left_at, member.joined_at = True, None, now
        member.updated_at, member.invited_by, member.invited_at = now, user.id, now
    else:
        db.add(
            ChannelMember(
                id=str(uuid.uuid4()),
                channel_id=channel_id,
                user_id=None,
                app_id=app.id,
                role='member',
                status='joined',
                is_active=True,
                invited_by=user.id,
                invited_at=now,
                joined_at=now,
                created_at=now,
                updated_at=now,
            )
        )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, 'Invitation changed concurrently; reload the app list') from None
    return get_app_response(app)


@router.delete('/{channel_id}/apps/{app_id}')
async def remove_app(
    channel_id: str, app_id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    await check_app_channel_access(channel_id, require_manager=True, user=user, db=db)
    await db.execute(
        update(ChannelMember)
        .where(ChannelMember.channel_id == channel_id, ChannelMember.app_id == app_id)
        .values(
            is_active=False,
            left_at=time.time_ns(),
            updated_at=time.time_ns(),
        )
    )
    await db.commit()
    return {'removed': True}


class MessageUserResponse(MessageResponse):
    data: dict | bool | None = None

    @field_validator('data', mode='before')
    def serialize_data(cls, v, info):
        if not isinstance(v, dict):
            return False
        # App cards and buttons are message content, not lazy-loaded attachments.
        if info.data.get('app_id'):
            return v
        return any(bool(val) for val in v.values())


@router.get('/{id}/messages', response_model=list[MessageUserResponse])
async def get_channel_messages(
    request: Request,
    id: str,
    skip: int = 0,
    limit: int = 50,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if channel.type in ['group', 'dm']:
        if not await Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
    else:
        if user.role != 'admin' and not await channel_has_access(user.id, channel, permission='read', db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

        channel_member = await Channels.join_channel(id, user.id, db=db)  # Ensure user is a member of the channel

    message_list = await Messages.get_messages_by_channel_id(id, skip, limit, db=db)

    if not message_list:
        return []

    # Batch fetch all users in a single query (fixes N+1 problem)
    user_ids = list(set(m.user_id for m in message_list))
    fetched_users = {u.id: u for u in await Users.get_users_by_user_ids(user_ids, db=db)}

    # Batch fetch reactions and reply counts in 2 queries (fixes N+1)
    message_ids = [m.id for m in message_list]
    all_reactions = await Messages.get_reactions_by_message_ids(message_ids, db=db)
    all_reply_counts = await Messages.get_thread_reply_counts_by_message_ids(message_ids, db=db)

    messages = []
    for message in message_list:
        reply_count, latest_reply_at = all_reply_counts.get(message.id, (0, None))

        # Use message.user if present (for webhooks), otherwise look up by user_id
        user_info = message.user
        if user_info is None and message.user_id in fetched_users:
            user_info = UserNameResponse(**fetched_users[message.user_id].model_dump())

        messages.append(
            MessageUserResponse(
                **{
                    **message.model_dump(),
                    'reply_count': reply_count,
                    'latest_reply_at': latest_reply_at,
                    'reactions': all_reactions.get(message.id, []),
                    'user': user_info,
                }
            )
        )

    return messages


############################
# GetPinnedChannelMessages
############################

PAGE_ITEM_COUNT_PINNED = 20


@router.get('/{id}/messages/pinned', response_model=list[MessageWithReactionsResponse])
async def get_pinned_channel_messages(
    request: Request,
    id: str,
    page: int = 1,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if channel.type in ['group', 'dm']:
        if not await Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
    else:
        if user.role != 'admin' and not await channel_has_access(user.id, channel, permission='read', db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    page = max(1, page)
    skip = (page - 1) * PAGE_ITEM_COUNT_PINNED
    limit = PAGE_ITEM_COUNT_PINNED

    message_list = await Messages.get_pinned_messages_by_channel_id(id, skip, limit, db=db)

    if not message_list:
        return []

    # Batch fetch all users in a single query (fixes N+1 problem)
    user_ids = list(set(m.user_id for m in message_list))
    fetched_users = {u.id: u for u in await Users.get_users_by_user_ids(user_ids, db=db)}

    # Batch fetch reactions in 1 query (fixes N+1)
    message_ids = [m.id for m in message_list]
    all_reactions = await Messages.get_reactions_by_message_ids(message_ids, db=db)

    messages = []
    for message in message_list:
        # Check for webhook identity in meta
        webhook_info = message.meta.get('webhook') if message.meta else None
        if webhook_info:
            user_info = UserNameResponse(
                id=webhook_info.get('id') or '',
                name=webhook_info.get('name') or 'Webhook',
                role='webhook',
            )
        elif message.user_id in fetched_users:
            user_info = UserNameResponse(**fetched_users[message.user_id].model_dump())
        else:
            user_info = None

        messages.append(
            MessageWithReactionsResponse(
                **{
                    **message.model_dump(),
                    'reactions': all_reactions.get(message.id, []),
                    'user': user_info,
                }
            )
        )

    return messages


############################
# PostNewMessage
############################


async def send_notification(request, channel, message, active_user_ids, db=None):
    webui_url = await Config.get('webui.url')
    enable_user_webhooks = await Config.get('ui.enable_user_webhooks')

    # Batch fetch channel members in 1 query (fixes N+1)
    members = {m.user_id: m for m in await Channels.get_members_by_channel_id(channel.id, db=db)}
    if channel.type in ['group', 'dm']:
        users = await Users.get_users_by_user_ids(list(members), db=db)
    else:
        users = await get_channel_users_with_access(channel, 'read', db=db)
    mentioned_user_ids = {m['id'] for m in extract_mentions(message.content) if m['id_type'] == 'U'}
    url = f'{webui_url}/channels/{channel.id}'

    for u in users:
        member = members.get(u.id)
        if member and member.is_channel_muted and u.id not in mentioned_user_ids:
            continue
        if (u.id not in active_user_ids) and member:
            if enable_user_webhooks and u.settings:
                await publish_event(
                    request,
                    EVENTS.CHANNEL_MESSAGE,
                    subject_id=channel.id,
                    subject_type='channel',
                    data={
                        'user_id': u.id,
                        'channel_id': channel.id,
                        'message_id': message.id,
                        'sender_id': message.user_id,
                        'content': message.content,
                        'message': f'#{channel.name} - {url}\n\n{message.content}',
                        'content_preview': message.content[:300],
                        'title': channel.name,
                        'url': url,
                    },
                    message=channel.name,
                )

    return True


async def app_channel_reply_handler(channel_id, message_id, user_id):
    """Committed human messages only; errors never cause the human POST to retry."""
    if not await Config.get('apps.enable'):
        return
    async with get_async_db() as db:
        message = await db.get(Message, message_id)
        if not message or message.app_id or message.user_id != user_id or message.channel_id != channel_id:
            return
        text = message.content
        parent_id = message.parent_id
        app_ids = dict.fromkeys(mention['id'] for mention in extract_mentions(text) if mention['id_type'] == 'A')
    for app_id in list(app_ids)[:10]:
        app_name = None
        try:
            async with get_async_db() as db:
                app = await get_app_by_id(app_id, require_active=True, db=db)
                app_name = app.name
                user = await Users.get_user_by_id(user_id, db=db)
                if not user:
                    continue
                await send_app_mention(
                    app,
                    user,
                    channel_id,
                    {'text': text, 'message_id': message_id, 'parent_id': parent_id},
                    operation_id=message_id,
                    db=db,
                    scope='channels:messages:read'
                    if 'channels:messages:read' in app.data['granted_scopes']
                    else 'channels:mentions:read',
                )
        except Exception as exc:
            log.warning(
                'App mention delivery failed: app=%s message=%s status=%s',
                app_id,
                message_id,
                getattr(exc, 'status_code', None),
            )
            status_code = getattr(exc, 'status_code', None)
            detail = (
                exc.detail
                if isinstance(exc, HTTPException) and isinstance(exc.detail, str)
                else 'Unexpected error while delivering the message.'
            )
            if status_code == 504:
                detail += '\nDelivery was not confirmed. The app may have accepted the message; check before retrying.'
            try:
                async with get_async_db() as db:
                    app = await get_app_by_id(app_id, require_active=True, db=db)
                    await create_app_message(
                        db,
                        app,
                        channel_id,
                        AppChannelMessage(
                            content='App error:\n\n```text\n' + detail[:2400].replace('```', '` ` `') + '\n```',
                            parent_id=parent_id,
                            reply_to_id=message_id,
                        ),
                    )
                continue
            except Exception:
                # An inactive/removed app or one without write access cannot post a public reply.
                log.warning('Could not save app error reply: app=%s message=%s', app_id, message_id)
            await emit_to_users(
                'events:app',
                {
                    'app_id': app_id,
                    'app_name': app_name,
                    'channel_id': channel_id,
                    'message_id': message_id,
                    'parent_id': parent_id,
                    'reply': {'type': 'error', 'content': detail},
                },
                [user_id],
            )


async def model_response_handler(request, channel, message, user, db=None):
    MODELS = {model['id']: model for model in await get_filtered_models(await get_all_models(request, user=user), user)}

    mentions = extract_mentions(message.content)
    message_content = replace_mentions(message.content)

    model_mentions = {}

    # check if the message is a reply to a message sent by a model
    if (
        message.reply_to_message
        and message.reply_to_message.meta
        and message.reply_to_message.meta.get('model_id', None)
    ):
        model_id = message.reply_to_message.meta.get('model_id', None)
        model_mentions[model_id] = {'id': model_id, 'id_type': 'M'}

    # check if any of the mentions are models
    for mention in mentions:
        if mention['id_type'] == 'M' and mention['id'] not in model_mentions:
            model_mentions[mention['id']] = mention

    if not model_mentions:
        return False

    for mention in model_mentions.values():
        model_id = mention['id']
        model = MODELS.get(model_id, None)

        if model:
            try:
                # reverse to get in chronological order
                thread_messages = (
                    await Messages.get_messages_by_parent_id(
                        channel.id,
                        message.parent_id if message.parent_id else message.id,
                        db=db,
                    )
                )[::-1]
                response_parent_id = (
                    message.parent_id
                    if message.parent_id
                    else (
                        message.id if await Config.get('channels.model_response_mode', 'thread') == 'thread' else None
                    )
                )

                response_message, channel = await new_message_handler(
                    request,
                    channel.id,
                    MessageForm(
                        **{
                            'parent_id': response_parent_id,
                            'content': f'',
                            'data': {},
                            'meta': {
                                'model_id': model_id,
                                'model_name': model.get('name', model_id),
                            },
                        }
                    ),
                    user,
                    db,
                )

                thread_history = []
                images = []
                files = []

                # Batch fetch all users in a single query (fixes N+1 problem)
                user_ids = list({message.user_id for message in thread_messages})
                message_users = {user.id: user for user in await Users.get_users_by_user_ids(user_ids, db=db)}

                for thread_message in thread_messages:
                    message_user = message_users.get(thread_message.user_id)

                    if thread_message.meta and thread_message.meta.get('model_id', None):
                        # If the message was sent by a model, use the model name
                        message_model_id = thread_message.meta.get('model_id', None)
                        message_model = MODELS.get(message_model_id, None)
                        username = message_model.get('name', message_model_id) if message_model else message_model_id
                    else:
                        username = message_user.name if message_user else 'Unknown'

                    thread_history.append(f'{username}: {replace_mentions(thread_message.content)}')

                    thread_message_files = (thread_message.data or {}).get('files', [])
                    for file in thread_message_files:
                        if file.get('type', '') == 'image':
                            images.append(file.get('url', ''))
                        elif file.get('content_type', '').startswith('image/'):
                            image = await get_image_base64_from_file_id(file.get('id', ''), user=user)
                            if image:
                                images.append(image)
                        elif file.get('id'):
                            files.append(file)

                thread_history_string = '\n\n'.join(thread_history)
                system_message = {
                    'role': 'system',
                    'content': f'You are {model.get("name", model_id)}, participating in a threaded conversation. Be concise and conversational.'
                    + (
                        f"Here's the thread history:\n\n\n{thread_history_string}\n\n\nContinue the conversation naturally as {model.get('name', model_id)}, addressing the most recent message while being aware of the full context."
                        if thread_history
                        else ''
                    ),
                }

                content = f'{user.name if user else "User"}: {message_content}'
                if images:
                    content = [
                        {
                            'type': 'text',
                            'text': content,
                        },
                        *[
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': image,
                                },
                            }
                            for image in images
                        ],
                    ]

                # Resolve model config (same path automations use)
                from open_webui.utils.automations import _resolve_model_defaults

                # Build full form_data — same shape as frontend POST.
                # The channel: prefix routes pipeline events to the
                # channel emitter in socket/main.py instead of the
                # default chat emitter.
                form_data = {
                    **await _resolve_model_defaults(request.app, model_id),
                    'model': model_id,
                    'messages': [
                        system_message,
                        {'role': 'user', 'content': content},
                    ],
                    'stream': True,
                    'chat_id': f'channel:{channel.id}',
                    'id': response_message.id,
                    'session_id': f'channel:{channel.id}',
                    'background_tasks': {},
                }
                if files:
                    form_data['files'] = files

                # Call the full chat completion pipeline — streaming,
                # tools, filters, RAG — everything. The pipeline runs as
                # an async task; the channel emitter handles progressive
                # message updates via socket events.
                await request.app.state.CHAT_COMPLETION_HANDLER(request, form_data, user=user)

            except Exception as e:
                log.exception(e)

    return True


async def new_message_handler(request: Request, id: str, form_data: MessageForm, user, db):
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if channel.type in ['group', 'dm']:
        if not await Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
    else:
        if user.role != 'admin' and not await channel_has_access(
            user.id,
            channel,
            permission='write',
            strict=False,
            db=db,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    # Thread parent / reply target must belong to this channel (no cross-channel binding).
    for ref_id in (form_data.parent_id, form_data.reply_to_id):
        if ref_id:
            ref = await Messages.get_message_by_id(ref_id, include_thread_replies=False, db=db)
            if not ref or ref.channel_id != channel.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    try:
        message = await Messages.insert_new_message(form_data, channel.id, user.id, db=db)
        if message:
            if channel.type in ['group', 'dm']:
                members = await Channels.get_members_by_channel_id(channel.id, db=db)
                for member in members:
                    if not member.is_active:
                        await Channels.update_member_active_status(channel.id, member.user_id, True, db=db)

            message = await Messages.get_message_by_id(message.id, db=db)
            event_data = {
                'channel_id': channel.id,
                'message_id': message.id,
                'data': {
                    'type': 'message',
                    'data': {'temp_id': form_data.temp_id, **message.model_dump()},
                },
                'user': UserNameResponse(**user.model_dump()).model_dump(),
                'channel': channel.model_dump(),
            }

            await sio.emit(
                'events:channel',
                event_data,
                to=f'channel:{channel.id}',
            )

            if message.parent_id:
                # If this message is a reply, emit to the parent message as well
                parent_message = await Messages.get_message_by_id(message.parent_id, db=db)

                if parent_message:
                    await sio.emit(
                        'events:channel',
                        {
                            'channel_id': channel.id,
                            'message_id': parent_message.id,
                            'data': {
                                'type': 'message:reply',
                                'data': parent_message.model_dump(),
                            },
                            'user': UserNameResponse(**user.model_dump()).model_dump(),
                            'channel': channel.model_dump(),
                        },
                        to=f'channel:{channel.id}',
                    )
            return message, channel
        else:
            raise Exception('Error creating message')
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.post('/{id}/messages/post', response_model=Optional[MessageModel])
async def post_new_message(
    request: Request,
    id: str,
    form_data: MessageForm,
    background_tasks: BackgroundTasks,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    # Message metadata is set by the server only.
    form_data.meta = None

    try:
        message, channel = await new_message_handler(request, id, form_data, user, db)
        try:
            if files := message.data.get('files', []):
                for file in files:
                    await Channels.set_file_message_id_in_channel_by_id(
                        channel.id, file.get('id', ''), message.id, db=db
                    )
        except Exception as e:
            log.debug(e)

        # NOTE: We intentionally do NOT pass db to background_handler.
        # Background tasks should manage their own short-lived sessions to avoid
        # holding database connections during slow operations (e.g., LLM calls).
        async def background_handler():
            active_user_ids = await get_user_ids_from_room(f'channel:{channel.id}')
            await create_task(None, app_channel_reply_handler(channel.id, message.id, user.id))
            await model_response_handler(request, channel, message, user)
            await send_notification(
                request,
                channel,
                message,
                active_user_ids,
            )

        background_tasks.add_task(background_handler)

        await publish_event(
            request,
            EVENTS.MESSAGE_CREATED,
            actor=user,
            subject_id=message.id,
            data={
                'channel_id': channel.id,
                'content_preview': message.content[:300],
            },
        )
        return message

    except HTTPException as e:
        raise e
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# GetChannelMessage
############################


@router.get('/{id}/messages/{message_id}', response_model=Optional[MessageResponse])
async def get_channel_message(
    request: Request,
    id: str,
    message_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if channel.type in ['group', 'dm']:
        if not await Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
    else:
        if user.role != 'admin' and not await channel_has_access(user.id, channel, permission='read', db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    message = await Messages.get_message_by_id(message_id, db=db)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if message.channel_id != id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    message_user = await Users.get_user_by_id(message.user_id, db=db)
    return MessageResponse(
        **{
            **message.model_dump(),
            'user': UserNameResponse(**message_user.model_dump()) if message_user else getattr(message, 'user', None),
        }
    )


############################
# GetChannelMessageData
############################


@router.get('/{id}/messages/{message_id}/data', response_model=Optional[dict])
async def get_channel_message_data(
    request: Request,
    id: str,
    message_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if channel.type in ['group', 'dm']:
        if not await Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
    else:
        if user.role != 'admin' and not await channel_has_access(user.id, channel, permission='read', db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    message = await Messages.get_message_by_id(message_id, db=db)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if message.channel_id != id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    return message.data


############################
# PinChannelMessage
############################


class PinMessageForm(BaseModel):
    is_pinned: bool


@router.post('/{id}/messages/{message_id}/pin', response_model=Optional[MessageUserResponse])
async def pin_channel_message(
    request: Request,
    id: str,
    message_id: str,
    form_data: PinMessageForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if channel.type in ['group', 'dm']:
        if not await Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
    else:
        # Pin/unpin mutates is_pinned/pinned_by/pinned_at — require write.
        if user.role != 'admin' and not await channel_has_access(user.id, channel, permission='write', db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    message = await Messages.get_message_by_id(message_id, db=db)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if message.channel_id != id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    try:
        await Messages.update_is_pinned_by_id(message_id, form_data.is_pinned, user.id, db=db)
        message = await Messages.get_message_by_id(message_id, db=db)
        message_user = await Users.get_user_by_id(message.user_id, db=db)
        message_data = MessageUserResponse(
            **{
                **message.model_dump(),
                'user': UserNameResponse(**message_user.model_dump())
                if message_user
                else getattr(message, 'user', None),
            }
        )

        await sio.emit(
            'events:channel',
            {
                'channel_id': channel.id,
                'message_id': message.id,
                'data': {
                    'type': 'message:update',
                    'data': message_data.model_dump(),
                },
                'user': UserNameResponse(**user.model_dump()).model_dump(),
                'channel': channel.model_dump(),
            },
            to=f'channel:{channel.id}',
        )

        await publish_event(
            request,
            EVENTS.MESSAGE_PINNED if form_data.is_pinned else EVENTS.MESSAGE_UNPINNED,
            actor=user,
            subject_id=message_id,
            subject_type='message',
            data={'channel_id': id},
        )
        return message_data
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# GetChannelThreadMessages
############################


@router.get('/{id}/messages/{message_id}/thread', response_model=list[MessageUserResponse])
async def get_channel_thread_messages(
    request: Request,
    id: str,
    message_id: str,
    skip: int = 0,
    limit: int = 50,
    around: str | None = None,
    before: str | None = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if channel.type in ['group', 'dm']:
        if not await Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
    else:
        if user.role != 'admin' and not await channel_has_access(user.id, channel, permission='read', db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    message_list = await Messages.get_messages_by_parent_id(
        id, message_id, skip, min(max(limit, 1), 100), db=db, around=around, before=before
    )

    if not message_list:
        return []

    # Batch fetch all users in a single query (fixes N+1 problem)
    user_ids = list(set(m.user_id for m in message_list))
    fetched_users = {u.id: u for u in await Users.get_users_by_user_ids(user_ids, db=db)}

    # Batch fetch reactions in 1 query (fixes N+1)
    message_ids = [m.id for m in message_list]
    all_reactions = await Messages.get_reactions_by_message_ids(message_ids, db=db)

    messages = []
    for message in message_list:
        # Use message.user if present (for webhooks), otherwise look up by user_id
        user_info = message.user
        if user_info is None and message.user_id in fetched_users:
            user_info = UserNameResponse(**fetched_users[message.user_id].model_dump())

        messages.append(
            MessageUserResponse(
                **{
                    **message.model_dump(),
                    'reply_count': 0,
                    'latest_reply_at': None,
                    'reactions': all_reactions.get(message.id, []),
                    'user': user_info,
                }
            )
        )

    return messages


############################
# UpdateMessageById
############################


@router.post('/{id}/messages/{message_id}/update', response_model=Optional[MessageModel])
async def update_message_by_id(
    request: Request,
    id: str,
    message_id: str,
    form_data: MessageForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    message = await Messages.get_message_by_id(message_id, db=db)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if message.channel_id != id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    if channel.type in ['group', 'dm']:
        if not await Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
        # Membership is not authorship — block cross-member edits.
        if user.role != 'admin' and message.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
    else:
        if user.role != 'admin' and not await channel_has_access(
            user.id, channel, permission='write', strict=False, db=db
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
        # Write access is not authorship — block cross-member edits.
        if user.role != 'admin' and message.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    form_data.meta = None
    try:
        await Messages.update_message_by_id(message_id, form_data, db=db)
        message = await Messages.get_message_by_id(message_id, db=db)

        if message:
            await sio.emit(
                'events:channel',
                {
                    'channel_id': channel.id,
                    'message_id': message.id,
                    'data': {
                        'type': 'message:update',
                        'data': message.model_dump(),
                    },
                    'user': UserNameResponse(**user.model_dump()).model_dump(),
                    'channel': channel.model_dump(),
                },
                to=f'channel:{channel.id}',
            )

        await publish_event(
            request,
            EVENTS.MESSAGE_UPDATED,
            actor=user,
            subject_id=message_id,
            data={'channel_id': id, 'content_preview': form_data.content[:300]},
        )
        return MessageModel(**message.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# AddReactionToMessage
############################


class ReactionForm(BaseModel):
    name: str


@router.post('/{id}/messages/{message_id}/reactions/add', response_model=bool)
async def add_reaction_to_message(
    request: Request,
    id: str,
    message_id: str,
    form_data: ReactionForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if channel.type in ['group', 'dm']:
        if not await Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
    else:
        if user.role != 'admin' and not await channel_has_access(
            user.id,
            channel,
            permission='write',
            strict=False,
            db=db,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    message = await Messages.get_message_by_id(message_id, db=db)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if message.channel_id != id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    try:
        await Messages.add_reaction_to_message(message_id, user.id, form_data.name, db=db)
        message = await Messages.get_message_by_id(message_id, db=db)

        await sio.emit(
            'events:channel',
            {
                'channel_id': channel.id,
                'message_id': message.id,
                'data': {
                    'type': 'message:reaction:add',
                    'data': {
                        **message.model_dump(),
                        'name': form_data.name,
                    },
                },
                'user': UserNameResponse(**user.model_dump()).model_dump(),
                'channel': channel.model_dump(),
            },
            to=f'channel:{channel.id}',
        )

        await publish_event(
            request,
            EVENTS.MESSAGE_REACTION_ADDED,
            actor=user,
            subject_id=message_id,
            data={'channel_id': id, 'reaction': form_data.name},
        )
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# RemoveReactionById
############################


@router.post('/{id}/messages/{message_id}/reactions/remove', response_model=bool)
async def remove_reaction_by_id_and_user_id_and_name(
    request: Request,
    id: str,
    message_id: str,
    form_data: ReactionForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if channel.type in ['group', 'dm']:
        if not await Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
    else:
        if user.role != 'admin' and not await channel_has_access(
            user.id,
            channel,
            permission='write',
            strict=False,
            db=db,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    message = await Messages.get_message_by_id(message_id, db=db)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if message.channel_id != id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    try:
        await Messages.remove_reaction_by_id_and_user_id_and_name(message_id, user.id, form_data.name, db=db)

        message = await Messages.get_message_by_id(message_id, db=db)

        await sio.emit(
            'events:channel',
            {
                'channel_id': channel.id,
                'message_id': message.id,
                'data': {
                    'type': 'message:reaction:remove',
                    'data': {
                        **message.model_dump(),
                        'name': form_data.name,
                    },
                },
                'user': UserNameResponse(**user.model_dump()).model_dump(),
                'channel': channel.model_dump(),
            },
            to=f'channel:{channel.id}',
        )

        await publish_event(
            request,
            EVENTS.MESSAGE_REACTION_REMOVED,
            actor=user,
            subject_id=message_id,
            data={'channel_id': id, 'reaction': form_data.name},
        )
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# DeleteMessageById
############################


@router.delete('/{id}/messages/{message_id}/delete', response_model=bool)
async def delete_message_by_id(
    request: Request,
    id: str,
    message_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    message = await Messages.get_message_by_id(message_id, db=db)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if message.channel_id != id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    if channel.type in ['group', 'dm']:
        if not await Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
        # Membership is not authorship — block cross-member deletes.
        if user.role != 'admin' and message.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
    else:
        if user.role != 'admin' and not await channel_has_access(
            user.id,
            channel,
            permission='write',
            strict=False,
            db=db,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
        # Write access is not authorship — block cross-member deletes.
        if user.role != 'admin' and message.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    try:
        await Messages.delete_message_by_id(message_id, db=db)
        await Messages.delete_replies_by_id(message_id, db=db)
        await sio.emit(
            'events:channel',
            {
                'channel_id': channel.id,
                'message_id': message.id,
                'data': {
                    'type': 'message:delete',
                    'data': {
                        **message.model_dump(),
                        'user': UserNameResponse(**user.model_dump()).model_dump(),
                    },
                },
                'user': UserNameResponse(**user.model_dump()).model_dump(),
                'channel': channel.model_dump(),
            },
            to=f'channel:{channel.id}',
        )

        if message.parent_id:
            # If this message is a reply, emit to the parent message as well
            parent_message = await Messages.get_message_by_id(message.parent_id, db=db)

            if parent_message:
                await sio.emit(
                    'events:channel',
                    {
                        'channel_id': channel.id,
                        'message_id': parent_message.id,
                        'data': {
                            'type': 'message:reply',
                            'data': parent_message.model_dump(),
                        },
                        'user': UserNameResponse(**user.model_dump()).model_dump(),
                        'channel': channel.model_dump(),
                    },
                    to=f'channel:{channel.id}',
                )

        await publish_event(
            request,
            EVENTS.MESSAGE_DELETED,
            actor=user,
            subject_id=message_id,
            data={'channel_id': id},
        )
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# Webhooks
############################


@router.get('/webhooks/{webhook_id}/profile/image')
async def get_webhook_profile_image(
    request: Request,
    webhook_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get webhook profile image by webhook ID."""
    await check_channels_access(request, user)
    webhook = await Channels.get_webhook_by_id(webhook_id, db=db)
    if not webhook:
        # Return default favicon if webhook not found
        # LICENSE covers this Open WebUI fallback logo.
        # Do not alter, remove, obscure, or replace it except as LICENSE permits:
        # https://docs.openwebui.com/license.
        return FileResponse(f'{STATIC_DIR}/favicon.png')

    channel = await Channels.get_channel_by_id(webhook.channel_id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if channel.type in ['group', 'dm']:
        if not await Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())
    else:
        if user.role != 'admin' and not await channel_has_access(user.id, channel, permission='read', db=db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    if webhook.profile_image_url:
        # Check if it's url or base64
        if webhook.profile_image_url.startswith('http'):
            if ENABLE_PROFILE_IMAGE_URL_FORWARDING:
                return Response(
                    status_code=status.HTTP_302_FOUND,
                    headers={'Location': webhook.profile_image_url},
                )
            # When forwarding is disabled, fall through to the default image to prevent client-side IP/UA/Referer leaks.
        elif webhook.profile_image_url.startswith('data:image'):
            try:
                header, base64_data = webhook.profile_image_url.split(',', 1)
                image_data = base64.b64decode(base64_data)
                image_buffer = io.BytesIO(image_data)
                media_type = header.split(';')[0].lstrip('data:')

                return StreamingResponse(
                    image_buffer,
                    media_type=media_type,
                    headers={'Content-Disposition': 'inline'},
                )
            except Exception as e:
                pass

    # Return default favicon if no profile image
    # LICENSE covers this Open WebUI fallback logo.
    # Do not alter, remove, obscure, or replace it except as LICENSE permits:
    # https://docs.openwebui.com/license.
    return FileResponse(f'{STATIC_DIR}/favicon.png')


@router.get('/{id}/webhooks', response_model=list[ChannelWebhookModel])
async def get_channel_webhooks(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    # Only channel managers can view webhooks
    if not await Channels.is_user_channel_manager(channel.id, user.id, db=db) and user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.UNAUTHORIZED)

    return await Channels.get_webhooks_by_channel_id(id, db=db)


@router.post('/{id}/webhooks/create', response_model=ChannelWebhookModel)
async def create_channel_webhook(
    request: Request,
    id: str,
    form_data: ChannelWebhookForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    # Only channel managers can create webhooks
    if not await Channels.is_user_channel_manager(channel.id, user.id, db=db) and user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.UNAUTHORIZED)

    webhook = await Channels.insert_webhook(id, user.id, form_data, db=db)
    if not webhook:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    await publish_event(
        request,
        EVENTS.CHANNEL_WEBHOOK_CREATED,
        actor=user,
        subject_id=webhook.id,
        data={'channel_id': id, 'name': webhook.name},
    )
    return webhook


@router.post('/{id}/webhooks/{webhook_id}/update', response_model=ChannelWebhookModel)
async def update_channel_webhook(
    request: Request,
    id: str,
    webhook_id: str,
    form_data: ChannelWebhookForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    # Only channel managers can update webhooks
    if not await Channels.is_user_channel_manager(channel.id, user.id, db=db) and user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.UNAUTHORIZED)

    webhook = await Channels.get_webhook_by_id(webhook_id, db=db)
    if not webhook or webhook.channel_id != id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    updated = await Channels.update_webhook_by_id(webhook_id, form_data, db=db)
    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    await publish_event(
        request,
        EVENTS.CHANNEL_WEBHOOK_UPDATED,
        actor=user,
        subject_id=webhook_id,
        data={'channel_id': id, 'name': updated.name},
    )
    return updated


@router.delete('/{id}/webhooks/{webhook_id}/delete', response_model=bool)
async def delete_channel_webhook(
    request: Request,
    id: str,
    webhook_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_channels_access(request, user)
    channel = await Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    # Only channel managers can delete webhooks
    if not await Channels.is_user_channel_manager(channel.id, user.id, db=db) and user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.UNAUTHORIZED)

    webhook = await Channels.get_webhook_by_id(webhook_id, db=db)
    if not webhook or webhook.channel_id != id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    deleted = await Channels.delete_webhook_by_id(webhook_id, db=db)
    if deleted:
        await publish_event(
            request,
            EVENTS.CHANNEL_WEBHOOK_DELETED,
            actor=user,
            subject_id=webhook_id,
            data={'channel_id': id},
        )
    return deleted


############################
# Public Webhook Endpoint
############################


class WebhookMessageForm(BaseModel):
    content: str


@router.post('/webhooks/{webhook_id}/{token}')
async def post_webhook_message(
    request: Request,
    webhook_id: str,
    token: str,
    form_data: WebhookMessageForm,
    db: AsyncSession = Depends(get_async_session),
):
    """Public endpoint to post messages via webhook. No authentication required."""
    await check_channels_access(request)

    # Validate webhook
    webhook = await Channels.get_webhook_by_id_and_token(webhook_id, token, db=db)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.INVALID_URL,
        )

    channel = await Channels.get_channel_by_id(webhook.channel_id, db=db)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    # Create message with webhook identity stored in meta
    message = await Messages.insert_new_message(
        MessageForm(content=form_data.content, meta={'webhook': {'id': webhook.id}}),
        webhook.channel_id,
        webhook.user_id,  # Required for DB but webhook info in meta takes precedence
        db=db,
    )

    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Failed to create message'),
        )

    # Update last_used_at
    await Channels.update_webhook_last_used_at(webhook_id, db=db)

    # Get full message and emit event
    message = await Messages.get_message_by_id(message.id, db=db)

    event_data = {
        'channel_id': channel.id,
        'message_id': message.id,
        'data': {
            'type': 'message',
            'data': {
                **message.model_dump(),
                'user': {
                    'id': webhook.id,
                    'name': webhook.name,
                    'role': 'webhook',
                },
            },
        },
        'user': {
            'id': webhook.id,
            'name': webhook.name,
            'role': 'webhook',
        },
        'channel': channel.model_dump(),
    }

    await sio.emit(
        'events:channel',
        event_data,
        to=f'channel:{channel.id}',
    )

    await publish_event(
        request,
        EVENTS.MESSAGE_CREATED,
        actor={'id': webhook.id, 'name': webhook.name, 'role': 'webhook', 'type': 'webhook'},
        subject_id=message.id,
        source='channel_webhook',
        data={'channel_id': channel.id, 'content_preview': form_data.content[:300]},
    )
    return {'success': True, 'message_id': message.id}
