import json
import logging
from typing import Optional
from sqlalchemy.orm import Session
import asyncio
from fastapi.responses import StreamingResponse


from open_webui.utils.misc import get_message_list
from open_webui.socket.main import get_event_emitter
from open_webui.models.chats import (
    ChatForm,
    ChatImportForm,
    ChatUsageStatsListResponse,
    ChatsImportForm,
    ChatResponse,
    Chats,
    ChatTitleIdResponse,
    ChatStatsExport,
    AggregateChatStats,
    ChatBody,
    ChatHistoryStats,
    MessageStats,
)
from open_webui.models.tags import TagModel, Tags
from open_webui.models.folders import Folders
from open_webui.internal.db import get_session

from open_webui.config import ENABLE_ADMIN_CHAT_ACCESS, ENABLE_ADMIN_EXPORT
from open_webui.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel


from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_permission

log = logging.getLogger(__name__)

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
    db: Session = Depends(get_session),
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
                db=db,
            )
        else:
            return Chats.get_chat_title_id_list_by_user_id(
                user.id,
                include_folders=include_folders,
                include_pinned=include_pinned,
                db=db,
            )
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetChatUsageStats
# EXPERIMENTAL: may be removed in future releases
############################


@router.get("/stats/usage", response_model=ChatUsageStatsListResponse)
def get_session_user_chat_usage_stats(
    items_per_page: Optional[int] = 50,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    try:
        limit = items_per_page
        skip = (page - 1) * limit

        result = Chats.get_chats_by_user_id(user.id, skip=skip, limit=limit, db=db)

        chats = result.items
        total = result.total

        chat_stats = []
        for chat in chats:
            messages_map = chat.chat.get("history", {}).get("messages", {})
            message_id = chat.chat.get("history", {}).get("currentId")

            if messages_map and message_id:
                try:
                    history_models = {}
                    history_message_count = len(messages_map)
                    history_user_messages = []
                    history_assistant_messages = []

                    for message in messages_map.values():
                        if message.get("role", "") == "user":
                            history_user_messages.append(message)
                        elif message.get("role", "") == "assistant":
                            history_assistant_messages.append(message)
                            model = message.get("model", None)
                            if model:
                                if model not in history_models:
                                    history_models[model] = 0
                                history_models[model] += 1

                    average_user_message_content_length = (
                        sum(
                            len(message.get("content", ""))
                            for message in history_user_messages
                        )
                        / len(history_user_messages)
                        if len(history_user_messages) > 0
                        else 0
                    )
                    average_assistant_message_content_length = (
                        sum(
                            len(message.get("content", ""))
                            for message in history_assistant_messages
                        )
                        / len(history_assistant_messages)
                        if len(history_assistant_messages) > 0
                        else 0
                    )

                    response_times = []
                    for message in history_assistant_messages:
                        user_message_id = message.get("parentId", None)
                        if user_message_id and user_message_id in messages_map:
                            user_message = messages_map[user_message_id]
                            response_time = message.get(
                                "timestamp", 0
                            ) - user_message.get("timestamp", 0)

                            response_times.append(response_time)

                    average_response_time = (
                        sum(response_times) / len(response_times)
                        if len(response_times) > 0
                        else 0
                    )

                    message_list = get_message_list(messages_map, message_id)
                    message_count = len(message_list)

                    models = {}
                    for message in reversed(message_list):
                        if message.get("role") == "assistant":
                            model = message.get("model", None)
                            if model:
                                if model not in models:
                                    models[model] = 0
                                models[model] += 1

                            annotation = message.get("annotation", {})

                    chat_stats.append(
                        {
                            "id": chat.id,
                            "models": models,
                            "message_count": message_count,
                            "history_models": history_models,
                            "history_message_count": history_message_count,
                            "history_user_message_count": len(history_user_messages),
                            "history_assistant_message_count": len(
                                history_assistant_messages
                            ),
                            "average_response_time": average_response_time,
                            "average_user_message_content_length": average_user_message_content_length,
                            "average_assistant_message_content_length": average_assistant_message_content_length,
                            "tags": chat.meta.get("tags", []),
                            "last_message_at": message_list[-1].get("timestamp", None),
                            "updated_at": chat.updated_at,
                            "created_at": chat.created_at,
                        }
                    )
                except Exception as e:
                    pass

        return ChatUsageStatsListResponse(items=chat_stats, total=total)

    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetChatStatsExport
############################


CHAT_EXPORT_PAGE_ITEM_COUNT = 10


class ChatStatsExportList(BaseModel):
    type: str = "chats"
    items: list[ChatStatsExport]
    total: int
    page: int


def _process_chat_for_export(chat) -> Optional[ChatStatsExport]:
    try:

        def get_message_content_length(message):
            content = message.get("content", "")
            if isinstance(content, str):
                return len(content)
            elif isinstance(content, list):
                return sum(
                    len(item.get("text", ""))
                    for item in content
                    if item.get("type") == "text"
                )
            return 0

        messages_map = chat.chat.get("history", {}).get("messages", {})
        message_id = chat.chat.get("history", {}).get("currentId")

        history_models = {}
        history_message_count = len(messages_map)
        history_user_messages = []
        history_assistant_messages = []

        export_messages = {}
        for key, message in messages_map.items():
            try:
                content_length = get_message_content_length(message)

                # Extract rating safely
                rating = message.get("annotation", {}).get("rating")
                tags = message.get("annotation", {}).get("tags")

                message_stat = MessageStats(
                    id=message.get("id"),
                    role=message.get("role"),
                    model=message.get("model"),
                    timestamp=message.get("timestamp"),
                    content_length=content_length,
                    token_count=None,  # Populate if available, e.g. message.get("info", {}).get("token_count")
                    rating=rating,
                    tags=tags,
                )

                export_messages[key] = message_stat

                # --- Aggregation Logic (copied/adapted from usage stats) ---
                role = message.get("role", "")
                if role == "user":
                    history_user_messages.append(message)
                elif role == "assistant":
                    history_assistant_messages.append(message)
                    model = message.get("model")
                    if model:
                        if model not in history_models:
                            history_models[model] = 0
                        history_models[model] += 1
            except Exception as e:
                log.debug(f"Error processing message {key}: {e}")
                continue

        # Calculate Averages
        average_user_message_content_length = (
            sum(get_message_content_length(m) for m in history_user_messages)
            / len(history_user_messages)
            if history_user_messages
            else 0
        )

        average_assistant_message_content_length = (
            sum(get_message_content_length(m) for m in history_assistant_messages)
            / len(history_assistant_messages)
            if history_assistant_messages
            else 0
        )

        # Response Times
        response_times = []
        for message in history_assistant_messages:
            user_message_id = message.get("parentId", None)
            if user_message_id and user_message_id in messages_map:
                user_message = messages_map[user_message_id]
                # Ensure timestamps exist
                t1 = message.get("timestamp")
                t0 = user_message.get("timestamp")
                if t1 and t0:
                    response_times.append(t1 - t0)

        average_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )

        # Current Message List Logic (Main path)
        message_list = get_message_list(messages_map, message_id)
        message_count = len(message_list)
        models = {}
        for message in reversed(message_list):
            if message.get("role") == "assistant":
                model = message.get("model")
                if model:
                    if model not in models:
                        models[model] = 0
                    models[model] += 1

        # Construct Aggregate Stats
        stats = AggregateChatStats(
            average_response_time=average_response_time,
            average_user_message_content_length=average_user_message_content_length,
            average_assistant_message_content_length=average_assistant_message_content_length,
            models=models,
            message_count=message_count,
            history_models=history_models,
            history_message_count=history_message_count,
            history_user_message_count=len(history_user_messages),
            history_assistant_message_count=len(history_assistant_messages),
        )

        # Construct Chat Body
        chat_body = ChatBody(
            history=ChatHistoryStats(messages=export_messages, currentId=message_id)
        )

        return ChatStatsExport(
            id=chat.id,
            user_id=chat.user_id,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            tags=chat.meta.get("tags", []),
            stats=stats,
            chat=chat_body,
        )
    except Exception as e:
        log.exception(f"Error exporting stats for chat {chat.id}: {e}")
        return None


def calculate_chat_stats(
    user_id, skip=0, limit=10, filter=None, db: Optional[Session] = None
):
    if filter is None:
        filter = {}

    result = Chats.get_chats_by_user_id(
        user_id,
        skip=skip,
        limit=limit,
        filter=filter,
        db=db,
    )

    chat_stats_export_list = []
    for chat in result.items:
        chat_stat = _process_chat_for_export(chat)
        if chat_stat:
            chat_stats_export_list.append(chat_stat)

    return chat_stats_export_list, result.total


def generate_chat_stats_jsonl_generator(user_id, filter):
    """
    Synchronous generator for streaming chat stats export.

    NOTE: We intentionally do NOT pass a shared db session here. Instead, we let
    each batch create its own short-lived session via get_db_context(None).
    This is critical for SQLite in low-resource environments because:
    1. SQLite uses file-level locking
    2. Holding a session open for the entire streaming duration blocks other requests
    3. Short-lived sessions release locks between batches, allowing other operations
    """
    skip = 0
    limit = CHAT_EXPORT_PAGE_ITEM_COUNT

    while True:
        # Each batch gets its own session that closes after the query
        result = Chats.get_chats_by_user_id(
            user_id,
            filter=filter,
            skip=skip,
            limit=limit,
            db=None,  # Let get_db_context create a fresh session per batch
        )
        if not result.items:
            break

        for chat in result.items:
            try:
                chat_stat = _process_chat_for_export(chat)
                if chat_stat:
                    yield chat_stat.model_dump_json() + "\n"
            except Exception as e:
                log.exception(f"Error processing chat {chat.id}: {e}")

        skip += limit


@router.get("/stats/export", response_model=ChatStatsExportList)
async def export_chat_stats(
    request: Request,
    updated_at: Optional[int] = None,
    page: Optional[int] = 1,
    stream: bool = False,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    # Check if the user has permission to share/export chats
    if (user.role != "admin") and (
        not request.app.state.config.ENABLE_COMMUNITY_SHARING
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    try:
        # Fetch chats with date filtering
        filter = {"order_by": "updated_at", "direction": "asc"}

        if updated_at:
            filter["updated_at"] = updated_at

        if stream:
            return StreamingResponse(
                generate_chat_stats_jsonl_generator(user.id, filter),
                media_type="application/x-ndjson",
                headers={
                    "Content-Disposition": f"attachment; filename=chat-stats-export-{user.id}.jsonl"
                },
            )
        else:
            limit = CHAT_EXPORT_PAGE_ITEM_COUNT
            skip = (page - 1) * limit

            chat_stats_export_list, total = await asyncio.to_thread(
                calculate_chat_stats, user.id, skip, limit, filter, db=db
            )

            return ChatStatsExportList(
                items=chat_stats_export_list, total=total, page=page
            )

    except Exception as e:
        log.debug(f"Error exporting chat stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetSingleChatStatsExport
############################


@router.get("/stats/export/{chat_id}", response_model=Optional[ChatStatsExport])
async def export_single_chat_stats(
    request: Request,
    chat_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Export stats for exactly one chat by ID.
    Returns ChatStatsExport for the specified chat.
    """
    # Check if the user has permission to share/export chats
    if (user.role != "admin") and (
        not request.app.state.config.ENABLE_COMMUNITY_SHARING
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    try:
        chat = Chats.get_chat_by_id(chat_id, db=db)

        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )

        # Verify the chat belongs to the user (unless admin)
        if chat.user_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )

        # Process the chat for export
        chat_stats = await asyncio.to_thread(_process_chat_for_export, chat)

        if not chat_stats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to process chat stats",
            )

        return chat_stats

    except HTTPException:
        raise
    except Exception as e:
        log.debug(f"Error exporting single chat stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


@router.delete("/", response_model=bool)
async def delete_all_user_chats(
    request: Request,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):

    if user.role == "user" and not has_permission(
        user.id, "chat.delete", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = Chats.delete_chats_by_user_id(user.id, db=db)
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
    db: Session = Depends(get_session),
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
        user_id, include_archived=True, filter=filter, skip=skip, limit=limit, db=db
    )


############################
# CreateNewChat
############################


@router.post("/new", response_model=Optional[ChatResponse])
async def create_new_chat(
    form_data: ChatForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    try:
        chat = Chats.insert_new_chat(user.id, form_data, db=db)
        return ChatResponse(**chat.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# ImportChats
############################


@router.post("/import", response_model=list[ChatResponse])
async def import_chats(
    form_data: ChatsImportForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    try:
        chats = Chats.import_chats(user.id, form_data.chats, db=db)
        return chats
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
    text: str,
    page: Optional[int] = None,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if page is None:
        page = 1

    limit = 60
    skip = (page - 1) * limit

    chat_list = [
        ChatTitleIdResponse(**chat.model_dump())
        for chat in Chats.get_chats_by_user_id_and_search_text(
            user.id, text, skip=skip, limit=limit, db=db
        )
    ]

    # Delete tag if no chat is found
    words = text.strip().split(" ")
    if page == 1 and len(words) == 1 and words[0].startswith("tag:"):
        tag_id = words[0].replace("tag:", "")
        if len(chat_list) == 0:
            if Tags.get_tag_by_name_and_user_id(tag_id, user.id, db=db):
                log.debug(f"deleting tag: {tag_id}")
                Tags.delete_tag_by_name_and_user_id(tag_id, user.id, db=db)

    return chat_list


############################
# GetChatsByFolderId
############################


@router.get("/folder/{folder_id}", response_model=list[ChatResponse])
async def get_chats_by_folder_id(
    folder_id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    folder_ids = [folder_id]
    children_folders = Folders.get_children_folders_by_id_and_user_id(
        folder_id, user.id, db=db
    )
    if children_folders:
        folder_ids.extend([folder.id for folder in children_folders])

    return [
        ChatResponse(**chat.model_dump())
        for chat in Chats.get_chats_by_folder_ids_and_user_id(
            folder_ids, user.id, db=db
        )
    ]


@router.get("/folder/{folder_id}/list")
async def get_chat_list_by_folder_id(
    folder_id: str,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    try:
        limit = 10
        skip = (page - 1) * limit

        return [
            {"title": chat.title, "id": chat.id, "updated_at": chat.updated_at}
            for chat in Chats.get_chats_by_folder_id_and_user_id(
                folder_id, user.id, skip=skip, limit=limit, db=db
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
async def get_user_pinned_chats(
    user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    return [
        ChatTitleIdResponse(**chat.model_dump())
        for chat in Chats.get_pinned_chats_by_user_id(user.id, db=db)
    ]


############################
# GetChats
############################


@router.get("/all", response_model=list[ChatResponse])
async def get_user_chats(
    user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    result = Chats.get_chats_by_user_id(user.id, db=db)
    return [ChatResponse(**chat.model_dump()) for chat in result.items]


############################
# GetArchivedChats
############################


@router.get("/all/archived", response_model=list[ChatResponse])
async def get_user_archived_chats(
    user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    return [
        ChatResponse(**chat.model_dump())
        for chat in Chats.get_archived_chats_by_user_id(user.id, db=db)
    ]


############################
# GetAllTags
############################


@router.get("/all/tags", response_model=list[TagModel])
async def get_all_user_tags(
    user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    try:
        tags = Tags.get_tags_by_user_id(user.id, db=db)
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
async def get_all_user_chats_in_db(
    user=Depends(get_admin_user), db: Session = Depends(get_session)
):
    if not ENABLE_ADMIN_EXPORT:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    return [ChatResponse(**chat.model_dump()) for chat in Chats.get_chats(db=db)]


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
    db: Session = Depends(get_session),
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
            db=db,
        )
    ]

    return chat_list


############################
# ArchiveAllChats
############################


@router.post("/archive/all", response_model=bool)
async def archive_all_chats(
    user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    return Chats.archive_all_chats_by_user_id(user.id, db=db)


############################
# UnarchiveAllChats
############################


@router.post("/unarchive/all", response_model=bool)
async def unarchive_all_chats(
    user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    return Chats.unarchive_all_chats_by_user_id(user.id, db=db)


############################
# GetSharedChatById
############################


@router.get("/share/{share_id}", response_model=Optional[ChatResponse])
async def get_shared_chat_by_id(
    share_id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    if user.role == "pending":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role == "user" or (user.role == "admin" and not ENABLE_ADMIN_CHAT_ACCESS):
        chat = Chats.get_chat_by_share_id(share_id, db=db)
    elif user.role == "admin" and ENABLE_ADMIN_CHAT_ACCESS:
        chat = Chats.get_chat_by_id(share_id, db=db)

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
    form_data: TagFilterForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    chats = Chats.get_chat_list_by_user_id_and_tag_name(
        user.id, form_data.name, form_data.skip, form_data.limit, db=db
    )
    if len(chats) == 0:
        Tags.delete_tag_by_name_and_user_id(form_data.name, user.id, db=db)

    return chats


############################
# GetChatById
############################


@router.get("/{id}", response_model=Optional[ChatResponse])
async def get_chat_by_id(
    id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id, db=db)

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
    id: str,
    form_data: ChatForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        updated_chat = {**chat.chat, **form_data.chat}
        chat = Chats.update_chat_by_id(id, updated_chat, db=db)
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
    id: str,
    message_id: str,
    form_data: MessageForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    chat = Chats.get_chat_by_id(id, db=db)

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
        db=db,
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
    id: str,
    message_id: str,
    form_data: EventForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    chat = Chats.get_chat_by_id(id, db=db)

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
async def delete_chat_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role == "admin":
        chat = Chats.get_chat_by_id(id, db=db)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )
        for tag in chat.meta.get("tags", []):
            if Chats.count_chats_by_tag_name_and_user_id(tag, user.id, db=db) == 1:
                Tags.delete_tag_by_name_and_user_id(tag, user.id, db=db)

        result = Chats.delete_chat_by_id(id, db=db)

        return result
    else:
        if not has_permission(
            user.id, "chat.delete", request.app.state.config.USER_PERMISSIONS
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )

        chat = Chats.get_chat_by_id(id, db=db)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )
        for tag in chat.meta.get("tags", []):
            if Chats.count_chats_by_tag_name_and_user_id(tag, user.id, db=db) == 1:
                Tags.delete_tag_by_name_and_user_id(tag, user.id, db=db)

        result = Chats.delete_chat_by_id_and_user_id(id, user.id, db=db)
        return result


############################
# GetPinnedStatusById
############################


@router.get("/{id}/pinned", response_model=Optional[bool])
async def get_pinned_status_by_id(
    id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
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
async def pin_chat_by_id(
    id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        chat = Chats.toggle_chat_pinned_by_id(id, db=db)
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
    form_data: CloneForm,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        updated_chat = {
            **chat.chat,
            "originalChatId": chat.id,
            "branchPointMessageId": chat.chat["history"]["currentId"],
            "title": form_data.title if form_data.title else f"Clone of {chat.title}",
        }

        chats = Chats.import_chats(
            user.id,
            [
                ChatImportForm(
                    **{
                        "chat": updated_chat,
                        "meta": chat.meta,
                        "pinned": chat.pinned,
                        "folder_id": chat.folder_id,
                    }
                )
            ],
            db=db,
        )

        if chats:
            chat = chats[0]
            return ChatResponse(**chat.model_dump())
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ERROR_MESSAGES.DEFAULT(),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# CloneSharedChatById
############################


@router.post("/{id}/clone/shared", response_model=Optional[ChatResponse])
async def clone_shared_chat_by_id(
    id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):

    if user.role == "admin":
        chat = Chats.get_chat_by_id(id, db=db)
    else:
        chat = Chats.get_chat_by_share_id(id, db=db)

    if chat:
        updated_chat = {
            **chat.chat,
            "originalChatId": chat.id,
            "branchPointMessageId": chat.chat["history"]["currentId"],
            "title": f"Clone of {chat.title}",
        }

        chats = Chats.import_chats(
            user.id,
            [
                ChatImportForm(
                    **{
                        "chat": updated_chat,
                        "meta": chat.meta,
                        "pinned": chat.pinned,
                        "folder_id": chat.folder_id,
                    }
                )
            ],
            db=db,
        )

        if chats:
            chat = chats[0]
            return ChatResponse(**chat.model_dump())
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ERROR_MESSAGES.DEFAULT(),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# ArchiveChat
############################


@router.post("/{id}/archive", response_model=Optional[ChatResponse])
async def archive_chat_by_id(
    id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        chat = Chats.toggle_chat_archive_by_id(id, db=db)

        # Delete tags if chat is archived
        if chat.archived:
            for tag_id in chat.meta.get("tags", []):
                if (
                    Chats.count_chats_by_tag_name_and_user_id(tag_id, user.id, db=db)
                    == 0
                ):
                    log.debug(f"deleting tag: {tag_id}")
                    Tags.delete_tag_by_name_and_user_id(tag_id, user.id, db=db)
        else:
            for tag_id in chat.meta.get("tags", []):
                tag = Tags.get_tag_by_name_and_user_id(tag_id, user.id, db=db)
                if tag is None:
                    log.debug(f"inserting tag: {tag_id}")
                    tag = Tags.insert_new_tag(tag_id, user.id, db=db)

        return ChatResponse(**chat.model_dump())
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# ShareChatById
############################


@router.post("/{id}/share", response_model=Optional[ChatResponse])
async def share_chat_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if (user.role != "admin") and (
        not has_permission(
            user.id, "chat.share", request.app.state.config.USER_PERMISSIONS
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    chat = Chats.get_chat_by_id_and_user_id(id, user.id, db=db)

    if chat:
        if chat.share_id:
            shared_chat = Chats.update_shared_chat_by_chat_id(chat.id, db=db)
            return ChatResponse(**shared_chat.model_dump())

        shared_chat = Chats.insert_shared_chat_by_chat_id(chat.id, db=db)
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
async def delete_shared_chat_by_id(
    id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        if not chat.share_id:
            return False

        result = Chats.delete_shared_chat_by_chat_id(id, db=db)
        update_result = Chats.update_chat_share_id_by_id(id, None, db=db)

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
    id: str,
    form_data: ChatFolderIdForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        chat = Chats.update_chat_folder_id_by_id_and_user_id(
            id, user.id, form_data.folder_id, db=db
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
async def get_chat_tags_by_id(
    id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        tags = chat.meta.get("tags", [])
        return Tags.get_tags_by_ids_and_user_id(tags, user.id, db=db)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )


############################
# AddChatTagById
############################


@router.post("/{id}/tags", response_model=list[TagModel])
async def add_tag_by_id_and_tag_name(
    id: str,
    form_data: TagForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
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
                id, user.id, form_data.name, db=db
            )

        chat = Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
        tags = chat.meta.get("tags", [])
        return Tags.get_tags_by_ids_and_user_id(tags, user.id, db=db)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteChatTagById
############################


@router.delete("/{id}/tags", response_model=list[TagModel])
async def delete_tag_by_id_and_tag_name(
    id: str,
    form_data: TagForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        Chats.delete_tag_by_id_and_user_id_and_tag_name(
            id, user.id, form_data.name, db=db
        )

        if (
            Chats.count_chats_by_tag_name_and_user_id(form_data.name, user.id, db=db)
            == 0
        ):
            Tags.delete_tag_by_name_and_user_id(form_data.name, user.id, db=db)

        chat = Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
        tags = chat.meta.get("tags", [])
        return Tags.get_tags_by_ids_and_user_id(tags, user.id, db=db)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )


############################
# DeleteAllTagsById
############################


@router.delete("/{id}/tags/all", response_model=Optional[bool])
async def delete_all_tags_by_id(
    id: str, user=Depends(get_verified_user), db: Session = Depends(get_session)
):
    chat = Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        Chats.delete_all_tags_by_id_and_user_id(id, user.id, db=db)

        for tag in chat.meta.get("tags", []):
            if Chats.count_chats_by_tag_name_and_user_id(tag, user.id, db=db) == 0:
                Tags.delete_tag_by_name_and_user_id(tag, user.id, db=db)

        return True
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND
        )
