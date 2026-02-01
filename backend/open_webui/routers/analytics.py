from typing import Optional
import logging
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from open_webui.models.chat_messages import ChatMessages, ChatMessageModel
from open_webui.utils.auth import get_admin_user
from open_webui.internal.db import get_session
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)


router = APIRouter()


####################
# Response Models
####################


class ModelAnalyticsEntry(BaseModel):
    model_id: str
    count: int


class ModelAnalyticsResponse(BaseModel):
    models: list[ModelAnalyticsEntry]


class UserAnalyticsEntry(BaseModel):
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    count: int


class UserAnalyticsResponse(BaseModel):
    users: list[UserAnalyticsEntry]


####################
# Endpoints
####################


@router.get("/models", response_model=ModelAnalyticsResponse)
async def get_model_analytics(
    start_date: Optional[int] = Query(None, description="Start timestamp (epoch)"),
    end_date: Optional[int] = Query(None, description="End timestamp (epoch)"),
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get message counts per model."""
    counts = ChatMessages.get_message_count_by_model(
        start_date=start_date, end_date=end_date, db=db
    )
    models = [
        ModelAnalyticsEntry(model_id=model_id, count=count)
        for model_id, count in sorted(counts.items(), key=lambda x: -x[1])
    ]
    return ModelAnalyticsResponse(models=models)


@router.get("/users", response_model=UserAnalyticsResponse)
async def get_user_analytics(
    start_date: Optional[int] = Query(None, description="Start timestamp (epoch)"),
    end_date: Optional[int] = Query(None, description="End timestamp (epoch)"),
    limit: int = Query(50, description="Max users to return"),
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get message counts per user with user info."""
    from open_webui.models.users import Users
    
    counts = ChatMessages.get_message_count_by_user(
        start_date=start_date, end_date=end_date, db=db
    )
    
    # Get user info for top users
    top_user_ids = [uid for uid, _ in sorted(counts.items(), key=lambda x: -x[1])[:limit]]
    user_info = {u.id: u for u in Users.get_users_by_user_ids(top_user_ids, db=db)}
    
    users = []
    for user_id in top_user_ids:
        u = user_info.get(user_id)
        users.append(UserAnalyticsEntry(
            user_id=user_id,
            name=u.name if u else None,
            email=u.email if u else None,
            count=counts[user_id]
        ))
    
    return UserAnalyticsResponse(users=users)


@router.get("/messages", response_model=list[ChatMessageModel])
async def get_messages(
    model_id: Optional[str] = Query(None, description="Filter by model ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    chat_id: Optional[str] = Query(None, description="Filter by chat ID"),
    start_date: Optional[int] = Query(None, description="Start timestamp (epoch)"),
    end_date: Optional[int] = Query(None, description="End timestamp (epoch)"),
    skip: int = Query(0),
    limit: int = Query(50, le=100),
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Query messages with filters."""
    if chat_id:
        return ChatMessages.get_messages_by_chat_id(chat_id=chat_id, db=db)
    elif model_id:
        return ChatMessages.get_messages_by_model_id(
            model_id=model_id,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit,
            db=db,
        )
    elif user_id:
        return ChatMessages.get_messages_by_user_id(
            user_id=user_id, skip=skip, limit=limit, db=db
        )
    else:
        # Return empty if no filter specified
        return []


class SummaryResponse(BaseModel):
    total_messages: int
    total_chats: int
    total_models: int
    total_users: int


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    start_date: Optional[int] = Query(None, description="Start timestamp (epoch)"),
    end_date: Optional[int] = Query(None, description="End timestamp (epoch)"),
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get summary statistics for the dashboard."""
    model_counts = ChatMessages.get_message_count_by_model(
        start_date=start_date, end_date=end_date, db=db
    )
    user_counts = ChatMessages.get_message_count_by_user(
        start_date=start_date, end_date=end_date, db=db
    )
    chat_counts = ChatMessages.get_message_count_by_chat(
        start_date=start_date, end_date=end_date, db=db
    )
    
    return SummaryResponse(
        total_messages=sum(model_counts.values()),
        total_chats=len(chat_counts),
        total_models=len(model_counts),
        total_users=len(user_counts),
    )


class DailyStatsEntry(BaseModel):
    date: str
    models: dict[str, int]


class DailyStatsResponse(BaseModel):
    data: list[DailyStatsEntry]


@router.get("/daily", response_model=DailyStatsResponse)
async def get_daily_stats(
    start_date: Optional[int] = Query(None, description="Start timestamp (epoch)"),
    end_date: Optional[int] = Query(None, description="End timestamp (epoch)"),
    granularity: str = Query("daily", description="Granularity: 'hourly' or 'daily'"),
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get message counts grouped by model for time-series chart."""
    if granularity == "hourly":
        counts = ChatMessages.get_hourly_message_counts_by_model(
            start_date=start_date, end_date=end_date, db=db
        )
    else:
        counts = ChatMessages.get_daily_message_counts_by_model(
            start_date=start_date, end_date=end_date, db=db
        )
    return DailyStatsResponse(
        data=[
            DailyStatsEntry(date=date, models=models)
            for date, models in sorted(counts.items())
        ]
    )


class TokenUsageEntry(BaseModel):
    model_id: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    message_count: int


class TokenUsageResponse(BaseModel):
    models: list[TokenUsageEntry]
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int


@router.get("/tokens", response_model=TokenUsageResponse)
async def get_token_usage(
    start_date: Optional[int] = Query(None),
    end_date: Optional[int] = Query(None),
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get token usage aggregated by model."""
    usage = ChatMessages.get_token_usage_by_model(
        start_date=start_date, end_date=end_date, db=db
    )

    models = [
        TokenUsageEntry(model_id=model_id, **data)
        for model_id, data in sorted(usage.items(), key=lambda x: -x[1]["total_tokens"])
    ]

    total_input = sum(m.input_tokens for m in models)
    total_output = sum(m.output_tokens for m in models)

    return TokenUsageResponse(
        models=models,
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_tokens=total_input + total_output,
    )
