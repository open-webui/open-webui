from fastapi import Depends, FastAPI, HTTPException, status
from datetime import datetime, timedelta
from typing import List, Union, Optional

from fastapi import APIRouter
from pydantic import BaseModel
import json

from apps.webui.models.documents import (
    Documents,
    DocumentForm,
    DocumentUpdateForm,
    DocumentModel,
    DocumentResponse,
)

from utils.utils import get_verified_user, get_admin_user
from constants import ERROR_MESSAGES

router = APIRouter()

############################
# GetDocuments
############################


@router.get("/", response_model=List[DocumentResponse])
async def get_documents(user=Depends(get_verified_user)):
    docs = [
        DocumentResponse(
            **{
                **doc.model_dump(),
                "content": json.loads(doc.content if doc.content else "{}"),
            }
        )
        for doc in Documents.get_docs()
    ]
    return docs


############################
# CreateNewDoc
############################


@router.post("/create", response_model=Optional[DocumentResponse])
async def create_new_doc(form_data: DocumentForm, user=Depends(get_admin_user)):
    doc = Documents.get_doc_by_name(form_data.name)
    if doc == None:
        doc = Documents.insert_new_doc(user.id, form_data)

        if doc:
            return DocumentResponse(
                **{
                    **doc.model_dump(),
                    "content": json.loads(doc.content if doc.content else "{}"),
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.FILE_EXISTS,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NAME_TAG_TAKEN,
        )


############################
# GetDocByName
############################


@router.get("/doc", response_model=Optional[DocumentResponse])
async def get_doc_by_name(name: str, user=Depends(get_verified_user)):
    doc = Documents.get_doc_by_name(name)

    if doc:
        return DocumentResponse(
            **{
                **doc.model_dump(),
                "content": json.loads(doc.content if doc.content else "{}"),
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# TagDocByName
############################


class TagItem(BaseModel):
    name: str


class TagDocumentForm(BaseModel):
    name: str
    tags: List[dict]


@router.post("/doc/tags", response_model=Optional[DocumentResponse])
async def tag_doc_by_name(form_data: TagDocumentForm, user=Depends(get_verified_user)):
    doc = Documents.update_doc_content_by_name(form_data.name, {"tags": form_data.tags})

    if doc:
        return DocumentResponse(
            **{
                **doc.model_dump(),
                "content": json.loads(doc.content if doc.content else "{}"),
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateDocByName
############################


@router.post("/doc/update", response_model=Optional[DocumentResponse])
async def update_doc_by_name(
    name: str, form_data: DocumentUpdateForm, user=Depends(get_admin_user)
):
    doc = Documents.update_doc_by_name(name, form_data)
    if doc:
        return DocumentResponse(
            **{
                **doc.model_dump(),
                "content": json.loads(doc.content if doc.content else "{}"),
            }
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NAME_TAG_TAKEN,
        )

############################
# BulkTagDocuments
############################

class BulkTagForm(BaseModel):
    doc_names: List[str]
    tags: List[str]
    action: str  # 'add' or 'remove'

@router.post("/bulk_tag", response_model=List[DocumentResponse])
async def bulk_tag_documents(form_data: BulkTagForm, user=Depends(get_verified_user)):
    updated_docs = []
    for doc_name in form_data.doc_names:
        doc = Documents.get_doc_by_name(doc_name)
        if doc:
            current_content = json.loads(doc.content) if doc.content else {}
            current_tags = current_content.get('tags', [])
            
            if form_data.action == 'add':
                existing_tag_names = {tag["name"] for tag in current_tags}
                for new_tag in form_data.tags:
                    if new_tag not in existing_tag_names:
                        current_tags.append({"name": new_tag})
            elif form_data.action == 'remove':
                current_tags = [tag for tag in current_tags if tag["name"] not in form_data.tags]
            else:
                raise HTTPException(status_code=400, detail="Invalid action")
            
            current_content['tags'] = current_tags
            updated_doc = Documents.update_doc_content_by_name(doc_name, current_content)
            if updated_doc:
                updated_docs.append(DocumentResponse(
                    **{
                        **updated_doc.model_dump(),
                        "content": json.loads(updated_doc.content if updated_doc.content else "{}"),
                    }
                ))
    
    return updated_docs

############################
# DeleteDocByName
############################


@router.delete("/doc/delete", response_model=bool)
async def delete_doc_by_name(name: str, user=Depends(get_admin_user)):
    result = Documents.delete_doc_by_name(name)
    return result
