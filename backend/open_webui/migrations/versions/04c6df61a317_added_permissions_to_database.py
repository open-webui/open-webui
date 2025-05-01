"""Added permissions to the database

Revision ID: 04c6df61a317
Revises: 262aff902ca3
Create Date: 2025-04-22 14:55:58.948054

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Enum


# revision identifiers, used by Alembic.
revision: str = '04c6df61a317'
down_revision: Union[str, None] = '262aff902ca3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Create a permissions table.
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), primary_key=True,  autoincrement=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('category', Enum('workspace', 'sharing', 'chat', 'features', name='permissioncategory'), nullable=False),
        sa.Column('description', sa.String()),
    )

    # Create a role_permissions join table to allow many-to-many relationships between roles and permissions.
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('permission_id', sa.Integer(), nullable=False),
        sa.Column('value', sa.Boolean(), default=False),  # Added value column here
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )


def downgrade():
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.execute("DROP TYPE permissioncategory")
