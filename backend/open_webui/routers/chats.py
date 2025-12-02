import csv
import json
import logging
import zipfile
from datetime import datetime
from io import BytesIO, StringIO
from typing import Optional
import pytz

from open_webui.models.chats import (
    ChatForm,
    ChatImportForm,
    ChatResponse,
    Chats,
    ChatTitleIdResponse,
    ChatFilterResponse,
    ChatExportZipForm,
    ChatExportCSVForm,
    ChatTitleMessagesForm,
)
from open_webui.models.tags import TagModel, Tags
from open_webui.models.folders import Folders

from open_webui.config import ENABLE_ADMIN_CHAT_ACCESS, ENABLE_ADMIN_EXPORT
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel


from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_permission
from open_webui.utils.pdf_generator import PDFGenerator
from open_webui.models.users import Users

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

############################
# GetChatList
############################


@router.get("/", response_model=list[ChatTitleIdResponse])
@router.get("/list", response_model=list[ChatTitleIdResponse])
async def get_session_user_chat_list(
    user=Depends(get_verified_user), page: Optional[int] = None
):
    if page is not None:
        limit = 60
        skip = (page - 1) * limit

        return Chats.get_chat_title_id_list_by_user_id(user.id, skip=skip, limit=limit)
    else:
        return Chats.get_chat_title_id_list_by_user_id(user.id)


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
    user=Depends(get_admin_user),
    skip: int = 0,
    limit: int = 50,
):
    if not ENABLE_ADMIN_CHAT_ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return Chats.get_chat_list_by_user_id(
        user_id, include_archived=True, skip=skip, limit=limit
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
async def search_user_chats(
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


############################
# GetPinnedChats
############################


@router.get("/pinned", response_model=list[ChatResponse])
async def get_user_pinned_chats(user=Depends(get_verified_user)):
    return [
        ChatResponse(**chat.model_dump())
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
    user=Depends(get_verified_user), skip: int = 0, limit: int = 50
):
    return Chats.get_archived_chat_list_by_user_id(user.id, skip, limit)


############################
# ArchiveAllChats
############################


@router.post("/archive/all", response_model=bool)
async def archive_all_chats(user=Depends(get_verified_user)):
    return Chats.archive_all_chats_by_user_id(user.id)


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
        if user.role == "admin":
            try:
                from open_webui.models.models import Models  # lazy import to avoid cycles

                # Infer model info
                model_id = None
                base_model_id = None
                messages = Chats.get_messages_by_chat_id(chat.id)
                if messages:
                    current_id = chat.chat.get("history", {}).get("currentId")
                    if current_id and current_id in messages:
                        model_id = messages[current_id].get("model")
                    else:
                        try:
                            model_id = list(messages.values())[-1].get("model")
                        except Exception:
                            pass

                model_name = None
                base_model_name = None
                if model_id:
                    m = Models.get_model_by_id(model_id)
                    if m:
                        model_name = m.name
                        base_model_id = m.base_model_id
                        if base_model_id:
                            bm = Models.get_model_by_id(base_model_id)
                            base_model_name = bm.name if bm else None

                log.info(
                    f"[ADMIN] Chat meta for chat_id={chat.id}, owner={chat.user_id}: model_id={model_id}, model_name={model_name}, base_model_id={base_model_id}, base_model_name={base_model_name}, meta={json.dumps(chat.meta, ensure_ascii=False)}"
                )
            except Exception as e:
                log.exception(f"Failed to log chat meta/model info for chat_id={chat.id}: {e}")
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

        ### update metadata for chat filtering ###
        user_id = chat.user_id
        messages = chat.chat.get("messages", [])
        num_of_messages = len(messages)        
        total_time_taken = messages[-1].get("timestamp", 0) - messages[0].get("timestamp", 0)
        questions_asked = []
        for m in messages:
            if m["role"] == "user":
                # Get timestamp and convert to EST
                timestamp = m.get("timestamp", 0)
                if timestamp:
                    # Convert timestamp to datetime and then to EST
                    dt = datetime.fromtimestamp(timestamp)
                    est_tz = pytz.timezone('US/Eastern')
                    dt_est = dt.astimezone(est_tz)
                    # Convert to string format for database storage
                    dt_est_str = dt_est.strftime('%Y-%m-%d %H:%M:%S %Z')
                    questions_asked.append([m["content"], dt_est_str])
                else:
                    # If no timestamp, append with None
                    questions_asked.append([m["content"], None])


        model_name = None
        base_model_name = None
        if chat.chat.get("models") and len(chat.chat["models"]) > 0:
            model_id = chat.chat["models"][0]
            from open_webui.models.models import Models  # lazy import to avoid cycles
            if model_id:
                m = Models.get_model_by_id(model_id)
                if m:
                    model_name = m.name
                    base_model_id = m.base_model_id
                    if base_model_id:
                        bm = Models.get_model_by_id(base_model_id)
                        base_model_name = bm.name if bm else None
                    else:
                        base_model_name = model_name
        
        updated_meta = {
            "user_id": user_id, 
            "total_time_taken": total_time_taken, 
            "num_of_messages": num_of_messages, 
            "model_name": model_name, 
            "base_model_name": base_model_name,
            "questions_asked": questions_asked,
        }
        
        chat = Chats.update_chat_meta_by_id_and_user_id(id, user_id, updated_meta)
        ######
        
        return ChatResponse(**chat.model_dump())
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    

############################
# FilterChatByMeta
############################


class ChatMetaFilterForm(BaseModel):
    user_id: Optional[str] = ""
    group_id: Optional[str] = ""  
    model_name: Optional[str] = ""
    base_model_name: Optional[str] = ""
    min_messages: Optional[int] = None
    max_messages: Optional[int] = None
    min_time_taken: Optional[int] = None  # in seconds
    max_time_taken: Optional[int] = None  # in seconds
    skip: Optional[int] = 0
    limit: Optional[int] = 50


@router.post("/filter/meta", response_model=list[ChatFilterResponse])
async def filter_chats_by_meta(form_data: ChatMetaFilterForm, user=Depends(get_verified_user)):
    try:
        # Check group access permission if group_id is provided
        if form_data.group_id:
            # Only admins can filter chats by group
            if user.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only administrators can filter chats by group"
                )
            
            # Check if admin has access to the specified group
            from open_webui.models.groups import Groups  # lazy import to avoid cycles
            group = Groups.get_group_by_id(form_data.group_id)
            if not group:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Group not found"
                )
            
            # Admin must be a member of the group or be the creator of the group
            user_groups = Groups.get_groups_by_member_id(user.id)
            user_group_ids = [g.id for g in user_groups]
            
            # Check if super admin
            first_user = Users.get_first_user()
            allowed_emails = [
                "sm11538@nyu.edu", "ms15138@nyu.edu", "mb484@nyu.edu",
                "cg4532@nyu.edu", "ht2490@nyu.edu", "ps5226@nyu.edu"
            ]
            is_super_admin = (first_user and user.id == first_user.id) or user.email in allowed_emails
            
            if form_data.group_id not in user_group_ids and group.user_id != user.id and not is_super_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have access to this group"
                )
        
        chats = Chats.get_chats_by_user_id_and_meta_filter(
            form_data.model_dump(), form_data.skip, form_data.limit
        )
        return [
            ChatFilterResponse(**chat.model_dump())
            for chat in chats
        ]
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


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

        chat = Chats.insert_new_chat(user.id, ChatForm(**{"chat": updated_chat}))
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
    chat = Chats.get_chat_by_share_id(id)
    if chat:
        updated_chat = {
            **chat.chat,
            "originalChatId": chat.id,
            "branchPointMessageId": chat.chat["history"]["currentId"],
            "title": f"Clone of {chat.title}",
        }

        chat = Chats.insert_new_chat(user.id, ChatForm(**{"chat": updated_chat}))
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
async def share_chat_by_id(id: str, user=Depends(get_verified_user)):
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


############################
# Export Chats as ZIP
############################


@router.post("/export/zip")
async def export_chats_as_zip(
    form_data: ChatExportZipForm, user=Depends(get_verified_user)
):
    """
    Export selected chats as a ZIP file containing individual PDFs for each student.
    Each PDF contains all conversations for that student with the same homework/model.
    """
    try:
        # Only admins can export group chat data
        if user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can export group chat data"
            )

        # Validate that all chat IDs exist and belong to the specified group
        chats = []
        for chat_id in form_data.chat_ids:
            chat = Chats.get_chat_by_id(chat_id)
            if not chat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Chat {chat_id} not found"
                )
            
            if chat.group_id != form_data.group_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Chat {chat_id} does not belong to group {form_data.group_id}"
                )
            
            chats.append(chat)

        if not chats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid chats found for export"
            )

        # Group chats by user_id + model_name for merged PDFs
        grouped_chats = {}
        for chat in chats:
            user_id = chat.user_id
            model_name = chat.meta.get('model_name') or chat.meta.get('base_model_name') or 'Unknown_Model'
            
            # Create a unique key for each user-model combination
            key = f"{user_id}_{model_name}"
            
            if key not in grouped_chats:
                grouped_chats[key] = {
                    'user_id': user_id,
                    'model_name': model_name,
                    'chats': []
                }
            
            grouped_chats[key]['chats'].append(chat)

        # Generate PDFs for each group
        pdf_files = {}
        for group_key, group_data in grouped_chats.items():
            try:
                # Get user information
                user_info = Users.get_user_by_id(group_data['user_id'])
                if not user_info:
                    user_name = f"User_{group_data['user_id']}"
                else:
                    # Clean user name for filename (remove invalid characters)
                    user_name = "".join(c for c in user_info.name if c.isalnum() or c in (' ', '-', '_')).strip()
                    user_name = user_name.replace(' ', '_')

                # Clean model name for filename
                model_name = "".join(c for c in group_data['model_name'] if c.isalnum() or c in (' ', '-', '_')).strip()
                model_name = model_name.replace(' ', '_')

                # Collect and merge all messages from all chats for this user-model combination
                all_messages = []
                chat_titles = []
                
                for chat in group_data['chats']:
                    chat_titles.append(chat.title)
                    messages = chat.chat.get('messages', [])
                    
                    # Add chat context to messages if multiple chats
                    if len(group_data['chats']) > 1:
                        # Add a separator message to distinguish between different chat sessions
                        separator_message = {
                            "role": "system",
                            "content": f"--- Chat Session: {chat.title} ---",
                            "timestamp": messages[0].get('timestamp', 0) if messages else 0
                        }
                        all_messages.append(separator_message)
                    
                    all_messages.extend(messages)

                # Sort all messages by timestamp to maintain chronological order
                all_messages.sort(key=lambda x: x.get('timestamp', 0))

                # Create title for the merged PDF
                if len(chat_titles) == 1:
                    pdf_title = f"{user_name} - {model_name} - {chat_titles[0]}"
                else:
                    pdf_title = f"{user_name} - {model_name} - {len(chat_titles)} Conversations"

                # Generate PDF using existing PDFGenerator
                pdf_form = ChatTitleMessagesForm(
                    title=pdf_title,
                    messages=all_messages
                )
                
                pdf_generator = PDFGenerator(pdf_form)
                pdf_bytes = pdf_generator.generate_chat_pdf()
                
                # Create filename for the PDF
                filename = f"{user_name}_{model_name}.pdf"
                
                # Handle duplicate filenames by adding a counter
                original_filename = filename
                counter = 1
                while filename in pdf_files:
                    name_part = original_filename.replace('.pdf', '')
                    filename = f"{name_part}_{counter}.pdf"
                    counter += 1
                
                pdf_files[filename] = pdf_bytes

            except Exception as e:
                log.error(f"Error generating PDF for group {group_key}: {e}")
                # Continue with other PDFs even if one fails
                continue

        if not pdf_files:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate any PDFs"
            )

        # Create ZIP file containing all PDFs
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, pdf_bytes in pdf_files.items():
                zip_file.writestr(filename, pdf_bytes)

        zip_buffer.seek(0)
        zip_content = zip_buffer.getvalue()

        # Create filename for the ZIP
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d")
        zip_filename = f"group-{form_data.group_id}-conversations-{timestamp}.zip"

        log.info(f"Successfully created ZIP export: {zip_filename} with {len(pdf_files)} PDFs")

        return Response(
            content=zip_content,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        log.exception(f"Error exporting chats as ZIP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export chats as ZIP"
        )


############################
# Export Chats as CSV
############################


@router.post("/export/csv")
async def export_chats_as_csv(
    form_data: ChatExportCSVForm, user=Depends(get_verified_user)
):
    """
    Export filtered chats as CSV with one question per row.
    """
    try:
        # Only admins can export group chat data
        if user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can export group chat data"
            )

        # Check group access permission
        from open_webui.models.groups import Groups
        group = Groups.get_group_by_id(form_data.group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found"
            )

        # Get filtered chats
        chats = Chats.get_chats_by_user_id_and_meta_filter(
            form_data.model_dump(), form_data.skip, form_data.limit
        )

        if not chats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No chats found matching the criteria"
            )

        # Batch get user data
        user_ids = list(set(chat.user_id for chat in chats))
        users_map = {user.id: user for user in Users.get_users_by_user_ids(user_ids)}

        # Generate CSV rows
        csv_rows = []
        for chat in chats:
            user_info = users_map.get(chat.user_id)
            member_name = user_info.name if user_info else f"User_{chat.user_id}"
            model_name = chat.meta.get('model_name') or chat.meta.get('base_model_name') or 'Unknown'

            # Get messages for this chat
            messages = Chats.get_messages_by_chat_id(chat.id)
            if not messages:
                continue

            # Extract user questions with timestamps
            for message_id, message in messages.items():
                if message.get('role') == 'user':
                    timestamp = message.get('timestamp', 0)
                    if timestamp:
                        # Convert to EST timezone
                        est_tz = pytz.timezone('US/Eastern')
                        utc_dt = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
                        est_dt = utc_dt.astimezone(est_tz)
                        human_timestamp = est_dt.strftime('%Y-%m-%d %I:%M:%S %p EST')
                    else:
                        human_timestamp = 'Unknown'
                    
                    csv_rows.append({
                        'member': member_name,
                        'model_name': model_name,
                        'chat_id': chat.id,
                        'question': message.get('content', ''),
                        'timestamp': human_timestamp
                    })

        if not csv_rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No questions found in the selected chats"
            )

        # Generate CSV
        output = StringIO()
        fieldnames = ['member', 'model_name', 'chat_id', 'question', 'timestamp']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

        csv_content = output.getvalue()
        output.close()

        # Create filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"group-{form_data.group_id}-conversations-{timestamp}.csv"

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error exporting chats as CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export chats as CSV"
        )
