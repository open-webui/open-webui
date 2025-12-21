from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Request, UploadFile, File
import logging

from open_webui.models.knowledge import (
    Knowledges,
    KnowledgeForm,
    KnowledgeResponse,
    KnowledgeUserResponse,
)
from open_webui.models.files import Files, FileModel, FileModelResponse
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.routers.retrieval import (
    process_file,
    ProcessFileForm,
    process_files_batch,
    BatchProcessFilesForm,
)
from open_webui.utils.job_queue import is_job_queue_available
from open_webui.storage.provider import Storage
from open_webui.routers.audio import transcribe
from open_webui.utils.file_cleanup import (
    cleanup_file_completely,
    cleanup_file_from_knowledge_only,
)

from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import has_access, has_permission
from open_webui.utils.super_admin import is_super_admin


from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.models import Models, ModelForm

# OpenTelemetry instrumentation (conditional import)
try:
    from open_webui.utils.otel_instrumentation import (
        trace_span_async,
        add_span_event,
        set_span_attribute,
    )
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    # Create no-op functions if OTEL not available
    # NOTE: Must be regular function (not async def) to match @asynccontextmanager signature
    def trace_span_async(*args, **kwargs):
        span_name = kwargs.get('name', args[0] if args else 'unknown')
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def _noop():
            # Get logger at call time (log variable will be defined by then)
            _log = logging.getLogger(__name__)
            try:
                _log.debug(f"[trace_span_async] Generator entering (OTEL unavailable, no-op) for span '{span_name}'")
                yield None
                _log.debug(f"[trace_span_async] Generator exiting normally (OTEL unavailable, no-op) for span '{span_name}'")
            except GeneratorExit as ge:
                _log.debug(f"[trace_span_async] GeneratorExit caught (OTEL unavailable, no-op) for span '{span_name}': {ge}")
                # Properly handle generator exit
                raise
            except Exception as e:
                _log.warning(f"[trace_span_async] Exception thrown into generator (OTEL unavailable, no-op) for span '{span_name}': {type(e).__name__}: {e}", exc_info=True)
                # Properly handle exceptions thrown into generator - must re-raise or return
                # Re-raising ensures the exception propagates correctly
                raise
        return _noop()
    def add_span_event(*args, **kwargs):
        pass
    def set_span_attribute(*args, **kwargs):
        pass

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

# Safe wrapper functions that NEVER fail - OTEL is monitoring only, must not affect task execution
def safe_add_span_event(event_name, attributes=None):
    """Safely add span event - never fails, even if OTEL is broken"""
    try:
        add_span_event(event_name, attributes)
    except Exception as e:
        log.debug(f"OTEL add_span_event failed (non-critical): {e}")

def safe_set_span_attribute(span, key, value):
    """Safely set span attribute - never fails, even if OTEL is broken"""
    try:
        if span:
            set_span_attribute(span, key, value)
    except Exception as e:
        log.debug(f"OTEL set_span_attribute failed (non-critical): {e}")

def safe_trace_span_async(*args, **kwargs):
    """Safely create async trace span - never fails, even if OTEL is broken
    
    Returns an async context manager (same signature as trace_span_async).
    Can be used with: async with safe_trace_span_async(...) as span:
    """
    span_name = kwargs.get('name', args[0] if args else 'unknown')
    try:
        log.debug(f"[safe_trace_span_async] Attempting to create span '{span_name}'")
        return trace_span_async(*args, **kwargs)  # Returns async context manager, not a coroutine
    except Exception as e:
        log.warning(f"[safe_trace_span_async] OTEL trace_span_async failed (non-critical) for span '{span_name}': {type(e).__name__}: {e}", exc_info=True)
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def _noop():
            try:
                log.debug(f"[safe_trace_span_async] Generator entering (safe fallback) for span '{span_name}'")
                yield None
                log.debug(f"[safe_trace_span_async] Generator exiting normally (safe fallback) for span '{span_name}'")
            except GeneratorExit as ge:
                log.debug(f"[safe_trace_span_async] GeneratorExit caught (safe fallback) for span '{span_name}': {ge}")
                # Properly handle generator exit
                raise
            except Exception as gen_exc:
                log.warning(f"[safe_trace_span_async] Exception thrown into generator (safe fallback) for span '{span_name}': {type(gen_exc).__name__}: {gen_exc}", exc_info=True)
                # Properly handle exceptions thrown into generator - must re-raise or return
                # Re-raising ensures the exception propagates correctly
                raise
        return _noop()

router = APIRouter()

############################
# getKnowledgeBases
############################


@router.get("/", response_model=list[KnowledgeUserResponse])
async def get_knowledge(user=Depends(get_verified_user)):
    knowledge_bases = []

    # if user.role == "admin":
    #     knowledge_bases = Knowledges.get_knowledge_bases()
    # else:
    knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(user.id, "read")

    # Batch file operations: Collect all file_ids from all knowledge bases first
    all_file_ids = []
    knowledge_file_ids_map = {}  # Maps knowledge_base.id -> list of file_ids
    
    for knowledge_base in knowledge_bases:
        file_ids = []
        if knowledge_base.data:
            file_ids = knowledge_base.data.get("file_ids", [])
        
        if file_ids:
            all_file_ids.extend(file_ids)
            knowledge_file_ids_map[knowledge_base.id] = file_ids
        else:
            knowledge_file_ids_map[knowledge_base.id] = []

    # Single batch query for all file metadata
    all_files_dict = {}
    if all_file_ids:
        all_files = Files.get_file_metadatas_by_ids(all_file_ids)
        all_files_dict = {file.id: file for file in all_files}

    # Build response with files mapped back to knowledge bases
    knowledge_with_files = []
    knowledge_bases_to_update = []  # Track knowledge bases with missing files
    
    for knowledge_base in knowledge_bases:
        file_ids = knowledge_file_ids_map.get(knowledge_base.id, [])
        files = []
        
        if file_ids:
            # Get files from the batch-loaded dictionary
            files = [all_files_dict[file_id] for file_id in file_ids if file_id in all_files_dict]
            
            # Check if all files exist
            if len(files) != len(file_ids):
                missing_files = list(set(file_ids) - set([file.id for file in files]))
                if missing_files:
                    # Track for batch update
                    knowledge_bases_to_update.append({
                        "knowledge_base": knowledge_base,
                        "missing_files": missing_files,
                        "file_ids": file_ids
                    })

        knowledge_with_files.append(
            KnowledgeUserResponse(
                **knowledge_base.model_dump(),
                files=files,
            )
        )
    
    # Batch update knowledge bases with missing files removed
    for kb_update in knowledge_bases_to_update:
        data = kb_update["knowledge_base"].data or {}
        file_ids = [fid for fid in kb_update["file_ids"] if fid not in kb_update["missing_files"]]
        data["file_ids"] = file_ids
        Knowledges.update_knowledge_data_by_id(id=kb_update["knowledge_base"].id, data=data)
        
        # Update the response with corrected files
        for kb_response in knowledge_with_files:
            if kb_response.id == kb_update["knowledge_base"].id:
                kb_response.files = [all_files_dict[fid] for fid in file_ids if fid in all_files_dict]
                break

    return knowledge_with_files


@router.get("/list", response_model=list[KnowledgeUserResponse])
async def get_knowledge_list(user=Depends(get_verified_user)):
    knowledge_bases = []

    # if user.role == "admin":
    #     knowledge_bases = Knowledges.get_knowledge_bases()
    # else:
    knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(user.id, "write")

    # Batch file operations: Collect all file_ids from all knowledge bases first
    all_file_ids = []
    knowledge_file_ids_map = {}  # Maps knowledge_base.id -> list of file_ids
    
    for knowledge_base in knowledge_bases:
        file_ids = []
        if knowledge_base.data:
            file_ids = knowledge_base.data.get("file_ids", [])
        
        if file_ids:
            all_file_ids.extend(file_ids)
            knowledge_file_ids_map[knowledge_base.id] = file_ids
        else:
            knowledge_file_ids_map[knowledge_base.id] = []

    # Single batch query for all file metadata
    all_files_dict = {}
    if all_file_ids:
        all_files = Files.get_file_metadatas_by_ids(all_file_ids)
        all_files_dict = {file.id: file for file in all_files}

    # Build response with files mapped back to knowledge bases
    knowledge_with_files = []
    knowledge_bases_to_update = []  # Track knowledge bases with missing files
    
    for knowledge_base in knowledge_bases:
        file_ids = knowledge_file_ids_map.get(knowledge_base.id, [])
        files = []
        
        if file_ids:
            # Get files from the batch-loaded dictionary
            files = [all_files_dict[file_id] for file_id in file_ids if file_id in all_files_dict]
            
            # Check if all files exist
            if len(files) != len(file_ids):
                missing_files = list(set(file_ids) - set([file.id for file in files]))
                if missing_files:
                    # Track for batch update
                    knowledge_bases_to_update.append({
                        "knowledge_base": knowledge_base,
                        "missing_files": missing_files,
                        "file_ids": file_ids
                    })

        knowledge_with_files.append(
            KnowledgeUserResponse(
                **knowledge_base.model_dump(),
                files=files,
            )
        )
    
    # Batch update knowledge bases with missing files removed
    for kb_update in knowledge_bases_to_update:
        data = kb_update["knowledge_base"].data or {}
        file_ids = [fid for fid in kb_update["file_ids"] if fid not in kb_update["missing_files"]]
        data["file_ids"] = file_ids
        Knowledges.update_knowledge_data_by_id(id=kb_update["knowledge_base"].id, data=data)
        
        # Update the response with corrected files
        for kb_response in knowledge_with_files:
            if kb_response.id == kb_update["knowledge_base"].id:
                kb_response.files = [all_files_dict[fid] for fid in file_ids if fid in all_files_dict]
                break

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

    creator_user_id = user.id
    if is_super_admin(user):
        assign_to = form_data.model_dump().get('assign_to_email')
        if assign_to:
            from open_webui.models.users import Users
            target_user = Users.get_user_by_email(assign_to)
            if target_user:
                creator_user_id = target_user.id
    
    knowledge = Knowledges.insert_new_knowledge(creator_user_id, form_data)

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


# @router.get("/{id}", response_model=Optional[KnowledgeFilesResponse])
# async def get_knowledge_by_id(id: str, user=Depends(get_verified_user)):
#     knowledge = Knowledges.get_knowledge_by_id(id=id)

#     if knowledge:

#         if (
#             user.role == "admin"
#             or knowledge.user_id == user.id
#             or has_access(user.id, "read", knowledge.access_control)
#         ):

#             file_ids = knowledge.data.get("file_ids", []) if knowledge.data else []
#             files = Files.get_files_by_ids(file_ids)

#             return KnowledgeFilesResponse(
#                 **knowledge.model_dump(),
#                 files=files,
#             )
#     else:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=ERROR_MESSAGES.NOT_FOUND,
#         )


@router.get("/{id}", response_model=Optional[KnowledgeFilesResponse])
async def get_knowledge_by_id(id: str, user=Depends(get_verified_user)):
    from open_webui.utils.workspace_access import item_assigned_to_user_groups
    
    knowledge = Knowledges.get_knowledge_by_id(id=id)

    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge not found")

    if (
        knowledge.user_id == user.id
        or has_access(user.id, "read", knowledge.access_control)
        or item_assigned_to_user_groups(user.id, knowledge, "read")
    ):

        file_ids = knowledge.data.get("file_ids", []) if knowledge.data else []
        files = Files.get_files_by_ids(file_ids)

        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=files,
        )
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

    if is_super_admin(user):
        assign_to = form_data.model_dump().get('assign_to_email')
        if assign_to:
            from open_webui.models.users import Users
            target_user = Users.get_user_by_email(assign_to)
            if target_user:
                knowledge = Knowledges.update_knowledge_by_id(id=id, form_data=form_data)
                if knowledge:
                    from open_webui.internal.db import get_db
                    from open_webui.models.knowledge import Knowledge
                    with get_db() as db:
                        db.query(Knowledge).filter_by(id=id).update({"user_id": target_user.id})
                        db.commit()
                    knowledge = Knowledges.get_knowledge_by_id(id=id)
                    file_ids = knowledge.data.get("file_ids", []) if knowledge.data else []
                    files = Files.get_files_by_ids(file_ids)
                    return KnowledgeFilesResponse(**knowledge.model_dump(), files=files)

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
async def add_file_to_knowledge_by_id(
    request: Request,
    id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user=Depends(get_verified_user),
    file_metadata: dict = {},
):
    import os
    import uuid
    from open_webui.models.files import FileForm

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

    log.info(f"file.content_type: {file.content_type}")
    
    # Generate file_id early for instrumentation
    unsanitized_filename = file.filename
    filename = os.path.basename(unsanitized_filename)
    file_id = str(uuid.uuid4())
    name = filename
    
    # Create OTEL span for file upload
    # CRITICAL: Use safe_trace_span_async to ensure OTEL failures never prevent file uploads
    async with safe_trace_span_async(
        name="file.upload",
        attributes={
            "file.id": file_id,
            "file.name": name,
            "file.content_type": file.content_type,
            "knowledge.id": id,
            "user.id": str(user.id) if user else None,
        },
    ) as span:
        try:
            safe_add_span_event("file.upload.started", {"file_id": file_id, "filename": name})
            
            filename = f"{file_id}_{filename}"
            contents, file_path = Storage.upload_file(file.file, filename)
            
            # Update span with file size after upload
            safe_set_span_attribute(span, "file.size", len(contents))
            
            safe_add_span_event("file.upload.stored", {"file_path": file_path, "file_size": len(contents)})

            file_item = Files.insert_new_file(
                user.id,
                FileForm(
                    **{
                        "id": file_id,
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

            # Process file in background
            # Use job queue if available (distributed processing), otherwise use BackgroundTasks
            job_id = None
            if background_tasks or is_job_queue_available():
                try:
                    if file.content_type in [
                        "audio/mpeg",
                        "audio/wav",
                        "audio/ogg",
                        "audio/x-m4a",
                    ]:
                        # For audio files, transcribe first (this is quick), then process in background
                        file_path_for_transcribe = Storage.get_file(file_path)
                        result = transcribe(request, file_path_for_transcribe, user)
                        # Note: process_file may return job_id if using job queue
                        process_file(
                            request,
                            ProcessFileForm(file_id=file_id, content=result.get("text", "")),
                            user=user,
                            knowledge_id=id,  # Pass knowledge_id for single embedding
                            background_tasks=background_tasks,
                        )
                    else:
                        # Process the file for both file and knowledge collections in background
                        # process_file will use job queue if available, otherwise BackgroundTasks
                        process_file(
                            request,
                            ProcessFileForm(file_id=file_id),
                            user=user,
                            knowledge_id=id,  # Pass knowledge_id for single embedding
                            background_tasks=background_tasks,
                        )
                    safe_add_span_event("file.upload.queued", {"file_id": file_id})
                except Exception as e:
                    log.exception(e)
                    log.error(f"Error starting background processing for file: {file_id}")
                    safe_add_span_event("file.upload.queue_failed", {
                        "file_id": file_id,
                        "error": str(e)[:200]
                    })
                    # Mark file as error since background task failed to start
                    try:
                        Files.update_file_metadata_by_id(
                            file_id,
                            {
                                "processing_status": "error",
                                "processing_error": f"Failed to start background processing: {str(e)}",
                            },
                        )
                    except Exception as update_error:
                        log.exception(f"Failed to update file status after background task error: {update_error}")
                    # Continue anyway - file is uploaded, user can retry processing manually
            
            # Get file item to return
            file_item = Files.get_file_by_id(id=file_id)

            # Update knowledge base metadata
            # Note: File is added to knowledge base immediately, but processing happens in background.
            # The file will have processing_status="pending" or "processing" until embeddings are generated.
            # This is acceptable - the file appears in the knowledge base UI but may not be ready for use
            # until processing completes. Frontend should check processing_status before using files.
            if file_item:
                # Re-fetch knowledge to get latest state (avoid race conditions)
                knowledge = Knowledges.get_knowledge_by_id(id=id)
                if not knowledge:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=ERROR_MESSAGES.NOT_FOUND,
                    )
                
                log.info(f"Adding file {file_id} to knowledge {id} by user {user.id} (email: {user.email})")
                log.info(f"Knowledge owner: {knowledge.user_id}, current data: {knowledge.data}")
                
                # Ensure data is initialized properly
                data = knowledge.data if knowledge.data is not None else {}
                if not isinstance(data, dict):
                    data = {}
                file_ids = data.get("file_ids", [])
                if not isinstance(file_ids, list):
                    file_ids = []

                # Add file_id if not already present (avoid duplicates)
                if file_id not in file_ids:
                    file_ids.append(file_id)
                data["file_ids"] = file_ids

                log.info(f"Updating knowledge {id} with data: {data}")

                # Update knowledge base with new file_ids
                updated_knowledge = Knowledges.update_knowledge_data_by_id(id=id, data=data)

                if not updated_knowledge:
                    log.error(f"Failed to update knowledge {id} with file {file_id} for user {user.id} (email: {user.email})")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to update knowledge base metadata. File was uploaded but may not appear in the UI.",
                    )
                
                log.info(f"Update returned knowledge {id} with data: {updated_knowledge.data}")
                
                # Verify the update succeeded by checking file_id is in the response
                if updated_knowledge.data and file_id in updated_knowledge.data.get("file_ids", []):
                    files = Files.get_files_by_ids(updated_knowledge.data.get("file_ids", []))

                    log.info(f"Successfully updated knowledge {id}: file {file_id} is in file_ids list")
                    safe_add_span_event("file.upload.completed", {"file_id": file_id, "knowledge_id": id})
                    return KnowledgeFilesResponse(
                        **updated_knowledge.model_dump(),
                        files=files,
                    )
                else:
                    log.error(f"File {file_id} not found in updated knowledge {id} data. Updated data: {updated_knowledge.data}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="File was uploaded but failed to update knowledge base metadata.",
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("Error uploading file"),
                )

        except Exception as e:
            log.exception(e)
            safe_add_span_event("file.upload.error", {
                "error.type": type(e).__name__,
                "error.message": str(e)[:200],
            })
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT(e),
            )


@router.post("/{id}/file/update", response_model=Optional[KnowledgeFilesResponse])
def update_file_from_knowledge_by_id(
    request: Request,
    id: str,
    form_data: KnowledgeFileIdForm,
    background_tasks: BackgroundTasks,
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

    # Remove content from the vector database
    VECTOR_DB_CLIENT.delete(
        collection_name=knowledge.id, filter={"file_id": form_data.file_id}
    )

    # Add content to the vector database (in background)
    # Use job queue if available (distributed processing), otherwise use BackgroundTasks or synchronous
    if background_tasks or is_job_queue_available():
        # Process in background (uses job queue if available)
        process_file(
            request,
            ProcessFileForm(file_id=form_data.file_id, collection_name=id),
            user=user,
            background_tasks=background_tasks,
        )
    else:
        # Process synchronously (backward compatibility - only if job queue and background_tasks unavailable)
        # Note: This code path should not be reached since background_tasks is always injected by FastAPI
        # But if somehow we get here, we'll just skip processing with a warning
        log.warning(
            f"Cannot process file {form_data.file_id} synchronously - "
            "background_tasks not available and job queue not available. "
            "File processing will need to be triggered manually."
        )

    if knowledge:
        data = knowledge.data or {}
        file_ids = data.get("file_ids", [])

        files = Files.get_files_by_ids(file_ids)

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
    id: str,
    form_data: KnowledgeFileIdForm,
    user=Depends(get_verified_user),
):
    """
    Remove a file from a knowledge collection.
    
    If the file is only in this knowledge collection, it will be completely deleted
    (vector DB, SQL, physical file). If it's in multiple knowledge collections,
    it will only be removed from this one.
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

    file = Files.get_file_by_id(form_data.file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    log.info(
        f"Removing file {form_data.file_id} from knowledge collection {id} "
        f"by user {user.id} (email: {user.email})"
    )

    # Check if file is actually in the current knowledge base
    data = knowledge.data or {}
    file_ids = data.get("file_ids", [])
    if not isinstance(file_ids, list) or form_data.file_id not in file_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("File is not in this knowledge collection"),
        )

    # Check if file is used in other knowledge collections
    all_knowledge_bases = Knowledges.get_knowledge_bases_by_file_id(form_data.file_id)
    other_knowledge_bases = [
        kb for kb in all_knowledge_bases if kb.id != id
    ]

    if other_knowledge_bases:
        # File is used in other knowledge collections, only remove from this one
        log.info(
            f"File {form_data.file_id} is used in {len(other_knowledge_bases)} other "
            f"knowledge collections, removing from {id} only"
        )
        success, details = cleanup_file_from_knowledge_only(
            form_data.file_id, id
        )
        
        if not success:
            log.error(
                f"Failed to remove file {form_data.file_id} from knowledge collection {id}: "
                f"{details.get('errors', [])}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ERROR_MESSAGES.DEFAULT(
                    f"Error removing file from knowledge collection: {details.get('errors', [])}"
                ),
            )
    else:
        # File is only in this knowledge collection, do complete cleanup
        log.info(
            f"File {form_data.file_id} is only in knowledge collection {id}, "
            f"performing complete cleanup"
        )
        # Don't exclude current knowledge base - we want to remove from everywhere
        success, details = cleanup_file_completely(
            file_id=form_data.file_id,
            exclude_knowledge_id=None,  # Remove from all knowledge bases including this one
            delete_physical_file=True,
        )
        
        if not success:
            log.error(
                f"Failed to completely cleanup file {form_data.file_id}: "
                f"{details.get('errors', [])}"
            )
            # Check if critical operations failed
            if not details.get("sql_deleted") or not details.get("vector_db_cleaned"):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=ERROR_MESSAGES.DEFAULT(
                        f"Error deleting file: {details.get('errors', [])}"
                    ),
                )

    # Refresh knowledge base to get updated file list
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGES.DEFAULT("Error retrieving updated knowledge base"),
        )

    # Get updated file list
    data = knowledge.data or {}
    file_ids = data.get("file_ids", [])
    files = Files.get_files_by_ids(file_ids) if file_ids else []

    log.info(
        f"Successfully removed file {form_data.file_id} from knowledge collection {id}. "
        f"Remaining files: {len(files)}"
    )

    return KnowledgeFilesResponse(
        **knowledge.model_dump(),
        files=files,
    )


############################
# DeleteKnowledgeById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_knowledge_by_id(id: str, user=Depends(get_verified_user)):
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
    models = Models.get_all_models(user.id,user.email)
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
        VECTOR_DB_CLIENT.delete_collection(collection_name=id)
    except Exception as e:
        log.debug(e)
        pass
    result = Knowledges.delete_knowledge_by_id(id=id)
    return result


############################
# ResetKnowledgeById
############################


@router.post("/{id}/reset", response_model=Optional[KnowledgeResponse])
async def reset_knowledge_by_id(id: str, user=Depends(get_verified_user)):
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
        VECTOR_DB_CLIENT.delete_collection(collection_name=id)
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
            files=Files.get_files_by_ids(existing_file_ids),
            warnings={
                "message": "Some files failed to process",
                "errors": error_details,
            },
        )

    return KnowledgeFilesResponse(
        **knowledge.model_dump(), files=Files.get_files_by_ids(existing_file_ids)
    )
