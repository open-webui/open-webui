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

    # Idempotent: skip if created_at already exists on user
    try:
        if isinstance(database, pw.SqliteDatabase):
            cursor = database.execute_sql('PRAGMA table_info("user")')
            columns = [row[1] for row in cursor.fetchall()]
            if "created_at" in columns:
                return
        else:
            cursor = database.execute_sql(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'user' AND column_name = 'created_at'"
            )
            if cursor.fetchone() is not None:
                return
    except Exception:
        pass

    # Adding fields created_at, updated_at, last_active_at to the 'user' table
    try:
        migrator.add_fields(
            "user",
            created_at=pw.BigIntegerField(null=True),
            updated_at=pw.BigIntegerField(null=True),
            last_active_at=pw.BigIntegerField(null=True),
        )
    except Exception as e:
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            return
        raise

    try:
        migrator.sql(
            'UPDATE "user" SET created_at = timestamp, updated_at = timestamp, last_active_at = timestamp WHERE timestamp IS NOT NULL'
        )
    except Exception:
        pass

    try:
        migrator.remove_fields("user", "timestamp")
    except Exception:
        pass

    try:
        migrator.change_fields(
            "user",
            created_at=pw.BigIntegerField(null=False),
            updated_at=pw.BigIntegerField(null=False),
            last_active_at=pw.BigIntegerField(null=False),
        )
    except Exception:
        pass


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    # Recreate the timestamp field initially allowing null values for safe transition
    migrator.add_fields("user", timestamp=pw.BigIntegerField(null=True))

    # Copy the earliest created_at date back into the new timestamp field
    # This assumes created_at was originally a copy of timestamp
    migrator.sql('UPDATE "user" SET timestamp = created_at')

    # Remove the created_at and updated_at fields
    migrator.remove_fields("user", "created_at", "updated_at", "last_active_at")

    # Finally, alter the timestamp field to not allow nulls if that was the original setting
    migrator.change_fields("user", timestamp=pw.BigIntegerField(null=False))
