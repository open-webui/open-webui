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
    # Create the enum type first
    #op.execute("CREATE TYPE permissioncategory AS ENUM ('workspace', 'sharing', 'chat', 'features')")

    # Create a permissions table.
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), primary_key=True,  autoincrement=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('category', Enum('workspace', 'sharing', 'chat', 'features', name='permissioncategory'), nullable=False),
        sa.Column('description', sa.String()),
        sa.Column('default_value', sa.Boolean(), default=False),
    )

def downgrade():
    op.drop_table('permissions')
    # Drop the enum type
    op.execute("DROP TYPE permissioncategory")
