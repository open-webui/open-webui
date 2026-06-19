"""Router do modulo editorial (Funcionalidade 1 + base da ficha por autor F3).

Fatia 1: camada de dados + endpoints de projeto e ficha (versionada) + criacao
do registro de documento (a ingestao/parse de verdade entra na Fatia 2/3).

Isolamento: toda operacao exige que o projeto pertenca ao autor (user_id).
Admin pode acessar para suporte/auditoria.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from open_webui.constants import ERROR_MESSAGES
from open_webui.editorial.ingest import run_ingestion
from open_webui.editorial.jobs import get_job_queue
from open_webui.models.editorial import (
    Documents,
    DocumentIngestForm,
    EditorialDocumentModel,
    EditorialProjectModel,
    EditorialProjectSheetModel,
    Projects,
    ProjectForm,
    Sheets,
    SheetForm,
)
from open_webui.storage.provider import Storage
from open_webui.utils.auth import get_verified_user

log = logging.getLogger(__name__)

router = APIRouter()


async def _get_owned_project(project_id: str, user) -> EditorialProjectModel:
    """Carrega o projeto garantindo posse. Retorna 404 se nao existir ou nao
    pertencer ao autor (nao vaza existencia). Admin tem acesso para suporte."""
    project = await Projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if project.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    return project


############################
# Projetos
############################


@router.post("/projects", response_model=EditorialProjectModel)
async def create_project(form: ProjectForm, user=Depends(get_verified_user)):
    return await Projects.create(user.id, form)


@router.get("/projects", response_model=list[EditorialProjectModel])
async def list_projects(user=Depends(get_verified_user)):
    return await Projects.get_by_user(user.id)


@router.get("/projects/{project_id}", response_model=EditorialProjectModel)
async def get_project(project_id: str, user=Depends(get_verified_user)):
    return await _get_owned_project(project_id, user)


############################
# Ficha viva (versionada)
############################


@router.get("/projects/{project_id}/sheet", response_model=Optional[EditorialProjectSheetModel])
async def get_current_sheet(project_id: str, user=Depends(get_verified_user)):
    await _get_owned_project(project_id, user)
    return await Sheets.get_current(project_id)


@router.post("/projects/{project_id}/sheet", response_model=EditorialProjectSheetModel)
async def create_sheet_version(
    project_id: str, form: SheetForm, user=Depends(get_verified_user)
):
    await _get_owned_project(project_id, user)
    return await Sheets.create_version(
        project_id=project_id,
        data=form.data,
        created_by=user.id,
        change_note=form.change_note,
    )


@router.get(
    "/projects/{project_id}/sheet/versions",
    response_model=list[EditorialProjectSheetModel],
)
async def list_sheet_versions(project_id: str, user=Depends(get_verified_user)):
    await _get_owned_project(project_id, user)
    return await Sheets.list_versions(project_id)


############################
# Documentos (Fatia 1: cria o registro; parse vem na Fatia 2/3)
############################


@router.post(
    "/projects/{project_id}/documents",
    response_model=EditorialDocumentModel,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_document(
    project_id: str, form: DocumentIngestForm, user=Depends(get_verified_user)
):
    await _get_owned_project(project_id, user)
    doc = await Documents.create(user.id, project_id, form)
    # Enfileira a ingestao. No modo inline (default) roda agora e ja atualiza o
    # status; com backend arq, fica pendente e o cliente acompanha via GET.
    await get_job_queue().enqueue(run_ingestion, doc.id)
    return await Documents.get(doc.id)


@router.get("/documents/{document_id}", response_model=EditorialDocumentModel)
async def get_document(document_id: str, user=Depends(get_verified_user)):
    doc = await Documents.get(document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if doc.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    return doc


@router.get("/documents/{document_id}/tree")
async def get_document_tree(document_id: str, user=Depends(get_verified_user)):
    doc = await Documents.get(document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if doc.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if not doc.tree_ref:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"arvore indisponivel (status={doc.status})",
        )
    local_path = Storage.get_file(doc.tree_ref)
    with open(local_path, "r", encoding="utf-8") as f:
        return json.load(f)
