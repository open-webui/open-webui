from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Request
import logging
from open_webui.routers.progress import endWhileRun
from open_webui.models.knowledge import (
    Knowledges,
    KnowledgeForm,
    KnowledgeResponse,
    KnowledgeUserResponse,
)

from open_webui.routers.retrieval import get_file_id
from open_webui.utils.parser import PARSER_TYPE
from open_webui.models.files import Files, FileModel, FileMetadataResponse
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.routers.retrieval import (
    process_file,
    ProcessFileForm,
    process_files_batch,
    BatchProcessFilesForm,
)
from open_webui.functions import get_parsers_by_type, get_all_parsers, get_file_relevant_parsers

from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import has_access, has_permission

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.models import Models, ModelForm
from pathlib import Path
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


############################
# getKnowledgeBases
############################


@router.get("/", response_model=list[KnowledgeUserResponse])
async def get_knowledge(user=Depends(get_verified_user)):
    knowledge_bases = []

    if user.role == "admin":
        knowledge_bases = Knowledges.get_knowledge_bases()
    else:
        knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(user.id, "read")

    # Get files for each knowledge base
    knowledge_with_files = []
    for knowledge_base in knowledge_bases:
        files = []
        if knowledge_base.data:
            files = Files.get_file_metadatas_by_ids(
                knowledge_base.data.get("file_ids", [])
            )

            # Check if all files exist
            if len(files) != len(knowledge_base.data.get("file_ids", [])):
                missing_files = list(
                    set(knowledge_base.data.get("file_ids", []))
                    - set([file.id for file in files])
                )
                if missing_files:
                    data = knowledge_base.data or {}
                    file_ids = data.get("file_ids", [])

                    for missing_file in missing_files:
                        file_ids.remove(missing_file)

                    data["file_ids"] = file_ids
                    Knowledges.update_knowledge_data_by_id(
                        id=knowledge_base.id, data=data
                    )

                    files = Files.get_file_metadatas_by_ids(file_ids)

        knowledge_with_files.append(
            KnowledgeUserResponse(
                **knowledge_base.model_dump(),
                files=files,
            )
        )

    return knowledge_with_files


@router.get("/list", response_model=list[KnowledgeUserResponse])
async def get_knowledge_list(user=Depends(get_verified_user)):
    knowledge_bases = []

    if user.role == "admin":
        knowledge_bases = Knowledges.get_knowledge_bases()
    else:
        knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(user.id, "write")

    # Get files for each knowledge base
    knowledge_with_files = []
    for knowledge_base in knowledge_bases:
        files = []
        if knowledge_base.data:
            files = Files.get_file_metadatas_by_ids(
                knowledge_base.data.get("file_ids", [])
            )

            # Check if all files exist
            if len(files) != len(knowledge_base.data.get("file_ids", [])):
                missing_files = list(
                    set(knowledge_base.data.get("file_ids", []))
                    - set([file.id for file in files])
                )
                if missing_files:
                    data = knowledge_base.data or {}
                    file_ids = data.get("file_ids", [])

                    for missing_file in missing_files:
                        file_ids.remove(missing_file)

                    data["file_ids"] = file_ids
                    Knowledges.update_knowledge_data_by_id(
                        id=knowledge_base.id, data=data
                    )

                    files = Files.get_file_metadatas_by_ids(file_ids)

        knowledge_with_files.append(
            KnowledgeUserResponse(
                **knowledge_base.model_dump(),
                files=files,
            )
        )
    return knowledge_with_files


############################
# CreateNewKnowledge
############################


@router.post("/create", response_model=Optional[KnowledgeResponse])
async def create_new_knowledge(
        request: Request, form_data: KnowledgeForm, user=Depends(get_verified_user)
):
    if user.role != "admin" and not has_permission(
            user.id, "workspace.knowledge", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    knowledge = Knowledges.insert_new_knowledge(user.id, form_data)

    if knowledge:
        return knowledge
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FILE_EXISTS,
        )


############################
# ReindexKnowledgeFiles
############################
@router.post("/reindex", response_model=bool)
async def reindex_knowledge_files(request: Request, user=Depends(get_verified_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    knowledge_bases = Knowledges.get_knowledge_bases()

    log.info(f"Starting reindexing for {len(knowledge_bases)} knowledge bases")

    deleted_knowledge_bases = []

    parsers = get_all_parsers(request)
    for knowledge_base in knowledge_bases:
        # -- Robust error handling for missing or invalid data
        if not knowledge_base.data or not isinstance(knowledge_base.data, dict):
            log.warning(
                f"Knowledge base {knowledge_base.id} has no data or invalid data ({knowledge_base.data!r}). Deleting."
            )
            try:
                Knowledges.delete_knowledge_by_id(id=knowledge_base.id)
                deleted_knowledge_bases.append(knowledge_base.id)
            except Exception as e:
                log.error(
                    f"Failed to delete invalid knowledge base {knowledge_base.id}: {e}"
                )
            continue

        try:
            file_ids = knowledge_base.data.get("file_ids", [])
            files = Files.get_files_by_ids(file_ids)

            for parser in parsers:
                parser.delete_collection(knowledge_base.id)

            try:
                if VECTOR_DB_CLIENT.has_collection(collection_name=knowledge_base.id):
                    VECTOR_DB_CLIENT.delete_collection(
                        collection_name=knowledge_base.id
                    )
            except Exception as e:
                log.error(f"Error deleting collection {knowledge_base.id}: {str(e)}")
                continue  # Skip, don't raise

            failed_files = []
            for file in files:
                try:
                    process_file(
                        request,
                        ProcessFileForm(
                            file_id=file.id, collection_name=knowledge_base.id
                        ),
                        user=user,
                    )
                except Exception as e:
                    log.error(
                        f"Error processing file {file.filename} (ID: {file.id}): {str(e)}"
                    )
                    failed_files.append({"file_id": file.id, "error": str(e)})
                    continue

        except Exception as e:
            log.error(f"Error processing knowledge base {knowledge_base.id}: {str(e)}")
            # Don't raise, just continue
            continue

        if failed_files:
            log.warning(
                f"Failed to process {len(failed_files)} files in knowledge base {knowledge_base.id}"
            )
            for failed in failed_files:
                log.warning(f"File ID: {failed['file_id']}, Error: {failed['error']}")

    log.info(
        f"Reindexing completed. Deleted {len(deleted_knowledge_bases)} invalid knowledge bases: {deleted_knowledge_bases}"
    )
    return True


############################
# GetKnowledgeById
############################


class KnowledgeFilesResponse(KnowledgeResponse):
    files: list[FileMetadataResponse]


@router.get("/{id}", response_model=Optional[KnowledgeFilesResponse])
async def get_knowledge_by_id(id: str, user=Depends(get_verified_user)):
    knowledge = Knowledges.get_knowledge_by_id(id=id)

    if knowledge:

        if (
                user.role == "admin"
                or knowledge.user_id == user.id
                or has_access(user.id, "read", knowledge.access_control)
        ):
            file_ids = knowledge.data.get("file_ids", []) if knowledge.data else []
            files = Files.get_file_metadatas_by_ids(file_ids)

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


@router.post("/{id}/update", response_model=Optional[KnowledgeFilesResponse])
async def update_knowledge_by_id(
        id: str,
        form_data: KnowledgeForm,
        user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    # Is the user the original creator, in a group with write access, or an admin
    if (
            knowledge.user_id != user.id
            and not has_access(user.id, "write", knowledge.access_control)
            and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    knowledge = Knowledges.update_knowledge_by_id(id=id, form_data=form_data)
    if knowledge:
        file_ids = knowledge.data.get("file_ids", []) if knowledge.data else []
        files = Files.get_files_by_ids(file_ids)

        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=files,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ID_TAKEN,
        )


############################
# AddFileToKnowledge
############################


class KnowledgeFileIdForm(BaseModel):
    file_id: str


@router.post("/{id}/file/add", response_model=Optional[KnowledgeFilesResponse])
def add_file_to_knowledge_by_id(
        request: Request,
        id: str,
        form_data: KnowledgeFileIdForm,
        user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)

    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
            knowledge.user_id != user.id
            and not has_access(user.id, "write", knowledge.access_control)
            and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    file = Files.get_file_by_id(form_data.file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if not file.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FILE_NOT_PROCESSED,
        )

    parsers = get_parsers_by_type(request, PARSER_TYPE.FILE, file.filename)
    # content is the raw data and not to be used in collection
    content_keys = [k for k in file.data.keys() if k != 'content']

    assert 'content' in file.data.keys()
    assert len(content_keys) > 0

    for key in content_keys:
        content = file.data[key]

        assert 'texts' in content.keys()
        assert 'embeddings' in content.keys()
        assert 'metadatas' in content.keys()

        for parser in parsers:
            parser.store(request,
                         id,
                         content['texts'],
                         content['embeddings'],
                         content['metadatas'])

    if knowledge:
        data = knowledge.data or {}
        file_ids = data.get("file_ids", [])

        Files.update_file_metadata_by_id(
            file.id,
            {
                "collection_name": id,
            },
        )

        if form_data.file_id not in file_ids:
            file_ids.append(form_data.file_id)
            data["file_ids"] = file_ids

            knowledge = Knowledges.update_knowledge_data_by_id(id=id, data=data)

            if knowledge:
                files = Files.get_file_metadatas_by_ids(file_ids)

                return KnowledgeFilesResponse(
                    **knowledge.model_dump(),
                    files=files,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("knowledge"),
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("file_id"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.post("/{id}/file/update", response_model=Optional[KnowledgeFilesResponse])
def update_file_from_knowledge_by_id(
        request: Request,
        id: str,
        form_data: KnowledgeFileIdForm,
        user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
            knowledge.user_id != user.id
            and not has_access(user.id, "write", knowledge.access_control)
            and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    file = Files.get_file_by_id(form_data.file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    parsers = get_file_relevant_parsers(request, file.filename)
    for parser in parsers:
        parser.delete_doc(knowledge.id, file.filename)

    try:
        process_file(
            request,
            ProcessFileForm(file_id=form_data.file_id, collection_name=id),
            user=user,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if knowledge:
        data = knowledge.data or {}
        file_ids = data.get("file_ids", [])

        files = Files.get_file_metadatas_by_ids(file_ids)

        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=files,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# RemoveFileFromKnowledge
############################


@router.post("/{id}/file/remove", response_model=Optional[KnowledgeFilesResponse])
def remove_file_from_knowledge_by_id(
        request: Request,
        id: str,
        form_data: KnowledgeFileIdForm,
        user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
            knowledge.user_id != user.id
            and not has_access(user.id, "write", knowledge.access_control)
            and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    file = Files.get_file_by_id(form_data.file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    file_collection = f"file-{form_data.file_id}"
    parsers = get_file_relevant_parsers(request, file.filename)
    for parser in parsers:
        parser.delete_segment_by_file_id(file_collection, file.filename)
        parser.delete_doc(file_collection)
        # note that this is only deleting the file-specific collection
        parser.delete_collection(file_collection)
        parser.compact_chroma_fts()
    # Delete file from database
    Files.delete_file_by_id(form_data.file_id)

    if knowledge:
        data = knowledge.data or {}
        file_ids = data.get("file_ids", [])

        if form_data.file_id in file_ids:
            file_ids.remove(form_data.file_id)
            data["file_ids"] = file_ids

            knowledge = Knowledges.update_knowledge_data_by_id(id=id, data=data)

            if knowledge:
                if file.path:
                    try:
                        Path(file.path).unlink(missing_ok=True)
                        log.info(f'Deleted physical path: {file.path}')
                    except Exception as e:
                        log.error(f'Failed to delete file: {e}')
                files = Files.get_file_metadatas_by_ids(file_ids)

                return KnowledgeFilesResponse(
                    **knowledge.model_dump(),
                    files=files,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("knowledge"),
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("file_id"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    

#Router used to end embedding if prompted by the user
@router.post("/{id}/process/file/stop", response_model=Optional[KnowledgeFilesResponse])
def endduringembedding(
        request: Request,
        id: str,
        user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if (
        knowledge.user_id != user.id
        and not has_access(user.id, "write", knowledge.access_control)
        and user.role != "admin"
):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    endWhileRun()
    file_id = get_file_id()
    Files.delete_file_by_id(id=file_id)

            
############################
# DeleteKnowledgeById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_knowledge_by_id(request: Request,
                                 id: str,
                                 user=Depends(get_verified_user)):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
            knowledge.user_id != user.id
            and not has_access(user.id, "write", knowledge.access_control)
            and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    log.info(f"Deleting knowledge base: {id} (name: {knowledge.name})")

    # Get all models
    models = Models.get_all_models()
    log.info(f"Found {len(models)} models to check for knowledge base {id}")

    # Update models that reference this knowledge base
    for model in models:
        if model.meta and hasattr(model.meta, "knowledge"):
            knowledge_list = model.meta.knowledge or []
            # Filter out the deleted knowledge base
            updated_knowledge = [k for k in knowledge_list if k.get("id") != id]

            # If the knowledge list changed, update the model
            if len(updated_knowledge) != len(knowledge_list):
                log.info(f"Updating model {model.id} to remove knowledge base {id}")
                model.meta.knowledge = updated_knowledge
                # Create a ModelForm for the update
                model_form = ModelForm(
                    id=model.id,
                    name=model.name,
                    base_model_id=model.base_model_id,
                    meta=model.meta,
                    params=model.params,
                    access_control=model.access_control,
                    is_active=model.is_active,
                )
                Models.update_model_by_id(model.id, model_form)

    # Clean up vector DB
    try:
        parsers = get_all_parsers(request)
        for parser in parsers:
            parser.delete_collection(id)
    except Exception as e:
        log.debug(e)
        pass
    result = Knowledges.delete_knowledge_by_id(id=id)
    return result


############################
# ResetKnowledgeById
############################


@router.post("/{id}/reset", response_model=Optional[KnowledgeResponse])
async def reset_knowledge_by_id(request: Request,
                                id: str,
                                user=Depends(get_verified_user)):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
            knowledge.user_id != user.id
            and not has_access(user.id, "write", knowledge.access_control)
            and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    try:
        parsers = get_all_parsers(request)
        for parser in parsers:
            parser.delete_collection(id)
    except Exception as e:
        log.debug(e)
        pass

    knowledge = Knowledges.update_knowledge_data_by_id(id=id, data={"file_ids": []})

    return knowledge


############################
# AddFilesToKnowledge
############################


@router.post("/{id}/files/batch/add", response_model=Optional[KnowledgeFilesResponse])
def add_files_to_knowledge_batch(
        request: Request,
        id: str,
        form_data: list[KnowledgeFileIdForm],
        user=Depends(get_verified_user),
):
    """
    Add multiple files to a knowledge base
    """
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
            knowledge.user_id != user.id
            and not has_access(user.id, "write", knowledge.access_control)
            and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Get files content
    log.info(f"files/batch/add - {len(form_data)} files")
    files: List[FileModel] = []
    for form in form_data:
        file = Files.get_file_by_id(form.file_id)
        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {form.file_id} not found",
            )
        files.append(file)

    # Process files
    try:
        result = process_files_batch(
            request=request,
            form_data=BatchProcessFilesForm(files=files, collection_name=id),
            user=user,
        )
    except Exception as e:
        log.error(
            f"add_files_to_knowledge_batch: Exception occurred: {e}", exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Add successful files to knowledge base
    data = knowledge.data or {}
    existing_file_ids = data.get("file_ids", [])

    # Only add files that were successfully processed
    successful_file_ids = [r.file_id for r in result.results if r.status == "completed"]
    for file_id in successful_file_ids:
        if file_id not in existing_file_ids:
            existing_file_ids.append(file_id)

    data["file_ids"] = existing_file_ids
    knowledge = Knowledges.update_knowledge_data_by_id(id=id, data=data)

    # If there were any errors, include them in the response
    if result.errors:
        error_details = [f"{err.file_id}: {err.error}" for err in result.errors]
        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=Files.get_file_metadatas_by_ids(existing_file_ids),
            warnings={
                "message": "Some files failed to process",
                "errors": error_details,
            },
        )

    return KnowledgeFilesResponse(
        **knowledge.model_dump(),
        files=Files.get_file_metadatas_by_ids(existing_file_ids),
    )
