import json
import logging
from typing import Optional


from open_webui.socket.main import get_event_emitter
from open_webui.models.chats import (
    ChatForm,
    ChatImportForm,
    ChatResponse,
    Chats,
    ChatTitleIdResponse,
)
from open_webui.models.tags import TagModel, Tags
from open_webui.models.folders import Folders

from open_webui.config import ENABLE_ADMIN_CHAT_ACCESS, ENABLE_ADMIN_EXPORT
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel


from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_permission

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

############################
# GetChatList
############################


@router.get("/", response_model=list[ChatTitleIdResponse])
@router.get("/list", response_model=list[ChatTitleIdResponse])
def get_session_user_chat_list(
    user=Depends(get_verified_user),
    page: Optional[int] = None,
    include_pinned: Optional[bool] = False,
    include_folders: Optional[bool] = False,
):
    try:
        if page is not None:
            limit = 60
            skip = (page - 1) * limit

            return Chats.get_chat_title_id_list_by_user_id(
                user.id,
                include_folders=include_folders,
                include_pinned=include_pinned,
                skip=skip,
                limit=limit,
            )
        else:
            return Chats.get_chat_title_id_list_by_user_id(
                user.id, include_folders=include_folders, include_pinned=include_pinned
            )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteAllChats
############################


@router.delete("/", response_model=bool)
async def delete_all_user_chats(request: Request, user=Depends(get_verified_user)):

    if user.role == "user" and not has_permission(
        user.id, "chat.delete", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = Chats.delete_chats_by_user_id(user.id)
    return result


############################
# GetUserChatList
############################


@router.get("/list/user/{user_id}", response_model=list[ChatTitleIdResponse])
async def get_user_chat_list_by_user_id(
    user_id: str,
    page: Optional[int] = None,
    query: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    user=Depends(get_admin_user),
):
    if not ENABLE_ADMIN_CHAT_ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if page is None:
        page = 1

    limit = 60
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter["query"] = query
    if order_by:
        filter["order_by"] = order_by
    if direction:
        filter["direction"] = direction

    return Chats.get_chat_list_by_user_id(
        user_id, include_archived=True, filter=filter, skip=skip, limit=limit
    )


############################
# CreateNewChat
############################


@router.post("/new", response_model=Optional[ChatResponse])
async def create_new_chat(form_data: ChatForm, user=Depends(get_verified_user)):
    try:
        chat = Chats.insert_new_chat(user.id, form_data)
        return ChatResponse(**chat.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# ImportChat
############################


@router.post("/import", response_model=Optional[ChatResponse])
async def import_chat(form_data: ChatImportForm, user=Depends(get_verified_user)):
    try:
        chat = Chats.import_chat(user.id, form_data)
        if chat:
            tags = chat.meta.get("tags", [])
            for tag_id in tags:
                tag_id = tag_id.replace(" ", "_").lower()
                tag_name = " ".join([word.capitalize() for word in tag_id.split("_")])
                if (
                    tag_id != "none"
                    and Tags.get_tag_by_name_and_user_id(tag_name, user.id) is None
                ):
                    Tags.insert_new_tag(tag_name, user.id)

        return ChatResponse(**chat.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetChats
############################


@router.get("/search", response_model=list[ChatTitleIdResponse])
def search_user_chats(
    text: str, page: Optional[int] = None, user=Depends(get_verified_user)
):
    if page is None:
        page = 1

    limit = 60
    skip = (page - 1) * limit

    chat_list = [
        ChatTitleIdResponse(**chat.model_dump())
        for chat in Chats.get_chats_by_user_id_and_search_text(
            user.id, text, skip=skip, limit=limit
        )
    ]

    # Delete tag if no chat is found
    words = text.strip().split(" ")
    if page == 1 and len(words) == 1 and words[0].startswith("tag:"):
        tag_id = words[0].replace("tag:", "")
        if len(chat_list) == 0:
            if Tags.get_tag_by_name_and_user_id(tag_id, user.id):
                log.debug(f"deleting tag: {tag_id}")
                Tags.delete_tag_by_name_and_user_id(tag_id, user.id)

    return chat_list


############################
# GetChatsByFolderId
############################


@router.get("/folder/{folder_id}", response_model=list[ChatResponse])
async def get_chats_by_folder_id(folder_id: str, user=Depends(get_verified_user)):
    folder_ids = [folder_id]
    children_folders = Folders.get_children_folders_by_id_and_user_id(
        folder_id, user.id
    )
    if children_folders:
        folder_ids.extend([folder.id for folder in children_folders])

    return [
        ChatResponse(**chat.model_dump())
        for chat in Chats.get_chats_by_folder_ids_and_user_id(folder_ids, user.id)
    ]


@router.get("/folder/{folder_id}/list")
async def get_chat_list_by_folder_id(
    folder_id: str, page: Optional[int] = 1, user=Depends(get_verified_user)
):
    try:
        limit = 60
        skip = (page - 1) * limit

        return [
            {"title": chat.title, "id": chat.id, "updated_at": chat.updated_at}
            for chat in Chats.get_chats_by_folder_id_and_user_id(
                folder_id, user.id, skip=skip, limit=limit
            )
        ]

    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetPinnedChats
############################


@router.get("/pinned", response_model=list[ChatTitleIdResponse])
async def get_user_pinned_chats(user=Depends(get_verified_user)):
    return [
        ChatTitleIdResponse(**chat.model_dump())
        for chat in Chats.get_pinned_chats_by_user_id(user.id)
    ]


############################
# GetChats
############################


@router.get("/all", response_model=list[ChatResponse])
async def get_user_chats(user=Depends(get_verified_user)):
    return [
        ChatResponse(**chat.model_dump())
        for chat in Chats.get_chats_by_user_id(user.id)
    ]


############################
# GetArchivedChats
############################


@router.get("/all/archived", response_model=list[ChatResponse])
async def get_user_archived_chats(user=Depends(get_verified_user)):
    return [
        ChatResponse(**chat.model_dump())
        for chat in Chats.get_archived_chats_by_user_id(user.id)
    ]


############################
# GetAllTags
############################


@router.get("/all/tags", response_model=list[TagModel])
async def get_all_user_tags(user=Depends(get_verified_user)):
    try:
        tags = Tags.get_tags_by_user_id(user.id)
        return tags
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetAllChatsInDB
############################


@router.get("/all/db", response_model=list[ChatResponse])
async def get_all_user_chats_in_db(user=Depends(get_admin_user)):
    if not ENABLE_ADMIN_EXPORT:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return [ChatResponse(**chat.model_dump()) for chat in Chats.get_chats()]


############################
# GetArchivedChats
############################


@router.get("/archived", response_model=list[ChatTitleIdResponse])
async def get_archived_session_user_chat_list(
    page: Optional[int] = None,
    query: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    user=Depends(get_verified_user),
):
    if page is None:
        page = 1

    limit = 60
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter["query"] = query
    if order_by:
        filter["order_by"] = order_by
    if direction:
        filter["direction"] = direction

    chat_list = [
        ChatTitleIdResponse(**chat.model_dump())
        for chat in Chats.get_archived_chat_list_by_user_id(
            user.id,
            filter=filter,
            skip=skip,
            limit=limit,
        )
    ]

    return chat_list


############################
# ArchiveAllChats
############################


@router.post("/archive/all", response_model=bool)
async def archive_all_chats(user=Depends(get_verified_user)):
    return Chats.archive_all_chats_by_user_id(user.id)


############################
# UnarchiveAllChats
############################


@router.post("/unarchive/all", response_model=bool)
async def unarchive_all_chats(user=Depends(get_verified_user)):
    return Chats.unarchive_all_chats_by_user_id(user.id)


############################
# GetSharedChatById
############################


@router.get("/share/{share_id}", response_model=Optional[ChatResponse])
async def get_shared_chat_by_id(share_id: str, user=Depends(get_verified_user)):
    if user.role == "pending":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role == "user" or (user.role == "admin" and not ENABLE_ADMIN_CHAT_ACCESS):
        chat = Chats.get_chat_by_share_id(share_id)
    elif user.role == "admin" and ENABLE_ADMIN_CHAT_ACCESS:
        chat = Chats.get_chat_by_id(share_id)

    if chat:
        return ChatResponse(**chat.model_dump())

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )


############################
# GetChatsByTags
############################


class TagForm(BaseModel):
    name: str


class TagFilterForm(TagForm):
    skip: Optional[int] = 0
    limit: Optional[int] = 50


@router.post("/tags", response_model=list[ChatTitleIdResponse])
async def get_user_chat_list_by_tag_name(
    form_data: TagFilterForm, user=Depends(get_verified_user)
):
    chats = Chats.get_chat_list_by_user_id_and_tag_name(
        user.id, form_data.name, form_data.skip, form_data.limit
    )
    if len(chats) == 0:
        Tags.delete_tag_by_name_and_user_id(form_data.name, user.id)

    return chats


############################
# GetChatById
############################


@router.get("/{id}", response_model=Optional[ChatResponse])
async def get_chat_by_id(id: str, user=Depends(get_verified_user)):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)

    if chat:
        return ChatResponse(**chat.model_dump())

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )


############################
# UpdateChatById
############################


@router.post("/{id}", response_model=Optional[ChatResponse])
async def update_chat_by_id(
    id: str, form_data: ChatForm, user=Depends(get_verified_user)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        updated_chat = {**chat.chat, **form_data.chat}
        chat = Chats.update_chat_by_id(id, updated_chat)
        return ChatResponse(**chat.model_dump())
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


############################
# UpdateChatMessageById
############################
class MessageForm(BaseModel):
    content: str


@router.post("/{id}/messages/{message_id}", response_model=Optional[ChatResponse])
async def update_chat_message_by_id(
    id: str, message_id: str, form_data: MessageForm, user=Depends(get_verified_user)
):
    chat = Chats.get_chat_by_id(id)

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if chat.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    chat = Chats.upsert_message_to_chat_by_id_and_message_id(
        id,
        message_id,
        {
            "content": form_data.content,
        },
    )

    event_emitter = get_event_emitter(
        {
            "user_id": user.id,
            "chat_id": id,
            "message_id": message_id,
        },
        False,
    )

    if event_emitter:
        await event_emitter(
            {
                "type": "chat:message",
                "data": {
                    "chat_id": id,
                    "message_id": message_id,
                    "content": form_data.content,
                },
            }
        )

    return ChatResponse(**chat.model_dump())


############################
# SendChatMessageEventById
############################
class EventForm(BaseModel):
    type: str
    data: dict


@router.post("/{id}/messages/{message_id}/event", response_model=Optional[bool])
async def send_chat_message_event_by_id(
    id: str, message_id: str, form_data: EventForm, user=Depends(get_verified_user)
):
    chat = Chats.get_chat_by_id(id)

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if chat.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    event_emitter = get_event_emitter(
        {
            "user_id": user.id,
            "chat_id": id,
            "message_id": message_id,
        }
    )

    try:
        if event_emitter:
            await event_emitter(form_data.model_dump())
        else:
            return False
        return True
    except:
        return False


############################
# DeleteChatById
############################


@router.delete("/{id}", response_model=bool)
async def delete_chat_by_id(request: Request, id: str, user=Depends(get_verified_user)):
    if user.role == "admin":
        chat = Chats.get_chat_by_id(id)
        for tag in chat.meta.get("tags", []):
            if Chats.count_chats_by_tag_name_and_user_id(tag, user.id) == 1:
                Tags.delete_tag_by_name_and_user_id(tag, user.id)

        result = Chats.delete_chat_by_id(id)

        return result
    else:
        if not has_permission(
            user.id, "chat.delete", request.app.state.config.USER_PERMISSIONS
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )

        chat = Chats.get_chat_by_id(id)
        for tag in chat.meta.get("tags", []):
            if Chats.count_chats_by_tag_name_and_user_id(tag, user.id) == 1:
                Tags.delete_tag_by_name_and_user_id(tag, user.id)

        result = Chats.delete_chat_by_id_and_user_id(id, user.id)
        return result


############################
# GetPinnedStatusById
############################


@router.get("/{id}/pinned", response_model=Optional[bool])
async def get_pinned_status_by_id(id: str, user=Depends(get_verified_user)):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        return chat.pinned
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# PinChatById
############################


@router.post("/{id}/pin", response_model=Optional[ChatResponse])
async def pin_chat_by_id(id: str, user=Depends(get_verified_user)):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        chat = Chats.toggle_chat_pinned_by_id(id)
        return chat
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# CloneChat
############################


class CloneForm(BaseModel):
    title: Optional[str] = None


@router.post("/{id}/clone", response_model=Optional[ChatResponse])
async def clone_chat_by_id(
    form_data: CloneForm, id: str, user=Depends(get_verified_user)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        updated_chat = {
            **chat.chat,
            "originalChatId": chat.id,
            "branchPointMessageId": chat.chat["history"]["currentId"],
            "title": form_data.title if form_data.title else f"Clone of {chat.title}",
        }

        chat = Chats.import_chat(
            user.id,
            ChatImportForm(
                **{
                    "chat": updated_chat,
                    "meta": chat.meta,
                    "pinned": chat.pinned,
                    "folder_id": chat.folder_id,
                }
            ),
        )

        return ChatResponse(**chat.model_dump())
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# CloneSharedChatById
############################


@router.post("/{id}/clone/shared", response_model=Optional[ChatResponse])
async def clone_shared_chat_by_id(id: str, user=Depends(get_verified_user)):

    if user.role == "admin":
        chat = Chats.get_chat_by_id(id)
    else:
        chat = Chats.get_chat_by_share_id(id)

    if chat:
        updated_chat = {
            **chat.chat,
            "originalChatId": chat.id,
            "branchPointMessageId": chat.chat["history"]["currentId"],
            "title": f"Clone of {chat.title}",
        }

        chat = Chats.import_chat(
            user.id,
            ChatImportForm(
                **{
                    "chat": updated_chat,
                    "meta": chat.meta,
                    "pinned": chat.pinned,
                    "folder_id": chat.folder_id,
                }
            ),
        )
        return ChatResponse(**chat.model_dump())
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# ArchiveChat
############################


@router.post("/{id}/archive", response_model=Optional[ChatResponse])
async def archive_chat_by_id(id: str, user=Depends(get_verified_user)):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        chat = Chats.toggle_chat_archive_by_id(id)

        # Delete tags if chat is archived
        if chat.archived:
            for tag_id in chat.meta.get("tags", []):
                if Chats.count_chats_by_tag_name_and_user_id(tag_id, user.id) == 0:
                    log.debug(f"deleting tag: {tag_id}")
                    Tags.delete_tag_by_name_and_user_id(tag_id, user.id)
        else:
            for tag_id in chat.meta.get("tags", []):
                tag = Tags.get_tag_by_name_and_user_id(tag_id, user.id)
                if tag is None:
                    log.debug(f"inserting tag: {tag_id}")
                    tag = Tags.insert_new_tag(tag_id, user.id)

        return ChatResponse(**chat.model_dump())
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# ShareChatById
############################


@router.post("/{id}/share", response_model=Optional[ChatResponse])
async def share_chat_by_id(request: Request, id: str, user=Depends(get_verified_user)):
    if (user.role != "admin") and (
        not has_permission(
            user.id, "chat.share", request.app.state.config.USER_PERMISSIONS
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    chat = Chats.get_chat_by_id_and_user_id(id, user.id)

    if chat:
        if chat.share_id:
            shared_chat = Chats.update_shared_chat_by_chat_id(chat.id)
            return ChatResponse(**shared_chat.model_dump())

        shared_chat = Chats.insert_shared_chat_by_chat_id(chat.id)
        if not shared_chat:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ERROR_MESSAGES.DEFAULT(),
            )
        return ChatResponse(**shared_chat.model_dump())

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


############################
# DeletedSharedChatById
############################


@router.delete("/{id}/share", response_model=Optional[bool])
async def delete_shared_chat_by_id(id: str, user=Depends(get_verified_user)):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        if not chat.share_id:
            return False

        result = Chats.delete_shared_chat_by_chat_id(id)
        update_result = Chats.update_chat_share_id_by_id(id, None)

        return result and update_result != None
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


############################
# UpdateChatFolderIdById
############################


class ChatFolderIdForm(BaseModel):
    folder_id: Optional[str] = None


@router.post("/{id}/folder", response_model=Optional[ChatResponse])
async def update_chat_folder_id_by_id(
    id: str, form_data: ChatFolderIdForm, user=Depends(get_verified_user)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        chat = Chats.update_chat_folder_id_by_id_and_user_id(
            id, user.id, form_data.folder_id
        )
        return ChatResponse(**chat.model_dump())
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetChatTagsById
############################


@router.get("/{id}/tags", response_model=list[TagModel])
async def get_chat_tags_by_id(id: str, user=Depends(get_verified_user)):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        tags = chat.meta.get("tags", [])
        return Tags.get_tags_by_ids_and_user_id(tags, user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )


############################
# AddChatTagById
############################


@router.post("/{id}/tags", response_model=list[TagModel])
async def add_tag_by_id_and_tag_name(
    id: str, form_data: TagForm, user=Depends(get_verified_user)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        tags = chat.meta.get("tags", [])
        tag_id = form_data.name.replace(" ", "_").lower()

        if tag_id == "none":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Tag name cannot be 'None'"),
            )

        if tag_id not in tags:
            Chats.add_chat_tag_by_id_and_user_id_and_tag_name(
                id, user.id, form_data.name
            )

        chat = Chats.get_chat_by_id_and_user_id(id, user.id)
        tags = chat.meta.get("tags", [])
        return Tags.get_tags_by_ids_and_user_id(tags, user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteChatTagById
############################


@router.delete("/{id}/tags", response_model=list[TagModel])
async def delete_tag_by_id_and_tag_name(
    id: str, form_data: TagForm, user=Depends(get_verified_user)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        Chats.delete_tag_by_id_and_user_id_and_tag_name(id, user.id, form_data.name)

        if Chats.count_chats_by_tag_name_and_user_id(form_data.name, user.id) == 0:
            Tags.delete_tag_by_name_and_user_id(form_data.name, user.id)

        chat = Chats.get_chat_by_id_and_user_id(id, user.id)
        tags = chat.meta.get("tags", [])
        return Tags.get_tags_by_ids_and_user_id(tags, user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )


############################
# DeleteAllTagsById
############################


@router.delete("/{id}/tags/all", response_model=Optional[bool])
async def delete_all_tags_by_id(id: str, user=Depends(get_verified_user)):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id)
    if chat:
        Chats.delete_all_tags_by_id_and_user_id(id, user.id)

        for tag in chat.meta.get("tags", []):
            if Chats.count_chats_by_tag_name_and_user_id(tag, user.id) == 0:
                Tags.delete_tag_by_name_and_user_id(tag, user.id)

        return True
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )
