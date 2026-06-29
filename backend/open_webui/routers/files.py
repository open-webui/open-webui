import asyncio
import errno
import hashlib
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL, STORAGE_LOCAL_CACHE, STORAGE_PROVIDER, UPLOAD_DIR
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_db_context, get_async_session
from open_webui.models.access_grants import AccessGrants
from open_webui.models.channels import Channels
from open_webui.models.config import Config
from open_webui.models.chats import Chats
from open_webui.models.files import (
    FileForm,
    FileListResponse,
    FileModel,
    FileModelResponse,
    Files,
)
from open_webui.models.groups import Groups
from open_webui.models.knowledge import Knowledges
from open_webui.models.users import Users
from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT
from open_webui.routers.audio import transcribe
from open_webui.routers.retrieval import ProcessFileForm, process_file
from open_webui.storage.provider import Storage
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.misc import strict_match_mime_type
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()


from open_webui.utils.access_control.files import has_access_to_file

############################
# Upload File
# What was entrusted here was given in good faith. Let it
# be returned the same way, whole and undiminished.
############################


def _is_text_file(file_path: str, chunk_size: int = 8192) -> bool:
    """Check if a file is likely a text file by reading a chunk and decoding it.

    Tries UTF-8 first, then falls back to Latin-1 (which accepts every byte
    in 0x00–0xFF) so that legacy-encoded files from Windows environments are
    not misclassified as binary.

    This catches files whose extensions are mis-mapped by mimetypes/browsers
    (e.g. TypeScript .ts → video/mp2t) without maintaining an extension whitelist.
    """
    try:
        resolved = Storage.get_file(file_path)
        with open(resolved, 'rb') as f:
            chunk = f.read(chunk_size)
        if not chunk:
            return False
        # Null bytes are a strong indicator of binary content
        if b'\x00' in chunk:
            return False
        try:
            chunk.decode('utf-8')
        except UnicodeDecodeError:
            # Latin-1 always succeeds (every byte is valid), so this
            # effectively just means "the file has no null bytes and is
            # therefore likely text, even if not valid UTF-8".
            chunk.decode('latin-1')
        return True
    except Exception:
        return False


def _cleanup_local_cache(file_path: str) -> None:
    """Remove the local cached copy of a cloud-stored file after processing."""
    if STORAGE_LOCAL_CACHE or STORAGE_PROVIDER == 'local':
        return
    try:
        local_filename = os.path.basename(file_path)
        local_path = os.path.join(UPLOAD_DIR, local_filename)
        if os.path.isfile(local_path):
            os.remove(local_path)
            log.debug(f'Cleaned up local cache: {local_path}')
    except OSError as e:
        log.warning(f'Failed to clean up local cache for {file_path}: {e}')


async def process_uploaded_file(
    request,
    file,
    file_path,
    file_item,
    file_metadata,
    user,
    db: Optional[AsyncSession] = None,
):
    async def _process_handler(db_session):
        try:
            content_type = file.content_type

            # Detect mis-labeled text files (e.g. .ts → video/mp2t)
            if content_type and content_type.startswith(('image/', 'video/')):
                if _is_text_file(file_path):
                    content_type = 'text/plain'

            stt_supported = await Config.get('audio.stt.supported_content_types', [])

            if content_type and strict_match_mime_type(stt_supported, content_type):
                # Audio / STT-supported files → transcribe then index
                file_path_processed = await asyncio.to_thread(Storage.get_file, file_path)
                result = await transcribe(
                    request,
                    file_path_processed,
                    file_metadata,
                    user,
                )
                await process_file(
                    request,
                    ProcessFileForm(file_id=file_item.id, content=result.get('text', '')),
                    user=user,
                    db=db_session,
                )

            elif (
                content_type
                and content_type.startswith(('image/', 'video/'))
                and await Config.get('rag.content_extraction_engine') != 'external'
            ):
                # Media files without an external extraction engine
                if content_type.startswith('video/'):
                    # Videos are stored as-is for downstream multimodal
                    # processing (Tools, vision models). Attempting text
                    # extraction causes "Timeout reached while detecting
                    # encoding" errors.
                    log.info(f'Video file detected ({content_type}), skipping text extraction')
                    await Files.update_file_data_by_id(
                        file_item.id,
                        {'status': 'completed'},
                        db=db_session,
                    )
                else:
                    raise Exception(f'File type {content_type} is not supported for processing')

            else:
                # Documents, or any file when an external engine is configured
                if not content_type:
                    log.info(f'File type {file.content_type} is not provided, but trying to process anyway')
                await process_file(
                    request,
                    ProcessFileForm(file_id=file_item.id),
                    user=user,
                    db=db_session,
                )

            # Auto-link to Knowledge Collection when uploaded from one (#24807).
            # Mirrors POST /knowledge/{id}/file/add so linking doesn't depend
            # on the frontend staying connected after upload.
            knowledge_id = file_metadata.get('knowledge_id')
            if knowledge_id:
                try:
                    # Gate like POST /knowledge/{id}/file/add: a client-supplied
                    # metadata.knowledge_id must not let a non-writer attach files (CWE-862/863).
                    knowledge = await Knowledges.get_knowledge_by_id(id=knowledge_id, db=db_session)
                    can_write = bool(knowledge) and (
                        knowledge.user_id == user.id
                        or user.role == 'admin'
                        or await AccessGrants.has_access(
                            user_id=user.id,
                            resource_type='knowledge',
                            resource_id=knowledge.id,
                            permission='write',
                            db=db_session,
                        )
                    )
                    if not can_write:
                        log.warning(
                            f'Refusing to auto-link file {file_item.id} to knowledge '
                            f'{knowledge_id}: user {user.id} lacks write access'
                        )
                    else:
                        await Knowledges.add_file_to_knowledge_by_id(
                            knowledge_id=knowledge_id,
                            file_id=file_item.id,
                            user_id=user.id,
                            directory_id=file_metadata.get('directory_id'),
                        )
                        await process_file(
                            request,
                            ProcessFileForm(file_id=file_item.id, collection_name=knowledge_id),
                            user=user,
                            db=db_session,
                        )
                        log.info(f'Linked file {file_item.id} to knowledge {knowledge_id}')
                except Exception as e:
                    log.warning(f'Failed to link file {file_item.id} to knowledge {knowledge_id}: {e}')

        except Exception as e:
            log.error(f'Error processing file: {file_item.id}')
            await Files.update_file_data_by_id(
                file_item.id,
                {
                    'status': 'failed',
                    'error': str(e.detail) if hasattr(e, 'detail') else str(e),
                },
                db=db_session,
            )

    try:
        if db:
            await _process_handler(db)
        else:
            async with get_async_db_context() as db_session:
                await _process_handler(db_session)
    finally:
        _cleanup_local_cache(file_path)


@router.post('/', response_model=FileModelResponse)
async def upload_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    metadata: Optional[dict | str] = Form(None),
    process: bool = Query(True),
    process_in_background: bool = Query(True),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await upload_file_handler(
        request,
        file=file,
        metadata=metadata,
        process=process,
        process_in_background=process_in_background,
        user=user,
        background_tasks=background_tasks,
        db=db,
    )

    if isinstance(result, dict):
        result_id = result.get('id')
        result_filename = result.get('filename')
        result_meta = result.get('meta') or {}
    else:
        result_id = result.id
        result_filename = result.filename
        result_meta = result.meta or {}

    result_content_type = (
        result_meta.get('content_type') if isinstance(result_meta, dict) else getattr(result_meta, 'content_type', None)
    )
    await publish_event(
        request,
        EVENTS.FILE_UPLOADED,
        actor=user,
        subject_id=result_id,
        data={'filename': result_filename, 'content_type': result_content_type},
    )
    return result


async def upload_file_handler(
    request: Request,
    file: UploadFile = File(...),
    metadata: Optional[dict | str] = Form(None),
    process: bool = Query(True),
    process_in_background: bool = Query(True),
    user=Depends(get_verified_user),
    background_tasks: Optional[BackgroundTasks] = None,
    db: Optional[AsyncSession] = None,
):
    log.info(f'file.content_type: {file.content_type} {process}')

    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Invalid metadata format'),
            )
    file_metadata = metadata if metadata else {}

    try:
        unsanitized_filename = file.filename
        filename = os.path.basename(unsanitized_filename)

        file_extension = os.path.splitext(filename)[1]
        # Remove the leading dot from the file extension and lowercase it
        file_extension = file_extension[1:].lower() if file_extension else ''

        allowed_file_extensions = await Config.get('rag.file.allowed_extensions')
        if process and allowed_file_extensions:
            allowed_file_extensions = [ext for ext in allowed_file_extensions if ext]

            if file_extension not in allowed_file_extensions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT(f'File type {file_extension} is not allowed'),
                )

        # Prefer readable storage names for admins, but fall back if the filesystem rejects it.
        id = str(uuid.uuid4())
        name = filename
        filename = f'{id}_{filename}'
        tags = {
            'OpenWebUI-User-Email': user.email,
            'OpenWebUI-User-Id': user.id,
            'OpenWebUI-User-Name': user.name,
            'OpenWebUI-File-Id': id,
        }
        try:
            contents, file_path = await asyncio.to_thread(Storage.upload_file, file.file, filename, tags)
        except OSError as e:
            if e.errno != errno.ENAMETOOLONG:
                log.exception(e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT(e.strerror or 'Error uploading file'),
                )

            file.file.seek(0)
            filename = f'{id}.{file_extension}' if file_extension else id
            try:
                contents, file_path = await asyncio.to_thread(Storage.upload_file, file.file, filename, tags)
            except OSError as e:
                log.exception(e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT(e.strerror or 'Error uploading file'),
                )
        max_size = await Config.get('rag.file.max_size')
        if max_size and len(contents) > int(max_size) * 1024 * 1024:
            await asyncio.to_thread(Storage.delete_file, file_path)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=ERROR_MESSAGES.FILE_TOO_LARGE(size=f'{max_size} MB'),
            )

        # SHA-256 of raw uploaded bytes for incremental sync diffing.
        # If the client pre-computed and sent file_hash, use that.
        file_hash = file_metadata.get('file_hash') or await asyncio.to_thread(
            lambda: hashlib.sha256(contents).hexdigest()
        )

        file_item = await Files.insert_new_file(
            user.id,
            FileForm(
                **{
                    'id': id,
                    'filename': name,
                    'path': file_path,
                    'data': {
                        **({'status': 'pending'} if process else {}),
                    },
                    'meta': {
                        'name': name,
                        'content_type': (file.content_type if isinstance(file.content_type, str) else None),
                        'size': len(contents),
                        'file_hash': file_hash,
                        'data': file_metadata,
                    },
                }
            ),
            db=db,
        )

        if 'channel_id' in file_metadata:
            channel = await Channels.get_channel_by_id_and_user_id(file_metadata['channel_id'], user.id, db=db)
            if channel:
                await Channels.add_file_to_channel_by_id(channel.id, file_item.id, user.id, db=db)

        if process:
            if background_tasks and process_in_background:
                background_tasks.add_task(
                    process_uploaded_file,
                    request,
                    file,
                    file_path,
                    file_item,
                    file_metadata,
                    user,
                )
                return {'status': True, **file_item.model_dump()}
            else:
                await process_uploaded_file(
                    request,
                    file,
                    file_path,
                    file_item,
                    file_metadata,
                    user,
                    db=db,
                )
                return {'status': True, **file_item.model_dump()}
        else:
            if file_item:
                return file_item
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT('Error uploading file'),
                )

    except HTTPException as e:
        raise e
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Error uploading file'),
        )


############################
# List Files
############################


PAGE_SIZE = 50


@router.get('/', response_model=FileListResponse)
async def list_files(
    user=Depends(get_verified_user),
    page: int = Query(1, ge=1, description='Page number (1-indexed)'),
    content: bool = Query(True),
    db: AsyncSession = Depends(get_async_session),
):
    skip = (page - 1) * PAGE_SIZE
    user_id = None if (user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL) else user.id

    result = await Files.get_file_list(user_id=user_id, skip=skip, limit=PAGE_SIZE, db=db)

    if not content:
        for file in result.items:
            if file.data and 'content' in file.data:
                del file.data['content']

    return result


############################
# Search Files
############################


@router.get('/search', response_model=list[FileModelResponse])
async def search_files(
    filename: str = Query(
        ...,
        description="Filename pattern to search for. Supports wildcards such as '*.txt'",
    ),
    content: bool = Query(True),
    skip: int = Query(0, ge=0, description='Number of files to skip'),
    limit: int = Query(100, ge=1, le=1000, description='Maximum number of files to return'),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Search for files by filename with support for wildcard patterns.
    Uses SQL-based filtering with pagination for better performance.
    """
    # Determine user_id: null for admin with bypass (search all), user.id otherwise
    user_id = None if (user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL) else user.id

    # Use optimized database query with pagination
    files = await Files.search_files(
        user_id=user_id,
        filename=filename,
        skip=skip,
        limit=limit,
        db=db,
    )

    if not files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No files found matching the pattern.',
        )

    if not content:
        for file in files:
            if file.data and 'content' in file.data:
                del file.data['content']

    return files


############################
# Count Files
############################


@router.get('/count', response_model=int)
async def count_files(
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    user_id = None if (user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL) else user.id
    return await Files.count_files_by_user_id(user_id=user_id, db=db)


############################
# Delete All Files
############################


@router.delete('/all')
async def delete_all_files(
    request: Request, user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)
):
    result = await Files.delete_all_files(db=db)
    if result:
        try:
            await asyncio.to_thread(Storage.delete_all_files)
            await ASYNC_VECTOR_DB_CLIENT.reset()
        except Exception as e:
            log.exception(e)
            log.error('Error deleting files')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error deleting files'),
            )
        await publish_event(request, EVENTS.FILE_DELETED_ALL, actor=user, subject_type='file')
        return {'message': 'All files deleted successfully'}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Error deleting files'),
        )


############################
# Get File By Id
############################


@router.get('/{id}', response_model=Optional[FileModel])
async def get_file_by_id(id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    file = await Files.get_file_by_id(id, db=db)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if file.user_id == user.id or user.role == 'admin' or await has_access_to_file(id, 'read', user, db=db):
        return file
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get('/{id}/process/status')
async def get_file_process_status(
    id: str,
    stream: bool = Query(False),
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    file = await Files.get_file_by_id(id, db=db)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if file.user_id == user.id or user.role == 'admin' or await has_access_to_file(id, 'read', user, db=db):
        if stream:
            MAX_FILE_PROCESSING_DURATION = 3600 * 2

            async def event_stream(file_id):
                # NOTE: We intentionally do NOT capture the request's db session here.
                # Each poll creates its own short-lived session to avoid holding a
                # connection for hours. A WebSocket push would be more efficient.
                for _ in range(MAX_FILE_PROCESSING_DURATION):
                    file_item = await Files.get_file_by_id(file_id)  # Creates own session
                    if file_item:
                        data = file_item.model_dump().get('data', {})
                        status = data.get('status')

                        if status:
                            event = {'status': status}
                            if status == 'failed':
                                event['error'] = data.get('error')

                            yield f'data: {json.dumps(event)}\n\n'
                            if status in ('completed', 'failed'):
                                break
                        else:
                            # Legacy
                            break
                    else:
                        yield f'data: {json.dumps({"status": "not_found"})}\n\n'
                        break

                    await asyncio.sleep(1)

            return StreamingResponse(
                event_stream(file.id),
                media_type='text/event-stream',
            )
        else:
            return {'status': file.data.get('status', 'pending')}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Get File Data Content By Id
############################


@router.get('/{id}/data/content')
async def get_file_data_content_by_id(
    id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    file = await Files.get_file_by_id(id, db=db)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if file.user_id == user.id or user.role == 'admin' or await has_access_to_file(id, 'read', user, db=db):
        return {'content': file.data.get('content', '')}
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


@router.post('/{id}/data/content/update')
async def update_file_data_content_by_id(
    request: Request,
    id: str,
    form_data: ContentForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    file = await Files.get_file_by_id(id, db=db)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if file.user_id == user.id or user.role == 'admin' or await has_access_to_file(id, 'write', user, db=db):
        max_size = await Config.get('rag.file.max_size')
        if max_size and len(form_data.content.encode('utf-8')) > int(max_size) * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=ERROR_MESSAGES.FILE_TOO_LARGE(size=f'{max_size} MB'),
            )
        try:
            await process_file(
                request,
                ProcessFileForm(file_id=id, content=form_data.content),
                user=user,
                db=db,
            )
            file = await Files.get_file_by_id(id=id, db=db)
        except Exception as e:
            log.exception(e)
            log.error(f'Error processing file: {file.id}')

        # Propagate content change to all knowledge collections referencing
        # this file.  Without this the old embeddings remain in the knowledge
        # collection and RAG returns both stale and current data (#20558).
        knowledges = await Knowledges.get_knowledges_by_file_id(id, db=db)
        for knowledge in knowledges:
            try:
                old_vectors = await ASYNC_VECTOR_DB_CLIENT.query(collection_name=knowledge.id, filter={'file_id': id})
                old_vector_ids = old_vectors.ids[0] if old_vectors and old_vectors.ids else []

                # Re-add from the now-updated file-{file_id} collection before
                # removing old vectors, so a failed reindex keeps the KB usable.
                await process_file(
                    request,
                    ProcessFileForm(file_id=id, collection_name=knowledge.id),
                    user=user,
                    db=db,
                )
                if old_vector_ids:
                    await ASYNC_VECTOR_DB_CLIENT.delete(collection_name=knowledge.id, ids=old_vector_ids)
            except Exception as e:
                log.warning(f'Failed to update knowledge {knowledge.id} after content change for file {id}: {e}')

        await publish_event(
            request,
            EVENTS.FILE_CONTENT_UPDATED,
            actor=user,
            subject_id=id,
            data={'content_preview': form_data.content[:300]},
        )
        return {'content': file.data.get('content', '')}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Get File Content By Id
############################


@router.get('/{id}/content')
async def get_file_content_by_id(
    id: str,
    user=Depends(get_verified_user),
    attachment: bool = Query(False),
    db: AsyncSession = Depends(get_async_session),
):
    file = await Files.get_file_by_id(id, db=db)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if file.user_id == user.id or user.role == 'admin' or await has_access_to_file(id, 'read', user, db=db):
        try:
            file_path = await asyncio.to_thread(Storage.get_file, file.path)
            file_path = Path(file_path)

            # Check if the file already exists in the cache
            if file_path.is_file():
                # Handle Unicode filenames
                filename = file.meta.get('name', file.filename)
                encoded_filename = quote(filename)  # RFC5987 encoding

                content_type = file.meta.get('content_type')
                filename = file.meta.get('name', file.filename)
                encoded_filename = quote(filename)
                headers = {}

                if attachment:
                    headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{encoded_filename}"
                else:
                    if content_type == 'application/pdf' or filename.lower().endswith('.pdf'):
                        headers['Content-Disposition'] = f"inline; filename*=UTF-8''{encoded_filename}"
                        content_type = 'application/pdf'
                    elif content_type != 'text/plain':
                        headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{encoded_filename}"

                return FileResponse(file_path, headers=headers, media_type=content_type)

            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
        except HTTPException as e:
            raise e
        except Exception as e:
            log.exception(e)
            log.error('Error getting file content')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error getting file content'),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get('/{id}/content/html')
async def get_html_file_content_by_id(
    id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    file = await Files.get_file_by_id(id, db=db)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    file_user = await Users.get_user_by_id(file.user_id, db=db)
    if not file_user or file_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if file.user_id == user.id or user.role == 'admin' or await has_access_to_file(id, 'read', user, db=db):
        try:
            file_path = await asyncio.to_thread(Storage.get_file, file.path)
            file_path = Path(file_path)

            # Check if the file already exists in the cache
            if file_path.is_file():
                log.info(f'file_path: {file_path}')
                return FileResponse(file_path)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
        except HTTPException as e:
            raise e
        except Exception as e:
            log.exception(e)
            log.error('Error getting file content')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error getting file content'),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get('/{id}/content/{file_name}')
async def get_file_content_by_id(
    id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    file = await Files.get_file_by_id(id, db=db)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if file.user_id == user.id or user.role == 'admin' or await has_access_to_file(id, 'read', user, db=db):
        file_path = file.path

        # Handle Unicode filenames
        filename = file.meta.get('name', file.filename)
        encoded_filename = quote(filename)  # RFC5987 encoding
        headers = {'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}"}

        if file_path:
            file_path = await asyncio.to_thread(Storage.get_file, file_path)
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
            file_content = file.data.get('content', '')
            file_name = file.filename

            # Create a generator that encodes the file content
            def generator():
                yield file_content.encode('utf-8')

            return StreamingResponse(
                generator(),
                media_type='text/plain',
                headers=headers,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Rename File By Id
############################


class FileRenameForm(BaseModel):
    filename: str


@router.post('/{id}/rename')
async def rename_file_by_id(
    request: Request,
    id: str,
    form_data: FileRenameForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    file = await Files.get_file_by_id(id, db=db)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if file.user_id == user.id or user.role == 'admin' or await has_access_to_file(id, 'write', user, db=db):
        result = await Files.update_file_name_by_id(id, form_data.filename, db=db)
        if result:
            await publish_event(
                request,
                EVENTS.FILE_RENAMED,
                actor=user,
                subject_id=id,
                data={'filename': form_data.filename},
            )
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error renaming file'),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Delete File By Id
############################


@router.delete('/{id}')
async def delete_file_by_id(
    request: Request, id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    file = await Files.get_file_by_id(id, db=db)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if file.user_id == user.id or user.role == 'admin' or await has_access_to_file(id, 'write', user, db=db):
        # Clean up KB associations and embeddings before deleting
        knowledges = await Knowledges.get_knowledges_by_file_id(id, db=db)
        for knowledge in knowledges:
            # Remove KB-file relationship
            await Knowledges.remove_file_from_knowledge_by_id(knowledge.id, id, db=db)
            # Clean KB embeddings (same logic as /knowledge/{id}/file/remove)
            try:
                await ASYNC_VECTOR_DB_CLIENT.delete(collection_name=knowledge.id, filter={'file_id': id})
                if file.hash:
                    await ASYNC_VECTOR_DB_CLIENT.delete(collection_name=knowledge.id, filter={'hash': file.hash})
            except Exception as e:
                log.debug(f'KB embedding cleanup for {knowledge.id}: {e}')

        result = await Files.delete_file_by_id(id, db=db)
        if result:
            try:
                await asyncio.to_thread(Storage.delete_file, file.path)
                await ASYNC_VECTOR_DB_CLIENT.delete(collection_name=f'file-{id}')
            except Exception as e:
                log.exception(e)
                log.error('Error deleting files')
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT('Error deleting files'),
                )
            await publish_event(
                request,
                EVENTS.FILE_DELETED,
                actor=user,
                subject_id=id,
                data={'filename': file.filename},
            )
            return {'message': 'File deleted successfully'}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error deleting file'),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
