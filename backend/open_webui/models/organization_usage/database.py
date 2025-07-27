"""
Database Models for Organization Usage Tracking
SQLAlchemy models and database schema definitions (Clean Architecture Infrastructure Layer)
"""
from open_webui.internal.db import Base, JSONField
from sqlalchemy import BigInteger, Column, String, Text, Integer, Float, Date, Index, Boolean


####################
# Database Models (SQLAlchemy)
####################


class GlobalSettings(Base):
    __tablename__ = "global_settings"

    id = Column(String, primary_key=True)
    openrouter_provisioning_key = Column(Text, nullable=True)  # For creating client API keys
    default_markup_rate = Column(Float, default=1.3)
    billing_currency = Column(String, default="USD")
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class ProcessedGeneration(Base):
    """Track processed OpenRouter generations to prevent duplicates"""
    __tablename__ = "processed_generations"

    id = Column(String, primary_key=True)  # OpenRouter generation ID
    client_org_id = Column(String, nullable=False)
    generation_date = Column(Date, nullable=False)
    processed_at = Column(BigInteger, nullable=False)
    total_cost = Column(Float, nullable=False)
    total_tokens = Column(Integer, nullable=False)

    __table_args__ = (
        Index('idx_client_date', 'client_org_id', 'generation_date'),
        Index('idx_processed_at', 'processed_at'),
    )


class ProcessedGenerationCleanupLog(Base):
    """Track cleanup operations for audit and monitoring"""
    __tablename__ = "processed_generation_cleanup_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cleanup_date = Column(Date, nullable=False)  # Date when cleanup was performed
    cutoff_date = Column(Date, nullable=False)   # Records older than this were deleted
    days_retained = Column(Integer, nullable=False)  # Retention period used
    records_before = Column(Integer, nullable=False)
    records_deleted = Column(Integer, nullable=False)
    records_remaining = Column(Integer, nullable=False)
    old_tokens_removed = Column(BigInteger, nullable=False)
    old_cost_removed = Column(Float, nullable=False)
    storage_saved_kb = Column(Float, nullable=False)
    cleanup_duration_seconds = Column(Float, nullable=False)
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index('idx_cleanup_date', 'cleanup_date'),
        Index('idx_success', 'success'),
    )


class ClientOrganization(Base):
    __tablename__ = "client_organizations"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    openrouter_api_key = Column(Text, nullable=False, unique=True)  # Dedicated key per client
    openrouter_key_hash = Column(String, nullable=True)  # OpenRouter's key identifier
    markup_rate = Column(Float, default=1.3)
    monthly_limit = Column(Float, nullable=True)  # Optional spending limit
    billing_email = Column(String, nullable=True)
    timezone = Column(String, default="Europe/Warsaw")  # Client's local timezone for accurate date calculations
    is_active = Column(Integer, default=1)  # Boolean as integer
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    # Add indexes for performance
    __table_args__ = (
        Index('idx_api_key', 'openrouter_api_key'),
        Index('idx_active', 'is_active'),
    )


class UserClientMapping(Base):
    __tablename__ = "user_client_mapping"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)  # Open WebUI user ID
    client_org_id = Column(String, nullable=False)  # References client_organizations.id
    openrouter_user_id = Column(String, nullable=False)  # For OpenRouter user parameter
    is_active = Column(Integer, default=1)  # Boolean as integer
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    # Add indexes for performance
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_client_org_id', 'client_org_id'),
        Index('idx_openrouter_user_id', 'openrouter_user_id'),
    )


class ClientDailyUsage(Base):
    """
    Daily usage summaries - 99% storage reduction vs per-request tracking
    One record per client per day instead of thousands of request records
    """
    __tablename__ = "client_daily_usage"

    id = Column(String, primary_key=True)
    client_org_id = Column(String, nullable=False)  # References client_organizations.id
    usage_date = Column(Date, nullable=False)  # SQL Date type for daily grouping

    # Daily totals
    total_tokens = Column(BigInteger, default=0)
    total_requests = Column(Integer, default=0)
    raw_cost = Column(Float, default=0.0)  # OpenRouter cost
    markup_cost = Column(Float, default=0.0)  # Client cost (with markup)

    # Optional: Most used model (if needed for reporting)
    primary_model = Column(String, nullable=True)
    unique_users = Column(Integer, default=1)  # Count of unique users that day

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    # Indexes for performance
    __table_args__ = (
        Index('idx_client_date', 'client_org_id', 'usage_date'),
        Index('idx_usage_date', 'usage_date'),
    )


class ClientUserDailyUsage(Base):
    """
    Per-user daily usage summaries within each client organization
    Tracks which users are using how much
    """
    __tablename__ = "client_user_daily_usage"

    id = Column(String, primary_key=True)
    client_org_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)  # Open WebUI user ID
    openrouter_user_id = Column(String, nullable=False)  # OpenRouter tracking ID
    usage_date = Column(Date, nullable=False)
    
    # User's daily totals
    total_tokens = Column(BigInteger, default=0)
    total_requests = Column(Integer, default=0)
    raw_cost = Column(Float, default=0.0)
    markup_cost = Column(Float, default=0.0)
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    
    __table_args__ = (
        Index('idx_client_user_date', 'client_org_id', 'user_id', 'usage_date'),
        Index('idx_user_date', 'user_id', 'usage_date'),
    )


class ClientModelDailyUsage(Base):
    """
    Per-model daily usage summaries within each client organization
    Tracks which AI models are being used and their costs
    """
    __tablename__ = "client_model_daily_usage"

    id = Column(String, primary_key=True)
    client_org_id = Column(String, nullable=False)
    model_name = Column(String, nullable=False)  # e.g., "anthropic/claude-3.5-sonnet"
    usage_date = Column(Date, nullable=False)
    
    # Model's daily totals
    total_tokens = Column(BigInteger, default=0)
    total_requests = Column(Integer, default=0)
    raw_cost = Column(Float, default=0.0)
    markup_cost = Column(Float, default=0.0)
    
    # Optional model metadata
    provider = Column(String, nullable=True)  # e.g., "anthropic", "openai"
    
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    
    __table_args__ = (
        Index('idx_client_model_date', 'client_org_id', 'model_name', 'usage_date'),
        Index('idx_model_date', 'model_name', 'usage_date'),
    )