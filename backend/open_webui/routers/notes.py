import json
import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from open_webui.config import (
    BYPASS_ADMIN_ACCESS_CONTROL,
    ENABLE_ADMIN_CHAT_ACCESS,
    ENABLE_ADMIN_EXPORT,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrants
from open_webui.models.chats import ChatForm, ChatResponse, Chats
from open_webui.models.config import Config
from open_webui.models.groups import Groups
from open_webui.models.notes import (
    NoteForm,
    NoteListResponse,
    NoteModel,
    Notes,
    NoteUserResponse,
)
from open_webui.models.users import UserResponse, Users
from open_webui.socket.main import sio
from open_webui.utils.access_control import (
    filter_allowed_access_grants,
    has_permission,
    has_public_read_access_grant,
    has_public_write_access_grant,
)
from open_webui.utils.auth import get_admin_user, get_verified_user
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()


def _truncate_note_data(data: Optional[dict], max_length: int = 1000) -> Optional[dict]:
    if not data:
        return data
    md = (data.get('content') or {}).get('md') or ''
    return {'content': {'md': md[:max_length]}}


############################
# GetNotes
############################


class NoteItemResponse(BaseModel):
    id: str
    title: str
    data: Optional[dict]
    is_pinned: Optional[bool] = False
    updated_at: int
    created_at: int
    user: Optional[UserResponse] = None


@router.get('/', response_model=list[NoteItemResponse])
async def get_notes(
    request: Request,
    page: Optional[int] = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'features.notes', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    limit = None
    skip = None
    if page is not None:
        limit = 60
        skip = (page - 1) * limit

    notes = await Notes.get_notes_by_user_id(user.id, 'read', skip=skip, limit=limit, db=db)
    if not notes:
        return []

    user_ids = list(set(note.user_id for note in notes))
    users = {user.id: user for user in await Users.get_users_by_user_ids(user_ids, db=db)}

    pinned_note_ids = await Notes.get_pinned_note_ids(user.id, db=db)

    return [
        NoteUserResponse(
            **{
                **note.model_dump(),
                'is_pinned': note.id in pinned_note_ids,
                'data': _truncate_note_data(note.data),
                'user': UserResponse(**users[note.user_id].model_dump()),
            }
        )
        for note in notes
        if note.user_id in users
    ]


############################
# GetPinnedNotes
############################


@router.get('/pinned', response_model=list[NoteItemResponse])
async def get_pinned_notes(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'features.notes', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    notes = await Notes.get_pinned_notes_by_user_id(user.id, 'read', db=db)
    if not notes:
        return []

    user_ids = list(set(note.user_id for note in notes))
    users = {user.id: user for user in await Users.get_users_by_user_ids(user_ids, db=db)}

    return [
        NoteUserResponse(
            **{
                **note.model_dump(),
                'is_pinned': True,
                'data': _truncate_note_data(note.data),
                'user': UserResponse(**users[note.user_id].model_dump()),
            }
        )
        for note in notes
        if note.user_id in users
    ]


@router.get('/search', response_model=NoteListResponse)
async def search_notes(
    request: Request,
    query: Optional[str] = None,
    view_option: Optional[str] = None,
    permission: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'features.notes', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    limit = None
    skip = None
    if page is not None:
        limit = 60
        skip = (page - 1) * limit

    filter = {}
    if query:
        filter['query'] = query
    if view_option:
        filter['view_option'] = view_option
    if permission:
        filter['permission'] = permission
    if order_by:
        filter['order_by'] = order_by
    if direction:
        filter['direction'] = direction

    if not user.role == 'admin' or not BYPASS_ADMIN_ACCESS_CONTROL:
        groups = await Groups.get_groups_by_member_id(user.id, db=db)
        if groups:
            filter['group_ids'] = [group.id for group in groups]

        filter['user_id'] = user.id

    result = await Notes.search_notes(user.id, filter, skip=skip, limit=limit, db=db)
    pinned_note_ids = await Notes.get_pinned_note_ids(user.id, db=db)
    for note in result.items:
        note.is_pinned = note.id in pinned_note_ids
        note.data = _truncate_note_data(note.data)
    return result


############################
# CreateNewNote
############################


@router.post('/create', response_model=Optional[NoteModel])
async def create_new_note(
    request: Request,
    form_data: NoteForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'features.notes', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        'sharing.public_notes',
        db=db,
    )

    try:
        note = await Notes.insert_new_note(user.id, form_data, db=db)
        await publish_event(
            request,
            EVENTS.NOTE_CREATED,
            actor=user,
            subject_id=note.id,
            data={'title': note.title},
        )
        return note
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# GetNoteById
############################


class NoteResponse(NoteModel):
    write_access: bool = False


@router.get('/{id}', response_model=Optional[NoteResponse])
async def get_note_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'features.notes', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    note = await Notes.get_note_by_id(id, db=db)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if user.role != 'admin' and (
        user.id != note.user_id
        and (
            not await AccessGrants.has_access(
                user_id=user.id,
                resource_type='note',
                resource_id=note.id,
                permission='read',
                db=db,
            )
        )
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    write_access = (
        user.role == 'admin'
        or (user.id == note.user_id)
        or await AccessGrants.has_access(
            user_id=user.id,
            resource_type='note',
            resource_id=note.id,
            permission='write',
            db=db,
        )
        or has_public_write_access_grant(note.access_grants)
    )

    pinned_note_ids = await Notes.get_pinned_note_ids(user.id, db=db)
    return NoteResponse(
        **{**note.model_dump(), 'is_pinned': note.id in pinned_note_ids},
        write_access=write_access,
    )


@router.get('/{id}/chat', response_model=ChatResponse)
async def get_note_chat_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    log.info('[note-chat] get-or-create requested note_id=%s user_id=%s', id, user.id)
    if user.role != 'admin' and not await has_permission(
        user.id, 'features.notes', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    note = await Notes.get_note_by_id(id, db=db)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if user.role != 'admin' and (
        user.id != note.user_id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='note',
            resource_id=note.id,
            permission='read',
            db=db,
        )
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    chat = await Chats.get_internal_chat_by_note_id(note.id, user.id, db=db)
    if chat:
        log.info('[note-chat] reusing hidden chat note_id=%s chat_id=%s user_id=%s', note.id, chat.id, user.id)
        payload = {**(chat.chat or {})}
        params = {**(payload.get('params') or {})}
        changed = False

        if params.pop('note_id', None) is not None:
            changed = True

        system = (
            f'CONTEXT:
Current note id: {note.id}
'
            'This chat is attached to the current note.
'
            'For edit requests like make this concise, rewrite, enhance, shorten, or update: call view_note then replace_note_content.
'
            'Do not say an edit is done unless replace_note_content succeeds.'
        )
        if params.get('system') != system:
            params['system'] = system
            changed = True

        if payload.pop('system', None) is not None:
            changed = True

        payload['params'] = params
        if changed:
            updated_chat = await Chats.update_chat_by_id(chat.id, payload, db=db, touch=False)
            if updated_chat:
                return updated_chat

        return chat

    chat_id = str(uuid4())
    chat = await Chats.insert_new_chat(
        chat_id,
        user.id,
        ChatForm(
            chat={
                'id': chat_id,
                'title': 'Chat',
                'models': [''],
                'params': {
                    'system': (
                        f'CONTEXT:
Current note id: {note.id}
'
            'This chat is attached to the current note.
'
            'For edit requests like make this concise, rewrite, enhance, shorten, or update: call view_note then replace_note_content.
'
            'Do not say an edit is done unless replace_note_content succeeds.'
                    )
                },
                'history': {'messages': {}, 'currentId': None},
                'messages': [],
                'tags': [],
            }
        ),
        db=db,
        internal_meta={'internal': True, 'type': 'note', 'note_id': note.id},
    )
    if not chat:
        log.error('[note-chat] failed creating hidden chat note_id=%s user_id=%s', note.id, user.id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    log.info('[note-chat] created hidden chat note_id=%s chat_id=%s user_id=%s', note.id, chat.id, user.id)
    return chat


@router.get('/{id}/chats', response_model=list[ChatResponse])
async def get_note_chats_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'features.notes', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    note = await Notes.get_note_by_id(id, db=db)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if user.role != 'admin' and (
        user.id != note.user_id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='note',
            resource_id=note.id,
            permission='read',
            db=db,
        )
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    chats = await Chats.get_internal_chats_by_note_id(note.id, user.id, db=db)
    normalized_chats = []
    for chat in chats:
        payload = {**(chat.chat or {})}
        params = {**(payload.get('params') or {})}
        changed = False

        if params.pop('note_id', None) is not None:
            changed = True

        system = (
            f'CONTEXT:
Current note id: {note.id}
'
            'This chat is attached to the current note.
'
            'For edit requests like make this concise, rewrite, enhance, shorten, or update: call view_note then replace_note_content.
'
            'Do not say an edit is done unless replace_note_content succeeds.'
        )
        if params.get('system') != system:
            params['system'] = system
            changed = True

        if payload.pop('system', None) is not None:
            changed = True

        payload['params'] = params
        if changed:
            chat = await Chats.update_chat_by_id(chat.id, payload, db=db, touch=False) or chat

        normalized_chats.append(chat)

    return normalized_chats


@router.post('/{id}/chat', response_model=ChatResponse)
async def create_note_chat_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'features.notes', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    note = await Notes.get_note_by_id(id, db=db)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if user.role != 'admin' and (
        user.id != note.user_id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='note',
            resource_id=note.id,
            permission='read',
            db=db,
        )
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    chat_id = str(uuid4())
    chat = await Chats.insert_new_chat(
        chat_id,
        user.id,
        ChatForm(
            chat={
                'id': chat_id,
                'title': 'Chat',
                'models': [''],
                'params': {
                    'system': (
                        f'CONTEXT:
Current note id: {note.id}
'
            'This chat is attached to the current note.
'
            'For edit requests like make this concise, rewrite, enhance, shorten, or update: call view_note then replace_note_content.
'
            'Do not say an edit is done unless replace_note_content succeeds.'
                    )
                },
                'history': {'messages': {}, 'currentId': None},
                'messages': [],
                'tags': [],
            }
        ),
        db=db,
        internal_meta={'internal': True, 'type': 'note', 'note_id': note.id},
    )
    if not chat:
        log.error('[note-chat] failed creating hidden chat note_id=%s user_id=%s', note.id, user.id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    log.info('[note-chat] created hidden chat note_id=%s chat_id=%s user_id=%s', note.id, chat.id, user.id)
    return chat


############################
# UpdateNoteById
############################


@router.post('/{id}/update', response_model=Optional[NoteModel])
async def update_note_by_id(
    request: Request,
    id: str,
    form_data: NoteForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'features.notes', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    note = await Notes.get_note_by_id(id, db=db)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if user.role != 'admin' and (
        user.id != note.user_id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='note',
            resource_id=note.id,
            permission='write',
            db=db,
        )
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        'sharing.public_notes',
        db=db,
    )

    try:
        note = await Notes.update_note_by_id(id, form_data, db=db)
        pinned_note_ids = await Notes.get_pinned_note_ids(user.id, db=db)
        note.is_pinned = note.id in pinned_note_ids

        await sio.emit(
            'events:note',
            note.model_dump(),
            to=f'note:{note.id}',
        )

        await publish_event(
            request,
            EVENTS.NOTE_UPDATED,
            actor=user,
            subject_id=note.id,
            data={'title': note.title},
        )
        return note
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


############################
# UpdateNoteAccessById
############################


class NoteAccessGrantsForm(BaseModel):
    access_grants: list[dict]


@router.post('/{id}/access/update', response_model=Optional[NoteModel])
async def update_note_access_by_id(
    request: Request,
    id: str,
    form_data: NoteAccessGrantsForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'features.notes', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    note = await Notes.get_note_by_id(id, db=db)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if user.role != 'admin' and (
        user.id != note.user_id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='note',
            resource_id=note.id,
            permission='write',
            db=db,
        )
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        'sharing.public_notes',
    )

    await AccessGrants.set_access_grants('note', id, form_data.access_grants, db=db)

    note = await Notes.get_note_by_id(id, db=db)
    pinned_note_ids = await Notes.get_pinned_note_ids(user.id, db=db)
    note.is_pinned = note.id in pinned_note_ids
    await publish_event(
        request,
        EVENTS.NOTE_ACCESS_UPDATED,
        actor=user,
        subject_id=note.id,
    )
    return note


############################
# PinNoteById
############################


@router.post('/{id}/pin', response_model=Optional[NoteModel])
async def pin_note_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'features.notes', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    note = await Notes.get_note_by_id(id, db=db)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if user.role != 'admin' and (
        user.id != note.user_id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='note',
            resource_id=note.id,
            permission='read',
            db=db,
        )
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    note = await Notes.toggle_note_pinned_by_id(id, user.id, db=db)
    pinned_note_ids = await Notes.get_pinned_note_ids(user.id, db=db)
    note.is_pinned = note.id in pinned_note_ids
    await publish_event(
        request,
        EVENTS.NOTE_PINNED if note.is_pinned else EVENTS.NOTE_UNPINNED,
        actor=user,
        subject_id=note.id,
        subject_type='note',
    )
    return note


############################
# DeleteNoteById
############################


@router.delete('/{id}/delete', response_model=bool)
async def delete_note_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'features.notes', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    note = await Notes.get_note_by_id(id, db=db)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if user.role != 'admin' and (
        user.id != note.user_id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='note',
            resource_id=note.id,
            permission='write',
            db=db,
        )
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT())

    try:
        note = await Notes.delete_note_by_id(id, db=db)
        await publish_event(
            request,
            EVENTS.NOTE_DELETED,
            actor=user,
            subject_id=id,
        )
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())
