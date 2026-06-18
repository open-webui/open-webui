"""Add context column to knowledge_file table

Revision ID: 1a2b3c4d5e6f
Revises: f1e2d3c4b5a6
Create Date: 2026-06-18 00:00:00.000000

Adds an optional `context` column to the `knowledge_file` join table.
When set to 'full', the file is injected directly into the LLM context
(bypassing chunked RAG retrieval) while the rest of the knowledge base
still uses vector search.
"""

import sqlalchemy as sa
from alembic import op

revision = '1a2b3c4d5e6f'
down_revision = 'f1e2d3c4b5a6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('knowledge_file', sa.Column('context', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('knowledge_file', 'context')
