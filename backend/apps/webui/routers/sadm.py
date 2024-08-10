# apps/webui/router/sadm.py
import logging

from fastapi import APIRouter, HTTPException, Depends, status

from apps.webui.models.sadm import (
    SADMStatus,
    SelfAwareDocumentMonitoring
)

from apps.rag.main import (
    scan_docs_dir
)

from utils.utils import (
    get_admin_user
)

from config import (
    DOCS_DIR,
    SRC_LOG_LEVELS,
    GLOBAL_LOG_LEVEL
)

# Logging setup
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()
monitoring_manager = SelfAwareDocumentMonitoring()

@router.post("/enable")
def enable_monitoring_route(user=Depends(get_admin_user)):
    if monitoring_manager.read_sadm_state() == "enabled":
        return {"message": "Self-Aware Document Monitoring is already enabled"}

    try:
        monitoring_manager.write_sadm_state("enabled")
        log.info("Self-Aware Document Monitoring has been enabled and will automatically start across application startups!")
        monitoring_manager.ensure_location_column_exists()

        if DOCS_DIR:
            try:
                log.info("Scanning for new Documents...")
                scan_docs_dir(user=user)
                log.info("Scan completed successfully!")
            except Exception as scan_error:
                log.error(f"Failed to scan documents: {scan_error}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to scan documents: {scan_error}")

        monitoring_manager.start_monitoring_thread(DOCS_DIR)
        return {"message": "Self-Aware Document Monitoring has been enabled and is now Active"}
    except Exception as e:
        log.error(f"Failed to enable monitoring: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to enable monitoring: {e}")


@router.post("/disable")
def disable_monitoring_route(user=Depends(get_admin_user)):
    if monitoring_manager.read_sadm_state() == "disabled":
        return {"message": "Self-Aware Document Monitoring is already disabled"}

    try:
        monitoring_manager.write_sadm_state("disabled")
        monitoring_manager.stop_monitoring_thread()
        return {"message": "Self-Aware Document Monitoring has been disabled and is now inactive"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to disable monitoring: {e}")

@router.get("/status", response_model=SADMStatus)
def status_route(user=Depends(get_admin_user)):
    state = monitoring_manager.read_sadm_state()
    is_thread_alive = monitoring_manager.monitoring_thread and monitoring_manager.monitoring_thread.is_alive()
    
    status = "running" if (state == "enabled" and is_thread_alive) else "disabled"
    
    return {"status": status}