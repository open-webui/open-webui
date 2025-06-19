"""create_rag_processed_files_and_file_chunks_tables

Revision ID: e2a5c4f0d3b1
Revises: ca81bd47c050
Create Date: 2024-07-27 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import time # For default timestamp

# revision identifiers, used by Alembic.
revision = "e2a5c4f0d3b1"
down_revision = "ca81bd47c050" # Assuming this is the latest head
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "processed_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("processing_status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("metadata_", sa.JSON, nullable=True, name="metadata"), # Explicitly name column to avoid trailing underscore issues
        sa.Column("created_at", sa.BigInteger, nullable=False, server_default=sa.text(str(int(time.time()))))
    )

    op.create_table(
        "file_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("processed_files.id"), nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("chunk_metadata", sa.JSON, nullable=True),
        sa.Column("embedding", sa.JSON, nullable=True),
        sa.Column("created_at", sa.BigInteger, nullable=False, server_default=sa.text(str(int(time.time()))))
    )


def downgrade():
    op.drop_table("file_chunks")
    op.drop_table("processed_files")
