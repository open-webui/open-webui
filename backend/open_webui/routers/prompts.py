from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request

from open_webui.models.prompts import (
    PromptForm,
    PromptUserResponse,
    PromptModel,
    Prompts,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access, has_permission
from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.utils.prompt_counter import update_prompt_counter
from open_webui.internal.db import SessionLocal
from sqlalchemy import select, func
from open_webui.models.prompt_usage import PromptUsage

router = APIRouter()

############################
# GetPrompts
############################


@router.get("/", response_model=list[PromptModel])
async def get_prompts(user=Depends(get_verified_user)):
    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        prompts = Prompts.get_prompts()
    else:
        prompts = Prompts.get_prompts_by_user_id(user.id, "read")

    return prompts


@router.get("/list", response_model=list[PromptUserResponse])
async def get_prompt_list(user=Depends(get_verified_user)):
    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        prompts = Prompts.get_prompts()
    else:
        prompts = Prompts.get_prompts_by_user_id(user.id, "write")

    return prompts


############################
# CreateNewPrompt
############################


@router.post("/create", response_model=Optional[PromptModel])
async def create_new_prompt(
    request: Request, form_data: PromptForm, user=Depends(get_verified_user)
):
    if user.role != "admin" and not has_permission(
        user.id, "workspace.prompts", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    prompt = Prompts.get_prompt_by_command(form_data.command)
    if prompt is None:
        prompt = Prompts.insert_new_prompt(user.id, form_data)

        if prompt:
            return prompt
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERROR_MESSAGES.COMMAND_TAKEN,
    )


############################
# GetPromptByCommand
############################


@router.get("/command/{command}", response_model=Optional[PromptModel])
async def get_prompt_by_command(command: str, user=Depends(get_verified_user)):
    prompt = Prompts.get_prompt_by_command(f"/{command}")

    if prompt:
        if (
            user.role == "admin"
            or prompt.user_id == user.id
            or has_access(user.id, "read", prompt.access_control)
        ):
            return prompt
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdatePromptByCommand
############################


@router.post("/command/{command}/update", response_model=Optional[PromptModel])
async def update_prompt_by_command(
    command: str,
    form_data: PromptForm,
    user=Depends(get_verified_user),
):
    prompt = Prompts.get_prompt_by_command(f"/{command}")
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Is the user the original creator, in a group with write access, or an admin
    if (
        prompt.user_id != user.id
        and not has_access(user.id, "write", prompt.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    prompt = Prompts.update_prompt_by_command(f"/{command}", form_data)
    if prompt:
        return prompt
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


############################
# DeletePromptByCommand
############################


@router.delete("/command/{command}/delete", response_model=bool)
async def delete_prompt_by_command(command: str, user=Depends(get_verified_user)):
    prompt = Prompts.get_prompt_by_command(f"/{command}")
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        prompt.user_id != user.id
        and not has_access(user.id, "write", prompt.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    result = Prompts.delete_prompt_by_command(f"/{command}")
    return result


############################
# Prompt Usage Statistics (DB-based)
############################

@router.get("/usage/stats", response_model=dict)
async def get_prompt_usage_stats(request: Request, user=Depends(get_verified_user)):
    """Возвращает общую статистику использования промптов (агрегация из БД)."""

    db = SessionLocal()
    try:
        total_usage = db.execute(select(func.coalesce(func.sum(PromptUsage.count), 0))).scalar() or 0

        by_prompt_rows = db.execute(
            select(PromptUsage.prompt, func.sum(PromptUsage.count)).group_by(PromptUsage.prompt)
        ).all()
        by_prompt = {row[0]: int(row[1]) for row in by_prompt_rows}

        by_user_rows = db.execute(
            select(PromptUsage.user_id, func.sum(PromptUsage.count)).group_by(PromptUsage.user_id)
        ).all()
        by_user = {row[0]: int(row[1]) for row in by_user_rows}

        by_date_rows = db.execute(
            select(PromptUsage.used_date, func.sum(PromptUsage.count)).group_by(PromptUsage.used_date)
        ).all()
        by_date = {row[0].isoformat(): int(row[1]) for row in by_date_rows}

        return {
            "total_usage": int(total_usage),
            "by_prompt": by_prompt,
            "by_user": by_user,
            "by_date": by_date,
        }
    finally:
        db.close()


@router.get("/usage/prompt/{prompt_command}", response_model=dict)
async def get_prompt_usage_by_command(
        request: Request,
        prompt_command: str,
        user=Depends(get_verified_user)
):
    """Возвращает статистику использования конкретного промпта (из БД)."""

    db = SessionLocal()
    try:
        usage_count = db.execute(
            select(func.coalesce(func.sum(PromptUsage.count), 0)).where(PromptUsage.prompt == prompt_command)
        ).scalar() or 0

        total_usage = db.execute(select(func.coalesce(func.sum(PromptUsage.count), 0))).scalar() or 0

        return {
            "prompt_command": prompt_command,
            "usage_count": int(usage_count),
            "total_usage": int(total_usage),
        }
    finally:
        db.close()


@router.get("/usage/user/{user_id}", response_model=dict)
async def get_prompt_usage_by_user(
        request: Request,
        user_id: str,
        user=Depends(get_verified_user)
):
    """Возвращает статистику использования промптов конкретным пользователем (из БД)."""

    if user.role != "admin" and user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    db = SessionLocal()
    try:
        usage_count = db.execute(
            select(func.coalesce(func.sum(PromptUsage.count), 0)).where(PromptUsage.user_id == user_id)
        ).scalar() or 0

        total_usage = db.execute(select(func.coalesce(func.sum(PromptUsage.count), 0))).scalar() or 0

        return {
            "user_id": user_id,
            "usage_count": int(usage_count),
            "total_usage": int(total_usage),
        }
    finally:
        db.close()


@router.post("/usage/click", response_model=dict)
async def record_prompt_click(
    request: Request,
    payload: dict,
    user=Depends(get_verified_user),
):
    """Фиксирует клик по предложенному промпту и инкрементирует счетчик.

    Ожидает payload вида:
    {
        "command": "/fun_fact"  # опционально
        "content": "Tell me a fun fact about the Roman Empire"  # опционально
    }
    Приоритет: command, иначе content.
    """

    command = (payload.get("command") or "").strip()
    content = (payload.get("content") or "").strip()

    prompts_used: list[str] = []
    if command:
        prompts_used = [command if command.startswith("/") else f"/{command}"]
    elif content:
        # Ключом будет сам текст подсказки
        prompts_used = [content]
    else:
        return {"ok": False}

    update_prompt_counter(request, user.id, prompts_used)

    return {"ok": True}