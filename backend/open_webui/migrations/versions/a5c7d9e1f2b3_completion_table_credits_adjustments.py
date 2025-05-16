"""Completion table credits adjustments

Revision ID: a5c7d9e1f2b3
Revises: f77bb6c4b3ba
Create Date: 2025-05-14 13:33:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = 'a5c7d9e1f2b3'
down_revision: Union[str, None] = 'f77bb6c4b3ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Create a new temporary table with the updated schema
    op.create_table(
        'completion_tmp',
        sa.Column('id', sa.String, primary_key=True, unique=True),
        sa.Column('user_id', sa.String, sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column('chat_id', sa.String),
        sa.Column('model', sa.Text),
        sa.Column('credits_used', sa.Float(), nullable=False),  # Changed from Integer to Float
        sa.Column('created_at', sa.BigInteger),
        sa.Column('time_saved_in_seconds', sa.Float),
    )

    # Copy data from old table to new table
    op.execute("""
        INSERT INTO completion_tmp (id, user_id, chat_id, model, credits_used, created_at, time_saved_in_seconds)
        SELECT id, user_id, chat_id, model, CAST(credits_used AS FLOAT), created_at, time_saved_in_seconds
        FROM completion;
    """)

    # Drop the old table
    op.drop_table('completion')

    # Rename the new table to the original name
    op.rename_table('completion_tmp', 'completion')


def downgrade():
    # Reverse the process
    op.create_table(
        'completion_tmp',
        sa.Column('id', sa.String, primary_key=True, unique=True),
        sa.Column('user_id', sa.String, sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column('chat_id', sa.String),
        sa.Column('model', sa.Text),
        sa.Column('credits_used', sa.Integer(), nullable=False),  # Changed back from Float to Integer
        sa.Column('created_at', sa.BigInteger),
        sa.Column('time_saved_in_seconds', sa.Float),
    )

    op.execute("""
        INSERT INTO completion_tmp (id, user_id, chat_id, model, credits_used, created_at, time_saved_in_seconds)
        SELECT id, user_id, chat_id, model, CAST(credits_used AS INTEGER), created_at, time_saved_in_seconds
        FROM completion;
    """)

    op.drop_table('completion')
    op.rename_table('completion_tmp', 'completion')
