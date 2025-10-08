import asyncio
import json
import logging
from typing import Optional


from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from pydantic import BaseModel


from open_webui.socket.main import sio, get_user_ids_from_room, USER_POOL
from open_webui.models.users import Users, UserNameResponse

from open_webui.models.channels import Channels, ChannelModel, ChannelForm
from open_webui.models.messages import (
    Messages,
    MessageModel,
    MessageResponse,
    MessageForm,
)


from open_webui.config import ENABLE_ADMIN_CHAT_ACCESS, ENABLE_ADMIN_EXPORT
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS


from open_webui.utils.models import (
    get_all_models,
    get_filtered_models,
)
from open_webui.utils.chat import generate_chat_completion


from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access, get_users_with_access
from open_webui.utils.webhook import post_webhook
from open_webui.utils.channels import extract_mentions, replace_mentions
from open_webui.utils.email_notifications import (
    is_email_configured,
    send_channel_message_email,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

EMAIL_NOTIFICATION_DELAY_SECONDS = 600
PENDING_EMAIL_NOTIFICATIONS: dict[tuple[str, str, str], asyncio.Task] = {}


def _schedule_email_notifications(channel, message, recipients, sender):
    if not is_email_configured():
        return

    for recipient in recipients:
        key = (channel.id, message.id, recipient.id)
        if key in PENDING_EMAIL_NOTIFICATIONS:
            continue

        task = asyncio.create_task(
            _email_notification_task(channel, message, recipient, sender)
        )
        PENDING_EMAIL_NOTIFICATIONS[key] = task


async def _email_notification_task(channel, message, recipient, sender):
    key = (channel.id, message.id, recipient.id)
    try:
        await asyncio.sleep(EMAIL_NOTIFICATION_DELAY_SECONDS)
        active_user_ids = get_user_ids_from_room(f"channel:{channel.id}")
        if recipient.id in active_user_ids:
            return
        await send_channel_message_email(recipient, sender, channel, message)
    except Exception as exc:
        log.exception(
            "Failed to send delayed email notification for channel %s message %s: %s",
            channel.id,
            message.id,
            exc,
        )
    finally:
        PENDING_EMAIL_NOTIFICATIONS.pop(key, None)


class DirectChannelForm(BaseModel):
    user_id: str


############################
# GetChatList
############################


@router.get("/", response_model=list[ChannelModel])
async def get_channels(user=Depends(get_verified_user)):
    return Channels.get_channels_by_user_id(user.id)


@router.get("/list", response_model=list[ChannelModel])
async def get_all_channels(user=Depends(get_verified_user)):
    if user.role == "admin":
        return Channels.get_channels()
    return Channels.get_channels_by_user_id(user.id)


############################
# CreateNewChannel
############################


@router.post("/create", response_model=Optional[ChannelModel])
async def create_new_channel(form_data: ChannelForm, user=Depends(get_admin_user)):
    try:
        channel = Channels.insert_new_channel(None, form_data, user.id)
        return ChannelModel(**channel.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# StartDirectChannel
############################


@router.post("/direct/start", response_model=ChannelModel)
async def start_direct_channel(
    form_data: DirectChannelForm, user=Depends(get_verified_user)
):
    if form_data.user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    participant = Users.get_user_by_id(form_data.user_id)
    if not participant or participant.role == "pending":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    participant_ids = sorted([user.id, participant.id])
    channel_key = "-".join(participant_ids)
    channel_name = f"direct-{channel_key}"

    channel = Channels.get_channel_by_name(channel_name)
    if not channel:
        access_control = {
            "read": {"user_ids": participant_ids, "group_ids": []},
            "write": {"user_ids": participant_ids, "group_ids": []},
            "admin": {"user_ids": participant_ids, "group_ids": []},
        }

        meta = {
            "direct": {
                "key": channel_key,
                "participant_ids": participant_ids,
                "participants": [
                    UserNameResponse(**user.model_dump()).model_dump(),
                    UserNameResponse(**participant.model_dump()).model_dump(),
                ],
            }
        }

        channel_form = ChannelForm(
            name=channel_name,
            description=f"Direct conversation between {user.name} and {participant.name}",
            access_control=access_control,
            meta=meta,
            data={"direct": True},
        )

        try:
            channel = Channels.insert_new_channel("direct", channel_form, user.id)
        except Exception as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(),
            )

    channel = Channels.touch_channel_by_id(channel.id) or channel
    channel_payload = channel.model_dump()
    initiator = UserNameResponse(**user.model_dump()).model_dump()

    for participant_user in [user, participant]:
        for sid in USER_POOL.get(participant_user.id, []):
            await sio.enter_room(sid, f"channel:{channel.id}")
            await sio.emit(
                "channel-events",
                {
                    "channel_id": channel.id,
                    "message_id": None,
                    "data": {
                        "type": "channel:created",
                        "data": channel_payload,
                    },
                    "user": initiator,
                    "channel": channel_payload,
                },
                to=sid,
            )

    return ChannelModel(**channel_payload)


############################
# GetChannelById
############################


@router.get("/{id}", response_model=Optional[ChannelModel])
async def get_channel_by_id(id: str, user=Depends(get_verified_user)):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and not has_access(
        user.id, type="read", access_control=channel.access_control
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    return ChannelModel(**channel.model_dump())


############################
# UpdateChannelById
############################


@router.post("/{id}/update", response_model=Optional[ChannelModel])
async def update_channel_by_id(
    id: str, form_data: ChannelForm, user=Depends(get_admin_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    try:
        channel = Channels.update_channel_by_id(id, form_data)
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
async def delete_channel_by_id(id: str, user=Depends(get_admin_user)):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    try:
        Channels.delete_channel_by_id(id)
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
    user: UserNameResponse


@router.get("/{id}/messages", response_model=list[MessageUserResponse])
async def get_channel_messages(
    id: str, skip: int = 0, limit: int = 50, user=Depends(get_verified_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and not has_access(
        user.id, type="read", access_control=channel.access_control
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    message_list = Messages.get_messages_by_channel_id(id, skip, limit)
    users = {}

    messages = []
    for message in message_list:
        if message.user_id not in users:
            user = Users.get_user_by_id(message.user_id)
            users[message.user_id] = user

        replies = Messages.get_replies_by_message_id(message.id)
        latest_reply_at = replies[0].created_at if replies else None

        messages.append(
            MessageUserResponse(
                **{
                    **message.model_dump(),
                    "reply_count": len(replies),
                    "latest_reply_at": latest_reply_at,
                    "reactions": Messages.get_reactions_by_message_id(message.id),
                    "user": UserNameResponse(**users[message.user_id].model_dump()),
                }
            )
        )

    return messages


############################
# PostNewMessage
############################


async def send_notification(name, webui_url, channel, message, active_user_ids):
    recipients = get_users_with_access("read", channel.access_control)
    active_ids = set(active_user_ids or [])
    sender = Users.get_user_by_id(message.user_id)
    email_candidates = []

    for recipient in recipients:
        if recipient.id == message.user_id:
            continue

        is_active = recipient.id in active_ids

        if not is_active and recipient.settings:
            webhook_url = recipient.settings.ui.get("notifications", {}).get(
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

        if not is_active and recipient.email:
            email_candidates.append(recipient)

    if email_candidates:
        _schedule_email_notifications(channel, message, email_candidates, sender)

    return True


async def model_response_handler(request, channel, message, user):
    MODELS = {
        model["id"]: model
        for model in get_filtered_models(await get_all_models(request, user=user), user)
    }

    mentions = extract_mentions(message.content)
    message_content = replace_mentions(message.content)

    # check if any of the mentions are models
    model_mentions = [mention for mention in mentions if mention["id_type"] == "M"]
    if not model_mentions:
        return False

    for mention in model_mentions:
        model_id = mention["id"]
        model = MODELS.get(model_id, None)

        if model:
            try:
                # reverse to get in chronological order
                thread_messages = Messages.get_messages_by_parent_id(
                    channel.id,
                    message.parent_id if message.parent_id else message.id,
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
                )

                thread_history = []
                message_users = {}

                for thread_message in thread_messages:
                    message_user = None
                    if thread_message.user_id not in message_users:
                        message_user = Users.get_user_by_id(thread_message.user_id)
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

                system_message = {
                    "role": "system",
                    "content": f"You are {model.get('name', model_id)}, an AI assistant participating in a threaded conversation. Be helpful, concise, and conversational."
                    + (
                        f"Here's the thread history:\n\n{''.join([f'{msg}' for msg in thread_history])}\n\nContinue the conversation naturally, addressing the most recent message while being aware of the full context."
                        if thread_history
                        else ""
                    ),
                }

                form_data = {
                    "model": model_id,
                    "messages": [
                        system_message,
                        {
                            "role": "user",
                            "content": f"{user.name if user else 'User'}: {message_content}",
                        },
                    ],
                    "stream": False,
                }

                res = await generate_chat_completion(
                    request,
                    form_data=form_data,
                    user=user,
                )

                if res:
                    await update_message_by_id(
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
                    )
            except Exception as e:
                log.info(e)
                pass

    return True


async def new_message_handler(
    request: Request, id: str, form_data: MessageForm, user=Depends(get_verified_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and not has_access(
        user.id, type="read", access_control=channel.access_control
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        message = Messages.insert_new_message(form_data, channel.id, user.id)

        if message:
            updated_channel = Channels.touch_channel_by_id(channel.id)
            if updated_channel:
                channel = updated_channel

            event_data = {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {
                    "type": "message",
                    "data": MessageUserResponse(
                        **{
                            **message.model_dump(),
                            "reply_count": 0,
                            "latest_reply_at": None,
                            "reactions": Messages.get_reactions_by_message_id(
                                message.id
                            ),
                            "user": UserNameResponse(**user.model_dump()),
                        }
                    ).model_dump(),
                },
                "user": UserNameResponse(**user.model_dump()).model_dump(),
                "channel": channel.model_dump(),
            }

            await sio.emit(
                "channel-events",
                event_data,
                to=f"channel:{channel.id}",
            )

            if message.parent_id:
                # If this message is a reply, emit to the parent message as well
                parent_message = Messages.get_message_by_id(message.parent_id)

                if parent_message:
                    await sio.emit(
                        "channel-events",
                        {
                            "channel_id": channel.id,
                            "message_id": parent_message.id,
                            "data": {
                                "type": "message:reply",
                                "data": MessageUserResponse(
                                    **{
                                        **parent_message.model_dump(),
                                        "user": UserNameResponse(
                                            **Users.get_user_by_id(
                                                parent_message.user_id
                                            ).model_dump()
                                        ),
                                    }
                                ).model_dump(),
                            },
                            "user": UserNameResponse(**user.model_dump()).model_dump(),
                            "channel": channel.model_dump(),
                        },
                        to=f"channel:{channel.id}",
                    )
        return MessageModel(**message.model_dump()), channel
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
):

    try:
        message, channel = await new_message_handler(request, id, form_data, user)
        active_user_ids = get_user_ids_from_room(f"channel:{channel.id}")

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


@router.get("/{id}/messages/{message_id}", response_model=Optional[MessageUserResponse])
async def get_channel_message(
    id: str, message_id: str, user=Depends(get_verified_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and not has_access(
        user.id, type="read", access_control=channel.access_control
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    message = Messages.get_message_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    return MessageUserResponse(
        **{
            **message.model_dump(),
            "user": UserNameResponse(
                **Users.get_user_by_id(message.user_id).model_dump()
            ),
        }
    )


############################
# GetChannelThreadMessages
############################


@router.get(
    "/{id}/messages/{message_id}/thread", response_model=list[MessageUserResponse]
)
async def get_channel_thread_messages(
    id: str,
    message_id: str,
    skip: int = 0,
    limit: int = 50,
    user=Depends(get_verified_user),
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and not has_access(
        user.id, type="read", access_control=channel.access_control
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    message_list = Messages.get_messages_by_parent_id(id, message_id, skip, limit)
    users = {}

    messages = []
    for message in message_list:
        if message.user_id not in users:
            user = Users.get_user_by_id(message.user_id)
            users[message.user_id] = user

        messages.append(
            MessageUserResponse(
                **{
                    **message.model_dump(),
                    "reply_count": 0,
                    "latest_reply_at": None,
                    "reactions": Messages.get_reactions_by_message_id(message.id),
                    "user": UserNameResponse(**users[message.user_id].model_dump()),
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
    id: str, message_id: str, form_data: MessageForm, user=Depends(get_verified_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    message = Messages.get_message_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    if (
        user.role != "admin"
        and message.user_id != user.id
        and not has_access(user.id, type="read", access_control=channel.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        message = Messages.update_message_by_id(message_id, form_data)
        message = Messages.get_message_by_id(message_id)

        if message:
            await sio.emit(
                "channel-events",
                {
                    "channel_id": channel.id,
                    "message_id": message.id,
                    "data": {
                        "type": "message:update",
                        "data": MessageUserResponse(
                            **{
                                **message.model_dump(),
                                "user": UserNameResponse(
                                    **user.model_dump()
                                ).model_dump(),
                            }
                        ).model_dump(),
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
    id: str, message_id: str, form_data: ReactionForm, user=Depends(get_verified_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and not has_access(
        user.id, type="read", access_control=channel.access_control
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    message = Messages.get_message_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        Messages.add_reaction_to_message(message_id, user.id, form_data.name)
        message = Messages.get_message_by_id(message_id)

        await sio.emit(
            "channel-events",
            {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {
                    "type": "message:reaction:add",
                    "data": {
                        **message.model_dump(),
                        "user": UserNameResponse(
                            **Users.get_user_by_id(message.user_id).model_dump()
                        ).model_dump(),
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
    id: str, message_id: str, form_data: ReactionForm, user=Depends(get_verified_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and not has_access(
        user.id, type="read", access_control=channel.access_control
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    message = Messages.get_message_by_id(message_id)
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
            message_id, user.id, form_data.name
        )

        message = Messages.get_message_by_id(message_id)

        await sio.emit(
            "channel-events",
            {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {
                    "type": "message:reaction:remove",
                    "data": {
                        **message.model_dump(),
                        "user": UserNameResponse(
                            **Users.get_user_by_id(message.user_id).model_dump()
                        ).model_dump(),
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
    id: str, message_id: str, user=Depends(get_verified_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    message = Messages.get_message_by_id(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if message.channel_id != id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )

    if (
        user.role != "admin"
        and message.user_id != user.id
        and not has_access(user.id, type="read", access_control=channel.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        Messages.delete_message_by_id(message_id)
        await sio.emit(
            "channel-events",
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
            parent_message = Messages.get_message_by_id(message.parent_id)

            if parent_message:
                await sio.emit(
                    "channel-events",
                    {
                        "channel_id": channel.id,
                        "message_id": parent_message.id,
                        "data": {
                            "type": "message:reply",
                            "data": MessageUserResponse(
                                **{
                                    **parent_message.model_dump(),
                                    "user": UserNameResponse(
                                        **Users.get_user_by_id(
                                            parent_message.user_id
                                        ).model_dump()
                                    ),
                                }
                            ).model_dump(),
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
