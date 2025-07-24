"""
Production-safe migration handler for mAI
Handles existing tables gracefully
"""
import logging
from typing import List
from sqlalchemy import inspect, text
from open_webui.apps.webui.internal.db import engine

log = logging.getLogger(__name__)

USAGE_TRACKING_TABLES = [
    'client_organizations',
    'user_client_mapping',
    'client_live_counters',
    'client_user_daily_usage',
    'client_model_daily_usage',
    'client_billing_summary',
    'global_settings'
]

def check_usage_tables_exist() -> bool:
    """Check if usage tracking tables exist"""
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        return any(table in existing_tables for table in USAGE_TRACKING_TABLES)
    except Exception as e:
        log.error(f"Error checking tables: {e}")
        return False

def ensure_usage_tracking_ready() -> bool:
    """Ensure usage tracking is ready for production"""
    try:
        if not check_usage_tables_exist():
            log.warning("⚠️  Usage tracking tables not found")
            return False
        
        # Verify critical tables have data
        with engine.connect() as conn:
            # Check if we have at least one organization
            result = conn.execute(text("SELECT COUNT(*) FROM client_organizations WHERE is_active = 1"))
            org_count = result.scalar()
            
            if org_count == 0:
                log.warning("⚠️  No active organizations found")
                # Auto-create default organization for single-tenant instances
                conn.execute(text("""
                    INSERT INTO client_organizations 
                    (id, name, openrouter_api_key, markup_rate, is_active, created_at, updated_at)
                    VALUES 
                    ('default-org', 'Default Organization', '', 1.3, 1, 
                     strftime('%s', 'now'), strftime('%s', 'now'))
                """))
                conn.commit()
                log.info("✅ Created default organization")
            
            return True
            
    except Exception as e:
        log.error(f"Error ensuring usage tracking: {e}")
        return False