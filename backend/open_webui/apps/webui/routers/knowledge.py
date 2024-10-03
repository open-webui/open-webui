import json
from typing import Optional, Union
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status


from open_webui.apps.webui.models.knowledge import (
    Knowledges,
    KnowledgeUpdateForm,
    KnowledgeForm,
    KnowledgeResponse,
)
from open_webui.apps.webui.models.files import Files, FileModel

from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.utils import get_admin_user, get_verified_user

router = APIRouter()

############################
# GetKnowledgeItems
############################


@router.get(
    "/", response_model=Optional[Union[list[KnowledgeResponse], KnowledgeResponse]]
)
async def get_knowledge_items(
    id: Optional[str] = None, user=Depends(get_verified_user)
):
    if id:
        knowledge = Knowledges.get_knowledge_by_id(id=id)

        if knowledge:
            return knowledge
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )
    else:
        return [
            KnowledgeResponse(**knowledge.model_dump())
            for knowledge in Knowledges.get_knowledge_items()
        ]


############################
# CreateNewKnowledge
############################


@router.post("/create", response_model=Optional[KnowledgeResponse])
async def create_new_knowledge(form_data: KnowledgeForm, user=Depends(get_admin_user)):
    knowledge = Knowledges.insert_new_knowledge(user.id, form_data)

    if knowledge:
        return knowledge
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FILE_EXISTS,
        )


############################
# GetKnowledgeById
############################


class KnowledgeFilesResponse(KnowledgeResponse):
    files: list[FileModel]


@router.get("/{id}", response_model=Optional[KnowledgeFilesResponse])
async def get_knowledge_by_id(id: str, user=Depends(get_verified_user)):
    knowledge = Knowledges.get_knowledge_by_id(id=id)

    if knowledge:
        file_ids = knowledge.data.get("file_ids", []) if knowledge.data else []
        files = Files.get_files_by_ids(file_ids)

        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=files,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateKnowledgeById
############################


@router.post("/{id}/update", response_model=Optional[KnowledgeResponse])
async def update_knowledge_by_id(
    id: str,
    form_data: KnowledgeUpdateForm,
    user=Depends(get_admin_user),
):
    knowledge = Knowledges.update_knowledge_by_id(id=id, form_data=form_data)

    if knowledge:
        return knowledge
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ID_TAKEN,
        )


############################
# DeleteKnowledgeById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_knowledge_by_id(id: str, user=Depends(get_admin_user)):
    result = Knowledges.delete_knowledge_by_id(id=id)
    return result
