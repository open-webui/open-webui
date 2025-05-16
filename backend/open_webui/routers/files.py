import asyncio
from threading import Lock
import logging
import base64
import os
from uuid import uuid4
import json
from pathlib import Path
from fastapi import Form
from typing import Optional, Dict
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.files import (
    FileForm,
    FileModel,
    FileModelResponse,
    Files,
)
from open_webui.models.tasks import AsyncTaskResponse
from open_webui.routers.retrieval import (
    ProcessFileForm,
    process_file,
)
from open_webui.storage.provider import Storage
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.tasks_celery import process_tasks
from open_webui.tasks_celery import celery_app
from celery.result import AsyncResult
from pydantic import BaseModel


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()
############################
# Upload File
############################


@router.post("/", response_model=FileModelResponse)
def upload_file(
    request: Request,
    file: UploadFile = File(...),
    user=Depends(get_verified_user),
    file_metadata: dict = {},
):
    log.info(f"file.content_type: {file.content_type}")
    try:
        unsanitized_filename = file.filename
        filename = os.path.basename(unsanitized_filename)

        # replace filename with uuid
        id = str(uuid4())
        name = filename
        filename = f"{id}_{filename}"
        contents, file_path = Storage.upload_file(file.file, filename)

        file_item = Files.insert_new_file(
            user.id,
            FileForm(
                **{
                    "id": id,
                    "filename": name,
                    "path": file_path,
                    "meta": {
                        "name": name,
                        "content_type": file.content_type,
                        "size": len(contents),
                        "data": file_metadata,
                    },
                }
            ),
        )

        try:
            process_file(request, ProcessFileForm(file_id=id), user=user)
            file_item = Files.get_file_by_id(id=id)
        except Exception as e:
            log.exception(e)
            log.error(f"Error processing file: {file_item.id}")
            file_item = FileModelResponse(
                **{
                    **file_item.model_dump(),
                    "error": str(e.detail) if hasattr(e, "detail") else str(e),
                }
            )

        if file_item:
            return file_item
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error uploading file"),
            )

    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# Async Files routes
############################

@router.post("/async", response_model=AsyncTaskResponse)
async def upload_file_async(
    request: Request,
    file: UploadFile = File(...),
    user=Depends(get_verified_user),
):
    log.info(f"file.content_type: {file.content_type}")

    unsanitized_filename = file.filename
    filename = os.path.basename(unsanitized_filename)

    # replace filename with uuid
    task_id = str(uuid4())
    name = filename
    filename = f"{id}_{filename}"
    contents, file_path = Storage.upload_file(file.file, filename)

    _ = Files.insert_new_file(
        user.id,
        FileForm(
            **{
                "id": task_id,
                "filename": name,
                "path": file_path,
                "meta": {
                    "name": name,
                    "content_type": file.content_type,
                    "size": len(contents),
                },
            }
        ),
    )
    # Envia a task pro RabbitMQ via Celery
    form_data = ProcessFileForm(file_id=task_id)
    # Adiciona os parâmetros necessários para o processamento
    # da task
    # args = {
    #     "collection_name": form_data.collection_name,
    #     "text_splitter": request.app.state.config.TEXT_SPLITTER,
    #     "task_id": task_id,
    #     "chunk_overlap": request.app.state.config.CHUNK_OVERLAP,
    #     "chunk_size": request.app.state.config.CHUNK_SIZE,
    #     "engine": request.app.state.config.CONTENT_EXTRACTION_ENGINE,
    #     "model": request.app.state.config.RAG_EMBEDDING_MODEL,
    #     "tiktoken_encoding_name": request.app.state.config.TIKTOKEN_ENCODING_NAME,
    #     "rag_embedding_engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
    #     "rag_openai_api_base_url": request.app.state.config.RAG_OPENAI_API_BASE_URL,
    #     "rag_ollama_api_key": request.app.state.config.RAG_OLLAMA_API_KEY,
    #     "rag_ollama_base_url": request.app.state.config.RAG_OLLAMA_BASE_URL,
    #     "rag_embedding_batch_size": request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
    #     "tika_server_url": request.app.state.config.TIKA_SERVER_URL,
    #     "pdftotext_server_url": request.app.state.config.PDFTOTEXT_SERVER_URL,
    #     "pdf_extract_images": request.app.state.config.PDF_EXTRACT_IMAGES,
    #     "maxpages_pdftotext": request.app.state.config.MAXPAGES_PDFTOTEXT,
    # }

    args = {'collection_name': form_data.collection_name,
            'text_splitter': request.app.state.config.TEXT_SPLITTER,
            'task_id': task_id,
            'chunk_overlap': request.app.state.config.CHUNK_OVERLAP,
            'chunk_size': request.app.state.config.CHUNK_SIZE,
            'engine': request.app.state.config.CONTENT_EXTRACTION_ENGINE,
            "rag_embedding_model": request.app.state.config.RAG_EMBEDDING_MODEL,
            "tiktoken_encoding_name": request.app.state.config.TIKTOKEN_ENCODING_NAME,
            "rag_embedding_engine": request.app.state.config.RAG_EMBEDDING_ENGINE,
            "rag_openai_api_base_url": request.app.state.config.RAG_OPENAI_API_BASE_URL,
            "rag_ollama_api_key": request.app.state.config.RAG_OLLAMA_API_KEY,
            "rag_ollama_base_url": request.app.state.config.RAG_OLLAMA_BASE_URL,
            "rag_embedding_batch_size": request.app.state.config.RAG_EMBEDDING_BATCH_SIZE,
            "tika_server_url": request.app.state.config.TIKA_SERVER_URL,
            "pdftotext_server_url": request.app.state.config.PDFTOTEXT_SERVER_URL,
            "pdf_extract_images": request.app.state.config.PDF_EXTRACT_IMAGES,
            "maxpages_pdftotext": request.app.state.config.MAXPAGES_PDFTOTEXT,
            }

    try:
        async_result = process_tasks.delay(args=args)
        message = f"Task {task_id} adicionada à fila de processamento"
        log.info(f"Task {task_id} adicionada à fila de processamento")
    except Exception as e:
        log.exception(e)
        log.error(f"Error processing file: {task_id}")
        message = f"Task {task_id} falhou ao ser processada"
        return AsyncTaskResponse(task_id=task_id, status="Error", message=message)
    return AsyncTaskResponse(task_id=async_result.id, status="queued", message=message)

############################
# Get task_status
############################


# Rota opcional para verificar status da task
@router.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    res = AsyncResult(task_id, app=celery_app)
    return {"task_id": task_id, "result": res.result if res.ready() else None}


############################
# List Files
############################


@router.get("/", response_model=list[FileModelResponse])
async def list_files(user=Depends(get_verified_user)):
    if user.role == "admin":
        files = Files.get_files()
    else:
        files = Files.get_files_by_user_id(user.id)
    return files


############################
# Delete All Files
############################


@router.delete("/all")
async def delete_all_files(user=Depends(get_admin_user)):
    result = Files.delete_all_files()
    if result:
        try:
            Storage.delete_all_files()
        except Exception as e:
            log.exception(e)
            log.error("Error deleting files")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error deleting files"),
            )
        return {"message": "All files deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error deleting files"),
        )


############################
# Get File By Id
############################


@router.get("/{id}", response_model=Optional[FileModel])
async def get_file_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if file and (file.user_id == user.id or user.role == "admin"):
        return file
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Get File Data Content By Id
############################


@router.get("/{id}/data/content")
async def get_file_data_content_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if file and (file.user_id == user.id or user.role == "admin"):
        return {"content": file.data.get("content", "")}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Update File Data Content By Id
############################


class ContentForm(BaseModel):
    content: str


@router.post("/{id}/data/content/update")
async def update_file_data_content_by_id(
    request: Request, id: str, form_data: ContentForm, user=Depends(get_verified_user)
):
    file = Files.get_file_by_id(id)

    if file and (file.user_id == user.id or user.role == "admin"):
        try:
            process_file(
                request,
                ProcessFileForm(file_id=id, content=form_data.content),
                user=user,
            )
            file = Files.get_file_by_id(id=id)
        except Exception as e:
            log.exception(e)
            log.error(f"Error processing file: {file.id}")

        return {"content": file.data.get("content", "")}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Get File Content By Id
############################


@router.get("/{id}/content")
async def get_file_content_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)
    if file and (file.user_id == user.id or user.role == "admin"):
        try:
            file_path = Storage.get_file(file.path)
            file_path = Path(file_path)

            # Check if the file already exists in the cache
            if file_path.is_file():
                # Handle Unicode filenames
                filename = file.meta.get("name", file.filename)
                encoded_filename = quote(filename)  # RFC5987 encoding

                content_type = file.meta.get("content_type")
                filename = file.meta.get("name", file.filename)
                encoded_filename = quote(filename)
                headers = {}

                if content_type == "application/pdf" or filename.lower().endswith(
                    ".pdf"
                ):
                    headers["Content-Disposition"] = (
                        f"inline; filename*=UTF-8''{encoded_filename}"
                    )
                    content_type = "application/pdf"
                elif content_type != "text/plain":
                    headers["Content-Disposition"] = (
                        f"attachment; filename*=UTF-8''{encoded_filename}"
                    )

                return FileResponse(file_path, headers=headers, media_type=content_type)

            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
        except Exception as e:
            log.exception(e)
            log.error("Error getting file content")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error getting file content"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get("/{id}/content/html")
async def get_html_file_content_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)
    if file and (file.user_id == user.id or user.role == "admin"):
        try:
            file_path = Storage.get_file(file.path)
            file_path = Path(file_path)

            # Check if the file already exists in the cache
            if file_path.is_file():
                print(f"file_path: {file_path}")
                return FileResponse(file_path)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
        except Exception as e:
            log.exception(e)
            log.error("Error getting file content")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error getting file content"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get("/{id}/content/{file_name}")
async def get_file_content_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if file and (file.user_id == user.id or user.role == "admin"):
        file_path = file.path

        # Handle Unicode filenames
        filename = file.meta.get("name", file.filename)
        encoded_filename = quote(filename)  # RFC5987 encoding
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }

        if file_path:
            file_path = Storage.get_file(file_path)
            file_path = Path(file_path)

            # Check if the file already exists in the cache
            if file_path.is_file():
                return FileResponse(file_path, headers=headers)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
        else:
            # File path doesn’t exist, return the content as .txt if possible
            file_content = file.content.get("content", "")
            file_name = file.filename

            # Create a generator that encodes the file content
            def generator():
                yield file_content.encode("utf-8")

            return StreamingResponse(
                generator(),
                media_type="text/plain",
                headers=headers,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Delete File By Id
############################


@router.delete("/{id}")
async def delete_file_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)
    if file and (file.user_id == user.id or user.role == "admin"):
        # We should add Chroma cleanup here

        result = Files.delete_file_by_id(id)
        if result:
            try:
                Storage.delete_file(file.path)
            except Exception as e:
                log.exception(e)
                log.error("Error deleting files")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("Error deleting files"),
                )
            return {"message": "File deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error deleting file"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
