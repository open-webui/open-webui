import json
import logging
import base64
import io
from typing import Optional


from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from fastapi.responses import Response, StreamingResponse, FileResponse
from pydantic import BaseModel
from pydantic import field_validator

from open_webui.socket.main import (
    emit_to_users,
    enter_room_for_users,
    sio,
    get_user_ids_from_room,
)
from open_webui.models.users import (
    UserIdNameResponse,
    UserIdNameStatusResponse,
    UserListResponse,
    UserModelResponse,
    Users,
    UserModel,
    UserNameResponse,
)

from open_webui.models.groups import Groups
from open_webui.models.channels import (
    Channels,
    ChannelModel,
    ChannelForm,
    ChannelResponse,
    CreateChannelForm,
    ChannelWebhookModel,
    ChannelWebhookForm,
)
from open_webui.models.access_grants import AccessGrants, has_public_read_access_grant
from open_webui.models.messages import (
    Messages,
    MessageModel,
    MessageResponse,
    MessageWithReactionsResponse,
    MessageForm,
)


from open_webui.utils.files import get_image_base64_from_file_id

from open_webui.config import ENABLE_ADMIN_CHAT_ACCESS, ENABLE_ADMIN_EXPORT
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import STATIC_DIR


from open_webui.utils.models import (
    get_all_models,
    get_filtered_models,
)
from open_webui.utils.chat import generate_chat_completion


from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_permission
from open_webui.utils.webhook import post_webhook
from open_webui.utils.channels import extract_mentions, replace_mentions
from open_webui.internal.db import get_session
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

router = APIRouter()


def channel_has_access(
    user_id: str,
    channel: ChannelModel,
    permission: str = "read",
    strict: bool = True,
    db: Optional[Session] = None,
) -> bool:
    if AccessGrants.has_access(
        user_id=user_id,
        resource_type="channel",
        resource_id=channel.id,
        permission=permission,
        db=db,
    ):
        return True

    if (
        not strict
        and permission == "write"
        and has_public_read_access_grant(channel.access_grants)
    ):
        return True

    return False


def get_channel_users_with_access(
    channel: ChannelModel, permission: str = "read", db: Optional[Session] = None
):
    return AccessGrants.get_users_with_access(
        resource_type="channel",
        resource_id=channel.id,
        permission=permission,
        db=db,
    )


def get_channel_permitted_group_and_user_ids(
    channel: ChannelModel, permission: str = "read"
) -> Optional[dict[str, list[str]]]:
    if permission == "read" and has_public_read_access_grant(channel.access_grants):
        return None

    user_ids = []
    group_ids = []

    for grant in channel.access_grants:
        if grant.permission != permission:
            continue
        if grant.principal_type == "group":
            group_ids.append(grant.principal_id)
        elif grant.principal_type == "user" and grant.principal_id != "*":
            user_ids.append(grant.principal_id)

    return {
        "user_ids": list(dict.fromkeys(user_ids)),
        "group_ids": list(dict.fromkeys(group_ids)),
    }


############################
# Channels Enabled Dependency
############################


def check_channels_access(request: Request, user: Optional[UserModel] = None):
    """Dependency to ensure channels are globally enabled."""
    if not request.app.state.config.ENABLE_CHANNELS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Channels are not enabled",
        )

    if user:
        if user.role != "admin" and not has_permission(
            user.id, "features.channels", request.app.state.config.USER_PERMISSIONS
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.UNAUTHORIZED,
            )


############################
# GetChatList
############################


class ChannelListItemResponse(ChannelModel):
    user_ids: Optional[list[str]] = None  # 'dm' channels only
    users: Optional[list[UserIdNameStatusResponse]] = None  # 'dm' channels only

    last_message_at: Optional[int] = None  # timestamp in epoch (time_ns)
    unread_count: int = 0


@router.get("/", response_model=list[ChannelListItemResponse])
async def get_channels(
    request: Request,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request, user)

    channels = Channels.get_channels_by_user_id(user.id, db=db)
    channel_list = []
    for channel in channels:
        last_message = Messages.get_last_message_by_channel_id(channel.id, db=db)
        last_message_at = last_message.created_at if last_message else None

        channel_member = Channels.get_member_by_channel_and_user_id(
            channel.id, user.id, db=db
        )
        unread_count = (
            Messages.get_unread_message_count(
                channel.id, user.id, channel_member.last_read_at, db=db
            )
            if channel_member
            else 0
        )

        user_ids = None
        users = None
        if channel.type == "dm":
            user_ids = [
                member.user_id
                for member in Channels.get_members_by_channel_id(channel.id, db=db)
            ]
            users = [
                UserIdNameStatusResponse(
                    **{
                        **user.model_dump(),
                        "is_active": Users.is_user_active(user.id, db=db),
                    }
                )
                for user in Users.get_users_by_user_ids(user_ids, db=db)
            ]

        channel_list.append(
            ChannelListItemResponse(
                **channel.model_dump(),
                user_ids=user_ids,
                users=users,
                last_message_at=last_message_at,
                unread_count=unread_count,
            )
        )

    return channel_list


@router.get("/list", response_model=list[ChannelModel])
async def get_all_channels(
    request: Request,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request)
    if user.role == "admin":
        return Channels.get_channels(db=db)
    return Channels.get_channels_by_user_id(user.id, db=db)


############################
# GetDMChannelByUserId
############################


@router.get("/users/{user_id}", response_model=Optional[ChannelModel])
async def get_dm_channel_by_user_id(
    request: Request,
    user_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request, user)
    try:
        existing_channel = Channels.get_dm_channel_by_user_ids(
            [user.id, user_id], db=db
        )
        if existing_channel:
            participant_ids = [
                member.user_id
                for member in Channels.get_members_by_channel_id(
                    existing_channel.id, db=db
                )
            ]

            await emit_to_users(
                "events:channel",
                {"data": {"type": "channel:created"}},
                participant_ids,
            )
            await enter_room_for_users(
                f"channel:{existing_channel.id}", participant_ids
            )

            Channels.update_member_active_status(
                existing_channel.id, user.id, True, db=db
            )
            return ChannelModel(**existing_channel.model_dump())

        channel = Channels.insert_new_channel(
            CreateChannelForm(
                type="dm",
                name="",
                user_ids=[user_id],
            ),
            user.id,
            db=db,
        )

        if channel:
            participant_ids = [
                member.user_id
                for member in Channels.get_members_by_channel_id(channel.id, db=db)
            ]

            await emit_to_users(
                "events:channel",
                {"data": {"type": "channel:created"}},
                participant_ids,
            )
            await enter_room_for_users(f"channel:{channel.id}", participant_ids)

            return ChannelModel(**channel.model_dump())
        else:
            raise Exception("Error creating channel")
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# CreateNewChannel
############################


@router.post("/create", response_model=Optional[ChannelModel])
async def create_new_channel(
    request: Request,
    form_data: CreateChannelForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request, user)

    if form_data.type not in ["group", "dm"] and user.role != "admin":
        # Only admins can create standard channels (joined by default)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    try:
        if form_data.type == "dm":
            existing_channel = Channels.get_dm_channel_by_user_ids(
                [user.id, *form_data.user_ids], db=db
            )
            if existing_channel:
                participant_ids = [
                    member.user_id
                    for member in Channels.get_members_by_channel_id(
                        existing_channel.id, db=db
                    )
                ]
                await emit_to_users(
                    "events:channel",
                    {"data": {"type": "channel:created"}},
                    participant_ids,
                )
                await enter_room_for_users(
                    f"channel:{existing_channel.id}", participant_ids
                )

                Channels.update_member_active_status(
                    existing_channel.id, user.id, True, db=db
                )
                return ChannelModel(**existing_channel.model_dump())

        channel = Channels.insert_new_channel(form_data, user.id, db=db)

        if channel:
            participant_ids = [
                member.user_id
                for member in Channels.get_members_by_channel_id(channel.id, db=db)
            ]

            await emit_to_users(
                "events:channel",
                {"data": {"type": "channel:created"}},
                participant_ids,
            )
            await enter_room_for_users(f"channel:{channel.id}", participant_ids)

            return ChannelModel(**channel.model_dump())
        else:
            raise Exception("Error creating channel")
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetChannelById
############################


class ChannelFullResponse(ChannelResponse):
    user_ids: Optional[list[str]] = None  # 'group'/'dm' channels only
    users: Optional[list[UserIdNameStatusResponse]] = None  # 'group'/'dm' channels only

    last_read_at: Optional[int] = None  # timestamp in epoch (time_ns)
    unread_count: int = 0


@router.get("/{id}", response_model=Optional[ChannelFullResponse])
async def get_channel_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request, user)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    user_ids = None
    users = None

    if channel.type in ["group", "dm"]:
        if not Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )

        user_ids = [
            member.user_id
            for member in Channels.get_members_by_channel_id(channel.id, db=db)
        ]

        users = [
            UserIdNameStatusResponse(
                **{
                    **user.model_dump(),
                    "is_active": Users.is_user_active(user.id, db=db),
                }
            )
            for user in Users.get_users_by_user_ids(user_ids, db=db)
        ]

        channel_member = Channels.get_member_by_channel_and_user_id(
            channel.id, user.id, db=db
        )
        unread_count = Messages.get_unread_message_count(
            channel.id, user.id, channel_member.last_read_at if channel_member else None
        )

        return ChannelFullResponse(
            **{
                **channel.model_dump(),
                "user_ids": user_ids,
                "users": users,
                "is_manager": Channels.is_user_channel_manager(
                    channel.id, user.id, db=db
                ),
                "write_access": True,
                "user_count": len(user_ids),
                "last_read_at": channel_member.last_read_at if channel_member else None,
                "unread_count": unread_count,
            }
        )
    else:
        if user.role != "admin" and not channel_has_access(
            user.id, channel, permission="read", db=db
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )

        write_access = channel_has_access(
            user.id,
            channel,
            permission="write",
            strict=False,
            db=db,
        )

        user_count = len(get_channel_users_with_access(channel, "read", db=db))

        channel_member = Channels.get_member_by_channel_and_user_id(
            channel.id, user.id, db=db
        )
        unread_count = Messages.get_unread_message_count(
            channel.id, user.id, channel_member.last_read_at if channel_member else None
        )

        return ChannelFullResponse(
            **{
                **channel.model_dump(),
                "user_ids": user_ids,
                "users": users,
                "is_manager": Channels.is_user_channel_manager(
                    channel.id, user.id, db=db
                ),
                "write_access": write_access or user.role == "admin",
                "user_count": user_count,
                "last_read_at": channel_member.last_read_at if channel_member else None,
                "unread_count": unread_count,
            }
        )


############################
# GetChannelMembersById
############################


PAGE_ITEM_COUNT = 30


@router.get("/{id}/members", response_model=UserListResponse)
async def get_channel_members_by_id(
    request: Request,
    id: str,
    query: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request, user)

    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    limit = PAGE_ITEM_COUNT

    page = max(1, page)
    skip = (page - 1) * limit

    if channel.type in ["group", "dm"]:
        if not Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )

    if channel.type == "dm":
        user_ids = [
            member.user_id
            for member in Channels.get_members_by_channel_id(channel.id, db=db)
        ]
        users = Users.get_users_by_user_ids(user_ids, db=db)
        total = len(users)

        return {
            "users": [
                UserModelResponse(
                    **user.model_dump(), is_active=Users.is_user_active(user.id, db=db)
                )
                for user in users
            ],
            "total": total,
        }
    else:
        filter = {}

        if query:
            filter["query"] = query
        if order_by:
            filter["order_by"] = order_by
        if direction:
            filter["direction"] = direction

        if channel.type == "group":
            filter["channel_id"] = channel.id
        else:
            filter["roles"] = ["!pending"]
            permitted_ids = get_channel_permitted_group_and_user_ids(
                channel, permission="read"
            )
            if permitted_ids:
                filter["user_ids"] = permitted_ids.get("user_ids")
                filter["group_ids"] = permitted_ids.get("group_ids")

        result = Users.get_users(filter=filter, skip=skip, limit=limit, db=db)

        users = result["users"]
        total = result["total"]

        return {
            "users": [
                UserModelResponse(
                    **user.model_dump(), is_active=Users.is_user_active(user.id, db=db)
                )
                for user in users
            ],
            "total": total,
        }


#################################################
# UpdateIsActiveMemberByIdAndUserId
#################################################


class UpdateActiveMemberForm(BaseModel):
    is_active: bool


@router.post("/{id}/members/active", response_model=bool)
async def update_is_active_member_by_id_and_user_id(
    request: Request,
    id: str,
    form_data: UpdateActiveMemberForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if not Channels.is_user_channel_member(channel.id, user.id, db=db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    Channels.update_member_active_status(
        channel.id, user.id, form_data.is_active, db=db
    )
    return True


#################################################
# AddMembersById
#################################################


class UpdateMembersForm(BaseModel):
    user_ids: list[str] = []
    group_ids: list[str] = []


@router.post("/{id}/update/members/add")
async def add_members_by_id(
    request: Request,
    id: str,
    form_data: UpdateMembersForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request, user)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if channel.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        memberships = Channels.add_members_to_channel(
            channel.id, user.id, form_data.user_ids, form_data.group_ids, db=db
        )

        return memberships
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


#################################################
#
#################################################


class RemoveMembersForm(BaseModel):
    user_ids: list[str] = []


@router.post("/{id}/update/members/remove")
async def remove_members_by_id(
    request: Request,
    id: str,
    form_data: RemoveMembersForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request, user)

    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if channel.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        deleted = Channels.remove_members_from_channel(
            channel.id, form_data.user_ids, db=db
        )

        return deleted
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# UpdateChannelById
############################


@router.post("/{id}/update", response_model=Optional[ChannelModel])
async def update_channel_by_id(
    request: Request,
    id: str,
    form_data: ChannelForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request, user)

    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if channel.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        channel = Channels.update_channel_by_id(id, form_data, db=db)
        return ChannelModel(**channel.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteChannelById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_channel_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request, user)

    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if channel.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        Channels.delete_channel_by_id(id, db=db)
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetChannelMessages
############################


class MessageUserResponse(MessageResponse):
    data: bool | None = None

    @field_validator("data", mode="before")
    def convert_data_to_bool(cls, v):
        # No data or not a dict → False
        if not isinstance(v, dict):
            return False

        # True if ANY value in the dict is non-empty
        return any(bool(val) for val in v.values())


@router.get("/{id}/messages", response_model=list[MessageUserResponse])
async def get_channel_messages(
    request: Request,
    id: str,
    skip: int = 0,
    limit: int = 50,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request, user)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if channel.type in ["group", "dm"]:
        if not Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )
    else:
        if user.role != "admin" and not channel_has_access(
            user.id, channel, permission="read", db=db
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )

        channel_member = Channels.join_channel(
            id, user.id, db=db
        )  # Ensure user is a member of the channel

    message_list = Messages.get_messages_by_channel_id(id, skip, limit, db=db)

    if not message_list:
        return []

    # Batch fetch all users in a single query (fixes N+1 problem)
    user_ids = list(set(m.user_id for m in message_list))
    users = {u.id: u for u in Users.get_users_by_user_ids(user_ids, db=db)}

    messages = []
    for message in message_list:
        thread_replies = Messages.get_thread_replies_by_message_id(message.id, db=db)
        latest_thread_reply_at = (
            thread_replies[0].created_at if thread_replies else None
        )

        # Use message.user if present (for webhooks), otherwise look up by user_id
        user_info = message.user
        if user_info is None and message.user_id in users:
            user_info = UserNameResponse(**users[message.user_id].model_dump())

        messages.append(
            MessageUserResponse(
                **{
                    **message.model_dump(),
                    "reply_count": len(thread_replies),
                    "latest_reply_at": latest_thread_reply_at,
                    "reactions": Messages.get_reactions_by_message_id(
                        message.id, db=db
                    ),
                    "user": user_info,
                }
            )
        )

    return messages


############################
# GetPinnedChannelMessages
############################

PAGE_ITEM_COUNT_PINNED = 20


@router.get("/{id}/messages/pinned", response_model=list[MessageWithReactionsResponse])
async def get_pinned_channel_messages(
    request: Request,
    id: str,
    page: int = 1,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if channel.type in ["group", "dm"]:
        if not Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )
    else:
        if user.role != "admin" and not channel_has_access(
            user.id, channel, permission="read", db=db
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )

    page = max(1, page)
    skip = (page - 1) * PAGE_ITEM_COUNT_PINNED
    limit = PAGE_ITEM_COUNT_PINNED

    message_list = Messages.get_pinned_messages_by_channel_id(id, skip, limit, db=db)

    if not message_list:
        return []

    # Batch fetch all users in a single query (fixes N+1 problem)
    user_ids = list(set(m.user_id for m in message_list))
    users = {u.id: u for u in Users.get_users_by_user_ids(user_ids, db=db)}

    messages = []
    for message in message_list:
        # Check for webhook identity in meta
        webhook_info = message.meta.get("webhook") if message.meta else None
        if webhook_info:
            user_info = UserNameResponse(
                id=webhook_info.get("id"),
                name=webhook_info.get("name"),
                role="webhook",
            )
        elif message.user_id in users:
            user_info = UserNameResponse(**users[message.user_id].model_dump())
        else:
            user_info = None

        messages.append(
            MessageWithReactionsResponse(
                **{
                    **message.model_dump(),
                    "reactions": Messages.get_reactions_by_message_id(
                        message.id, db=db
                    ),
                    "user": user_info,
                }
            )
        )

    return messages


############################
# PostNewMessage
############################


async def send_notification(
    name, webui_url, channel, message, active_user_ids, db=None
):
    users = get_channel_users_with_access(channel, "read", db=db)

    for user in users:
        if (user.id not in active_user_ids) and Channels.is_user_channel_member(
            channel.id, user.id, db=db
        ):
            if user.settings:
                webhook_url = user.settings.ui.get("notifications", {}).get(
                    "webhook_url", None
                )
                if webhook_url:
                    await post_webhook(
                        name,
                        webhook_url,
                        f"#{channel.name} - {webui_url}/channels/{channel.id}\n\n{message.content}",
                        {
                            "action": "channel",
                            "message": message.content,
                            "title": channel.name,
                            "url": f"{webui_url}/channels/{channel.id}",
                        },
                    )

    return True


async def model_response_handler(request, channel, message, user, db=None):
    MODELS = {
        model["id"]: model
        for model in get_filtered_models(await get_all_models(request, user=user), user)
    }

    mentions = extract_mentions(message.content)
    message_content = replace_mentions(message.content)

    model_mentions = {}

    # check if the message is a reply to a message sent by a model
    if (
        message.reply_to_message
        and message.reply_to_message.meta
        and message.reply_to_message.meta.get("model_id", None)
    ):
        model_id = message.reply_to_message.meta.get("model_id", None)
        model_mentions[model_id] = {"id": model_id, "id_type": "M"}

    # check if any of the mentions are models
    for mention in mentions:
        if mention["id_type"] == "M" and mention["id"] not in model_mentions:
            model_mentions[mention["id"]] = mention

    if not model_mentions:
        return False

    for mention in model_mentions.values():
        model_id = mention["id"]
        model = MODELS.get(model_id, None)

        if model:
            try:
                # reverse to get in chronological order
                thread_messages = Messages.get_messages_by_parent_id(
                    channel.id,
                    message.parent_id if message.parent_id else message.id,
                    db=db,
                )[::-1]

                response_message, channel = await new_message_handler(
                    request,
                    channel.id,
                    MessageForm(
                        **{
                            "parent_id": (
                                message.parent_id if message.parent_id else message.id
                            ),
                            "content": f"",
                            "data": {},
                            "meta": {
                                "model_id": model_id,
                                "model_name": model.get("name", model_id),
                            },
                        }
                    ),
                    user,
                    db,
                )

                thread_history = []
                images = []
                message_users = {}

                for thread_message in thread_messages:
                    message_user = None
                    if thread_message.user_id not in message_users:
                        message_user = Users.get_user_by_id(
                            thread_message.user_id, db=db
                        )
                        message_users[thread_message.user_id] = message_user
                    else:
                        message_user = message_users[thread_message.user_id]

                    if thread_message.meta and thread_message.meta.get(
                        "model_id", None
                    ):
                        # If the message was sent by a model, use the model name
                        message_model_id = thread_message.meta.get("model_id", None)
                        message_model = MODELS.get(message_model_id, None)
                        username = (
                            message_model.get("name", message_model_id)
                            if message_model
                            else message_model_id
                        )
                    else:
                        username = message_user.name if message_user else "Unknown"

                    thread_history.append(
                        f"{username}: {replace_mentions(thread_message.content)}"
                    )

                    thread_message_files = (thread_message.data or {}).get("files", [])
                    for file in thread_message_files:
                        if file.get("type", "") == "image":
                            images.append(file.get("url", ""))
                        elif file.get("content_type", "").startswith("image/"):
                            image = get_image_base64_from_file_id(file.get("id", ""))
                            if image:
                                images.append(image)

                thread_history_string = "\n\n".join(thread_history)
                system_message = {
                    "role": "system",
                    "content": f"You are {model.get('name', model_id)}, participating in a threaded conversation. Be concise and conversational."
                    + (
                        f"Here's the thread history:\n\n\n{thread_history_string}\n\n\nContinue the conversation naturally as {model.get('name', model_id)}, addressing the most recent message while being aware of the full context."
                        if thread_history
                        else ""
                    ),
                }

                content = f"{user.name if user else 'User'}: {message_content}"
                if images:
                    content = [
                        {
                            "type": "text",
                            "text": content,
                        },
                        *[
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image,
                                },
                            }
                            for image in images
                        ],
                    ]

                form_data = {
                    "model": model_id,
                    "messages": [
                        system_message,
                        {"role": "user", "content": content},
                    ],
                    "stream": False,
                }

                res = await generate_chat_completion(
                    request,
                    form_data=form_data,
                    user=user,
                )

                if res:
                    if res.get("choices", []) and len(res["choices"]) > 0:
                        await update_message_by_id(
                            request,
                            channel.id,
                            response_message.id,
                            MessageForm(
                                **{
                                    "content": res["choices"][0]["message"]["content"],
                                    "meta": {
                                        "done": True,
                                    },
                                }
                            ),
                            user,
                            db,
                        )
                    elif res.get("error", None):
                        await update_message_by_id(
                            request,
                            channel.id,
                            response_message.id,
                            MessageForm(
                                **{
                                    "content": f"Error: {res['error']}",
                                    "meta": {
                                        "done": True,
                                    },
                                }
                            ),
                            user,
                            db,
                        )
            except Exception as e:
                log.info(e)
                pass

    return True


async def new_message_handler(
    request: Request, id: str, form_data: MessageForm, user, db
):
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if channel.type in ["group", "dm"]:
        if not Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )
    else:
        if user.role != "admin" and not channel_has_access(
            user.id,
            channel,
            permission="write",
            strict=False,
            db=db,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )

    try:
        message = Messages.insert_new_message(form_data, channel.id, user.id, db=db)
        if message:
            if channel.type in ["group", "dm"]:
                members = Channels.get_members_by_channel_id(channel.id, db=db)
                for member in members:
                    if not member.is_active:
                        Channels.update_member_active_status(
                            channel.id, member.user_id, True, db=db
                        )

            message = Messages.get_message_by_id(message.id, db=db)
            event_data = {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {
                    "type": "message",
                    "data": {"temp_id": form_data.temp_id, **message.model_dump()},
                },
                "user": UserNameResponse(**user.model_dump()).model_dump(),
                "channel": channel.model_dump(),
            }

            await sio.emit(
                "events:channel",
                event_data,
                to=f"channel:{channel.id}",
            )

            if message.parent_id:
                # If this message is a reply, emit to the parent message as well
                parent_message = Messages.get_message_by_id(message.parent_id, db=db)

                if parent_message:
                    await sio.emit(
                        "events:channel",
                        {
                            "channel_id": channel.id,
                            "message_id": parent_message.id,
                            "data": {
                                "type": "message:reply",
                                "data": parent_message.model_dump(),
                            },
                            "user": UserNameResponse(**user.model_dump()).model_dump(),
                            "channel": channel.model_dump(),
                        },
                        to=f"channel:{channel.id}",
                    )
            return message, channel
        else:
            raise Exception("Error creating message")
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


@router.post("/{id}/messages/post", response_model=Optional[MessageModel])
async def post_new_message(
    request: Request,
    id: str,
    form_data: MessageForm,
    background_tasks: BackgroundTasks,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request)

    try:
        message, channel = await new_message_handler(request, id, form_data, user, db)
        try:
            if files := message.data.get("files", []):
                for file in files:
                    Channels.set_file_message_id_in_channel_by_id(
                        channel.id, file.get("id", ""), message.id, db=db
                    )
        except Exception as e:
            log.debug(e)

        active_user_ids = get_user_ids_from_room(f"channel:{channel.id}")

        # NOTE: We intentionally do NOT pass db to background_handler.
        # Background tasks should manage their own short-lived sessions to avoid
        # holding database connections during slow operations (e.g., LLM calls).
        async def background_handler():
            await model_response_handler(request, channel, message, user)
            await send_notification(
                request.app.state.WEBUI_NAME,
                request.app.state.config.WEBUI_URL,
                channel,
                message,
                active_user_ids,
            )

        background_tasks.add_task(background_handler)

        return message

    except HTTPException as e:
        raise e
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetChannelMessage
############################


@router.get("/{id}/messages/{message_id}", response_model=Optional[MessageResponse])
async def get_channel_message(
    request: Request,
    id: str,
    message_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if channel.type in ["group", "dm"]:
        if not Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )
    else:
        if user.role != "admin" and not channel_has_access(
            user.id, channel, permission="read", db=db
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )

    message = Messages.get_message_by_id(message_id, db=db)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    return MessageResponse(
        **{
            **message.model_dump(),
            "user": UserNameResponse(
                **Users.get_user_by_id(message.user_id, db=db).model_dump()
            ),
        }
    )


############################
# GetChannelMessageData
############################


@router.get("/{id}/messages/{message_id}/data", response_model=Optional[dict])
async def get_channel_message_data(
    request: Request,
    id: str,
    message_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if channel.type in ["group", "dm"]:
        if not Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )
    else:
        if user.role != "admin" and not channel_has_access(
            user.id, channel, permission="read", db=db
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )

    message = Messages.get_message_by_id(message_id, db=db)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    return message.data


############################
# PinChannelMessage
############################


class PinMessageForm(BaseModel):
    is_pinned: bool


@router.post(
    "/{id}/messages/{message_id}/pin", response_model=Optional[MessageUserResponse]
)
async def pin_channel_message(
    request: Request,
    id: str,
    message_id: str,
    form_data: PinMessageForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if channel.type in ["group", "dm"]:
        if not Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )
    else:
        if user.role != "admin" and not channel_has_access(
            user.id, channel, permission="read", db=db
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )

    message = Messages.get_message_by_id(message_id, db=db)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        Messages.update_is_pinned_by_id(message_id, form_data.is_pinned, user.id, db=db)
        message = Messages.get_message_by_id(message_id, db=db)
        return MessageUserResponse(
            **{
                **message.model_dump(),
                "user": UserNameResponse(
                    **Users.get_user_by_id(message.user_id, db=db).model_dump()
                ),
            }
        )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetChannelThreadMessages
############################


@router.get(
    "/{id}/messages/{message_id}/thread", response_model=list[MessageUserResponse]
)
async def get_channel_thread_messages(
    request: Request,
    id: str,
    message_id: str,
    skip: int = 0,
    limit: int = 50,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if channel.type in ["group", "dm"]:
        if not Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )
    else:
        if user.role != "admin" and not channel_has_access(
            user.id, channel, permission="read", db=db
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )

    message_list = Messages.get_messages_by_parent_id(
        id, message_id, skip, limit, db=db
    )

    if not message_list:
        return []

    # Batch fetch all users in a single query (fixes N+1 problem)
    user_ids = list(set(m.user_id for m in message_list))
    users = {u.id: u for u in Users.get_users_by_user_ids(user_ids, db=db)}

    messages = []
    for message in message_list:
        # Use message.user if present (for webhooks), otherwise look up by user_id
        user_info = message.user
        if user_info is None and message.user_id in users:
            user_info = UserNameResponse(**users[message.user_id].model_dump())

        messages.append(
            MessageUserResponse(
                **{
                    **message.model_dump(),
                    "reply_count": 0,
                    "latest_reply_at": None,
                    "reactions": Messages.get_reactions_by_message_id(
                        message.id, db=db
                    ),
                    "user": user_info,
                }
            )
        )

    return messages


############################
# UpdateMessageById
############################


@router.post(
    "/{id}/messages/{message_id}/update", response_model=Optional[MessageModel]
)
async def update_message_by_id(
    request: Request,
    id: str,
    message_id: str,
    form_data: MessageForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    message = Messages.get_message_by_id(message_id, db=db)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    if channel.type in ["group", "dm"]:
        if not Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )
    else:
        if (
            user.role != "admin"
            and message.user_id != user.id
            and not channel_has_access(user.id, channel, permission="read", db=db)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )

    try:
        message = Messages.update_message_by_id(message_id, form_data, db=db)
        message = Messages.get_message_by_id(message_id, db=db)

        if message:
            await sio.emit(
                "events:channel",
                {
                    "channel_id": channel.id,
                    "message_id": message.id,
                    "data": {
                        "type": "message:update",
                        "data": message.model_dump(),
                    },
                    "user": UserNameResponse(**user.model_dump()).model_dump(),
                    "channel": channel.model_dump(),
                },
                to=f"channel:{channel.id}",
            )

        return MessageModel(**message.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# AddReactionToMessage
############################


class ReactionForm(BaseModel):
    name: str


@router.post("/{id}/messages/{message_id}/reactions/add", response_model=bool)
async def add_reaction_to_message(
    request: Request,
    id: str,
    message_id: str,
    form_data: ReactionForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if channel.type in ["group", "dm"]:
        if not Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )
    else:
        if user.role != "admin" and not channel_has_access(
            user.id,
            channel,
            permission="write",
            strict=False,
            db=db,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )

    message = Messages.get_message_by_id(message_id, db=db)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        Messages.add_reaction_to_message(message_id, user.id, form_data.name, db=db)
        message = Messages.get_message_by_id(message_id, db=db)

        await sio.emit(
            "events:channel",
            {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {
                    "type": "message:reaction:add",
                    "data": {
                        **message.model_dump(),
                        "name": form_data.name,
                    },
                },
                "user": UserNameResponse(**user.model_dump()).model_dump(),
                "channel": channel.model_dump(),
            },
            to=f"channel:{channel.id}",
        )

        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# RemoveReactionById
############################


@router.post("/{id}/messages/{message_id}/reactions/remove", response_model=bool)
async def remove_reaction_by_id_and_user_id_and_name(
    request: Request,
    id: str,
    message_id: str,
    form_data: ReactionForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if channel.type in ["group", "dm"]:
        if not Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )
    else:
        if user.role != "admin" and not channel_has_access(
            user.id,
            channel,
            permission="write",
            strict=False,
            db=db,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )

    message = Messages.get_message_by_id(message_id, db=db)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        Messages.remove_reaction_by_id_and_user_id_and_name(
            message_id, user.id, form_data.name, db=db
        )

        message = Messages.get_message_by_id(message_id, db=db)

        await sio.emit(
            "events:channel",
            {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {
                    "type": "message:reaction:remove",
                    "data": {
                        **message.model_dump(),
                        "name": form_data.name,
                    },
                },
                "user": UserNameResponse(**user.model_dump()).model_dump(),
                "channel": channel.model_dump(),
            },
            to=f"channel:{channel.id}",
        )

        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteMessageById
############################


@router.delete("/{id}/messages/{message_id}/delete", response_model=bool)
async def delete_message_by_id(
    request: Request,
    id: str,
    message_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    message = Messages.get_message_by_id(message_id, db=db)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    if channel.type in ["group", "dm"]:
        if not Channels.is_user_channel_member(channel.id, user.id, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )
    else:
        if (
            user.role != "admin"
            and message.user_id != user.id
            and not channel_has_access(
                user.id,
                channel,
                permission="write",
                strict=False,
                db=db,
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
            )

    try:
        Messages.delete_message_by_id(message_id, db=db)
        await sio.emit(
            "events:channel",
            {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {
                    "type": "message:delete",
                    "data": {
                        **message.model_dump(),
                        "user": UserNameResponse(**user.model_dump()).model_dump(),
                    },
                },
                "user": UserNameResponse(**user.model_dump()).model_dump(),
                "channel": channel.model_dump(),
            },
            to=f"channel:{channel.id}",
        )

        if message.parent_id:
            # If this message is a reply, emit to the parent message as well
            parent_message = Messages.get_message_by_id(message.parent_id, db=db)

            if parent_message:
                await sio.emit(
                    "events:channel",
                    {
                        "channel_id": channel.id,
                        "message_id": parent_message.id,
                        "data": {
                            "type": "message:reply",
                            "data": parent_message.model_dump(),
                        },
                        "user": UserNameResponse(**user.model_dump()).model_dump(),
                        "channel": channel.model_dump(),
                    },
                    to=f"channel:{channel.id}",
                )

        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# Webhooks
############################


@router.get("/webhooks/{webhook_id}/profile/image")
def get_webhook_profile_image(webhook_id: str, user=Depends(get_verified_user)):
    """Get webhook profile image by webhook ID."""
    webhook = Channels.get_webhook_by_id(webhook_id)
    if not webhook:
        # Return default favicon if webhook not found
        return FileResponse(f"{STATIC_DIR}/favicon.png")

    if webhook.profile_image_url:
        # Check if it's url or base64
        if webhook.profile_image_url.startswith("http"):
            return Response(
                status_code=status.HTTP_302_FOUND,
                headers={"Location": webhook.profile_image_url},
            )
        elif webhook.profile_image_url.startswith("data:image"):
            try:
                header, base64_data = webhook.profile_image_url.split(",", 1)
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

    # Return default favicon if no profile image
    return FileResponse(f"{STATIC_DIR}/favicon.png")


@router.get("/{id}/webhooks", response_model=list[ChannelWebhookModel])
async def get_channel_webhooks(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Only channel managers can view webhooks
    if (
        not Channels.is_user_channel_manager(channel.id, user.id, db=db)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.UNAUTHORIZED
        )

    return Channels.get_webhooks_by_channel_id(id, db=db)


@router.post("/{id}/webhooks/create", response_model=ChannelWebhookModel)
async def create_channel_webhook(
    request: Request,
    id: str,
    form_data: ChannelWebhookForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Only channel managers can create webhooks
    if (
        not Channels.is_user_channel_manager(channel.id, user.id, db=db)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.UNAUTHORIZED
        )

    webhook = Channels.insert_webhook(id, user.id, form_data, db=db)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    return webhook


@router.post("/{id}/webhooks/{webhook_id}/update", response_model=ChannelWebhookModel)
async def update_channel_webhook(
    request: Request,
    id: str,
    webhook_id: str,
    form_data: ChannelWebhookForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Only channel managers can update webhooks
    if (
        not Channels.is_user_channel_manager(channel.id, user.id, db=db)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.UNAUTHORIZED
        )

    webhook = Channels.get_webhook_by_id(webhook_id, db=db)
    if not webhook or webhook.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    updated = Channels.update_webhook_by_id(webhook_id, form_data, db=db)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    return updated


@router.delete("/{id}/webhooks/{webhook_id}/delete", response_model=bool)
async def delete_channel_webhook(
    request: Request,
    id: str,
    webhook_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    check_channels_access(request)
    channel = Channels.get_channel_by_id(id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Only channel managers can delete webhooks
    if (
        not Channels.is_user_channel_manager(channel.id, user.id, db=db)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.UNAUTHORIZED
        )

    webhook = Channels.get_webhook_by_id(webhook_id, db=db)
    if not webhook or webhook.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    return Channels.delete_webhook_by_id(webhook_id, db=db)


############################
# Public Webhook Endpoint
############################


class WebhookMessageForm(BaseModel):
    content: str


@router.post("/webhooks/{webhook_id}/{token}")
async def post_webhook_message(
    request: Request,
    webhook_id: str,
    token: str,
    form_data: WebhookMessageForm,
    db: Session = Depends(get_session),
):
    """Public endpoint to post messages via webhook. No authentication required."""
    check_channels_access(request)

    # Validate webhook
    webhook = Channels.get_webhook_by_id_and_token(webhook_id, token, db=db)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook URL",
        )

    channel = Channels.get_channel_by_id(webhook.channel_id, db=db)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Create message with webhook identity stored in meta
    message = Messages.insert_new_message(
        MessageForm(content=form_data.content, meta={"webhook": {"id": webhook.id}}),
        webhook.channel_id,
        webhook.user_id,  # Required for DB but webhook info in meta takes precedence
        db=db,
    )

    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create message",
        )

    # Update last_used_at
    Channels.update_webhook_last_used_at(webhook_id, db=db)

    # Get full message and emit event
    message = Messages.get_message_by_id(message.id, db=db)

    event_data = {
        "channel_id": channel.id,
        "message_id": message.id,
        "data": {
            "type": "message",
            "data": {
                **message.model_dump(),
                "user": {
                    "id": webhook.id,
                    "name": webhook.name,
                    "role": "webhook",
                },
            },
        },
        "user": {
            "id": webhook.id,
            "name": webhook.name,
            "role": "webhook",
        },
        "channel": channel.model_dump(),
    }

    await sio.emit(
        "events:channel",
        event_data,
        to=f"channel:{channel.id}",
    )

    return {"success": True, "message_id": message.id}
