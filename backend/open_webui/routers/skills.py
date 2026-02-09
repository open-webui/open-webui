import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from open_webui.constants import ERROR_MESSAGES
from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.internal.db import get_session
from open_webui.models.skills import (
    SkillForm,
    SkillModel,
    SkillResponse,
    SkillAccessResponse,
    Skills,
)
from open_webui.utils.skills_external_bridge import sync_external_skills_from_env
from open_webui.utils.access_control import has_access, has_permission
from open_webui.utils.auth import get_verified_user


router = APIRouter()


@router.get("/", response_model=list[SkillModel])
async def get_skills(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        skills = Skills.get_skills(db=db)
    else:
        skills = Skills.get_skills_by_user_id(user.id, "read", db=db)

    return [SkillModel.model_validate(skill.model_dump()) for skill in skills]


@router.get("/list", response_model=list[SkillAccessResponse])
async def get_skill_list(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        skills = Skills.get_skills(db=db)
    else:
        skills = Skills.get_skills_by_user_id(user.id, "read", db=db)

    return [
        SkillAccessResponse(
            **skill.model_dump(),
            write_access=(
                (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
                or user.id == skill.user_id
                or has_access(user.id, "write", skill.access_control, db=db)
            ),
        )
        for skill in skills
    ]


@router.get("/export", response_model=list[SkillModel])
async def export_skills(
    request: Request,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id,
        "workspace.skills_export",
        request.app.state.config.USER_PERMISSIONS,
        db=db,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        skills = Skills.get_skills(db=db)
    else:
        skills = Skills.get_skills_by_user_id(user.id, "read", db=db)

    return [SkillModel.model_validate(skill.model_dump()) for skill in skills]


@router.post("/create", response_model=Optional[SkillResponse])
async def create_new_skill(
    request: Request,
    form_data: SkillForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not (
        has_permission(
            user.id,
            "workspace.skills",
            request.app.state.config.USER_PERMISSIONS,
            db=db,
        )
        or has_permission(
            user.id,
            "workspace.skills_import",
            request.app.state.config.USER_PERMISSIONS,
            db=db,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    if not re.match(r"^[A-Za-z0-9_-]+$", form_data.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only alphanumeric characters, underscores, and hyphens are allowed in the id",
        )

    form_data.id = form_data.id.lower()

    existing = Skills.get_skill_by_id(form_data.id, db=db)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ID_TAKEN,
        )

    skill = Skills.insert_new_skill(user.id, form_data, db=db)
    if skill:
        return skill

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERROR_MESSAGES.DEFAULT("Error creating skill"),
    )


@router.get("/id/{id}", response_model=Optional[SkillAccessResponse])
async def get_skill_by_id(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    skill = Skills.get_skill_by_id(id, db=db)

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        user.role == "admin"
        or skill.user_id == user.id
        or has_access(user.id, "read", skill.access_control, db=db)
    ):
        return SkillAccessResponse(
            **skill.model_dump(),
            write_access=(
                (user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL)
                or user.id == skill.user_id
                or has_access(user.id, "write", skill.access_control, db=db)
            ),
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
    )


@router.post("/id/{id}/update", response_model=Optional[SkillModel])
async def update_skill_by_id(
    id: str,
    form_data: SkillForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    skill = Skills.get_skill_by_id(id, db=db)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        skill.user_id != user.id
        and not has_access(user.id, "write", skill.access_control, db=db)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    updated = {
        **form_data.model_dump(exclude={"id"}),
    }
    result = Skills.update_skill_by_id(id, updated, db=db)

    if result:
        return result

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERROR_MESSAGES.DEFAULT("Error updating skill"),
    )


@router.post("/id/{id}/toggle", response_model=Optional[SkillModel])
async def toggle_skill_by_id(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    skill = Skills.get_skill_by_id(id, db=db)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        skill.user_id != user.id
        and not has_access(user.id, "write", skill.access_control, db=db)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    result = Skills.update_skill_by_id(id, {"is_active": not skill.is_active}, db=db)
    if result:
        return result

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ERROR_MESSAGES.DEFAULT("Error updating skill"),
    )


@router.delete("/id/{id}/delete", response_model=bool)
async def delete_skill_by_id(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    skill = Skills.get_skill_by_id(id, db=db)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        skill.user_id != user.id
        and not has_access(user.id, "write", skill.access_control, db=db)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    return Skills.delete_skill_by_id(id, db=db)


@router.post("/sync/external", response_model=dict)
async def sync_external_skills(
    request: Request,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id,
        "workspace.skills_import",
        request.app.state.config.USER_PERMISSIONS,
        db=db,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    return sync_external_skills_from_env(initiator_user_id=user.id, db=db)
