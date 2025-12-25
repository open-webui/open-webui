"""
Analytics Router for Token Usage "Wrapped" Feature

Provides API endpoints for:
- Per-conversation token stats (for chat UI display)
- User wrapped summary and heatmap data
- Global/site-wide analytics (admin only)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from open_webui.models.analytics import (
    Analytics,
    ConversationTokenUsageResponse,
    HeatmapResponse,
    ModelUsageResponse,
    TopChatResponse,
    WrappedSummaryResponse,
    GlobalWrappedResponse,
)
from open_webui.models.chats import Chats
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_admin_user, get_verified_user

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


############################
# Conversation Token Stats
############################


@router.get("/chat/{chat_id}", response_model=Optional[ConversationTokenUsageResponse])
async def get_chat_token_stats(chat_id: str, user=Depends(get_verified_user)):
    """
    Get token usage statistics for a specific conversation.
    
    Returns:
    - total_input_tokens: Total input tokens for all messages
    - total_output_tokens: Total output tokens for all messages
    - total_tokens: Combined total
    - last_input_tokens: Input tokens for most recent message
    - last_output_tokens: Output tokens for most recent message
    - message_count: Number of message exchanges
    
    Used to display token stats next to model name in chat UI.
    """
    # Verify user has access to this chat
    chat = Chats.get_chat_by_id_and_user_id(chat_id, user.id)
    if not chat and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    # Admin can access any chat
    if not chat and user.role == "admin":
        chat = Chats.get_chat_by_id(chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )
    
    stats = Analytics.get_conversation_token_usage(chat_id)
    
    # Return empty stats if no token data yet
    if not stats:
        return ConversationTokenUsageResponse(
            chat_id=chat_id,
            user_id=user.id,
            total_input_tokens=0,
            total_output_tokens=0,
            total_tokens=0,
            last_input_tokens=0,
            last_output_tokens=0,
            message_count=0,
            created_at=0,
            updated_at=0,
        )
    
    return stats


############################
# User Wrapped Data
############################


@router.get("/user/wrapped", response_model=WrappedSummaryResponse)
async def get_user_wrapped(
    year: Optional[int] = None,
    user=Depends(get_verified_user)
):
    """
    Get comprehensive "Wrapped" summary for the authenticated user.
    
    Includes:
    - Total conversations, messages, and tokens
    - Days active
    - Most active day with details
    - Favorite (most-used) model
    - Top 10 chats by token count
    
    Args:
        year: Optional year to filter (defaults to current year)
    """
    if year is None:
        year = datetime.now(timezone.utc).year
    
    wrapped = Analytics.get_user_wrapped(user.id, year)
    
    # Enrich top chats with titles from Chats table
    enriched_chats = []
    for chat in wrapped.top_chats:
        chat_data = Chats.get_chat_by_id(chat.chat_id)
        title = chat_data.title if chat_data else None
        enriched_chats.append(TopChatResponse(
            chat_id=chat.chat_id,
            title=title,
            model_id=chat.model_id,
            total_tokens=chat.total_tokens,
            total_input_tokens=chat.total_input_tokens,
            total_output_tokens=chat.total_output_tokens,
            message_count=chat.message_count,
        ))
    
    wrapped.top_chats = enriched_chats
    return wrapped


@router.get("/user/heatmap", response_model=HeatmapResponse)
async def get_user_heatmap(
    year: Optional[int] = None,
    user=Depends(get_verified_user)
):
    """
    Get activity heatmap data for the authenticated user.
    
    Returns daily token counts for all days in the specified year,
    with intensity levels (0-4) for visualization.
    
    Similar to GitHub's contribution graph.
    
    Args:
        year: Optional year (defaults to current year)
    """
    if year is None:
        year = datetime.now(timezone.utc).year
    
    return Analytics.get_heatmap_data(user.id, year)


@router.get("/user/models", response_model=list[ModelUsageResponse])
async def get_user_model_usage(
    year: Optional[int] = None,
    user=Depends(get_verified_user)
):
    """
    Get per-model token usage breakdown for the authenticated user.
    
    Returns list of models used with:
    - Token counts (input, output, total)
    - Usage counts (conversations, messages)
    - Percentage of total usage
    
    Sorted by total tokens descending.
    """
    return Analytics.get_model_usage_by_user(user.id, year)


@router.get("/user/top-chats", response_model=list[TopChatResponse])
async def get_user_top_chats(
    year: Optional[int] = None,
    limit: int = 10,
    user=Depends(get_verified_user)
):
    """
    Get user's top conversations by token count.
    
    Args:
        year: Optional year filter
        limit: Max results (default 10)
    """
    chats = Analytics.get_top_chats_by_user(user.id, year, limit)
    
    # Enrich with chat titles
    enriched = []
    for chat in chats:
        chat_data = Chats.get_chat_by_id(chat.chat_id)
        title = chat_data.title if chat_data else None
        enriched.append(TopChatResponse(
            chat_id=chat.chat_id,
            title=title,
            model_id=chat.model_id,
            total_tokens=chat.total_tokens,
            total_input_tokens=chat.total_input_tokens,
            total_output_tokens=chat.total_output_tokens,
            message_count=chat.message_count,
        ))
    
    return enriched


############################
# Global/Admin Analytics
############################


@router.get("/global/wrapped", response_model=GlobalWrappedResponse)
async def get_global_wrapped(
    year: Optional[int] = None,
    user=Depends(get_admin_user)
):
    """
    Get site-wide "Wrapped" statistics.
    
    Admin only endpoint.
    
    Includes:
    - Total active users
    - Total conversations and messages
    - Total tokens processed
    - Top models by usage
    - Busiest day
    """
    if year is None:
        year = datetime.now(timezone.utc).year
    
    return Analytics.get_global_wrapped(year)


@router.get("/global/models", response_model=list[ModelUsageResponse])
async def get_global_model_usage(
    limit: int = 20,
    user=Depends(get_admin_user)
):
    """
    Get site-wide model usage breakdown.
    
    Admin only endpoint.
    
    Returns top models by total token count with percentages.
    """
    return Analytics.get_global_model_usage(limit)


@router.get("/global/heatmap", response_model=HeatmapResponse)
async def get_global_heatmap(
    year: Optional[int] = None,
    user=Depends(get_admin_user)
):
    """
    Get site-wide activity heatmap data.
    
    Admin only endpoint.
    
    Aggregates all users' activity for the specified year.
    Note: This uses a special "global" user_id internally.
    """
    if year is None:
        year = datetime.now(timezone.utc).year
    
    # For global heatmap, we need to aggregate across all users
    # We'll use a special method or aggregate from daily_token_usage
    try:
        from open_webui.internal.db import get_db
        from open_webui.models.analytics import DailyTokenUsage, HeatmapDataPoint
        from sqlalchemy import func
        from datetime import timedelta
        
        with get_db() as db:
            year_start = f"{year}-01-01"
            year_end = f"{year}-12-31"
            
            # Aggregate all users' daily data
            daily_totals = db.query(
                DailyTokenUsage.date,
                func.sum(DailyTokenUsage.total_tokens).label('total')
            ).filter(
                DailyTokenUsage.date >= year_start,
                DailyTokenUsage.date <= year_end
            ).group_by(DailyTokenUsage.date).all()
            
            # Build date -> tokens map
            date_tokens = {row.date: row.total for row in daily_totals}
            max_tokens = max(date_tokens.values()) if date_tokens else 0
            
            # Calculate levels
            def calculate_level(tokens: int) -> int:
                if tokens == 0:
                    return 0
                if max_tokens == 0:
                    return 0
                ratio = tokens / max_tokens
                if ratio < 0.25:
                    return 1
                elif ratio < 0.5:
                    return 2
                elif ratio < 0.75:
                    return 3
                else:
                    return 4
            
            # Generate all days
            data_points = []
            current_date = datetime(year, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(year, 12, 31, tzinfo=timezone.utc)
            
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                tokens = date_tokens.get(date_str, 0)
                data_points.append(HeatmapDataPoint(
                    date=date_str,
                    tokens=tokens,
                    level=calculate_level(tokens)
                ))
                current_date += timedelta(days=1)
            
            return HeatmapResponse(
                year=year,
                data=data_points,
                max_tokens=max_tokens,
                total_days_active=len([d for d in data_points if d.tokens > 0])
            )
    except Exception as e:
        log.error(f"Error getting global heatmap: {e}")
        return HeatmapResponse(year=year, data=[], max_tokens=0, total_days_active=0)
