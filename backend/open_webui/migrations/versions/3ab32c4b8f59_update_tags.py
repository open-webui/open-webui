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

    print(f"Primary Key: {existing_pk}")
    print(f"Unique Constraints: {unique_constraints}")
    print(f"Indexes: {existing_indexes}")

    with op.batch_alter_table("tag", schema=None) as batch_op:
        # Drop existing primary key constraint if it exists
        if existing_pk and existing_pk.get("constrained_columns"):
            pk_name = existing_pk.get("name")
            if pk_name:
                print(f"Dropping primary key constraint: {pk_name}")
                batch_op.drop_constraint(pk_name, type_="primary")

        # Now create the new primary key with the combination of 'id' and 'user_id'
        print("Creating new primary key with 'id' and 'user_id'.")
        batch_op.create_primary_key("pk_id_user_id", ["id", "user_id"])

        # Drop unique constraints that could conflict with the new primary key
        for constraint in unique_constraints:
            if (
                constraint["name"] == "uq_id_user_id"
            ):  # Adjust this name according to what is actually returned by the inspector
                print(f"Dropping unique constraint: {constraint['name']}")
                batch_op.drop_constraint(constraint["name"], type_="unique")

        for index in existing_indexes:
            if index["unique"]:
                if not any(
                    constraint["name"] == index["name"]
                    for constraint in unique_constraints
                ):
                    # You are attempting to drop unique indexes
                    print(f"Dropping unique index: {index['name']}")
                    batch_op.drop_index(index["name"])


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
