import json
import logging
from typing import Optional


from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from pydantic import BaseModel

from open_webui.models.users import Users, UserResponse
from open_webui.models.notes import Notes, NoteModel, NoteForm, NoteUserResponse

from open_webui.config import ENABLE_ADMIN_CHAT_ACCESS, ENABLE_ADMIN_EXPORT
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS


from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_permission

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

############################
# GetNotes
############################


@router.get("/", response_model=list[NoteUserResponse])
async def get_notes(request: Request, user=Depends(get_verified_user)):

    if user.role != "admin" and not has_permission(
        user.id, "features.notes", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    notes = [
        NoteUserResponse(
            **{
                **note.model_dump(),
                "user": UserResponse(**Users.get_user_by_id(note.user_id).model_dump()),
            }
        )
        for note in Notes.get_notes_by_user_id(user.id, "write")
    ]

    return notes


@router.get("/list", response_model=list[NoteUserResponse])
async def get_note_list(request: Request, user=Depends(get_verified_user)):

    if user.role != "admin" and not has_permission(
        user.id, "features.notes", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    notes = [
        NoteUserResponse(
            **{
                **note.model_dump(),
                "user": UserResponse(**Users.get_user_by_id(note.user_id).model_dump()),
            }
        )
        for note in Notes.get_notes_by_user_id(user.id, "read")
    ]

    return notes


############################
# CreateNewNote
############################


@router.post("/create", response_model=Optional[NoteModel])
async def create_new_note(
    request: Request, form_data: NoteForm, user=Depends(get_verified_user)
):

    if user.role != "admin" and not has_permission(
        user.id, "features.notes", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    try:
        note = Notes.insert_new_note(form_data, user.id)
        return note
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetNoteById
############################


@router.get("/{id}", response_model=Optional[NoteModel])
async def get_note_by_id(request: Request, id: str, user=Depends(get_verified_user)):
    if user.role != "admin" and not has_permission(
        user.id, "features.notes", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    note = Notes.get_note_by_id(id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and not has_access(
        user.id, type="read", access_control=note.access_control
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    return note


############################
# UpdateNoteById
############################


@router.post("/{id}/update", response_model=Optional[NoteModel])
async def update_note_by_id(
    request: Request, id: str, form_data: NoteForm, user=Depends(get_verified_user)
):
    if user.role != "admin" and not has_permission(
        user.id, "features.notes", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    note = Notes.get_note_by_id(id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and not has_access(
        user.id, type="write", access_control=note.access_control
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        note = Notes.update_note_by_id(id, form_data)
        return note
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteNoteById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_note_by_id(request: Request, id: str, user=Depends(get_verified_user)):
    if user.role != "admin" and not has_permission(
        user.id, "features.notes", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    note = Notes.get_note_by_id(id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and not has_access(
        user.id, type="write", access_control=note.access_control
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        note = Notes.delete_note_by_id(id)
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )
