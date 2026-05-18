from __future__ import annotations

"""Initial Alembic schema — creates all base tables.

Revision ID: 7e5b5dc7342b
Revises: —
Create Date: 2024-06-24 13:15:33.808998
"""

from typing import Sequence, Union

import open_webui.internal.db  # noqa: F401
import sqlalchemy as sa
from alembic import op
from open_webui.internal.db import JSONField
from open_webui.migrations.util import get_existing_tables

revision: str = '7e5b5dc7342b'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── Table definitions ────────────────────────────────────────────────────────
# Each table is only created if it doesn't already exist, because databases
# migrated from the Peewee era will already have these tables.

_TABLES: list[tuple[str, list[sa.Column], list]] = [
    (
        'auth',
        [
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('email', sa.String(), nullable=True),
            sa.Column('password', sa.Text(), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=True),
        ],
        [sa.PrimaryKeyConstraint('id')],
    ),
    (
        'chat',
        [
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=True),
            sa.Column('title', sa.Text(), nullable=True),
            sa.Column('chat', sa.Text(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=True),
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
            sa.Column('share_id', sa.Text(), nullable=True),
            sa.Column('archived', sa.Boolean(), nullable=True),
        ],
        [sa.PrimaryKeyConstraint('id'), sa.UniqueConstraint('share_id')],
    ),
    (
        'chatidtag',
        [
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('tag_name', sa.String(), nullable=True),
            sa.Column('chat_id', sa.String(), nullable=True),
            sa.Column('user_id', sa.String(), nullable=True),
            sa.Column('timestamp', sa.BigInteger(), nullable=True),
        ],
        [sa.PrimaryKeyConstraint('id')],
    ),
    (
        'document',
        [
            sa.Column('collection_name', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=True),
            sa.Column('title', sa.Text(), nullable=True),
            sa.Column('filename', sa.Text(), nullable=True),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('user_id', sa.String(), nullable=True),
            sa.Column('timestamp', sa.BigInteger(), nullable=True),
        ],
        [sa.PrimaryKeyConstraint('collection_name'), sa.UniqueConstraint('name')],
    ),
    (
        'file',
        [
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=True),
            sa.Column('filename', sa.Text(), nullable=True),
            sa.Column('meta', JSONField(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=True),
        ],
        [sa.PrimaryKeyConstraint('id')],
    ),
    (
        'function',
        [
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=True),
            sa.Column('name', sa.Text(), nullable=True),
            sa.Column('type', sa.Text(), nullable=True),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('meta', JSONField(), nullable=True),
            sa.Column('valves', JSONField(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True),
            sa.Column('is_global', sa.Boolean(), nullable=True),
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=True),
        ],
        [sa.PrimaryKeyConstraint('id')],
    ),
    (
        'memory',
        [
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=True),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=True),
        ],
        [sa.PrimaryKeyConstraint('id')],
    ),
    (
        'model',
        [
            sa.Column('id', sa.Text(), nullable=False),
            sa.Column('user_id', sa.Text(), nullable=True),
            sa.Column('base_model_id', sa.Text(), nullable=True),
            sa.Column('name', sa.Text(), nullable=True),
            sa.Column('params', JSONField(), nullable=True),
            sa.Column('meta', JSONField(), nullable=True),
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=True),
        ],
        [sa.PrimaryKeyConstraint('id')],
    ),
    (
        'prompt',
        [
            sa.Column('command', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=True),
            sa.Column('title', sa.Text(), nullable=True),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('timestamp', sa.BigInteger(), nullable=True),
        ],
        [sa.PrimaryKeyConstraint('command')],
    ),
    (
        'tag',
        [
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=True),
            sa.Column('user_id', sa.String(), nullable=True),
            sa.Column('data', sa.Text(), nullable=True),
        ],
        [sa.PrimaryKeyConstraint('id')],
    ),
    (
        'tool',
        [
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=True),
            sa.Column('name', sa.Text(), nullable=True),
            sa.Column('content', sa.Text(), nullable=True),
            sa.Column('specs', JSONField(), nullable=True),
            sa.Column('meta', JSONField(), nullable=True),
            sa.Column('valves', JSONField(), nullable=True),
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=True),
        ],
        [sa.PrimaryKeyConstraint('id')],
    ),
    (
        'user',
        [
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=True),
            sa.Column('email', sa.String(), nullable=True),
            sa.Column('role', sa.String(), nullable=True),
            sa.Column('profile_image_url', sa.Text(), nullable=True),
            sa.Column('last_active_at', sa.BigInteger(), nullable=True),
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=True),
            sa.Column('api_key', sa.String(), nullable=True),
            sa.Column('settings', JSONField(), nullable=True),
            sa.Column('info', JSONField(), nullable=True),
            sa.Column('oauth_sub', sa.Text(), nullable=True),
        ],
        [
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('api_key'),
            sa.UniqueConstraint('oauth_sub'),
        ],
    ),
]


def upgrade() -> None:
    existing = set(get_existing_tables())
    for name, columns, constraints in _TABLES:
        if name not in existing:
            op.create_table(name, *columns, *constraints)


def downgrade() -> None:
    for name, _, _ in reversed(_TABLES):
        op.drop_table(name)
