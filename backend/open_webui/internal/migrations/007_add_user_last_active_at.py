"""Peewee migrations -- 002_add_local_sharing.py.

Some examples (model - class or model name)::

    > Model = migrator.orm['table_name']            # Return model in current state by name
    > Model = migrator.ModelClass                   # Return model in current state by name

    > migrator.sql(sql)                             # Run custom SQL
    > migrator.run(func, *args, **kwargs)           # Run python function with the given args
    > migrator.create_model(Model)                  # Create a model (could be used as decorator)
    > migrator.remove_model(model, cascade=True)    # Remove a model
    > migrator.add_fields(model, **fields)          # Add fields to a model
    > migrator.change_fields(model, **fields)       # Change fields
    > migrator.remove_fields(model, *field_names, cascade=True)
    > migrator.rename_field(model, old_field_name, new_field_name)
    > migrator.rename_table(model, new_table_name)
    > migrator.add_index(model, *col_names, unique=False)
    > migrator.add_not_null(model, *field_names)
    > migrator.add_default(model, field_name, default)
    > migrator.add_constraint(model, name, sql)
    > migrator.drop_index(model, *col_names)
    > migrator.drop_not_null(model, *field_names)
    > migrator.drop_constraints(model, *constraints)

"""

from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""

    # Adding fields created_at and updated_at to the 'user' table
    cols = {c.name for c in database.get_columns("user")}
    
    if "created_at" not in cols:
      migrator.add_fields("user", created_at=pw.BigIntegerField(null=True))

    if "updated_at" not in cols:
      migrator.add_fields("user", updated_at=pw.BigIntegerField(null=True))

    if "last_active_at" not in cols:
      migrator.add_fields("user", last_active_at=pw.BigIntegerField(null=True))

    # Populate the new fields from an existing 'timestamp' field.
    # Use the ORM wrapper so identifier quoting works on every backend.
    User = migrator.orm["user"]
    (
        User.update(
            created_at=User.timestamp,
            updated_at=User.timestamp,
            last_active_at=User.timestamp,
        )
        .where(User.timestamp.is_null(False))
        .execute()
    )

    # Now that the data has been copied, remove the original 'timestamp' field
    migrator.remove_fields("user", "timestamp")

    # Update the fields to be not null now that they are populated
    migrator.change_fields(
        "user",
        created_at=pw.BigIntegerField(null=False),
        updated_at=pw.BigIntegerField(null=False),
        last_active_at=pw.BigIntegerField(null=False),
    )


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    # Recreate the timestamp field initially allowing null values for safe transition
    migrator.add_fields("user", timestamp=pw.BigIntegerField(null=True))

    # Copy the earliest created_at date back into the new timestamp field.
    User = migrator.orm["user"]
    User.update(timestamp=User.created_at).execute()

    # Remove the created_at and updated_at fields
    migrator.remove_fields("user", "created_at", "updated_at", "last_active_at")

    # Finally, alter the timestamp field to not allow nulls if that was the original setting
    migrator.change_fields("user", timestamp=pw.BigIntegerField(null=False))
