import logging
from typing import Optional

from open_webui.internal.db import Base, get_db

from open_webui.models.uos_notes import (
    GrantsNoteModel,
    GrantsNoteResponse,
    GrantsNoteForm,
    Notes,
)

from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.models.users import Users

from fastapi import APIRouter, Depends, HTTPException, status, Request

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

#####################
# Post Notes Initial
#####################


@router.post("/{chat_id}", response_model=GrantsNoteModel)
async def insert_new_note(
    chat_id: str,
    form_data: GrantsNoteForm,
    user=Depends(get_verified_user),
):
    note = Notes.insert_new_note(
        user_id=user.id,
        chat_id=chat_id,
        note=form_data.note,
        # optional: pass form_data.extra_data or others if needed
    )
    if not note:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to insert note",
        )
    return note


@router.get("/{chat_id}", response_model=GrantsNoteModel)
async def get_note_by_user_id_and_chat_id(
    chat_id: str,
    user=Depends(get_verified_user),
) -> Optional[GrantsNoteModel]:
    note = Notes.get_note_by_user_id_and_chat_id(
        user_id=user.id,
        chat_id=chat_id,
    )
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        )
    return note


@router.put("/update/{chat_id}", response_model=GrantsNoteModel)
async def update_note_by_user_id_and_chat_id(
    chat_id: str,
    form_data: GrantsNoteForm,
    user=Depends(get_verified_user),
) -> Optional[GrantsNoteModel]:
    note = Notes.update_note_by_user_id_and_chat_id(
        user_id=user.id,
        chat_id=chat_id,
        note=form_data.note,
        # optional: pass form_data.extra_data or others if needed
    )
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        )
    return note
