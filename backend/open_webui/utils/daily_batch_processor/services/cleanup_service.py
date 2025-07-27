"""
Data Cleanup Service - Removes old processed generation records
"""

from datetime import datetime
import logging
from typing import Dict, Any

from open_webui.models.organization_usage import ProcessedGenerationDB
from ..models.batch_models import CleanupResult
from ..repositories.system_repository import SystemRepository
from ..utils.batch_logger import BatchLogger

log = logging.getLogger(__name__)


class DataCleanupService:
    """Service for cleaning up old data"""
    
    def __init__(self, system_repo: SystemRepository):
        self.system_repo = system_repo
        self.logger = BatchLogger("Data Cleanup")
        
    async def cleanup_old_data(self) -> CleanupResult:
        """Clean up old processed generation records to prevent database bloat"""
        self.logger.start()
        
        try:
            with self.logger.step("Getting retention settings") as step:
                # Get retention period from settings
                retention_days = await self.system_repo.get_system_setting("retention_days")
                if not retention_days:
                    retention_days = 60  # Default
                    
                step["details"]["retention_days"] = retention_days
                
            with self.logger.step("Cleaning old records") as step:
                # Use existing cleanup method
                cleanup_result = ProcessedGenerationDB.cleanup_old_processed_generations(
                    days_to_keep=retention_days
                )
                
                step["details"]["records_deleted"] = cleanup_result.get("records_deleted", 0)
                step["details"]["storage_saved_kb"] = cleanup_result.get("storage_saved_kb", 0)
                
                if cleanup_result["success"]:
                    log.info(
                        f"🧹 Data cleanup completed: {cleanup_result['records_deleted']} "
                        f"old records removed, ~{cleanup_result['storage_saved_kb']}KB saved"
                    )
                    
                result = CleanupResult(
                    success=cleanup_result["success"],
                    records_deleted=cleanup_result.get("records_deleted", 0),
                    storage_saved_kb=cleanup_result.get("storage_saved_kb", 0)
                )
                
                self.logger.complete({
                    "records_deleted": result.records_deleted,
                    "storage_saved_kb": result.storage_saved_kb
                })
                
                return result
                
        except Exception as e:
            log.error(f"❌ Data cleanup failed: {e}")
            
            result = CleanupResult(
                success=False,
                error=str(e)
            )
            
            self.logger.complete({"error": str(e)})
            
            return result