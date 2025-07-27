import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import uuid
import io

from open_webui.env import ENV
from open_webui.models.knowledge import Knowledges, KnowledgeModel
from open_webui.services.google_drive import google_drive_service, GoogleDriveFile
from open_webui.models.files import Files, FileModel, FileForm
from open_webui.routers.retrieval import process_file, ProcessFileForm
from open_webui.storage.provider import Storage

log = logging.getLogger(__name__)


class GoogleDriveSyncScheduler:
    """Background scheduler for automatic Google Drive folder sync."""

    def __init__(self) -> None:
        self.running: bool = False
        self.sync_tasks: Dict[str, Any] = {}
        # In dev environment, check every minute for faster testing
        # In production, check every hour
        self.check_interval: int = 60 if ENV == "dev" else 3600

    async def start(self) -> None:
        """Start the background sync scheduler."""
        if self.running:
            return

        self.running = True
        log.info(f"Google Drive sync scheduler started (ENV: {ENV}, check_interval: {self.check_interval}s)")

        # Start the background task
        asyncio.create_task(self._sync_loop())

    async def stop(self) -> None:
        """Stop the background sync scheduler."""
        self.running = False
        log.info("Google Drive sync scheduler stopped")

    async def _sync_loop(self) -> None:
        """Main sync loop that runs in the background."""
        while self.running:
            try:
                await self._check_and_sync_knowledge_bases()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                log.error(f"Error in sync loop: {e}")
                await asyncio.sleep(self.check_interval)

    async def _check_and_sync_knowledge_bases(self) -> None:
        """Check all knowledge bases for Google Drive sync requirements."""
        if not google_drive_service.is_configured():
            return

        try:
            # Get all knowledge bases
            knowledge_bases = Knowledges.get_knowledge_bases()

            for kb in knowledge_bases:
                if not kb.data:
                    continue

                # Check if this knowledge base has Google Drive sync configured
                folder_id = kb.data.get("google_drive_folder_id")
                sync_interval_days = kb.data.get("google_drive_sync_interval_days", 1)
                last_sync = kb.data.get("google_drive_last_sync", 0)

                if not folder_id:
                    continue

                # Check if sync is due
                current_time = int(time.time())
                sync_interval_seconds = sync_interval_days * 24 * 3600

                if current_time - last_sync >= sync_interval_seconds:
                    log.info(
                        f"Auto-syncing knowledge base {kb.id} with Google Drive folder {folder_id}"
                    )
                    await self._sync_knowledge_base(kb)

        except Exception as e:
            log.error(f"Error checking knowledge bases for sync: {e}")

    async def _sync_knowledge_base(self, knowledge_base: KnowledgeModel) -> None:
        """Sync a specific knowledge base with its Google Drive folder."""
        try:
            if not knowledge_base.data:
                return

            # Type guard for mypy
            assert knowledge_base.data is not None

            folder_id = knowledge_base.data.get("google_drive_folder_id")
            include_nested = knowledge_base.data.get(
                "google_drive_include_nested", True
            )

            if not folder_id:
                return

            # Get current files in knowledge base
            current_file_ids = knowledge_base.data.get("file_ids", [])
            current_files = Files.get_files_by_ids(current_file_ids)

            # Create a map of Google Drive file IDs to local file IDs
            gdrive_file_map = {}
            for file in current_files:
                if file.meta and file.meta.get("google_drive_id"):
                    gdrive_file_map[file.meta["google_drive_id"]] = file.id

            # Get files from Google Drive folder
            gdrive_files = google_drive_service.list_folder_files(
                folder_id, include_nested
            )

            # Track files to keep and files to add
            files_to_keep = set()
            files_to_add = []

            for gdrive_file in gdrive_files:
                gdrive_id = gdrive_file["id"]

                if gdrive_id in gdrive_file_map:
                    # File exists, check if it needs updating
                    local_file_id = gdrive_file_map[gdrive_id]
                    local_file = Files.get_file_by_id(local_file_id)

                    if local_file and local_file.meta:
                        local_modified = local_file.meta.get("google_drive_modified")
                        gdrive_modified = gdrive_file["modifiedTime"]

                        if local_modified != gdrive_modified:
                            # File was modified, re-download and update
                            files_to_add.append(gdrive_file)
                            # Remove old file
                            Files.delete_file_by_id(local_file_id)
                        else:
                            # File is up to date, keep it
                            files_to_keep.add(local_file_id)
                    else:
                        # Local file metadata is missing, re-download
                        files_to_add.append(gdrive_file)
                else:
                    # New file, add it
                    files_to_add.append(gdrive_file)

            # Remove files that are no longer in Google Drive
            files_to_remove = set(current_file_ids) - files_to_keep
            for file_id in files_to_remove:
                Files.delete_file_by_id(file_id)

            # Download and add new/updated files
            new_file_ids = list(files_to_keep)

            for gdrive_file in files_to_add:
                try:
                    # Download file from Google Drive
                    file_content, filename = google_drive_service.download_file(
                        gdrive_file["id"], gdrive_file
                    )

                    # Create file object
                    file_obj = io.BytesIO(file_content)
                    file_obj.name = filename

                    # Upload to storage
                    file_id = str(uuid.uuid4())
                    tags = {
                        "OpenWebUI-User-Email": "system",
                        "OpenWebUI-User-Id": "system",
                        "OpenWebUI-User-Name": "Google Drive Sync",
                        "OpenWebUI-File-Id": file_id,
                    }

                    contents, file_path = Storage.upload_file(
                        file_obj, f"{file_id}_{filename}", tags
                    )

                    # Create file record
                    file_form = FileForm(
                        id=file_id,
                        filename=filename,
                        path=file_path,
                        meta={
                            "name": filename,
                            "content_type": "application/octet-stream",
                            "size": len(contents),
                            "google_drive_id": gdrive_file["id"],
                            "google_drive_modified": gdrive_file["modifiedTime"],
                            "google_drive_path": gdrive_file["path"],
                            "collection_name": knowledge_base.id,
                        },
                    )
                    file_item = Files.insert_new_file(knowledge_base.user_id, file_form)

                    if file_item:
                        new_file_ids.append(file_id)

                        # Process file for vector storage
                        try:
                            process_file(
                                ProcessFileForm(
                                    file_id=file_id,
                                    collection_name=knowledge_base.id,
                                )
                            )
                        except Exception as e:
                            log.error(f"Failed to process file {file_id}: {e}")

                except Exception as e:
                    log.error(f"Failed to sync file {gdrive_file['name']}: {e}")
                    continue

            # Update knowledge base data
            assert knowledge_base.data is not None  # Type guard for mypy
            updated_data = knowledge_base.data.copy()
            updated_data["file_ids"] = new_file_ids
            updated_data["google_drive_last_sync"] = int(time.time())

            Knowledges.update_knowledge_data_by_id(
                id=knowledge_base.id, data=updated_data
            )

            log.info(
                f"Successfully synced knowledge base {knowledge_base.id} with {len(files_to_add)} new/updated files"
            )

        except Exception as e:
            log.error(f"Error syncing knowledge base {knowledge_base.id}: {e}")


# Global scheduler instance
google_drive_scheduler = GoogleDriveSyncScheduler()
