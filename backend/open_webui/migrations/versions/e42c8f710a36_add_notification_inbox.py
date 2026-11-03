"""Add persistent general inbox notifications.

Revision ID: e42c8f710a36
Revises: 6f8c2a91d4e7
"""

import sqlalchemy as sa
from alembic import op

revision = 'e42c8f710a36'
down_revision = '6f8c2a91d4e7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'notification',
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('event_type', sa.Text(), nullable=False),
        sa.Column('event_key', sa.Text(), nullable=False),
        sa.Column('actor_type', sa.Text(), nullable=False),
        sa.Column('actor_id', sa.Text(), nullable=True),
        sa.Column('resource_type', sa.Text(), nullable=True),
        sa.Column('resource_id', sa.Text(), nullable=True),
        sa.Column('object_type', sa.Text(), nullable=True),
        sa.Column('object_id', sa.Text(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('seen_at', sa.BigInteger(), nullable=True),
        sa.Column('read_at', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.UniqueConstraint('user_id', 'event_key', name='uq_notification_occurrence'),
        sa.CheckConstraint('(resource_type IS NULL) = (resource_id IS NULL)', name='ck_notification_resource'),
        sa.CheckConstraint('(object_type IS NULL) = (object_id IS NULL)', name='ck_notification_object'),
        sa.CheckConstraint("actor_type IN ('user', 'system')", name='ck_notification_actor'),
    )
    op.create_index('ix_notification_user_created', 'notification', ['user_id', 'created_at', 'id'])
    op.create_index(
        'ix_notification_unseen',
        'notification',
        ['user_id', 'created_at', 'id'],
        sqlite_where=sa.text('seen_at IS NULL'),
        postgresql_where=sa.text('seen_at IS NULL'),
    )
    op.create_index('ix_notification_resource', 'notification', ['resource_type', 'resource_id'])
    op.create_index('ix_notification_object', 'notification', ['object_type', 'object_id'])


def downgrade():
    op.drop_table('notification')
