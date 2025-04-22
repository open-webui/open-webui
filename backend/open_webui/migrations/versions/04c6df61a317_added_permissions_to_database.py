"""Added permissions to the database

Revision ID: 04c6df61a317
Revises: 262aff902ca3
Create Date: 2025-04-22 14:55:58.948054

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db


# revision identifiers, used by Alembic.
revision: str = '04c6df61a317'
down_revision: Union[str, None] = '262aff902ca3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Create a permissions table.
    permissions_table = op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('description', sa.String()),
        sa.Column('default_value', sa.Boolean(), default=False),
    )

    # Insert default permissions
    default_permissions = [
        # Workspace permissions
        {'category': 'workspace', 'name': 'models', 'default_value': False},
        {'category': 'workspace', 'name': 'knowledge', 'default_value': False},
        {'category': 'workspace', 'name': 'prompts', 'default_value': False},
        {'category': 'workspace', 'name': 'tools', 'default_value': False},
        # Sharing permissions
        {'category': 'sharing', 'name': 'public_models', 'default_value': True},
        {'category': 'sharing', 'name': 'public_knowledge', 'default_value': True},
        {'category': 'sharing', 'name': 'public_prompts', 'default_value': True},
        {'category': 'sharing', 'name': 'public_tools', 'default_value': True},
        # Chat permissions.
        {'category': 'chat', 'name': 'controls', 'default_value': True},
        {'category': 'chat', 'name': 'file_upload', 'default_value': True},
        {'category': 'chat', 'name': 'delete', 'default_value': True},
        {'category': 'chat', 'name': 'edit', 'default_value': True},
        {'category': 'chat', 'name': 'stt', 'default_value': True},
        {'category': 'chat', 'name': 'tts', 'default_value': True},
        {'category': 'chat', 'name': 'call', 'default_value': True},
        {'category': 'chat', 'name': 'multiple_models', 'default_value': True},
        {'category': 'chat', 'name': 'temporary', 'default_value': True},
        {'category': 'chat', 'name': 'temporary_enforced', 'default_value': True},
        # Features permissions.
        {'category': 'features', 'name': 'direct_tool_servers', 'default_value': False},
        {'category': 'features', 'name': 'web_search', 'default_value': True},
        {'category': 'features', 'name': 'image_generation', 'default_value': True},
        {'category': 'features', 'name': 'code_interpreter', 'default_value': True},
    ]

    for perm in default_permissions:
        op.execute(
            permissions_table.insert().values(
                name=perm['name'],
                category=perm['category'],
                default_value=perm['default_value']
            )
        )


def downgrade():
    op.drop_table('permissions')
