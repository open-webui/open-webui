"""Add indexes for channel message and reaction lookups.

Revision ID: 9f6c2a8d1b43
Revises: 6a23bd107e54
"""

from alembic import op

revision = '9f6c2a8d1b43'
down_revision = '6a23bd107e54'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_message_channel_parent_created', 'message', ['channel_id', 'parent_id', 'created_at'])
    op.create_index('ix_message_parent_id', 'message', ['parent_id'])
    op.create_index('ix_message_reaction_message_id', 'message_reaction', ['message_id'])


def downgrade():
    op.drop_index('ix_message_reaction_message_id', table_name='message_reaction')
    op.drop_index('ix_message_parent_id', table_name='message')
    op.drop_index('ix_message_channel_parent_created', table_name='message')
