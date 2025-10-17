import json
import logging
from typing import Optional


from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from pydantic import BaseModel


from open_webui.socket.main import sio, get_user_ids_from_room
from open_webui.models.users import Users, UserNameResponse

from open_webui.models.groups import Groups
from open_webui.models.channels import (
    Channels,
    ChannelModel,
    ChannelForm,
    ChannelResponse,
)
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

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

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
# GetChannelById
############################


@router.get("/{id}", response_model=Optional[ChannelResponse])
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

    write_access = has_access(
        user.id, type="write", access_control=channel.access_control, strict=False
    )

    return ChannelResponse(
        **{
            **channel.model_dump(),
            "write_access": write_access or user.role == "admin",
        }
    )


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
    pass


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

        thread_replies = Messages.get_thread_replies_by_message_id(message.id)
        latest_thread_reply_at = (
            thread_replies[0].created_at if thread_replies else None
        )

        messages.append(
            MessageUserResponse(
                **{
                    **message.model_dump(),
                    "reply_count": len(thread_replies),
                    "latest_reply_at": latest_thread_reply_at,
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
    users = get_users_with_access("read", channel.access_control)

    for user in users:
        if user.id not in active_user_ids:
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


async def model_response_handler(request, channel, message, user):
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
                images = []
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

                    thread_message_files = thread_message.data.get("files", [])
                    for file in thread_message_files:
                        if file.get("type", "") == "image":
                            images.append(file.get("url", ""))

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
                    elif res.get("error", None):
                        await update_message_by_id(
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
        user.id, type="write", access_control=channel.access_control, strict=False
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        message = Messages.insert_new_message(form_data, channel.id, user.id)
        if message:
            message = Messages.get_message_by_id(message.id)
            event_data = {
                "channel_id": channel.id,
                "message_id": message.id,
                "data": {
                    "type": "message",
                    "data": message.model_dump(),
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
                parent_message = Messages.get_message_by_id(message.parent_id)

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
    id: str, message_id: str, form_data: ReactionForm, user=Depends(get_verified_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and not has_access(
        user.id, type="write", access_control=channel.access_control, strict=False
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
    id: str, message_id: str, form_data: ReactionForm, user=Depends(get_verified_user)
):
    channel = Channels.get_channel_by_id(id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and not has_access(
        user.id, type="write", access_control=channel.access_control, strict=False
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
        and not has_access(
            user.id, type="write", access_control=channel.access_control, strict=False
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        Messages.delete_message_by_id(message_id)
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
            parent_message = Messages.get_message_by_id(message.parent_id)

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
