"""
Analytics router — global summary metrics from Langfuse traces.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from open_webui.utils.auth import get_admin_user
from open_webui.integrations.langfuse_adapter import get_langfuse_adapter

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/summary")
async def get_global_summary(days: int = 7, user=Depends(get_admin_user)):
    if days not in (1, 7, 30):
        days = 7

    adapter = get_langfuse_adapter()
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Langfuse not configured",
        )

    try:
        return adapter.get_global_summary(days=days)
    except Exception as e:
        log.error(f"[ANALYTICS] summary failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/trace/{trace_id}")
async def get_trace_detail(trace_id: str, user=Depends(get_admin_user)):
    adapter = get_langfuse_adapter()
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Langfuse not configured",
        )

    try:
        detail = adapter.get_trace_detail(trace_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="trace not found")
        return detail
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"[ANALYTICS] trace detail failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
