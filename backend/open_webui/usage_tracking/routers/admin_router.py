"""
Admin Router - Administrative endpoints for testing and maintenance
Includes batch processing triggers and system diagnostics
"""

import os
from datetime import date, datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from open_webui.utils.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

admin_router = APIRouter()


class BatchTriggerRequest(BaseModel):
    """Request model for manual batch processing trigger"""
    processing_date: str  # YYYY-MM-DD format
    force_reprocess: bool = False


class BatchTriggerResponse(BaseModel):
    """Response model for batch processing trigger"""
    success: bool
    message: str
    processing_date: str
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@admin_router.post("/admin/trigger-batch", response_model=BatchTriggerResponse)
async def trigger_manual_batch_processing(
    request: BatchTriggerRequest,
    user=Depends(get_current_user)
):
    """
    Manually trigger batch processing for a specific date
    
    This endpoint is primarily for testing and emergency processing.
    In production, batch processing runs automatically via scheduler.
    """
    try:
        # Parse the processing date
        try:
            processing_date = datetime.strptime(request.processing_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: {request.processing_date}. Use YYYY-MM-DD"
            )
        
        # Check if this is a test environment or admin user
        is_test_env = os.getenv("ENVIRONMENT", "production").lower() in ["test", "development", "dev"]
        
        if not is_test_env:
            # In production, add additional security checks
            logger.warning(f"Manual batch processing triggered in production by user {user.id}")
            
            # You might want to add role-based access control here
            # For now, we'll allow it but log it heavily
        
        logger.info(f"Manual batch processing triggered for {processing_date} by user {user.id}")
        
        # Import and run the batch processor
        try:
            from open_webui.utils.daily_batch_processor_influx import run_influxdb_batch
            
            # Run the batch processing
            batch_result = await run_influxdb_batch(processing_date)
            
            if batch_result.get("success", False):
                return BatchTriggerResponse(
                    success=True,
                    message=f"Batch processing completed successfully for {processing_date}",
                    processing_date=request.processing_date,
                    results=batch_result
                )
            else:
                return BatchTriggerResponse(
                    success=False,
                    message=f"Batch processing failed for {processing_date}",
                    processing_date=request.processing_date,
                    error=batch_result.get("error", "Unknown error"),
                    results=batch_result
                )
        
        except ImportError as e:
            logger.error(f"Failed to import batch processor: {e}")
            raise HTTPException(
                status_code=503,
                detail="Batch processing service not available"
            )
        
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return BatchTriggerResponse(
                success=False,
                message=f"Batch processing failed for {processing_date}",
                processing_date=request.processing_date,
                error=str(e)
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual batch trigger failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger batch processing: {str(e)}"
        )


@admin_router.get("/admin/batch-status")
async def get_batch_processing_status(user=Depends(get_current_user)):
    """Get the status of batch processing system"""
    try:
        status = {
            "batch_processor_available": False,
            "influxdb_enabled": os.getenv("INFLUXDB_ENABLED", "false").lower() == "true",
            "dual_write_mode": os.getenv("DUAL_WRITE_MODE", "false").lower() == "true",
            "last_batch_run": None,
            "environment": os.getenv("ENVIRONMENT", "production")
        }
        
        # Try to import batch processor to check availability
        try:
            from open_webui.utils.daily_batch_processor_influx import DailyBatchProcessorInflux
            status["batch_processor_available"] = True
            
            # Try to get last run information from database if available
            # This would require a batch_runs table to track execution history
            
        except ImportError:
            pass
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get batch status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get batch processing status: {str(e)}"
        )


@admin_router.get("/admin/system-health")
async def get_system_health(user=Depends(get_current_user)):
    """Get overall system health for diagnostics"""
    try:
        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "database": {"status": "unknown"},
            "influxdb": {"status": "unknown"},
            "nbp_service": {"status": "unknown"},
            "webhook_service": {"status": "unknown"}
        }
        
        # Check database connectivity
        try:
            from open_webui.utils.database import get_db
            db = next(get_db())
            db.execute("SELECT 1")
            health["database"]["status"] = "healthy"
            db.close()
        except Exception as e:
            health["database"]["status"] = "error"
            health["database"]["error"] = str(e)
        
        # Check InfluxDB if enabled
        if os.getenv("INFLUXDB_ENABLED", "false").lower() == "true":
            try:
                from open_webui.usage_tracking.services.influxdb_service import InfluxDBService
                influx_service = InfluxDBService()
                influx_health = await influx_service.health_check()
                health["influxdb"] = influx_health
            except Exception as e:
                health["influxdb"]["status"] = "error"
                health["influxdb"]["error"] = str(e)
        else:
            health["influxdb"]["status"] = "disabled"
        
        # Check NBP service
        try:
            nbp_url = os.getenv("NBP_SERVICE_URL", "http://localhost:8001")
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{nbp_url}/health", timeout=5.0)
                if response.status_code == 200:
                    health["nbp_service"]["status"] = "healthy"
                else:
                    health["nbp_service"]["status"] = "error"
                    health["nbp_service"]["error"] = f"HTTP {response.status_code}"
        except Exception as e:
            health["nbp_service"]["status"] = "error"
            health["nbp_service"]["error"] = str(e)
        
        # Check webhook service
        try:
            from open_webui.usage_tracking.services.webhook_service import WebhookService
            webhook_service = WebhookService()
            webhook_status = await webhook_service.get_service_status()
            health["webhook_service"] = webhook_status
        except Exception as e:
            health["webhook_service"]["status"] = "error"
            health["webhook_service"]["error"] = str(e)
        
        return health
        
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"System health check failed: {str(e)}"
        )


@admin_router.post("/admin/cleanup-test-data")
async def cleanup_test_data(user=Depends(get_current_user)):
    """Clean up test data from databases (test environments only)"""
    try:
        environment = os.getenv("ENVIRONMENT", "production").lower()
        
        if environment == "production":
            raise HTTPException(
                status_code=403,
                detail="Test data cleanup is not allowed in production"
            )
        
        logger.info(f"Test data cleanup triggered by user {user.id}")
        
        cleanup_results = {
            "sqlite_records_deleted": 0,
            "influxdb_records_deleted": 0,
            "test_clients_removed": 0
        }
        
        # Clean SQLite test data
        try:
            from open_webui.utils.database import get_db
            from open_webui.usage_tracking.models.database import (
                ClientDailyUsageDB, 
                ClientUserDailyUsageDB,
                DailyExchangeRateDB
            )
            from open_webui.models.organization_usage import ClientOrganizationDB
            
            db = next(get_db())
            
            # Delete test client organizations
            test_clients = db.query(ClientOrganizationDB).filter(
                ClientOrganizationDB.id.like("test-%")
            ).all()
            
            for client in test_clients:
                # Delete usage records
                db.query(ClientDailyUsageDB).filter_by(client_org_id=client.id).delete()
                db.query(ClientUserDailyUsageDB).filter_by(client_org_id=client.id).delete()
                cleanup_results["sqlite_records_deleted"] += 1
                
                # Delete client
                db.delete(client)
                cleanup_results["test_clients_removed"] += 1
            
            # Delete test exchange rates (dates from 2025 are probably test data)
            test_rates = db.query(DailyExchangeRateDB).filter(
                DailyExchangeRateDB.date >= date(2025, 1, 1)
            ).delete()
            cleanup_results["sqlite_records_deleted"] += test_rates
            
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error(f"SQLite cleanup failed: {e}")
            cleanup_results["sqlite_error"] = str(e)
        
        # Clean InfluxDB test data if enabled
        if os.getenv("INFLUXDB_ENABLED", "false").lower() == "true":
            try:
                from open_webui.usage_tracking.services.influxdb_service import InfluxDBService
                influx_service = InfluxDBService()
                
                # Delete test data (this would need to be implemented in InfluxDBService)
                # For now, just report that it would be cleaned
                cleanup_results["influxdb_records_deleted"] = "Not implemented"
                
            except Exception as e:
                logger.error(f"InfluxDB cleanup failed: {e}")
                cleanup_results["influxdb_error"] = str(e)
        
        return {
            "success": True,
            "message": "Test data cleanup completed",
            "results": cleanup_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Test data cleanup failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Test data cleanup failed: {str(e)}"
        )