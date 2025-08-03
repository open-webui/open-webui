"""
Extended automatic database initialization for environment-based usage tracking
Includes organization table creation and model linking
"""

import os
import logging
import json
from datetime import datetime
from typing import Optional, List, Dict
import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from open_webui.internal.db import get_db
from open_webui.env import SRC_LOG_LEVELS
from open_webui.constants import MAI_BUSINESS_MODEL_IDS

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
            # STEP 1: Ensure ALL tables exist (including organization tables)
            await ensure_all_tables(db)
            
            # STEP 2: Now safely check if client organization already exists
            existing_org = db.execute(
                text("SELECT id FROM client_organizations WHERE id = :org_id"),
                {"org_id": openrouter_external_user}
            ).fetchone()
            
            if existing_org:
                log.debug(f"Client organization already exists: {openrouter_external_user}")
                # Update the API key in case it changed
                current_time = int(time.time())
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
                        "updated_at": current_time,
                        "org_id": openrouter_external_user
                    }
                )
            else:
                # Create new client organization
                log.info(f"Creating new client organization: {openrouter_external_user}")
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
            
            # STEP 3: Link models to organization if new
            await ensure_organization_models(db, openrouter_external_user, organization_name)
            
            # STEP 4: Auto-populate members in development mode
            if "dev" in openrouter_external_user.lower() or "DEV" in organization_name:
                await populate_development_members(db, openrouter_external_user)
            
            db.commit()
            log.info(f"✅ Usage tracking initialized for {organization_name} ({openrouter_external_user})")
            return True
            
    except Exception as e:
        log.error(f"Failed to initialize usage tracking: {e}")
        return False


async def ensure_all_tables(db: Session) -> None:
    """
    Ensure ALL required tables exist, including organization tables.
    This is a comprehensive initialization that covers both usage tracking and organization model access.
    """
    try:
        # First, ensure usage tracking tables
        await ensure_usage_tracking_tables(db)
        
        # Then add organization-specific tables
        await ensure_organization_tables(db)
        
        # Create the user_available_models view
        await create_user_available_models_view(db)
        
        log.info("✅ All database tables initialized (usage tracking + organization access)")
        
    except Exception as e:
        log.error(f"Error ensuring all tables: {e}")
        raise


async def ensure_organization_tables(db: Session) -> None:
    """Create organization-specific tables for model access control"""
    try:
        log.info("📦 Creating organization access tables...")
        
        # 1. Organization Models - links organizations to their available models
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS organization_models (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                UNIQUE(organization_id, model_id),
                FOREIGN KEY (organization_id) REFERENCES client_organizations(id),
                FOREIGN KEY (model_id) REFERENCES model(id)
            )
        """))
        
        # 2. Organization Members - tracks which users belong to which organizations
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS organization_members (
                id TEXT PRIMARY KEY,
                organization_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT DEFAULT 'member',
                is_active INTEGER DEFAULT 1,
                joined_at INTEGER NOT NULL,
                UNIQUE(organization_id, user_id),
                FOREIGN KEY (organization_id) REFERENCES client_organizations(id),
                FOREIGN KEY (user_id) REFERENCES user(id)
            )
        """))
        
        # Create indexes for organization tables
        await create_organization_indexes(db)
        
        log.info("✅ Organization tables created/verified")
        
    except Exception as e:
        log.error(f"Error creating organization tables: {e}")
        raise


async def create_organization_indexes(db: Session) -> None:
    """Create performance indexes for organization tables"""
    try:
        # Organization members indexes
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_org_members_user_active 
            ON organization_members(user_id, is_active)
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_org_members_org_active 
            ON organization_members(organization_id, is_active)
        """))
        
        # Organization models indexes
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_org_models_org_active 
            ON organization_models(organization_id, is_active)
        """))
        
        db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_org_models_org_model 
            ON organization_models(organization_id, model_id)
        """))
        
        log.info("✅ Organization indexes created")
        
    except Exception as e:
        log.error(f"Error creating organization indexes: {e}")
        raise


async def create_user_available_models_view(db: Session) -> None:
    """Create a view that shows which models each user can access through their organizations"""
    try:
        # Drop existing view if it exists (views can't use CREATE IF NOT EXISTS in SQLite)
        db.execute(text("DROP VIEW IF EXISTS user_available_models"))
        
        # Create the view
        db.execute(text("""
            CREATE VIEW user_available_models AS
            SELECT DISTINCT
                om.user_id,
                u.name as user_name,
                u.email as user_email,
                orgm.model_id,
                m.name as model_name,
                org.name as organization_name,
                org.id as organization_id
            FROM organization_members om
            JOIN organization_models orgm ON om.organization_id = orgm.organization_id
            JOIN user u ON om.user_id = u.id
            JOIN model m ON orgm.model_id = m.id
            JOIN client_organizations org ON om.organization_id = org.id
            WHERE om.is_active = 1 
                AND orgm.is_active = 1 
                AND org.is_active = 1
                AND m.is_active = 1
        """))
        
        log.info("✅ User available models view created")
        
    except Exception as e:
        log.error(f"Error creating user_available_models view: {e}")
        # Non-critical error, don't raise


async def ensure_organization_models(db: Session, org_id: str, org_name: str) -> None:
    """
    Ensure organization has access to the 12 mAI business models.
    Links only the specific mAI models to the organization.
    """
    try:
        # Check if organization already has models
        existing_count = db.execute(
            text("SELECT COUNT(*) FROM organization_models WHERE organization_id = :org_id"),
            {"org_id": org_id}
        ).scalar()
        
        if existing_count > 0:
            log.debug(f"Organization {org_id} already has {existing_count} models linked")
            return
        
        # Use the 12 mAI business models
        model_ids = list(MAI_BUSINESS_MODEL_IDS)
        
        log.info(f"Linking {len(model_ids)} mAI business models to organization {org_name}")
        
        # First, ensure these models exist in the Models table
        await ensure_mai_models_exist(db, model_ids)
        
        # Link each model to the organization
        timestamp = int(time.time())
        linked_count = 0
        for model_id in model_ids:
            unique_id = f"{org_id}_{model_id.replace('/', '_')}_{timestamp}"
            try:
                db.execute(
                    text("""
                        INSERT OR IGNORE INTO organization_models 
                        (id, organization_id, model_id, is_active, created_at, updated_at)
                        VALUES (:id, :org_id, :model_id, 1, :created_at, :updated_at)
                    """),
                    {
                        "id": unique_id,
                        "org_id": org_id,
                        "model_id": model_id,
                        "created_at": timestamp,
                        "updated_at": timestamp
                    }
                )
                linked_count += 1
            except Exception as e:
                log.warning(f"Could not link model {model_id}: {e}")
        
        log.info(f"✅ {linked_count}/{len(model_ids)} mAI business models linked to organization {org_name}")
        
    except Exception as e:
        log.error(f"Error linking models to organization: {e}")
        # Non-critical error, don't raise


async def ensure_mai_models_exist(db: Session, model_ids: list) -> None:
    """
    Ensure the 12 mAI business models exist in the Models table.
    Creates missing models with default configuration.
    """
    try:
        timestamp = int(time.time())
        created_count = 0
        
        for model_id in model_ids:
            # Check if model exists
            existing = db.execute(
                text("SELECT COUNT(*) FROM model WHERE id = :model_id"),
                {"model_id": model_id}
            ).scalar()
            
            if existing == 0:
                # Create the model
                try:
                    # Extract provider and model name for display
                    parts = model_id.split('/')
                    provider = parts[0] if len(parts) > 1 else 'Unknown'
                    model_name = parts[1] if len(parts) > 1 else model_id
                    
                    db.execute(
                        text("""
                            INSERT OR IGNORE INTO model 
                            (id, user_id, base_model_id, name, meta, params, is_active, created_at, updated_at)
                            VALUES (:id, 'system', :base_model_id, :name, :meta, '{}', 1, :created_at, :updated_at)
                        """),
                        {
                            "id": model_id,
                            "base_model_id": model_id,  # Set to same as id to make it visible in get_models()
                            "name": f"{model_name.title()} ({provider})",
                            "meta": json.dumps({
                                "provider": provider,
                                "model_type": "openrouter",
                                "description": f"mAI Business Model - {model_name}"
                            }),
                            "created_at": timestamp,
                            "updated_at": timestamp
                        }
                    )
                    created_count += 1
                    log.debug(f"Created model: {model_id}")
                except Exception as e:
                    log.warning(f"Could not create model {model_id}: {e}")
        
        if created_count > 0:
            log.info(f"✅ Created {created_count} missing mAI business models")
        else:
            log.debug("All mAI business models already exist")
            
    except Exception as e:
        log.error(f"Error ensuring mAI models exist: {e}")
        # Non-critical error, don't raise


async def populate_development_members(db: Session, org_id: str) -> None:
    """
    In development mode, automatically add all non-system users to the organization.
    This simplifies testing and development.
    """
    try:
        log.info(f"🔧 Development mode: Auto-populating organization members")
        
        # Get all non-system users
        users = db.execute(
            text("""
                SELECT id, name, email 
                FROM user 
                WHERE email != 'system@mai.local' 
                    AND role != 'pending'
            """)
        ).fetchall()
        
        if not users:
            log.debug("No users to add to organization")
            return
        
        timestamp = int(time.time())
        added_count = 0
        
        for user_id, user_name, user_email in users:
            # Check if already a member
            existing = db.execute(
                text("""
                    SELECT 1 FROM organization_members 
                    WHERE organization_id = :org_id AND user_id = :user_id
                """),
                {"org_id": org_id, "user_id": user_id}
            ).fetchone()
            
            if existing:
                continue
            
            unique_id = f"{org_id}_{user_id}_{timestamp}"
            try:
                db.execute(
                    text("""
                        INSERT INTO organization_members
                        (id, organization_id, user_id, role, is_active, joined_at)
                        VALUES (:id, :org_id, :user_id, 'member', 1, :joined_at)
                    """),
                    {
                        "id": unique_id,
                        "org_id": org_id,
                        "user_id": user_id,
                        "joined_at": timestamp
                    }
                )
                added_count += 1
                log.debug(f"Added user {user_name} ({user_email}) to organization")
            except Exception as e:
                log.warning(f"Could not add user {user_id}: {e}")
        
        log.info(f"✅ Added {added_count} users to development organization")
        
    except Exception as e:
        log.error(f"Error populating development members: {e}")
        # Non-critical error, don't raise


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
        
        # 7. Processed Generations - deduplication tracking
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
        
        # 8. Processed Generation Cleanup Log - audit trail
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
        
        log.info("✅ Usage tracking database schema created/verified")
        
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