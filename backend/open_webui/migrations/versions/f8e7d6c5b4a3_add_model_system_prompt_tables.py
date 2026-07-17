"""Add model system prompt version and binding tables

Revision ID: f8e7d6c5b4a3
Revises: 856c5b02fb54
Create Date: 2026-07-17 19:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from open_webui.migrations.util import get_existing_tables

revision: str = 'f8e7d6c5b4a3'
down_revision: str | None = '856c5b02fb54'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    existing_tables = set(get_existing_tables())
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'model_system_prompt_version' not in existing_tables:
        op.create_table(
            'model_system_prompt_version',
            sa.Column('id', sa.Text(), primary_key=True, nullable=False),
            sa.Column(
                'model_id',
                sa.Text(),
                sa.ForeignKey('model.id', ondelete='CASCADE'),
                nullable=False,
            ),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('commit_message', sa.Text(), nullable=True),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
        )

    inspector.clear_cache()
    if 'model_system_prompt_version' in inspector.get_table_names():
        version_indexes = {
            idx['name'] for idx in inspector.get_indexes('model_system_prompt_version')
        }
        if 'idx_model_system_prompt_version_model_id' not in version_indexes:
            op.create_index(
                'idx_model_system_prompt_version_model_id',
                'model_system_prompt_version',
                ['model_id'],
            )

    if 'model_system_prompt_binding' not in existing_tables:
        # active_version_id uses ON DELETE SET NULL so deleting a version row clears
        # the pointer without removing the binding (SQLite supports this via FK).
        op.create_table(
            'model_system_prompt_binding',
            sa.Column(
                'model_id',
                sa.Text(),
                sa.ForeignKey('model.id', ondelete='CASCADE'),
                primary_key=True,
                nullable=False,
            ),
            sa.Column('source', sa.Text(), nullable=False),
            sa.Column(
                'active_version_id',
                sa.Text(),
                sa.ForeignKey(
                    'model_system_prompt_version.id',
                    ondelete='SET NULL',
                ),
                nullable=True,
            ),
            sa.Column('connection_id', sa.Text(), nullable=True),
            sa.Column('external_name', sa.Text(), nullable=True),
            sa.Column('external_label', sa.Text(), nullable=True),
            sa.Column('external_version', sa.Text(), nullable=True),
            sa.Column('cached_content', sa.Text(), nullable=True),
            sa.Column('cached_version', sa.Text(), nullable=True),
            sa.Column('cached_at', sa.BigInteger(), nullable=True),
            sa.Column('cache_ttl_seconds', sa.Integer(), nullable=True),
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
            sa.CheckConstraint(
                "source IN ('local', 'langfuse')",
                name='ck_model_system_prompt_binding_source',
            ),
        )


def downgrade() -> None:
    op.drop_table('model_system_prompt_binding')
    op.drop_index(
        'idx_model_system_prompt_version_model_id',
        table_name='model_system_prompt_version',
    )
    op.drop_table('model_system_prompt_version')
