"""
Automatic database initialization for environment-based usage tracking
"""

import os
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from open_webui.internal.db import get_db
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


async def initialize_usage_tracking_from_environment() -> bool:
    """
    Initialize client organization and usage tracking tables from environment variables.
    This ensures the database is ready for usage tracking on container startup.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    # Get environment variables
    openrouter_external_user = os.getenv("OPENROUTER_EXTERNAL_USER")
    organization_name = os.getenv("ORGANIZATION_NAME")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not all([openrouter_external_user, organization_name, openrouter_api_key]):
        log.debug("Environment-based usage tracking not configured (missing required env vars)")
        return False
    
    log.info(f"🔧 Initializing usage tracking for organization: {organization_name}")
    
    try:
        # Use the database context manager
        with get_db() as db:
            # STEP 1: Ensure usage tracking tables exist FIRST (before any queries)
            await ensure_usage_tracking_tables(db)
            
            # STEP 2: Now safely check if client organization already exists
            existing_org = db.execute(
                text("SELECT id FROM client_organizations WHERE id = :org_id"),
                {"org_id": openrouter_external_user}
            ).fetchone()
            
            if existing_org:
                log.debug(f"Client organization already exists: {openrouter_external_user}")
                # Update the API key in case it changed
                import time
                db.execute(
                    text("""
                        UPDATE client_organizations 
                        SET openrouter_api_key = :api_key, 
                            name = :name,
                            updated_at = :updated_at
                        WHERE id = :org_id
                    """),
                    {
                        "api_key": openrouter_api_key,
                        "name": organization_name,
                        "updated_at": int(time.time()),
                        "org_id": openrouter_external_user
                    }
                )
            else:
                # Create new client organization
                log.info(f"Creating new client organization: {openrouter_external_user}")
                import time
                current_time = int(time.time())
                
                db.execute(
                    text("""
                        INSERT INTO client_organizations 
                        (id, name, openrouter_api_key, openrouter_key_hash, markup_rate, 
                         monthly_limit, billing_email, timezone, is_active, created_at, updated_at)
                        VALUES (:id, :name, :api_key, :key_hash, :markup_rate, 
                                :monthly_limit, :billing_email, :timezone, :is_active, :created_at, :updated_at)
                    """),
                    {
                        "id": openrouter_external_user,
                        "name": organization_name,
                        "api_key": openrouter_api_key,
                        "key_hash": None,  # Will be populated later if needed
                        "markup_rate": 1.3,  # Default mAI markup rate
                        "monthly_limit": None,  # No limit by default
                        "billing_email": None,  # Can be set later
                        "timezone": "Europe/Warsaw",  # Default for Polish SMEs
                        "is_active": 1,
                        "created_at": current_time,
                        "updated_at": current_time
                    }
                )
            
            db.commit()
            log.info(f"✅ Usage tracking initialized for {organization_name} ({openrouter_external_user})")
            return True
            
    except Exception as e:
        log.error(f"Failed to initialize usage tracking: {e}")
        return False


def _ensure_correct_table_schema(db: Session) -> None:
    """
    Ensure tables have correct schema by checking and recreating if needed.
    This handles the case where tables were created with wrong schema by other processes.
    """
    try:
        # Check if client_model_daily_usage exists with wrong schema
        result = db.execute(text("PRAGMA table_info(client_model_daily_usage)")).fetchall()
        if result:
            # Check if id column has wrong type (should be TEXT, not INTEGER)
            id_column = next((col for col in result if col[1] == 'id'), None)
            if id_column and id_column[2] == 'INTEGER':
                log.info("⚠️  Detected usage tables with incorrect schema, recreating with proper schema...")
                
                # Drop tables that need schema fixes (in dependency order)
                tables_to_recreate = [
                    'client_user_daily_usage',
                    'client_model_daily_usage', 
                    'client_daily_usage'
                ]
                
                for table in tables_to_recreate:
                    db.execute(text(f"DROP TABLE IF EXISTS {table}"))
                
                db.commit()
                log.info("✅ Dropped old tables with incorrect schema")
                
    except Exception as e:
        log.warning(f"Schema check failed, will create tables normally: {e}")

async def ensure_usage_tracking_tables(db: Session) -> None:
    """
    Ensure all required usage tracking tables exist with proper schema.
    Creates complete database schema for full usage tracking functionality.
    This is idempotent - safe to run multiple times and handles schema updates.
    """
    try:
        # First, ensure correct schema by checking existing tables
        _ensure_correct_table_schema(db)
        # 1. Global Settings - for system-wide configuration
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS global_settings (
                id TEXT PRIMARY KEY,
                openrouter_provisioning_key TEXT,
                default_markup_rate REAL DEFAULT 1.3,
                billing_currency TEXT DEFAULT 'USD',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """))
        
        # 2. Client Organizations - core client management
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS client_organizations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                openrouter_api_key TEXT NOT NULL UNIQUE,
                openrouter_key_hash TEXT,
                markup_rate REAL DEFAULT 1.3,
                monthly_limit REAL,
                billing_email TEXT,
                timezone TEXT DEFAULT 'Europe/Warsaw',
                is_active INTEGER DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """))
        
        # 3. User-Client Mapping - for database-based client assignment
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS user_client_mapping (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                client_org_id TEXT NOT NULL,
                openrouter_user_id TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (client_org_id) REFERENCES client_organizations(id)
            )
        """))
        
        # 4. Client Daily Usage - overall daily summaries per client
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS client_daily_usage (
                id TEXT PRIMARY KEY,
                client_org_id TEXT NOT NULL,
                usage_date DATE NOT NULL,
                total_tokens INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                raw_cost REAL DEFAULT 0.0,
                markup_cost REAL DEFAULT 0.0,
                primary_model TEXT,
                unique_users INTEGER DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (client_org_id) REFERENCES client_organizations(id)
            )
        """))
        
        # 5. Client User Daily Usage - per-user daily summaries
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS client_user_daily_usage (
                id TEXT PRIMARY KEY,
                client_org_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                usage_date DATE NOT NULL,
                openrouter_user_id TEXT NOT NULL,
                total_tokens INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                raw_cost REAL DEFAULT 0.0,
                markup_cost REAL DEFAULT 0.0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (client_org_id) REFERENCES client_organizations(id)
            )
        """))
        
        # 6. Client Model Daily Usage - per-model daily summaries
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS client_model_daily_usage (
                id TEXT PRIMARY KEY,
                client_org_id TEXT NOT NULL,
                model_name TEXT NOT NULL,
                provider TEXT,
                usage_date DATE NOT NULL,
                total_tokens INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                raw_cost REAL DEFAULT 0.0,
                markup_cost REAL DEFAULT 0.0,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (client_org_id) REFERENCES client_organizations(id)
            )
        """))
        
        
        # 8. Processed Generations - deduplication tracking
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS processed_generations (
                id TEXT PRIMARY KEY,
                client_org_id TEXT NOT NULL,
                generation_date DATE NOT NULL,
                processed_at INTEGER NOT NULL,
                total_cost REAL NOT NULL,
                total_tokens INTEGER NOT NULL,
                FOREIGN KEY (client_org_id) REFERENCES client_organizations(id)
            )
        """))
        
        # 9. Processed Generation Cleanup Log - audit trail
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS processed_generation_cleanup_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cleanup_date DATE NOT NULL,
                cutoff_date DATE NOT NULL,
                days_retained INTEGER NOT NULL,
                records_before INTEGER NOT NULL,
                records_deleted INTEGER NOT NULL,
                records_remaining INTEGER NOT NULL,
                old_tokens_removed INTEGER NOT NULL,
                old_cost_removed REAL NOT NULL,
                storage_saved_kb REAL NOT NULL,
                cleanup_duration_seconds REAL NOT NULL,
                success INTEGER NOT NULL DEFAULT 1,
                error_message TEXT,
                created_at INTEGER NOT NULL
            )
        """))
        
        # Create indexes for optimal query performance
        _create_usage_tracking_indexes(db)
        
        log.info("✅ Simplified usage tracking database schema created/verified (8 tables)")
        
    except Exception as e:
        log.error(f"Error ensuring usage tracking tables: {e}")
        raise


def _create_usage_tracking_indexes(db: Session) -> None:
    """Create all required indexes for usage tracking tables"""
    
    # Client Organizations indexes
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_api_key ON client_organizations(openrouter_api_key)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_active ON client_organizations(is_active)"))
    
    # User-Client Mapping indexes  
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_user_id ON user_client_mapping(user_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_client_org_id ON user_client_mapping(client_org_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_openrouter_user_id ON user_client_mapping(openrouter_user_id)"))
    
    # Client Daily Usage indexes
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_daily_client_date ON client_daily_usage(client_org_id, usage_date)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_daily_usage_date ON client_daily_usage(usage_date)"))
    
    # Client User Daily Usage indexes
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_user_daily_client_user_date ON client_user_daily_usage(client_org_id, user_id, usage_date)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_user_daily_user_date ON client_user_daily_usage(user_id, usage_date)"))
    
    # Client Model Daily Usage indexes
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_model_daily_client_model_date ON client_model_daily_usage(client_org_id, model_name, usage_date)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_model_daily_model_date ON client_model_daily_usage(model_name, usage_date)"))
    
    
    # Processed Generations indexes
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_proc_client_date ON processed_generations(client_org_id, generation_date)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_proc_processed_at ON processed_generations(processed_at)"))
    
    # Cleanup Log indexes
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_cleanup_log_date ON processed_generation_cleanup_log(cleanup_date)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_cleanup_success ON processed_generation_cleanup_log(success)"))