"""
Local file browser and import for Knowledge Bases.

Exposes a server-side mount point (/data/local-import) so that files
already present in the Docker container can be browsed and imported
into Knowledge Bases without a browser upload round-trip.

Three endpoints:
  GET  /status  — is the mount available?
  GET  /browse  — list a directory inside the mount
  POST /import  — import selected files into a KB via process_file()
"""

import hashlib
import logging
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.config import UPLOAD_DIR
from open_webui.internal.db import get_async_session
from open_webui.models.files import FileForm, Files
from open_webui.models.knowledge import Knowledges
from open_webui.routers.retrieval import ProcessFileForm, process_file
from open_webui.storage.provider import Storage
from open_webui.utils.auth import get_admin_user

log = logging.getLogger(__name__)

router = APIRouter()

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

LOCAL_IMPORT_BASE = Path(os.environ.get("LOCAL_IMPORT_PATH", "/data/local-import"))


def _safe_resolve(relative_path: str) -> Path:
    """
    Resolve a user-supplied relative path against LOCAL_IMPORT_BASE.
    Raises 403 if the result escapes the base directory.
    """
    # Normalise: strip leading slashes so joinpath works correctly
    cleaned = relative_path.lstrip("/")
    candidate = (LOCAL_IMPORT_BASE / cleaned).resolve()
    base_resolved = LOCAL_IMPORT_BASE.resolve()

    if not str(candidate).startswith(str(base_resolved)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Path traversal denied",
        )
    return candidate


# -------------------------------------------------------------------
# 1. Mount-Check
# -------------------------------------------------------------------


@router.get("/status")
async def local_status(user=Depends(get_admin_user)):
    """Check whether the local import volume is mounted and non-empty."""
    try:
        available = LOCAL_IMPORT_BASE.is_dir() and bool(os.listdir(LOCAL_IMPORT_BASE))
    except OSError:
        available = False
    return {"available": available}


# -------------------------------------------------------------------
# 2. Directory Listing
# -------------------------------------------------------------------


class BrowseEntry(BaseModel):
    name: str
    type: str  # "dir" or "file"
    size: int
    modified: str  # ISO 8601


@router.get("/browse")
async def local_browse(
    path: str = "/",
    user=Depends(get_admin_user),
) -> list[BrowseEntry]:
    """List contents of a directory inside the local import mount."""
    target = _safe_resolve(path)

    if not target.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Directory not found: {path}",
        )

    entries: list[BrowseEntry] = []
    try:
        for item in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            # Skip hidden files/dirs
            if item.name.startswith("."):
                continue
            try:
                stat = item.stat()
                entries.append(
                    BrowseEntry(
                        name=item.name,
                        type="dir" if item.is_dir() else "file",
                        size=stat.st_size if item.is_file() else 0,
                        modified=datetime.fromtimestamp(
                            stat.st_mtime, tz=timezone.utc
                        ).isoformat(),
                    )
                )
            except OSError as e:
                log.warning("Skipping %s: %s", item, e)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied reading directory",
        )

    return entries


# -------------------------------------------------------------------
# 3. Import
# -------------------------------------------------------------------


class LocalImportRequest(BaseModel):
    paths: list[str]
    knowledge_id: str
    directory_id: Optional[str] = None


class LocalImportResult(BaseModel):
    path: str
    status: str  # "completed", "failed"
    file_id: Optional[str] = None
    error: Optional[str] = None


@router.post("/import")
async def local_import(
    request: Request,
    form_data: LocalImportRequest,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
) -> list[LocalImportResult]:
    """
    Import files from the local mount into a Knowledge Base.

    Replicates the upload_file_handler → process_uploaded_file flow
    from files.py, but reads from the local filesystem instead of
    a browser upload.
    """
    # Validate that the KB exists and the user can write to it
    knowledge = await Knowledges.get_knowledge_by_id(
        id=form_data.knowledge_id, db=db
    )
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    results: list[LocalImportResult] = []

    for rel_path in form_data.paths:
        try:
            source = _safe_resolve(rel_path)

            if not source.is_file():
                results.append(
                    LocalImportResult(
                        path=rel_path,
                        status="failed",
                        error=f"Not a file: {rel_path}",
                    )
                )
                continue

            # --- Step 1: Copy file into Open WebUI's upload storage ---
            file_id = str(uuid.uuid4())
            original_name = source.name
            storage_name = f"{file_id}_{original_name}"

            with open(source, "rb") as f:
                contents = f.read()

            if len(contents) == 0:
                results.append(
                    LocalImportResult(
                        path=rel_path,
                        status="failed",
                        error="Empty file",
                    )
                )
                continue

            file_hash = hashlib.sha256(contents).hexdigest()

            # Guess content type
            content_type, _ = mimetypes.guess_type(original_name)
            if content_type is None:
                content_type = "application/octet-stream"

            # Write to upload dir (same as Storage.upload_file does for local)
            upload_path = UPLOAD_DIR / storage_name
            with open(upload_path, "wb") as out:
                out.write(contents)
            file_path = str(upload_path)

            # --- Step 2: Create DB record ---
            file_item = await Files.insert_new_file(
                user.id,
                FileForm(
                    id=file_id,
                    filename=original_name,
                    path=file_path,
                    data={"status": "pending"},
                    meta={
                        "name": original_name,
                        "content_type": content_type,
                        "size": len(contents),
                        "file_hash": file_hash,
                        "data": {
                            "knowledge_id": form_data.knowledge_id,
                            "directory_id": form_data.directory_id,
                        },
                    },
                ),
                db=db,
            )

            if not file_item:
                results.append(
                    LocalImportResult(
                        path=rel_path,
                        status="failed",
                        error="Failed to create file record",
                    )
                )
                continue

            # --- Step 3: Process (extract text, chunk, embed) ---
            try:
                await process_file(
                    request,
                    ProcessFileForm(
                        file_id=file_id,
                        collection_name=form_data.knowledge_id,
                    ),
                    user=user,
                    db=db,
                )

                # Link file to knowledge base
                await Knowledges.add_file_to_knowledge_by_id(
                    knowledge_id=form_data.knowledge_id,
                    file_id=file_id,
                    user_id=user.id,
                    directory_id=form_data.directory_id,
                    db=db,
                )

                results.append(
                    LocalImportResult(
                        path=rel_path,
                        status="completed",
                        file_id=file_id,
                    )
                )
                log.info(
                    "Local import OK: %s → KB %s (file_id=%s)",
                    rel_path,
                    form_data.knowledge_id,
                    file_id,
                )

            except Exception as e:
                error_msg = str(e.detail) if hasattr(e, "detail") else str(e)
                await Files.update_file_data_by_id(
                    file_id,
                    {"status": "failed", "error": error_msg},
                    db=db,
                )
                results.append(
                    LocalImportResult(
                        path=rel_path,
                        status="failed",
                        file_id=file_id,
                        error=error_msg,
                    )
                )
                log.error(
                    "Local import FAILED: %s → %s",
                    rel_path,
                    error_msg,
                )

        except HTTPException:
            raise
        except Exception as e:
            results.append(
                LocalImportResult(
                    path=rel_path,
                    status="failed",
                    error=str(e),
                )
            )
            log.error("Local import error for %s: %s", rel_path, e)

    return results
