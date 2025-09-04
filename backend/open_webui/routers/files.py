import asyncio
from threading import Lock
import logging
import os
import uuid
import json
from pathlib import Path
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
    BackgroundTasks,
)
from fastapi.responses import FileResponse, StreamingResponse
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS, REDIS_URL
from open_webui.models.files import (
    FileForm,
    FileModel,
    FileModelResponse,
    Files,
)
from open_webui.routers.retrieval import (
    ProcessFileForm,
    process_file,
    process_file_async,
)
from open_webui.storage.provider import Storage
from open_webui.utils.auth import get_admin_user, get_verified_user
from pydantic import BaseModel
import redis


# Conectando ao Redis usando a URL
redis_url = os.getenv('REDIS_URL')
# decode_responses=True retorna string direto
redis_client = redis.StrictRedis.from_url(redis_url, decode_responses=True)


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
        req_id = str(uuid.uuid4())
        name = filename
        filename = f"{req_id}_{filename}"
        contents, file_path = Storage.upload_file(file.file, filename)

        file_item = Files.insert_new_file(
            user.id,
            FileForm(
                **{
                    "id": req_id,
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
            process_file(request, ProcessFileForm(file_id=req_id), user=user)
            file_item = Files.get_file_by_id(id=req_id)
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

def process_tasks(request, form_data, user, task_id):
    """
    Executa OCR e processamento do PDF de forma assíncrona,
    utilizando Redis para armazenamento de status e resultados (apenas texto).
    """
    redis_key = f"task:{task_id}"

    # Armazenando um dicionário como JSON (simples e legível)
    state = {'status': "Processing document"}
    redis_client.set(redis_key, json.dumps(state))

    try:
        process_file_async(request, form_data, task_id, user)
    except Exception as e:
        log.exception(e)
        state['error'] = str(e)
        state['status'] = "Processing Failed"
        redis_client.set(redis_key, json.dumps(state))
        raise e

    state['status'] = "Processing Completed"
    redis_client.set(redis_key, json.dumps(state))


@router.post("/async")
async def upload_file_async(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user=Depends(get_verified_user),
):
    log.info(f"file.content_type: {file.content_type}")

    unsanitized_filename = file.filename
    filename = os.path.basename(unsanitized_filename)

    # replace filename with uuid
    task_id = str(uuid.uuid4())

    redis_key = f"task:{task_id}"

    name = filename
    filename = f"{id}_{filename}"
    try:
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

        background_tasks.add_task(
            process_tasks,
            request,
            ProcessFileForm(file_id=task_id),
            user,
            task_id,
        )
        # file_item = Files.get_file_by_id(id=id)

        return {"task_id": task_id}
    except Exception as e:
        log.exception(e)
        # Atualiza status da task em caso de erro
        error_state = {
            "status": "Processing Failed",
            "result": None,
            "error": str(e),
        }
        redis_client.set(redis_key, json.dumps(error_state))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# Get task_status
############################


@router.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    redis_key = f"task:{task_id}"
    state_json = redis_client.get(redis_key)
    if state_json:
        state = json.loads(state_json)
        status = state.get("status", "not_found")
        if status == "Process completed":
            status = "Processing Completed"
        return {
            "task_id": task_id,
            "status": status,
            "error": state.get("error"),
        }
    return {
        "task_id": task_id,
        "status": "not_found",
        "error": "Task ID not found",
    }


@router.get("/get_tasks")
def get_tasks():
    # Busca todas as chaves de tasks
    keys = redis_client.keys("task:*")
    task_ids = [k.split("task:")[1] for k in keys]
    if task_ids:
        return {"task_ids": task_ids}
    return {"message": "No tasks found"}

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
