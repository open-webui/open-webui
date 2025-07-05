"""Add api_key table

Revision ID: d5a13e7c8f9b
Revises: 7e5b5dc7342b
Create Date: 2024-12-31 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column, select
import uuid
import time


revision = "d5a13e7c8f9b"
down_revision = "9f0c9cd09105"
branch_labels = None
depends_on = None


def upgrade():
    # Creating the 'api_key' table
    print("Creating api_key table")
    api_key_table = op.create_table(
        "api_key",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("api_key", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.Column("last_used_at", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
    )

    print("Migrating existing API keys from user table to api_key table")
    # Representation of the existing 'user' table for migration
    user_table = table(
        "user",
        column("id", sa.String()),
        column("api_key", sa.String()),
    )

    # Select users that have API keys
    users_with_keys = op.get_bind().execute(
        select(
            user_table.c.id,
            user_table.c.api_key,
        ).where(user_table.c.api_key.isnot(None))
    )

    current_time = int(time.time())

    # Insert existing API keys into the new table
    for user in users_with_keys:
        if user.api_key:  # Double check it's not None
            op.get_bind().execute(
                api_key_table.insert().values(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    api_key=user.api_key,
                    name="Legacy API Key",  # Default name for migrated keys
                    created_at=current_time,
                    updated_at=current_time,
                )
            )

    print("Migration of API keys completed")


def downgrade():
    # Before dropping the table, migrate keys back to user table
    print("Migrating API keys back to user table")
    
    # Representation of tables for downgrade
    api_key_table = table(
        "api_key",
        column("user_id", sa.String()),
        column("api_key", sa.String()),
    )
    
    user_table = table(
        "user",
        column("id", sa.String()),
        column("api_key", sa.String()),
    )

    # Get the first API key for each user (since user table only supports one)
    api_keys = op.get_bind().execute(
        select(api_key_table.c.user_id, api_key_table.c.api_key)
        .distinct(api_key_table.c.user_id)
    )

    # Update user table with the API keys
    for key_row in api_keys:
        op.get_bind().execute(
            user_table.update()
            .where(user_table.c.id == key_row.user_id)
            .values(api_key=key_row.api_key)
        )

    print("Dropping api_key table")
    op.drop_table("api_key") 