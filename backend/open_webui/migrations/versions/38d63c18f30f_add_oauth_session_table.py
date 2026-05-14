"""Add oauth_session table

Revision ID: 38d63c18f30f
Revises: 3af16a1c9fb6
Create Date: 2025-09-08 14:19:59.583921

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '38d63c18f30f'
down_revision: Union[str, None] = '3af16a1c9fb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())

    # ── Fix user.id PK only when it is genuinely wrong ────────────────
    # On databases migrated from the old Peewee layer the PK may have
    # drifted.  Fresh installs (init migration 7e5b5dc7342b) already
    # have a correct PK on 'id', so we must NOT attempt to re-create it
    # — PostgreSQL will reject a duplicate PRIMARY KEY constraint.
    pk_columns = inspector.get_pk_constraint('user')['constrained_columns']

    if pk_columns != ['id']:
        columns = inspector.get_columns('user')
        id_column = next((col for col in columns if col['name'] == 'id'), None)
        unique_constraints = inspector.get_unique_constraints('user')
        unique_columns = {tuple(u['column_names']) for u in unique_constraints}

        if id_column:
            with op.batch_alter_table('user') as batch_op:
                if pk_columns:
                    batch_op.drop_constraint(
                        inspector.get_pk_constraint('user')['name'],
                        type_='primary',
                    )
                if ('id',) not in unique_columns:
                    batch_op.create_unique_constraint('uq_user_id', ['id'])
                batch_op.create_primary_key('pk_user_id', ['id'])

    # ── Create oauth_session table (idempotent) ───────────────────────
    if 'oauth_session' not in existing_tables:
        op.create_table(
            'oauth_session',
            sa.Column('id', sa.Text(), primary_key=True, nullable=False, unique=True),
            sa.Column(
                'user_id',
                sa.Text(),
                sa.ForeignKey('user.id', ondelete='CASCADE'),
                nullable=False,
            ),
            sa.Column('provider', sa.Text(), nullable=False),
            sa.Column('token', sa.Text(), nullable=False),
            sa.Column('expires_at', sa.BigInteger(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )

    # Create indexes (idempotent — no-ops when table was just created
    # with the columns above, and safe to call if indexes already exist).
    existing_indexes = {
        idx['name'] for idx in inspector.get_indexes('oauth_session')
    } if 'oauth_session' in existing_tables else set()

    if 'idx_oauth_session_user_id' not in existing_indexes:
        op.create_index('idx_oauth_session_user_id', 'oauth_session', ['user_id'])
    if 'idx_oauth_session_expires_at' not in existing_indexes:
        op.create_index('idx_oauth_session_expires_at', 'oauth_session', ['expires_at'])
    if 'idx_oauth_session_user_provider' not in existing_indexes:
        op.create_index('idx_oauth_session_user_provider', 'oauth_session', ['user_id', 'provider'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_oauth_session_user_provider', table_name='oauth_session')
    op.drop_index('idx_oauth_session_expires_at', table_name='oauth_session')
    op.drop_index('idx_oauth_session_user_id', table_name='oauth_session')

    # Drop the table
    op.drop_table('oauth_session')
