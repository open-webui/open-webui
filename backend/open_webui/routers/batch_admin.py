"""
Admin endpoints for daily batch processing management
"""

from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from open_webui.models.users import Users
from open_webui.utils.auth import get_admin_user

# Import batch scheduler functions
from open_webui.utils.batch_scheduler import (
    get_batch_scheduler,
    trigger_batch_manually
)

batch_admin_router = APIRouter(tags=["admin", "batch"])

class BatchStatusResponse(BaseModel):
    """Response model for batch scheduler status"""
    is_running: bool
    next_run_time: Optional[str] = None
    timezone: str = "Europe/Warsaw (CET/CEST)"
    scheduled_time: str = "13:00 daily"

class BatchTriggerResponse(BaseModel):
    """Response model for manual batch trigger"""
    success: bool
    message: str
    execution_time: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

@batch_admin_router.get("/status", response_model=BatchStatusResponse)
async def get_batch_scheduler_status(user=Depends(get_admin_user)):
    """
    Get current status of the daily batch processing scheduler
    Admin only endpoint
    """
    try:
        scheduler = get_batch_scheduler()
        
        if scheduler is None:
            return BatchStatusResponse(
                is_running=False,
                next_run_time=None
            )
        
        next_run = scheduler.get_next_run_time()
        next_run_str = next_run.isoformat() if next_run else None
        
        return BatchStatusResponse(
            is_running=scheduler.is_scheduler_running(),
            next_run_time=next_run_str
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting batch scheduler status: {str(e)}"
        )

@batch_admin_router.post("/trigger", response_model=BatchTriggerResponse)
async def trigger_batch_processing(user=Depends(get_admin_user)):
    """
    Manually trigger daily batch processing
    Admin only endpoint - useful for testing or emergency processing
    """
    try:
        execution_start = datetime.now()
        
        # Trigger batch processing manually
        result = await trigger_batch_manually()
        
        execution_time = (datetime.now() - execution_start).total_seconds()
        
        if result.get('success', False):
            return BatchTriggerResponse(
                success=True,
                message="Batch processing completed successfully",
                execution_time=f"{execution_time:.2f} seconds",
                details=result
            )
        else:
            return BatchTriggerResponse(
                success=False,
                message=f"Batch processing failed: {result.get('error', 'Unknown error')}",
                execution_time=f"{execution_time:.2f} seconds",
                details=result
            )
            
    except Exception as e:
        return BatchTriggerResponse(
            success=False,
            message=f"Error triggering batch processing: {str(e)}"
        )

# Export the router
router = batch_admin_router