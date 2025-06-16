import logging
from datetime import datetime

from open_webui.models.users import Users

from fastapi import APIRouter
from pydantic import BaseModel

from open_webui.internal.db import get_db
from sqlalchemy import text

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

def get_json_count_query():
    """Return the SQL query to count messages in all chats for PostgreSQL."""
    return """
        SELECT COUNT(*)
        FROM chat, LATERAL jsonb_array_elements(chat::jsonb->'history'->'messages') AS msg
        WHERE chat::jsonb ? 'history' 
        AND chat::jsonb->'history' ? 'messages'
        AND jsonb_typeof(chat::jsonb->'history'->'messages') = 'array'
    """

def get_model_usage_query():
    """Return the SQL query to count model usage for PostgreSQL."""
    return """
        SELECT 
            msg->>'model' as model,
            COUNT(*) as count
        FROM chat, LATERAL jsonb_array_elements(chat::jsonb->'history'->'messages') AS msg
        WHERE chat::jsonb ? 'history' 
        AND chat::jsonb->'history' ? 'messages'
        AND jsonb_typeof(chat::jsonb->'history'->'messages') = 'array'
        AND msg->>'role' = 'assistant' 
        AND msg ? 'model'
        GROUP BY msg->>'model'
        ORDER BY count DESC
    """

def get_users_evolution_query():
    """Return the SQL query for users evolution for PostgreSQL."""
    return """
        SELECT 
            DATE(to_timestamp(created_at)) as date,
            COUNT(*) as count
        FROM "user" 
        WHERE created_at > :threshold
        GROUP BY DATE(to_timestamp(created_at))
        ORDER BY date
    """

def get_conversations_evolution_query():
    """Return the SQL query for conversations evolution for PostgreSQL."""
    return """
        SELECT 
            DATE(to_timestamp(created_at)) as date,
            COUNT(*) as count
        FROM chat 
        WHERE created_at > :threshold
        GROUP BY DATE(to_timestamp(created_at))
        ORDER BY date
    """

@router.get("/", response_model=StatsResponse)
async def get_stats():
    """Get comprehensive statistics for the platform - publicly accessible"""
    
    # Global indicators
    total_users = Users.get_num_users()
    
    # Get total conversations
    with get_db() as db:
        total_conversations = db.execute(text("SELECT COUNT(*) FROM chat")).scalar()
        
        # Get total messages by counting all messages in all chats
        try:
            total_messages_result = db.execute(text(get_json_count_query())).scalar()
        except Exception as e:
            log.error(f"Error counting messages: {e}")
            total_messages_result = 0
        total_messages = total_messages_result or 0
    
    # Current active users (users active in last 24 hours)
    current_time = int(datetime.now().timestamp())
    active_threshold = current_time - (24 * 60 * 60)  # 24 hours ago
    
    with get_db() as db:
        try:
            active_users_query = '''
                SELECT COUNT(*) FROM "user" 
                WHERE last_active_at > :threshold
            '''
            active_users = db.execute(text(active_users_query), {"threshold": active_threshold}).scalar()
        except Exception as e:
            log.error(f"Error counting active users: {e}")
            active_users = 0
    
    # Model usage stats - extract from actual chat data
    with get_db() as db:
        try:
            model_usage_result = db.execute(text(get_model_usage_query())).fetchall()
        except Exception as e:
            log.error(f"Error getting model usage: {e}")
            model_usage_result = []
    
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
        try:
            users_evolution = db.execute(text(get_users_evolution_query()), {"threshold": ninety_days_ago}).fetchall()
        except Exception as e:
            log.error(f"Error getting users evolution: {e}")
            users_evolution = []
            
        try:
            conversations_evolution = db.execute(text(get_conversations_evolution_query()), {"threshold": ninety_days_ago}).fetchall()
        except Exception as e:
            log.error(f"Error getting conversations evolution: {e}")
            conversations_evolution = []
    
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