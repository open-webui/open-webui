from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from open_webui.config import ENABLE_ADMIN_CHAT_ACCESS, ENABLE_ADMIN_EXPORT
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrants
from open_webui.models.config import Config
from open_webui.models.chats import (
    AggregateChatStats,
    ChatBody,
    ChatForm,
    ChatHistoryStats,
    ChatImportForm,
    ChatResponse,
    Chats,
    ChatsImportForm,
    ChatStatsExport,
    ChatTitleIdResponse,
    ChatUsageStatsListResponse,
    MessageStats,
)
from open_webui.models.folders import Folders
from open_webui.models.shared_chats import SharedChatResponse, SharedChats
from open_webui.models.tags import TagModel, Tags
from open_webui.socket.main import get_event_emitter
from open_webui.tasks import has_active_tasks, stop_item_tasks
from open_webui.utils.access_control import filter_allowed_access_grants, has_permission
from open_webui.utils.access_control.folders import has_folder_access
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.context_compaction import compact_chat_branch
from open_webui.utils.misc import get_message_list
from open_webui.utils.models import get_all_models
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()

SEARCH_FILTER_PREFIXES = ('tag:', 'folder:', 'pinned:', 'archived:', 'shared:')

CHAT_CONFIG_KEYS = {
    'ENABLE_CONTEXT_COMPACTION': 'chat.context_compaction.enable',
    'CONTEXT_COMPACTION_TOKEN_THRESHOLD': 'chat.context_compaction.token_threshold',
    'CONTEXT_COMPACTION_PROMPT_TEMPLATE': 'chat.context_compaction.prompt_template',
}


class ChatConfigForm(BaseModel):
    ENABLE_CONTEXT_COMPACTION: bool
    CONTEXT_COMPACTION_TOKEN_THRESHOLD: int
    CONTEXT_COMPACTION_PROMPT_TEMPLATE: str


class CompactChatForm(BaseModel):
    model: str | None = None


def chat_search_content_text(text: str) -> str:
    words = text.lower().strip().split(' ')
    return ' '.join(word for word in words if not word.startswith(SEARCH_FILTER_PREFIXES)).strip()


def chat_search_snippet(chat: dict, search_text: str, max_length: int = 200) -> str | None:
    if not search_text:
        return None

    messages = chat.get('messages', [])
    if isinstance(messages, dict):
        messages = messages.values()

    for message in messages:
        if not isinstance(message, dict):
            continue

        content = message.get('content')
        if not isinstance(content, str):
            continue

        index = content.lower().find(search_text)
        if index == -1:
            continue

        start = max(index - max_length // 2, 0)
        end = min(start + max_length, len(content))
        if index + len(search_text) > end:
            end = min(index + len(search_text), len(content))
            start = max(end - max_length, 0)

        snippet = ' '.join(content[start:end].split())
        return f'{"..." if start else ""}{snippet}{"..." if end < len(content) else ""}'

    return None


async def get_chat_config_values() -> dict:
    values = await Config.get_many(*CHAT_CONFIG_KEYS.values())
    return {field: values[storage_key] for field, storage_key in CHAT_CONFIG_KEYS.items() if storage_key in values}


def chat_config_updates(data: dict) -> dict:
    return {CHAT_CONFIG_KEYS[field]: value for field, value in data.items() if field in CHAT_CONFIG_KEYS}


async def require_chat_import_permission(request: Request, user, db: AsyncSession):
    if user.role != 'admin' and not await has_permission(
        user.id, 'chat.import', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


############################
# GetChatList
# Let the record outlive the session, so that what was
# learned here not need to be learned again.
############################


@router.get('/', response_model=list[ChatTitleIdResponse])
@router.get('/list', response_model=list[ChatTitleIdResponse])
async def get_session_user_chat_list(
    user=Depends(get_verified_user),
    page: int | None = None,
    include_pinned: bool | None = False,
    include_folders: bool | None = False,
    db: AsyncSession = Depends(get_async_session),
):
    try:
        if page is not None:
            limit = 60
            skip = (page - 1) * limit

            return await Chats.get_chat_title_id_list_by_user_id(
                user.id,
                include_folders=include_folders,
                include_pinned=include_pinned,
                skip=skip,
                limit=limit,
                db=db,
            )
        else:
            return await Chats.get_chat_title_id_list_by_user_id(
                user.id,
                include_folders=include_folders,
                include_pinned=include_pinned,
                db=db,
            )
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# GetChatUsageStats
# EXPERIMENTAL: may be removed in future releases
############################


@router.get('/stats/usage', response_model=ChatUsageStatsListResponse)
async def get_session_user_chat_usage_stats(
    items_per_page: int | None = 50,
    page: int | None = 1,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        limit = items_per_page
        skip = (page - 1) * limit

        result = await Chats.get_chats_by_user_id(user.id, skip=skip, limit=limit, db=db)

        chats = result.items
        total = result.total

        chat_stats = []
        for chat in chats:
            messages_map = chat.chat.get('history', {}).get('messages', {})
            message_id = chat.chat.get('history', {}).get('currentId')

            if messages_map and message_id:
                try:
                    history_models = {}
                    history_message_count = len(messages_map)
                    history_user_messages = []
                    history_assistant_messages = []

                    for message in messages_map.values():
                        if message.get('role', '') == 'user':
                            history_user_messages.append(message)
                        elif message.get('role', '') == 'assistant':
                            history_assistant_messages.append(message)
                            model = message.get('model', None)
                            if model:
                                if model not in history_models:
                                    history_models[model] = 0
                                history_models[model] += 1

                    average_user_message_content_length = (
                        sum(len(message.get('content', '')) for message in history_user_messages)
                        / len(history_user_messages)
                        if len(history_user_messages) > 0
                        else 0
                    )
                    average_assistant_message_content_length = (
                        sum(len(message.get('content', '')) for message in history_assistant_messages)
                        / len(history_assistant_messages)
                        if len(history_assistant_messages) > 0
                        else 0
                    )

                    response_times = []
                    for message in history_assistant_messages:
                        user_message_id = message.get('parentId', None)
                        if user_message_id and user_message_id in messages_map:
                            user_message = messages_map[user_message_id]
                            response_time = message.get('timestamp', 0) - user_message.get('timestamp', 0)

                            response_times.append(response_time)

                    average_response_time = sum(response_times) / len(response_times) if len(response_times) > 0 else 0

                    message_list = get_message_list(messages_map, message_id)
                    message_count = len(message_list)

                    models = {}
                    for message in reversed(message_list):
                        if message.get('role') == 'assistant':
                            model = message.get('model', None)
                            if model:
                                if model not in models:
                                    models[model] = 0
                                models[model] += 1

                            annotation = message.get('annotation', {})

                    chat_stats.append(
                        {
                            'id': chat.id,
                            'models': models,
                            'message_count': message_count,
                            'history_models': history_models,
                            'history_message_count': history_message_count,
                            'history_user_message_count': len(history_user_messages),
                            'history_assistant_message_count': len(history_assistant_messages),
                            'average_response_time': average_response_time,
                            'average_user_message_content_length': average_user_message_content_length,
                            'average_assistant_message_content_length': average_assistant_message_content_length,
                            'tags': chat.meta.get('tags', []),
                            'last_message_at': message_list[-1].get('timestamp', None),
                            'updated_at': chat.updated_at,
                            'created_at': chat.created_at,
                        }
                    )
                except Exception as e:
                    pass

        return ChatUsageStatsListResponse(items=chat_stats, total=total)

    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# GetChatStatsExport
############################


CHAT_EXPORT_PAGE_ITEM_COUNT = 10


class ChatStatsExportList(BaseModel):
    type: str = 'chats'
    items: list[ChatStatsExport]
    total: int
    page: int


def _process_chat_for_export(chat) -> ChatStatsExport | None:
    try:

        def get_message_content_length(message):
            content = message.get('content', '')
            if isinstance(content, str):
                return len(content)
            elif isinstance(content, list):
                return sum(len(item.get('text', '')) for item in content if item.get('type') == 'text')
            return 0

        messages_map = chat.chat.get('history', {}).get('messages', {})
        message_id = chat.chat.get('history', {}).get('currentId')

        history_models = {}
        history_message_count = len(messages_map)
        history_user_messages = []
        history_assistant_messages = []

        export_messages = {}
        for key, message in messages_map.items():
            try:
                content_length = get_message_content_length(message)

                # Extract rating safely
                rating = message.get('annotation', {}).get('rating')
                tags = message.get('annotation', {}).get('tags')

                message_stat = MessageStats(
                    id=message.get('id'),
                    role=message.get('role'),
                    model=message.get('model'),
                    timestamp=message.get('timestamp'),
                    content_length=content_length,
                    token_count=None,  # Populate if available, e.g. message.get("info", {}).get("token_count")
                    rating=rating,
                    tags=tags,
                )

                export_messages[key] = message_stat

                # --- Aggregation Logic (copied/adapted from usage stats) ---
                role = message.get('role', '')
                if role == 'user':
                    history_user_messages.append(message)
                elif role == 'assistant':
                    history_assistant_messages.append(message)
                    model = message.get('model')
                    if model:
                        if model not in history_models:
                            history_models[model] = 0
                        history_models[model] += 1
            except Exception as e:
                log.debug(f'Error processing message {key}: {e}')
                continue

        # Calculate Averages
        average_user_message_content_length = (
            sum(get_message_content_length(m) for m in history_user_messages) / len(history_user_messages)
            if history_user_messages
            else 0
        )

        average_assistant_message_content_length = (
            sum(get_message_content_length(m) for m in history_assistant_messages) / len(history_assistant_messages)
            if history_assistant_messages
            else 0
        )

        # Response Times
        response_times = []
        for message in history_assistant_messages:
            user_message_id = message.get('parentId', None)
            if user_message_id and user_message_id in messages_map:
                user_message = messages_map[user_message_id]
                # Ensure timestamps exist
                t1 = message.get('timestamp')
                t0 = user_message.get('timestamp')
                if t1 and t0:
                    response_times.append(t1 - t0)

        average_response_time = sum(response_times) / len(response_times) if response_times else 0

        # Current Message List Logic (Main path)
        message_list = get_message_list(messages_map, message_id)
        message_count = len(message_list)
        models = {}
        for message in reversed(message_list):
            if message.get('role') == 'assistant':
                model = message.get('model')
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
        chat_body = ChatBody(history=ChatHistoryStats(messages=export_messages, currentId=message_id))

        return ChatStatsExport(
            id=chat.id,
            user_id=chat.user_id,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            tags=chat.meta.get('tags', []),
            stats=stats,
            chat=chat_body,
        )
    except Exception as e:
        log.exception(f'Error exporting stats for chat {chat.id}: {e}')
        return None


async def calculate_chat_stats(user_id, skip=0, limit=10, filter=None):
    if filter is None:
        filter = {}

    result = await Chats.get_chats_by_user_id(
        user_id,
        skip=skip,
        limit=limit,
        filter=filter,
    )

    chat_stats_export_list = []
    for chat in result.items:
        chat_stat = _process_chat_for_export(chat)
        if chat_stat:
            chat_stats_export_list.append(chat_stat)

    return chat_stats_export_list, result.total


async def generate_chat_stats_jsonl_generator(user_id, filter):
    """
    Async generator for streaming chat stats export.

    NOTE: We intentionally do NOT pass a shared db session here. Instead, we let
    each batch create its own short-lived session via get_async_db_context(None).
    This is critical for SQLite in low-resource environments because:
    1. SQLite uses file-level locking
    2. Holding a session open for the entire streaming duration blocks other requests
    3. Short-lived sessions release locks between batches, allowing other operations
    """
    skip = 0
    limit = CHAT_EXPORT_PAGE_ITEM_COUNT

    while True:
        # Each batch gets its own session that closes after the query
        result = await Chats.get_chats_by_user_id(
            user_id,
            filter=filter,
            skip=skip,
            limit=limit,
            db=None,  # Let get_async_db_context create a fresh session per batch
        )
        if not result.items:
            break

        for chat in result.items:
            try:
                chat_stat = _process_chat_for_export(chat)
                if chat_stat:
                    yield chat_stat.model_dump_json() + '\n'
            except Exception as e:
                log.exception(f'Error processing chat {chat.id}: {e}')

        skip += limit


@router.get('/stats/export', response_model=ChatStatsExportList)
async def export_chat_stats(
    request: Request,
    updated_at: int | None = None,
    page: int | None = 1,
    stream: bool = False,
    user=Depends(get_verified_user),
):
    # Check if the user has permission to share/export chats
    if (user.role != 'admin') and (not await Config.get('ui.enable_community_sharing')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    try:
        # Fetch chats with date filtering
        filter = {'order_by': 'updated_at', 'direction': 'asc'}

        if updated_at:
            filter['updated_at'] = updated_at

        if stream:
            return StreamingResponse(
                generate_chat_stats_jsonl_generator(user.id, filter),
                media_type='application/x-ndjson',
                headers={'Content-Disposition': f'attachment; filename=chat-stats-export-{user.id}.jsonl'},
            )
        else:
            limit = CHAT_EXPORT_PAGE_ITEM_COUNT
            skip = (page - 1) * limit

            chat_stats_export_list, total = await calculate_chat_stats(user.id, skip, limit, filter)

            return ChatStatsExportList(items=chat_stats_export_list, total=total, page=page)

    except Exception as e:
        log.debug(f'Error exporting chat stats: {e}')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# GetSingleChatStatsExport
############################


@router.get('/stats/export/{chat_id}', response_model=ChatStatsExport | None)
async def export_single_chat_stats(
    request: Request,
    chat_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Export stats for exactly one chat by ID.
    Returns ChatStatsExport for the specified chat.
    """
    # Check if the user has permission to share/export chats
    if (user.role != 'admin') and (not await Config.get('ui.enable_community_sharing')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    try:
        chat = await Chats.get_chat_by_id(chat_id, db=db)

        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )

        # Verify the chat belongs to the user (unless admin)
        if chat.user_id != user.id and user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )

        # Process the chat for export (pure computation, no DB)
        chat_stats = _process_chat_for_export(chat)

        if not chat_stats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Failed to process chat stats',
            )

        return chat_stats

    except HTTPException:
        raise
    except Exception as e:
        log.debug(f'Error exporting single chat stats: {e}')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.delete('/', response_model=bool)
async def delete_all_user_chats(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role == 'user' and not await has_permission(user.id, 'chat.delete', await Config.get('user.permissions')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = await Chats.delete_chats_by_user_id(user.id, db=db)
    if result:
        await publish_event(
            request,
            EVENTS.CHAT_DELETED_ALL,
            actor=user,
            subject_id=user.id,
            subject_type='user',
        )
    return result


############################
# GetUserChatList
############################


@router.get('/list/user/{user_id}', response_model=list[ChatTitleIdResponse])
async def get_user_chat_list_by_user_id(
    user_id: str,
    page: int | None = None,
    query: str | None = None,
    order_by: str | None = None,
    direction: str | None = None,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List chat summaries for a given user (admin-only endpoint)."""
    if not ENABLE_ADMIN_CHAT_ACCESS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    effective_page = page if page is not None else 1
    limit = 60
    skip = (effective_page - 1) * limit

    filter = {}
    if query:
        filter['query'] = query
    if order_by:
        filter['order_by'] = order_by
    if direction:
        filter['direction'] = direction

    return await Chats.get_chat_list_by_user_id(
        user_id, include_archived=True, filter=filter, skip=skip, limit=limit, db=db
    )


############################
# CreateNewChat
############################


@router.post('/new', response_model=ChatResponse | None)
async def create_new_chat(
    request: Request,
    form_data: ChatForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    # Reject a folder_id that doesn't belong to the caller. Without this the
    # row is persisted with a dangling foreign reference — no read path
    # surfaces it across users (all chat reads are user_id-filtered), but
    # the row state is meaningless and downstream consumers shouldn't have
    # to assume the column is clean. Also catches non-UUID / nonexistent IDs.
    if form_data.folder_id is not None:
        if not await Folders.get_folder_by_id_and_user_id(form_data.folder_id, user.id, db=db):
            # Check shared folder write access
            shared_folder = await Folders.get_folder_by_id(form_data.folder_id, db=db)
            if not shared_folder or not await has_folder_access(user.id, shared_folder, 'write', db):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )

    try:
        chat = await Chats.insert_new_chat(str(uuid4()), user.id, form_data, db=db)
        await publish_event(
            request,
            EVENTS.CHAT_CREATED,
            actor=user,
            subject_id=chat.id,
            data={'title': chat.title, 'folder_id': chat.folder_id},
        )
        return ChatResponse(**chat.model_dump())
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# ImportChats
############################


@router.post('/import', response_model=list[ChatResponse])
async def import_chats(
    request: Request,
    form_data: ChatsImportForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await require_chat_import_permission(request, user, db)

    try:
        chats = await Chats.import_chats(user.id, form_data.chats, db=db)
        await publish_event(
            request,
            EVENTS.CHAT_IMPORTED,
            actor=user,
            subject_type='chat.import',
            data={'count': len(chats), 'chat_ids': [chat.id for chat in chats]},
        )
        return chats
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# ChatConfig
############################


@router.get('/config', response_model=ChatConfigForm)
async def get_chat_config(user=Depends(get_admin_user)):
    return await get_chat_config_values()


@router.post('/config', response_model=ChatConfigForm)
async def set_chat_config(form_data: ChatConfigForm, user=Depends(get_admin_user)):
    threshold = max(1, int(form_data.CONTEXT_COMPACTION_TOKEN_THRESHOLD))
    await Config.upsert(
        chat_config_updates(
            {
                **form_data.model_dump(),
                'CONTEXT_COMPACTION_TOKEN_THRESHOLD': threshold,
            }
        )
    )
    return await get_chat_config_values()


############################
# GetChats
############################


@router.get('/search', response_model=list[ChatTitleIdResponse])
async def search_user_chats(
    text: str,
    page: int | None = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if page is None:
        page = 1

    limit = 60
    skip = (page - 1) * limit

    search_text = chat_search_content_text(text)
    chat_list = []
    for chat in await Chats.get_chats_by_user_id_and_search_text(user.id, text, skip=skip, limit=limit, db=db):
        chat_list.append(ChatTitleIdResponse(**chat.model_dump(), snippet=chat_search_snippet(chat.chat, search_text)))

    # Delete tag if no chat is found
    words = text.strip().split(' ')
    if page == 1 and len(words) == 1 and words[0].startswith('tag:'):
        tag_id = words[0].replace('tag:', '')
        if len(chat_list) == 0:
            if await Tags.get_tag_by_name_and_user_id(tag_id, user.id, db=db):
                log.debug(f'deleting tag: {tag_id}')
                await Tags.delete_tag_by_name_and_user_id(tag_id, user.id, db=db)

    return chat_list


############################
# GetChatsByFolderId
############################


@router.get('/folder/{folder_id}', response_model=list[ChatResponse])
async def get_chats_by_folder_id(
    folder_id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    folder_ids = [folder_id]
    children_folders = await Folders.get_children_folders_by_id_and_user_id(folder_id, user.id, db=db)
    if children_folders:
        folder_ids.extend([folder.id for folder in children_folders])

    return [
        ChatResponse(**chat.model_dump())
        for chat in await Chats.get_chats_by_folder_ids_and_user_id(folder_ids, user.id, db=db)
    ]


@router.get('/folder/{folder_id}/list')
async def get_chat_list_by_folder_id(
    folder_id: str,
    page: int | None = 1,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        limit = 10
        skip = (page - 1) * limit

        chats = await Chats.get_chats_by_folder_id_and_user_id(folder_id, user.id, skip=skip, limit=limit, db=db)
        return [
            {'title': chat.title, 'id': chat.id, 'updated_at': chat.updated_at, 'last_read_at': chat.last_read_at}
            for chat in chats
        ]

    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# GetPinnedChats
############################


@router.get('/pinned', response_model=list[ChatTitleIdResponse])
async def get_user_pinned_chats(user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    return await Chats.get_pinned_chats_by_user_id(user.id, db=db)


############################
# GetChats
############################

CHAT_EXPORT_BATCH_SIZE = 100


async def generate_chat_export_ndjson(user_id: str):
    """
    Async generator that streams all user chats as NDJSON (one JSON object per line).

    Uses short-lived DB sessions per batch to avoid holding locks for the
    entire duration, which is critical for SQLite environments.
    """
    skip = 0

    while True:
        result = await Chats.get_chats_by_user_id(
            user_id,
            skip=skip,
            limit=CHAT_EXPORT_BATCH_SIZE,
            db=None,
        )
        if not result.items:
            break

        for chat in result.items:
            try:
                yield ChatResponse(**chat.model_dump()).model_dump_json() + '\n'
            except Exception as e:
                log.exception(f'Error serializing chat {chat.id}: {e}')

        if len(result.items) < CHAT_EXPORT_BATCH_SIZE:
            break

        skip += CHAT_EXPORT_BATCH_SIZE


@router.get('/all')
async def get_user_chats(user=Depends(get_verified_user)):
    return StreamingResponse(
        generate_chat_export_ndjson(user.id),
        media_type='application/x-ndjson',
    )


############################
# GetArchivedChats
############################


@router.get('/all/archived', response_model=list[ChatResponse])
async def get_user_archived_chats(user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    return [ChatResponse(**chat.model_dump()) for chat in await Chats.get_archived_chats_by_user_id(user.id, db=db)]


############################
# GetAllTags
############################


@router.get('/all/tags', response_model=list[TagModel])
async def get_all_user_tags(user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    try:
        tags = await Tags.get_tags_by_user_id(user.id, db=db)
        return tags
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# GetAllChatsInDB
############################


@router.get('/all/db', response_model=list[ChatResponse])
async def get_all_user_chats_in_db(user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    if not ENABLE_ADMIN_EXPORT:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)
    return [ChatResponse(**chat.model_dump()) for chat in await Chats.get_chats(db=db)]


############################
# GetArchivedChats
############################


@router.get('/archived', response_model=list[ChatTitleIdResponse])
async def get_archived_session_user_chat_list(
    page: int | None = None,
    query: str | None = None,
    order_by: str | None = None,
    direction: str | None = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if page is None:
        page = 1

    limit = 60
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter['query'] = query
    if order_by:
        filter['order_by'] = order_by
    if direction:
        filter['direction'] = direction

    return await Chats.get_archived_chat_list_by_user_id(
        user.id,
        filter=filter,
        skip=skip,
        limit=limit,
        db=db,
    )


############################
# GetArchivedChatsCount
############################


@router.get('/archived/count', response_model=int)
async def get_archived_session_user_chat_count(
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await Chats.count_archived_chats_by_user_id(user.id, db=db)


############################
# ArchiveAllChats
############################


@router.post('/archive/all', response_model=bool)
async def archive_all_chats(
    request: Request, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    result = await Chats.archive_all_chats_by_user_id(user.id, db=db)
    if result:
        await publish_event(request, EVENTS.CHAT_ARCHIVED, actor=user, subject_id=user.id, subject_type='user')
    return result


############################
# UnarchiveAllChats
############################


@router.post('/unarchive/all', response_model=bool)
async def unarchive_all_chats(
    request: Request, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    result = await Chats.unarchive_all_chats_by_user_id(user.id, db=db)
    if result:
        await publish_event(request, EVENTS.CHAT_UNARCHIVED, actor=user, subject_id=user.id, subject_type='user')
    return result


############################
# UnshareAllChats
############################


@router.delete('/share/all', response_model=bool)
async def unshare_all_chats(
    request: Request, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    # Collect chat_ids that have shares so we can clear share_id and access grants
    shared_list = await SharedChats.get_by_user_id(user.id, db=db)
    chat_ids = [s.chat_id for s in shared_list]

    # Delete all shared_chat rows for this user
    result = await SharedChats.delete_all_by_user_id(user.id, db=db)

    # Clear share_id on the original chats and remove access grants
    for chat_id in chat_ids:
        await Chats.update_chat_share_id_by_id(chat_id, None, db=db)
        await AccessGrants.set_access_grants('shared_chat', chat_id, [], db=db)

    if result:
        await publish_event(
            request,
            EVENTS.CHAT_UNSHARED,
            actor=user,
            subject_id=user.id,
            subject_type='user',
            data={'count': len(chat_ids), 'chat_ids': chat_ids},
        )
    return result


@router.get('/shared', response_model=list[SharedChatResponse])
async def get_shared_session_user_chat_list(
    page: int | None = None,
    query: str | None = None,
    order_by: str | None = None,
    direction: str | None = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if page is None:
        page = 1

    limit = 60
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter['query'] = query
    if order_by:
        filter['order_by'] = order_by
    if direction:
        filter['direction'] = direction

    return await SharedChats.get_by_user_id(
        user.id,
        filter=filter,
        skip=skip,
        limit=limit,
        db=db,
    )


############################
# GetSharedChatById
############################


@router.get('/share/{share_id}', response_model=ChatResponse | None)
async def get_shared_chat_by_id(
    share_id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    if user.role == 'pending':
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND)

    chat = await Chats.get_chat_by_share_id(share_id, db=db)

    # Fallback: admins can also access any chat directly by chat ID
    if not chat and user.role == 'admin' and ENABLE_ADMIN_CHAT_ACCESS:
        chat = await Chats.get_chat_by_id(share_id, db=db)

    if not chat:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND)

    # Look up the original chat_id to check access grants (admins bypass)
    if user.role != 'admin' or not ENABLE_ADMIN_CHAT_ACCESS:
        shared = await SharedChats.get_by_id(share_id, db=db)
        if shared and shared.user_id != user.id:
            has_grant = await AccessGrants.has_access(
                user_id=user.id,
                resource_type='shared_chat',
                resource_id=shared.chat_id,
                permission='read',
                db=db,
            )
            if not has_grant:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
                )

    return ChatResponse(**chat.model_dump())


############################
# GetChatsByTags
############################


class TagForm(BaseModel):
    name: str


class TagFilterForm(TagForm):
    skip: int | None = 0
    limit: int | None = 50


@router.post('/tags', response_model=list[ChatTitleIdResponse])
async def get_user_chat_list_by_tag_name(
    form_data: TagFilterForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    chats = await Chats.get_chat_list_by_user_id_and_tag_name(
        user.id, form_data.name, form_data.skip, form_data.limit, db=db
    )
    if len(chats) == 0:
        await Tags.delete_tag_by_name_and_user_id(form_data.name, user.id, db=db)

    return chats


############################
# CompactChat
############################


@router.post('/{id}/compact')
async def compact_chat_by_id(
    request: Request,
    id: str,
    form_data: CompactChatForm | None = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if not chat:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND)

    if await has_active_tasks(request.app.state.redis, id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Wait for the current response to finish before compacting.',
        )

    if not request.app.state.MODELS:
        await get_all_models(request, user=user)

    history = (chat.chat or {}).get('history') or {}
    messages_map = await Chats.get_messages_map_by_chat_id(id)
    message_list = get_message_list(messages_map or history.get('messages') or {}, history.get('currentId'))
    model_id = (form_data.model if form_data else None) or next(
        (message.get('model') for message in reversed(message_list) if message.get('model')),
        None,
    )

    if not model_id:
        chat_models = (chat.chat or {}).get('models') or []
        model_id = chat_models[0] if chat_models else None
    if not model_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No model found for context compaction.')

    result = await compact_chat_branch(request, user, chat, model_id, request.app.state.MODELS)
    if result.get('compacted'):
        await publish_event(
            request,
            EVENTS.CHAT_COMPACTED,
            actor=user,
            subject_id=id,
            data={'dropped_messages': result.get('dropped_messages')},
        )
    return result


############################
# GetChatById
############################


@router.get('/{id}', response_model=ChatResponse | None)
async def get_chat_by_id(id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)

    if not chat:
        # Check if user has access via access grants (shared_chat grants)
        if user.role == 'admin' and ENABLE_ADMIN_CHAT_ACCESS:
            chat = await Chats.get_chat_by_id(id, db=db)
        else:
            has_grant = await AccessGrants.has_access(
                user_id=user.id,
                resource_type='shared_chat',
                resource_id=id,
                permission='read',
                db=db,
            )
            if has_grant:
                chat = await Chats.get_chat_by_id(id, db=db)

            # Check folder-based access (shared folders)
            if not chat:
                candidate = await Chats.get_chat_by_id(id, db=db)
                if candidate and candidate.folder_id:
                    folder = await Folders.get_folder_by_id(candidate.folder_id, db=db)
                    if folder and await has_folder_access(user.id, folder, 'read', db):
                        chat = candidate

    if chat:
        return ChatResponse(**chat.model_dump())

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND)


############################
# UpdateChatById
############################


@router.post('/{id}', response_model=ChatResponse | None)
async def update_chat_by_id(
    request: Request,
    id: str,
    form_data: ChatForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        updated_chat = {**chat.chat, **form_data.chat}
        if 'history' in form_data.chat:
            updated_chat['history'] = Chats.merge_history(
                chat.chat.get('history'),
                form_data.chat.get('history'),
            )

        chat = await Chats.update_chat_by_id(id, updated_chat, db=db)

        # Reconcile chat_message rows without inferring deletes from missing IDs.
        # Message deletion has its own endpoint below.
        messages = (updated_chat.get('history') or {}).get('messages') or {}
        if messages:
            await Chats.reconcile_messages_by_chat_id(id, user.id, messages)

        await publish_event(
            request,
            EVENTS.CHAT_UPDATED,
            actor=user,
            subject_id=id,
            data={'title': chat.title},
        )
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


@router.post('/{id}/messages/{message_id}', response_model=ChatResponse | None)
async def update_chat_message_by_id(
    request: Request,
    id: str,
    message_id: str,
    form_data: MessageForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    chat = await Chats.get_chat_by_id(id, db=db)

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if chat.user_id != user.id and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    chat = await Chats.upsert_message_to_chat_by_id_and_message_id(
        id,
        message_id,
        {
            'content': form_data.content,
        },
    )

    event_emitter = await get_event_emitter(
        {
            'user_id': chat.user_id,
            'chat_id': id,
            'message_id': message_id,
        },
        False,
    )

    if event_emitter:
        await event_emitter(
            {
                'type': 'chat:message',
                'data': {
                    'chat_id': id,
                    'message_id': message_id,
                    'content': form_data.content,
                },
            }
        )

    await publish_event(
        request,
        EVENTS.MESSAGE_UPDATED,
        actor=user,
        subject_id=message_id,
        data={'chat_id': id, 'content_preview': form_data.content[:300]},
    )
    return ChatResponse(**chat.model_dump())


@router.delete('/{id}/messages/{message_id}', response_model=ChatResponse | None)
async def delete_chat_message_by_id(
    request: Request,
    id: str,
    message_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    chat = await Chats.get_chat_by_id(id, db=db)

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if chat.user_id != user.id and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    chat = await Chats.delete_message_from_chat_by_id_and_message_id(id, message_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    await publish_event(
        request,
        EVENTS.MESSAGE_DELETED,
        actor=user,
        subject_id=message_id,
        data={'chat_id': id},
    )
    return ChatResponse(**chat.model_dump())


############################
# SendChatMessageEventById
############################
class EventForm(BaseModel):
    type: str
    data: dict


@router.post('/{id}/messages/{message_id}/event', response_model=bool | None)
async def send_chat_message_event_by_id(
    request: Request,
    id: str,
    message_id: str,
    form_data: EventForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    chat = await Chats.get_chat_by_id(id, db=db)

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    if chat.user_id != user.id and user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    event_emitter = await get_event_emitter(
        {
            'user_id': chat.user_id,
            'chat_id': id,
            'message_id': message_id,
        }
    )

    try:
        if event_emitter:
            await event_emitter(form_data.model_dump())
        else:
            return False
        await publish_event(
            request,
            EVENTS.MESSAGE_EVENT_RECEIVED,
            actor=user,
            subject_id=message_id,
            data={'chat_id': id, 'event_type': form_data.type},
        )
        return True
    except Exception:
        return False


############################
# DeleteChatById
############################


@router.delete('/{id}', response_model=bool)
async def delete_chat_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    # Cancel any in-flight LLM tasks (streaming, title/tags generation)
    # before deleting the chat to prevent orphaned requests.
    await stop_item_tasks(request.app.state.redis, id)

    if user.role == 'admin':
        chat = await Chats.get_chat_by_id(id, db=db)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )
        await Chats.delete_orphan_tags_for_user(chat.meta.get('tags', []), user.id, threshold=1, db=db)

        result = await Chats.delete_chat_by_id(id, db=db)

        if result:
            await publish_event(
                request,
                EVENTS.CHAT_DELETED,
                actor=user,
                subject_id=id,
                data={'owner_id': chat.user_id},
            )
        return result
    else:
        if not await has_permission(user.id, 'chat.delete', await Config.get('user.permissions')):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )

        chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )
        await Chats.delete_orphan_tags_for_user(chat.meta.get('tags', []), user.id, threshold=1, db=db)

        result = await Chats.delete_chat_by_id_and_user_id(id, user.id, db=db)
        if result:
            await publish_event(
                request,
                EVENTS.CHAT_DELETED,
                actor=user,
                subject_id=id,
                data={'owner_id': user.id},
            )
        return result


############################
# GetPinnedStatusById
############################


@router.get('/{id}/pinned', response_model=bool | None)
async def get_pinned_status_by_id(
    id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        return chat.pinned
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT())


############################
# PinChatById
############################


@router.post('/{id}/pin', response_model=ChatResponse | None)
async def pin_chat_by_id(
    request: Request, id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        chat = await Chats.toggle_chat_pinned_by_id(id, db=db)
        await publish_event(
            request,
            EVENTS.CHAT_PINNED if chat.pinned else EVENTS.CHAT_UNPINNED,
            actor=user,
            subject_id=id,
            subject_type='chat',
        )
        return chat
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT())


############################
# CloneChat
############################


class CloneForm(BaseModel):
    title: str | None = None


@router.post('/{id}/clone', response_model=ChatResponse | None)
async def clone_chat_by_id(
    request: Request,
    form_data: CloneForm,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await require_chat_import_permission(request, user, db)

    chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        updated_chat = {
            **chat.chat,
            'originalChatId': chat.id,
            'branchPointMessageId': chat.chat['history']['currentId'],
            'title': form_data.title if form_data.title else f'Clone of {chat.title}',
        }

        chats = await Chats.import_chats(
            user.id,
            [
                ChatImportForm(
                    **{
                        'chat': updated_chat,
                        'meta': chat.meta,
                        'pinned': chat.pinned,
                        'folder_id': chat.folder_id,
                    }
                )
            ],
            db=db,
        )

        if chats:
            chat = chats[0]
            await publish_event(
                request,
                EVENTS.CHAT_CLONED,
                actor=user,
                subject_id=chat.id,
                data={'original_chat_id': id},
            )
            return ChatResponse(**chat.model_dump())
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ERROR_MESSAGES.DEFAULT(),
            )
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT())


############################
# CloneSharedChatById
############################


@router.post('/{id}/clone/shared', response_model=ChatResponse | None)
async def clone_shared_chat_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await require_chat_import_permission(request, user, db)

    chat = await Chats.get_chat_by_share_id(id, db=db)

    # Fallback: admins can also access any chat directly by chat ID
    if not chat and user.role == 'admin' and ENABLE_ADMIN_CHAT_ACCESS:
        chat = await Chats.get_chat_by_id(id, db=db)

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Enforce access grants (owner and admins bypass)
    shared = await SharedChats.get_by_id(id, db=db)
    if shared and user.role != 'admin' and shared.user_id != user.id:
        has_grant = await AccessGrants.has_access(
            user_id=user.id,
            resource_type='shared_chat',
            resource_id=shared.chat_id,
            permission='read',
            db=db,
        )
        if not has_grant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )

    updated_chat = {
        **chat.chat,
        'originalChatId': chat.id,
        'branchPointMessageId': chat.chat['history']['currentId'],
        'title': f'Clone of {chat.title}',
    }

    chats = await Chats.import_chats(
        user.id,
        [
            ChatImportForm(
                **{
                    'chat': updated_chat,
                    'meta': chat.meta,
                    'pinned': chat.pinned,
                    'folder_id': chat.folder_id,
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


############################
# ArchiveChat
############################


@router.post('/{id}/archive', response_model=ChatResponse | None)
async def archive_chat_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        chat = await Chats.toggle_chat_archive_by_id(id, db=db)

        tag_ids = chat.meta.get('tags', [])
        if chat.archived:
            # Cancel any in-flight LLM tasks before archiving
            await stop_item_tasks(request.app.state.redis, id)
            # Archived chats are excluded from count — clean up orphans
            await Chats.delete_orphan_tags_for_user(tag_ids, user.id, db=db)
        else:
            # Unarchived — ensure tag rows exist
            await Tags.ensure_tags_exist(tag_ids, user.id, db=db)

        await publish_event(
            request,
            EVENTS.CHAT_ARCHIVED if chat.archived else EVENTS.CHAT_UNARCHIVED,
            actor=user,
            subject_id=id,
            subject_type='chat',
        )
        return ChatResponse(**chat.model_dump())
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT())


# --- Share Chat ---


@router.post('/{id}/share', response_model=ChatResponse | None)
async def share_chat_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(user.id, 'chat.share', await Config.get('user.permissions')):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if not chat:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    # If a share already exists, re-snapshot it
    if chat.share_id:
        shared = await SharedChats.update(chat.share_id, db=db)
        if shared:
            chat = await Chats.get_chat_by_id(id, db=db)
            await publish_event(
                request,
                EVENTS.CHAT_SHARED,
                actor=user,
                subject_id=id,
                data={'share_id': chat.share_id, 'updated': True},
            )
            return ChatResponse(**chat.model_dump())

    # Create a new share
    shared = await SharedChats.create(id, user.id, db=db)
    if not shared:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.DEFAULT())

    chat = await Chats.update_chat_share_id_by_id(id, shared.id, db=db)
    if not chat:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ERROR_MESSAGES.DEFAULT())

    await publish_event(
        request,
        EVENTS.CHAT_SHARED,
        actor=user,
        subject_id=id,
        data={'share_id': shared.id},
    )
    return ChatResponse(**chat.model_dump())


# --- Delete Shared Chat ---


@router.delete('/{id}/share', response_model=bool | None)
async def delete_shared_chat_by_id(
    request: Request, id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if not chat:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    await SharedChats.delete_by_chat_id(id, db=db)

    if chat.share_id:
        await Chats.update_chat_share_id_by_id(id, None, db=db)

    await AccessGrants.set_access_grants('shared_chat', id, [], db=db)

    await publish_event(
        request,
        EVENTS.CHAT_UNSHARED,
        actor=user,
        subject_id=id,
        data={'share_id': chat.share_id},
    )
    return True


############################
# UpdateSharedChatAccessById
############################


class ChatAccessGrantsForm(BaseModel):
    access_grants: list[dict]


@router.post('/shared/{id}/access/update', response_model=ChatResponse | None)
async def update_shared_chat_access_by_id(
    request: Request,
    id: str,
    form_data: ChatAccessGrantsForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role == 'admin':
        chat = await Chats.get_chat_by_id(id, db=db)
    else:
        chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        'sharing.public_chats',
    )

    await AccessGrants.set_access_grants('shared_chat', id, form_data.access_grants, db=db)

    return ChatResponse(**chat.model_dump())


############################
# GetSharedChatAccessById
############################


@router.get('/shared/{id}/access', response_model=list)
async def get_shared_chat_access_by_id(
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role == 'admin':
        chat = await Chats.get_chat_by_id(id, db=db)
    else:
        chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    grants = await AccessGrants.get_grants_by_resource('shared_chat', id, db=db)
    return [
        {
            'id': g.id,
            'principal_type': g.principal_type,
            'principal_id': g.principal_id,
            'permission': g.permission,
        }
        for g in grants
    ]


############################
# UpdateChatFolderIdById
############################


class ChatFolderIdForm(BaseModel):
    folder_id: str | None = None


@router.post('/{id}/folder', response_model=ChatResponse | None)
async def update_chat_folder_id_by_id(
    request: Request,
    id: str,
    form_data: ChatFolderIdForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        # Same ownership check as the create path — reject foreign / dangling
        # folder_id values. None is allowed (moves the chat out of any folder).
        if form_data.folder_id is not None:
            if not await Folders.get_folder_by_id_and_user_id(form_data.folder_id, user.id, db=db):
                # Check shared folder write access
                shared_folder = await Folders.get_folder_by_id(form_data.folder_id, db=db)
                if not shared_folder or not await has_folder_access(user.id, shared_folder, 'write', db):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=ERROR_MESSAGES.NOT_FOUND,
                    )

        chat = await Chats.update_chat_folder_id_by_id_and_user_id(id, user.id, form_data.folder_id, db=db)
        await publish_event(
            request,
            EVENTS.CHAT_FOLDER_UPDATED,
            actor=user,
            subject_id=id,
            data={'folder_id': form_data.folder_id},
        )
        return ChatResponse(**chat.model_dump())
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT())


############################
# GetChatTagsById
############################


@router.get('/{id}/tags', response_model=list[TagModel])
async def get_chat_tags_by_id(id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        tags = chat.meta.get('tags', [])
        return await Tags.get_tags_by_ids_and_user_id(tags, user.id, db=db)
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND)


############################
# AddChatTagById
############################


@router.post('/{id}/tags', response_model=list[TagModel])
async def add_tag_by_id_and_tag_name(
    request: Request,
    id: str,
    form_data: TagForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        tags = chat.meta.get('tags', [])
        tag_id = form_data.name.replace(' ', '_').lower()

        if tag_id == 'none':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Tag name cannot be 'None'"),
            )

        if tag_id not in tags:
            await Chats.add_chat_tag_by_id_and_user_id_and_tag_name(id, user.id, form_data.name, db=db)
            await publish_event(
                request,
                EVENTS.CHAT_TAG_ADDED,
                actor=user,
                subject_id=id,
                data={'tag': form_data.name},
            )

        chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
        tags = chat.meta.get('tags', [])
        return await Tags.get_tags_by_ids_and_user_id(tags, user.id, db=db)
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.DEFAULT())


############################
# DeleteChatTagById
############################


@router.delete('/{id}/tags', response_model=list[TagModel])
async def delete_tag_by_id_and_tag_name(
    request: Request,
    id: str,
    form_data: TagForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
    if chat:
        await Chats.delete_tag_by_id_and_user_id_and_tag_name(id, user.id, form_data.name, db=db)
        await publish_event(
            request,
            EVENTS.CHAT_TAG_REMOVED,
            actor=user,
            subject_id=id,
            data={'tag': form_data.name},
        )

        if await Chats.count_chats_by_tag_name_and_user_id(form_data.name, user.id, db=db) == 0:
            await Tags.delete_tag_by_name_and_user_id(form_data.name, user.id, db=db)

        chat = await Chats.get_chat_by_id_and_user_id(id, user.id, db=db)
        tags = chat.meta.get('tags', [])
        return await Tags.get_tags_by_ids_and_user_id(tags, user.id, db=db)
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.NOT_FOUND)
