"""add_document_chunk_table

Revision ID: 817da597db81
Revises: b2c3d4e5f6a7
Create Date: 2025-12-03 16:41:09.171266

"""
import os
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text, inspect


# revision identifiers, used by Alembic.
revision: str = '817da597db81'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Default vector length - should match PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH
# This can be overridden via environment variable, but 1536 is the default
VECTOR_LENGTH = int(os.environ.get("PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH", "1536"))


def upgrade() -> None:
    """
    Create the document_chunk table for pgvector support.
    This includes:
    - Creating the pgvector extension (if not exists)
    - Creating the document_chunk table with all required columns
    - Creating indexes for optimal performance
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())
    
    # Only proceed if document_chunk table doesn't exist
    if "document_chunk" in existing_tables:
        print("document_chunk table already exists, skipping creation")
        return
    
    # Create pgvector extension if it doesn't exist
    # This requires superuser privileges or the extension to be pre-installed
    try:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
        print("pgvector extension created or already exists")
    except Exception as e:
        print(f"Warning: Could not create pgvector extension: {e}")
        print("The extension may need to be created manually by a database administrator")
        # Don't fail the migration - the extension might already exist or be created separately
        conn.rollback()
    
    # Create the document_chunk table using raw SQL for the vector type
    # The vector column uses the pgvector extension's vector type
    conn.execute(text(f"""
        CREATE TABLE document_chunk (
            id TEXT NOT NULL PRIMARY KEY,
            vector vector({VECTOR_LENGTH}),
            collection_name TEXT NOT NULL,
            text TEXT,
            vmetadata JSONB
        );
    """))
    
    # Create indexes for optimal performance
    # IVFFlat index for vector similarity search (cosine distance)
    conn.execute(text(f"""
        CREATE INDEX idx_document_chunk_vector 
        ON document_chunk 
        USING ivfflat (vector vector_cosine_ops) 
        WITH (lists = 100);
    """))
    
    # Index on collection_name for filtering by collection
    conn.execute(text("""
        CREATE INDEX idx_document_chunk_collection_name 
        ON document_chunk (collection_name);
    """))
    
    conn.commit()
    print("document_chunk table and indexes created successfully")


def downgrade() -> None:
    """
    Drop the document_chunk table and related indexes.
    Note: We do NOT drop the pgvector extension as it might be used by other tables.
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())
    
    if "document_chunk" not in existing_tables:
        print("document_chunk table does not exist, skipping drop")
        return
    
    # Drop indexes first
    try:
        conn.execute(text("DROP INDEX IF EXISTS idx_document_chunk_vector;"))
        conn.execute(text("DROP INDEX IF EXISTS idx_document_chunk_collection_name;"))
    except Exception as e:
        print(f"Warning: Could not drop indexes: {e}")
    
    # Drop the table
    try:
        conn.execute(text("DROP TABLE document_chunk;"))
        conn.commit()
        print("document_chunk table dropped successfully")
    except Exception as e:
        print(f"Error dropping document_chunk table: {e}")
        conn.rollback()
        raise

