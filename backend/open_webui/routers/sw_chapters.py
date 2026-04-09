"""
StoryWeaver — Chapters Router
=============================

Description fonctionnelle:
    Gère le cycle de vie des chapitres d'un roman StoryWeaver.
    Permet le CRUD des chapitres, l'ordonnancement par glisser-déposer (via reorder)
    et le suivi du statut (brouillon, terminé, etc.).

Règles métier:
    - Un chapitre appartient à un seul novel.
    - L'accès est restreint au propriétaire du novel (ou admin).
    - L'ordre (`order`) des chapitres est géré linéairement (0, 1, 2...).

Architecture tech:
    - Router FastAPI monté sur /api/sw/novels/{novel_id}/chapters dans main.py.
    - Utilise ChaptersTable pour les opérations DB.
"""

import logging
import uuid
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from open_webui.internal.db import get_session
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_verified_user

from open_webui.models.sw_novels import (
    ChapterModel,
    Chapters,
    Novels,
)

log = logging.getLogger(__name__)

router = APIRouter()

############################
# Helpers
############################

def _check_novel_ownership(novel_id: str, user, db: Session) -> None:
    novel = Novels.get_novel_by_id(id=novel_id, db=db)
    if not novel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if novel.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

def _check_chapter_ownership(chapter_id: str, user, db: Session):
    chapter = Chapters.get_chapter_by_id(chapter_id, db=db)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    _check_novel_ownership(chapter.novel_id, user, db)
    return chapter

############################
# Schemas
############################

class ChapterCreateForm(BaseModel):
    title: str = Field(..., min_length=1)
    content: Optional[str] = ""
    order: Optional[int] = 0
    status: Optional[str] = "draft"

class ChapterUpdateForm(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    order: Optional[int] = None
    status: Optional[str] = None

class ChaptersReorderForm(BaseModel):
    ordered_ids: List[str]

############################
# Endpoints
############################

@router.get("/{novel_id}/chapters", response_model=List[ChapterModel])
async def get_novel_chapters(
    novel_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Liste tous les chapitres d'un roman, triés par ordre."""
    _check_novel_ownership(novel_id, user, db)
    return Chapters.get_chapters_by_novel_id(novel_id, db=db)


@router.post("/{novel_id}/chapters", response_model=ChapterModel)
async def create_chapter(
    novel_id: str,
    form_data: ChapterCreateForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Crée un nouveau chapitre."""
    _check_novel_ownership(novel_id, user, db)
    
    chapter_id = str(uuid.uuid4())
    chapter = Chapters.insert_new_chapter(
        id=chapter_id,
        novel_id=novel_id,
        title=form_data.title,
        content=form_data.content,
        order=form_data.order,
        status=form_data.status,
        db=db
    )
    
    if not chapter:
        raise HTTPException(status_code=400, detail="Failed to create chapter")
    return chapter


@router.get("/chapters/{chapter_id}", response_model=ChapterModel)
async def get_chapter(
    chapter_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Récupère un chapitre spécifique."""
    return _check_chapter_ownership(chapter_id, user, db)


@router.post("/chapters/{chapter_id}/update", response_model=ChapterModel)
async def update_chapter(
    chapter_id: str,
    form_data: ChapterUpdateForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Met à jour les informations d'un chapitre."""
    _check_chapter_ownership(chapter_id, user, db)
    
    updated_data = form_data.model_dump(exclude_none=True)
    chapter = Chapters.update_chapter_by_id(chapter_id, updated_data, db=db)
    
    if not chapter:
        raise HTTPException(status_code=400, detail="Failed to update chapter")
    return chapter


@router.delete("/chapters/{chapter_id}", response_model=bool)
async def delete_chapter(
    chapter_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Supprime un chapitre."""
    _check_chapter_ownership(chapter_id, user, db)
    return Chapters.delete_chapter_by_id(chapter_id, db=db)


@router.post("/{novel_id}/chapters/reorder", response_model=bool)
async def reorder_chapters(
    novel_id: str,
    form_data: ChaptersReorderForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """Réordonne une liste de chapitres."""
    _check_novel_ownership(novel_id, user, db)
    
    success = True
    for index, chapter_id in enumerate(form_data.ordered_ids):
        # On vérifie vite fait que le chapitre appartient bien au novel pour éviter les injections
        chapter = Chapters.get_chapter_by_id(chapter_id, db=db)
        if chapter and chapter.novel_id == novel_id:
            Chapters.update_chapter_by_id(chapter_id, {"order": index}, db=db)
        else:
            log.warning(f"Attempt to reorder chapter {chapter_id} not belonging to novel {novel_id}")
            success = False
            
    return success
