import datetime
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.langfuse.metrics import (
    get_today_so_far,
    get_last_day,
    get_last_week,
    get_last_month,
    get_current_month,
    get_custom_days,
)

log = logging.getLogger(__name__)
router = APIRouter()


class MetricRow(BaseModel):
    user: str
    model: str
    tokens: int
    cost: float


class MyUsage(BaseModel):
    month: int
    year: int
    total_tokens: int
    total_cost: float


@router.get("/metrics", response_model=List[MetricRow])
async def get_langfuse_metrics(
    period: str = "week",
    days: Optional[int] = None,
    user=Depends(get_admin_user),
):
    """
    Fetch Langfuse token/cost metrics per user.

    period: today | day | week | month | current_month | custom
    days: required when period=custom
    """
    try:
        if period == "today":
            rows = get_today_so_far()
        elif period == "day":
            rows = get_last_day()
        elif period == "week":
            rows = get_last_week()
        elif period == "month":
            rows = get_last_month()
        elif period == "current_month":
            rows = get_current_month()
        elif period == "custom":
            if not days or days <= 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="days parameter is required and must be positive when period=custom",
                )
            rows = get_custom_days(days)
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown period '{period}'. Use: today, day, week, month, current_month, custom",
            )
        return rows
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Langfuse metrics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch Langfuse metrics: {str(e)}",
        )


@router.get("/my-usage", response_model=MyUsage)
async def get_my_langfuse_usage(
    user=Depends(get_verified_user),
):
    """
    Returns the current user's aggregated token/cost usage for the current calendar month.
    Matches Langfuse userId against the user's email.
    """
    try:
        rows = get_current_month()
    except Exception as e:
        log.error(f"Langfuse my-usage error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch Langfuse usage: {str(e)}",
        )

    user_email = user.email if hasattr(user, "email") else ""
    user_rows = [r for r in rows if r.get("user", "") == user_email]

    now = datetime.datetime.utcnow()
    return MyUsage(
        month=now.month,
        year=now.year,
        total_tokens=sum(r["tokens"] for r in user_rows),
        total_cost=sum(r["cost"] for r in user_rows),
    )
