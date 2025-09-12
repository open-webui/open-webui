import json
import logging
from typing import Optional, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from open_webui.socket.main import sio

from open_webui.models.users import Users, UserResponse
from open_webui.models.noteplus import (
    NotesPlus, 
    NotePlusModel, 
    NotePlusForm, 
    NotePlusUserResponse,
    NotePlusCategoryTree
)

from open_webui.config import ENABLE_ADMIN_CHAT_ACCESS, ENABLE_ADMIN_EXPORT
from open_webui.constants import ERROR_MESSAGES, TASKS
from open_webui.env import SRC_LOG_LEVELS

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access, has_permission

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()

############################
# GetNotesPlus
############################


@router.get("/", response_model=list[NotePlusUserResponse])
async def get_noteplus_list(request: Request, user=Depends(get_verified_user)):
    
    if user.role != "admin" and not has_permission(
        user.id, "features.noteplus", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    noteplus_list = [
        NotePlusUserResponse(
            **{
                **noteplus.model_dump(),
                "user": UserResponse(**Users.get_user_by_id(noteplus.user_id).model_dump()),
            }
        )
        for noteplus in NotesPlus.get_noteplus_by_user_id(user.id, "write")
    ]

    return noteplus_list


class NotePlusTitleIdResponse(BaseModel):
    id: str
    title: str
    category_major: Optional[str] = None
    category_middle: Optional[str] = None
    category_minor: Optional[str] = None
    updated_at: int
    created_at: int


@router.get("/list", response_model=list[NotePlusTitleIdResponse])
async def get_noteplus_title_list(request: Request, user=Depends(get_verified_user)):
    
    if user.role != "admin" and not has_permission(
        user.id, "features.noteplus", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    noteplus_list = [
        NotePlusTitleIdResponse(**noteplus.model_dump())
        for noteplus in NotesPlus.get_noteplus_by_user_id(user.id, "write")
    ]

    return noteplus_list


############################
# GetCategoryTree
############################


@router.get("/categories", response_model=Dict[str, NotePlusCategoryTree])
async def get_category_tree(request: Request, user=Depends(get_verified_user)):
    
    if user.role != "admin" and not has_permission(
        user.id, "features.noteplus", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    return NotesPlus.get_category_tree(user.id)


############################
# GetNotesPlusByCategory
############################


@router.get("/category", response_model=list[NotePlusUserResponse])
async def get_noteplus_by_category(
    request: Request,
    major: Optional[str] = None,
    middle: Optional[str] = None,
    minor: Optional[str] = None,
    user=Depends(get_verified_user)
):
    
    if user.role != "admin" and not has_permission(
        user.id, "features.noteplus", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    noteplus_list = [
        NotePlusUserResponse(
            **{
                **noteplus.model_dump(),
                "user": UserResponse(**Users.get_user_by_id(noteplus.user_id).model_dump()),
            }
        )
        for noteplus in NotesPlus.get_noteplus_by_category(
            user.id, major, middle, minor, "read"
        )
    ]

    return noteplus_list


############################
# CreateNewNotePlus
############################


@router.post("/create", response_model=Optional[NotePlusModel])
async def create_new_noteplus(
    request: Request, form_data: NotePlusForm, user=Depends(get_verified_user)
):
    
    if user.role != "admin" and not has_permission(
        user.id, "features.noteplus", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    try:
        # Auto-categorize if categories are not provided
        if not form_data.category_major:
            # Use auto-categorization based on title and content
            content = form_data.data.get("content", {}).get("md", "") if form_data.data else ""
            major, middle, minor = auto_categorize(form_data.title, content)
            form_data.category_major = major
            form_data.category_middle = middle
            form_data.category_minor = minor
        
        noteplus = NotesPlus.insert_new_noteplus(form_data, user.id)
        return noteplus
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetNotePlusById
############################


@router.get("/{id}", response_model=Optional[NotePlusModel])
async def get_noteplus_by_id(request: Request, id: str, user=Depends(get_verified_user)):
    if user.role != "admin" and not has_permission(
        user.id, "features.noteplus", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    noteplus = NotesPlus.get_noteplus_by_id(id)
    if not noteplus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and (
        user.id != noteplus.user_id
        and (not has_access(user.id, type="read", access_control=noteplus.access_control))
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    return noteplus


############################
# UpdateNotePlusById
############################


@router.post("/{id}/update", response_model=Optional[NotePlusModel])
async def update_noteplus_by_id(
    request: Request, id: str, form_data: NotePlusForm, user=Depends(get_verified_user)
):
    if user.role != "admin" and not has_permission(
        user.id, "features.noteplus", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    noteplus = NotesPlus.get_noteplus_by_id(id)
    if not noteplus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and (
        user.id != noteplus.user_id
        and not has_access(user.id, type="write", access_control=noteplus.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        # Auto-categorize if title changes and categories are not explicitly set
        if form_data.title and not (form_data.category_major or form_data.category_middle or form_data.category_minor):
            # Use auto-categorization based on title and content
            content = form_data.data.get("content", {}).get("md", "") if form_data.data else ""
            major, middle, minor = auto_categorize(form_data.title, content)
            form_data.category_major = major
            form_data.category_middle = middle
            form_data.category_minor = minor
        
        noteplus = NotesPlus.update_noteplus_by_id(id, form_data)
        await sio.emit(
            "noteplus-events",
            noteplus.model_dump(),
            to=f"noteplus:{noteplus.id}",
        )

        return noteplus
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteNotePlusById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_noteplus_by_id(request: Request, id: str, user=Depends(get_verified_user)):
    if user.role != "admin" and not has_permission(
        user.id, "features.noteplus", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    noteplus = NotesPlus.get_noteplus_by_id(id)
    if not noteplus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and (
        user.id != noteplus.user_id
        and not has_access(user.id, type="write", access_control=noteplus.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        NotesPlus.delete_noteplus_by_id(id)
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


