"""Remove api_key column from user table

Revision ID: 1c888e354098
Revises: d5a13e7c8f9b
Create Date: 2024-12-31 12:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "1c888e354098"
down_revision = "d5a13e7c8f9b"
branch_labels = None
depends_on = None


def upgrade():
    # Remove the api_key column from the user table
    print("Removing api_key column from user table")
    op.drop_column("user", "api_key")
    print("Removed api_key column from user table")


def downgrade():
    # Add the api_key column back to the user table
    print("Adding api_key column back to user table")
    op.add_column(
        "user",
        sa.Column("api_key", sa.String(), nullable=True, unique=True)
    )
    print("Added api_key column back to user table") 