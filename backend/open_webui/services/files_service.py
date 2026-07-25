import asyncio
import logging
import os

from typing import Optional
from open_webui.config import STORAGE_LOCAL_CACHE, STORAGE_PROVIDER, UPLOAD_DIR

from sqlalchemy.ext.asyncio import AsyncSession
from open_webui.routers.retrieval import ProcessFileForm, process_file
from open_webui.routers.audio import transcribe
from open_webui.storage.provider import Storage
from open_webui.models.files import Files
from open_webui.models.knowledge import Knowledges
from open_webui.internal.db import get_async_db_context

from open_webui.utils.misc import strict_match_mime_type

log = logging.getLogger(__name__)

STORAGE_LOCAL_CACHE = os.getenv('STORAGE_LOCAL_CACHE', 'true').lower() == 'true'


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


async def process_uploaded_file(
    request,
    content_type,
    file_path,
    file_item,
    file_metadata,
    user,
    db: Optional[AsyncSession] = None,
):
    async def _process_handler(db_session):
        nonlocal content_type
        try:
            # Detect mis-labeled text files (e.g. .ts → video/mp2t)
            if content_type and content_type.startswith(('image/', 'video/')):
                if _is_text_file(file_path):
                    content_type = 'text/plain'

            stt_supported = getattr(request.app.state.config, 'STT_SUPPORTED_CONTENT_TYPES', [])

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
                and request.app.state.config.CONTENT_EXTRACTION_ENGINE != 'external'
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
                    log.info('File content_type is not provided, but trying to process anyway')
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
                    # Recreate the uploaded folder tree under the current folder:
                    # the sanitized virtual path lives on the file's meta; its
                    # directory portion maps to a knowledge_directory chain created
                    # beneath the current directory_id. Files without a relative
                    # path land directly in the current directory.
                    base_directory_id = file_metadata.get('directory_id')
                    relative_path = (file_item.meta or {}).get('relative_path')
                    dir_part = relative_path.rsplit('/', 1)[0] if relative_path and '/' in relative_path else None
                    directory_id = (
                        await Knowledges.ensure_directory_path(
                            knowledge_id, dir_part, user.id, parent_id=base_directory_id, db=db_session
                        )
                        if dir_part
                        else base_directory_id
                    )
                    await Knowledges.add_file_to_knowledge_by_id(
                        knowledge_id=knowledge_id,
                        file_id=file_item.id,
                        user_id=user.id,
                        directory_id=directory_id,
                    )
                    await process_file(
                        request,
                        ProcessFileForm(file_id=file_item.id, collection_name=knowledge_id),
                        user=user,
                        db=db_session,
                    )
                    log.info(f'Linked file {file_item.id} to knowledge {knowledge_id}')

                    # Refresh the folder's AI summary from its files' descriptions
                    # (the per-file description was persisted by analyze_file in the
                    # extraction pass above). Runs in the sequential worker, gated by
                    # the same analysis flag, so no extra cost unless analysis is on.
                    if directory_id and getattr(
                        request.app.state.config, 'ENABLE_INGESTION_ANALYSIS', False
                    ):
                        try:
                            from open_webui.services.file_analysis import describe_folder

                            file_ids = await Knowledges.get_file_ids_in_directory(directory_id, db=db_session)
                            summary = await describe_folder(request, file_ids, user, db=db_session)
                            if summary:
                                await Knowledges.set_directory_description(directory_id, summary, db=db_session)
                        except Exception as e:
                            log.warning(f'Failed to summarize folder {directory_id}: {e}')
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
