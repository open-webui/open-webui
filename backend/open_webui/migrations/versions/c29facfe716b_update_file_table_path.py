"""Update file table path

Revision ID: c29facfe716b
Revises: c69f45358db4
Create Date: 2024-10-20 17:02:35.241684

"""

from alembic import op
import sqlalchemy as sa
import json
from sqlalchemy.sql import table, column
from sqlalchemy import String, Text, JSON, and_

revision = "c29facfe716b"
down_revision = "c69f45358db4"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add the `path` column to the "file" table.
    op.add_column("file", sa.Column("path", sa.Text(), nullable=True))

    # 2. Convert the `meta` column from Text/JSONField to `JSON()`
    # Use Alembic's default batch_op for dialect compatibility.
    with op.batch_alter_table("file", schema=None) as batch_op:
        batch_op.alter_column(
            "meta",
            type_=sa.JSON(),
            existing_type=sa.Text(),
            existing_nullable=True,
            nullable=True,
            postgresql_using="meta::json",
        )

    # 3. Migrate legacy data from `meta` JSONField
    # Fetch and process `meta` data from the table, add values to the new `path` column as necessary.
    # We will use SQLAlchemy core bindings to ensure safety across different databases.

    file_table = table(
        "file", column("id", String), column("meta", JSON), column("path", Text)
    )

    # Create connection to the database
    connection = op.get_bind()

    # Get the rows where `meta` has a path and `path` column is null (new column)
    # Loop through each row in the result set to update the path
    results = connection.execute(
        sa.select(file_table.c.id, file_table.c.meta).where(
            and_(file_table.c.path.is_(None), file_table.c.meta.isnot(None))
        )
    ).fetchall()

    # Iterate over each row to extract and update the `path` from `meta` column
    for row in results:
        if "path" in row.meta:
            # Extract the `path` field from the `meta` JSON
            path = row.meta.get("path")

            # Update the `file` table with the new `path` value
            connection.execute(
                file_table.update()
                .where(file_table.c.id == row.id)
                .values({"path": path})
            )


def downgrade():
    # 1. Remove the `path` column
    op.drop_column("file", "path")

    # 2. Revert the `meta` column back to Text/JSONField
    with op.batch_alter_table("file", schema=None) as batch_op:
        batch_op.alter_column(
            "meta", type_=sa.Text(), existing_type=sa.JSON(), existing_nullable=True
        )
