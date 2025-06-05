import logging
from datetime import datetime, timedelta
from typing import Optional

from open_webui.models.users import Users
from open_webui.models.chats import Chats
from open_webui.models.messages import MessageTable

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from open_webui.utils.auth import get_admin_user
from open_webui.socket.main import get_active_status_by_user_id
from open_webui.internal.db import get_db
from sqlalchemy import func, text

log = logging.getLogger(__name__)

router = APIRouter()

class GlobalIndicators(BaseModel):
    total_users: int
    total_messages: int
    total_conversations: int

class CurrentStats(BaseModel):
    active_users: int
    model_usage: dict

class EvolutionStats(BaseModel):
    users_over_time: list[dict]
    conversations_over_time: list[dict]

class StatsResponse(BaseModel):
    global_indicators: GlobalIndicators
    current_stats: CurrentStats
    evolution_stats: EvolutionStats

@router.get("/", response_model=StatsResponse)
async def get_stats(user=Depends(get_admin_user)):
    """Get comprehensive statistics for the platform"""
    
    # Global indicators
    total_users = Users.get_num_users()
    
    # Get total conversations
    with get_db() as db:
        total_conversations = db.execute(text("SELECT COUNT(*) FROM chat")).scalar()
        
        # Get total messages by counting all messages in all chats
        # Messages are stored as JSON in the chat.chat column
        total_messages_result = db.execute(text("""
            SELECT COUNT(*)
            FROM chat, json_each(json_extract(chat, '$.history.messages'))
            WHERE json_valid(chat) = 1
        """)).scalar()
        
        total_messages = total_messages_result or 0
    
    # Current active users (users active in last 24 hours)
    current_time = int(datetime.now().timestamp())
    active_threshold = current_time - (24 * 60 * 60)  # 24 hours ago
    
    with get_db() as db:
        active_users = db.execute(text("""
            SELECT COUNT(*) FROM user 
            WHERE last_active_at > :threshold
        """), {"threshold": active_threshold}).scalar()
    
    # Model usage stats - extract from actual chat data
    with get_db() as db:
        model_usage_result = db.execute(text("""
            SELECT 
                json_extract(value, '$.model') as model,
                COUNT(*) as count
            FROM chat, json_each(json_extract(chat, '$.history.messages'))
            WHERE json_extract(value, '$.role') = 'assistant' 
            AND json_extract(value, '$.model') IS NOT NULL
            GROUP BY json_extract(value, '$.model')
            ORDER BY count DESC
        """)).fetchall()
    
    # Convert to dictionary format
    model_usage = {}
    for row in model_usage_result:
        model_name = row[0]
        count = row[1]
        if model_name:  # Only include non-null model names
            model_usage[model_name] = count
    
    # Evolution stats - users over time (last 90 days for better data visibility)
    ninety_days_ago = current_time - (90 * 24 * 60 * 60)
    
    with get_db() as db:
        users_evolution = db.execute(text("""
            SELECT 
                DATE(datetime(created_at, 'unixepoch')) as date,
                COUNT(*) as count
            FROM user 
            WHERE created_at > :threshold
            GROUP BY DATE(datetime(created_at, 'unixepoch'))
            ORDER BY date
        """), {"threshold": ninety_days_ago}).fetchall()
        
        conversations_evolution = db.execute(text("""
            SELECT 
                DATE(datetime(created_at, 'unixepoch')) as date,
                COUNT(*) as count
            FROM chat 
            WHERE created_at > :threshold
            GROUP BY DATE(datetime(created_at, 'unixepoch'))
            ORDER BY date
        """), {"threshold": ninety_days_ago}).fetchall()
    
    users_over_time = [{"date": row[0], "count": row[1]} for row in users_evolution]
    conversations_over_time = [{"date": row[0], "count": row[1]} for row in conversations_evolution]
    
    return StatsResponse(
        global_indicators=GlobalIndicators(
            total_users=total_users,
            total_messages=total_messages,
            total_conversations=total_conversations
        ),
        current_stats=CurrentStats(
            active_users=active_users,
            model_usage=model_usage
        ),
        evolution_stats=EvolutionStats(
            users_over_time=users_over_time,
            conversations_over_time=conversations_over_time
        )
    ) 