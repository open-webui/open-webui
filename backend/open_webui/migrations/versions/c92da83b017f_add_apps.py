"""Add apps."""

import sqlalchemy as sa
from alembic import op

revision = 'c92da83b017f'
down_revision = 'b8f2c6d91a04'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'app',
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('slug', sa.Text(), nullable=False, unique=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('user_id', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('api_key', sa.Text(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
    )
    with op.batch_alter_table('channel_member') as batch:
        batch.alter_column('user_id', existing_type=sa.Text(), nullable=True)
        batch.add_column(sa.Column('app_id', sa.Text(), nullable=True))
        batch.create_check_constraint('ck_channel_member_identity', '(user_id IS NULL) <> (app_id IS NULL)')
        batch.create_unique_constraint('uq_channel_member_app', ['channel_id', 'app_id'])
        batch.create_index('ix_channel_member_app_active', ['app_id', 'is_active'])
    op.add_column('message', sa.Column('app_id', sa.Text(), nullable=True))
    op.create_index('ix_message_app', 'message', ['app_id'])


def downgrade():
    # App-authored history cannot be converted to human messages without inventing an author.
    conn = op.get_bind()
    if conn.execute(sa.text('SELECT COUNT(*) FROM message WHERE app_id IS NOT NULL')).scalar():
        raise RuntimeError('Export/remove app messages before downgrading apps')
    op.drop_index('ix_message_app', table_name='message')
    op.drop_column('message', 'app_id')
    conn.execute(sa.text('DELETE FROM channel_member WHERE app_id IS NOT NULL'))
    with op.batch_alter_table('channel_member') as batch:
        batch.drop_index('ix_channel_member_app_active')
        batch.drop_constraint('uq_channel_member_app', type_='unique')
        batch.drop_constraint('ck_channel_member_identity', type_='check')
        batch.drop_column('app_id')
        batch.alter_column('user_id', existing_type=sa.Text(), nullable=False)
    op.drop_table('app')
