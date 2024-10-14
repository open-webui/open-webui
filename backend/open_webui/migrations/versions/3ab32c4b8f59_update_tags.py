"""Update tags

Revision ID: 3ab32c4b8f59
Revises: 1af9b942657b
Create Date: 2024-10-09 21:02:35.241684

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, select, update, column
from sqlalchemy.engine.reflection import Inspector

import json

revision = "3ab32c4b8f59"
down_revision = "1af9b942657b"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    # Inspecting the 'tag' table constraints and structure
    existing_pk = inspector.get_pk_constraint("tag")
    unique_constraints = inspector.get_unique_constraints("tag")
    existing_indexes = inspector.get_indexes("tag")

    print(existing_pk, unique_constraints)

    with op.batch_alter_table("tag", schema=None) as batch_op:
        # Drop unique constraints that could conflict with new primary key
        for constraint in unique_constraints:
            if constraint["name"] == "uq_id_user_id":
                batch_op.drop_constraint(constraint["name"], type_="unique")

        for index in existing_indexes:
            if index["unique"]:
                # Drop the unique index
                batch_op.drop_index(index["name"])

        # Drop existing primary key constraint if it exists
        if existing_pk and existing_pk.get("constrained_columns"):
            batch_op.drop_constraint(existing_pk["name"], type_="primary")

        # Immediately after dropping the old primary key, create the new one
        batch_op.create_primary_key("pk_id_user_id", ["id", "user_id"])


def downgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)

    current_pk = inspector.get_pk_constraint("tag")

    with op.batch_alter_table("tag", schema=None) as batch_op:
        # Drop the current primary key first, if it matches the one we know we added in upgrade
        if current_pk and "pk_id_user_id" == current_pk.get("name"):
            batch_op.drop_constraint("pk_id_user_id", type_="primary")

        # Restore the original primary key
        batch_op.create_primary_key("pk_id", ["id"])

        # Since primary key on just 'id' is restored, we now add back any unique constraints if necessary
        batch_op.create_unique_constraint("uq_id_user_id", ["id", "user_id"])
