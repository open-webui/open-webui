"""
StoryWeaver — Novels Router
============================

Description fonctionnelle:
    Fournit les endpoints REST CRUD pour gérer les romans (Novel) d'un utilisateur,
    ainsi que le système de sélection du roman courant (session management).

Règles métier:
    - Un utilisateur ne peut accéder qu'à ses propres romans.
    - Le champ `status` est contraint à : draft | in-progress | completed | archived.
    - La suppression est irréversible et cascade les entités liées.
    - `updated_at` est automatiquement rafraîchi à chaque modification via le DAO.
    - `current_novel_id` est persisté sur la colonne `user.current_novel_id`.
    - Sélectionner un roman invalide (autre user / inexistant) leve 403/404.
    - Désélectionner remet `current_novel_id` à None sans erreur.

Architecture tech:
    - Router FastAPI monté sur /api/sw/novels dans main.py.
    - Dépend de `get_verified_user` pour l'authentification.
    - Dépend de `get_session` pour la session SQLAlchemy.
    - Les DAOs (NovelsTable, UsersTable) sont importés depuis leurs modules respectifs.
    - `get_current_novel()` est une dépendance FastAPI injectable par les routers aval.
"""

import logging
import uuid
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from open_webui.internal.db import get_session
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_verified_user

from open_webui.models.sw_novels import (
    NovelModel,
    Novels,
)
from open_webui.models.users import Users

log = logging.getLogger(__name__)

router = APIRouter()

NovelStatus = Literal["draft", "in-progress", "completed", "archived"]


############################
# Pydantic Forms / Responses
############################


class NovelCreateForm(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    status: NovelStatus = "draft"


class NovelUpdateForm(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[NovelStatus] = None


############################
# POST /create — CreateNovel
############################


@router.post("/create", response_model=NovelModel)
async def create_novel(
    form_data: NovelCreateForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Crée un nouveau roman pour l'utilisateur authentifié.

    Returns:
        NovelModel: Le roman nouvellement créé.
    """
    try:
        novel = Novels.insert_new_novel(
            id=str(uuid.uuid4()),
            user_id=user.id,
            title=form_data.title,
            description=form_data.description,
            status=form_data.status,
            db=db,
        )
        if not novel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(),
            )
        return novel
    except HTTPException:
        raise
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


############################
# GET / — GetNovels
############################


@router.get("/", response_model=list[NovelModel])
async def get_novels(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Retourne la liste de tous les romans de l'utilisateur authentifié,
    triés par date de mise à jour décroissante.

    Returns:
        list[NovelModel]: La liste des romans.
    """
    return Novels.get_novels_by_user(user_id=user.id, db=db)


############################
# GET /current — GetCurrentNovel
############################


class CurrentNovelResponse(BaseModel):
    """Réponse enrichie incluant le roman courant + indicateur de sélection active."""
    novel: Optional[NovelModel] = None
    is_selected: bool = False


@router.get("/current", response_model=CurrentNovelResponse)
async def get_current_novel_endpoint(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Retourne le roman actuellement sélectionné pour l'utilisateur authentifié.
    Si aucun roman n'est sélectionné, retourne `{novel: null, is_selected: false}`.

    Returns:
        CurrentNovelResponse: Le roman courant ou null.
    """
    current_novel_id = user.current_novel_id
    if not current_novel_id:
        return CurrentNovelResponse(novel=None, is_selected=False)

    novel = Novels.get_novel_by_id(id=current_novel_id, db=db)
    if not novel or novel.user_id != user.id:
        # Le roman a été supprimé ou appartient à un autre user : on réinitialise silencieusement
        Users.update_user_by_id(id=user.id, updated={"current_novel_id": None}, db=db)
        return CurrentNovelResponse(novel=None, is_selected=False)

    return CurrentNovelResponse(novel=novel, is_selected=True)


############################
# POST /{id}/select — SelectNovel
############################


@router.post("/{id}/select", response_model=CurrentNovelResponse)
async def select_novel(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Sélectionne un roman comme roman courant pour la session de l'utilisateur.
    Persiste `current_novel_id` sur l'enregistrement User.

    Returns:
        CurrentNovelResponse: Le roman nouvellement sélectionné.
    """
    novel = Novels.get_novel_by_id(id=id, db=db)
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

    result = Users.update_user_by_id(
        id=user.id,
        updated={"current_novel_id": id},
        db=db,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    return CurrentNovelResponse(novel=novel, is_selected=True)


############################
# POST /deselect — DeselectNovel
############################


@router.post("/deselect", response_model=CurrentNovelResponse)
async def deselect_novel(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Désélectionne le roman courant. Remet `current_novel_id` à None.
    Opération idempotente : ne lève pas d'erreur si aucun roman était sélectionné.

    Returns:
        CurrentNovelResponse: {novel: null, is_selected: false}.
    """
    Users.update_user_by_id(
        id=user.id,
        updated={"current_novel_id": None},
        db=db,
    )
    return CurrentNovelResponse(novel=None, is_selected=False)


############################
# GET /{id} — GetNovelById
############################


@router.get("/{id}", response_model=NovelModel)
async def get_novel_by_id(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Récupère un roman par son ID.
    Retourne 404 si non trouvé, 403 si appartenant à un autre utilisateur.

    Returns:
        NovelModel: Le roman correspondant.
    """
    novel = Novels.get_novel_by_id(id=id, db=db)
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

    return novel


############################
# POST /{id}/update — UpdateNovelById
############################


@router.post("/{id}/update", response_model=NovelModel)
async def update_novel_by_id(
    id: str,
    form_data: NovelUpdateForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Met à jour un roman existant (title, description, status).
    Seuls les champs fournis (non-None) sont modifiés.
    `updated_at` est rafraîchi automatiquement par le DAO.

    Returns:
        NovelModel: Le roman mis à jour.
    """
    novel = Novels.get_novel_by_id(id=id, db=db)
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

    # Construit le dict de mise à jour en excluant les valeurs None
    update_data = form_data.model_dump(exclude_none=True)

    if not update_data:
        # Rien à mettre à jour — on retourne le roman inchangé
        return novel

    try:
        updated = Novels.update_novel_by_id(
            id=id,
            updated=update_data,
            user_id=user.id,
            db=db,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(),
            )
        return updated
    except HTTPException:
        raise
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )


############################
# DELETE /{id}/delete — DeleteNovelById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_novel_by_id(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Supprime un roman et ses entités liées en cascade
    (KnowledgeBase, Manuscript, Versions).
    Opération irréversible — requiert confirmation côté frontend.

    Returns:
        bool: True si la suppression a réussi.
    """
    novel = Novels.get_novel_by_id(id=id, db=db)
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

    try:
        result = Novels.delete_novel_by_id(id=id, user_id=user.id, db=db)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(),
            )
        return True
    except HTTPException:
        raise
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )
