from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from open_webui.models.chat_messages import ChatMessages, ChatMessageModel
from open_webui.models.chats import Chats
from open_webui.models.groups import Groups
from open_webui.models.users import Users
from open_webui.models.feedbacks import Feedbacks
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
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class UserAnalyticsResponse(BaseModel):
    users: list[UserAnalyticsEntry]


####################
# Endpoints
####################


@router.get("/models", response_model=ModelAnalyticsResponse)
async def get_model_analytics(
    start_date: Optional[int] = Query(None, description="Start timestamp (epoch)"),
    end_date: Optional[int] = Query(None, description="End timestamp (epoch)"),
    group_id: Optional[str] = Query(None, description="Filter by user group ID"),
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get message counts per model."""
    counts = ChatMessages.get_message_count_by_model(
        start_date=start_date, end_date=end_date, group_id=group_id, db=db
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
    group_id: Optional[str] = Query(None, description="Filter by user group ID"),
    limit: int = Query(50, description="Max users to return"),
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get message counts and token usage per user with user info."""
    counts = ChatMessages.get_message_count_by_user(
        start_date=start_date, end_date=end_date, group_id=group_id, db=db
    )
    token_usage = ChatMessages.get_token_usage_by_user(
        start_date=start_date, end_date=end_date, db=db
    )

    # Get user info for top users
    top_user_ids = [
        uid for uid, _ in sorted(counts.items(), key=lambda x: -x[1])[:limit]
    ]
    user_info = {u.id: u for u in Users.get_users_by_user_ids(top_user_ids, db=db)}

    users = []
    for user_id in top_user_ids:
        u = user_info.get(user_id)
        tokens = token_usage.get(user_id, {})
        users.append(
            UserAnalyticsEntry(
                user_id=user_id,
                name=u.name if u else None,
                email=u.email if u else None,
                count=counts[user_id],
                input_tokens=tokens.get("input_tokens", 0),
                output_tokens=tokens.get("output_tokens", 0),
                total_tokens=tokens.get("total_tokens", 0),
            )
        )

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
    group_id: Optional[str] = Query(None, description="Filter by user group ID"),
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get summary statistics for the dashboard."""
    model_counts = ChatMessages.get_message_count_by_model(
        start_date=start_date, end_date=end_date, group_id=group_id, db=db
    )
    user_counts = ChatMessages.get_message_count_by_user(
        start_date=start_date, end_date=end_date, group_id=group_id, db=db
    )
    chat_counts = ChatMessages.get_message_count_by_chat(
        start_date=start_date, end_date=end_date, group_id=group_id, db=db
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
    group_id: Optional[str] = Query(None, description="Filter by user group ID"),
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
            start_date=start_date, end_date=end_date, group_id=group_id, db=db
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
    group_id: Optional[str] = Query(None, description="Filter by user group ID"),
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get token usage aggregated by model."""
    usage = ChatMessages.get_token_usage_by_model(
        start_date=start_date, end_date=end_date, group_id=group_id, db=db
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


####################
# Model Chats Browser
####################


class ModelChatEntry(BaseModel):
    chat_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    first_message: Optional[str] = None
    updated_at: int


class ModelChatsResponse(BaseModel):
    chats: list[ModelChatEntry]
    total: int


@router.get("/models/{model_id}/chats", response_model=ModelChatsResponse)
async def get_model_chats(
    model_id: str,
    start_date: Optional[int] = Query(None),
    end_date: Optional[int] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50, le=100),
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get chats that used a specific model, with preview and feedback info."""

    # Get chat IDs that used this model
    chat_ids = ChatMessages.get_chat_ids_by_model_id(
        model_id=model_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
        db=db,
    )

    if not chat_ids:
        return ModelChatsResponse(chats=[], total=0)

    # Get chat details from messages only
    chats_data = []
    for chat_id in chat_ids:
        messages = ChatMessages.get_messages_by_chat_id(chat_id, db=db)
        if not messages:
            continue

        # Get user_id from first user message
        first_user_msg = next((m for m in messages if m.role == "user"), None)
        user_id = first_user_msg.user_id if first_user_msg else None

        # Extract first message content as preview
        first_message = None
        if first_user_msg and first_user_msg.content:
            content = first_user_msg.content
            if isinstance(content, str):
                first_message = content[:200]
            elif isinstance(content, list):
                text_parts = [b.get("text", "") for b in content if isinstance(b, dict)]
                first_message = " ".join(text_parts)[:200]

        # Get user info
        user_name = None
        if user_id:
            user_info = Users.get_user_by_id(user_id, db=db)
            user_name = user_info.name if user_info else None

        # Timestamps from messages
        updated_at = max(m.created_at for m in messages) if messages else 0

        chats_data.append(
            ModelChatEntry(
                chat_id=chat_id,
                user_id=user_id,
                user_name=user_name,
                first_message=first_message,
                updated_at=updated_at,
            )
        )

    return ModelChatsResponse(chats=chats_data, total=len(chats_data))


####################
# Model Overview
####################


class HistoryEntry(BaseModel):
    date: str
    won: int = 0
    lost: int = 0


class TagEntry(BaseModel):
    tag: str
    count: int


class ModelOverviewResponse(BaseModel):
    history: list[HistoryEntry]
    tags: list[TagEntry]


@router.get("/models/{model_id}/overview", response_model=ModelOverviewResponse)
async def get_model_overview(
    model_id: str,
    days: int = Query(30, description="Number of days of history (0 for all)"),
    user=Depends(get_admin_user),
    db: Session = Depends(get_session),
):
    """Get model overview with feedback history and chat tags."""

    # Get chat IDs that used this model
    chat_ids = ChatMessages.get_chat_ids_by_model_id(
        model_id=model_id,
        start_date=None,
        end_date=None,
        skip=0,
        limit=10000,  # Get all chats
        db=db,
    )

    # Get feedback history per day
    history_counts: dict[str, dict] = defaultdict(lambda: {"won": 0, "lost": 0})

    # Calculate start date for history
    now = datetime.now()
    start_dt = None
    if days > 0:
        start_dt = now - timedelta(days=days)

    for chat_id in chat_ids:
        feedbacks = Feedbacks.get_feedbacks_by_chat_id(chat_id, db=db)
        for fb in feedbacks:
            if fb.data and "rating" in fb.data:
                rating = fb.data["rating"]
                fb_date = datetime.fromtimestamp(fb.created_at)

                # Filter by date range
                if start_dt and fb_date < start_dt:
                    continue

                date_str = fb_date.strftime("%Y-%m-%d")
                if rating == 1:
                    history_counts[date_str]["won"] += 1
                elif rating == -1:
                    history_counts[date_str]["lost"] += 1

    # Fill in missing days
    history = []
    if history_counts or days > 0:
        end_dt = now
        if days > 0:
            current = start_dt
        elif history_counts:
            # Find earliest date
            min_date = min(history_counts.keys())
            current = datetime.strptime(min_date, "%Y-%m-%d")
        else:
            current = now

        while current <= end_dt:
            date_str = current.strftime("%Y-%m-%d")
            counts = history_counts.get(date_str, {"won": 0, "lost": 0})
            history.append(
                HistoryEntry(
                    date=date_str,
                    won=counts["won"],
                    lost=counts["lost"],
                )
            )
            current += timedelta(days=1)

    # Get chat tags
    tag_counts: dict[str, int] = defaultdict(int)
    for chat_id in chat_ids:
        chat = Chats.get_chat_by_id(chat_id, db=db)
        if chat and chat.meta:
            for tag in chat.meta.get("tags", []):
                tag_counts[tag] += 1

    # Sort by count and take top 10
    tags = [
        TagEntry(tag=tag, count=count)
        for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:10]
    ]

    return ModelOverviewResponse(history=history, tags=tags)
