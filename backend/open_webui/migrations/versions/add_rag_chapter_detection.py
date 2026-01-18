"""add rag chapter detection config

Revision ID: add_rag_chapter_detection
Revises: add_hanyang_user_fields
Create Date: 2026-01-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "add_rag_chapter_detection"
down_revision: Union[str, None] = "add_hanyang_user_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add enable_rag_chapter_detection column to tagging_daemon_config
    with op.batch_alter_table('tagging_daemon_config', schema=None) as batch_op:
        batch_op.add_column(sa.Column('enable_rag_chapter_detection', sa.Boolean(), nullable=True))

    # Set default value for existing rows (False for backward compatibility)
    op.execute("UPDATE tagging_daemon_config SET enable_rag_chapter_detection = 0 WHERE enable_rag_chapter_detection IS NULL")

    # Make column non-nullable after setting defaults
    with op.batch_alter_table('tagging_daemon_config', schema=None) as batch_op:
        batch_op.alter_column('enable_rag_chapter_detection', nullable=False, server_default=sa.false())


def downgrade() -> None:
    # Remove enable_rag_chapter_detection column
    with op.batch_alter_table('tagging_daemon_config', schema=None) as batch_op:
        batch_op.drop_column('enable_rag_chapter_detection')
