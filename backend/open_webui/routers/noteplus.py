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
from open_webui.utils.categorizer import auto_categorize
from open_webui.utils.chat import generate_chat_completion
from open_webui.utils.task import title_generation_template, get_task_model_id
from open_webui.routers.pipelines import process_pipeline_inlet_filter

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


############################
# GenerateNotePlusTitle
############################


@router.post("/title/generate")
async def generate_noteplus_title(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    if user.role != "admin" and not has_permission(
        user.id, "features.noteplus", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    if not request.app.state.config.ENABLE_TITLE_GENERATION:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"detail": "Title generation is disabled"},
        )

    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        models = {
            request.state.model["id"]: request.state.model,
        }
    else:
        models = request.app.state.MODELS

    model_id = form_data.get("model")
    if not model_id:
        # Use default model
        model_id = request.app.state.config.TASK_MODEL or next(iter(models.keys()), None)
    
    if model_id and model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    task_model_id = get_task_model_id(
        model_id,
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )

    log.debug(
        f"generating noteplus title using model {task_model_id} for user {user.email}"
    )

    # Get content from form_data
    content_data = form_data.get("content", "")
    
    # Create a simple message format for title generation
    messages = [
        {
            "role": "user",
            "content": f"Generate a concise title for this note:\n\n{content_data}"
        }
    ]

    template = request.app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE or """Generate a concise title (3-10 words) for this note. Return only the title text, no quotes or formatting:

{{CONTENT}}"""

    prompt_content = title_generation_template(template, messages, user)

    max_tokens = (
        models[task_model_id].get("info", {}).get("params", {}).get("max_tokens", 50)
    )

    payload = {
        "model": task_model_id,
        "messages": [{"role": "user", "content": prompt_content}],
        "stream": False,
        **(
            {"max_tokens": max_tokens}
            if models[task_model_id].get("owned_by") == "ollama"
            else {
                "max_completion_tokens": max_tokens,
            }
        ),
        "metadata": {
            **(request.state.metadata if hasattr(request.state, "metadata") else {}),
            "task": "NOTEPLUS_TITLE_GENERATION",
            "task_body": form_data,
        },
    }

    try:
        payload = await process_pipeline_inlet_filter(request, payload, user, models)
    except Exception as e:
        raise e

    try:
        response = await generate_chat_completion(request, form_data=payload, user=user)
        return response
    except Exception as e:
        log.error("Exception occurred", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "An internal error has occurred."},
        )


############################
# AutoCategorizeNotePlus (Code-based)
############################


@router.post("/category/auto")
async def auto_categorize_noteplus(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    if user.role != "admin" and not has_permission(
        user.id, "features.noteplus", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    title = form_data.get("title", "")
    content = form_data.get("content", "")
    
    # Use the code-based auto-categorization
    major, middle, minor = auto_categorize(title, content)
    
    return {
        "major": major,
        "middle": middle,
        "minor": minor
    }


############################
# GenerateNotePlusCategory (LLM-based)
############################


@router.post("/category/generate")
async def generate_noteplus_category(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    if user.role != "admin" and not has_permission(
        user.id, "features.noteplus", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    if getattr(request.state, "direct", False) and hasattr(request.state, "model"):
        models = {
            request.state.model["id"]: request.state.model,
        }
    else:
        models = request.app.state.MODELS

    model_id = form_data.get("model")
    if not model_id:
        # Use default model
        model_id = request.app.state.config.TASK_MODEL or next(iter(models.keys()), None)
    
    if model_id and model_id not in models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    # Check if the user has a custom task model
    task_model_id = get_task_model_id(
        model_id,
        request.app.state.config.TASK_MODEL,
        request.app.state.config.TASK_MODEL_EXTERNAL,
        models,
    )

    log.debug(
        f"generating noteplus categories using model {task_model_id} for user {user.email}"
    )

    # Get title and content from form_data
    title = form_data.get("title", "")
    content_data = form_data.get("content", "")
    
    # Create prompt for category generation
    prompt_content = f"""Analyze the language of the content below and categorize it into a 3-level hierarchy using the SAME LANGUAGE as the content.

Guidelines:
1. First, detect the primary language of the content
2. Generate ALL category names in that detected language
3. Category examples:
   - Korean: 개발/프론트엔드/리액트, 개인/일기/일일
   - English: Development/Frontend/React, Personal/Journal/Daily
   - Japanese: 開発/フロントエンド/React, 個人/日記/日々

Return ONLY a JSON object with this exact structure:
{{
  "major": "category name in content's language",
  "middle": "category name in content's language",
  "minor": "category name in content's language"
}}

Title: {title}
Content: {content_data}"""

    max_tokens = 100

    payload = {
        "model": task_model_id,
        "messages": [{"role": "user", "content": prompt_content}],
        "stream": False,
        **(
            {"max_tokens": max_tokens}
            if models[task_model_id].get("owned_by") == "ollama"
            else {
                "max_completion_tokens": max_tokens,
            }
        ),
        "metadata": {
            **(request.state.metadata if hasattr(request.state, "metadata") else {}),
            "task": "NOTEPLUS_CATEGORY_GENERATION",
            "task_body": form_data,
        },
    }

    try:
        payload = await process_pipeline_inlet_filter(request, payload, user, models)
    except Exception as e:
        raise e

    try:
        response = await generate_chat_completion(request, form_data=payload, user=user)
        return response
    except Exception as e:
        log.error("Exception occurred", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "An internal error has occurred."},
        )