"""
StoryWeaver — Knowledge Base Router
=====================================

Description fonctionnelle:
    Fournit les endpoints REST pour gérer la Knowledge Base (KB) d'un roman.
    Chaque roman possède exactement une KB (1-to-1), créée automatiquement au
    premier accès (lazy init). La KB est organisée en 5 sections :
        - universe_docs : documents de worldbuilding
        - characters    : fiches personnages
        - locations     : lieux
        - objects       : objets importants
        - timeline      : événements chronologiques

    Chaque section est une liste d'items JSON libre. Chaque item reçoit un
    identifiant unique `id` généré côté backend à la création.

Règles métier:
    - Seul le propriétaire du roman parent peut accéder à sa KB (ou un admin).
    - La KB est initialisée automatiquement si elle n'existe pas (lazy creation).
    - Les sections valides sont : universe_docs, characters, locations, objects, timeline.
    - L'ajout d'un item génère automatiquement un `id` UUID si absent.
    - La suppression d'un item est par `id` — retourne 404 si non trouvé.
    - Le remplacement complet d'une section écrase l'existant.

Architecture tech:
    - Router FastAPI monté sur /api/sw/novels/{novel_id}/kb dans main.py.
    - Dépend de `get_verified_user` et `get_session`.
    - Utilise NovelsTable pour vérifier l'ownership du roman parent.
    - Utilise KnowledgeBasesTable pour les opérations sur la KB.
"""

import logging
import uuid
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from open_webui.internal.db import get_session
from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_verified_user

from open_webui.models.sw_novels import (
    KnowledgeBaseModel,
    KnowledgeBases,
    Novels,
)

log = logging.getLogger(__name__)

router = APIRouter()

# Les 5 sections valides de la KB
KBSection = Literal["universe_docs", "characters", "locations", "objects", "timeline"]
KB_SECTIONS: list[str] = ["universe_docs", "characters", "locations", "objects", "timeline"]


############################
# Helpers internes
############################


def _check_novel_ownership(novel_id: str, user, db: Session) -> None:
    """
    Vérifie que le novel existe et appartient à l'utilisateur.
    Lève 404 si inexistant, 403 si autre propriétaire (sauf admin).
    """
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


def _get_or_create_kb(novel_id: str, db: Session) -> KnowledgeBaseModel:
    """
    Récupère la KB d'un roman, ou la crée si elle n'existe pas encore (lazy init).
    """
    kb = KnowledgeBases.get_kb_by_novel_id(novel_id=novel_id, db=db)
    if not kb:
        kb = KnowledgeBases.insert_new_kb(
            id=str(uuid.uuid4()),
            novel_id=novel_id,
            db=db,
        )
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize Knowledge Base.",
            )
    return kb


def _get_section(kb: KnowledgeBaseModel, section: str) -> list:
    """Retourne la liste d'items d'une section de la KB."""
    return getattr(kb, section) or []


############################
# Pydantic Schemas
############################


class KBItemForm(BaseModel):
    """Un item libre à ajouter dans une section KB."""
    data: dict[str, Any] = Field(..., description="Données libres de l'item (fiche personnage, lieu, etc.)")


class KBSectionReplaceForm(BaseModel):
    """Remplacement complet d'une section KB."""
    items: list[dict[str, Any]] = Field(
        ...,
        description="La nouvelle liste complète d'items pour cette section.",
    )


############################
# GET /                     — GetKB
############################


@router.get("/", response_model=KnowledgeBaseModel)
async def get_kb(
    novel_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Récupère la Knowledge Base complète d'un roman.
    La crée automatiquement si elle n'existe pas encore.

    Returns:
        KnowledgeBaseModel: La KB du roman avec toutes ses sections.
    """
    _check_novel_ownership(novel_id, user, db)
    kb = _get_or_create_kb(novel_id, db)
    return kb


############################
# GET /{section}            — GetKBSection
############################


@router.get("/{section}", response_model=list[dict])
async def get_kb_section(
    novel_id: str,
    section: KBSection,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Retourne la liste d'items d'une section spécifique de la KB.

    Args:
        section: Une des 5 sections valides (universe_docs, characters, locations, objects, timeline).

    Returns:
        list[dict]: La liste d'items de la section.
    """
    _check_novel_ownership(novel_id, user, db)
    kb = _get_or_create_kb(novel_id, db)
    return _get_section(kb, section)


############################
# POST /{section}/add       — AddKBItem
############################


@router.post("/{section}/add", response_model=dict)
async def add_kb_item(
    novel_id: str,
    section: KBSection,
    form_data: KBItemForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Ajoute un nouvel item à une section de la KB.
    Un identifiant UUID est généré automatiquement si absent du payload.

    Returns:
        dict: L'item créé avec son `id` généré.
    """
    _check_novel_ownership(novel_id, user, db)
    kb = _get_or_create_kb(novel_id, db)

    # Construction de l'item : on merge l'id + les data
    new_item: dict[str, Any] = {"id": str(uuid.uuid4()), **form_data.data}

    # Ajout à la section courante
    current_items = _get_section(kb, section)
    updated_items = current_items + [new_item]

    result = KnowledgeBases.update_kb_by_novel_id(
        novel_id=novel_id,
        updated={section: updated_items},
        db=db,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    return new_item


############################
# POST /{section}/{item_id}/update — UpdateKBItem
############################


class KBItemUpdateForm(BaseModel):
    data: dict[str, Any] = Field(..., description="Nouvelles données de l'item (merge avec l'existant).")


@router.post("/{section}/{item_id}/update", response_model=dict)
async def update_kb_item(
    novel_id: str,
    section: KBSection,
    item_id: str,
    form_data: KBItemUpdateForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Met à jour un item existant dans une section de la KB (merge des champs).
    L'`id` de l'item est préservé.

    Returns:
        dict: L'item mis à jour.
    """
    _check_novel_ownership(novel_id, user, db)
    kb = _get_or_create_kb(novel_id, db)

    current_items: list[dict] = _get_section(kb, section)

    # Trouver l'item cible
    target_idx = next(
        (i for i, it in enumerate(current_items) if it.get("id") == item_id),
        None,
    )
    if target_idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Merge : on préserve l'id et on écrase les champs fournis
    updated_item = {**current_items[target_idx], **form_data.data, "id": item_id}
    updated_items = current_items[:target_idx] + [updated_item] + current_items[target_idx + 1 :]

    result = KnowledgeBases.update_kb_by_novel_id(
        novel_id=novel_id,
        updated={section: updated_items},
        db=db,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    return updated_item


############################
# DELETE /{section}/{item_id}/delete — DeleteKBItem
############################


@router.delete("/{section}/{item_id}/delete", response_model=bool)
async def delete_kb_item(
    novel_id: str,
    section: KBSection,
    item_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Supprime un item d'une section de la KB par son `id`.

    Returns:
        bool: True si la suppression a réussi.
    """
    _check_novel_ownership(novel_id, user, db)
    kb = _get_or_create_kb(novel_id, db)

    current_items: list[dict] = _get_section(kb, section)

    original_len = len(current_items)
    updated_items = [it for it in current_items if it.get("id") != item_id]

    if len(updated_items) == original_len:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    result = KnowledgeBases.update_kb_by_novel_id(
        novel_id=novel_id,
        updated={section: updated_items},
        db=db,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    return True


############################
# PUT /{section}/replace    — ReplaceKBSection
############################


@router.put("/{section}/replace", response_model=KnowledgeBaseModel)
async def replace_kb_section(
    novel_id: str,
    section: KBSection,
    form_data: KBSectionReplaceForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Remplace **entièrement** le contenu d'une section KB.
    Chaque item sans `id` se voit attribuer un UUID généré.
    Opération destructive — remplace la liste existante.

    Returns:
        KnowledgeBaseModel: La KB complète après remplacement.
    """
    _check_novel_ownership(novel_id, user, db)
    _get_or_create_kb(novel_id, db)  # Lazy init si nécessaire

    # Garantir que chaque item a un id
    items_with_ids = [
        {**item, "id": item.get("id") or str(uuid.uuid4())}
        for item in form_data.items
    ]

    result = KnowledgeBases.update_kb_by_novel_id(
        novel_id=novel_id,
        updated={section: items_with_ids},
        db=db,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(),
        )

    return result
