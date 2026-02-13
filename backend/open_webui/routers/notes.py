import json
import logging
from typing import Optional


from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from pydantic import BaseModel

from open_webui.socket.main import sio

from open_webui.models.groups import Groups
from open_webui.models.users import Users, UserResponse
from open_webui.models.notes import (
    NoteListResponse,
    Notes,
    NoteModel,
    NoteForm,
    NoteUserResponse,
)

from open_webui.config import (
    BYPASS_ADMIN_ACCESS_CONTROL,
    ENABLE_ADMIN_CHAT_ACCESS,
    ENABLE_ADMIN_EXPORT,
)
from open_webui.constants import ERROR_MESSAGES


from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_permission
from open_webui.models.access_grants import AccessGrants, has_public_read_access_grant
from open_webui.internal.db import get_session
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

router = APIRouter()

############################
# GetNotes
############################


class NoteItemResponse(BaseModel):
    id: str
    title: str
    data: Optional[dict]
    updated_at: int
    created_at: int
    user: Optional[UserResponse] = None


@router.get("/", response_model=list[NoteItemResponse])
async def get_notes(
    request: Request,
    page: Optional[int] = None,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.notes", request.app.state.config.USER_PERMISSIONS, db=db
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

    notes = Notes.get_notes_by_user_id(user.id, "read", skip=skip, limit=limit, db=db)
    if not notes:
        return []

    user_ids = list(set(note.user_id for note in notes))
    users = {user.id: user for user in Users.get_users_by_user_ids(user_ids, db=db)}

    return [
        NoteUserResponse(
            **{
                **note.model_dump(),
                "user": UserResponse(**users[note.user_id].model_dump()),
            }
        )
        for note in notes
        if note.user_id in users
    ]


@router.get("/search", response_model=NoteListResponse)
async def search_notes(
    request: Request,
    query: Optional[str] = None,
    view_option: Optional[str] = None,
    permission: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.notes", request.app.state.config.USER_PERMISSIONS, db=db
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
        filter["query"] = query
    if view_option:
        filter["view_option"] = view_option
    if permission:
        filter["permission"] = permission
    if order_by:
        filter["order_by"] = order_by
    if direction:
        filter["direction"] = direction

    if not user.role == "admin" or not BYPASS_ADMIN_ACCESS_CONTROL:
        groups = Groups.get_groups_by_member_id(user.id, db=db)
        if groups:
            filter["group_ids"] = [group.id for group in groups]

        filter["user_id"] = user.id

    return Notes.search_notes(user.id, filter, skip=skip, limit=limit, db=db)


############################
# CreateNewNote
############################


@router.post("/create", response_model=Optional[NoteModel])
async def create_new_note(
    request: Request,
    form_data: NoteForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.notes", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    try:
        note = Notes.insert_new_note(user.id, form_data, db=db)
        return note
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetNoteById
############################


class NoteResponse(NoteModel):
    write_access: bool = False


@router.get("/{id}", response_model=Optional[NoteResponse])
async def get_note_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.notes", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    note = Notes.get_note_by_id(id, db=db)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and (
        user.id != note.user_id
        and (
            not AccessGrants.has_access(
                user_id=user.id,
                resource_type="note",
                resource_id=note.id,
                permission="read",
                db=db,
            )
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    write_access = (
        user.role == "admin"
        or (user.id == note.user_id)
        or AccessGrants.has_access(
            user_id=user.id,
            resource_type="note",
            resource_id=note.id,
            permission="write",
            db=db,
        )
        or has_public_read_access_grant(note.access_grants)
    )

    return NoteResponse(**note.model_dump(), write_access=write_access)


############################
# UpdateNoteById
############################


@router.post("/{id}/update", response_model=Optional[NoteModel])
async def update_note_by_id(
    request: Request,
    id: str,
    form_data: NoteForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.notes", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    note = Notes.get_note_by_id(id, db=db)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and (
        user.id != note.user_id
        and not AccessGrants.has_access(
            user_id=user.id,
            resource_type="note",
            resource_id=note.id,
            permission="write",
            db=db,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    # Check if user can share publicly
    if (
        user.role != "admin"
        and has_public_read_access_grant(form_data.access_grants)
        and not has_permission(
            user.id,
            "sharing.public_notes",
            request.app.state.config.USER_PERMISSIONS,
            db=db,
        )
    ):
        form_data.access_grants = []

    try:
        note = Notes.update_note_by_id(id, form_data, db=db)
        await sio.emit(
            "note-events",
            note.model_dump(),
            to=f"note:{note.id}",
        )

        return note
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# UpdateNoteAccessById
############################


class NoteAccessGrantsForm(BaseModel):
    access_grants: list[dict]


@router.post("/{id}/access/update", response_model=Optional[NoteModel])
async def update_note_access_by_id(
    request: Request,
    id: str,
    form_data: NoteAccessGrantsForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.notes", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    note = Notes.get_note_by_id(id, db=db)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and (
        user.id != note.user_id
        and not AccessGrants.has_access(
            user_id=user.id,
            resource_type="note",
            resource_id=note.id,
            permission="write",
            db=db,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    AccessGrants.set_access_grants("note", id, form_data.access_grants, db=db)

    return Notes.get_note_by_id(id, db=db)


############################
# DeleteNoteById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_note_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.notes", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    note = Notes.get_note_by_id(id, db=db)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and (
        user.id != note.user_id
        and not AccessGrants.has_access(
            user_id=user.id,
            resource_type="note",
            resource_id=note.id,
            permission="write",
            db=db,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        note = Notes.delete_note_by_id(id, db=db)
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )
