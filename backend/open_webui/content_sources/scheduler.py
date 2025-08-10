"""Generic content source sync scheduler for all providers."""
import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from open_webui.env import ENV
from open_webui.models.knowledge import Knowledges
from open_webui.content_sources import content_source_factory, content_source_registry
from open_webui.models.files import Files

log = logging.getLogger(__name__)


class ContentSourceScheduler:
    """Generic background scheduler for automatic content source sync.
    
    This scheduler handles sync for all content source providers (Google Drive,
    Dropbox, OneDrive, etc.) in a unified way.
    """

    def __init__(self) -> None:
        self.running: bool = False
        self.sync_tasks: Dict[str, Any] = {}
        self.scheduler_task: Optional[asyncio.Task] = None
        # In dev environment, check every minute for faster testing
        # In production, check every hour
        self.check_interval: int = 60 if ENV == "dev" else 3600

    async def start(self) -> None:
        """Start the background sync scheduler."""
        if self.running:
            log.warning("Sync scheduler already running")
            return

        self.running = True
        log.info("Starting content source sync scheduler")
        
        # Start the main scheduler loop as a background task
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """Stop the background sync scheduler."""
        log.info("Stopping content source sync scheduler")
        self.running = False
        
        # Cancel the scheduler task if it exists
        if self.scheduler_task and not self.scheduler_task.done():
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all running sync tasks
        for task_id, task in self.sync_tasks.items():
            if not task.done():
                task.cancel()
                log.info(f"Cancelled sync task: {task_id}")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop that checks for sync tasks."""
        while self.running:
            try:
                await self._check_and_sync_knowledge_bases()
            except Exception as e:
                log.error(f"Error in sync scheduler loop: {e}", exc_info=True)
            
            # Wait before next check
            await asyncio.sleep(self.check_interval)

    async def _check_and_sync_knowledge_bases(self) -> None:
        """Check all knowledge bases for content source sync needs."""
        try:
            # Run synchronous database operation in a thread pool to avoid blocking
            import asyncio
            loop = asyncio.get_event_loop()
            knowledge_bases = await loop.run_in_executor(None, Knowledges.get_knowledge_bases)
        except Exception as e:
            log.error(f"Error fetching knowledge bases: {e}")
            return
        
        if ENV == "dev":
            log.info(f"Checking {len(knowledge_bases)} knowledge bases for sync needs")
        
        for kb in knowledge_bases:
            if not kb.data:
                continue
                
            # Check for sync metadata (new structure)
            sync_metadata = kb.data.get("sync_metadata", {})
            if not sync_metadata:
                continue
            
            if ENV == "dev":
                log.info(f"KB {kb.id} has sync_metadata for providers: {list(sync_metadata.keys())}")
            
            # Check each provider's sync configuration
            for provider_name, provider_config in sync_metadata.items():
                if not provider_config:
                    continue
                    
                # Get sync interval from options
                options = provider_config.get("options", {})
                sync_interval_days = options.get("sync_interval_days", 1)
                last_sync = provider_config.get("last_sync", 0)
                
                # Convert sync interval to seconds
                sync_interval_seconds = sync_interval_days * 24 * 60 * 60
                current_time = time.time()
                
                # Log for debugging in dev mode
                if ENV == "dev":
                    time_since_last_sync = current_time - last_sync
                    time_until_next_sync = sync_interval_seconds - time_since_last_sync
                    log.info(f"KB {kb.id} - Provider {provider_name}: "
                             f"sync_interval_days={sync_interval_days} ({sync_interval_seconds}s), "
                             f"last_sync={datetime.fromtimestamp(last_sync).isoformat() if last_sync else 'never'}, "
                             f"time_since_last={time_since_last_sync:.1f}s, "
                             f"time_until_next={time_until_next_sync:.1f}s, "
                             f"needs_sync={time_since_last_sync >= sync_interval_seconds}")
                
                if current_time - last_sync >= sync_interval_seconds:
                    # Schedule sync task
                    task_id = f"{kb.id}_{provider_name}_{int(current_time)}"
                    
                    if task_id not in self.sync_tasks or self.sync_tasks[task_id].done():
                        log.info(f"Scheduling sync for knowledge base {kb.id} with provider {provider_name}")
                        
                        # Build content source config for sync
                        content_source_config = {
                            "provider": provider_name,
                            "source_id": provider_config.get("source_id"),
                            "options": options
                        }
                        
                        task = asyncio.create_task(
                            self._sync_knowledge_base(kb.id, provider_name, content_source_config)
                        )
                        self.sync_tasks[task_id] = task

    async def _sync_knowledge_base(
        self, 
        kb_id: str, 
        provider_name: str,
        content_source_config: Dict[str, Any]
    ) -> None:
        """Sync a specific knowledge base with its content source provider."""
        try:
            log.info(f"Starting scheduled sync for knowledge base {kb_id} with {provider_name}")
            
            # Import the sync service
            from open_webui.content_sources.syncer import content_syncer
            
            # Get knowledge base to get user ID (run in thread pool to avoid blocking)
            loop = asyncio.get_event_loop()
            kb = await loop.run_in_executor(None, Knowledges.get_knowledge_by_id, kb_id)
            if not kb:
                log.error(f"Knowledge base {kb_id} not found")
                return
            
            # Perform actual sync using the sync service
            source_id = content_source_config.get("source_id")
            options = content_source_config.get("options", {})
            
            # Add auto_sync flag for scheduled syncs
            options["auto_sync"] = True
            options["rollback_on_error"] = False  # Don't rollback on scheduled syncs
            
            try:
                # Use the sync service to perform the actual sync
                sync_result = await content_syncer.sync_provider_files(
                    provider_name=provider_name,
                    source_id=source_id,
                    options=options,
                    request=None,  # No request object in scheduler context
                    user_id=kb.user_id,
                    knowledge_base_id=kb_id
                )
                
                # Update knowledge base with sync results
                data = kb.data or {}
                
                # Get event loop for async operations
                loop = asyncio.get_event_loop()
                
                # Update file IDs with successfully synced files
                existing_file_ids = set(data.get("file_ids", []))
                new_file_ids = set(sync_result.successful_files)
                updated_file_ids = list(existing_file_ids | new_file_ids)
                data["file_ids"] = updated_file_ids
                
                # Update sync metadata in new structure
                data.setdefault("sync_metadata", {})
                data["sync_metadata"].setdefault(provider_name, {})
                
                # Preserve existing configuration
                existing_config = data["sync_metadata"][provider_name]
                
                # Update with new sync results
                data["sync_metadata"][provider_name].update({
                    "source_id": source_id,
                    "last_sync": time.time(),
                    "options": options,
                    "results": {
                        "status": sync_result.status.value,
                        "added": len(sync_result.added_files),
                        "updated": len(sync_result.updated_files),
                        "failed": len(sync_result.failed_files),
                        "duplicates": len(sync_result.duplicate_files),
                        "changes": sync_result.changes
                    }
                })
                
                # Store any errors for monitoring
                if sync_result.errors:
                    data["sync_metadata"][provider_name]["last_sync_errors"] = sync_result.errors[:5]  # Keep last 5 errors
                
                await loop.run_in_executor(None, Knowledges.update_knowledge_data_by_id, kb_id, data)
                
                log.info(f"Completed scheduled sync for knowledge base {kb_id}: "
                        f"status={sync_result.status.value}, "
                        f"added={len(sync_result.added_files)}, "
                        f"updated={len(sync_result.updated_files)}, "
                        f"failed={len(sync_result.failed_files)}")
                
            except Exception as sync_error:
                log.error(f"Sync service error for knowledge base {kb_id}: {sync_error}")
                
                # Get event loop for async operations
                loop = asyncio.get_event_loop()
                
                # Update knowledge base with error status
                data = kb.data or {}
                data.setdefault("sync_metadata", {})
                data["sync_metadata"].setdefault(provider_name, {})
                
                # Preserve existing configuration
                existing_config = data["sync_metadata"][provider_name]
                source_id = existing_config.get("source_id", source_id)
                existing_options = existing_config.get("options", {})
                
                data["sync_metadata"][provider_name].update({
                    "source_id": source_id,
                    "last_sync": time.time(),
                    "options": existing_options,
                    "results": {
                        "status": "failed",
                        "error": str(sync_error)
                    }
                })
                await loop.run_in_executor(None, Knowledges.update_knowledge_data_by_id, kb_id, data)
                raise
            
        except Exception as e:
            log.error(f"Error in scheduled sync for knowledge base {kb_id}: {e}", exc_info=True)


# Global scheduler instance
scheduler = ContentSourceScheduler()