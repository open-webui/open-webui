"""add supervision_callback table

Revision ID: 8a2b4c6e1d3f
Revises: 56359461a091
Create Date: 2026-05-14

"""

from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = '8a2b4c6e1d3f'
down_revision: Union[str, None] = '56359461a091'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'supervision_callback',
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('event_id', sa.Text(), nullable=False),
        sa.Column('supervision_session_id', sa.Text(), nullable=False),
        sa.Column('agent_name', sa.Text(), nullable=False),
        sa.Column('evaluation_status', sa.Text(), nullable=False),
        sa.Column('external_message_id', sa.Text(), nullable=True),
        sa.Column('external_chat_id', sa.Text(), nullable=True),
        sa.Column('evaluated_at', sa.Text(), nullable=True),
        sa.Column('raw', sa.JSON(), nullable=True),
        sa.Column('received_at', sa.BigInteger(), nullable=False),
    )
    op.create_index(
        'ix_supervision_callback_event_id',
        'supervision_callback',
        ['event_id'],
        unique=True,
    )
    op.create_index(
        'ix_supervision_callback_external_chat_id',
        'supervision_callback',
        ['external_chat_id'],
    )


def downgrade():
    op.drop_index('ix_supervision_callback_external_chat_id', table_name='supervision_callback')
    op.drop_index('ix_supervision_callback_event_id', table_name='supervision_callback')
    op.drop_table('supervision_callback')
