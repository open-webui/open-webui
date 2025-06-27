from open_webui.constants import ERROR_MESSAGES
from open_webui.models.users import Users
from open_webui.models.message_metrics import MessageMetrics
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
import logging

from open_webui.utils.auth import get_metrics_user
from open_webui.env import SRC_LOG_LEVELS
from datetime import datetime

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["METRICS"])

router = APIRouter()

############################
# GetTotalPrompts
############################


@router.get("/prompts")
async def get_total_prompts(domain: str = None, user=Depends(get_metrics_user)):
    # For analyst role, enforce domain restriction
    if user.role == "analyst":
        # Force domain to user's domain for analysts
        domain = user.domain

    # Admin and global_analyst can see all domains or filter by domain

    total_prompts = (
        MessageMetrics.get_messages_number(domain)
        if domain
        else MessageMetrics.get_messages_number()
    )

    # Return 0 instead of raising a 404 error
    return {"total_prompts": total_prompts or 0}


############################
# GetDomains
############################


@router.get("/domains")
async def get_domains(user=Depends(get_metrics_user)):
    if not user.role in ["admin", "analyst", "global_analyst"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # If user is analyst, only return their domain
    if user.role == "analyst":
        return {"domains": [user.domain] if user.domain else []}

    # For admins and global_analysts, return all domains
    domains = MessageMetrics.get_domains() or []
    return {"domains": domains}


############################
# GetDailyUsers
############################


@router.get("/daily/prompts")
async def get_daily_prompts_number(domain: str = None, user=Depends(get_metrics_user)):
    # For analyst role, enforce domain restriction
    if user.role == "analyst":
        # Force domain to user's domain for analysts
        domain = user.domain

    # Admin and global_analyst can see all domains or filter by domain

    total_daily_prompts = (
        MessageMetrics.get_daily_messages_number(domain=domain)
        if domain
        else MessageMetrics.get_daily_messages_number()
    )
    return {"total_daily_prompts": total_daily_prompts}


############################
# GetTotalTokens
############################


@router.get("/tokens")
async def get_total_tokens(domain: str = None, user=Depends(get_metrics_user)):
    # For analyst role, enforce domain restriction
    if user.role == "analyst":
        # Force domain to user's domain for analysts
        domain = user.domain

    # Admin and global_analyst can see all domains or filter by domain

    total_tokens = (
        MessageMetrics.get_message_tokens_sum(domain)
        if domain
        else MessageMetrics.get_message_tokens_sum()
    )

    return {"total_tokens": total_tokens}


############################
# GetDailyTokens
############################


@router.get("/daily/tokens")
async def get_daily_tokens(domain: str = None, user=Depends(get_metrics_user)):
    # For analyst role, enforce domain restriction
    if user.role == "analyst":
        # Force domain to user's domain for analysts
        domain = user.domain

    # Admin and global_analyst can see all domains or filter by domain

    total_daily_tokens = (
        MessageMetrics.get_daily_message_tokens_sum(domain=domain)
        if domain
        else MessageMetrics.get_daily_message_tokens_sum()
    )
    return {"total_daily_tokens": total_daily_tokens}


############################
# GetHistoricalPrompts
############################


@router.get("/historical/prompts")
async def get_historical_prompts(
    days: int = 7, domain: str = None, user=Depends(get_metrics_user)
):
    # For analyst role, enforce domain restriction
    if user.role == "analyst":
        # Force domain to user's domain for analysts
        domain = user.domain

    # Admin and global_analyst can see all domains or filter by domain

    # Handle both None and empty string for domain
    if domain == "":
        domain = None

    historical_data = MessageMetrics.get_historical_messages_data(days, domain)

    return {"historical_prompts": historical_data}


############################
# GetHistoricalTokens
############################


@router.get("/historical/tokens")
async def get_historical_tokens(
    days: int = 7, domain: str = None, user=Depends(get_metrics_user)
):
    # For analyst role, enforce domain restriction
    if user.role == "analyst":
        # Force domain to user's domain for analysts
        domain = user.domain

    # Admin and global_analyst can see all domains or filter by domain

    # Handle both None and empty string for domain
    if domain == "":
        domain = None

    historical_data = MessageMetrics.get_historical_tokens_data(days, domain)

    return {"historical_tokens": historical_data}


############################
# GetModels
############################


@router.get("/models")
async def get_models(user=Depends(get_metrics_user)):
    models = MessageMetrics.get_used_models() or []
    
    # For analyst role, we should filter models by domain if needed
    # However, since this is for metrics display, analysts should see all models
    # that have been used (they'll be domain-filtered in the actual data queries)
    # This allows the dropdown to show all available models for selection
    
    return {"models": models}


############################
# GetModelPrompts
############################


@router.get("/models/prompts")
async def get_model_prompts(
    model: str = None, domain: str = None, user=Depends(get_metrics_user)
):
    # For analyst role, enforce domain restriction
    if user.role == "analyst":
        # Force domain to user's domain for analysts
        domain = user.domain

    # Admin and global_analyst can see all domains or filter by domain

    total_prompts = MessageMetrics.get_messages_number(domain, model)
    return {"total_prompts": total_prompts or 0}


############################
# GetModelDailyPrompts
############################


@router.get("/models/daily/prompts")
async def get_model_daily_prompts(
    model: str = None, domain: str = None, user=Depends(get_metrics_user)
):
    # For analyst role, enforce domain restriction
    if user.role == "analyst":
        # Force domain to user's domain for analysts
        domain = user.domain

    # Admin and global_analyst can see all domains or filter by domain

    total_daily_prompts = MessageMetrics.get_daily_messages_number(
        domain=domain, model=model
    )
    return {"total_daily_prompts": total_daily_prompts}


############################
# GetModelHistoricalPrompts
############################


@router.get("/models/historical/prompts")
async def get_model_historical_prompts(
    days: int = 7,
    model: str = None,
    domain: str = None,
    user=Depends(get_metrics_user),
):
    # For analyst role, enforce domain restriction
    if user.role == "analyst":
        # Force domain to user's domain for analysts
        domain = user.domain

    # Admin and global_analyst can see all domains or filter by domain

    # Handle both None and empty string
    if domain == "":
        domain = None
    if model == "":
        model = None

    historical_data = MessageMetrics.get_historical_messages_data(days, domain, model)

    return {"historical_prompts": historical_data}


############################
# GetHistoricalDailyUsers
############################


@router.get("/historical/users/daily")
async def get_historical_daily_users(
    days: int = 7,
    model: str = None,
    domain: str = None,
    user=Depends(get_metrics_user),
):
    if user.role in ["admin", "global_analyst"]:
        domain_to_use = domain if domain != "" else None
    elif user.role == "analyst":
        domain_to_use = user.domain
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    historical_daily_data = MessageMetrics.get_historical_daily_users(
        days, domain_to_use, model
    )

    return {"historical_daily_users": historical_daily_data}


############################
# Date Range Metrics
############################


@router.get("/range/users")
async def get_range_metrics(
    start_date: str,
    end_date: str,
    domain: str = None,
    model: str = None,
    user=Depends(get_metrics_user),
):
    """Get metrics for a specific date range"""
    # For analyst role, enforce domain restriction
    if user.role == "analyst":
        # Force domain to user's domain for analysts
        domain = user.domain

    # Admin and global_analyst can see all domains or filter by domain

    try:
        # Convert dates to timestamps
        start_timestamp = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        end_timestamp = (
            int(datetime.strptime(end_date, "%Y-%m-%d").timestamp()) + 86400
        )  # End of day

        # Calculate total number of days in range for averaging
        days_in_range = (end_timestamp - start_timestamp) // 86400

        # Get metrics for date range
        users_data = Users.get_range_metrics(start_timestamp, end_timestamp, domain)
        prompts_data = MessageMetrics.get_range_metrics(
            start_timestamp, end_timestamp, domain, model
        )

        # Calculate averages
        avg_daily_users = (
            users_data["total_users"] / days_in_range if days_in_range > 0 else 0
        )
        avg_daily_prompts = (
            prompts_data["total_prompts"] / days_in_range if days_in_range > 0 else 0
        )
        avg_tokens_per_prompt = (
            prompts_data["total_tokens"] / prompts_data["total_prompts"]
            if prompts_data["total_prompts"] > 0
            else 0
        )

        # Calculate growth rates if previous period data is available
        prev_start = start_timestamp - (end_timestamp - start_timestamp)
        prev_end = start_timestamp
        prev_users_data = Users.get_range_metrics(prev_start, prev_end, domain)
        prev_prompts_data = MessageMetrics.get_range_metrics(
            prev_start, prev_end, domain, model
        )

        user_growth = (
            (
                (users_data["total_users"] - prev_users_data["total_users"])
                / prev_users_data["total_users"]
            )
            * 100
            if prev_users_data["total_users"] > 0
            else 0
        )
        prompt_growth = (
            (
                (prompts_data["total_prompts"] - prev_prompts_data["total_prompts"])
                / prev_prompts_data["total_prompts"]
            )
            * 100
            if prev_prompts_data["total_prompts"] > 0
            else 0
        )

        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "days": days_in_range,
            },
            "metrics": {
                "total_users": users_data["total_users"],
                "total_prompts": prompts_data["total_prompts"],
                "total_tokens": prompts_data["total_tokens"],
                "active_users": users_data["active_users"],
            },
            "averages": {
                "avg_daily_users": round(avg_daily_users, 2),
                "avg_daily_prompts": round(avg_daily_prompts, 2),
                "avg_tokens_per_prompt": round(avg_tokens_per_prompt, 2),
                "avg_prompts_per_user": (
                    round(prompts_data["total_prompts"] / users_data["active_users"], 2)
                    if users_data["active_users"] > 0
                    else 0
                ),
            },
            "growth": {
                "user_growth_percent": round(user_growth, 2),
                "prompt_growth_percent": round(prompt_growth, 2),
            },
        }
    except Exception as e:
        log.exception(f"Error getting range metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get range metrics: {str(e)}",
        )
