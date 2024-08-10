from fastapi import Depends, FastAPI, HTTPException, status
from datetime import datetime, timedelta
from typing import List, Union, Optional
import os


from fastapi import APIRouter
from pydantic import BaseModel
import json

from apps.webui.models.documents import (
    Documents,
    DocumentForm,
    DocumentUpdateForm,
    DocumentResponse,
)

from utils.utils import get_verified_user, get_admin_user

from config import (
    UPLOADS_DIR_NAME,
)

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
    
    # Ensure location field is set to Uploads Directory Name (UPLOAD_DIR_NAME)
    # as the form location data and include it in to the db insertion since this endpoint only serve the file upload function

    if form_data.location is None:
        form_data.location = UPLOADS_DIR_NAME

    # Extract file extension and add it as a tag
    file_extension = os.path.splitext(form_data.filename)[1].lstrip('.')  # Extract the file extension

    # Initialize tags and add file extension as a tag
    tags = [f".{file_extension}"]

    
    # Fetch or create the document
    doc = Documents.get_doc_by_name(form_data.name)
    if doc is None:
        # Prepare the content field with tags
        content_data = {
            "tags": [{"name": name} for name in tags]
        }
        
        form_data.content = json.dumps(content_data)

        # Insert the new document
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
    name: str,
    form_data: DocumentUpdateForm,
    user=Depends(get_admin_user),
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
# DeleteDocByName
############################


@router.delete("/doc/delete", response_model=bool)
async def delete_doc_by_name(name: str, user=Depends(get_admin_user)):
    result = Documents.delete_doc_by_name(name)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT,
        )
    return result
