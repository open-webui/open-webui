"""Periodic auto-sync scheduler for tracked SharePoint folders.

Runs as a long-lived asyncio task started at app startup.
Every SHAREPOINT_SYNC_INTERVAL seconds (default 900 = 15 min), it iterates
all SpaceSharePointFolder records, runs a delta sync for each, and updates
last_synced_at + per-run counters.
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
import uuid

log = logging.getLogger(__name__)


async def periodic_sharepoint_sync() -> None:
    """Infinite loop: delta-sync every tracked SP folder on a schedule."""
    await asyncio.sleep(30)  # Let app finish startup before first run

    while True:
        interval = 900  # fallback default
        try:
            from open_webui.config import (
                ENABLE_SHAREPOINT_INTEGRATION,
                SHAREPOINT_SYNC_INTERVAL,
            )

            interval = int(SHAREPOINT_SYNC_INTERVAL.value)

            if ENABLE_SHAREPOINT_INTEGRATION.value:
                log.debug("[sp_scheduler] Starting scheduled sync run")
                await _sync_all_folders()
            else:
                log.debug("[sp_scheduler] SharePoint integration disabled, skipping")
        except Exception as exc:
            log.error(
                f"[sp_scheduler] Unhandled error in sync loop: {exc}", exc_info=True
            )

        await asyncio.sleep(interval)


async def _sync_all_folders() -> None:
    from open_webui.models.spaces import SpaceSharePointFolders
    from open_webui.internal.db import get_db

    with get_db() as db:
        all_folders = SpaceSharePointFolders.get_all(db=db)

    if not all_folders:
        log.debug("[sp_scheduler] No tracked folders found")
        return

    log.info(f"[sp_scheduler] Syncing {len(all_folders)} tracked folder(s)")

    for folder_rec in all_folders:
        try:
            await _sync_folder(folder_rec)
        except Exception as exc:
            log.warning(
                f"[sp_scheduler] Folder {folder_rec.id} "
                f"({folder_rec.folder_name} / space {folder_rec.space_id}): {exc}"
            )


async def _sync_folder(folder_rec) -> None:
    """Run a delta sync for a single SpaceSharePointFolderModel record."""
    from open_webui.models.spaces import SpaceSharePointFolders, Spaces
    from open_webui.models.files import Files, FileForm
    from open_webui.storage.provider import Storage
    from open_webui.routers.sharepoint import (
        get_tokens_for_tenant,
        get_tenant_by_id,
        graph_api_request,
    )
    from open_webui.routers.spaces import (
        _process_file_background,
        _download_sp_file,
        _space_sync_in_progress,
    )
    from open_webui.models.users import Users
    from open_webui.internal.db import get_db
    import aiohttp

    # Skip if a manual sync is already running for this space
    if folder_rec.space_id in _space_sync_in_progress:
        log.debug(
            f"[sp_scheduler] Space {folder_rec.space_id} sync in progress, skipping"
        )
        return

    # Resolve tenant
    tenant = get_tenant_by_id(folder_rec.tenant_id)
    if not tenant:
        log.warning(
            f"[sp_scheduler] Tenant {folder_rec.tenant_id} not found, skipping folder {folder_rec.id}"
        )
        return

    # Resolve space owner for file record ownership
    with get_db() as db:
        space = Spaces.get_space_by_id(id=folder_rec.space_id, db=db)
    if not space:
        log.warning(f"[sp_scheduler] Space {folder_rec.space_id} not found")
        return

    user = Users.get_user_by_id(space.user_id)
    if not user:
        log.warning(f"[sp_scheduler] Space owner {space.user_id} not found")
        return

    # Build a minimal Request for _process_file_background (needs app.state)
    fake_request = None
    try:
        from open_webui.main import app as _app
        from starlette.requests import Request as _StarletteRequest

        fake_request = _StarletteRequest(
            {
                "type": "http",
                "method": "GET",
                "path": "/",
                "headers": [],
                "app": _app,
                "query_string": b"",
            }
        )
    except Exception:
        pass  # RAG indexing will be skipped this run

    # Acquire tokens (client credentials, user/request not needed)
    try:
        tokens = await get_tokens_for_tenant(tenant, user, None)
    except Exception as tok_err:
        log.warning(
            f"[sp_scheduler] Token acquisition failed for tenant {folder_rec.tenant_id}: {tok_err}"
        )
        return

    # Determine delta start URL
    if folder_rec.delta_link:
        start_url = folder_rec.delta_link
        use_full_url = True
    else:
        if folder_rec.folder_id:
            start_url = (
                f"/drives/{folder_rec.drive_id}/items/{folder_rec.folder_id}/delta"
            )
        else:
            start_url = f"/drives/{folder_rec.drive_id}/root/delta"
        use_full_url = False

    new_delta_link = None
    next_url = start_url
    is_full_url = use_full_url
    auth_header = {"Authorization": tokens.authorization_header()}
    page = 0
    added = updated = removed = 0

    # Build item-id → file-record map for this folder
    with get_db() as db:
        all_space_files = Spaces.get_files_by_space_id(folder_rec.space_id, db=db)

    sp_item_map: dict = {}
    for f in all_space_files:
        if (
            f.meta
            and f.meta.get("source") == "sharepoint"
            and f.meta.get("sharepoint_item_id")
            and f.meta.get("sharepoint_folder_id") == (folder_rec.folder_id or "")
        ):
            sp_item_map[f.meta["sharepoint_item_id"]] = f

    # --- Delta pagination loop ---
    while next_url:
        page += 1
        if page > 200:
            log.warning(
                f"[sp_scheduler] Delta pagination cap hit for folder {folder_rec.id}"
            )
            break

        try:
            if is_full_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(next_url, headers=auth_header) as resp:
                        if resp.status >= 400:
                            err_text = await resp.text()
                            raise Exception(f"Delta {resp.status}: {err_text[:200]}")
                        resp_data = await resp.json()
            else:
                resp_data = await graph_api_request("GET", next_url, tokens)
                is_full_url = True
        except Exception as fetch_err:
            log.warning(f"[sp_scheduler] Delta fetch failed page {page}: {fetch_err}")
            break

        items = resp_data.get("value", [])
        new_delta_link = resp_data.get("@odata.deltaLink")
        next_url = resp_data.get("@odata.nextLink")

        for item in items:
            item_id = item.get("id")
            if not item_id or item.get("folder"):
                continue

            # --- Deleted ---
            if item.get("deleted"):
                existing = sp_item_map.get(item_id)
                if existing:
                    with get_db() as db:
                        Spaces.remove_file_from_space(
                            space_id=folder_rec.space_id, file_id=existing.id, db=db
                        )
                    sp_item_map.pop(item_id, None)
                    removed += 1
                continue

            # --- File ---
            item_name = item.get("name", "")
            item_modified = item.get("lastModifiedDateTime")
            mime_type = item.get("file", {}).get("mimeType", "application/octet-stream")
            file_size = item.get("size", 0)
            download_url = item.get("@microsoft.graph.downloadUrl")
            item_quick_xor_hash = (
                item.get("file", {}).get("hashes", {}).get("quickXorHash")
            )

            unsupported_types = [
                "application/vnd.ms-excel.sheet.macroEnabled.12",
                "application/vnd.ms-powerpoint.presentation.macroEnabled.12",
                "application/vnd.ms-word.document.macroEnabled.12",
            ]
            if mime_type in unsupported_types:
                continue

            existing_file = sp_item_map.get(item_id)

            if existing_file:
                # --- Change detection (hash-first, timestamp fallback) ---
                if item_quick_xor_hash and existing_file.hash:
                    if existing_file.hash == item_quick_xor_hash:
                        continue
                elif item_quick_xor_hash is None or existing_file.hash is None:
                    stored_modified = (existing_file.meta or {}).get(
                        "sharepoint_modified_at"
                    )
                    if stored_modified == item_modified:
                        if item_quick_xor_hash and existing_file.hash is None:
                            Files.update_file_hash_by_id(
                                existing_file.id, item_quick_xor_hash
                            )
                        continue

                # --- Modified: re-download ---
                try:
                    old_path = existing_file.path
                    file_bytes = await _download_sp_file(
                        download_url, folder_rec.drive_id, item_id, tokens
                    )
                    file_obj = io.BytesIO(file_bytes)
                    _contents, new_path = Storage.upload_file(
                        file_obj,
                        item_name,
                        {"source": "sharepoint", "content_type": mime_type},
                    )
                    Files.update_file_metadata_by_id(
                        existing_file.id,
                        {
                            **(existing_file.meta or {}),
                            "name": item_name,
                            "content_type": mime_type,
                            "size": file_size,
                            "sharepoint_modified_at": item_modified,
                            "last_synced_at": int(time.time()),
                        },
                    )
                    Files.update_file_path_by_id(existing_file.id, new_path)
                    if item_quick_xor_hash:
                        Files.update_file_hash_by_id(
                            existing_file.id, item_quick_xor_hash
                        )
                    try:
                        if old_path and old_path != new_path:
                            Storage.delete_file(old_path)
                    except Exception:
                        pass
                    if fake_request:
                        loop = asyncio.get_event_loop()
                        loop.run_in_executor(
                            None,
                            _process_file_background,
                            fake_request,
                            existing_file.id,
                            user,
                        )
                    updated += 1
                    log.info(f"[sp_scheduler] Updated {item_name}")
                except Exception as upd_err:
                    log.warning(
                        f"[sp_scheduler] Failed to update {item_name}: {upd_err}"
                    )

            else:
                # --- New file ---
                try:
                    # Cross-space dedup check
                    existing_global = Files.get_file_by_sharepoint_item_id(item_id)
                    if existing_global:
                        with get_db() as db:
                            Spaces.add_file_to_space(
                                space_id=folder_rec.space_id,
                                file_id=existing_global.id,
                                user_id=user.id,
                                db=db,
                            )
                        sp_item_map[item_id] = existing_global
                        added += 1
                        log.info(
                            f"[sp_scheduler] Linked existing file {item_name} (dedup)"
                        )
                        continue

                    file_bytes = await _download_sp_file(
                        download_url, folder_rec.drive_id, item_id, tokens
                    )
                    new_file_id = str(uuid.uuid4())
                    file_obj = io.BytesIO(file_bytes)
                    _contents, file_path = Storage.upload_file(
                        file_obj,
                        item_name,
                        {"source": "sharepoint", "content_type": mime_type},
                    )
                    file_form = FileForm(
                        id=new_file_id,
                        filename=item_name,
                        path=file_path,
                        hash=item_quick_xor_hash,
                        meta={
                            "name": item_name,
                            "content_type": mime_type,
                            "size": file_size,
                            "source": "sharepoint",
                            "sharepoint_drive_id": folder_rec.drive_id,
                            "sharepoint_item_id": item_id,
                            "sharepoint_tenant_id": folder_rec.tenant_id,
                            "sharepoint_folder_id": folder_rec.folder_id,
                            "sharepoint_folder_name": folder_rec.folder_name,
                            "sharepoint_site_name": folder_rec.site_name,
                            "sharepoint_modified_at": item_modified,
                        },
                    )
                    new_file_rec = Files.insert_new_file(user.id, file_form)
                    if not new_file_rec:
                        raise Exception("Failed to create file record")
                    with get_db() as db:
                        Spaces.add_file_to_space(
                            space_id=folder_rec.space_id,
                            file_id=new_file_id,
                            user_id=user.id,
                            db=db,
                        )
                    sp_item_map[item_id] = new_file_rec
                    if fake_request:
                        loop = asyncio.get_event_loop()
                        loop.run_in_executor(
                            None,
                            _process_file_background,
                            fake_request,
                            new_file_id,
                            user,
                        )
                    added += 1
                    log.info(f"[sp_scheduler] Added {item_name}")
                except Exception as add_err:
                    log.warning(f"[sp_scheduler] Failed to add {item_name}: {add_err}")

    # Persist updated delta link and sync counters
    if new_delta_link:
        SpaceSharePointFolders.update_delta_link(
            record_id=folder_rec.id,
            delta_link=new_delta_link,
            last_synced_at=int(time.time()),
            added=added,
            updated=updated,
            removed=removed,
        )
        log.info(
            f"[sp_scheduler] Folder {folder_rec.id} ({folder_rec.folder_name}): +{added} ~{updated} -{removed}"
        )
