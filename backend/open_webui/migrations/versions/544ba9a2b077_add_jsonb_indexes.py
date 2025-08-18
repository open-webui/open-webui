"""Add JSONB indexes for optimized chat queries

Revision ID: 544ba9a2b077
Revises: d31026856c01
Create Date: 2024-12-08 16:00:00.000000

"""

from alembic import op
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
import logging

revision = "544ba9a2b077"
down_revision = "d31026856c01"
branch_labels = None
depends_on = None

log = logging.getLogger(__name__)


def upgrade():
    """
    Add optimized GIN indexes for JSONB columns in PostgreSQL.
    
    This migration:
    - Only runs on PostgreSQL databases
    - Checks actual column types before creating indexes
    - Creates GIN indexes only for JSONB columns
    - Handles errors gracefully without failing the migration
    """
    conn = op.get_bind()
    
    # Skip for non-PostgreSQL databases
    if conn.dialect.name != "postgresql":
        log.info(f"Skipping JSONB index creation for {conn.dialect.name} database")
        return
    
    # Check actual column types in the database
    try:
        result = conn.execute(
            text(
                "SELECT column_name, data_type "
                "FROM information_schema.columns "
                "WHERE table_name = 'chat' "
                "AND column_name IN ('chat', 'meta')"
            )
        )
        column_types = dict(result.fetchall())
        column_types = {k: v.lower() for k, v in column_types.items()}
    except ProgrammingError as e:
        log.error(f"Failed to query column types: {e}")
        return
    
    log.info(f"Column types detected: {column_types}")
    
    # Define indexes to create based on column types
    indexes_to_create = []
    
    if column_types.get("meta") == "jsonb":
        indexes_to_create.extend([
            {
                "name": "idx_chat_meta_tags_gin",
                "table": "chat",
                "columns": [text("(meta->'tags')")],
                "postgresql_using": "gin"
            },
            {
                "name": "idx_chat_meta_gin",
                "table": "chat",
                "columns": ["meta"],
                "postgresql_using": "gin"
            }
        ])
    
    if column_types.get("chat") == "jsonb":
        indexes_to_create.append({
            "name": "idx_chat_messages_gin",
            "table": "chat",
            "columns": [text("(chat->'history'->'messages')")],
            "postgresql_using": "gin"
        })
    
    # Create indexes
    for index in indexes_to_create:
        try:
            # Check if index already exists
            result = conn.execute(
                text(
                    "SELECT 1 FROM pg_indexes "
                    "WHERE schemaname = 'public' "
                    "AND tablename = :table "
                    "AND indexname = :name"
                ),
                {"table": index["table"], "name": index["name"]}
            )
            
            if not result.fetchone():
                op.create_index(**index)
                log.info(f"Created index: {index['name']}")
            else:
                log.info(f"Index already exists: {index['name']}")
                
        except ProgrammingError as e:
            # Log warning but don't fail the migration
            log.warning(f"Could not create index {index['name']}: {e}")


def downgrade():
    """
    Remove the JSONB GIN indexes.
    
    This will drop the indexes if they exist, allowing for clean rollback.
    """
    conn = op.get_bind()
    
    # Skip for non-PostgreSQL databases
    if conn.dialect.name != "postgresql":
        return
    
    # List of indexes to drop
    indexes_to_drop = [
        "idx_chat_meta_tags_gin",
        "idx_chat_meta_gin",
        "idx_chat_messages_gin"
    ]
    
    for index_name in indexes_to_drop:
        try:
            # Check if index exists before dropping
            result = conn.execute(
                text(
                    "SELECT 1 FROM pg_indexes "
                    "WHERE schemaname = 'public' "
                    "AND tablename = 'chat' "
                    "AND indexname = :name"
                ),
                {"name": index_name}
            )
            
            if result.fetchone():
                op.drop_index(index_name, "chat")
                log.info(f"Dropped index: {index_name}")
            else:
                log.info(f"Index does not exist: {index_name}")
                
        except ProgrammingError as e:
            log.warning(f"Could not drop index {index_name}: {e}")
