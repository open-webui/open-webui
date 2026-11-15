"""Add renewable authentication sessions."""

from alembic import op
import sqlalchemy as sa

revision = '8bc7e5a902d1'
down_revision = 'e42c8f710a36'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'auth_session',
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('user_id', sa.Text(), nullable=True),
        sa.Column('refresh_token_id', sa.Text(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=False),
        *[sa.Column(key, sa.BigInteger(), nullable=False) for key in ('created_at', 'updated_at', 'expires_at')],
    )
    op.create_index('idx_auth_session_user', 'auth_session', ['user_id'])
    op.create_index('idx_auth_session_expires', 'auth_session', ['expires_at'])


def downgrade():
    op.drop_table('auth_session')
