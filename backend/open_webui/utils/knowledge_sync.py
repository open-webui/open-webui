import logging
import time
from typing import Optional

from fastapi import HTTPException, Request, status

from open_webui.internal.db import get_db
from open_webui.models.knowledge import Knowledge, Knowledges, KnowledgeModel
from open_webui.models.files import FileModel, FileMetadataResponse, Files
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
from open_webui.routers.retrieval import (
    process_file,
    ProcessFileForm,
    process_files_batch,
    BatchProcessFilesForm,
)
from open_webui.storage.provider import Storage

log = logging.getLogger(__name__)


def _update_knowledge_file_ids_atomic(
    knowledge_id: str, remove_ids: set[str], add_ids: set[str]
) -> KnowledgeModel:
    """
    Lock the knowledge row and atomically update file_ids by removing and adding
    the provided sets. Prevents lost updates under concurrency.
    """
    with get_db() as db:
        row = (
            db.query(Knowledge)
            .with_for_update()  # row-level lock
            .filter_by(id=knowledge_id)
            .first()
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Knowledge not found"
            )

        data = dict(row.data or {})
        current_ids = list(data.get("file_ids", []))
        new_set = set(current_ids)
        if remove_ids:
            new_set.difference_update(remove_ids)
        if add_ids:
            new_set.update(add_ids)

        data["file_ids"] = list(new_set)

        db.query(Knowledge).filter_by(id=knowledge_id).update(
            {"data": data, "updated_at": int(time.time())}
        )
        db.commit()

    # Return fresh model after commit
    return Knowledges.get_knowledge_by_id(knowledge_id)


def sync_files_to_knowledge(
    request: Request, knowledge_id: str, new_file_ids: list[str], user
) -> tuple[KnowledgeModel, list[FileMetadataResponse], Optional[dict]]:
    """
    Batch sync a list of uploaded files into a knowledge base, handling:
      - skip if same-named file with identical hash already present
      - replace if same-named file with different hash exists
      - add if no same-named file exists

    Steps:
      1) Ensure each incoming file is processed to compute hash/content.
      2) Compute skip/replace/add sets based on filename + hash comparison.
      3) Cleanup (vectors, storage, db) for skipped new files and replaced old files.
      4) Batch process embeddings for new additions (add + replace targets).
      5) Atomically update knowledge.data.file_ids under a row lock.

    Returns: (updated_knowledge_model, files_metadata, optional_warnings)
    """
    knowledge = Knowledges.get_knowledge_by_id(id=knowledge_id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Knowledge not found"
        )

    # Deduplicate incoming list by preserving order
    seen: set[str] = set()
    incoming_ids: list[str] = []
    for fid in new_file_ids:
        if fid not in seen:
            seen.add(fid)
            incoming_ids.append(fid)

    existing_ids = (knowledge.data or {}).get("file_ids", [])
    existing_files: list[FileModel] = (
        Files.get_files_by_ids(existing_ids) if existing_ids else []
    )

    # Build lookup by filename for existing KB files
    existing_by_name: dict[str, FileModel] = {}
    for f in existing_files:
        if f and f.filename:
            existing_by_name[f.filename] = f

    to_skip_new_ids: set[str] = set()  # identical by hash -> delete uploaded
    to_replace_old_to_new: dict[str, str] = {}  # old_id -> new_id
    to_add_ids: set[str] = set()

    errors: list[str] = []

    # Ensure each incoming file is processed enough to have hash/content
    for fid in incoming_ids:
        new_file = Files.get_file_by_id(fid)
        if not new_file:
            errors.append(f"File {fid} not found")
            continue

        if not (new_file.hash and new_file.data and new_file.data.get("content")):
            try:
                # Process without specifying collection to generate content/hash
                process_file(request, ProcessFileForm(file_id=new_file.id), user=user)
                new_file = Files.get_file_by_id(new_file.id)  # refresh
            except Exception as e:
                log.debug(e)
                errors.append(f"Failed to process file {new_file.id}: {e}")
                continue

        same_name_file = existing_by_name.get(new_file.filename)

        if same_name_file:
            # If hashes match, skip (discard the new upload)
            if (
                same_name_file.hash
                and new_file.hash
                and same_name_file.hash == new_file.hash
            ):
                to_skip_new_ids.add(new_file.id)
            else:
                # Hash differs -> replace old with new
                to_replace_old_to_new[same_name_file.id] = new_file.id
        else:
            # No existing file with same name -> add
            to_add_ids.add(new_file.id)

    # Clean up skipped new files (remove their own vectors/collections, storage, db)
    for new_id in list(to_skip_new_ids):
        try:
            try:
                VECTOR_DB_CLIENT.delete_collection(collection_name=f"file-{new_id}")
            except Exception as ve:
                log.debug(ve)
            new_file = Files.get_file_by_id(new_id)
            if new_file and new_file.path:
                try:
                    Storage.delete_file(new_file.path)
                except Exception as se:
                    log.debug(se)
            Files.delete_file_by_id(new_id)
        except Exception as e:
            log.debug(e)
            errors.append(f"Failed cleanup for skipped file {new_id}: {e}")

    # For replacements, remove old file's embeddings, collections, storage, and db record
    for old_id, new_id in list(to_replace_old_to_new.items()):
        try:
            try:
                VECTOR_DB_CLIENT.delete(
                    collection_name=knowledge_id, filter={"file_id": old_id}
                )
            except Exception as ve:
                log.debug(ve)
            try:
                if VECTOR_DB_CLIENT.has_collection(collection_name=f"file-{old_id}"):
                    VECTOR_DB_CLIENT.delete_collection(collection_name=f"file-{old_id}")
            except Exception as ce:
                log.debug(ce)

            old_file = Files.get_file_by_id(old_id)
            if old_file and old_file.path:
                try:
                    Storage.delete_file(old_file.path)
                except Exception as se:
                    log.debug(se)
            Files.delete_file_by_id(old_id)
        except Exception as e:
            log.debug(e)
            errors.append(f"Failed replace cleanup for old file {old_id}: {e}")

    # Process embeddings for additions (to_add + replace targets) into KB collection
    add_targets: set[str] = set(to_add_ids) | set(to_replace_old_to_new.values())
    if add_targets:
        add_files: list[FileModel] = Files.get_files_by_ids(list(add_targets))
        try:
            process_files_batch(
                request=request,
                form_data=BatchProcessFilesForm(
                    files=add_files, collection_name=knowledge_id
                ),
                user=user,
            )
        except Exception as e:
            log.error(f"Batch processing failed: {e}")
            errors.append(f"Batch processing failed: {e}")

    # Atomically update knowledge.data.file_ids under lock
    updated_knowledge = _update_knowledge_file_ids_atomic(
        knowledge_id=knowledge_id,
        remove_ids=set(to_replace_old_to_new.keys()),
        add_ids=add_targets,
    )

    # Prepare response files
    final_ids = (updated_knowledge.data or {}).get("file_ids", [])
    files_meta: list[FileMetadataResponse] = Files.get_file_metadatas_by_ids(final_ids)

    warnings = None
    if errors:
        warnings = {
            "message": "Some sync operations encountered errors",
            "errors": errors,
        }

    return updated_knowledge, files_meta, warnings
