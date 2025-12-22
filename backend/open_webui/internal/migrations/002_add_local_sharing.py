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
    
    # Check if share_id column already exists before adding it
    # This prevents errors when the column was already added by Alembic migrations
    column_exists = False
    
    try:
        if isinstance(database, pw.SqliteDatabase):
            # For SQLite, use PRAGMA table_info to check column existence
            cursor = database.execute_sql("PRAGMA table_info(chat)")
            columns = [row[1] for row in cursor.fetchall()]  # Column name is at index 1
            column_exists = "share_id" in columns
        else:
            # For PostgreSQL and other databases, query information_schema
            cursor = database.execute_sql(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'chat' AND column_name = 'share_id'"
            )
            column_exists = cursor.fetchone() is not None
    except Exception:
        # If checking fails, assume column doesn't exist and try to add it
        # The add_fields call will handle the error if column already exists
        column_exists = False
    
    # Only add the column if it doesn't exist
    if not column_exists:
        try:
            migrator.add_fields(
                "chat", share_id=pw.CharField(max_length=255, null=True, unique=True)
            )
        except Exception as e:
            # If column already exists (e.g., added by Alembic), ignore the error
            # This makes the migration idempotent
            error_msg = str(e).lower()
            if "duplicate column" not in error_msg and "already exists" not in error_msg:
                # Re-raise if it's a different error
                raise


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""

    migrator.remove_fields("chat", "share_id")
