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
            # Check if client organization already exists
            existing_org = db.execute(
                text("SELECT id FROM client_organizations WHERE id = :org_id"),
                {"org_id": openrouter_external_user}
            ).fetchone()
            
            if existing_org:
                log.debug(f"Client organization already exists: {openrouter_external_user}")
                # Update the API key in case it changed
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
                        "updated_at": datetime.now().isoformat(),
                        "org_id": openrouter_external_user
                    }
                )
            else:
                # Create new client organization
                log.info(f"Creating new client organization: {openrouter_external_user}")
                current_time = datetime.now().isoformat()
                
                db.execute(
                    text("""
                        INSERT INTO client_organizations 
                        (id, name, openrouter_api_key, markup_rate, is_active, created_at, updated_at)
                        VALUES (:id, :name, :api_key, :markup_rate, :is_active, :created_at, :updated_at)
                    """),
                    {
                        "id": openrouter_external_user,
                        "name": organization_name,
                        "api_key": openrouter_api_key,
                        "markup_rate": 1.3,  # Default mAI markup rate
                        "is_active": 1,
                        "created_at": current_time,
                        "updated_at": current_time
                    }
                )
            
            # Ensure usage tracking tables exist
            await ensure_usage_tracking_tables(db)
            
            db.commit()
            log.info(f"✅ Usage tracking initialized for {organization_name} ({openrouter_external_user})")
            return True
            
    except Exception as e:
        log.error(f"Failed to initialize usage tracking: {e}")
        return False


async def ensure_usage_tracking_tables(db: Session) -> None:
    """
    Ensure all required usage tracking tables exist with proper schema.
    This is idempotent - safe to run multiple times.
    """
    try:
        # Create client_organizations table if it doesn't exist
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS client_organizations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                openrouter_api_key TEXT NOT NULL,
                markup_rate REAL DEFAULT 1.3,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """))
        
        # Create client_user_daily_usage table if it doesn't exist
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS client_user_daily_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_org_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                usage_date DATE NOT NULL,
                openrouter_user_id TEXT,
                total_tokens INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                raw_cost REAL DEFAULT 0.0,
                markup_cost REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (client_org_id) REFERENCES client_organizations(id)
            )
        """))
        
        # Create client_model_daily_usage table if it doesn't exist
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS client_model_daily_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_org_id TEXT NOT NULL,
                model_name TEXT NOT NULL,
                provider TEXT NOT NULL,
                usage_date DATE NOT NULL,
                total_tokens INTEGER DEFAULT 0,
                total_requests INTEGER DEFAULT 0,
                raw_cost REAL DEFAULT 0.0,
                markup_cost REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (client_org_id) REFERENCES client_organizations(id)
            )
        """))
        
        # Create indexes for better query performance
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_user_usage_org_date 
            ON client_user_daily_usage(client_org_id, usage_date)
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_model_usage_org_date 
            ON client_model_daily_usage(client_org_id, usage_date)
        """))
        
        log.debug("Usage tracking tables verified/created")
        
    except Exception as e:
        log.error(f"Error ensuring usage tracking tables: {e}")
        raise